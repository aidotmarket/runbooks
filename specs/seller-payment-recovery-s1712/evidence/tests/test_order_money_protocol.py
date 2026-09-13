"""S1714 PostgreSQL ledger increment. Requires an explicitly disposable migrated DB.

No create_all or ad hoc chart seed: use the real full-ancestry migration database.
All test effects roll back; deployed triggers remain enabled.
"""
import asyncio
import importlib.util
import os
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.models.finance import BillingEntity, GLAccount, JournalEntry, JournalLine
from app.services.finance.engine import FinanceEngine


def disposable_url():
    value = os.environ['DATABASE_URL']
    url = make_url(value)
    expected = os.environ.get('S1714_DISPOSABLE_DATABASE', '')
    assert expected.startswith('s1714_') and url.database == expected
    assert url.host == '127.0.0.1' and url.port == int(os.environ['S1714_DISPOSABLE_PORT'])
    assert expected.startswith('s1714_f3_') and url.port != 5432
    assert len(os.environ.get('S1714_DISPOSABLE_CONTAINER_ID','')) == 64
    return value


@pytest.fixture
def provider_http_guard(monkeypatch, record_property):
    """Fail before provider/HTTP transport; permit only the verified PG socket."""
    import socket
    import requests
    import httpx
    import urllib.request
    import stripe._api_requestor
    attempts = []
    def refused(*args, **kwargs):
        attempts.append('unmocked provider HTTP')
        raise AssertionError('F3 unmocked provider HTTP forbidden')
    async def refused_async(*args, **kwargs):
        return refused(*args, **kwargs)
    monkeypatch.setattr(requests.sessions.Session, 'request', refused)
    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', refused)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, 'handle_async_request', refused_async)
    monkeypatch.setattr(urllib.request, 'urlopen', refused)
    monkeypatch.setattr(stripe._api_requestor._APIRequestor, 'request', refused)
    monkeypatch.setattr(stripe._api_requestor._APIRequestor, 'request_async', refused_async)
    original = socket.socket.connect
    original_ex = socket.socket.connect_ex
    def permitted(address):
        url = make_url(disposable_url())
        return isinstance(address, tuple) and address[:2] == (url.host, url.port)
    def connect(sock, address):
        if not permitted(address):
            return refused()
        return original(sock, address)
    def connect_ex(sock, address):
        if not permitted(address):
            return refused()
        return original_ex(sock, address)
    monkeypatch.setattr(socket.socket, 'connect', connect)
    monkeypatch.setattr(socket.socket, 'connect_ex', connect_ex)
    # This is an actual attempted requests boundary call, rejected before I/O.
    with pytest.raises(AssertionError, match='F3 unmocked provider HTTP forbidden'):
        requests.get('https://api.stripe.com/v1/charges/guard_self_test')
    with pytest.raises(AssertionError, match='F3 unmocked provider HTTP forbidden'):
        import stripe
        stripe.Charge.retrieve('ch_guard_self_test')
    with socket.socket() as probe:
        with pytest.raises(AssertionError, match='F3 unmocked provider HTTP forbidden'):
            probe.connect(('203.0.113.1',443))
    assert attempts == ['unmocked provider HTTP'] * 3
    record_property('provider_guard_self_test', 'fail-fast passed')
    attempts.clear()
    yield attempts
    record_property('unmocked_provider_attempts', len(attempts))
    assert attempts == [], 'Test attempted unmocked provider/HTTP transport'


@pytest.fixture(scope='module', autouse=True)
def migrated_protocol():
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    engine = create_engine(disposable_url())
    try:
        path = Path('alembic/versions/20260912_001_order_money_protocol.py')
        spec = importlib.util.spec_from_file_location('s1714_migration', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with engine.begin() as conn:
            assert conn.scalar(text('select current_database()')) == os.environ['S1714_DISPOSABLE_DATABASE']
            assert conn.scalar(text('show server_version_num')).startswith('17')
            assert conn.scalar(text("select count(*) from alembic_version where version_num='s1714_canonical_pi_binding_v1'")) == 1
            before = conn.execute(text('select id,entity_id,code,name from gl_accounts order by id')).all()
            with Operations.context(MigrationContext.configure(conn)):
                module.upgrade()
                module.upgrade()
            assert conn.execute(text('select id,entity_id,code,name from gl_accounts order by id')).all() == before
            assert conn.scalar(text("select count(*) from pg_trigger where tgname='trg_sync_order_to_transaction' and tgenabled='O'")) == 1
    finally:
        engine.dispose()


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(disposable_url().replace('postgresql://', 'postgresql+asyncpg://'), poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            try:
                await session.execute(text("set local lock_timeout='3s'"))
                yield session
            finally:
                await session.rollback()
    finally:
        await engine.dispose()


async def merchant(db):
    return (await db.execute(select(BillingEntity.id).where(BillingEntity.code == 'AIM_WY_LLC'))).scalar_one()


async def balances(db, eid, refs):
    rows = (await db.execute(text('''
        select a.code,sum(l.debit_cents-l.credit_cents) from journal_lines l
        join journal_entries j on j.id=l.entry_id join gl_accounts a on a.id=l.account_id
        where j.entity_id=:eid and j.source_ref=ANY(:refs) group by a.code
    '''), {'eid':eid,'refs':refs})).all()
    return {c: dict(rows).get(c, 0) for c in ('1000','2110','4000','5100')}


async def capture(db, eid, key):
    return await FinanceEngine().record_marketplace_capture(db=db, entity_id=eid,
        payment_id=uuid.uuid4(), stripe_pi_id='pi_'+key, gross_cents=2500,
        fee_cents=125, seller_cents=2375, origin='payment_event')


@pytest.mark.asyncio
@pytest.mark.parametrize('code',['1000','2110','4000','5100'])
async def test_migration_missing_account_reseed_preserves_other_accounts(db,code):
    # Run these cases on a fresh full-ancestry DB before committed money tests.
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    eid=await merchant(db)
    before=(await db.execute(text('select * from gl_accounts where entity_id<>:eid or code<>:code order by id'),{'eid':eid,'code':code})).all()
    await db.execute(text('delete from gl_accounts where entity_id=:eid and code=:code'),{'eid':eid,'code':code})
    def upgrade(sync):
        with Operations.context(MigrationContext.configure(sync.connection())):
            f2_migration().upgrade()
    await db.run_sync(upgrade)
    row=(await db.execute(text('select name,account_type,normal_balance,is_active,system_managed,allow_manual_posting from gl_accounts where entity_id=:eid and code=:code'),{'eid':eid,'code':code})).one()
    assert tuple(row)==(*FinanceEngine.MARKETPLACE_CHART[code],True,True,False)
    assert (await db.execute(text('select * from gl_accounts where entity_id<>:eid or code<>:code order by id'),{'eid':eid,'code':code})).all()==before
    await db.run_sync(upgrade)
    assert (await db.execute(text('select * from gl_accounts where entity_id<>:eid or code<>:code order by id'),{'eid':eid,'code':code})).all()==before


@pytest.mark.asyncio
@pytest.mark.parametrize('sequence', ['refund', 'payout_refund', 'refund_recovery'])
async def test_actual_marketplace_ledger_observation_orders(db, sequence):
    eid, key = await merchant(db), uuid.uuid4().hex
    engine = FinanceEngine()
    entry = await capture(db, eid, key)
    refs = [entry.source_ref]
    assert await balances(db,eid,refs) == {'1000':2500,'2110':-2375,'4000':-125,'5100':0}
    async def transfer(remaining):
        j = await engine.record_marketplace_transfer(db=db,entity_id=eid,order_id=uuid.uuid4(),
            stripe_transfer_id='tr_'+key,amount_cents=2375,remaining_payable_cents=remaining)
        refs.append(j.source_ref)
    if sequence == 'payout_refund':
        await transfer(2375)
    # Two partials; cumulative floor allocation gives fee 16 then 109.
    seller_remaining = 0 if sequence == 'payout_refund' else 2375
    j = await engine.record_marketplace_refund(db=db,entity_id=eid,refund_id=uuid.uuid4(),
        stripe_refund_id='re_a'+key,amount_cents=333,fee_refund_cents=16,
        seller_refund_cents=317,remaining_payable_cents=seller_remaining)
    refs.append(j.source_ref)
    if sequence != 'payout_refund':
        assert await balances(db,eid,refs) == {'1000':2167,'2110':-2058,'4000':-109,'5100':0}
    j = await engine.record_marketplace_refund(db=db,entity_id=eid,refund_id=uuid.uuid4(),
        stripe_refund_id='re_b'+key,amount_cents=2167,fee_refund_cents=109,
        seller_refund_cents=2058,remaining_payable_cents=max(seller_remaining-317,0))
    refs.append(j.source_ref)
    if sequence == 'refund_recovery':
        await transfer(0)
    expected = {'1000':0,'2110':0,'4000':0,'5100':0} if sequence == 'refund' else {
        '1000':-2375,'2110':0,'4000':0,'5100':2375}
    assert await balances(db,eid,refs) == expected


@pytest.mark.asyncio
async def test_capture_replay_validates_source_and_exact_allocation(db):
    eid, key, pid = await merchant(db), uuid.uuid4().hex, uuid.uuid4()
    args = dict(db=db,entity_id=eid,payment_id=pid,stripe_pi_id='pi_'+key,
                gross_cents=2500,fee_cents=125,seller_cents=2375,origin='payment_event')
    engine = FinanceEngine()
    first = await engine.record_marketplace_capture(**args)
    assert (await engine.record_marketplace_capture(**args)).id == first.id
    with pytest.raises(ValueError,match='Conflicting historical'):
        await engine.record_marketplace_capture(**{**args,'fee_cents':126,'seller_cents':2374})
    with pytest.raises(ValueError,match='Conflicting historical'):
        await engine.record_marketplace_capture(**{**args,'payment_id':uuid.uuid4()})


@pytest.mark.asyncio
@pytest.mark.parametrize('field,value', [('name','Wrong'),('normal_balance','debit'),('is_active',False),('allow_manual_posting',True)])
async def test_runtime_rejects_conflicting_chart(db, field, value):
    eid = await merchant(db)
    account = (await db.execute(select(GLAccount).where(GLAccount.entity_id==eid,GLAccount.code=='2110'))).scalar_one()
    setattr(account,field,value)
    await db.flush()
    with pytest.raises(ValueError,match='chart mismatch'):
        await capture(db,eid,uuid.uuid4().hex)


@pytest.mark.asyncio
async def test_runtime_rejects_legacy_entity(db):
    with pytest.raises(ValueError,match='merchant binding'):
        await capture(db,uuid.UUID('00000000-0000-0000-0000-000000000001'),uuid.uuid4().hex)


@pytest.mark.asyncio
@pytest.mark.parametrize('amount', [0, -1, True, 2500.0])
async def test_integer_positive_capture_amount(db, amount):
    with pytest.raises(ValueError,match='integer cents'):
        await FinanceEngine().record_marketplace_capture(db=db,entity_id=await merchant(db),
            payment_id=uuid.uuid4(),stripe_pi_id='pi_bad',gross_cents=amount,
            fee_cents=125,seller_cents=2375,origin='payment_event')


@pytest.mark.asyncio
async def test_journals_do_not_commit_caller_transaction(db):
    eid,key=await merchant(db),uuid.uuid4().hex
    await capture(db,eid,key)
    await db.rollback()
    assert (await db.execute(select(JournalEntry.id).where(JournalEntry.source_ref=='marketplace_payment:pi_'+key))).scalar_one_or_none() is None


@pytest.mark.parametrize('value',[9007199254740992,-9007199254740992,1.0,float('nan'),{'x':'é'}])
def test_f1_hash_refuses_noncanonical_values(value):
    from app.services.order_money_service import canonical_digest,OrderMoneyConflict
    with pytest.raises(OrderMoneyConflict):
        canonical_digest(value)


def test_f1_hash_numeric_key_golden_bytes():
    import hashlib
    from app.services.order_money_service import canonical_digest
    value={'2':{},'10':[],'nested':[{'2':False,'10':None},9007199254740991]}
    expected=b'{"10":[],"2":{},"nested":[{"10":null,"2":false},9007199254740991]}'
    assert canonical_digest(value)==hashlib.sha256(expected).hexdigest()


def test_lock_order_assertion_rejects_every_reversed_adjacent_edge():
    from app.services.order_money_service import LOCK_ORDER,assert_lock_sequence,OrderMoneyConflict
    assert_lock_sequence(LOCK_ORDER)
    for index in range(len(LOCK_ORDER)-1):
        with pytest.raises(OrderMoneyConflict):
            assert_lock_sequence([LOCK_ORDER[index+1],LOCK_ORDER[index]])


@pytest.mark.asyncio
@pytest.mark.parametrize('blocked_node',['accounting_periods','gl_accounts'])
async def test_real_finance_lock_order_before_posting(db,blocked_node):
    import asyncio
    from datetime import datetime,timezone
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    eid=await merchant(db)
    engine=FinanceEngine()
    now=datetime.now(timezone.utc)
    period=await engine._get_or_create_period(eid,now.year,now.month,db)
    period_id=period.id
    account_id=await db.scalar(text("select id from gl_accounts where entity_id=:id and code='1000'"),{'id':eid})
    await db.commit()
    ae=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    async with AsyncSession(ae) as blocker,AsyncSession(ae) as observer:
        first=await blocker.scalar(text('select pg_backend_pid()'))
        second=await db.scalar(text('select pg_backend_pid()'))
        await blocker.execute(text(f'select id from {blocked_node} where id=:id for update'),{'id':period_id if blocked_node=='accounting_periods' else account_id})
        # Draft template construction is a real supported API, not a posting
        # bypass; positive posted ledger tests remain separate and mandatory.
        task=asyncio.create_task(engine._build_entry_from_template('credit_purchase',2500,'lock:'+uuid.uuid4().hex,'lock proof','system',eid,db))
        try:
            async with asyncio.timeout(3):
                while not await observer.scalar(text('select :a=ANY(pg_blocking_pids(:b))'),{'a':first,'b':second}):
                    await asyncio.sleep(.01)
            if blocked_node=='accounting_periods':
                await observer.execute(text('select id from gl_accounts where id=:id for update nowait'),{'id':account_id})
                await observer.rollback()
            await blocker.rollback()
            entry=await asyncio.wait_for(task,3)
            assert entry.posted_at is None
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task,return_exceptions=True)
            await db.rollback()
    await ae.dispose()


@pytest.mark.asyncio
async def test_marketplace_journal_lock_follows_accounts(db):
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from sqlalchemy.exc import DBAPIError
    eid,key=await merchant(db),uuid.uuid4().hex
    engine=FinanceEngine()
    # An unposted historical journal must wait for its lock then refuse; it is
    # never relabeled or treated as a valid capture to get past posting checks.
    draft=await engine._build_entry_from_template('credit_purchase',2500,'marketplace_payment:pi_'+key,'legacy draft','system',eid,db)
    jid=draft.id
    account_id=await db.scalar(text("select id from gl_accounts where entity_id=:eid and code='1000'"),{'eid':eid})
    await db.commit()
    ae=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    async with AsyncSession(ae) as owner,AsyncSession(ae) as observer:
        first=await owner.scalar(text('select pg_backend_pid()'))
        second=await db.scalar(text('select pg_backend_pid()'))
        await owner.execute(text('select id from journal_entries where id=:id for update'),{'id':jid})
        task=asyncio.create_task(capture(db,eid,key))
        try:
            async with asyncio.timeout(3):
                while not await observer.scalar(text('select :a=ANY(pg_blocking_pids(:b))'),{'a':first,'b':second}):
                    await asyncio.sleep(.01)
            with pytest.raises(DBAPIError):
                await observer.execute(text('select id from gl_accounts where id=:id for update nowait'),{'id':account_id})
            await observer.rollback()
            await owner.rollback()
            with pytest.raises(ValueError,match='Conflicting historical'):
                await asyncio.wait_for(task,3)
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task,return_exceptions=True)
            await db.rollback()
    await ae.dispose()


def f2_migration():
    spec = importlib.util.spec_from_file_location('s1714_f2', Path('alembic/versions/20260912_001_order_money_protocol.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_f2_historical_body_normalization_is_exact():
    import re
    module=f2_migration()
    for name in ('000_initial.py','20260318_001_bq_financial_system_gate2_phase1.py'):
        source=Path('alembic/versions',name).read_text()
        body=re.search(r'CREATE (?:OR REPLACE )?FUNCTION (?:public\.)?finance_prevent_posted_entry_mutation\(\).*?AS \$\$(.*?)\$\$',source,re.S).group(1)
        assert ' '.join(body.split())==' '.join(module.POSTED_OLD_BODY.split())
    from app.services import refund_processing_service as runtime
    assert runtime.POSTED_BODY==module.POSTED_BODY
    assert runtime.POSTED_GUARDS==module.POSTED_GUARDS


@pytest.mark.asyncio
@pytest.mark.parametrize('variant', ['old','corrected'])
async def test_f2_recognized_upgrade_preserves_all_other_guards(db,variant):
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    from app.services.refund_processing_service import posting_guard_report,assert_order_money_protocol_ready
    module=f2_migration()
    body=module.POSTED_OLD_BODY if variant=='old' else module.POSTED_BODY
    await db.execute(text(f'CREATE OR REPLACE FUNCTION public.finance_prevent_posted_entry_mutation() RETURNS trigger LANGUAGE plpgsql AS $f2${body}$f2$'))
    before=await db.run_sync(posting_guard_report)
    def upgrade(sync):
        with Operations.context(MigrationContext.configure(sync.connection())):
            module.upgrade()
            module.upgrade()
    accounts=(await db.execute(text('select * from gl_accounts order by id'))).all()
    entities=(await db.execute(text('select * from billing_entities order by id'))).all()
    await db.run_sync(upgrade)
    after=await db.run_sync(posting_guard_report)
    assert after['corrected_ready'] and after['sole_attachment_count']==1
    assert before['guards'][1:]==after['guards'][1:]
    assert (await db.execute(text('select * from gl_accounts order by id'))).all()==accounts
    assert (await db.execute(text('select * from billing_entities order by id'))).all()==entities
    assert await assert_order_money_protocol_ready(db)==await merchant(db)


F2_DRIFTS = [
    ('missing_function', 'DROP FUNCTION public.finance_prevent_posted_entry_mutation() CASCADE'),
    ('unknown_body', "CREATE OR REPLACE FUNCTION public.finance_prevent_posted_entry_mutation() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RETURN NEW; END;$$"),
    ('security', 'ALTER FUNCTION public.finance_prevent_posted_entry_mutation() SECURITY DEFINER'),
    ('config', "ALTER FUNCTION public.finance_prevent_posted_entry_mutation() SET search_path=pg_catalog"),
    ('extra_attachment', 'CREATE TRIGGER f2_extra BEFORE UPDATE ON public.journal_lines FOR EACH ROW EXECUTE FUNCTION public.finance_prevent_posted_entry_mutation()'),
    ('missing_trigger', 'DROP TRIGGER trg_immutable_posted_entries ON public.journal_entries'),
]
for table,name,fn,tgtype in f2_migration().POSTED_GUARDS:
    for mode in ('DISABLE','ENABLE REPLICA','ENABLE ALWAYS'):
        F2_DRIFTS.append((name+'_'+mode, f'ALTER TABLE public.{table} {mode} TRIGGER {name}'))
for label,clause in [
    ('when', 'BEFORE UPDATE OR DELETE ON public.journal_entries FOR EACH ROW WHEN (OLD.status=\'draft\')'),
    ('statement','BEFORE UPDATE OR DELETE ON public.journal_entries FOR EACH STATEMENT'),
    ('insert','BEFORE INSERT OR UPDATE ON public.journal_entries FOR EACH ROW'),
    ('after','AFTER UPDATE OR DELETE ON public.journal_entries FOR EACH ROW'),
    ('columns','BEFORE UPDATE OF status OR DELETE ON public.journal_entries FOR EACH ROW'),
    ('constraint','AFTER UPDATE OR DELETE ON public.journal_entries DEFERRABLE INITIALLY DEFERRED FOR EACH ROW'),
]:
    kind='CONSTRAINT ' if label=='constraint' else ''
    F2_DRIFTS.append((label, f'DROP TRIGGER trg_immutable_posted_entries ON public.journal_entries; CREATE {kind}TRIGGER trg_immutable_posted_entries {clause} EXECUTE FUNCTION public.finance_prevent_posted_entry_mutation()'))
F2_DRIFTS.extend([
    ('args', "DROP TRIGGER trg_immutable_posted_entries ON public.journal_entries; CREATE TRIGGER trg_immutable_posted_entries BEFORE UPDATE OR DELETE ON public.journal_entries FOR EACH ROW EXECUTE FUNCTION public.finance_prevent_posted_entry_mutation('unexpected')"),
    ('foreign_function', "CREATE FUNCTION public.f2_foreign_guard() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RETURN NEW; END;$$; DROP TRIGGER trg_immutable_posted_entries ON public.journal_entries; CREATE TRIGGER trg_immutable_posted_entries BEFORE UPDATE OR DELETE ON public.journal_entries FOR EACH ROW EXECUTE FUNCTION public.f2_foreign_guard()"),
    ('return_type', 'DROP FUNCTION public.finance_prevent_posted_entry_mutation() CASCADE; CREATE FUNCTION public.finance_prevent_posted_entry_mutation() RETURNS integer LANGUAGE sql AS $$SELECT 1$$'),
])


@pytest.mark.asyncio
@pytest.mark.parametrize('label,ddl',F2_DRIFTS,ids=[v[0] for v in F2_DRIFTS])
async def test_f2_migration_readiness_report_refuse_catalog_drift(db,label,ddl):
    from app.services.refund_processing_service import posting_guard_report,assert_order_money_protocol_ready,OrderMoneyProtocolUnavailable
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    # Execute each DDL separately for the asyncpg prepared statement protocol.
    if label=='foreign_function':
        await db.execute(text('CREATE FUNCTION public.f2_foreign_guard() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RETURN NEW; END;$$'))
        ddl=ddl.split('$$; ',1)[1]
    if label in ('unknown_body','foreign_function') and 'AS $$' in ddl:
        await db.execute(text(ddl))
    else:
        for statement in ddl.split('; '):
            await db.execute(text(statement))
    report=await db.run_sync(posting_guard_report)
    assert not report['corrected_ready'] and report['errors'], (label,report)
    with pytest.raises(OrderMoneyProtocolUnavailable):
        await assert_order_money_protocol_ready(db)
    def migrate(sync):
        with Operations.context(MigrationContext.configure(sync.connection())):
            f2_migration().upgrade()
    with pytest.raises(RuntimeError,match='F2 posting guard refuses'):
        await db.run_sync(migrate)


async def assert_posted_and_immutable(db, entry, expected):
    from sqlalchemy.exc import DBAPIError
    await db.refresh(entry)
    assert entry.status=='posted' and entry.posted_at is not None
    eid=entry.id
    row=(await db.execute(text('select * from journal_entries where id=:id'),{'id':eid})).one()
    lines=(await db.execute(text('select * from journal_lines where entry_id=:id order by id'),{'id':eid})).all()
    actual=(await db.execute(text('select a.code,l.debit_cents,l.credit_cents from journal_lines l join gl_accounts a on a.id=l.account_id where l.entry_id=:id order by a.code'),{'id':eid})).all()
    assert [tuple(x) for x in actual]==sorted(expected)
    assert sum(x[1] for x in actual)==sum(x[2] for x in actual)>0
    for query in ('update journal_entries set description=description where id=:id',
                  'delete from journal_entries where id=:id',
                  'update journal_lines set memo=memo where entry_id=:id',
                  'delete from journal_lines where entry_id=:id'):
        with pytest.raises(DBAPIError,match='immutable'):
            async with db.begin_nested():
                await db.execute(text(query),{'id':eid})
        assert (await db.execute(text('select * from journal_entries where id=:id'),{'id':eid})).one()==row
        assert (await db.execute(text('select * from journal_lines where entry_id=:id order by id'),{'id':eid})).all()==lines


@pytest.mark.asyncio
@pytest.mark.parametrize('caller', ['commission','credit_purchase','subscription_payment','stripe_fee','refund','api_cost'])
async def test_f2_six_shared_callers_actual_posting_and_immutability(db,caller):
    # Use the real ancestry-seeded legacy chart. No new accounts or templates.
    from app.services.finance.engine import AIMARKET_ENTITY_ID
    engine,key=FinanceEngine(),uuid.uuid4().hex
    args,expected={
        'commission':(dict(order_id=uuid.uuid4(),amount_cents=2500,rate_bps=500),[('1000',125,0),('4000',0,125)]),
        'credit_purchase':(dict(user_id=uuid.uuid4(),amount_cents=2500,stripe_pi_id='pi_'+key),[('1000',2500,0),('4020',0,2500)]),
        'subscription_payment':(dict(subscription_id=uuid.uuid4(),amount_cents=2500,plan='test',stripe_pi_id='pi_'+key),[('1000',2500,0),('4010',0,2500)]),
        'stripe_fee':(dict(payment_id=uuid.uuid4(),fee_cents=103,stripe_charge_id='ch_'+key),[('6000',103,0),('1000',0,103)]),
        'refund':(dict(payment_id=uuid.uuid4(),amount_cents=2500,reason='requested_by_customer',stripe_refund_id='re_'+key),[('4000',2500,0),('1000',0,2500)]),
        'api_cost':(dict(provider='test',amount_cents=2500,period_id=uuid.uuid4(),idempotency_key=key),[('5000',2500,0),('2000',0,2500)]),
    }[caller]
    entry=await getattr(engine,'record_'+caller)(db=db,entity_id=AIMARKET_ENTITY_ID,**args)
    await assert_posted_and_immutable(db,entry,expected)


@pytest.mark.asyncio
async def test_f2_manual_post_timestamp_and_actual_trigger_status(db):
    engine=FinanceEngine()
    entry=await engine.propose_manual_journal(lines=[dict(account_code='1000',debit_cents=17),dict(account_code='4000',credit_cents=17)],
        description='F2 manual',created_by='test:author',idempotency_key=uuid.uuid4().hex,db=db)
    assert entry.status=='draft' and entry.posted_at is None
    await engine.approve_and_post_entry(entry.id,'test:approver',db)
    # The manual method only sets posted_at. The real balanced-on-post trigger
    # also supplies status=posted; refresh proves that distinct implementation.
    await assert_posted_and_immutable(db,entry,[('1000',17,0),('4000',0,17)])


@pytest.mark.asyncio
async def test_f2_draft_edit_delete_and_balance_period_entity_guards(db):
    from sqlalchemy.exc import DBAPIError
    engine=FinanceEngine()
    entry=await engine._build_entry_from_template('commission_earned',17,'f2:'+uuid.uuid4().hex,'draft','system',await merchant(db),db)
    await db.execute(text("update journal_entries set description='edited draft' where id=:id"),{'id':entry.id})
    await db.refresh(entry)
    assert entry.description=='edited draft' and entry.posted_at is None and entry.status=='draft'
    with pytest.raises(DBAPIError,match='not balanced'):
        async with db.begin_nested():
            await db.execute(text('update journal_lines set debit_cents=18 where entry_id=:id and debit_cents=17'),{'id':entry.id})
            await db.execute(text("update journal_entries set status='posted' where id=:id"),{'id':entry.id})
    with pytest.raises(DBAPIError,match='closed accounting period'):
        async with db.begin_nested():
            await db.execute(text("update accounting_periods set status='closed' where id=:id"),{'id':entry.period_id})
            await db.execute(text("update journal_entries set status='posted' where id=:id"),{'id':entry.id})
    with pytest.raises(DBAPIError,match='same entity'):
        async with db.begin_nested():
            await db.execute(text("update journal_lines set account_id=(select id from gl_accounts where entity_id='00000000-0000-0000-0000-000000000001' and code='1000') where entry_id=:id"),{'id':entry.id})
    await db.execute(text('delete from journal_lines where entry_id=:id'),{'id':entry.id})
    await db.execute(text('delete from journal_entries where id=:id'),{'id':entry.id})
    assert await db.scalar(text('select count(*) from journal_entries where id=:id'),{'id':entry.id})==0


@pytest.mark.asyncio
@pytest.mark.parametrize('field,value',[('name','foreign account'),('account_type','expense'),('normal_balance','debit'),('is_active',False),('system_managed',False),('allow_manual_posting',True)])
async def test_migration_conflicting_chart_is_never_rewritten(db,field,value):
    from alembic.operations import Operations
    from alembic.migration import MigrationContext
    eid=await merchant(db)
    await db.execute(text(f"update gl_accounts set {field}=:v where entity_id=:eid and code='2110'"),{'v':value,'eid':eid})
    before=(await db.execute(text('select * from gl_accounts order by id'))).all()
    def upgrade(sync):
        with Operations.context(MigrationContext.configure(sync.connection())):
            f2_migration().upgrade()
    with pytest.raises(RuntimeError,match='conflicting merchant account'):
        await db.run_sync(upgrade)
    assert (await db.execute(text('select * from gl_accounts order by id'))).all()==before


@pytest.mark.asyncio
@pytest.mark.parametrize('condition',["status='posted'",'posted_at=clock_timestamp()'])
async def test_f2_each_old_immutability_condition_independently(db,condition):
    from sqlalchemy.exc import DBAPIError
    # Ancillary branch probe; real journal history is tested separately above.
    # No guard on journal_entries or journal_lines is disabled or replaced.
    await db.execute(text('create temporary table f2_old_branch (id integer primary key,status text,posted_at timestamptz)'))
    await db.execute(text("insert into f2_old_branch values (1,'draft',null)"))
    await db.execute(text('update f2_old_branch set '+condition))
    await db.execute(text('create trigger f2_probe before update or delete on f2_old_branch for each row execute function public.finance_prevent_posted_entry_mutation()'))
    before=(await db.execute(text('select * from f2_old_branch'))).all()
    for statement in ('update f2_old_branch set id=id','delete from f2_old_branch'):
        with pytest.raises(DBAPIError,match='immutable'):
            async with db.begin_nested():
                await db.execute(text(statement))
        assert (await db.execute(text('select * from f2_old_branch'))).all()==before


@pytest.mark.asyncio
@pytest.mark.parametrize('caller',['commission','credit_purchase','subscription_payment','stripe_fee','refund','api_cost'])
@pytest.mark.parametrize('first_marketplace',[True,False])
async def test_marketplace_and_shared_finance_cross_order_lock_progress(db,caller,first_marketplace):
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    eid,key=await merchant(db),uuid.uuid4().hex
    engine=FinanceEngine()
    # Resolve and commit the real common period before testing account locks.
    from datetime import datetime,timezone
    now=datetime.now(timezone.utc)
    await engine._get_or_create_period(eid,now.year,now.month,db)
    await db.commit()
    ae=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    async def legacy(session,suffix):
        args = {
            'commission': dict(order_id=uuid.uuid4(),amount_cents=2500,rate_bps=500),
            'credit_purchase': dict(user_id=uuid.uuid4(),amount_cents=73,stripe_pi_id='pi_'+key+suffix),
            'subscription_payment': dict(subscription_id=uuid.uuid4(),amount_cents=73,plan='test',stripe_pi_id='pi_'+key+suffix),
            'stripe_fee': dict(payment_id=uuid.uuid4(),fee_cents=73,stripe_charge_id='ch_'+key+suffix),
            'refund': dict(payment_id=uuid.uuid4(),amount_cents=73,reason='requested_by_customer',stripe_refund_id='re_'+key+suffix),
            'api_cost': dict(provider='test',amount_cents=73,period_id=uuid.uuid4(),idempotency_key=key+suffix),
        }[caller]
        from app.services.finance.engine import AIMARKET_ENTITY_ID
        return await getattr(engine,'record_'+caller)(entity_id=AIMARKET_ENTITY_ID if caller=='api_cost' else eid,db=session,**args)
    async with AsyncSession(ae,expire_on_commit=False) as other,AsyncSession(ae) as observer:
        first_pid=await db.scalar(text('select pg_backend_pid()'))
        other_pid=await other.scalar(text('select pg_backend_pid()'))
        await other.execute(text("set local lock_timeout='3s'"))
        first=await capture(db,eid,key) if first_marketplace else await legacy(db,'first')
        task=asyncio.create_task(legacy(other,'second') if first_marketplace else capture(other,eid,key))
        try:
            if caller == 'api_cost':
                # The real legacy API-cost chart uses 5000/2000 on its own entity;
                # neither account overlaps the strict merchant capture chart.
                # Prove independent progress while the first posting is uncommitted.
                second = await asyncio.wait_for(task,3)
                assert not await observer.scalar(text('select :a=ANY(pg_blocking_pids(:b))'),{'a':first_pid,'b':other_pid})
                await db.commit()
            else:
                async with asyncio.timeout(3):
                    while not await observer.scalar(text('select :a=ANY(pg_blocking_pids(:b))'),{'a':first_pid,'b':other_pid}):
                        await asyncio.sleep(.01)
                assert not task.done()
                await db.commit()
                second=await asyncio.wait_for(task,3)
            await other.commit()
            for session,entry in ((db,first),(other,second)):
                await session.refresh(entry)
                assert entry.status=='posted' and entry.posted_at is not None
        finally:
            if not task.done():task.cancel()
            await asyncio.gather(task,return_exceptions=True)
    await ae.dispose()


# Fixed full-ancestry FK inventory; changes require reviewing implicit lock edges.
F3_FK_EDGES = [('accounting_periods', 'FOREIGN KEY (entity_id) REFERENCES billing_entities(id)'), ('agent_api_keys', 'FOREIGN KEY (org_id) REFERENCES party(id)'), ('api_credits', 'FOREIGN KEY (entity_id) REFERENCES billing_entities(id)'), ('api_credits', 'FOREIGN KEY (last_journal_entry_id) REFERENCES journal_entries(id)'), ('api_credits', 'FOREIGN KEY (last_topup_payment_id) REFERENCES payments(id)'), ('api_credits', 'FOREIGN KEY (user_id) REFERENCES users(id)'), ('gl_accounts', 'FOREIGN KEY (entity_id) REFERENCES billing_entities(id)'), ('gl_accounts', 'FOREIGN KEY (parent_id) REFERENCES gl_accounts(id)'), ('journal_entries', 'FOREIGN KEY (entity_id) REFERENCES billing_entities(id)'), ('journal_entries', 'FOREIGN KEY (period_id) REFERENCES accounting_periods(id)'), ('journal_entries', 'FOREIGN KEY (proposal_id) REFERENCES finance_agent_proposals(id)'), ('journal_entries', 'FOREIGN KEY (reversal_of) REFERENCES journal_entries(id)'), ('journal_lines', 'FOREIGN KEY (account_id) REFERENCES gl_accounts(id)'), ('journal_lines', 'FOREIGN KEY (entry_id) REFERENCES journal_entries(id)'), ('order_events', 'FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE'), ('order_money_states', 'FOREIGN KEY (billing_entity_id) REFERENCES billing_entities(id)'), ('order_money_states', 'FOREIGN KEY (capture_journal_entry_id) REFERENCES journal_entries(id)'), ('order_money_states', 'FOREIGN KEY (capture_payment_id) REFERENCES payments(id)'), ('order_money_states', 'FOREIGN KEY (order_id) REFERENCES orders(id)'), ('order_money_states', 'FOREIGN KEY (payout_journal_entry_id) REFERENCES journal_entries(id)'), ('order_money_states', 'FOREIGN KEY (transaction_id) REFERENCES transactions(id)'), ('orders', 'FOREIGN KEY (buyer_id) REFERENCES users(id)'), ('orders', 'FOREIGN KEY (dispute_resolved_by) REFERENCES users(id)'), ('orders', 'FOREIGN KEY (listing_id) REFERENCES listings(id)'), ('orders', 'FOREIGN KEY (party_id) REFERENCES party(id)'), ('orders', 'FOREIGN KEY (purchased_version_id) REFERENCES listing_versions(id)'), ('orders', 'FOREIGN KEY (revoked_by) REFERENCES users(id)'), ('orders', 'FOREIGN KEY (seller_id) REFERENCES users(id)'), ('orders', 'FOREIGN KEY (transaction_id) REFERENCES transactions(id)'), ('payments', 'FOREIGN KEY (customer_id) REFERENCES users(id)'), ('payments', 'FOREIGN KEY (entity_id) REFERENCES billing_entities(id)'), ('payments', 'FOREIGN KEY (invoice_id) REFERENCES invoices(id)'), ('payments', 'FOREIGN KEY (journal_entry_id) REFERENCES journal_entries(id)'), ('refunds', 'FOREIGN KEY (entity_id) REFERENCES billing_entities(id)'), ('refunds', 'FOREIGN KEY (invoice_id) REFERENCES invoices(id)'), ('refunds', 'FOREIGN KEY (journal_entry_id) REFERENCES journal_entries(id)'), ('refunds', 'FOREIGN KEY (order_id) REFERENCES orders(id)'), ('refunds', 'FOREIGN KEY (payment_id) REFERENCES payments(id)'), ('refunds', 'FOREIGN KEY (transaction_id) REFERENCES transactions(id)'), ('stripe_events', 'FOREIGN KEY (entity_id) REFERENCES billing_entities(id)'), ('stripe_events', 'FOREIGN KEY (refund_order_id) REFERENCES orders(id)'), ('transaction_events', 'FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE'), ('transactions', 'FOREIGN KEY (api_key_id) REFERENCES agent_api_keys(id)'), ('transactions', 'FOREIGN KEY (buyer_id) REFERENCES users(id)'), ('transactions', 'FOREIGN KEY (data_request_id) REFERENCES data_requests(id)'), ('transactions', 'FOREIGN KEY (listing_id) REFERENCES listings(id)'), ('transactions', 'FOREIGN KEY (order_id) REFERENCES orders(id)'), ('transactions', 'FOREIGN KEY (party_id) REFERENCES party(id)'), ('transactions', 'FOREIGN KEY (seller_id) REFERENCES users(id)')]


@pytest.mark.asyncio
async def test_full_participating_fk_and_trigger_lock_inventory(db):
    tables=sorted({child for child,_ in F3_FK_EDGES})
    rows=(await db.execute(text("select conrelid::regclass::text,pg_get_constraintdef(oid) from pg_constraint where contype='f' and conrelid=ANY(cast(:names as regclass[]))"),{'names':tables})).all()
    assert sorted(tuple(row) for row in rows)==F3_FK_EDGES
    triggers=(await db.execute(text("select c.relname,t.tgname,t.tgenabled::text from pg_trigger t join pg_class c on c.oid=t.tgrelid where not t.tgisinternal and c.relname=ANY(:names) order by c.relname,t.tgname"),{'names':tables})).all()
    assert [tuple(row) for row in triggers]==[
        ('journal_entries','trg_balanced_on_post','O'),
        ('journal_entries','trg_closed_period_guard','O'),
        ('journal_entries','trg_immutable_posted_entries','O'),
        ('journal_lines','trg_immutable_posted_lines','O'),
        ('journal_lines','trg_line_entity_consistency','O'),
        ('order_money_states','trg_s1714_money_immutable','O'),
        ('orders','trg_sync_order_to_transaction','O'),
        ('orders','trigger_orders_updated_at','O'),
        ('orders','trigger_set_order_number','O')]


@pytest.fixture(autouse=True)
def _no_real_provider_http(provider_http_guard):
    yield


@pytest.mark.asyncio
async def test_f5_api_cost_actual_supported_entity_chart_disposition(db,record_property):
    """Bounded impossibility evidence; this is explicitly NOT contention proof."""
    from app.services.finance.engine import AIMARKET_ENTITY_ID
    from app.services.finance.templates import JOURNAL_TEMPLATES
    eid=await merchant(db)
    assert eid!=AIMARKET_ENTITY_ID
    before=(await db.execute(text('select entity_id,code,id from gl_accounts order by entity_id,code,id'))).all()
    merchant_codes={row.code for row in before if row.entity_id==eid}
    legacy_codes={row.code for row in before if row.entity_id==AIMARKET_ENTITY_ID}
    api_codes={line['account_code'] for line in JOURNAL_TEMPLATES['api_cost']['lines']}
    assert api_codes=={'5000','2000'} and api_codes<=legacy_codes
    assert '2000' not in merchant_codes
    assert api_codes.isdisjoint(FinanceEngine.MARKETPLACE_CHART)
    key=uuid.uuid4().hex
    async with db.begin_nested():
        with pytest.raises(ValueError,match="GL account codes not found.*2000"):
            await FinanceEngine().record_api_cost(provider='test',amount_cents=73,period_id=uuid.uuid4(),idempotency_key=key,db=db,entity_id=eid)
    assert await db.scalar(text('select count(*) from journal_entries where source_ref=:ref'),{'ref':'api_cost:'+key})==0
    assert (await db.execute(text('select entity_id,code,id from gl_accounts order by entity_id,code,id'))).all()==before
    record_property('api_cost_shared_lock_disposition','UNSATISFIED: actual default legacy entity; merchant missing 2000; account sets disjoint; owner/Council disposition required')


@pytest.mark.parametrize("row_index", [0, 1])
@pytest.mark.parametrize("field_index", range(25))
def test_canonical_pi_extension_rejects_every_catalog_field(row_index, field_index):
    """Exact-field fixture proof; impossible catalog states are not DDL proof."""
    from app.services.refund_processing_service import _assert_canonical_pi_extension, OrderMoneyProtocolUnavailable
    rows = [
        [table, name, True, 'u', True, False, False, True, False, False,
         'character varying(255)', True, True, name, 'public',
         True, True, True, True, 1, 1, True, True, True, False]
        for table, name in [('orders', 'uq_s1714_order_payment_intent'),
                            ('transactions', 'uq_s1714_transaction_payment_intent')]
    ]
    _assert_canonical_pi_extension(rows)
    value = rows[row_index][field_index]
    rows[row_index][field_index] = (not value if type(value) is bool else
                                    value + 1 if type(value) is int else value + '_wrong')
    with pytest.raises(OrderMoneyProtocolUnavailable, match='extension mismatch'):
        _assert_canonical_pi_extension(rows)


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'wrong_table', 'not_null', 'deferred', 'nulls_not_distinct', 'wrong_column', 'missing_ancestry', 'legacy_guard'])
def test_canonical_pi_actual_catalog_refusal(mutation):
    from app.services.refund_processing_service import assert_order_money_protocol_ready_sync, OrderMoneyProtocolUnavailable
    from sqlalchemy.orm import Session
    engine = create_engine(disposable_url(), poolclass=NullPool)
    try:
        with Session(engine) as session:
            assert_order_money_protocol_ready_sync(session)
            if mutation == 'missing_ancestry':
                session.execute(text("UPDATE alembic_version SET version_num='s1712_workspace_authority_v1'"))
            elif mutation == 'legacy_guard':
                session.execute(text('ALTER TABLE order_money_states DISABLE TRIGGER trg_s1714_money_immutable'))
            elif mutation == 'wrong_table':
                session.execute(text('ALTER TABLE orders DROP CONSTRAINT uq_s1714_order_payment_intent'))
                session.execute(text('CREATE TABLE canonical_pi_wrong_table (stripe_payment_intent_id varchar(255), CONSTRAINT uq_s1714_order_payment_intent UNIQUE(stripe_payment_intent_id))'))
            elif mutation == 'not_null':
                # Owned rollback-only catalog fault staging: remove NULL data
                # obstruction without treating these adversarial PIs as money.
                session.execute(text("UPDATE transactions SET stripe_payment_intent_id='pi_catalog_' || id::text WHERE stripe_payment_intent_id IS NULL"))
                session.execute(text('ALTER TABLE transactions ALTER COLUMN stripe_payment_intent_id SET NOT NULL'))
            elif mutation == 'duplicate':
                session.execute(text('ALTER TABLE transactions ADD CONSTRAINT unexpected_s1714_pi UNIQUE(stripe_payment_intent_id)'))
            else:
                session.execute(text('ALTER TABLE transactions DROP CONSTRAINT uq_s1714_transaction_payment_intent'))
                definitions = {'deferred': 'UNIQUE(stripe_payment_intent_id) DEFERRABLE INITIALLY DEFERRED',
                               'nulls_not_distinct': 'UNIQUE NULLS NOT DISTINCT(stripe_payment_intent_id)',
                               'wrong_column': 'UNIQUE(id)'}
                if mutation in definitions:
                    if mutation=='nulls_not_distinct':
                        session.execute(text("UPDATE transactions SET stripe_payment_intent_id='pi_catalog_' || id::text WHERE stripe_payment_intent_id IS NULL"))
                    session.execute(text('ALTER TABLE transactions ADD CONSTRAINT uq_s1714_transaction_payment_intent '+definitions[mutation]))
            with pytest.raises(OrderMoneyProtocolUnavailable):
                assert_order_money_protocol_ready_sync(session)
            session.rollback()
            assert_order_money_protocol_ready_sync(session)
    finally:
        engine.dispose()


def _canonical_pi_migration():
    path=Path('alembic/versions/20260912_003_canonical_payment_intent_binding.py')
    spec=importlib.util.spec_from_file_location('owned_canonical_pi_migration',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('scenario',['repeat','fresh','duplicate_orders','duplicate_transactions','index_collision','wrong_constraint','downgrade'])
def test_canonical_pi_native_migration_census_collision_and_retention(scenario,record_property):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy.orm import Session
    migration=_canonical_pi_migration()
    engine=create_engine(disposable_url(),poolclass=NullPool)
    with engine.connect() as conn:
        outer=conn.begin()
        before=conn.execute(text("SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conname IN ('uq_s1714_order_payment_intent','uq_s1714_transaction_payment_intent') ORDER BY conname")).all()
        with Operations.context(MigrationContext.configure(conn)):
            if scenario=='downgrade':
                with pytest.raises(RuntimeError,match='retained'):migration.downgrade()
            elif scenario in {'repeat','fresh'}:
                if scenario=='fresh':
                    for table,name in migration.OBJECTS:conn.execute(text('ALTER TABLE '+table+' DROP CONSTRAINT '+name))
                migration.upgrade();migration.upgrade()
                assert all(migration.verify(conn,*obj) for obj in migration.OBJECTS)
            else:
                table,name=migration.OBJECTS[0 if scenario!='duplicate_transactions' else 1]
                conn.execute(text('ALTER TABLE '+table+' DROP CONSTRAINT '+name))
                if scenario.startswith('duplicate_'):
                    # Two real existing rows retain their identities; only this
                    # rolled-back pre-cutover catalog allows duplicate staging.
                    from test_refund_processing_protocol import purchase
                    class AsyncBoundary:
                        async def execute(self,*a,**kw):return conn.execute(*a,**kw)
                    pairs=[asyncio.run(purchase(AsyncBoundary())) for _ in range(2)]
                    ids=[pair[0 if table=='orders' else 1] for pair in pairs]
                    original=conn.execute(text('SELECT id,stripe_payment_intent_id FROM '+table+' WHERE id IN (:a,:b) ORDER BY id'),{'a':ids[0],'b':ids[1]}).all()
                    conn.execute(text('UPDATE '+table+" SET stripe_payment_intent_id='pi_owned_pre_cutover_duplicate' WHERE id IN (:a,:b)"),{'a':ids[0],'b':ids[1]})
                    with pytest.raises(RuntimeError,match='duplicate census'):migration.upgrade()
                    assert conn.scalar(text('SELECT count(*) FROM '+table+" WHERE stripe_payment_intent_id='pi_owned_pre_cutover_duplicate'"))==2
                    record_property('duplicate_original_row_ids',','.join(str(row[0]) for row in original))
                else:
                    if scenario=='index_collision':conn.execute(text('CREATE INDEX '+name+' ON '+table+'(id)'))
                    else:conn.execute(text('ALTER TABLE '+table+' ADD CONSTRAINT '+name+' UNIQUE(id)'))
                    with pytest.raises(RuntimeError,match='collision'):migration.upgrade()
        outer.rollback()
        assert conn.execute(text("SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conname IN ('uq_s1714_order_payment_intent','uq_s1714_transaction_payment_intent') ORDER BY conname")).all()==before
    engine.dispose()


@pytest.mark.parametrize('budget',['statement','whole_body'])
def test_canonical_payment_actual_statement_and_decreasing_body_deadlines(budget,record_property):
    import time
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import DBAPIError
    from app.services.order_money_service import payment_database_deadline,OrderMoneyConflict
    engine=create_engine(disposable_url(),poolclass=NullPool)
    start=time.monotonic();completed=0
    try:
        with Session(engine) as session:
            with pytest.raises((DBAPIError,OrderMoneyConflict)):
                with payment_database_deadline(session):
                    if budget=='statement':session.execute(text('SELECT pg_sleep(3)'))
                    else:
                        for _ in range(4):
                            session.execute(text('SELECT pg_sleep(1.4)'));completed+=1
                    session.commit()
            session.rollback()
            assert session.scalar(text('SELECT 1'))==1
        elapsed=time.monotonic()-start
        assert (1.8<=elapsed<3 if budget=='statement' else 4.7<=elapsed<5.8)
        if budget=='whole_body':assert completed==3
        record_property('measured_database_deadline_seconds',elapsed)
        record_property('completed_statements_before_refusal',completed)
    finally:engine.dispose()


@pytest.mark.parametrize('value_kind',['expected_binding','provider_evidence'])
def test_canonical_closed_immutable_values_reject_every_missing_extra_and_wrong_type(value_kind,record_property):
    from dataclasses import asdict,FrozenInstanceError
    from app.services.order_money_service import ExpectedPaymentBinding,AgentProviderEvidence,OrderMoneyConflict
    ids=[uuid.uuid4() for _ in range(5)]
    if value_kind=='expected_binding':
        cls=ExpectedPaymentBinding
        values=dict(order_id=ids[0],transaction_id=ids[1],stored_checkout_session_id='cs_original',signed_checkout_session_id='cs_original',
            signed_payment_intent_id='pi_original',signed_amount_cents=2500,signed_currency='USD',buyer_id=ids[2],seller_id=ids[3],listing_id=ids[4],platform_fee_cents=125,seller_amount_cents=2375)
        bad={k:(str(v) if type(v) is uuid.UUID else True if type(v) is int else '') for k,v in values.items()}
        assert len(values)==12
    else:
        cls=AgentProviderEvidence
        values=dict(source='signed_event_and_provider_read',payment_intent_id='pi_original',provider_status='succeeded',amount_cents=2500,currency='usd',
            customer_id='cus_original',payment_method_id='pm_original',provider_account_id=None,livemode=False,
            metadata=(('transaction_id',str(ids[1])),('order_id',str(ids[0])),('api_key_id',str(ids[2])),('buyer_type','agent')),
            observed_at='2026-09-12T00:00:00.000000Z',signed_event_id='evt_original',amount_received_cents=2500,amount_capturable_cents=0)
        bad={k:(True if type(v) is int else 1 if type(v) is bool else [] if v is None else {} if type(v) is tuple else '') for k,v in values.items()}
        assert len(values)==14
    original=cls(**values)
    checked=[]
    for field in values:
        missing=values.copy();missing.pop(field)
        with pytest.raises(TypeError):cls(**missing)
        with pytest.raises(OrderMoneyConflict):cls(**{**values,field:bad[field]})
        with pytest.raises((FrozenInstanceError,AttributeError)):setattr(original,field,bad[field])
        checked.append(field)
    with pytest.raises(TypeError):cls(**values,unapproved_extra=True)
    record_property('exact_fields_exercised',','.join(checked))


# Live catalog corruption is confined to this owned database transaction.
CATALOG_FAULTS=[
 ('constraint','convalidated=false'),('constraint','condeferrable=true'),('constraint','condeferred=true'),
 ('constraint',"contype='c'"),('constraint',"conkey=ARRAY[1]::smallint[]"),
 ('constraint',"conrelid='public.orders'::regclass"),('constraint',"conindid=(SELECT indexrelid FROM pg_index WHERE indrelid='public.orders'::regclass LIMIT 1)"),
 ('index','indisunique=false'),('index','indisvalid=false'),('index','indisready=false'),('index','indimmediate=false'),
 ('index','indnatts=2'),('index','indnkeyatts=2'),('index',"indkey='1'::int2vector"),('index','indnullsnotdistinct=true'),
 ('index',"indrelid='public.orders'::regclass"),
 ('index',"indpred=(SELECT indpred FROM pg_index WHERE indpred IS NOT NULL LIMIT 1)"),
 ('index',"indexprs=(SELECT indexprs FROM pg_index WHERE indexprs IS NOT NULL LIMIT 1)"),
 ('attribute','attisdropped=true'),('attribute','atttypmod=258'),
 ('class',"relname='owned_wrong_pi_index'"),('class',"relnamespace='pg_catalog'::regnamespace"),
]
@pytest.mark.parametrize('target,change',CATALOG_FAULTS)
def test_live_catalog_field_fault(target,change,record_property):
 from app.services.refund_processing_service import assert_order_money_protocol_ready_sync,OrderMoneyProtocolUnavailable,CANONICAL_PI_CATALOG_SQL
 from sqlalchemy.orm import Session
 engine=create_engine(disposable_url())
 try:
  with Session(engine) as db:
   assert_order_money_protocol_ready_sync(db)
   before=[list(row) for row in db.execute(text(CANONICAL_PI_CATALOG_SQL))]
   table,predicate={
    'constraint':('pg_constraint',"conname='uq_s1714_transaction_payment_intent' AND conrelid='public.transactions'::regclass"),
    'index':('pg_index',"indexrelid='public.uq_s1714_transaction_payment_intent'::regclass"),
    'attribute':('pg_attribute',"attrelid='public.transactions'::regclass AND attname='stripe_payment_intent_id'"),
    'class':('pg_class',"oid='public.uq_s1714_transaction_payment_intent'::regclass"),
   }[target]
   changed=db.execute(text('UPDATE pg_catalog.'+table+' SET '+change+' WHERE '+predicate))
   assert changed.rowcount==1
   after=[list(row) for row in db.execute(text(CANONICAL_PI_CATALOG_SQL))]
   assert before!=after
   with pytest.raises(OrderMoneyProtocolUnavailable):assert_order_money_protocol_ready_sync(db)
   db.rollback()
   assert_order_money_protocol_ready_sync(db)
   assert [list(row) for row in db.execute(text(CANONICAL_PI_CATALOG_SQL))]==before
   record_property('catalog_fault',target+': '+change)
 finally:engine.dispose()
