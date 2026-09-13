"""Real migrated PostgreSQL capture/refund services; no mocked SQL or triggers."""
import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from test_order_money_protocol import db, migrated_protocol, merchant, balances
from app.models.order import Order
from app.models.transaction import Transaction
from app.models.finance import Payment, Refund, JournalEntry
from app.models.order_money_state import OrderMoneyState
from app.services.order_money_service import lock_order_money, OrderMoneyConflict
from app.services.refund_processing_service import (
    ensure_order_capture, admit_order_refund, apply_order_refund_effects,
    assert_order_money_protocol_ready, OrderMoneyProtocolUnavailable,
)


async def purchase(db, status='confirmed', *, synthetic=False):
    key = uuid.uuid4().hex
    buyer,seller,listing,oid,tid = [uuid.uuid4() for _ in range(5)]
    for uid,role in [(buyer,'buyer'),(seller,'seller')]:
        await db.execute(text("insert into users (id,email,is_test,status) values (:id,:email,:synthetic,'active')"),
            {'id':uid,'email':f'{role}-{key}@'+('e2e-test.ai.market' if synthetic else 'example.invalid'),'synthetic':synthetic})
    await db.execute(text('''insert into listings (id,seller_id,slug,title,description,price,category,schema_info)
        values (:id,:seller,:slug,'S1714 disposable','Service test',25,'other','{}')'''),
        {'id':listing,'seller':seller,'slug':key})
    await db.execute(text('''insert into orders (id,order_number,buyer_id,seller_id,listing_id,listing_snapshot,
        amount_cents,platform_fee_cents,seller_amount_cents,currency,stripe_payment_intent_id,status)
        values (:id,:number,:buyer,:seller,:listing,'{}',2500,125,2375,'USD',:pi,'completed')'''),
        {'id':oid,'number':'O'+key[:18],'buyer':buyer,'seller':seller,'listing':listing,'pi':'pi_'+key})
    await db.execute(text('''insert into transactions (id,tx_number,origin,surface,buyer_type,buyer_id,seller_id,
        listing_id,order_id,amount_cents,platform_fee_cents,seller_amount_cents,currency,stripe_payment_intent_id,status)
        values (:id,:number,'listing_purchase','browser','human',:buyer,:seller,:listing,:oid,2500,125,2375,'USD',:pi,:status)'''),
        {'id':tid,'number':'TX-'+str(int(key[:7],16)),'buyer':buyer,'seller':seller,'listing':listing,'oid':oid,'pi':'pi_'+key,'status':status})
    await db.execute(text('update orders set transaction_id=:tid where id=:oid'), {'tid':tid,'oid':oid})
    pi = {'id':'pi_'+key,'latest_charge':'ch_'+key,'amount':2500,'amount_received':2500,
          'status':'succeeded','livemode':False,'currency':'usd','customer':'cus_'+key,
          'metadata':{'order_id':str(oid),'transaction_id':str(tid)}}
    charge = {'id':'ch_'+key,'payment_intent':pi['id'],'amount':2500,'amount_captured':2500,
        'amount_refunded':0,'paid':True,'captured':True,'livemode':False,'currency':'usd',
        'customer':pi['customer'],'created':int(datetime.now(timezone.utc).timestamp()),'metadata':{}}
    return oid,tid,pi,charge


async def signed_event(db, charge):
    event={'id':'evt_'+uuid.uuid4().hex,'type':'charge.refunded','livemode':False,'data':{'object':dict(charge)}}
    await db.execute(text('''insert into stripe_events (stripe_event_id,event_type,payload_json,signature_valid)
        values (:id,'charge.refunded',cast(:payload as jsonb),true)'''),{'id':event['id'],'payload':json.dumps(event)})
    return event


def refund(charge, amount, suffix):
    return {'id':'re_'+suffix,'amount':amount,'currency':'usd','status':'succeeded',
            'charge':charge['id'],'payment_intent':charge['payment_intent'],'livemode':False}


async def process(db, event, pi, ch, refunds):
    await admit_order_refund(db,event)
    result = await apply_order_refund_effects(db,event=event,provider_payment=pi,provider_charge=ch,provider_refunds=refunds)
    await db.commit()
    return result


@pytest.mark.asyncio
async def test_refund_before_capture_partial_full_and_late_payment(db):
    oid,tid,pi,ch=await purchase(db,'checkout_pending')
    ch['amount_refunded']=333
    first=refund(ch,333,uuid.uuid4().hex)
    event=await signed_event(db,ch)
    assert (await process(db,event,pi,ch,[first]))['refund_total_cents']==333
    order=await db.get(Order,oid)
    tx=await db.get(Transaction,tid)
    assert order.status=='partially_refunded' and not order.revoked
    assert tx.status=='checkout_pending'
    assert await db.scalar(text("select count(*) from transaction_events where transaction_id=:tid and to_status='refunded'"),{'tid':tid})==0
    ch['amount_refunded']=2500
    second=refund(ch,2167,uuid.uuid4().hex)
    event2=await signed_event(db,ch)
    await process(db,event2,pi,ch,[first,second])
    await db.refresh(order)
    await db.refresh(tx)
    assert order.status=='refunded' and order.revoked and order.refund_amount_cents==2500
    assert tx.status=='refunded'
    events=(await db.execute(text("select from_status,payload from transaction_events where transaction_id=:tid and to_status='refunded'"),{'tid':tid})).all()
    assert len(events)==1 and events[0].from_status=='checkout_pending'
    assert events[0].payload['stripe_refund_id']==second['id']
    state=await db.get(OrderMoneyState,oid)
    assert state.capture_origin=='refund_reconciliation'
    order_money=await lock_order_money(db,oid)
    payment=await ensure_order_capture(db,order=order,transaction=tx,provider_payment=pi,provider_charge=ch,origin='payment_event',locked=order_money)
    assert payment.status=='refunded'
    await db.commit()
    await process(db,event2,pi,ch,[first,second])
    assert await db.scalar(text("select count(*) from transaction_events where transaction_id=:tid and to_status='refunded'"),{'tid':tid})==1
    refunds=(await db.execute(select(Refund).where(Refund.order_id==oid))).scalars().all()
    assert len(refunds)==2 and sum(r.marketplace_fee_refund_cents for r in refunds)==125
    assert all(r.effects_applied_at and r.journal_entry_id for r in refunds)
    refs=['marketplace_payment:'+pi['id'],'refund:'+first['id'],'refund:'+second['id']]
    assert await balances(db,state.billing_entity_id,refs)=={'1000':0,'2110':0,'4000':0,'5100':0}


@pytest.mark.asyncio
@pytest.mark.parametrize('status',['delivered','confirmed','settled'])
async def test_full_refund_trigger_uses_actual_prior_state_including_local_refunded(db,status):
    oid,tid,pi,ch=await purchase(db,status)
    # A prior unresolved local dispute is not validated finance proof.
    await db.execute(text("update orders set status='refunded' where id=:oid"),{'oid':oid})
    ch['amount_refunded']=2500
    event=await signed_event(db,ch)
    r=refund(ch,2500,uuid.uuid4().hex)
    await process(db,event,pi,ch,[r])
    rows=(await db.execute(text("select from_status,to_status,payload from transaction_events where transaction_id=:tid and to_status='refunded'"),{'tid':tid})).all()
    assert len(rows)==1 and rows[0].from_status==status and rows[0].payload['stripe_refund_id']==r['id']


@pytest.mark.asyncio
async def test_durable_admission_survives_failed_effects_and_retry(db):
    oid,tid,pi,ch=await purchase(db)
    ch['amount_refunded']=2500
    event=await signed_event(db,ch)
    r=refund(ch,2500,uuid.uuid4().hex)
    await admit_order_refund(db,event)
    assert await db.scalar(text('select status from stripe_events where stripe_event_id=:id'),{'id':event['id']})=='failed'
    with pytest.raises(OrderMoneyConflict,match='gross mismatch'):
        await apply_order_refund_effects(db,event=event,provider_payment={**pi,'amount_received':2499},provider_charge=ch,provider_refunds=[r])
    await db.rollback()
    assert await db.scalar(text('select refund_phase from stripe_events where stripe_event_id=:id'),{'id':event['id']})=='admitted'
    assert await db.scalar(text('select count(*) from refunds where order_id=:id'),{'id':oid})==0
    await process(db,event,pi,ch,[r])
    assert await db.scalar(text('select refund_phase from stripe_events where stripe_event_id=:id'),{'id':event['id']})=='applied'


@pytest.mark.asyncio
async def test_immutable_entity_rejects_clear_and_reassignment(db):
    oid,tid,pi,ch=await purchase(db)
    money=await lock_order_money(db,oid)
    await ensure_order_capture(db,order=money.order,transaction=money.transaction,provider_payment=pi,provider_charge=ch,origin='payment_event',locked=money)
    await db.commit()
    for other in (None,uuid.UUID('00000000-0000-0000-0000-000000000001')):
        with pytest.raises(DBAPIError,match='immutable order money billing entity'):
            await db.execute(text('update order_money_states set billing_entity_id=:eid where order_id=:oid'),{'eid':other,'oid':oid})
        await db.rollback()
    assert (await db.get(OrderMoneyState,oid)).billing_entity_id==await merchant(db)


@pytest.mark.asyncio
async def test_readiness_detects_disabled_guard(db):
    await assert_order_money_protocol_ready(db)
    await db.execute(text('alter table order_money_states disable trigger trg_s1714_money_immutable'))
    with pytest.raises(OrderMoneyProtocolUnavailable,match='schema/guard'):
        await assert_order_money_protocol_ready(db)
    await db.rollback()
    await assert_order_money_protocol_ready(db)


@pytest.mark.asyncio
async def test_admission_is_durable_and_blocks_every_money_guard_before_hold(db):
    from app.services.order_money_service import order_payout_eligibility
    oid,tid,pi,ch=await purchase(db)
    await db.execute(text('update orders set revoked=true where id=:oid'),{'oid':oid})
    event=await signed_event(db,ch)
    await admit_order_refund(db,event)
    await db.rollback()
    money=await lock_order_money(db,oid)
    result=await order_payout_eligibility(db,money,destination=None)
    assert result['eligible'] is False
    assert {'dispatch_disabled','revoked','refund_admitted','captured_payment_unavailable','connect_destination_unavailable'} <= set(result['reasons'])
    assert result['reasons'][-1]=='confirmation_event_missing'
    assert await db.scalar(text('select refund_phase from stripe_events where stripe_event_id=:id'),{'id':event['id']})=='admitted'


@pytest.mark.asyncio
async def test_common_order_lock_serializes_independent_connections(db):
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from test_order_money_protocol import disposable_url
    oid,tid,pi,ch=await purchase(db)
    await db.commit()
    engine=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    async with AsyncSession(engine,expire_on_commit=False) as contender:
        first_pid=await db.scalar(text('select pg_backend_pid()'))
        second_pid=await contender.scalar(text('select pg_backend_pid()'))
        await contender.execute(text("set local lock_timeout='5s'"))
        await lock_order_money(db,oid)
        waiting=asyncio.create_task(lock_order_money(contender,oid))
        try:
            async with asyncio.timeout(3):
                while True:
                    blocked=await db.scalar(text('select :first=ANY(pg_blocking_pids(:second))'),{'first':first_pid,'second':second_pid})
                    if blocked:
                        break
                    await asyncio.sleep(.01)
            assert not waiting.done()
            await db.commit()
            money=await asyncio.wait_for(waiting,3)
            assert money.order.id==oid and money.transaction.id==tid
        finally:
            if not waiting.done():
                waiting.cancel()
                await asyncio.gather(waiting,return_exceptions=True)
            await contender.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_initial_entity_binding_then_immutable_reassignment(db):
    oid,tid,pi,ch=await purchase(db)
    money=await lock_order_money(db,oid)
    assert money.state.billing_entity_id is None
    money.state.billing_entity_id=await merchant(db)
    await db.flush()
    await db.commit()
    for eid in (None,uuid.UUID('00000000-0000-0000-0000-000000000001')):
        with pytest.raises(DBAPIError,match='immutable order money billing entity'):
            await db.execute(text('update order_money_states set billing_entity_id=:eid where order_id=:oid'),{'eid':eid,'oid':oid})
        await db.rollback()
    await assert_order_money_protocol_ready(db)


@pytest.mark.asyncio
async def test_missing_reverse_link_refuses_admission(db):
    oid,tid,pi,ch=await purchase(db)
    await db.execute(text('update orders set transaction_id=null where id=:oid'),{'oid':oid})
    event=await signed_event(db,ch)
    with pytest.raises(OrderMoneyConflict,match='reverse link'):
        await admit_order_refund(db,event)


@pytest.mark.asyncio
async def test_canonical_capture_route_without_customer_metadata(db,monkeypatch):
    from app.services.billing_service import BillingService
    from app.core import stripe_async
    oid,tid,pi,ch=await purchase(db)
    await db.commit()
    async def provider(fn,*args,**kwargs):
        return ch if args[0]==ch['id'] else pi
    monkeypatch.setattr(stripe_async,'run_stripe',provider)
    event={'id':'evt_'+uuid.uuid4().hex,'object':'event','type':'payment_intent.succeeded','livemode':False,'data':{'object':pi}}
    result=await BillingService().handle_stripe_event(event,db)
    await db.commit()
    assert result['processed_status']=='processed'
    assert await db.scalar(text('select count(*) from payments where stripe_payment_intent_id=:pi'),{'pi':pi['id']})==1


@pytest.mark.asyncio
async def test_disabled_existing_settlement_writer_never_calls_provider(db,monkeypatch):
    from app.services.settlement_service import SettlementService
    from app.core import stripe_async
    oid,tid,pi,ch=await purchase(db)
    async def forbidden(*args,**kwargs):
        pytest.fail('Disabled payout called provider')
    monkeypatch.setattr(stripe_async,'run_stripe',forbidden)
    result=await SettlementService(db).settle(tid)
    assert result['status']=='blocked' and 'dispatch_disabled' in result['reasons']
    assert await db.scalar(text("select count(*) from order_events where order_id=:id and metadata ? 'money_audit_sha256'"),{'id':oid})==1
    await SettlementService(db).settle(tid)
    assert await db.scalar(text("select count(*) from order_events where order_id=:id and metadata ? 'money_audit_sha256'"),{'id':oid})==1


@pytest.mark.asyncio
async def test_recovery_zero_matches_has_no_ttl_or_create(db,monkeypatch):
    from app.services.order_money_service import recover_order_payout,payout_request,canonical_digest
    from app.core import stripe_async
    oid,tid,pi,ch=await purchase(db)
    money=await lock_order_money(db,oid)
    state=money.state
    state.billing_entity_id=await merchant(db)
    state.request_json=payout_request(money,'acct_s1714')
    state.request_sha256=canonical_digest(state.request_json)
    state.idempotency_key=state.request_json['idempotency_key']
    state.transfer_group=state.request_json['transfer_group']
    state.dispatch_token=uuid.uuid4()
    state.payout_state='unknown'
    await db.commit()
    calls=[]
    async def provider(fn,*args,**kwargs):
        calls.append(fn.__name__)
        assert fn.__name__=='list'
        return {'data':[],'has_more':False}
    monkeypatch.setattr(stripe_async,'run_stripe',provider)
    for _ in range(2):
        assert (await recover_order_payout(db,oid))['status']=='unknown'
    assert calls==['list','list']


@pytest.mark.asyncio
async def test_revoke_and_confirmation_share_authority(db):
    from app.services.order_service import OrderService
    from app.services.transaction_service import TransactionService
    from fastapi import HTTPException
    oid,tid,pi,ch=await purchase(db,'delivered')
    await OrderService(db).revoke_access(oid,None,'S1714 service proof')
    with pytest.raises(HTTPException,match='restriction'):
        await TransactionService(db).confirm(tid,'buyer')
    await db.rollback()
    assert (await db.get(Order,oid)).revoked
    assert (await db.get(Transaction,tid)).status=='delivered'


@pytest.mark.asyncio
async def test_latest_confirmation_event_uses_pg_clock_not_updated_at(db,monkeypatch):
    from app.services.order_money_service import order_payout_eligibility
    oid,tid,pi,ch=await purchase(db)
    if tid:
        await db.execute(text("insert into transaction_events (id,transaction_id,event_type,actor_type,to_status,created_at) values (gen_random_uuid(),:tid,'status_changed','system','confirmed',clock_timestamp()-interval '49 hours')"),{'tid':tid})
    money=await lock_order_money(db,oid)
    first=await order_payout_eligibility(db,money,destination='acct_test')
    assert 'confirmation_hold' not in first['reasons']
    recent=uuid.uuid4()
    await db.execute(text("insert into transaction_events (id,transaction_id,event_type,actor_type,to_status,created_at) values (:id,:tid,'status_changed','system','confirmed',clock_timestamp()-interval '1 hour')"),{'tid':tid,'id':recent})
    await db.execute(text("update transactions set updated_at=clock_timestamp()-interval '90 hours' where id=:tid"),{'tid':tid})
    second=await order_payout_eligibility(db,money,destination='acct_test')
    assert second['confirmation_event_id']==str(recent)
    assert second['reasons'][-1]=='confirmation_hold'


@pytest.mark.asyncio
@pytest.mark.parametrize('node',['orders','transactions','order_money_states','payments','refunds','agent_api_keys'])
async def test_actual_common_lock_chain_waits_at_each_owned_node(db,node):
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from test_order_money_protocol import disposable_url
    oid,tid,pi,ch=await purchase(db)
    party,key=uuid.uuid4(),uuid.uuid4()
    await db.execute(text("insert into party (id,party_type) values (:id,'organization')"),{'id':party})
    await db.execute(text("insert into agent_api_keys (id,org_id,name,key_hash,prefix,spend_used) values (:id,:org,'lock test',:hash,'s1714',2500)"),{'id':key,'org':party,'hash':uuid.uuid4().hex*2})
    await db.execute(text("update transactions set party_id=:party,api_key_id=:key where id=:id"),{'party':party,'key':key,'id':tid})
    money=await lock_order_money(db,oid)
    payment=await ensure_order_capture(db,order=money.order,transaction=money.transaction,
        provider_payment=pi,provider_charge=ch,origin='payment_event',locked=money,_prepare_only=True)
    r=Refund(entity_id=payment.entity_id,payment_id=payment.id,order_id=oid,transaction_id=tid,
        stripe_refund_id='re_'+uuid.uuid4().hex,amount_cents=2500,currency='USD',reason='requested_by_customer',status='pending',requested_by='system')
    db.add(r)
    await db.flush()
    ids={'orders':oid,'transactions':tid,'order_money_states':oid,'payments':payment.id,'refunds':r.id,'agent_api_keys':key}
    await db.commit()
    ae=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    async with AsyncSession(ae,expire_on_commit=False) as owner,AsyncSession(ae,expire_on_commit=False) as observer:
        first=await owner.scalar(text('select pg_backend_pid()'))
        second=await db.scalar(text('select pg_backend_pid()'))
        column='order_id' if node=='order_money_states' else 'id'
        await owner.execute(text(f'select {column} from {node} where {column}=:id for update'),{'id':ids[node]})
        task=asyncio.create_task(lock_order_money(db,oid))
        try:
            async with asyncio.timeout(3):
                while not await observer.scalar(text('select :a=ANY(pg_blocking_pids(:b))'),{'a':first,'b':second}):
                    await asyncio.sleep(.01)
            assert not task.done()
            chain=list(ids)
            if chain.index(node)+1 < len(chain):
                later=chain[chain.index(node)+1]
                later_column='order_id' if later=='order_money_states' else 'id'
                await observer.execute(text(f'select {later_column} from {later} where {later_column}=:id for update nowait'),{'id':ids[later]})
                await observer.rollback()
            await owner.rollback()
            result=await asyncio.wait_for(task,3)
            assert result.order.id==oid and result.payment.id==payment.id
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task,return_exceptions=True)
            await db.rollback()
    await ae.dispose()


@pytest.mark.asyncio
async def test_event_admission_waits_for_own_event_before_order(db):
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from test_order_money_protocol import disposable_url
    oid,tid,pi,ch=await purchase(db)
    event=await signed_event(db,ch)
    await db.commit()
    ae=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    async with AsyncSession(ae) as blocker,AsyncSession(ae) as observer:
        first=await blocker.scalar(text('select pg_backend_pid()'))
        second=await db.scalar(text('select pg_backend_pid()'))
        await blocker.execute(text('select stripe_event_id from stripe_events where stripe_event_id=:id for update'),{'id':event['id']})
        task=asyncio.create_task(admit_order_refund(db,event))
        try:
            async with asyncio.timeout(3):
                while not await observer.scalar(text('select :a=ANY(pg_blocking_pids(:b))'),{'a':first,'b':second}):
                    await asyncio.sleep(.01)
            # Admission blocked at event must not own the order yet.
            await observer.execute(text('select id from orders where id=:id for update nowait'),{'id':oid})
            await observer.rollback()
            await blocker.rollback()
            assert (await asyncio.wait_for(task,3))['phase']=='admitted'
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task,return_exceptions=True)
    await ae.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize('case',['multiple','reversed','wrong_amount','wrong_metadata','pagination_duplicate'])
async def test_recovery_reconciles_contradictions_never_creates(db,monkeypatch,case):
    from app.services.order_money_service import recover_order_payout,payout_request,canonical_digest
    from app.core import stripe_async
    oid,tid,pi,ch=await purchase(db)
    money=await lock_order_money(db,oid)
    state=money.state
    state.billing_entity_id=await merchant(db)
    request=payout_request(money,'acct_s1714')
    state.request_json=request
    state.request_sha256=canonical_digest(request)
    state.idempotency_key=request['idempotency_key']
    state.transfer_group=request['transfer_group']
    state.dispatch_token=uuid.uuid4()
    state.payout_state='unknown'
    await db.commit()
    transfer={k:v for k,v in request.items() if k!='idempotency_key'}
    transfer.update(id='tr_'+uuid.uuid4().hex,reversed=False,amount_reversed=0,livemode=False)
    if case=='reversed':transfer['reversed']=True
    elif case=='wrong_amount':transfer['amount']=1
    elif case=='wrong_metadata':transfer['metadata']={'order_id':str(uuid.uuid4())}
    calls=[]
    async def provider(fn,*args,**kwargs):
        assert fn.__name__=='list'
        calls.append(kwargs)
        rows=[transfer]
        if case=='multiple':rows.append({**transfer,'id':'tr_'+uuid.uuid4().hex})
        return {'data':rows,'has_more':case=='pagination_duplicate'}
    monkeypatch.setattr(stripe_async,'run_stripe',provider)
    if case=='pagination_duplicate':
        with pytest.raises(OrderMoneyConflict,match='Repeated'):
            await recover_order_payout(db,oid)
        assert len(calls)==2
    else:
        assert (await recover_order_payout(db,oid))['status']=='reconciliation_required'
        assert len(calls)==1


@pytest.mark.asyncio
async def test_frozen_request_cannot_change_after_dispatch(db):
    from app.services.order_money_service import payout_request,canonical_digest
    oid,tid,pi,ch=await purchase(db)
    money=await lock_order_money(db,oid)
    state=money.state
    state.billing_entity_id=await merchant(db)
    request=payout_request(money,'acct_s1714')
    state.request_json=request
    state.request_sha256=canonical_digest(request)
    state.idempotency_key=request['idempotency_key']
    state.transfer_group=request['transfer_group']
    state.dispatch_token=uuid.uuid4()
    state.payout_state='dispatching'
    await db.commit()
    with pytest.raises(DBAPIError,match='immutable dispatched'):
        await db.execute(text("update order_money_states set request_json=jsonb_set(request_json,'{amount}','1') where order_id=:id"),{'id':oid})
    await db.rollback()
    assert await db.scalar(text('select request_sha256 from order_money_states where order_id=:id'),{'id':oid})==canonical_digest(request)


async def funded_purchase(db,monkeypatch,legacy=False, *, synthetic=False):
    from app.core.config import settings
    monkeypatch.setattr(settings,'ORDER_PAYOUT_DISPATCH_ENABLED',True)
    oid,tid,pi,ch=await purchase(db,synthetic=synthetic)
    if legacy:
        await db.execute(text('update orders set transaction_id=null where id=:id'),{'id':oid})
        await db.execute(text('delete from transactions where id=:id'),{'id':tid})
        pi['metadata'].pop('transaction_id')
        tid=None
    seller=await db.scalar(text('select seller_id from orders where id=:id'),{'id':oid})
    party=uuid.uuid4()
    await db.execute(text("insert into party (id,party_type) values (:id,'person')"),{'id':party})
    for provider,external in [('auth_user',str(seller)),('stripe_connect','acct_'+uuid.uuid4().hex)]:
        await db.execute(text('insert into party_identity (party_id,provider,external_id) values (:party,:provider,:external)'),{'party':party,'provider':provider,'external':external})
    if tid:
        await db.execute(text("insert into transaction_events (id,transaction_id,event_type,actor_type,to_status,created_at) values (gen_random_uuid(),:tid,'status_changed','system','confirmed',clock_timestamp()-interval '49 hours')"),{'tid':tid})
    money=await lock_order_money(db,oid)
    await ensure_order_capture(db,order=money.order,transaction=money.transaction,provider_payment=pi,provider_charge=ch,origin='payment_event',locked=money)
    await db.commit()
    return oid,tid,pi,ch


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['success','unknown_success','refund_after_ownership'])
async def test_actual_dispatch_crash_recovery_and_late_refund(db,monkeypatch,mode):
    import stripe
    from app.core import stripe_async
    from app.services.order_money_service import dispatch_order_payout,recover_order_payout
    oid,tid,pi,ch=await funded_purchase(db,monkeypatch)
    transfers=[]
    async def provider(fn,*args,**kwargs):
        if fn==stripe.Transfer.create:
            tr={k:v for k,v in kwargs.items() if k!='idempotency_key'}
            tr.update(id='tr_'+uuid.uuid4().hex,reversed=False,amount_reversed=0,livemode=False)
            transfers.append(tr)
            if mode!='success':
                raise TimeoutError('Provider accepted; response lost')
            return tr
        if fn==stripe.Transfer.list:return {'data':transfers,'has_more':False}
        if fn==stripe.Transfer.retrieve:return next(t for t in transfers if t['id']==args[0])
        if fn==stripe.Refund.list:
            return {'data':[refund(ch,2500,'late'+ch['id'][3:])] if ch['amount_refunded'] else [],'has_more':False}
        return pi if args[0]==pi['id'] else ch
    monkeypatch.setattr(stripe_async,'run_stripe',provider)
    if mode=='success':
        assert (await dispatch_order_payout(db,oid))['status']=='succeeded'
    else:
        with pytest.raises(TimeoutError):await dispatch_order_payout(db,oid)
        await db.rollback()
        assert (await dispatch_order_payout(db,oid))['status']=='blocked'
        if mode=='refund_after_ownership':
            ch['amount_refunded']=2500
            event=await signed_event(db,ch)
            await process(db,event,pi,ch,[refund(ch,2500,'late'+ch['id'][3:])])
        result=await recover_order_payout(db,oid)
        assert result['status']==('reconciliation_required' if mode=='refund_after_ownership' else 'succeeded')
    replay=await recover_order_payout(db,oid)
    assert replay['status']==('reconciliation_required' if mode=='refund_after_ownership' else 'succeeded')
    assert len(transfers)==1
    assert await db.scalar(text('select count(*) from journal_entries where source_ref=:ref'),{'ref':'marketplace_transfer:'+transfers[0]['id']})==1


@pytest.mark.asyncio
async def test_refund_admission_wins_at_reserved_provider_barrier(db,monkeypatch):
    import asyncio,stripe
    from app.core import stripe_async
    from app.services.order_money_service import dispatch_order_payout
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from test_order_money_protocol import disposable_url
    oid,tid,pi,ch=await funded_purchase(db,monkeypatch)
    reached,release=asyncio.Event(),asyncio.Event()
    async def provider(fn,*args,**kwargs):
        assert fn!=stripe.Transfer.create
        if fn==stripe.PaymentIntent.retrieve:
            reached.set()
            await release.wait()
            return pi
        if fn==stripe.Refund.list:return {'data':[],'has_more':False}
        return ch
    monkeypatch.setattr(stripe_async,'run_stripe',provider)
    ae=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    task=asyncio.create_task(dispatch_order_payout(db,oid))
    try:
        await asyncio.wait_for(reached.wait(),3)
        async with AsyncSession(ae,expire_on_commit=False) as contender:
            event=await signed_event(contender,ch)
            await admit_order_refund(contender,event)
        release.set()
        result=await asyncio.wait_for(task,3)
        assert result['status']=='blocked' and 'refund_admitted' in result['reasons']
    finally:
        release.set()
        if not task.done():
            task.cancel()
            await asyncio.gather(task,return_exceptions=True)
        await ae.dispose()


@pytest.mark.asyncio
async def test_finance_only_refund_complete_provider_set_no_order_authority(db,monkeypatch):
    from app.services.refund_processing_service import process_order_refund
    from app.core import stripe_async
    oid,tid,pi,ch=await purchase(db)
    buyer=await db.scalar(text('select buyer_id from orders where id=:id'),{'id':oid})
    pi['id']='pi_'+uuid.uuid4().hex
    pi['metadata']={}
    ch['payment_intent']=pi['id']
    ch['amount_refunded']=2500
    payment=Payment(entity_id=await merchant(db),customer_id=buyer,stripe_payment_intent_id=pi['id'],
        stripe_charge_id=ch['id'],stripe_customer_id=pi['customer'],amount_cents=2500,currency='USD',status='succeeded',payment_type='credits',received_at=datetime.fromtimestamp(ch['created'],timezone.utc))
    db.add(payment)
    await db.flush()
    event=await signed_event(db,ch)
    r=refund(ch,2500,uuid.uuid4().hex)
    async def provider(fn,*args,**kwargs):
        if fn.__name__=='list':return {'data':[r],'has_more':False}
        return pi if args[0]==pi['id'] else ch
    monkeypatch.setattr(stripe_async,'run_stripe',provider)
    result=await process_order_refund(db,event)
    assert result['refund_total_cents']==2500
    assert await db.scalar(text('select count(*) from refunds where stripe_refund_id=:id and order_id is null and effects_applied_at is not null'),{'id':r['id']})==1
    assert await db.scalar(text('select refund_order_id from stripe_events where stripe_event_id=:id'),{'id':event['id']}) is None
    assert (await process_order_refund(db,event))['refund_total_cents']==2500
    # Redirecting an applied Refund to a real posted but wrong-sized journal is
    # a historical contradiction, not a valid idempotent replay.
    from app.services.finance.engine import FinanceEngine
    wrong=await FinanceEngine().record_refund(payment_id=payment.id,amount_cents=17,
        reason='requested_by_customer',stripe_refund_id='re_'+uuid.uuid4().hex,db=db,entity_id=payment.entity_id)
    original_id=r['id']
    r['id']=wrong.source_ref.removeprefix('refund:')
    await db.execute(text('update refunds set journal_entry_id=:jid,stripe_refund_id=:new where stripe_refund_id=:rid'),{'jid':wrong.id,'rid':original_id,'new':r['id']})
    await db.commit()
    with pytest.raises(OrderMoneyConflict,match='allocation changed'):
        await process_order_refund(db,event)


@pytest.mark.asyncio
async def test_actual_effects_lock_trace_includes_agent_period_accounts_journal(db):
    import re
    from sqlalchemy import event as sqla_event
    from app.services.order_money_service import assert_lock_sequence,LOCK_ORDER
    oid,tid,pi,ch=await purchase(db)
    party,key=uuid.uuid4(),uuid.uuid4()
    await db.execute(text("insert into party (id,party_type) values (:id,'organization')"),{'id':party})
    await db.execute(text("insert into agent_api_keys (id,org_id,name,key_hash,prefix,spend_used) values (:id,:org,'trace test',:hash,'s1714',2500)"),{'id':key,'org':party,'hash':uuid.uuid4().hex*2})
    await db.execute(text('update transactions set party_id=:party,api_key_id=:key where id=:id'),{'party':party,'key':key,'id':tid})
    ch['amount_refunded']=2500
    event=await signed_event(db,ch)
    await admit_order_refund(db,event)
    trace=[]
    def capture_sql(conn,cursor,statement,parameters,context,executemany):
        if re.search(r'FOR (?:UPDATE|SHARE)',statement,re.I):
            match=re.search(r'\bFROM\s+(?:public\.)?(\w+)',statement,re.I)
            if match and match[1].lower() in LOCK_ORDER:
                trace.append(match[1].lower())
    engine=db.bind.sync_engine
    sqla_event.listen(engine,'before_cursor_execute',capture_sql)
    try:
        await apply_order_refund_effects(db,event=event,provider_payment=pi,provider_charge=ch,
            provider_refunds=[refund(ch,2500,uuid.uuid4().hex)])
        assert_lock_sequence(trace)
        assert set(LOCK_ORDER)<=set(trace)
    finally:
        sqla_event.remove(engine,'before_cursor_execute',capture_sql)
        await db.rollback()


@pytest.mark.asyncio
@pytest.mark.parametrize('delivered',[True,False])
async def test_partial_refund_retains_only_delivered_service_access(db,delivered):
    from app.services.order_service import OrderService
    from fastapi import HTTPException
    oid,tid,pi,ch=await purchase(db,'confirmed' if delivered else 'checkout_pending')
    ch['amount_refunded']=333
    event=await signed_event(db,ch)
    await process(db,event,pi,ch,[refund(ch,333,uuid.uuid4().hex)])
    buyer=await db.scalar(text('select buyer_id from orders where id=:id'),{'id':oid})
    service=OrderService(db)
    assert (await service.can_download(oid,buyer))[0] is delivered
    if delivered:
        actual,_,_=await service._authorize_download_access(oid,buyer)
        assert actual['status']=='partially_refunded' and not actual['revoked']
        await service.revoke_access(oid,None,'independent revoke')
        assert not (await service.can_download(oid,buyer))[0]
        with pytest.raises(HTTPException):
            await service._authorize_download_access(oid,buyer)
    else:
        with pytest.raises(HTTPException):
            await service._authorize_download_access(oid,buyer)


@pytest.mark.asyncio
@pytest.mark.parametrize('amounts',[(333,2167),(2167,333),(1,2499)])
async def test_agent_partial_full_replay_exact_delta_and_posted_balances(db,amounts):
    from test_order_money_protocol import assert_posted_and_immutable
    oid,tid,pi,ch=await purchase(db)
    party,key=uuid.uuid4(),uuid.uuid4()
    await db.execute(text("insert into party (id,party_type) values (:id,'organization')"),{'id':party})
    await db.execute(text("insert into agent_api_keys (id,org_id,name,key_hash,prefix,spend_used) values (:id,:org,'refund proof',:hash,'s1714',400)"),{'id':key,'org':party,'hash':uuid.uuid4().hex*2})
    await db.execute(text("update transactions set buyer_type='agent',party_id=:party,api_key_id=:key where id=:id"),{'party':party,'key':key,'id':tid})
    rs=[]
    for amount in amounts:
        rs.append(refund(ch,amount,uuid.uuid4().hex))
        ch['amount_refunded']=sum(r['amount'] for r in rs)
        event=await signed_event(db,ch)
        await process(db,event,pi,ch,rs)
        await process(db,event,pi,ch,rs)
        duplicate=await signed_event(db,ch)
        await process(db,duplicate,pi,ch,rs)
    assert await db.scalar(text('select spend_used from agent_api_keys where id=:id'),{'id':key})==0
    assert await db.scalar(text('select sum(agent_spend_delta_cents) from refunds where order_id=:id'),{'id':oid})==400
    assert await db.scalar(text('select count(*) from refunds where order_id=:id'),{'id':oid})==2
    assert await db.scalar(text("select count(*) from transaction_events where transaction_id=:id and to_status='refunded'"),{'id':tid})==1
    state=await db.get(OrderMoneyState,oid)
    assert state.refund_applied_cents==2500 and state.seller_refunded_cents==2375
    refs=['marketplace_payment:'+pi['id']]+['refund:'+r['id'] for r in rs]
    assert await balances(db,state.billing_entity_id,refs)=={'1000':0,'2110':0,'4000':0,'5100':0}
    entries=(await db.execute(select(JournalEntry).where(JournalEntry.source_ref.in_(refs)))).scalars().all()
    assert len(entries)==3
    for entry in entries:
        await db.refresh(entry)
        assert entry.status=='posted' and entry.posted_at is not None


@pytest.mark.asyncio
@pytest.mark.parametrize('stage',['mid_effects','commit_before_ack'])
async def test_real_refund_fault_boundaries_rollback_or_replay_once(db,monkeypatch,stage):
    from app.services.finance.engine import FinanceEngine
    oid,tid,pi,ch=await purchase(db)
    ch['amount_refunded']=2500
    event=await signed_event(db,ch)
    r=refund(ch,2500,uuid.uuid4().hex)
    await admit_order_refund(db,event)
    original=FinanceEngine.record_marketplace_refund
    async def fail_after_journal(self,**kwargs):
        await original(self,**kwargs)
        raise RuntimeError('crash after real refund journal flush')
    if stage=='mid_effects':
        with monkeypatch.context() as m:
            m.setattr(FinanceEngine,'record_marketplace_refund',fail_after_journal)
            with pytest.raises(RuntimeError,match='crash'):
                await apply_order_refund_effects(db,event=event,provider_payment=pi,provider_charge=ch,provider_refunds=[r])
            await db.rollback()
        assert await db.scalar(text('select count(*) from journal_entries where source_ref=:ref'),{'ref':'refund:'+r['id']})==0
        assert await db.scalar(text('select refund_phase from stripe_events where stripe_event_id=:id'),{'id':event['id']})=='admitted'
    else:
        await process(db,event,pi,ch,[r])
        # Lost HTTP acknowledgment, caller opens a fresh transaction for replay.
        await db.rollback()
    await process(db,event,pi,ch,[r])
    await process(db,event,pi,ch,[r])
    assert await db.scalar(text('select count(*) from refunds where order_id=:id'),{'id':oid})==1
    assert await db.scalar(text('select count(*) from journal_entries where source_ref=:ref'),{'ref':'refund:'+r['id']})==1
    assert await db.scalar(text("select count(*) from transaction_events where transaction_id=:id and to_status='refunded'"),{'id':tid})==1


@pytest.mark.asyncio
@pytest.mark.parametrize('legacy',[False,True])
@pytest.mark.parametrize('enabled',[False,True])
async def test_both_existing_payout_writers_real_post_or_default_disabled(db,monkeypatch,legacy,enabled):
    import stripe
    from app.core import stripe_async
    from app.core.config import settings
    from app.services.order_service import OrderService
    from app.services.settlement_service import SettlementService
    from app.services.order_money_service import recover_order_payout
    from test_order_money_protocol import assert_posted_and_immutable
    oid,tid,pi,ch=await funded_purchase(db,monkeypatch,legacy=legacy)
    monkeypatch.setattr(settings,'ORDER_PAYOUT_DISPATCH_ENABLED',enabled)
    transfers=[]
    async def provider(fn,*args,**kwargs):
        if fn==stripe.Transfer.create:
            assert enabled
            t={k:v for k,v in kwargs.items() if k!='idempotency_key'}
            t.update(id='tr_'+uuid.uuid4().hex,reversed=False,amount_reversed=0,livemode=False)
            transfers.append(t)
            return t
        if fn==stripe.Transfer.retrieve:return transfers[0]
        if fn==stripe.Refund.list:return {'data':[],'has_more':False}
        return pi if args[0]==pi['id'] else ch
    monkeypatch.setattr(stripe_async,'run_stripe',provider)
    if legacy:
        await db.execute(text("update orders set status='delivered',delivered_at=clock_timestamp() where id=:id"),{'id':oid})
        await db.commit()
        buyer=await db.scalar(text('select buyer_id from orders where id=:id'),{'id':oid})
        result=(await OrderService(db).confirm_order(oid,'buyer',buyer))['payout']
    else:
        result=await SettlementService(db).settle(tid)
    if not enabled:
        assert result['status']=='blocked' and 'dispatch_disabled' in result['reasons']
        assert not transfers
        return
    assert result['status']=='succeeded' and len(transfers)==1
    assert (await recover_order_payout(db,oid))['status']=='succeeded'
    assert len(transfers)==1
    state=await db.get(OrderMoneyState,oid)
    entry=await db.get(JournalEntry,state.payout_journal_entry_id)
    await assert_posted_and_immutable(db,entry,[('1000',0,2375),('2110',2375,0)])
    assert state.seller_payout_posted_cents==2375


@pytest.mark.asyncio
@pytest.mark.parametrize('legacy',[False,True])
@pytest.mark.parametrize('stage',['reserved','dispatching'])
@pytest.mark.parametrize('contender',['revoke','dispute','refund','confirm'])
async def test_payout_ownership_races_real_independent_transactions(db,monkeypatch,legacy,stage,contender):
    import asyncio,stripe
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from app.core import stripe_async
    from app.services.order_money_service import dispatch_order_payout,recover_order_payout
    from app.services.order_service import OrderService
    from app.api.v1.endpoints.webhooks import _handle_dispute_created
    from test_order_money_protocol import disposable_url
    oid,tid,pi,ch=await funded_purchase(db,monkeypatch,legacy=legacy)
    reached,release=asyncio.Event(),asyncio.Event()
    transfers=[]
    async def provider(fn,*args,**kwargs):
        if fn==stripe.Transfer.create:
            assert stage=='dispatching' or contender=='confirm'
            reached.set()
            await release.wait()
            tr={k:v for k,v in kwargs.items() if k!='idempotency_key'}
            tr.update(id='tr_'+uuid.uuid4().hex,reversed=False,amount_reversed=0,livemode=False)
            transfers.append(tr)
            return tr
        if fn==stripe.Transfer.retrieve:return transfers[0]
        if fn==stripe.PaymentIntent.retrieve and stage=='reserved':
            reached.set()
            await release.wait()
        if fn==stripe.Refund.list:return {'data':[],'has_more':False}
        return pi if args[0]==pi['id'] else ch
    monkeypatch.setattr(stripe_async,'run_stripe',provider)
    ae=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    task=asyncio.create_task(dispatch_order_payout(db,oid))
    try:
        await asyncio.wait_for(reached.wait(),4)
        async with AsyncSession(ae,expire_on_commit=False) as other:
            await other.execute(text("set local lock_timeout='2s'"))
            if contender=='revoke':
                await OrderService(other).revoke_access(oid,None,'race revoke')
            elif contender=='dispute':
                await other.run_sync(lambda sync:_handle_dispute_created({'id':'dp_'+uuid.uuid4().hex,'payment_intent':pi['id'],'reason':'fraudulent'},sync))
                await other.commit()
            elif contender=='confirm':
                from fastapi import HTTPException
                from app.services.transaction_service import TransactionService
                with pytest.raises(HTTPException) as exc:
                    if legacy:
                        await OrderService(other).confirm_order(oid,'auto')
                    else:
                        await TransactionService(other).confirm(tid,'buyer')
                assert exc.value.status_code==400
                assert ('Cannot confirm order' if legacy else 'Invalid transition: confirmed') in exc.value.detail
                await other.rollback()
            else:
                event=await signed_event(other,ch)
                await admit_order_refund(other,event)
        release.set()
        result=await asyncio.wait_for(task,4)
        if contender=='confirm':
            assert result['status']=='succeeded' and len(transfers)==1
        elif stage=='reserved':
            assert result['status']=='blocked' and not transfers
        else:
            assert result['status']=='reconciliation_required' and len(transfers)==1
            assert (await recover_order_payout(db,oid))['status']=='reconciliation_required'
            assert len(transfers)==1
        if contender=='refund':
            ch['amount_refunded']=2500
            r=refund(ch,2500,uuid.uuid4().hex)
            await process(db,event,pi,ch,[r])
            assert await db.scalar(text('select revoked from orders where id=:id'),{'id':oid})
    finally:
        release.set()
        if not task.done():
            task.cancel()
        await asyncio.gather(task,return_exceptions=True)
        await ae.dispose()


@pytest.mark.asyncio
async def test_real_canonical_delivery_and_confirmation_uses_actual_sync_trigger(db):
    from app.services.transaction_service import TransactionService
    oid,tid,pi,ch=await purchase(db,'fulfilling')
    await db.execute(text("update orders set status='pending_delivery' where id=:id"),{'id':oid})
    await db.commit()
    service=TransactionService(db)
    delivered=await service.mark_delivered(tid,{'sha256':'f'*64})
    assert delivered['status']=='delivered' and delivered['delivered_at'] is not None
    assert await db.scalar(text('select status from orders where id=:id'),{'id':oid})=='delivered'
    assert await db.scalar(text("select count(*) from transaction_events where transaction_id=:id and to_status='delivered'"),{'id':tid})==1
    confirmed=await service.confirm(tid,'buyer',delivered['buyer_id'])
    assert confirmed['status']=='confirmed'
    event=(await db.execute(text("select id,created_at from transaction_events where transaction_id=:id and to_status='confirmed' order by created_at desc limit 1"),{'id':tid})).one()
    from app.services.order_money_service import order_payout_eligibility
    money=await lock_order_money(db,oid)
    result=await order_payout_eligibility(db,money,destination='acct_test')
    assert 'confirmation_hold' in result['reasons']
    assert result['confirmation_event_id']==str(event.id)


@pytest.mark.asyncio
async def test_partial_refund_refresh_route_manifest_blocker(db,monkeypatch):
    # Original node retained; F4 replaces the no-exception assertion with the
    # entire real HTTP -> enqueue -> decrypted callback -> redemption proof.
    await test_f4_s3_http_refresh_decrypted_callback_and_redeem(db,monkeypatch,True,False)


@pytest.mark.asyncio
async def test_pi_only_pending_admission_resolves_after_order_commit(db):
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from test_order_money_protocol import disposable_url
    oid,tid,pi,ch=await purchase(db)
    ch['amount_refunded']=2500
    ae=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    try:
        async with AsyncSession(ae,expire_on_commit=False) as early:
            event=await signed_event(early,ch)
            result=await admit_order_refund(early,event)
            assert result['order_id'] is None
            assert await early.scalar(text('select refund_order_id from stripe_events where stripe_event_id=:id'),{'id':event['id']}) is None
        await db.commit()
        await process(db,event,pi,ch,[refund(ch,2500,uuid.uuid4().hex)])
        assert await db.scalar(text('select refund_order_id from stripe_events where stripe_event_id=:id'),{'id':event['id']})==oid
        assert await db.scalar(text('select status from transactions where id=:id'),{'id':tid})=='refunded'
    finally:
        await ae.dispose()


def payout_double(monkeypatch, pi, ch):
    """Deterministic adapter boundary, retaining complete frozen requests."""
    import stripe
    from app.core import stripe_async
    calls = []
    async def provider(fn, *args, **kwargs):
        if fn == stripe.Transfer.create:
            calls.append(dict(kwargs))
            return {**{k:v for k,v in kwargs.items() if k != 'idempotency_key'},
                    'id':'tr_'+pi['id'][3:], 'reversed':False, 'amount_reversed':0, 'livemode':False}
        if fn == stripe.Refund.list:
            return {'data':[], 'has_more':False}
        if fn == stripe.PaymentIntent.retrieve:
            assert args == (pi['id'],)
            return pi
        if fn == stripe.Charge.retrieve:
            assert args == (ch['id'],)
            return ch
        raise AssertionError('Unexpected provider adapter operation')
    monkeypatch.setattr(stripe_async, 'run_stripe', provider)
    return calls


@pytest.mark.asyncio
@pytest.mark.parametrize('linked',[False,True])
@pytest.mark.parametrize('actor',['buyer','system'])
async def test_generic_refund_refused_without_any_write_event_or_commit(db,linked,actor):
    from app.services.transaction_service import TransactionService
    from fastapi import HTTPException
    from sqlalchemy import event as sa_event
    oid,tid,pi,ch=await purchase(db,'settled')
    if not linked:
        await db.execute(text('update orders set transaction_id=null where id=:id'),{'id':oid})
        await db.execute(text('update transactions set order_id=null where id=:id'),{'id':tid})
    await db.commit()
    before=(await db.execute(text('select * from transactions where id=:id'),{'id':tid})).one()
    writes=[]; commits=[]
    def sql(conn,cursor,statement,parameters,context,executemany):
        if statement.lstrip().split()[0].lower() in {'update','insert','delete'}:writes.append(statement)
    def committed(session):commits.append(True)
    sa_event.listen(db.bind.sync_engine,'before_cursor_execute',sql)
    sa_event.listen(db.sync_session,'after_commit',committed)
    try:
        with pytest.raises(HTTPException) as exc:
            await TransactionService(db).transition(tid,'refunded',actor)
        assert exc.value.status_code==409
        assert exc.value.detail=='Validated provider refund processor owns this transition'
        assert writes==[] and commits==[]
        assert (await db.execute(text('select * from transactions where id=:id'),{'id':tid})).one()==before
        assert await db.scalar(text('select count(*) from transaction_events where transaction_id=:id'),{'id':tid})==0
    finally:
        sa_event.remove(db.bind.sync_engine,'before_cursor_execute',sql)
        sa_event.remove(db.sync_session,'after_commit',committed)


@pytest.mark.asyncio
async def test_quote_waits_for_parent_before_first_transaction_write(db):
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from test_order_money_protocol import disposable_url
    from app.services.transaction_service import TransactionService
    oid,tid,pi,ch=await purchase(db,'initiated')
    await db.execute(text('update orders set stripe_payment_intent_id=null where id=:id'),{'id':oid})
    await db.execute(text('update transactions set stripe_payment_intent_id=null where id=:id'),{'id':tid})
    await db.commit()
    engine=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    try:
        async with AsyncSession(engine) as owner,AsyncSession(engine) as quoting:
            await owner.execute(text('select id from orders where id=:id for update'),{'id':oid})
            pid=await quoting.scalar(text('select pg_backend_pid()'))
            task=asyncio.create_task(TransactionService(quoting).create_quote(tid,2500,'USD',{'license':'standard'}))
            for _ in range(300):
                if await db.scalar(text('select cardinality(pg_blocking_pids(:pid))>0'),{'pid':pid}):break
                await asyncio.sleep(.01)
            else:pytest.fail('Quote never waited on parent order')
            # A reversed first UPDATE would hold this row and NOWAIT would fail.
            await owner.execute(text('select id from transactions where id=:id for update nowait'),{'id':tid})
            assert await owner.scalar(text('select status from transactions where id=:id'),{'id':tid})=='initiated'
            assert await owner.scalar(text('select metadata from transactions where id=:id'),{'id':tid}) in (None,{})
            await owner.commit()
            result=await asyncio.wait_for(task,5)
            assert result['status']=='quoted' and result['metadata']['quote_terms']=={'license':'standard'}
            assert await db.scalar(text("select count(*) from transaction_events where transaction_id=:id and from_status='initiated' and to_status='quoted'"),{'id':tid})==1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize('newer_first',[False,True])
@pytest.mark.parametrize('total',[1000,2500])
async def test_simultaneous_partial_and_reordered_full_serialize_once(db,newer_first,total):
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from test_order_money_protocol import disposable_url
    oid,tid,pi,ch=await purchase(db,'delivered')
    first=refund(ch,333,uuid.uuid4().hex)
    second=refund(ch,total-333,uuid.uuid4().hex)
    partial={**ch,'amount_refunded':333};full={**ch,'amount_refunded':total}
    events=[await signed_event(db,partial),await signed_event(db,full)]
    for event in events: await admit_order_refund(db,event)
    await db.commit()
    ae=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    async with AsyncSession(ae) as blocker,AsyncSession(ae,expire_on_commit=False) as a,AsyncSession(ae,expire_on_commit=False) as b:
        await blocker.execute(text('select id from orders where id=:id for update'),{'id':oid})
        sessions=[a,b]; pids=[await x.scalar(text('select pg_backend_pid()')) for x in sessions]
        async def effects(index):
            async with asyncio.timeout(5):
                # Both independently read the current complete provider set;
                # delayed signed partial delivery never decreases effects.
                result=await apply_order_refund_effects(sessions[index],event=events[index],provider_payment=pi,provider_charge=full,provider_refunds=[first,second])
                await sessions[index].commit()
                return result
        order=[1,0] if newer_first else [0,1]
        tasks=[]
        try:
            for i in order:
                tasks.append(asyncio.create_task(effects(i)))
                async with asyncio.timeout(3):
                    while not await db.scalar(text('select cardinality(pg_blocking_pids(:pid))>0'),{'pid':pids[i]}):await asyncio.sleep(.01)
            await blocker.commit()
            results=await asyncio.gather(*tasks)
            assert all(row['refund_total_cents']==total for row in results)
        finally:
            await blocker.rollback()
            for task in tasks:
                if not task.done():task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)
    await ae.dispose()
    if total==1000:
        assert await db.scalar(text('select status from transactions where id=:id'),{'id':tid})=='delivered'
        assert await db.scalar(text('select revoked from orders where id=:id'),{'id':oid}) is False
        assert await balances(db,await merchant(db),['marketplace_payment:'+pi['id'],'refund:'+first['id'],'refund:'+second['id']])=={'1000':1500,'2110':-1425,'4000':-75,'5100':0}
        return
    assert await db.scalar(text('select refund_amount_cents from orders where id=:id'),{'id':oid})==2500
    assert await db.scalar(text('select count(*) from refunds where order_id=:id and effects_applied_at is not null'),{'id':oid})==2
    assert await db.scalar(text("select count(*) from transaction_events where transaction_id=:id and to_status='refunded'"),{'id':tid})==1
    assert await db.scalar(text('select status from transactions where id=:id'),{'id':tid})=='refunded'
    assert await balances(db,await merchant(db),['marketplace_payment:'+pi['id'],'refund:'+first['id'],'refund:'+second['id']])=={'1000':0,'2110':0,'4000':0,'5100':0}


@pytest.mark.asyncio
@pytest.mark.parametrize('refund_first',[False,True])
async def test_confirmation_and_refund_race_has_one_serial_outcome(db,refund_first):
    import asyncio
    from fastapi import HTTPException
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from test_order_money_protocol import disposable_url
    from app.services.transaction_service import TransactionService
    oid,tid,pi,ch=await purchase(db,'delivered')
    ch['amount_refunded']=2500
    event=await signed_event(db,ch)
    await db.commit()
    ae=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    async with AsyncSession(ae,expire_on_commit=False) as a,AsyncSession(ae,expire_on_commit=False) as b:
        async def confirm(session):
            try:return await TransactionService(session).confirm(tid,'buyer')
            except HTTPException as exc:
                await session.rollback()
                assert exc.status_code==409 and exc.detail in {'Order money restriction prevents transition','Refund admission prevents transition'}
                return {'status':'refused'}
        async def refund_effects(session):
            return await process(session,event,pi,ch,[refund(ch,2500,uuid.uuid4().hex)])
        waiting_pid=await b.scalar(text('select pg_backend_pid()'))
        async def wait_blocked():
            async with asyncio.timeout(3):
                while not await db.scalar(text('select cardinality(pg_blocking_pids(:pid))>0'),{'pid':waiting_pid}):await asyncio.sleep(.01)
        if refund_first:
            await admit_order_refund(a,event)
            await lock_order_money(a,oid)
            task=asyncio.create_task(confirm(b))
            await wait_blocked()
            await apply_order_refund_effects(a,event=event,provider_payment=pi,provider_charge=ch,provider_refunds=[refund(ch,2500,uuid.uuid4().hex)])
            await a.commit()
            assert (await task)['status']=='refused'
        else:
            await a.execute(text('select id from orders where id=:id for update'),{'id':oid})
            task=asyncio.create_task(refund_effects(b))
            await wait_blocked()
            assert (await confirm(a))['status']=='confirmed'
            await task
    await ae.dispose()
    assert await db.scalar(text('select status from transactions where id=:id'),{'id':tid})=='refunded'
    assert await db.scalar(text("select count(*) from transaction_events where transaction_id=:id and to_status='confirmed'"),{'id':tid})==(0 if refund_first else 1)
    assert await db.scalar(text("select count(*) from transaction_events where transaction_id=:id and to_status='refunded'"),{'id':tid})==1


@pytest.mark.asyncio
@pytest.mark.parametrize('case,expected',[
    ('fake_refund','Invalid provider identity'),
    ('refund_currency','Provider refund binding mismatch'),
    ('refund_amount','Provider refund binding mismatch'),
    ('unknown_status','Unknown provider refund status'),
    ('wrong_gross','Authoritative capture gross mismatch'),
    ('wrong_currency','Authoritative capture identity/scope mismatch'),
    ('wrong_owner','Provider order metadata mismatch'),
    ('wrong_entity','Authoritative capture identity/scope mismatch'),
    ('truncated','Truncated refund pagination'),
    ('changed_snapshot','Provider snapshot changed during pagination'),
    ('duplicate_refund','Duplicate identity across refund pages'),
])
async def test_provider_fault_matrix_keeps_admission_retryable_without_effects(db,monkeypatch,case,expected):
    from app.core import stripe_async
    from app.services.refund_processing_service import process_order_refund
    oid,tid,pi,ch=await purchase(db)
    ch['amount_refunded']=2500
    event=await signed_event(db,ch)
    r=refund(ch,2500,uuid.uuid4().hex)
    if case=='fake_refund':r['id']='not-a-provider-refund'
    if case=='refund_currency':r['currency']='eur'
    if case=='refund_amount':r['amount']=True
    if case=='unknown_status':r['status']='mystery'
    if case=='wrong_gross':pi['amount_received']=2499
    if case=='wrong_currency':pi['currency']='eur'
    if case=='wrong_owner':pi['metadata']['order_id']=str(uuid.uuid4())
    if case=='wrong_entity':pi['on_behalf_of']='acct_foreign'
    charge_reads=[]
    async def provider(fn,*args,**kwargs):
        if fn.__name__=='list':
            if case=='truncated':return {'data':[],'has_more':True}
            return {'data':[r,r] if case=='duplicate_refund' else [r],'has_more':False}
        if args[0]==pi['id']:return pi
        charge_reads.append(True)
        return {**ch,'amount_refunded':2499} if case=='changed_snapshot' and len(charge_reads)>1 else ch
    monkeypatch.setattr(stripe_async,'run_stripe',provider)
    with pytest.raises(OrderMoneyConflict,match=expected):
        await process_order_refund(db,event)
    await db.rollback()
    assert await db.scalar(text('select refund_phase from stripe_events where stripe_event_id=:id'),{'id':event['id']})=='admitted'
    assert await db.scalar(text('select count(*) from refunds where order_id=:id and effects_applied_at is not null'),{'id':oid})==0
    assert await db.scalar(text("select count(*) from journal_entries where source_ref=:ref"),{'ref':'marketplace_payment:'+pi['id']})==0
    assert await db.scalar(text('select status from transactions where id=:id'),{'id':tid})=='confirmed'


@pytest.mark.asyncio
@pytest.mark.parametrize('status',['pending','failed','canceled'])
async def test_non_succeeded_provider_refund_has_zero_money_or_spend_delta(db,status):
    oid,tid,pi,ch=await purchase(db)
    r=refund(ch,2500,uuid.uuid4().hex);r['status']=status
    event=await signed_event(db,ch)
    result=await process(db,event,pi,ch,[r])
    assert result['refund_total_cents']==0
    assert await db.scalar(text('select refund_applied_cents from order_money_states where order_id=:id'),{'id':oid})==0
    assert await db.scalar(text('select count(*) from refunds where order_id=:id and effects_applied_at is not null'),{'id':oid})==0
    assert await db.scalar(text('select revoked from orders where id=:id'),{'id':oid}) is False


@pytest.mark.asyncio
@pytest.mark.parametrize('parent',['users','billing_entities'])
async def test_capture_foreign_key_reference_wait_does_not_take_gl_early(db,parent):
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from test_order_money_protocol import disposable_url
    oid,tid,pi,ch=await purchase(db)
    eid=await merchant(db)
    uid=await db.scalar(text('select buyer_id from orders where id=:id'),{'id':oid})
    await db.commit()
    engine=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    async with AsyncSession(engine) as blocker,AsyncSession(engine,expire_on_commit=False) as worker:
        await blocker.execute(text(f'select id from {parent} where id=:id for update'),{'id':uid if parent=='users' else eid})
        pid=await worker.scalar(text('select pg_backend_pid()'))
        async def capture_effect():
            money=await lock_order_money(worker,oid)
            return await ensure_order_capture(worker,order=money.order,transaction=money.transaction,provider_payment=pi,provider_charge=ch,origin='payment_event',locked=money)
        task=asyncio.create_task(capture_effect())
        try:
            async with asyncio.timeout(3):
                while not await db.scalar(text('select cardinality(pg_blocking_pids(:pid))>0'),{'pid':pid}):await asyncio.sleep(.01)
            # Payment/authority FK parent validation occurs before finance locks.
            await db.execute(text("select id from gl_accounts where entity_id=:id order by entity_id,code,id for update nowait"),{'id':eid})
            await db.rollback()
            await blocker.rollback()
            payment=await asyncio.wait_for(task,4)
            assert payment.customer_id==uid and payment.entity_id==eid
            await worker.rollback()
        finally:
            if not task.done():task.cancel()
            await asyncio.gather(task,return_exceptions=True)
    await engine.dispose()

from test_order_money_protocol import provider_http_guard


@pytest.fixture(autouse=True)
def _no_real_provider_http(provider_http_guard):
    yield


@pytest.mark.asyncio
async def test_agent_update_lock_precedes_accounting_period_on_actual_effects(db):
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from app.services.finance.engine import FinanceEngine
    from test_order_money_protocol import disposable_url
    oid,tid,pi,ch=await purchase(db)
    party,key=uuid.uuid4(),uuid.uuid4()
    await db.execute(text("insert into party(id,party_type) values(:id,'organization')"),{'id':party})
    await db.execute(text("insert into agent_api_keys(id,org_id,name,key_hash,prefix,spend_used) values(:id,:party,'F3 barrier',:hash,'s1714',2500)"),{'id':key,'party':party,'hash':uuid.uuid4().hex*2})
    await db.execute(text('update transactions set party_id=:party,api_key_id=:key where id=:id'),{'party':party,'key':key,'id':tid})
    now=datetime.now(timezone.utc)
    period=await FinanceEngine()._get_or_create_period(await merchant(db),now.year,now.month,db)
    period_id=period.id
    ch['amount_refunded']=2500
    event=await signed_event(db,ch)
    await admit_order_refund(db,event)
    ae=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    async with AsyncSession(ae) as blocker,AsyncSession(ae,expire_on_commit=False) as effects:
        await blocker.execute(text('select id from agent_api_keys where id=:id for update'),{'id':key})
        pid=await effects.scalar(text('select pg_backend_pid()'))
        task=asyncio.create_task(apply_order_refund_effects(effects,event=event,provider_payment=pi,provider_charge=ch,provider_refunds=[refund(ch,2500,uuid.uuid4().hex)]))
        try:
            async with asyncio.timeout(3):
                while not await db.scalar(text('select cardinality(pg_blocking_pids(:pid))>0'),{'pid':pid}):await asyncio.sleep(.01)
            await db.execute(text('select id from accounting_periods where id=:id for update nowait'),{'id':period_id})
            await db.rollback()
            await blocker.rollback()
            assert (await asyncio.wait_for(task,4))['refund_total_cents']==2500
            await effects.commit()
            assert await db.scalar(text('select spend_used from agent_api_keys where id=:id'),{'id':key})==0
        finally:
            if not task.done():task.cancel()
            await asyncio.gather(task,return_exceptions=True)
    await ae.dispose()


@pytest.mark.asyncio
async def test_actual_provider_pagination_applies_all_pages_once(db,monkeypatch):
    from app.services.refund_processing_service import process_order_refund
    from app.core import stripe_async
    oid,tid,pi,ch=await purchase(db)
    ch['amount_refunded']=2500
    event=await signed_event(db,ch)
    first=refund(ch,333,uuid.uuid4().hex);last=refund(ch,2167,uuid.uuid4().hex)
    pages=[]
    async def provider(fn,*args,**kwargs):
        if fn.__name__=='list':
            pages.append(dict(kwargs))
            assert kwargs['charge']==ch['id'] and kwargs['limit']==100
            if 'starting_after' not in kwargs:return {'data':[first],'has_more':True}
            assert kwargs['starting_after']==first['id']
            return {'data':[last],'has_more':False}
        return pi if args[0]==pi['id'] else ch
    monkeypatch.setattr(stripe_async,'run_stripe',provider)
    assert (await process_order_refund(db,event))['refund_total_cents']==2500
    assert len(pages)==2
    assert await db.scalar(text('select count(*) from refunds where order_id=:id and effects_applied_at is not null'),{'id':oid})==2
    assert await balances(db,await merchant(db),['marketplace_payment:'+pi['id'],'refund:'+first['id'],'refund:'+last['id']])=={'1000':0,'2110':0,'4000':0,'5100':0}


@pytest.mark.asyncio
async def test_duplicate_payment_intent_order_binding_refuses_before_admission(db):
    oid,tid,pi,ch=await purchase(db)
    other,other_tid,other_pi,other_ch=await purchase(db)
    before=[await f6_snapshot(db,oid,tid,None),await f6_snapshot(db,other,other_tid,None)]
    with pytest.raises(DBAPIError) as refused:
        async with db.begin_nested():
            await db.execute(text('update orders set stripe_payment_intent_id=:pi where id=:id'),{'pi':pi['id'],'id':other})
    assert refused.value.orig.sqlstate=='23505'
    assert 'uq_s1714_order_payment_intent' in str(refused.value.orig)
    assert [await f6_snapshot(db,oid,tid,None),await f6_snapshot(db,other,other_tid,None)]==before
    assert await db.scalar(text('SELECT stripe_payment_intent_id FROM transactions WHERE id=:id'),{'id':other_tid})==other_pi['id']
    assert await db.scalar(text('SELECT count(*) FROM payments WHERE stripe_payment_intent_id=:pi'),{'pi':pi['id']})==0


@pytest.mark.asyncio
@pytest.mark.parametrize('restriction',['full_refund','independent_revoke','pending_refund'])
async def test_dispute_won_replay_cannot_erase_money_restriction(db,restriction):
    from app.api.v1.endpoints.webhooks import _handle_dispute_closed
    from app.services.order_service import OrderService
    oid,tid,pi,ch=await purchase(db,'delivered')
    if restriction=='full_refund':
        ch['amount_refunded']=2500
        await process(db,await signed_event(db,ch),pi,ch,[refund(ch,2500,uuid.uuid4().hex)])
    elif restriction=='independent_revoke':
        await OrderService(db).revoke_access(oid,None,'independent restriction')
    else:
        await admit_order_refund(db,await signed_event(db,ch))
    before=(await db.execute(text('select status,revoked,refund_amount_cents from orders where id=:id'),{'id':oid})).one()
    tx_before=await db.scalar(text('select status from transactions where id=:id'),{'id':tid})
    for _ in range(2):
        await db.run_sync(lambda sync:_handle_dispute_closed({'id':'dp_'+pi['id'][3:],'payment_intent':pi['id'],'status':'won'},sync))
        await db.commit()
    assert (await db.execute(text('select status,revoked,refund_amount_cents from orders where id=:id'),{'id':oid})).one()==before
    assert await db.scalar(text('select status from transactions where id=:id'),{'id':tid})==tx_before
    assert await db.scalar(text("select count(*) from order_events where order_id=:id and event_type='dispute_resolved'"),{'id':oid})==0


@pytest.mark.asyncio
async def test_downgrade_with_protocol_history_refuses_without_schema_or_data_change(db):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from test_order_money_protocol import f2_migration
    head_before=await db.scalar(text('select version_num from alembic_version'))
    assert head_before=='s1714_canonical_pi_binding_v1'
    oid,tid,pi,ch=await purchase(db)
    await lock_order_money(db,oid)
    before=(await db.execute(text('select * from order_money_states where order_id=:id'),{'id':oid})).one()
    def downgrade(sync):
        with Operations.context(MigrationContext.configure(sync.connection())):
            f2_migration().downgrade()
    with pytest.raises(RuntimeError,match='protocol history present: forward repair only'):
        await db.run_sync(downgrade)
    assert (await db.execute(text('select * from order_money_states where order_id=:id'),{'id':oid})).one()==before
    assert await db.scalar(text('select version_num from alembic_version'))==head_before


async def f4_partial(db):
    oid,tid,pi,ch=await purchase(db)
    await db.execute(text("update orders set delivered_at=clock_timestamp() where id=:id"),{'id':oid})
    ch['amount_refunded']=333
    r=refund(ch,333,uuid.uuid4().hex)
    await process(db,await signed_event(db,ch),pi,ch,[r])
    row=dict((await db.execute(text('select * from orders where id=:id'),{'id':oid})).mappings().one())
    return row,tid,pi,ch,r


@pytest.mark.asyncio
@pytest.mark.parametrize('surface',['reference','broker','raw'])
async def test_f4_actual_retained_access_surfaces(db,monkeypatch,surface):
    from types import SimpleNamespace
    from app.api.v1.endpoints.orders import get_order_access
    from app.services.fulfillment_broker import FulfillmentBroker
    from app.services.raw_download_service import RawDownloadService
    row,tid,pi,ch,r=await f4_partial(db)
    oid,buyer,lid=row['id'],row['buyer_id'],row['listing_id']
    if surface=='reference':
        await db.execute(text("update listings set fulfillment_type='reference',source_delivery=cast(:src as jsonb) where id=:id"),{'id':lid,'src':json.dumps({'kind':'public_url','url':'https://example.invalid/data'})})
        result=await get_order_access(oid,user=SimpleNamespace(id=buyer),db=db)
        assert result['is_delivered'] and result['can_download'] and result['download_urls'][0]['url']=='https://example.invalid/data'
    elif surface=='broker':
        result=await FulfillmentBroker(db).request_access(oid,str(buyer))
        assert result['status']=='already_available' and result['access_token']
    else:
        from unittest.mock import AsyncMock
        await db.execute(text("update listings set fulfillment_type='file_download',raw_metadata=cast(:raw as jsonb) where id=:id"),{'id':lid,'raw':json.dumps({'files':[{'path':'data.csv','sha256':'a'*64}]})})
        nonce=AsyncMock()
        monkeypatch.setattr(RawDownloadService,'_store_nonce',nonce)
        result=await RawDownloadService(db).generate_download_token(order_id=oid,listing_id=lid,user_id=buyer)
        assert 'error' not in result and result['token']
        assert nonce.await_count==1


async def f4_staged(db,monkeypatch,tmp_path):
    import hashlib,base64
    from app.services import fulfillment_listener_service as listener
    from app.schemas.fulfillment import FulfillmentMetadataMessage,FulfillmentChunkMessage,FulfillmentCompleteMessage
    oid,tid,pi,ch=await purchase(db,'fulfilling')
    await db.execute(text("update orders set status='pending_delivery' where id=:id"),{'id':oid})
    row=dict((await db.execute(text('select * from orders where id=:id'),{'id':oid})).mappings().one())
    monkeypatch.setattr(listener,'STAGING_DIR',tmp_path)
    svc=listener.FulfillmentListenerService(db)
    transfer=str(uuid.uuid4());data=b'F4 actual staged bytes';digest=hashlib.sha256(data).hexdigest()
    meta=FulfillmentMetadataMessage(transfer_id=transfer,order_id=str(oid),listing_id=str(row['listing_id']),parameters=dict(filename='data.csv',content_type='text/csv',total_bytes=len(data),total_chunks=1,sha256_hash=digest))
    assert (await svc.handle_metadata(meta,row['seller_id']))['success']
    chunk=FulfillmentChunkMessage(transfer_id=transfer,chunk_index=0,byte_offset=0,payload_length=len(data),chunk_sha256=digest,payload=base64.b64encode(data).decode())
    assert (await svc.handle_chunk(chunk,row['seller_id']))['success']
    complete=FulfillmentCompleteMessage(transfer_id=transfer,order_id=str(oid),parameters=dict(file_size_bytes=len(data),chunk_count=1,sha256_hash=digest))
    return svc,row,tid,pi,ch,complete


@pytest.mark.asyncio
@pytest.mark.parametrize('closure',['partial','full','revoked','disputed','cancelled','expired'])
async def test_f4_staged_late_complete_refuses(db,monkeypatch,tmp_path,closure):
    svc,row,tid,pi,ch,msg=await f4_staged(db,monkeypatch,tmp_path)
    if closure in ('partial','full'):
        amount=333 if closure=='partial' else 2500
        ch['amount_refunded']=amount
        await process(db,await signed_event(db,ch),pi,ch,[refund(ch,amount,uuid.uuid4().hex)])
    elif closure=='revoked':
        from app.services.order_service import OrderService
        await OrderService(db).revoke_access(row['id'],None,'F4 independent revoke')
    else:
        await db.execute(text('update transactions set status=:status where id=:id'),{'status':closure,'id':tid})
        await db.commit()
    before=(await db.execute(text('select status,delivered_at,completed_at,confirmed_at from orders where id=:id'),{'id':row['id']})).one()
    result=await svc.handle_complete(msg,row['seller_id'])
    assert result=={'success':False,'error':'INVALID_ORDER_STATE'}
    assert (await db.execute(text('select status,delivered_at,completed_at,confirmed_at from orders where id=:id'),{'id':row['id']})).one()==before
    assert await db.scalar(text('select count(*) from fulfillment_download_tokens where order_id=:id'),{'id':row['id']})==0
    assert not (tmp_path/msg.transfer_id).exists()


@pytest.mark.asyncio
@pytest.mark.parametrize('closure',['partial','full','revoked','disputed','cancelled','expired'])
async def test_f4_staged_token_current_access(db,monkeypatch,tmp_path,closure):
    svc,row,tid,pi,ch,msg=await f4_staged(db,monkeypatch,tmp_path)
    completed=await svc.handle_complete(msg,row['seller_id'])
    assert completed['success'] and completed['download_token']
    if closure in ('partial','full'):
        amount=333 if closure=='partial' else 2500
        ch['amount_refunded']=amount
        await process(db,await signed_event(db,ch),pi,ch,[refund(ch,amount,uuid.uuid4().hex)])
    elif closure=='revoked':
        from app.services.order_service import OrderService
        await OrderService(db).revoke_access(row['id'],None,'F4 independent revoke')
    else:
        await db.execute(text('update transactions set status=:status where id=:id'),{'status':closure,'id':tid})
        await db.commit()
    from app.api.v1.endpoints.fulfillment_download import download_fulfillment_file
    from fastapi import HTTPException
    if closure=='partial':
        response=await download_fulfillment_file(row['id'],completed['download_token'],{'id':str(row['buyer_id'])},db)
        body=b''.join([chunk async for chunk in response.body_iterator])
        assert body==b'F4 actual staged bytes'
        assert await db.scalar(text('select download_count from fulfillment_download_tokens where order_id=:id'),{'id':row['id']})==1
    else:
        with pytest.raises(HTTPException) as refused:
            await download_fulfillment_file(row['id'],completed['download_token'],{'id':str(row['buyer_id'])},db)
        assert refused.value.status_code==403 and refused.value.detail=='Order access unavailable'
        assert await db.scalar(text('select download_count from fulfillment_download_tokens where order_id=:id'),{'id':row['id']})==0
        assert await svc.handle_complete(msg,row['seller_id'])=={'success':False,'error':'INVALID_ORDER_STATE'}


async def f4_s3(db,monkeypatch,online=True):
    from datetime import timedelta
    from types import SimpleNamespace
    from unittest.mock import AsyncMock,Mock
    from app.api.v1.endpoints import trust_websocket,orders
    from app.services import fulfillment_service as fulfillment
    from app.services.order_service import OrderService
    from app.models.trust import Device,TrustSession
    from fastapi import FastAPI
    from app.services.rate_limit_service import RateLimiter
    from httpx import AsyncClient,ASGITransport
    oid,tid,pi,ch=await purchase(db,'fulfilling')
    row=dict((await db.execute(text('select * from orders where id=:id'),{'id':oid})).mappings().one())
    version=uuid.uuid4();device_id='f4-'+uuid.uuid4().hex
    await db.execute(text("update orders set status='pending_delivery',access_expires_at=clock_timestamp()+interval '1 day' where id=:id"),{'id':oid})
    await db.execute(text("update listings set fulfillment_type='ai_queryable',raw_metadata=cast(:raw as jsonb) where id=:id"),{'id':row['listing_id'],'raw':json.dumps({'s3_connection':{'bucket':'synthetic'}})})
    await db.execute(text("insert into listing_versions (id,listing_id,version_label,prefix,published_at,status,object_count,total_size_bytes,manifest_hash) values (:id,:listing,'v1','v1/',clock_timestamp(),'active',1,123,repeat('a',64))"),{'id':version,'listing':row['listing_id']})
    await db.execute(text('update orders set purchased_version_id=:version where id=:id'),{'version':version,'id':oid})
    device=Device(id=uuid.uuid4(),device_id=device_id,user_id=row['seller_id'],vectoraiz_version='test',os_type='linux')
    db.add(device);await db.flush()
    session=TrustSession(id=uuid.uuid4(),device_id=device.id,session_key_hash='f'*64,nonce='test',expires_at=datetime.now(timezone.utc)+timedelta(hours=1),is_active=online)
    db.add(session);await db.commit()
    captured={};published=[]
    async def send(response,*args):captured[response.request_id]=json.loads(response.model_dump_json())
    async def publish(message):published.append(message.event_id)
    monkeypatch.setattr(trust_websocket,'_send_encrypted_response',send)
    monkeypatch.setattr(fulfillment,'is_registered_trust_connection',AsyncMock(return_value=online))
    monkeypatch.setattr(fulfillment.trust_event_bus,'publish_message',publish)
    monkeypatch.setattr(fulfillment,'register_post_commit_notification',Mock())
    monkeypatch.setattr(fulfillment.FulfillmentService,'_notify_buyer_ready',AsyncMock())
    monkeypatch.setattr(fulfillment.FulfillmentService,'_notify_seller_sale',AsyncMock())
    monkeypatch.setattr(fulfillment.settings,'DEMO_FULFILLMENT',False)
    def url(old=False):
        date=datetime.now(timezone.utc)-timedelta(hours=1) if old else datetime.now(timezone.utc)
        return f'https://synthetic.s3.eu-west-1.amazonaws.com/v1/file%2Bname.csv?X-Amz-Date={date:%Y%m%dT%H%M%SZ}&X-Amz-Expires=300&X-Amz-Signature=synthetic%2fab%2BCD&versionId=v%2B1'
    def frame(raw=None,nested=False,request_id=None):
        business=dict(success=True,access_url=raw or url(),expires_at=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat(),file_hash='a'*64,file_size_bytes=123)
        identifiers=dict(order_id=str(oid),listing_id=str(row['listing_id']))
        params=dict(identifiers,parameters=business) if nested else dict(identifiers,**business)
        return dict(action='vai.fulfillment.response',request_id=request_id or str(uuid.uuid4()),parameters=params)
    async def dispatch(message,seller=None,device_name=None):
        await trust_websocket._handle_decrypted_payload(json.dumps(message).encode(),SimpleNamespace(user_id=seller or row['seller_id'],device_id=device_name or device_id),db,None,None,None,'nonce',uuid.uuid4())
        return captured[message['request_id']]
    assert (await dispatch(frame()))['success']
    service=OrderService(db)
    old_token=await service.issue_download_token(oid,row['buyer_id'])
    ch['amount_refunded']=333;r=refund(ch,333,uuid.uuid4().hex)
    await process(db,await signed_event(db,ch),pi,ch,[r])
    current=await service.get_order(oid)
    config=dict(current['delivery_config'],s3_presigned_url=url(True),presign_expires_at=(datetime.now(timezone.utc)-timedelta(minutes=55)).isoformat())
    await db.execute(text('update orders set delivery_config=cast(:config as jsonb) where id=:id'),{'config':json.dumps(config),'id':oid});await db.commit()
    app=FastAPI();app.include_router(orders.router)
    async def actor():return SimpleNamespace(id=row['buyer_id'])
    async def database():yield db
    app.dependency_overrides[orders.get_current_user_flexible]=actor
    app.dependency_overrides[orders.get_async_db]=database
    from app.services.rate_limit_service import RateLimitService
    async def redis_script(self):
        async def execute(*args,**kwargs): return [1,50]
        return execute
    monkeypatch.setattr(RateLimitService,'_get_script',redis_script)
    async def http_refresh(buyer=None):
        if buyer is not None:
            async def other_actor():return SimpleNamespace(id=buyer)
            app.dependency_overrides[orders.get_current_user_flexible]=other_actor
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
            return await client.post(f'/orders/{oid}/refresh')
    return SimpleNamespace(row=row,oid=oid,tid=tid,pi=pi,ch=ch,refund=r,version=version,device_id=device_id,frame=frame,dispatch=dispatch,http_refresh=http_refresh,service=service,old_token=old_token,published=published)


@pytest.mark.asyncio
@pytest.mark.parametrize('online',[True,False])
@pytest.mark.parametrize('nested',[True,False])
async def test_f4_s3_http_refresh_decrypted_callback_and_redeem(db,monkeypatch,online,nested):
    from app.services.fulfillment_service import S3_IDENTITY_FIELDS
    from fastapi import HTTPException
    h=await f4_s3(db,monkeypatch,online)
    before=await h.service.get_order(h.oid)
    tx_before=(await db.execute(text('select * from transactions where id=:id'),{'id':h.tid})).one()
    money_before=(await db.execute(text('select * from order_money_states where order_id=:id'),{'id':h.oid})).one()
    result=await h.http_refresh()
    assert result.status_code==200 and result.json()['status']=='refresh_requested',result.text
    pending=await h.service.get_order(h.oid);config=pending['delivery_config']
    outbound=(await db.execute(text('select * from trust_outbound_messages where related_order_id=:id'),{'id':h.oid})).mappings().all()
    assert len(outbound)==len(h.published)==1
    assert outbound[0]['device_id']==config['pending_refresh_device_id']==h.device_id
    assert outbound[0]['payload']['request_id']==config['pending_refresh_request_id']
    assert outbound[0]['payload']['action']=='vai.fulfillment.deliver'
    assert config['pending_refresh_generation']==config['credential_generation']==1
    message=h.frame(nested=nested,request_id=config['pending_refresh_request_id'])
    raw=message['parameters']['parameters']['access_url'] if nested else message['parameters']['access_url']
    response=await h.dispatch(message)
    assert response['success'],response
    after=await h.service.get_order(h.oid)
    assert after['status']=='partially_refunded'
    assert after['delivery_config']['credential_generation']==2
    assert after['delivery_config']['s3_presigned_url']==raw
    assert not any(k.startswith('pending_refresh_') for k in after['delivery_config'])
    assert all(after['delivery_config'][k]==before['delivery_config'][k] for k in S3_IDENTITY_FIELDS)
    for key in ('purchased_version_id','delivery_file_path','delivered_at','completed_at','confirmed_at','downloads_used'):
        assert after[key]==before[key]
    assert (await db.execute(text('select * from transactions where id=:id'),{'id':h.tid})).one()==tx_before
    assert (await db.execute(text('select * from order_money_states where order_id=:id'),{'id':h.oid})).one()==money_before
    assert await db.scalar(text('select status from pending_fulfillments where order_id=:id'),{'id':h.oid})=='completed'
    duplicate=await h.dispatch(message)
    assert duplicate['success'] is False and duplicate['error']=='INVALID_ORDER_STATE'
    assert (await h.service.get_order(h.oid))['delivery_config']==after['delivery_config']
    with pytest.raises(HTTPException):
        await h.service.redeem_download_token(h.oid,h.row['buyer_id'],h.old_token['token'])
    fresh=await h.service.issue_download_token(h.oid,h.row['buyer_id'])
    redeemed=await h.service.redeem_download_token(h.oid,h.row['buyer_id'],fresh['token'])
    assert redeemed==raw


F4_CLOSURES = ['revoked','full','refunded','disputed','cancelled','expired',
               'window','limit','version_unavailable','version_quarantined',
               'version_foreign','object','no_delivery','missing_evidence','foreign_evidence']


@pytest.mark.asyncio
@pytest.mark.parametrize('boundary',['request','callback'])
@pytest.mark.parametrize('closure',F4_CLOSURES)
async def test_f4_request_and_callback_closure_matrix(db,monkeypatch,boundary,closure):
    h=await f4_s3(db,monkeypatch)
    if boundary=='callback':
        requested=await h.http_refresh()
        assert requested.status_code==200 and requested.json()['status']=='refresh_requested'
    if closure=='full':
        h.ch['amount_refunded']=2500
        await process(db,await signed_event(db,h.ch),h.pi,h.ch,[h.refund,refund(h.ch,2167,uuid.uuid4().hex)])
    elif closure=='revoked':
        await h.service.revoke_access(h.oid,None,'F4 independent closure')
    elif closure in ('refunded','disputed','cancelled','expired'):
        await db.execute(text('update transactions set status=:status where id=:id'),{'status':closure,'id':h.tid})
    elif closure=='window':
        await db.execute(text("update orders set access_expires_at=clock_timestamp()-interval '1 second' where id=:id"),{'id':h.oid})
    elif closure=='limit':
        await db.execute(text('update orders set downloads_used=max_downloads where id=:id'),{'id':h.oid})
    elif closure=='version_unavailable':
        await db.execute(text('update orders set purchased_version_id=null where id=:id'),{'id':h.oid})
    elif closure=='version_quarantined':
        await db.execute(text("update listing_versions set status='quarantined' where id=:id"),{'id':h.version})
    elif closure=='version_foreign':
        _,_,_,other_ch=await purchase(db)
        lid=await db.scalar(text('select listing_id from orders where stripe_payment_intent_id=:pi'),{'pi':other_ch['payment_intent']})
        await db.execute(text('update listing_versions set listing_id=:lid where id=:id'),{'lid':lid,'id':h.version})
    elif closure=='object':
        await db.execute(text("update orders set delivery_file_path='v1/foreign.csv' where id=:id"),{'id':h.oid})
    else:
        await db.execute(text('update orders set delivered_at=null,completed_at=null,confirmed_at=null where id=:id'),{'id':h.oid})
        if closure=='no_delivery':
            await db.execute(text("update transactions set status='fulfilling' where id=:id"),{'id':h.tid})
        elif closure=='missing_evidence':
            await db.execute(text('update orders set transaction_id=null where id=:id'),{'id':h.oid})
        else:
            other_oid,other_tid,_,_=await purchase(db)
            await db.execute(text('update orders set transaction_id=:tid where id=:id'),{'tid':other_tid,'id':h.oid})
    await db.commit()
    before=await h.service.get_order(h.oid)
    tx_before=(await db.execute(text('select * from transactions where id=:id'),{'id':h.tid})).one()
    if boundary=='request':
        response=await h.http_refresh()
        assert response.status_code in (400,403,409),response.text
        assert h.published==[]
    else:
        config=before['delivery_config'];message=h.frame(request_id=config['pending_refresh_request_id'])
        response=await h.dispatch(message)
        expected='INVALID_ORDER_STATE' if closure=='full' else ('DELIVERY_OBJECT_BINDING_REJECTED' if closure.startswith('version_') or closure=='object' else 'DELIVERY_REFRESH_ACCESS_REJECTED')
        assert response['success'] is False and response['error']==expected,response
        assert len(h.published)==1
    after=await h.service.get_order(h.oid)
    for key in ('status','delivery_config','downloads_used','delivered_at','completed_at','confirmed_at','refund_amount_cents'):
        assert after[key]==before[key]
    assert (await db.execute(text('select * from transactions where id=:id'),{'id':h.tid})).one()==tx_before


@pytest.mark.asyncio
@pytest.mark.parametrize('wrong',['seller','listing','request','device','generation'])
async def test_f4_callback_tuple_refusals(db,monkeypatch,wrong):
    h=await f4_s3(db,monkeypatch)
    assert (await h.http_refresh()).status_code==200
    before=await h.service.get_order(h.oid)
    frame=h.frame(request_id=before['delivery_config']['pending_refresh_request_id'])
    kwargs={}
    if wrong=='seller':kwargs['seller']=uuid.uuid4()
    if wrong=='device':kwargs['device_name']='foreign-device'
    if wrong=='listing':frame['parameters']['listing_id']=str(uuid.uuid4())
    if wrong=='request':frame['request_id']=str(uuid.uuid4())
    if wrong=='generation':
        config=dict(before['delivery_config'],pending_refresh_generation=999)
        await db.execute(text('update orders set delivery_config=cast(:config as jsonb) where id=:id'),{'id':h.oid,'config':json.dumps(config)})
        await db.commit();before=await h.service.get_order(h.oid)
    response=await h.dispatch(frame,**kwargs)
    expected='AUTHORIZATION_MISMATCH' if wrong in ('seller','listing') else 'INVALID_ORDER_STATE'
    assert response['success'] is False and response['error']==expected
    assert (await h.service.get_order(h.oid))['delivery_config']==before['delivery_config']


@pytest.mark.asyncio
@pytest.mark.parametrize('operation',['complete','token'])
@pytest.mark.parametrize('refund_first',[True,False])
@pytest.mark.parametrize('amount',[333,2500])
async def test_f4_listener_refund_serial_barriers(db,monkeypatch,tmp_path,operation,refund_first,amount):
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from test_order_money_protocol import disposable_url
    from app.services.fulfillment_listener_service import FulfillmentListenerService
    svc,row,tid,pi,ch,msg=await f4_staged(db,monkeypatch,tmp_path)
    completed=await svc.handle_complete(msg,row['seller_id']) if operation=='token' else None
    if completed: assert completed['success']
    ch['amount_refunded']=amount
    r=refund(ch,amount,uuid.uuid4().hex)
    event=await signed_event(db,ch)
    await admit_order_refund(db,event)
    await db.commit()
    ae=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    async def effect(session):
        result=await apply_order_refund_effects(session,event=event,provider_payment=pi,provider_charge=ch,provider_refunds=[r])
        await session.commit()
        return result
    async def access(session):
        listener=FulfillmentListenerService(session)
        if operation=='complete':return await listener.handle_complete(msg,row['seller_id'])
        return await listener.consume_download_token(row['id'],completed['download_token'],row['buyer_id'])
    try:
        async with AsyncSession(ae,expire_on_commit=False) as other,AsyncSession(ae) as observer:
            p1=await db.scalar(text('select pg_backend_pid()'));p2=await other.scalar(text('select pg_backend_pid()'))
            assert p1!=p2
            await db.execute(text("set local lock_timeout='5s'"));await other.execute(text("set local lock_timeout='5s'"))
            await db.execute(text('select id from orders where id=:id for update'),{'id':row['id']})
            task=asyncio.create_task(access(other) if refund_first else effect(other))
            try:
                async with asyncio.timeout(3):
                    while not await observer.scalar(text('select :a=ANY(pg_blocking_pids(:b))'),{'a':p1,'b':p2}):
                        await asyncio.sleep(.01)
                assert not task.done()
                first=await effect(db) if refund_first else await access(db)
                second=await asyncio.wait_for(task,5)
                access_result=second if refund_first else first
                if operation=='complete':
                    if refund_first:
                        assert access_result=={'success':False,'error':'INVALID_ORDER_STATE'}
                    else:
                        assert access_result['success'] and access_result['download_token']
                elif refund_first and amount==2500:
                    assert access_result==(None,'Order access unavailable')
                else:
                    assert access_result[1] is None and access_result[0].download_count==1
            finally:
                if not task.done():task.cancel()
                await asyncio.gather(task,return_exceptions=True)
                await other.rollback()
        final=await db.scalar(text('select status from orders where id=:id'),{'id':row['id']})
        assert final==('refunded' if amount==2500 else 'partially_refunded')
        assert await db.scalar(text('select refund_amount_cents from orders where id=:id'),{'id':row['id']})==amount
        count=await db.scalar(text('select count(*) from fulfillment_download_tokens where order_id=:id'),{'id':row['id']})
        assert count==(0 if operation=='complete' and refund_first else 1)
        if operation=='token':
            used=await db.scalar(text('select download_count from fulfillment_download_tokens where order_id=:id'),{'id':row['id']})
            assert used==(0 if refund_first and amount==2500 else 1)
    finally:await ae.dispose()


@pytest.mark.asyncio
async def test_f4_actual_sync_trigger_does_not_guard_late_delivery(db):
    row,tid,pi,ch,r=await f4_partial(db)
    ch['amount_refunded']=2500
    await process(db,await signed_event(db,ch),pi,ch,[r,refund(ch,2167,uuid.uuid4().hex)])
    assert await db.scalar(text('select status from transactions where id=:id'),{'id':tid})=='refunded'
    # Rollback-only observation of the actual installed trigger, not a replacement.
    await db.execute(text("update orders set status='delivered' where id=:id"),{'id':row['id']})
    assert await db.scalar(text('select status from transactions where id=:id'),{'id':tid})=='delivered'
    await db.rollback()
    assert await db.scalar(text('select status from transactions where id=:id'),{'id':tid})=='refunded'


@pytest.mark.asyncio
@pytest.mark.parametrize('closed',[False,True])
async def test_f4_agent_duplicate_and_mcp_actual_selects(db,monkeypatch,closed):
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock,Mock
    from types import SimpleNamespace
    from app.services.agent_service import AgentService
    from app.services import mcp_marketplace_tools as mcp
    from app.services.redis_service import redis_service
    row,tid,pi,ch,r=await f4_partial(db)
    await db.execute(text("update listings set status='published' where id=:id"),{'id':row['listing_id']})
    if closed:
        await db.execute(text('update orders set revoked=true where id=:id'),{'id':row['id']})
    await db.commit()
    before=await db.scalar(text('select count(*) from orders where buyer_id=:id'),{'id':row['buyer_id']})
    result=await AgentService(db).execute_purchase(row['buyer_id'],row['listing_id'],idempotency_key='f4-'+uuid.uuid4().hex)
    assert result['is_duplicate'] and result['order_id']==str(row['id'])
    assert bool(result['data_url']) is (not closed)
    @asynccontextmanager
    async def database():yield db
    monkeypatch.setattr(mcp,'AsyncSessionLocal',database)
    pipe=Mock();pipe.execute=AsyncMock(return_value=[0,1,1,True])
    monkeypatch.setattr(redis_service,'connect',AsyncMock())
    monkeypatch.setattr(redis_service,'client',SimpleNamespace(pipeline=lambda:pipe))
    monkeypatch.setattr(redis_service,'get',AsyncMock(return_value=None))
    monkeypatch.setattr(redis_service,'set',AsyncMock())
    result=json.loads(await mcp.tool_check_access(listing_id=str(row['listing_id']),user_id=str(row['buyer_id']),key_hash='f4-test'))
    assert result['has_access'] is (not closed),result
    if not closed:assert result['order']['id']==str(row['id'])
    assert await db.scalar(text('select count(*) from orders where buyer_id=:id'),{'id':row['buyer_id']})==before
    assert await db.scalar(text('select count(*) from payments where stripe_payment_intent_id=:pi'),{'pi':pi['id']})==1


@pytest.mark.asyncio
@pytest.mark.parametrize('evidence',['timestamp','delivered','confirmed','settled'])
async def test_f4_get_information_and_reverse_evidence(db,evidence):
    from types import SimpleNamespace
    from app.api.v1.endpoints.orders import get_order_access
    row,tid,pi,ch,r=await f4_partial(db)
    if evidence!='timestamp':
        await db.execute(text('update orders set delivered_at=null,completed_at=null,confirmed_at=null where id=:id'),{'id':row['id']})
        await db.execute(text('update transactions set status=:status where id=:id'),{'id':tid,'status':evidence})
    result=await get_order_access(row['id'],user=SimpleNamespace(id=row['buyer_id']),db=db)
    assert result['is_delivered'] and result['can_download']
    assert await db.scalar(text('select downloads_used from orders where id=:id'),{'id':row['id']})==0
    await db.execute(text("update transactions set status='disputed' where id=:id"),{'id':tid})
    result=await get_order_access(row['id'],user=SimpleNamespace(id=row['buyer_id']),db=db)
    assert result['can_download'] is False and result['access_url'] is None
    assert await db.scalar(text('select downloads_used from orders where id=:id'),{'id':row['id']})==0


@pytest.mark.asyncio
@pytest.mark.parametrize('method',['GET','POST'])
@pytest.mark.parametrize('closed',[False,True])
async def test_f4_raw_http_nonce_audit_single_use(db,monkeypatch,method,closed):
    import base64,hashlib,hmac
    from types import SimpleNamespace
    from fastapi import FastAPI
    from httpx import AsyncClient,ASGITransport
    from app.api.v1.endpoints import orders
    from app.services.raw_download_service import RawDownloadService
    row,tid,pi,ch,r=await f4_partial(db)
    await db.execute(text("update listings set fulfillment_type='file_download',raw_metadata=cast(:raw as jsonb) where id=:id"),{'id':row['listing_id'],'raw':json.dumps({'files':[{'path':'data.csv','sha256':'a'*64}]})})
    if closed:await db.execute(text('update orders set revoked=true where id=:id'),{'id':row['id']})
    await db.commit()
    nonces={}
    from app.core import redis_cache
    async def store(key,value,**kwargs):nonces[key]=value;return True
    async def getdel(key):return nonces.pop(key,None)
    async def redis():return SimpleNamespace(set=store,getdel=getdel)
    monkeypatch.setattr(redis_cache,'get_cache_client',redis)
    before=await f5_access_snapshot(db,row['id'])
    path=f"/orders/{row['id']}/"+('download-token' if method=='POST' else 'download')
    response=await f5_orders_http(db,row['buyer_id'],method,path)
    if closed:
        assert response.status_code==400 and response.json()['detail']=='Order access unavailable'
        assert not nonces
        after=await f5_access_snapshot(db,row['id'])
        for key in before:
            if key!='delivery_audit_log':assert after[key]==before[key]
        assert [v['event_type'] for v in after['delivery_audit_log']]==(['download_requested'] if method=='GET' else [])
        assert await db.scalar(text("select count(*) from delivery_audit_log where order_id=:id and event_type='download_token_generated'"),{'id':row['id']})==0
    else:
        assert response.status_code==200,response.text
        token=response.json()['token']
        assert len(nonces)==1
        svc=RawDownloadService(db)
        valid,error=await svc.validate_download_token(token)
        assert error is None and valid['order_id']==str(row['id'])
        repeated,error=await svc.validate_download_token(token)
        assert repeated is None and error=='Token already used'
        assert await db.scalar(text("select count(*) from delivery_audit_log where order_id=:id and event_type='download_token_generated'"),{'id':row['id']})==1


@pytest.mark.asyncio
@pytest.mark.parametrize('access',['available','expired','zero','exhausted'])
@pytest.mark.parametrize('delivery',['partial','delivered','completed'])
async def test_f4_nondevice_s3_get_real_builder(db,monkeypatch,access,delivery):
    from types import SimpleNamespace
    from app.api.v1.endpoints.orders import get_order_access
    from app.services import order_service
    if delivery=='partial':
        row,tid,pi,ch,r=await f4_partial(db)
    else:
        oid,tid,pi,ch=await purchase(db)
        await db.execute(text("update orders set status=:status,delivered_at=clock_timestamp(),access_expires_at=clock_timestamp()+interval '1 day' where id=:id"),{'status':delivery,'id':oid})
        row=dict((await db.execute(text('select * from orders where id=:id'),{'id':oid})).mappings().one())
    if access=='expired':
        await db.execute(text("update orders set access_expires_at=clock_timestamp()-interval '1 second' where id=:id"),{'id':row['id']})
    elif access=='zero':
        await db.execute(text('update orders set max_downloads=0 where id=:id'),{'id':row['id']})
    elif access=='exhausted':
        await db.execute(text('update orders set max_downloads=3,downloads_used=3 where id=:id'),{'id':row['id']})
    serial=uuid.uuid4();version=uuid.uuid4()
    await db.execute(text("insert into serials (id,serial,user_id,status,token_prefix,token_last4,expires_at) values (:id,:serial,:user,'activated','test','test',clock_timestamp()+interval '1 day')"),{'id':serial,'serial':'VZ-'+uuid.uuid4().hex[:8]+'-'+uuid.uuid4().hex[:8],'user':row['seller_id']})
    await db.execute(text("insert into listing_versions (id,listing_id,version_label,prefix,published_at,status,object_count,total_size_bytes,manifest_hash) values (:id,:listing,'v1','v1/',clock_timestamp(),'active',1,123,repeat('a',64))"),{'id':version,'listing':row['listing_id']})
    await db.execute(text('update orders set purchased_version_id=:version where id=:id'),{'version':version,'id':row['id']})
    raw={'s3_connection':{'bucket':'synthetic','role_arn':'arn:aws:iam::123456789012:role/test','serial_id':str(serial)},'files':[{'path':'s3://synthetic/v1/data.csv'}]}
    await db.execute(text('update listings set raw_metadata=cast(:raw as jsonb) where id=:id'),{'id':row['listing_id'],'raw':json.dumps(raw)})
    calls=[]
    def assume(**kwargs):calls.append(('assume',kwargs));return {'access_key_id':'test','secret_access_key':'test','session_token':'test'}
    def presign(credentials,**kwargs):calls.append(('presign',kwargs));return 'https://example.invalid/signed'
    monkeypatch.setattr(order_service,'assume_seller_role',assume)
    monkeypatch.setattr(order_service,'generate_presigned_url',presign)
    from app.models.user import User
    user=await db.get(User,row['buyer_id'])
    before=await f5_access_snapshot(db,row['id'])
    http=await f5_orders_http(db,user.id,'GET',f"/orders/{row['id']}/access")
    assert http.status_code==200,http.text
    response=http.json()
    if access=='available':
        assert response['can_download']
        assert response['s3_download_urls'][0]['presigned_url']=='https://example.invalid/signed'
        assert [v[0] for v in calls]==['assume','presign']
        assert calls[1][1]['key']=='v1/data.csv' and calls[1][1]['bucket']=='synthetic'
    else:
        assert calls==[]
        assert not response['can_download'] and not response.get('s3_download_urls')
        assert not response.get('access_url')
        if access in ('zero','exhausted'):assert response['downloads_remaining']==0
    assert await f5_access_snapshot(db,row['id'])==before


@pytest.mark.asyncio
@pytest.mark.parametrize('parent',['payment','journal'])
@pytest.mark.parametrize('parent_first',[True,False])
async def test_f4_actual_legacy_credit_nullable_fk_barriers(db,parent,parent_first):
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from test_order_money_protocol import disposable_url
    from app.services.billing_service import BillingService
    row,tid,pi,ch,r=await f4_partial(db)
    payment=(await db.execute(select(Payment).where(Payment.stripe_payment_intent_id==pi['id']))).scalar_one()
    svc=BillingService()
    credits=await svc._get_or_create_api_credits(row['buyer_id'],payment.entity_id,db)
    assert credits.last_topup_payment_id is None and credits.last_journal_entry_id is None
    await db.commit()
    table,pk=('payments',payment.id) if parent=='payment' else ('journal_entries',payment.journal_entry_id)
    async def parent_lock(session):return await session.scalar(text(f'select id from {table} where id=:id for update'),{'id':pk})
    async def assign(session):
        return await svc._record_credit_topup(row['buyer_id'],payment.entity_id,payment,payment.journal_entry_id,73,None,session)
    ae=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    try:
        async with AsyncSession(ae,expire_on_commit=False) as other,AsyncSession(ae) as observer:
            p1=await db.scalar(text('select pg_backend_pid()'));p2=await other.scalar(text('select pg_backend_pid()'))
            await other.execute(text("set local lock_timeout='5s'"))
            if parent_first:await parent_lock(db)
            else:await assign(db)
            task=asyncio.create_task(assign(other) if parent_first else parent_lock(other))
            try:
                async with asyncio.timeout(3):
                    while not await observer.scalar(text('select :a=ANY(pg_blocking_pids(:b))'),{'a':p1,'b':p2}):
                        await asyncio.sleep(.01)
                assert not task.done()
                await db.commit();await asyncio.wait_for(task,5);await other.commit()
            finally:
                if not task.done():task.cancel()
                await asyncio.gather(task,return_exceptions=True)
        actual=(await db.execute(text('select last_topup_payment_id,last_journal_entry_id,balance_cents from api_credits where user_id=:id'),{'id':row['buyer_id']})).one()
        assert tuple(actual)==(payment.id,payment.journal_entry_id,73)
    finally:await ae.dispose()


@pytest.mark.asyncio
async def test_f4_wrong_buyer_http_refresh(db,monkeypatch):
    h=await f4_s3(db,monkeypatch)
    before=await h.service.get_order(h.oid)
    result=await h.http_refresh(uuid.uuid4())
    assert result.status_code==403
    assert not h.published
    assert (await h.service.get_order(h.oid))['delivery_config']==before['delivery_config']


@pytest.mark.asyncio
async def test_f4_normal_additional_partial_between_request_callback(db,monkeypatch):
    h=await f4_s3(db,monkeypatch)
    assert (await h.http_refresh()).json()['status']=='refresh_requested'
    h.ch['amount_refunded']=666
    await process(db,await signed_event(db,h.ch),h.pi,h.ch,[h.refund,refund(h.ch,333,uuid.uuid4().hex)])
    before=await h.service.get_order(h.oid)
    money=(await db.execute(text('select * from order_money_states where order_id=:id'),{'id':h.oid})).one()
    message=h.frame(request_id=before['delivery_config']['pending_refresh_request_id'])
    assert (await h.dispatch(message))['success']
    after=await h.service.get_order(h.oid)
    assert after['status']=='partially_refunded' and after['refund_amount_cents']==666
    assert after['delivery_config']['credential_generation']==2
    assert (await db.execute(text('select * from order_money_states where order_id=:id'),{'id':h.oid})).one()==money


@pytest.mark.asyncio
@pytest.mark.parametrize('surface',['data','request','artifact'])
@pytest.mark.parametrize('closed',[True,False])
async def test_f4_actual_agent_routes_oauth_and_broker(db,monkeypatch,surface,closed):
    from starlette.requests import Request
    from fastapi import HTTPException
    from app.api.v1.agent.router import get_order_data,request_order_access,get_order_artifact
    from app.services.oauth_service import OAuthService
    from app.services.fulfillment_broker import FulfillmentBroker
    h=await f4_s3(db,monkeypatch)
    assert (await h.http_refresh()).json()['status']=='refresh_requested'
    pending=await h.service.get_order(h.oid)
    assert (await h.dispatch(h.frame(request_id=pending['delivery_config']['pending_refresh_request_id'])))['success']
    row,tid,pi,ch=h.row,h.tid,h.pi,h.ch
    if closed:
        await db.execute(text('update orders set revoked=true where id=:id'),{'id':row['id']})
    await db.commit()
    before=await f5_access_snapshot(db,row['id'])
    token=OAuthService(db)._create_access_token(str(row['buyer_id']),'f4-test','marketplace:read')
    request=Request({'type':'http','headers':[(b'authorization',('Bearer '+token).encode())]})
    async def call():
        if surface=='data':return await get_order_data(row['id'],request,'csv',db)
        if surface=='request':return await request_order_access(request,row['id'],db,FulfillmentBroker(db))
        return await get_order_artifact(request,row['id'],db,FulfillmentBroker(db))
    if closed:
        with pytest.raises(HTTPException) as refused:await call()
        assert refused.value.status_code==403
        assert await f5_access_snapshot(db,row['id'])==before
    else:
        result=await call()
        if surface=='request':assert result.status=='already_available' and result.access_token
        else:assert result.download_url
    assert await db.scalar(text('select count(*) from orders where buyer_id=:b and listing_id=:l'),{'b':row['buyer_id'],'l':row['listing_id']})==1
    assert await db.scalar(text('select count(*) from payments where stripe_payment_intent_id=:pi'),{'pi':pi['id']})==1


@pytest.mark.asyncio
@pytest.mark.parametrize('boundary',['issue','file'])
@pytest.mark.parametrize('closure',['revoked','undelivered','refunded','disputed','cancelled','expired'])
async def test_f4_workspace_existing_shared_guard_refusal(db,monkeypatch,boundary,closure):
    from dataclasses import replace
    from app.core.seller_workspace_config import SellerWorkspaceConfig
    from app.core.config import settings
    from app.services.seller_workspace_delivery import SellerWorkspaceDeliveryService
    from fastapi import HTTPException
    row,tid,pi,ch,r=await f4_partial(db)
    if closure=='revoked':
        await db.execute(text('update orders set revoked=true where id=:id'),{'id':row['id']})
    elif closure=='undelivered':
        await db.execute(text('update orders set delivered_at=null,completed_at=null,confirmed_at=null where id=:id'),{'id':row['id']})
        await db.execute(text("update transactions set status='fulfilling' where id=:id"),{'id':tid})
    else:await db.execute(text('update transactions set status=:status where id=:id'),{'id':tid,'status':closure})
    await db.commit()
    for key in ('GCP_PROJECT_ID','GCP_KMS_LOCATION','GCP_KMS_KEYRING','GCP_KMS_ENCRYPTION_KEY_NAME'):
        monkeypatch.setattr(settings,key,'f4-test-only')
    config=replace(SellerWorkspaceConfig.from_environment({}),enabled=True,aws_connect_enabled=True,aws_delivery_enabled=True,aws_principal_arn='arn:aws:iam::123456789012:root')
    # No authority/provider fixture is needed: the real shared guard must refuse
    # before any source authority or provider can be consulted.
    svc=SellerWorkspaceDeliveryService(db,config,None)
    with pytest.raises(HTTPException) as refused:
        if boundary=='issue':await svc.issue(row['id'],row['buyer_id'],request_id=uuid.uuid4())
        else:await svc.file(row['id'],row['buyer_id'],uuid.uuid4(),0)
    assert refused.value.status_code==(400 if closure=='undelivered' else 403)
    assert await db.scalar(text('select downloads_used from orders where id=:id'),{'id':row['id']})==0
    assert await db.scalar(text('select count(*) from seller_download_sessions where order_id=:id'),{'id':row['id']})==0


async def f5_access_snapshot(db,oid):
    """Persisted access and money side effects, including full event payloads."""
    result={}
    for table,column in [('orders','id'),('transactions','order_id'),
                         ('order_money_states','order_id'),('refunds','order_id'),
                         ('order_events','order_id'),('download_tokens','order_id'),
                         ('delivery_audit_log','order_id'),('fulfillment_download_tokens','order_id'),
                         ('seller_download_sessions','order_id')]:
        result[table]=(await db.execute(text(f'SELECT to_jsonb(t) FROM {table} t WHERE {column}=:id ORDER BY to_jsonb(t)::text'),{'id':oid})).scalars().all()
    return result


@pytest.mark.asyncio
@pytest.mark.parametrize('case',['missing_header','malformed_bearer','empty_bearer','invalid_token','invalid_signature','invalid_type','absent_subject','malformed_subject','nonuuid_subject','unknown_user','valid_user'])
async def test_f5_actual_oauth_loader_signed_inputs(db,case):
    from starlette.requests import Request
    from sqlalchemy import event,inspect
    from app.api.v1.agent.router import get_oauth_user_from_request
    from app.services.oauth_service import OAuthService,jwt
    from app.core.config import settings
    from app.models.user import User
    oid,tid,pi,ch=await purchase(db)
    buyer=await db.scalar(text('select buyer_id from orders where id=:id'),{'id':oid})
    service=OAuthService(db)
    token=service._create_access_token(str(buyer),'f5-test','marketplace:read')
    payload=service.verify_access_token(token)
    if case=='absent_subject':payload.pop('sub')
    elif case=='malformed_subject':payload['sub']=''
    elif case=='nonuuid_subject':payload['sub']='not-a-uuid'
    elif case=='unknown_user':payload['sub']=str(uuid.uuid4())
    elif case=='invalid_type':payload['type']='refresh_token'
    token=jwt.encode(payload,settings.SECRET_KEY if case!='invalid_signature' else 'invalid-signature-test-secret',algorithm=settings.ALGORITHM)
    if case=='invalid_token':token='invalid'
    header='Bearer '+token
    if case=='malformed_bearer':header='Basic '+token
    elif case=='empty_bearer':header='Bearer '
    request=Request({'type':'http','headers':[] if case=='missing_header' else [(b'authorization',header.encode())]})
    statements=[]
    connection=await db.connection()
    def observe(conn,cursor,statement,parameters,context,executemany):statements.append(statement)
    event.listen(connection.sync_connection,'before_cursor_execute',observe)
    try:result=await get_oauth_user_from_request(request,db)
    finally:event.remove(connection.sync_connection,'before_cursor_execute',observe)
    if case=='valid_user':
        assert isinstance(result,User) and result.id==buyer
        assert inspect(result).persistent and inspect(result).session is db.sync_session
    else:assert result is None
    if case in ('valid_user','unknown_user'):assert len(statements)==1
    else:assert statements==[]


@pytest.mark.asyncio
async def test_f5_workspace_positive_partial_issue_file(db,monkeypatch):
    from dataclasses import replace
    from datetime import timedelta
    from types import SimpleNamespace
    from unittest.mock import AsyncMock,Mock
    from app.core.config import settings
    from app.core.seller_workspace_config import SellerWorkspaceConfig
    from app.models.seller_workspace import CloudConnection
    from app.schemas.seller_listing_source import SourceSave
    from app.schemas.seller_listing_draft import ListingDraftSave
    from app.schemas.seller_listing_approval import ListingApprovalRequest
    from app.schemas.seller_listing_publication import ListingPublishRequest
    from app.services.seller_listing_source import SellerListingSourceService
    from app.services.seller_listing_draft import SellerListingDraftService
    from app.services.seller_listing_review import SellerListingReviewService
    from app.services.seller_listing_approval import SellerListingApprovalService
    from app.services.seller_listing_publication import SellerListingPublicationService
    from app.services.seller_workspace_encryption import SellerWorkspaceEnvelopeEncryption
    from app.services.seller_workspace_delivery import SellerWorkspaceDeliveryService
    from app.services.seller_workspace_delivery_aws import DirectObjectGrant
    for key in ('GCP_PROJECT_ID','GCP_KMS_LOCATION','GCP_KMS_KEYRING','GCP_KMS_ENCRYPTION_KEY_NAME'):
        monkeypatch.setattr(settings,key,'f5-test-only')
    config=replace(SellerWorkspaceConfig.from_environment({}),enabled=True,aws_connect_enabled=True,
        aws_discovery_enabled=True,aws_publish_enabled=True,aws_delivery_enabled=True,
        aws_principal_arn='arn:aws:iam::123456789012:root')
    class KMSDouble:
        async def wrap_for_platform(self,plaintext,**kwargs):return b'test-only-'+plaintext
        async def decrypt_from_device(self,ciphertext,**kwargs):
            assert ciphertext.startswith(b'test-only-')
            return ciphertext[len(b'test-only-'):]
    encryption=SellerWorkspaceEnvelopeEncryption(kms=KMSDouble())
    oid,tid,pi,ch=await purchase(db)
    row=dict((await db.execute(text('select * from orders where id=:id'),{'id':oid})).mappings().one())
    connection=CloudConnection(id=uuid.uuid4(),seller_id=row['seller_id'],provider='aws',status='verified',
        version=1,provider_account_id='123456789012',role_arn='arn:aws:iam::123456789012:role/test',
        bucket='synthetic',prefix='data',region='eu-west-1',authorization_expires_at=datetime.now(timezone.utc)+timedelta(days=1))
    db.add(connection);await db.flush()
    credential=await encryption.encrypt_external_id(seller_id=row['seller_id'],connection_id=connection.id,
        external_id='test-only-external-id',purpose='aws_external_id',expires_at=connection.authorization_expires_at)
    credential.activated_at=datetime.now(timezone.utc)
    db.add(credential);await db.flush()
    connection.active_credential_id=credential.id
    await db.commit()
    aws=Mock()
    aws.list_objects.return_value={'Contents':[{'Key':'data/synthetic.csv','ETag':'synthetic-etag','Size':42}]}
    sources=SellerListingSourceService(db,config,encryption=encryption,
        discovery=SimpleNamespace(_connection_adapter=AsyncMock(return_value=aws)))
    await sources.save(row['seller_id'],SourceSave(request_id=uuid.uuid4(),expected_version=0,content={
        'connection_id':connection.id,'connection_version':1,'objects':[{'key':'data/synthetic.csv','etag':'synthetic-etag','size':42}]}))
    await SellerListingDraftService(db).save(row['seller_id'],ListingDraftSave(request_id=uuid.uuid4(),expected_version=0,
        content={'brief':'Test data','title':'Retail','description':'Weekly totals','category':'Retail','tags':'retail','price':'25.00','license':'Research'}))
    review=await SellerListingReviewService(db).prepare(row['seller_id'])
    approval=await SellerListingApprovalService(db,sources).approve(row['seller_id'],ListingApprovalRequest(
        request_id=uuid.uuid4(),review_hash=review['review_hash'],render_hash=review['render_hash'],sample_decision='none',
        confirmation_version=review['confirmation_version'],ownership_confirmed=True,privacy_confirmed=True,
        price_license_confirmed=True,public_disclosure_confirmed=True))
    published=await SellerListingPublicationService(db,sources).publish(row['seller_id'],ListingPublishRequest(
        request_id=uuid.uuid4(),approval_id=approval.id,review_hash=review['review_hash'],render_hash=review['render_hash']))
    await db.execute(text("update orders set listing_id=:listing,purchased_version_id=:version,delivered_at=clock_timestamp(),access_expires_at=clock_timestamp()+interval '1 day' where id=:id"),
        {'id':oid,'listing':published.listing_id,'version':published.listing_version_id})
    await db.execute(text('update transactions set listing_id=:listing where id=:id'),{'id':tid,'listing':published.listing_id})
    ch['amount_refunded']=333
    await process(db,await signed_event(db,ch),pi,ch,[refund(ch,333,uuid.uuid4().hex)])
    calls=[]
    def provider(**kwargs):
        calls.append(kwargs)
        return DirectObjectGrant(url='https://synthetic.s3.eu-west-1.amazonaws.com/data/synthetic.csv?test-only',
            headers={'If-Match':'"synthetic-etag"'},expires_at=datetime.now(timezone.utc)+timedelta(seconds=60),filename='synthetic.csv',size=42)
    service=SellerWorkspaceDeliveryService(db,config,sources,provider=provider)
    before=await f5_access_snapshot(db,oid)
    request_id=uuid.uuid4()
    result=await service.issue(oid,row['buyer_id'],request_id=request_id)
    assert result['delivery_type']=='workspace_direct' and result['download_number']==1
    grant=await service.file(oid,row['buyer_id'],uuid.UUID(result['session_id']),0)
    assert grant['url'].endswith('?test-only') and grant['headers']=={'If-Match':'"synthetic-etag"'}
    assert len(calls)==1 and calls[0]['external_id']=='test-only-external-id'
    assert calls[0]['item'].key=='data/synthetic.csv' and calls[0]['bucket']=='synthetic'
    assert await service.issue(oid,row['buyer_id'],request_id=request_id)==result
    assert await service.file(oid,row['buyer_id'],uuid.UUID(result['session_id']),0)==grant
    assert len(calls)==1
    after=await f5_access_snapshot(db,oid)
    for key in ('transactions','order_money_states','refunds'):assert after[key]==before[key]
    for key in ('status','delivered_at','completed_at','confirmed_at','refund_amount_cents'):assert after['orders'][0][key]==before['orders'][0][key]
    assert after['orders'][0]['downloads_used']==1
    assert len(after['seller_download_sessions'])==1
    assert await db.scalar(text('select count(*) from seller_download_file_grants where session_id=:id'),{'id':uuid.UUID(result['session_id'])})==1


async def f5_orders_http(db,buyer,method,path,**kwargs):
    from fastapi import FastAPI
    from httpx import AsyncClient,ASGITransport
    from app.api.v1.endpoints import orders
    from app.core.security import create_access_token
    app=FastAPI();app.include_router(orders.router)
    async def database():yield db
    app.dependency_overrides[orders.get_async_db]=database
    token=create_access_token({'sub':str(buyer)})
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        return await client.request(method,path,headers={'Authorization':'Bearer '+token},**kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize('case',['available','expired','zero','exhausted','closed'])
async def test_f5_device_s3_get_informational(db,monkeypatch,case):
    h=await f4_s3(db,monkeypatch)
    if case=='expired':await db.execute(text("update orders set access_expires_at=clock_timestamp()-interval '1 second' where id=:id"),{'id':h.oid})
    elif case=='zero':await db.execute(text('update orders set max_downloads=0 where id=:id'),{'id':h.oid})
    elif case=='exhausted':await db.execute(text('update orders set downloads_used=max_downloads where id=:id'),{'id':h.oid})
    elif case=='closed':await db.execute(text('update orders set revoked=true where id=:id'),{'id':h.oid})
    await db.commit()
    before=await f5_access_snapshot(db,h.oid)
    result=await f5_orders_http(db,h.row['buyer_id'],'GET',f'/orders/{h.oid}/access')
    assert result.status_code==200,result.text
    body=result.json()
    assert body['can_download'] is (case=='available')
    assert not body.get('s3_download_urls') and not body.get('s3_presigned_url')
    assert 'X-Amz-Signature' not in result.text
    assert await f5_access_snapshot(db,h.oid)==before
    assert not h.published


@pytest.mark.asyncio
@pytest.mark.parametrize('method',['GET','POST'])
@pytest.mark.parametrize('state',['partial','paid','in_escrow','pending_delivery','delivered','completed'])
@pytest.mark.parametrize('files_case',['single','multi_selected','multi_missing','foreign_path','outside_version','workspace'])
async def test_f5_raw_source_signature_nonce_audit(db,monkeypatch,method,state,files_case):
    import hashlib,hmac
    from types import SimpleNamespace
    from app.core import redis_cache
    from app.core.config import settings
    from app.services.raw_download_service import RawDownloadService
    if state=='partial':row,tid,pi,ch,r=await f4_partial(db)
    else:
        oid,tid,pi,ch=await purchase(db)
        await db.execute(text('update orders set status=:status where id=:id'),{'status':state,'id':oid})
        row=dict((await db.execute(text('select * from orders where id=:id'),{'id':oid})).mappings().one())
    version=uuid.uuid4()
    await db.execute(text("insert into listing_versions (id,listing_id,version_label,prefix,published_at,status,object_count,total_size_bytes,manifest_hash) values (:id,:listing,'v1','v1/',clock_timestamp(),'active',2,84,repeat('a',64))"),{'id':version,'listing':row['listing_id']})
    await db.execute(text('update orders set purchased_version_id=:version where id=:id'),{'version':version,'id':row['id']})
    files=[{'path':'v1/data.csv','checksum_sha256':'a'*64}]
    if files_case.startswith('multi'):files.append({'path':'v1/second.csv','checksum_sha256':'b'*64})
    if files_case=='outside_version':files[0]['path']='v2/foreign.csv'
    await db.execute(text("update listings set fulfillment_type='file_download',raw_metadata=cast(:raw as jsonb),source_delivery=cast(:source as jsonb) where id=:id"),
        {'id':row['listing_id'],'raw':json.dumps({'files':files}),'source':json.dumps({'authority_kind':'workspace_connection'} if files_case=='workspace' else {})})
    await db.commit()
    nonces={};calls=[]
    async def store(key,value,**kwargs):
        calls.append(('set',key,kwargs));nonces[key]=value;return True
    async def getdel(key):calls.append(('getdel',key));return nonces.pop(key,None)
    async def redis():return SimpleNamespace(set=store,getdel=getdel)
    monkeypatch.setattr(redis_cache,'get_cache_client',redis)
    before=await f5_access_snapshot(db,row['id'])
    path=f"/orders/{row['id']}/"+('download' if method=='GET' else 'download-token')
    params={}
    if method=='POST' and files_case=='multi_selected':params['file_path']='v1/second.csv'
    if method=='POST' and files_case=='foreign_path':params['file_path']='v1/absent.csv'
    response=await f5_orders_http(db,row['buyer_id'],method,path,params=params)
    success=(files_case=='single' or (method=='POST' and files_case=='multi_selected') or (method=='GET' and files_case=='foreign_path'))
    if success:
        assert response.status_code==200,response.text
        token=response.json()['token'];payload=json.loads(token);signature=payload.pop('sig')
        assert signature==hmac.new((settings.AUDIT_SIGNING_KEY or settings.SECRET_KEY).encode(),json.dumps(payload,sort_keys=True).encode(),hashlib.sha256).hexdigest()
        assert payload['order_id']==str(row['id']) and payload['buyer_id']==str(row['buyer_id'])
        selected='v1/second.csv' if files_case=='multi_selected' else 'v1/data.csv'
        assert payload['file_path']==selected and payload['file_hash']==('b' if files_case=='multi_selected' else 'a')*64
        assert len(nonces)==1 and calls==[('set','raw_dl_nonce:'+payload['nonce'],{'ex':300})]
        valid,error=await RawDownloadService(db).validate_download_token(token)
        assert error is None and valid['nonce']==payload['nonce']
        repeated,error=await RawDownloadService(db).validate_download_token(token)
        assert repeated is None and error=='Token already used' and not nonces
    else:
        expected=422 if method=='POST' and files_case in ('multi_missing','foreign_path') else 403 if files_case=='outside_version' or (files_case=='workspace' and method=='GET') else 400
        assert response.status_code==expected,response.text
        assert 'token' not in response.json() and not nonces and calls==[]
    after=await f5_access_snapshot(db,row['id'])
    for key in ('orders','transactions','order_money_states','refunds','order_events','download_tokens','fulfillment_download_tokens','seller_download_sessions'):assert after[key]==before[key]
    events=[v['event_type'] for v in after['delivery_audit_log']]
    assert events.count('download_token_generated')==int(success)
    assert events.count('download_requested')==int(method=='GET' and not files_case.startswith('multi'))


@pytest.mark.asyncio
@pytest.mark.parametrize('closed',[False,True])
async def test_f5_mcp_actual_initiate_duplicate_preserves_purchase(db,monkeypatch,closed):
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock,Mock
    from types import SimpleNamespace
    from app.services import mcp_marketplace_tools as mcp
    from app.services.redis_service import redis_service
    from app.services.stripe_connect_service import stripe_connect_service
    row,tid,pi,ch,r=await f4_partial(db)
    await db.execute(text("update listings set status='published' where id=:id"),{'id':row['listing_id']})
    party=uuid.uuid4()
    await db.execute(text("insert into party (id,party_type) values (:id,'person')"),{'id':party})
    for provider,external in [('auth_user',str(row['seller_id'])),('stripe_connect','acct_'+uuid.uuid4().hex)]:
        await db.execute(text('insert into party_identity (party_id,provider,external_id) values (:party,:provider,:external)'),{'party':party,'provider':provider,'external':external})
    if closed:await db.execute(text('update orders set revoked=true where id=:id'),{'id':row['id']})
    await db.commit()
    @asynccontextmanager
    async def database():yield db
    monkeypatch.setattr(mcp,'AsyncSessionLocal',database)
    pipe=Mock();pipe.execute=AsyncMock(return_value=[0,1,1,True])
    monkeypatch.setattr(redis_service,'connect',AsyncMock())
    monkeypatch.setattr(redis_service,'client',SimpleNamespace(pipeline=lambda:pipe))
    monkeypatch.setattr(redis_service,'get',AsyncMock(return_value=None))
    monkeypatch.setattr(redis_service,'set',AsyncMock())
    account=AsyncMock(return_value=SimpleNamespace(payouts_enabled=True,charges_enabled=True,details_submitted=True))
    monkeypatch.setattr(stripe_connect_service,'get_account',account)
    before=await f5_access_snapshot(db,row['id'])
    result=json.loads(await mcp.tool_initiate_purchase(str(row['listing_id']),str(uuid.uuid4()),
        user_id=str(row['buyer_id']),key_hash='f5-test',api_key_id=str(uuid.uuid4())))
    assert result['error']['code']=='VALIDATION_ERROR',result
    assert result['error']['message']=='Active order already exists for this listing'
    assert account.await_count==1
    assert await f5_access_snapshot(db,row['id'])==before
    assert await db.scalar(text('select count(*) from orders where buyer_id=:b and listing_id=:l'),{'b':row['buyer_id'],'l':row['listing_id']})==1
    assert await db.scalar(text('select count(*) from payments where stripe_payment_intent_id=:pi'),{'pi':pi['id']})==1


async def f5_parent_barrier(db,perform,table,parent_id,parent_first):
    """Real service commits release savepoints; owned outer tx retains FK locks."""
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from test_order_money_protocol import disposable_url
    engine=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    await db.commit()
    async with engine.connect() as connection:
        outer=await connection.begin()
        async with AsyncSession(bind=connection,expire_on_commit=False,join_transaction_mode='create_savepoint') as product,AsyncSession(engine) as parent:
            product_pid=await product.scalar(text('select pg_backend_pid()'))
            parent_pid=await parent.scalar(text('select pg_backend_pid()'))
            await parent.execute(text("set local lock_timeout='5s'"))
            await product.execute(text("set local lock_timeout='5s'"))
            async def lock():return await parent.scalar(text(f'select id from {table} where id=:id for update'),{'id':parent_id})
            if parent_first:
                assert await lock()==parent_id
                task=asyncio.create_task(perform(product))
                blocker,waiter=parent_pid,product_pid
            else:
                await perform(product);await product.flush()
                task=asyncio.create_task(lock())
                blocker,waiter=product_pid,parent_pid
            try:
                async with asyncio.timeout(3):
                    while not await db.scalar(text('select :a=ANY(pg_blocking_pids(:b))'),{'a':blocker,'b':waiter}):await asyncio.sleep(.01)
                assert not task.done()
                if parent_first:await parent.commit()
                else:await product.commit();await outer.commit()
                await asyncio.wait_for(task,4)
                await product.commit();await parent.commit()
                if outer.is_active:await outer.commit()
            finally:
                if not task.done():task.cancel()
                await asyncio.gather(task,return_exceptions=True)
                if outer.is_active:await outer.rollback()
    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize('edge',['revoked_by','dispute_resolved_by','credit_entity','event_entity'])
@pytest.mark.parametrize('parent_first',[True,False])
async def test_f5_actual_nullable_legacy_assignments(db,edge,parent_first):
    from app.services.order_service import OrderService
    from app.services.billing_service import BillingService
    from app.models.gateway import APICredits
    from app.schemas.order import DisputeResolveRequest
    oid,tid,pi,ch=await purchase(db)
    buyer=await db.scalar(text('select buyer_id from orders where id=:id'),{'id':oid})
    entity=await merchant(db)
    svc=BillingService()
    event={'id':'evt_'+uuid.uuid4().hex,'type':'checkout.session.completed','data':{'object':{'metadata':{}}}}
    if edge=='credit_entity':
        db.add(APICredits(user_id=buyer,entity_id=None));await db.flush()
    elif edge=='event_entity':
        await db.execute(text("insert into stripe_events (stripe_event_id,event_type,payload_json,signature_valid) values (:id,:type,cast(:payload as jsonb),true)"),{'id':event['id'],'type':event['type'],'payload':json.dumps(event)})
    elif edge=='dispute_resolved_by':
        await db.execute(text("update orders set status='disputed' where id=:id"),{'id':oid})
    await db.commit()
    async def perform(session):
        if edge=='revoked_by':await OrderService(session).revoke_access(oid,buyer,'F5 FK barrier',commit=False)
        elif edge=='dispute_resolved_by':await OrderService(session).resolve_dispute(oid,buyer,DisputeResolveRequest(resolution='seller_wins',notes='F5 FK barrier'))
        elif edge=='credit_entity':await svc._get_or_create_api_credits(buyer,entity,session);await session.flush()
        else:await svc.handle_stripe_event(event,session)
    await f5_parent_barrier(db,perform,'users' if edge in ('revoked_by','dispute_resolved_by') else 'billing_entities',
        buyer if edge in ('revoked_by','dispute_resolved_by') else entity,parent_first)
    if edge in ('revoked_by','dispute_resolved_by'):
        assert await db.scalar(text(f'select {edge} from orders where id=:id'),{'id':oid})==buyer
    elif edge=='credit_entity':assert await db.scalar(text('select entity_id from api_credits where user_id=:id'),{'id':buyer})==entity
    else:assert await db.scalar(text('select entity_id from stripe_events where stripe_event_id=:id'),{'id':event['id']})==entity


@pytest.mark.asyncio
@pytest.mark.parametrize('edge',['seller_id','listing_id','data_request_id','party_id','api_key_id','order_transaction_id','purchased_version_id'])
@pytest.mark.parametrize('parent_first',[True,False])
async def test_f5_actual_creation_fk_barriers(db,monkeypatch,edge,parent_first):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from app.services.transaction_service import TransactionService
    from app.services.order_service import OrderService
    from app.services.stripe_connect_service import stripe_connect_service
    from app.models.data_request import DataRequest
    oid,tid,pi,ch=await purchase(db)
    row=dict((await db.execute(text('select * from orders where id=:id'),{'id':oid})).mappings().one())
    await db.execute(text("update listings set status='published' where id=:id"),{'id':row['listing_id']})
    party,key,version,request_id=uuid.uuid4(),uuid.uuid4(),uuid.uuid4(),uuid.uuid4()
    await db.execute(text("insert into party (id,party_type) values (:id,'organization')"),{'id':party})
    await db.execute(text("insert into party_identity (party_id,provider,external_id,is_primary) values (:id,'auth_user',:user,true)"),{'id':party,'user':str(row['buyer_id'])})
    await db.execute(text("insert into agent_api_keys (id,org_id,name,key_hash,prefix,spend_used) values (:id,:org,'F5 creation',:hash,'f5',0)"),{'id':key,'org':party,'hash':uuid.uuid4().hex*2})
    seller_party=uuid.uuid4()
    await db.execute(text("insert into party (id,party_type) values (:id,'person')"),{'id':seller_party})
    for provider,external in [('auth_user',str(row['seller_id'])),('stripe_connect','acct_'+uuid.uuid4().hex)]:
        await db.execute(text('insert into party_identity (party_id,provider,external_id) values (:party,:provider,:external)'),{'party':seller_party,'provider':provider,'external':external})
    monkeypatch.setattr(stripe_connect_service,'get_account',AsyncMock(return_value=SimpleNamespace(payouts_enabled=True,details_submitted=True,charges_enabled=True)))
    db.add(DataRequest(id=request_id,buyer_id=row['buyer_id'],buyer_pseudonym='test',title='Test',description='Test',slug=uuid.uuid4().hex))
    await db.execute(text("insert into listing_versions (id,listing_id,version_label,prefix,published_at,status,object_count,total_size_bytes,manifest_hash) values (:id,:listing,'v1','v1/',clock_timestamp(),'active',1,42,repeat('a',64))"),{'id':version,'listing':row['listing_id']})
    await db.commit()
    if edge=='order_transaction_id':
        new_tx=await TransactionService(db).initiate(row['buyer_id'],'listing_purchase','browser',seller_id=row['seller_id'],listing_id=row['listing_id'],amount_cents=2500)
        tid=new_tx['id']
    parents={'seller_id':('users',row['seller_id']),'listing_id':('listings',row['listing_id']),
        'data_request_id':('data_requests',request_id),'party_id':('party',party),'api_key_id':('agent_api_keys',key),
        'order_transaction_id':('transactions',tid),'purchased_version_id':('listing_versions',version)}
    created=[]
    async def perform(session):
        if edge in ('party_id','api_key_id'):
            result=await TransactionService(session).initiate_agent(row['listing_id'],row['buyer_id'],key)
        elif edge in ('order_transaction_id','purchased_version_id'):
            result=await OrderService(session).create_order(row['buyer_id'],row['seller_id'],row['listing_id'],2500,{},
                transaction_id=tid if edge=='order_transaction_id' else None,auto_commit=False,purchased_version_id=version)
        else:
            result=await TransactionService(session).initiate(row['buyer_id'],'data_request' if edge=='data_request_id' else 'listing_purchase','browser',
                seller_id=row['seller_id'],listing_id=None if edge=='data_request_id' else row['listing_id'],data_request_id=request_id if edge=='data_request_id' else None,
                amount_cents=2500,auto_commit=False)
        created.append(result)
    await f5_parent_barrier(db,perform,*parents[edge],parent_first)
    assert len(created)==1
    actual=created[0]
    expected_key='transaction_id' if edge=='order_transaction_id' else edge
    assert actual[expected_key]==parents[edge][1]
    assert actual['buyer_id']==row['buyer_id']


@pytest.mark.asyncio
async def test_f5_reference_public_link_retains_uncounted_contract(db):
    row,tid,pi,ch,r=await f4_partial(db)
    await db.execute(text("update listings set fulfillment_type='reference',source_delivery=cast(:source as jsonb) where id=:id"),
        {'id':row['listing_id'],'source':json.dumps({'kind':'public_url','url':'https://example.invalid/public.csv'})})
    await db.execute(text("update orders set max_downloads=0,access_expires_at=clock_timestamp()-interval '1 day' where id=:id"),{'id':row['id']})
    await db.commit()
    before=await f5_access_snapshot(db,row['id'])
    result=await f5_orders_http(db,row['buyer_id'],'GET',f"/orders/{row['id']}/access")
    assert result.status_code==200,result.text
    assert result.json()['can_download'] and result.json()['downloads_remaining'] is None
    assert result.json()['download_urls'][0]['url']=='https://example.invalid/public.csv'
    assert await f5_access_snapshot(db,row['id'])==before


@pytest.mark.asyncio
@pytest.mark.parametrize('parent',['users','billing_entities'])
@pytest.mark.parametrize('parent_first',[True,False])
async def test_f5_capture_reference_both_orderings(db,parent,parent_first):
    oid,tid,pi,ch=await purchase(db)
    buyer=await db.scalar(text('select buyer_id from orders where id=:id'),{'id':oid})
    eid=await merchant(db)
    async def perform(session):
        money=await lock_order_money(session,oid)
        await ensure_order_capture(session,order=money.order,transaction=money.transaction,
            provider_payment=pi,provider_charge=ch,origin='payment_event',locked=money)
    await f5_parent_barrier(db,perform,parent,buyer if parent=='users' else eid,parent_first)
    payment=(await db.execute(select(Payment).where(Payment.stripe_payment_intent_id==pi['id']))).scalar_one()
    state=await db.get(OrderMoneyState,oid)
    assert payment.entity_id==eid and payment.customer_id==buyer
    assert state.billing_entity_id==eid and state.capture_payment_id==payment.id
    assert payment.journal_entry_id==state.capture_journal_entry_id
    journal=await db.get(JournalEntry,payment.journal_entry_id)
    assert journal.status=='posted' and journal.posted_at is not None


async def f6_pending_agent(db, monkeypatch):
    """Explicit historical no-attempt pair for the retained legacy cleanup path.

    Construct history directly; never strip metadata from a new producer.
    """
    oid, tid, pi, ch = await purchase(db, 'agent_payment_pending')
    party, key = uuid.uuid4(), uuid.uuid4()
    await db.execute(text("INSERT INTO party(id,party_type) VALUES(:id,'organization')"), {'id': party})
    await db.execute(text("""INSERT INTO agent_api_keys(id,org_id,name,key_hash,prefix,spend_used,spend_cap)
        VALUES(:id,:party,'F6 legacy',:hash,'f6',2500,10000)"""),
        {'id':key,'party':party,'hash':uuid.uuid4().hex*2})
    await db.execute(text("UPDATE orders SET status='created' WHERE id=:id"), {'id':oid})
    await db.execute(text("""UPDATE transactions SET buyer_type='agent',surface='agent_api',
        party_id=:party,api_key_id=:key,status='agent_payment_pending',
        created_at=NOW()-INTERVAL '2 hours' WHERE id=:id"""), {'id':tid,'party':party,'key':key})
    pi['metadata'].update(api_key_id=str(key),buyer_type='agent')
    await db.commit()
    assert await db.scalar(text("SELECT metadata ? 'canonical_agent_attempt_v1' FROM transactions WHERE id=:id"), {'id':tid}) is False
    return oid,tid,key,pi,ch


async def agent_checkout_candidate(db, monkeypatch, *, provider_status='processing'):
    """New producer with fresh PI/Charge and a committed original reservation."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    import stripe
    from app.services.transaction_service import TransactionService
    from app.services.stripe_connect_service import stripe_connect_service
    from app.services.agent_auth_service import AgentAuthService
    seed_oid, seed_tid, seed_pi, seed_ch = await purchase(db)
    row = (await db.execute(text('select * from orders where id=:id'), {'id':seed_oid})).mappings().one()
    await db.execute(text("UPDATE listings SET status='published' WHERE id=:id"), {'id':row['listing_id']})
    party, key, seller_party = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    customer='cus_'+uuid.uuid4().hex
    for pid, kind in [(party,'organization'),(seller_party,'person')]:
        await db.execute(text('INSERT INTO party(id,party_type) VALUES(:id,:kind)'), {'id':pid,'kind':kind})
    for pid, provider, external in [(party,'auth_user',str(row['buyer_id'])),(party,'stripe',customer),
            (seller_party,'auth_user',str(row['seller_id'])),(seller_party,'stripe_connect','acct_'+uuid.uuid4().hex)]:
        await db.execute(text("""INSERT INTO party_identity(party_id,provider,external_id,is_primary,metadata)
            VALUES(:id,:provider,:external,true,'{"default_payment_method_id":"pm_durable"}')"""),
            {'id':pid,'provider':provider,'external':external})
    await db.execute(text("""INSERT INTO agent_api_keys(id,org_id,name,key_hash,prefix,spend_used,spend_cap)
        VALUES(:id,:party,'durable test',:hash,'durable',0,10000)"""),
        {'id':key,'party':party,'hash':uuid.uuid4().hex*2})
    monkeypatch.setattr(stripe_connect_service,'get_account',AsyncMock(return_value=SimpleNamespace(
        payouts_enabled=True,details_submitted=True,charges_enabled=True)))
    pi_id, ch_id = 'pi_'+uuid.uuid4().hex, 'ch_'+uuid.uuid4().hex
    pi={'id':pi_id,'latest_charge':ch_id,'status':provider_status,'amount':2500,
        'amount_received':2500 if provider_status=='succeeded' else 0,'amount_capturable':0,
        'currency':'usd','livemode':False,'customer':customer,'payment_method':'pm_durable','metadata':{}}
    ch={'id':ch_id,'payment_intent':pi_id,'amount':2500,'amount_captured':2500,'amount_refunded':0,
        'currency':'usd','livemode':False,'customer':customer,'paid':True,'captured':True,'metadata':{},
        'created':int(datetime.now(timezone.utc).timestamp())}
    calls=[]
    def create(**kwargs):
        calls.append(('create',kwargs.copy()));pi['metadata']=kwargs['metadata'].copy();return pi.copy()
    def retrieve(ident, **kwargs):
        calls.append(('retrieve',ident));assert ident==pi_id;return pi.copy()
    def cancel(ident, **kwargs):
        calls.append(('cancel',ident));assert ident==pi_id;pi.update(status='canceled',amount_received=0,amount_capturable=0);return pi.copy()
    monkeypatch.setattr(stripe.PaymentIntent,'create',create)
    monkeypatch.setattr(stripe.PaymentIntent,'retrieve',retrieve)
    monkeypatch.setattr(stripe.PaymentIntent,'cancel',cancel)
    monkeypatch.setattr(stripe.Charge,'retrieve',lambda ident: ch.copy() if ident==ch_id else None)
    svc=TransactionService(db)
    tx=await svc.initiate_agent(row['listing_id'],row['buyer_id'],key)
    await AgentAuthService(db).reserve_spend(key,2500)
    await db.commit()
    assert await db.scalar(text('SELECT stripe_payment_intent_id FROM orders WHERE id=:id'),{'id':seed_oid})==seed_pi['id']
    assert await db.scalar(text('SELECT stripe_payment_intent_id FROM transactions WHERE id=:id'),{'id':seed_tid})==seed_pi['id']
    await db.rollback()
    return svc,tx,key,pi,ch,calls


async def f6_task(session, monkeypatch):
    from contextlib import asynccontextmanager
    from app.tasks import scheduled
    @asynccontextmanager
    async def local():
        # Match the task-owned fresh session, including on the base implementation.
        await session.rollback()
        yield session
    monkeypatch.setattr(scheduled,'AsyncSessionLocal',local)
    import inspect
    function = inspect.unwrap(scheduled.cleanup_stuck_agent_transactions.run)
    return await function(None) if len(inspect.signature(function).parameters) else await function()


async def f6_snapshot(db, oid, tid, key):
    result=[]
    for table, clause, ident in [('orders','id',oid),('transactions','id',tid),
            ('order_money_states','order_id',oid),('refunds','order_id',oid),
            ('transaction_events','transaction_id',tid),('agent_audit_log','transaction_id',tid),
            ('agent_api_keys','id',key)]:
        rows=(await db.execute(text(f'SELECT to_jsonb(t) FROM {table} t WHERE {clause}=:id ORDER BY to_jsonb(t)::text'),{'id':ident})).scalars().all()
        result.append(rows)
    return result


@pytest.mark.asyncio
@pytest.mark.parametrize('condition',['stale','unlinked','nonstale','paid','refund_admitted','partial','full','binding','reconciliation','no_pi'])
async def test_f6_cleanup_actual_task_revalidation(db,monkeypatch,condition):
    oid,tid,key,pi,ch=await f6_pending_agent(db,monkeypatch)
    if condition=='unlinked':
        await db.execute(text('update orders set transaction_id=null where id=:id'),{'id':oid})
        await db.execute(text('update transactions set order_id=null,stripe_payment_intent_id=null where id=:id'),{'id':tid})
    elif condition=='nonstale':await db.execute(text('update transactions set created_at=NOW() where id=:id'),{'id':tid})
    elif condition=='paid':await db.execute(text('update orders set paid_at=NOW() where id=:id'),{'id':oid})
    elif condition=='binding':await db.execute(text('update orders set transaction_id=null where id=:id'),{'id':oid})
    elif condition=='no_pi':await db.execute(text('update orders set stripe_payment_intent_id=null where id=:id'),{'id':oid})
    elif condition=='reconciliation':
        money=await lock_order_money(db,oid);money.state.reconciliation_reason='F6 retained exception'
    elif condition in ('refund_admitted','partial','full'):
        ch['amount_refunded']=333 if condition=='partial' else 2500
        event=await signed_event(db,ch)
        await admit_order_refund(db,event)
        if condition!='refund_admitted':await process(db,event,pi,ch,[refund(ch,ch['amount_refunded'],uuid.uuid4().hex)])
    await db.commit()
    before=await f6_snapshot(db,oid,tid,key)
    result=await f6_task(db,monkeypatch)
    if condition in ('stale','unlinked'):
        assert result['cleaned']>=1
        assert await db.scalar(text('select status from transactions where id=:id'),{'id':tid})==('agent_payment_failed' if condition=='unlinked' else 'cancelled')
        assert await db.scalar(text('select spend_used from agent_api_keys where id=:id'),{'id':key})==0
        assert await db.scalar(text("select count(*) from transaction_events where transaction_id=:id and to_status in ('cancelled','agent_payment_failed')"),{'id':tid})==1
        assert await db.scalar(text("select count(*) from agent_audit_log where transaction_id=:id and tool_name='cleanup_stuck_agent_transactions'"),{'id':tid})==1
        assert await db.scalar(text('select count(*) from order_money_states where order_id=:id'),{'id':oid})==0
        before=await f6_snapshot(db,oid,tid,key)
    else:
        assert result=={'cleaned':0}
        assert await f6_snapshot(db,oid,tid,key)==before
    assert await f6_task(db,monkeypatch)=={'cleaned':0}
    assert await f6_snapshot(db,oid,tid,key)==before


@pytest.mark.asyncio
@pytest.mark.parametrize('operation',['refund','listener'])
@pytest.mark.parametrize('cleanup_first',[False,True])
async def test_f6_cleanup_refund_listener_order_barriers(db,monkeypatch,tmp_path,operation,cleanup_first):
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from test_order_money_protocol import disposable_url
    from app.services.transaction_service import TransactionService
    from app.services.fulfillment_listener_service import FulfillmentListenerService
    from app.schemas.fulfillment import FulfillmentMetadataMessage
    oid,tid,key,pi,ch=await f6_pending_agent(db,monkeypatch)
    row=(await db.execute(text('select * from orders where id=:id'),{'id':oid})).mappings().one()
    ch['amount_refunded']=2500
    event=await signed_event(db,ch);r=refund(ch,2500,uuid.uuid4().hex)
    await db.commit()
    message=FulfillmentMetadataMessage(transfer_id=str(uuid.uuid4()),order_id=str(oid),listing_id=str(row['listing_id']),
        parameters=dict(filename='f6.csv',content_type='text/csv',total_bytes=1,total_chunks=1,sha256_hash='a'*64))
    async def competing(session):
        if operation=='refund':return await process(session,event,pi,ch,[r])
        result=await FulfillmentListenerService(session).handle_metadata(message,row['seller_id'])
        await session.commit()
        return result
    ae=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    reached,release=asyncio.Event(),asyncio.Event()
    original=TransactionService.lock_stale_agent_payment
    async def pause(self,tx_id,expected):
        value=await original(self,tx_id,expected)
        if cleanup_first and tx_id==tid:
            reached.set();await asyncio.wait_for(release.wait(),5)
        return value
    monkeypatch.setattr(TransactionService,'lock_stale_agent_payment',pause)
    try:
        async with ae.connect() as c1,ae.connect() as c2,AsyncSession(c1,expire_on_commit=False) as first_db,AsyncSession(c2,expire_on_commit=False) as other,AsyncSession(ae) as observer:
            p1=await first_db.scalar(text('select pg_backend_pid()'));p2=await other.scalar(text('select pg_backend_pid()'))
            await first_db.execute(text("set lock_timeout='4s'"));await other.execute(text("set lock_timeout='4s'"))
            if cleanup_first:
                first=asyncio.create_task(f6_task(first_db,monkeypatch))
                await asyncio.wait_for(reached.wait(),5)
                second=asyncio.create_task(competing(other))
            else:
                await first_db.execute(text('select id from orders where id=:id for update'),{'id':oid})
                first=None;second=asyncio.create_task(f6_task(other,monkeypatch))
            try:
                async with asyncio.timeout(3):
                    while not await observer.scalar(text('select :a=ANY(pg_blocking_pids(:b))'),{'a':p1,'b':p2}):await asyncio.sleep(.01)
                query=await observer.scalar(text('select query from pg_stat_activity where pid=:pid'),{'pid':p2})
                assert 'orders' in query.lower(),query
                assert await observer.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_locks WHERE pid=:pid AND relation='orders'::regclass AND mode='RowShareLock')"),{'pid':p2})
                # The blocked cleanup cannot already own the transaction lock.
                if not cleanup_first:
                    await first_db.execute(text('select id from transactions where id=:id for update nowait'),{'id':tid})
                    result=await competing(first_db)
                else:
                    release.set();await asyncio.wait_for(first,5)
                second_result=await asyncio.wait_for(second,5)
                if cleanup_first:result=second_result
                if operation=='listener':assert result['success'] is False and result['error']=='INVALID_ORDER_STATE'
                else:assert result['refund_total_cents']==2500
            finally:
                release.set()
                for task in (first,second):
                    if task and not task.done():task.cancel()
                await asyncio.gather(*(t for t in (first,second) if t),return_exceptions=True)
                await other.rollback()
        assert await db.scalar(text('select spend_used from agent_api_keys where id=:id'),{'id':key})==0
        assert await db.scalar(text('select status from orders where id=:id'),{'id':oid})==('refunded' if operation=='refund' else 'cancelled')
        assert await db.scalar(text('select status from transactions where id=:id'),{'id':tid})==('refunded' if operation=='refund' else 'cancelled')
        cleanup_count=await db.scalar(text("select count(*) from transaction_events where transaction_id=:id and to_status='cancelled'"),{'id':tid})
        assert cleanup_count==(1 if cleanup_first or operation=='listener' else 0)
        assert await db.scalar(text("select count(*) from agent_audit_log where transaction_id=:id and tool_name='cleanup_stuck_agent_transactions'"),{'id':tid})==cleanup_count
        assert await db.scalar(text('select count(*) from transfer_sessions where order_id=:id'),{'id':oid})==0
        if operation=='refund':
            stored=await db.scalar(select(Refund).where(Refund.order_id==oid))
            assert stored.agent_spend_delta_cents==(0 if cleanup_first else 2500)
            assert await db.scalar(text("select count(*) from transaction_events where transaction_id=:id and to_status='refunded'"),{'id':tid})==1
            await process(db,event,pi,ch,[r])
        before=await f6_snapshot(db,oid,tid,key)
        assert await f6_task(db,monkeypatch)=={'cleaned':0}
        assert await f6_snapshot(db,oid,tid,key)==before
    finally:await ae.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize('newly_linked',[True,False])
async def test_f6_binding_changes_under_transaction_lock_refuse_without_order_reentry(db,monkeypatch,newly_linked):
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from test_order_money_protocol import disposable_url
    from app.services.transaction_service import TransactionService
    oid,tid,key,pi,ch=await f6_pending_agent(db,monkeypatch)
    if newly_linked:
        await db.execute(text('update orders set transaction_id=null where id=:id'),{'id':oid})
        await db.execute(text('update transactions set order_id=null where id=:id'),{'id':tid})
        await db.commit()
    expected=None if newly_linked else oid
    # Candidate was scanned above; another owner changes its binding first.
    await db.execute(text('select id from orders where id=:id for update'),{'id':oid})
    await db.execute(text('update orders set transaction_id=:tid where id=:id'),{'id':oid,'tid':tid if newly_linked else None})
    await db.execute(text('update transactions set order_id=:oid where id=:id'),{'id':tid,'oid':oid if newly_linked else None})
    ae=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    try:
        async with AsyncSession(ae,expire_on_commit=False) as other,AsyncSession(ae) as observer:
            pid=await other.scalar(text('select pg_backend_pid()'))
            task=asyncio.create_task(TransactionService(other).lock_stale_agent_payment(tid,expected))
            try:
                async with asyncio.timeout(3):
                    while not await observer.scalar(text('select cardinality(pg_blocking_pids(:pid))>0'),{'pid':pid}):await asyncio.sleep(.01)
                query=await observer.scalar(text('select query from pg_stat_activity where pid=:pid'),{'pid':pid})
                assert ('transactions' if newly_linked else 'orders') in query.lower()
                await db.commit()
                before=await f6_snapshot(db,oid,tid,key)
                assert await asyncio.wait_for(task,3) is None
                await other.rollback()
                assert await f6_snapshot(db,oid,tid,key)==before
            finally:
                if not task.done():task.cancel()
                await asyncio.gather(task,return_exceptions=True)
    finally:await ae.dispose()


@pytest.mark.asyncio
async def test_f6_multicandidate_releases_previous_lock_chain(db,monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from test_order_money_protocol import disposable_url
    from app.services.transaction_service import TransactionService
    candidates=[await f6_pending_agent(db,monkeypatch) for _ in range(2)]
    candidates.sort(key=lambda x:x[1])
    original=TransactionService.lock_stale_agent_payment
    ae=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    checked=[]
    async def check(self,tx_id,expected):
        if tx_id==candidates[1][1]:
            async with AsyncSession(ae) as observer:
                for table,ident in [('orders',candidates[0][0]),('transactions',candidates[0][1]),('agent_api_keys',candidates[0][2])]:
                    await observer.execute(text(f'select id from {table} where id=:id for update nowait'),{'id':ident})
                checked.append(True)
        return await original(self,tx_id,expected)
    monkeypatch.setattr(TransactionService,'lock_stale_agent_payment',check)
    try:
        result=await f6_task(db,monkeypatch)
        assert result['cleaned']>=2 and checked==[True]
        for oid,tid,key,_,_ in candidates:
            assert await db.scalar(text('select spend_used from agent_api_keys where id=:id'),{'id':key})==0
            assert await db.scalar(text("select count(*) from transaction_events where transaction_id=:id and to_status='cancelled'"),{'id':tid})==1
    finally:await ae.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize('cleanup_first',[True,False])
async def test_f6_cached_cleanup_candidate_normal_capture_and_listener_completion(db,monkeypatch,tmp_path,cleanup_first):
    import asyncio,hashlib,base64
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from test_order_money_protocol import disposable_url
    from app.services.transaction_service import TransactionService
    from app.services import fulfillment_listener_service as listener
    from app.schemas.fulfillment import FulfillmentMetadataMessage,FulfillmentChunkMessage,FulfillmentCompleteMessage
    from app.api.v1.endpoints.webhooks import _handle_payment_succeeded
    oid,tid,key,pi,ch=await f6_pending_agent(db,monkeypatch)
    scanned,proceed,locked,release=asyncio.Event(),asyncio.Event(),asyncio.Event(),asyncio.Event()
    original=TransactionService.lock_stale_agent_payment
    async def paused(self,tx_id,expected):
        if tx_id==tid:
            scanned.set();await asyncio.wait_for(proceed.wait(),8)
        result=await original(self,tx_id,expected)
        if tx_id==tid and cleanup_first:
            locked.set();await asyncio.wait_for(release.wait(),5)
        return result
    monkeypatch.setattr(TransactionService,'lock_stale_agent_payment',paused)
    monkeypatch.setattr(listener,'STAGING_DIR',tmp_path)
    ae=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    try:
        async with ae.connect() as c1,ae.connect() as c2,AsyncSession(c1,expire_on_commit=False) as cleanup,AsyncSession(c2,expire_on_commit=False) as access,AsyncSession(ae) as observer:
            p1=await cleanup.scalar(text('select pg_backend_pid()'));p2=await access.scalar(text('select pg_backend_pid()'))
            task=asyncio.create_task(f6_task(cleanup,monkeypatch))
            await asyncio.wait_for(scanned.wait(),5)
            # Real capture and agent payment writer advance the scanned candidate.
            money=await lock_order_money(db,oid)
            await ensure_order_capture(db,order=money.order,transaction=money.transaction,provider_payment=pi,provider_charge=ch,origin='payment_event',locked=money)
            await db.run_sync(lambda sync:_handle_payment_succeeded(pi,sync))
            await db.commit()
            row=(await db.execute(text('select * from orders where id=:id'),{'id':oid})).mappings().one()
            data=b'F6 paid agent delivery';digest=hashlib.sha256(data).hexdigest();transfer=str(uuid.uuid4())
            svc=listener.FulfillmentListenerService(db)
            meta=FulfillmentMetadataMessage(transfer_id=transfer,order_id=str(oid),listing_id=str(row['listing_id']),parameters=dict(filename='f6.csv',content_type='text/csv',total_bytes=len(data),total_chunks=1,sha256_hash=digest))
            assert (await svc.handle_metadata(meta,row['seller_id']))['success']
            chunk=FulfillmentChunkMessage(transfer_id=transfer,chunk_index=0,byte_offset=0,payload_length=len(data),chunk_sha256=digest,payload=base64.b64encode(data).decode())
            assert (await svc.handle_chunk(chunk,row['seller_id']))['success']
            msg=FulfillmentCompleteMessage(transfer_id=transfer,order_id=str(oid),parameters=dict(file_size_bytes=len(data),chunk_count=1,sha256_hash=digest))
            await db.commit()
            async def complete():return await listener.FulfillmentListenerService(access).handle_complete(msg,row['seller_id'])
            completion=None
            try:
                if cleanup_first:
                    proceed.set();await asyncio.wait_for(locked.wait(),5)
                    completion=asyncio.create_task(complete());blocking,blocked=p1,p2
                else:
                    await access.execute(text('select id from orders where id=:id for update'),{'id':oid})
                    proceed.set();blocking,blocked=p2,p1
                async with asyncio.timeout(3):
                    while not await observer.scalar(text('select :a=ANY(pg_blocking_pids(:b))'),{'a':blocking,'b':blocked}):await asyncio.sleep(.01)
                assert await observer.scalar(text("select exists(select 1 from pg_locks where pid=:pid and relation='orders'::regclass and mode='RowShareLock')"),{'pid':blocked})
                if cleanup_first:
                    release.set();result=await asyncio.wait_for(completion,5)
                else:result=await complete()
                assert result['success'] and result['download_token']
                assert await asyncio.wait_for(task,5)=={'cleaned':0}
            finally:
                proceed.set();release.set()
                for item in (task,completion):
                    if item and not item.done():item.cancel()
                await asyncio.gather(*(item for item in (task,completion) if item),return_exceptions=True)
            assert await db.scalar(text('select status from orders where id=:id'),{'id':oid})=='delivered'
            assert await db.scalar(text('select spend_used from agent_api_keys where id=:id'),{'id':key})==2500
            assert await db.scalar(text("select count(*) from agent_audit_log where transaction_id=:id and tool_name='cleanup_stuck_agent_transactions'"),{'id':tid})==0
            assert await db.scalar(text("select count(*) from transaction_events where transaction_id=:id and to_status='delivered'"),{'id':tid})==1
            before=await f6_snapshot(db,oid,tid,key)
            assert await f6_task(db,monkeypatch)=={'cleaned':0}
            assert await f6_snapshot(db,oid,tid,key)==before
    finally:await ae.dispose()


@pytest.mark.asyncio
async def test_f6_task_blocks_at_order_without_owning_transaction(db,monkeypatch):
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
    from sqlalchemy.pool import NullPool
    from test_order_money_protocol import disposable_url
    oid,tid,key,_,_=await f6_pending_agent(db,monkeypatch)
    await db.execute(text('select id from orders where id=:id for update'),{'id':oid})
    blocker=await db.scalar(text('select pg_backend_pid()'))
    ae=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'),poolclass=NullPool)
    try:
        async with ae.connect() as conn,AsyncSession(conn,expire_on_commit=False) as other,AsyncSession(ae) as observer:
            pid=await other.scalar(text('select pg_backend_pid()'))
            task=asyncio.create_task(f6_task(other,monkeypatch))
            try:
                async with asyncio.timeout(3):
                    while not await observer.scalar(text('select :a=ANY(pg_blocking_pids(:b))'),{'a':blocker,'b':pid}):await asyncio.sleep(.01)
                # This succeeds only if cleanup has not taken the reverse edge.
                await db.execute(text('select id from transactions where id=:id for update nowait'),{'id':tid})
                await db.rollback()
                assert (await asyncio.wait_for(task,5))['cleaned']>=1
                assert await db.scalar(text('select spend_used from agent_api_keys where id=:id'),{'id':key})==0
            finally:
                await db.rollback()
                if not task.done():task.cancel()
                await asyncio.gather(task,return_exceptions=True)
                await other.rollback()
    finally:await ae.dispose()


# F7: real DeliveryService, signed tokens, and migrated parent/FK serialization.
async def f7_delivery(db):
    from app.services.delivery_service import DeliveryService
    oid, tid, pi, ch = await purchase(db, 'fulfilling')
    await db.execute(text("update orders set status='pending_delivery' where id=:id"), {'id':oid})
    await db.execute(text("update transactions set metadata=cast(:meta as jsonb) where id=:id"),
                     {'id':tid, 'meta':json.dumps({'descriptor':{'expected_bytes':4}})})
    await db.commit()
    service = DeliveryService(db)
    buyer = await db.scalar(text('select buyer_id from transactions where id=:id'), {'id':tid})
    token = await service.generate_delivery_token(tid, buyer_id=buyer)
    claims, _ = await service.validate_token(token['token'])
    await db.commit()
    return oid, tid, pi, ch, token, claims


async def f7_snapshot(db, oid, tid):
    result = {}
    for table, predicate, params in [
        ('orders','id=:id',{'id':oid}), ('transactions','id=:id',{'id':tid}),
        ('order_money_states','order_id=:id',{'id':oid}),
        ('delivery_audit_log','transaction_id=:id',{'id':tid}),
        ('delivery_dead_letter_queue','transaction_id=:id',{'id':tid}),
        ('stripe_webhook_idempotency','transaction_id=:id',{'id':tid}),
        ('transaction_events','transaction_id=:id',{'id':tid}),
        ('refunds','order_id=:id',{'id':oid}),
        ('stripe_events','refund_order_id=:id',{'id':oid}),
    ]:
        result[table] = (await db.execute(text(f'SELECT to_jsonb(t) FROM {table} t WHERE {predicate} ORDER BY to_jsonb(t)::text'), params)).scalars().all()
    result['payments']=(await db.execute(text("SELECT to_jsonb(p) FROM payments p JOIN transactions t ON t.stripe_payment_intent_id=p.stripe_payment_intent_id WHERE t.id=:id ORDER BY p.id"),{'id':tid})).scalars().all()
    result['journals']=(await db.execute(text("SELECT to_jsonb(j) FROM journal_entries j WHERE id IN (SELECT capture_journal_entry_id FROM order_money_states WHERE order_id=:oid UNION SELECT payout_journal_entry_id FROM order_money_states WHERE order_id=:oid UNION SELECT journal_entry_id FROM refunds WHERE order_id=:oid) ORDER BY id"),{'oid':oid})).scalars().all()
    result['journal_lines']=(await db.execute(text("SELECT to_jsonb(l) FROM journal_lines l WHERE entry_id IN (SELECT capture_journal_entry_id FROM order_money_states WHERE order_id=:oid UNION SELECT payout_journal_entry_id FROM order_money_states WHERE order_id=:oid UNION SELECT journal_entry_id FROM refunds WHERE order_id=:oid) ORDER BY id"),{'oid':oid})).scalars().all()
    result['agent_spend']=(await db.execute(text("SELECT to_jsonb(a) FROM agent_api_keys a JOIN transactions t ON t.api_key_id=a.id WHERE t.id=:tid ORDER BY a.id"),{'tid':tid})).scalars().all()
    return result


@pytest.mark.asyncio
@pytest.mark.parametrize('callback', ['fail', 'finalize'])
async def test_f7_late_refund_callback_preserves_exact_state(db, callback):
    from fastapi import HTTPException
    from app.services.delivery_service import DeliveryService
    oid,tid,pi,ch,token,claims = await f7_delivery(db)
    service = DeliveryService(db)
    await service._record_range_progress(transaction_id=tid, attempt=claims.attempt, jti=claims.jti,start=0,end=3)
    ch['amount_refunded']=2500
    await process(db, await signed_event(db,ch), pi,ch,[refund(ch,2500,uuid.uuid4().hex)])
    before = await f7_snapshot(db,oid,tid)
    await db.commit()
    try:
        if callback == 'fail':
            await service.fail_delivery(tid,reason='stream_failed',error_message='late transport error')
        else:
            await service._finalize_stream_if_complete(tid,claims,200)
    except HTTPException as exc:
        assert exc.status_code in (403,409,410)
        await db.rollback()
    assert await f7_snapshot(db,oid,tid) == before


@pytest.mark.asyncio
@pytest.mark.parametrize('operation',['token','idempotency'])
async def test_f7_first_parent_is_order(db,operation):
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.services.delivery_service import DeliveryService
    oid,tid,pi,ch,token,claims = await f7_delivery(db)
    await db.commit()
    async with AsyncSession(db.bind,expire_on_commit=False) as blocker, AsyncSession(db.bind,expire_on_commit=False) as worker, AsyncSession(db.bind) as observer:
        await blocker.execute(text('select id from orders where id=:id for update'),{'id':oid})
        p1=await blocker.scalar(text('select pg_backend_pid()'))
        p2=await worker.scalar(text('select pg_backend_pid()'))
        async def run():
            service=DeliveryService(worker)
            if operation=='token': return await service.generate_delivery_token(tid,buyer_id=claims.buyer_id)
            return await service.record_stripe_webhook_idempotency(event_id='evt_'+uuid.uuid4().hex,event_type='payment_intent.succeeded',idempotency_key=uuid.uuid4().hex,payload_hash='a'*64,transaction_id=tid)
        task=asyncio.create_task(run())
        try:
            async with asyncio.timeout(5):
                while not await observer.scalar(text('select :a=ANY(pg_blocking_pids(:b))'),{'a':p1,'b':p2}):
                    await asyncio.sleep(.01)
            # Actual inversion proof: the blocked operation must NOT own tx yet.
            await blocker.execute(text("set local lock_timeout='500ms'"))
            await blocker.execute(text('select id from transactions where id=:id for update'),{'id':tid})
            await blocker.commit()
            await asyncio.wait_for(task,5)
        finally:
            await blocker.rollback()
            try:
                await asyncio.wait_for(asyncio.shield(task),5)
            except Exception:
                if not task.done(): task.cancel()
                await asyncio.gather(task,return_exceptions=True)
            await worker.rollback()


async def f7_apply_full(db, pi, ch):
    ch['amount_refunded']=2500
    return await process(db,await signed_event(db,ch),pi,ch,[refund(ch,2500,uuid.uuid4().hex)])


@pytest.mark.asyncio
@pytest.mark.parametrize('condition',['full','revoked','partial_no_prior','partial_closed','expired','exhausted'])
@pytest.mark.parametrize('operation',['create','token','validate','progress','finalize','fail','confirm','dispute','retry','idempotency','dlq'])
async def test_f7_current_access_refuses_without_effects(db,condition,operation):
    from fastapi import HTTPException
    from app.services.delivery_service import DeliveryService
    oid,tid,pi,ch,token,claims=await f7_delivery(db)
    service=DeliveryService(db)
    await service.fail_delivery(tid,reason='transport',error_message='test transport failure')
    dlq=await db.scalar(text('select id from delivery_dead_letter_queue where transaction_id=:id'),{'id':tid})
    assert dlq
    if condition=='full': await f7_apply_full(db,pi,ch)
    elif condition.startswith('partial'):
        ch['amount_refunded']=333
        await process(db,await signed_event(db,ch),pi,ch,[refund(ch,333,uuid.uuid4().hex)])
        if condition=='partial_closed':
            await db.execute(text("update transactions set status='expired' where id=:id"),{'id':tid})
    elif condition=='revoked':
        from app.services.order_service import OrderService
        await OrderService(db).revoke_access(oid,revoker_id=claims.buyer_id,reason='F7 test revoke')
    elif condition=='expired':
        await db.execute(text("update orders set access_expires_at=now()-interval '1s' where id=:id"),{'id':oid})
    elif condition=='exhausted':
        await db.execute(text('update orders set max_downloads=0 where id=:id'),{'id':oid})
    await db.commit()
    before=await f7_snapshot(db,oid,tid)
    await db.commit()
    with pytest.raises(HTTPException) as caught:
        if operation=='create':await service.create_delivery_record(tid)
        elif operation=='token':await service.generate_delivery_token(tid,buyer_id=claims.buyer_id)
        elif operation=='validate':await service.validate_token(token['token'])
        elif operation=='progress':await service._record_range_progress(transaction_id=tid,attempt=claims.attempt,jti=claims.jti,start=0,end=3)
        elif operation=='finalize':await service._finalize_stream_if_complete(tid,claims,200)
        elif operation=='fail':await service.fail_delivery(tid,reason='late',error_message='late')
        elif operation=='confirm':await service.confirm_delivery(tid,actor_type='buyer',actor_id=claims.buyer_id)
        elif operation=='dispute':await service.dispute_delivery(tid,actor_type='buyer',actor_id=claims.buyer_id,category='quality',reason='test dispute')
        elif operation=='retry':await service.retry_delivery(tid,actor_type='admin',actor_id=claims.buyer_id,reason='retry')
        elif operation=='idempotency':await service.record_stripe_webhook_idempotency(transaction_id=tid,event_id='evt_'+uuid.uuid4().hex,event_type='payment_intent.succeeded',idempotency_key=uuid.uuid4().hex,payload_hash='a'*64)
        elif operation=='dlq':await service.process_dlq_retry(dlq)
    assert caught.value.status_code in (403,409,410)
    await db.rollback()
    assert await f7_snapshot(db,oid,tid)==before


@pytest.mark.asyncio
@pytest.mark.parametrize('condition',['wrong_buyer','foreign_route','forged','malformed','foreign_claim','stale_attempt','stale_jti','expired'])
async def test_f7_signed_credential_refusals(db,condition):
    from fastapi import HTTPException
    from app.services.delivery_service import DeliveryService
    from app.core.config import settings
    from jose import jwt
    oid,tid,pi,ch,token,claims=await f7_delivery(db)
    service=DeliveryService(db)
    presented=token['token']
    if condition in ('forged','malformed','foreign_claim'):
        payload=jwt.get_unverified_claims(presented)
        if condition=='malformed':payload['transaction_id']='not-a-uuid'
        if condition=='foreign_claim':payload['delivery_id']=str(uuid.uuid4())
        presented=jwt.encode(payload,'forged-key' if condition=='forged' else settings.DOWNLOAD_TOKEN_SECRET_KEY,algorithm=settings.ALGORITHM)
    if condition in ('stale_attempt','stale_jti'):
        state={'active_attempt':claims.attempt+(condition=='stale_attempt'),'jti':uuid.uuid4().hex if condition=='stale_jti' else claims.jti}
        await db.execute(text("update transactions set metadata=jsonb_set(metadata,'{delivery}',cast(:state as jsonb)) where id=:id"),{'id':tid,'state':json.dumps(state)})
    if condition=='expired':
        await db.execute(text("update transactions set delivery_expires_at=now()-interval '1s' where id=:id"),{'id':tid})
    await db.commit()
    before=await f7_snapshot(db,oid,tid);await db.commit()
    with pytest.raises(HTTPException) as caught:
        if condition=='wrong_buyer':await service.generate_delivery_token(tid,buyer_id=uuid.uuid4())
        elif condition=='foreign_route':await service.stream_from_vz(uuid.uuid4(),presented)
        else:await service.validate_token(presented)
    assert caught.value.status_code in (401,403,410)
    await db.rollback()
    assert await f7_snapshot(db,oid,tid)==before


@pytest.mark.asyncio
@pytest.mark.parametrize('partial',[False,True])
async def test_f7_normal_and_partial_prior_completion(db,partial):
    from app.services.delivery_service import DeliveryService
    oid,tid,pi,ch,token,claims=await f7_delivery(db)
    service=DeliveryService(db)
    await service._record_range_progress(transaction_id=tid,attempt=claims.attempt,jti=claims.jti,start=0,end=3)
    await service._finalize_stream_if_complete(tid,claims,200)
    assert (await service.get_delivery_record(tid))['status']=='delivered'
    if partial:
        ch['amount_refunded']=333
        await process(db,await signed_event(db,ch),pi,ch,[refund(ch,333,uuid.uuid4().hex)])
    before=await f7_snapshot(db,oid,tid);await db.commit()
    await service._finalize_stream_if_complete(tid,claims,200)
    assert await f7_snapshot(db,oid,tid)==before
    if partial:
        await service.confirm_delivery(tid,actor_type='buyer',actor_id=claims.buyer_id)
        await service.fail_delivery(tid,reason='late',error_message='late',attempt=claims.attempt,jti=claims.jti)
        assert await f7_snapshot(db,oid,tid)==before
        retried=await service.retry_delivery(tid,actor_type='admin',actor_id=claims.buyer_id,reason='refresh prior partial')
        assert retried['status']=='delivered'
        await service.generate_delivery_token(tid,buyer_id=claims.buyer_id,reuse_active_attempt=False)
        after=await f7_snapshot(db,oid,tid)
        for field in ('status','delivered_at','delivery_delivered_at','delivery_confirmed_at','delivery_ready_at','paid_at','settled_at'):
            assert after['transactions'][0][field]==before['transactions'][0][field]
        assert after['orders']==before['orders']
    else:
        assert (await service.confirm_delivery(tid,actor_type='buyer',actor_id=claims.buyer_id))['status']=='confirmed'


@pytest.mark.asyncio
async def test_f7_actual_dlq_retry_quarantine_and_normal_retry(db):
    from app.services.delivery_service import DeliveryService
    oid,tid,pi,ch,token,claims=await f7_delivery(db)
    service=DeliveryService(db)
    await service.fail_delivery(tid,reason='transport',error_message='failure')
    dlq=await db.scalar(text('select id from delivery_dead_letter_queue where transaction_id=:id'),{'id':tid})
    assert (await service.process_dlq_retry(dlq))=={'status':'retrying','attempt_count':2,'next_retry_minutes':5}
    assert (await service.process_dlq_retry(dlq))=={'status':'retrying','attempt_count':3,'next_retry_minutes':15}
    assert (await service.process_dlq_retry(dlq))=={'status':'quarantined','attempt_count':3}
    before=await f7_snapshot(db,oid,tid);await db.commit()
    assert (await service.process_dlq_retry(dlq))['status']=='quarantined'
    assert await f7_snapshot(db,oid,tid)==before
    result=await service.retry_delivery(tid,actor_type='admin',actor_id=claims.buyer_id,reason='recovered')
    assert result['status']=='fulfilling'
    new=await service.generate_delivery_token(tid,buyer_id=claims.buyer_id)
    assert new['attempt']==claims.attempt+1


@pytest.mark.asyncio
async def test_f7_genuine_unlinked_delivery_no_fabricated_authority(db):
    from app.services.delivery_service import DeliveryService
    oid,tid,pi,ch,token,claims=await f7_delivery(db)
    await db.execute(text('update orders set transaction_id=null,stripe_payment_intent_id=null where id=:id'),{'id':oid})
    await db.execute(text('update transactions set order_id=null where id=:id'),{'id':tid})
    await db.commit()
    service=DeliveryService(db)
    token=await service.generate_delivery_token(tid,buyer_id=claims.buyer_id)
    await service.validate_token(token['token'])
    await service._record_range_progress(transaction_id=tid,attempt=claims.attempt,jti=claims.jti,start=0,end=3)
    await service._finalize_stream_if_complete(tid,claims,200)
    assert (await service.get_delivery_record(tid))['status']=='delivered'
    assert not await db.scalar(text('select count(*) from order_money_states where transaction_id=:id'),{'id':tid})
    assert not await db.scalar(text('select count(*) from orders where transaction_id=:id'),{'id':tid})


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['complete','before_admission','after_admission','between_chunks','before_finalize','send_error','disconnect','disconnect_refunded','cancel','oversized'])
async def test_f7_actual_asgi_stream_owned_sessions(db,monkeypatch,mode,record_property):
    import asyncio
    import fastapi, starlette, sqlalchemy
    from fastapi import FastAPI
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from test_order_money_protocol import disposable_url
    import app.services.delivery_service as delivery
    from app.api.v1.endpoints import deliveries
    from app.core.database import get_async_db
    assert fastapi.__version__=='0.110.1'
    record_property('framework_versions',f'FastAPI={fastapi.__version__};Starlette={starlette.__version__};SQLAlchemy={sqlalchemy.__version__}')
    oid,tid,pi,ch,token,claims=await f7_delivery(db)
    engine=create_async_engine(disposable_url().replace('postgresql://','postgresql+asyncpg://'))
    sessions=[]
    class OwnedSession(AsyncSession):
        closed=False
        async def execute(self,*args,**kwargs):
            assert not self.closed, 'Request dependency session was reopened'
            return await super().execute(*args,**kwargs)
        async def close(self):
            await super().close()
            self.closed=True
    def factory():
        session=OwnedSession(engine,expire_on_commit=False)
        sessions.append(session)
        return session
    monkeypatch.setattr(delivery,'AsyncSessionLocal',factory)
    async def dependency():
        session=factory()
        try:yield session
        finally:await session.close()
    app=FastAPI();app.include_router(deliveries.router,prefix='/api/v1')
    app.dependency_overrides[get_async_db]=dependency
    reader_closed=[]
    async def unlocked():
        assert engine.pool.checkedout()==0
        assert all(s.closed for s in sessions)
        async with AsyncSession(db.bind) as probe:
            await probe.execute(text('select id from orders where id=:id for update nowait'),{'id':oid})
            await probe.execute(text('select id from transactions where id=:id for update nowait'),{'id':tid})
            await probe.rollback()
    def transport(self,metadata,start,end):
        async def reader():
            try:
                await unlocked()
                if mode=='before_admission': await f7_apply_full(db,pi,ch)
                yield b'x'*(delivery.MAX_CHUNK_BYTES+1) if mode=='oversized' else b'ab'
                await unlocked()
                if mode=='between_chunks':await f7_apply_full(db,pi,ch)
                yield b'cd'
            finally:reader_closed.append(True)
        return reader()
    monkeypatch.setattr(delivery.DeliveryService,'_open_vz_stream',transport)
    original_finalize=delivery.DeliveryService._finalize_stream_if_complete
    async def final_barrier(self,*args,**kwargs):
        if mode=='before_finalize':await f7_apply_full(db,pi,ch)
        return await original_finalize(self,*args,**kwargs)
    monkeypatch.setattr(delivery.DeliveryService,'_finalize_stream_if_complete',final_barrier)
    disconnect=asyncio.Event();send_entered=asyncio.Event();sent=[]
    async def receive():
        await disconnect.wait()
        return {'type':'http.disconnect'}
    async def send(message):
        if message['type']=='http.response.body' and message.get('body'):
            await unlocked()
            if mode=='send_error':raise OSError('F7 simulated ASGI send failure')
            if mode in ('disconnect','disconnect_refunded','cancel'):
                if mode=='disconnect_refunded':await f7_apply_full(db,pi,ch)
                send_entered.set()
                await asyncio.Event().wait()
            if mode=='after_admission':await f7_apply_full(db,pi,ch)
            sent.append(message['body'])
    scope={'type':'http','asgi':{'version':'3.0'},'http_version':'1.1','method':'GET',
           'scheme':'http','path':f'/api/v1/deliveries/{tid}/download','raw_path':f'/api/v1/deliveries/{tid}/download'.encode(),
           'query_string':b'','headers':[(b'authorization',('Bearer '+token['token']).encode())],
           'client':('203.0.113.1',1234),'server':('test',80),'root_path':''}
    task=asyncio.create_task(app(scope,receive,send))
    try:
        if mode in ('disconnect','disconnect_refunded','cancel'):
            await asyncio.wait_for(send_entered.wait(),5)
            if mode in ('disconnect','disconnect_refunded'):disconnect.set()
            else:task.cancel()
        result=await asyncio.gather(asyncio.wait_for(task,8),return_exceptions=True)
        if mode=='complete':assert result==[None]
        elif mode in ('disconnect','disconnect_refunded'):assert result==[None]
        else:assert isinstance(result[0],BaseException),result
        assert reader_closed==[True]
        await unlocked()
        row=(await db.execute(text('select status,delivery_bytes_delivered,delivery_delivered_at from transactions where id=:id'),{'id':tid})).mappings().one()
        if mode=='complete':
            assert sent==[b'ab',b'cd'] and row['status']=='delivered' and row['delivery_bytes_delivered']==4
        elif mode in ('before_admission','after_admission','between_chunks','before_finalize','disconnect_refunded'):
            assert row['status']=='refunded' and row['delivery_delivered_at'] is None
            assert sent==({'before_admission':[],'after_admission':[b'ab'],'between_chunks':[b'ab'],'before_finalize':[b'ab',b'cd'],'disconnect_refunded':[]}[mode])
        else:
            assert sent==[] and row['delivery_bytes_delivered']==0 and row['delivery_delivered_at'] is None
        assert await db.scalar(text("select count(*) from delivery_audit_log where transaction_id=:id and event_type='delivery_stream_completed'"),{'id':tid})==(1 if mode=='complete' else 0)
    finally:
        if not task.done():task.cancel()
        await asyncio.gather(task,return_exceptions=True)
        for session in sessions:await session.close()
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize('operation',['token','idempotency','replay','helper','fail_dlq','dlq_retry','dlq_quarantine'])
@pytest.mark.parametrize('refund_first',[True,False])
async def test_f7_real_refund_both_orderings(db,monkeypatch,operation,refund_first):
    import asyncio
    from fastapi import HTTPException
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.services.delivery_service import DeliveryService
    oid,tid,pi,ch,token,claims=await f7_delivery(db)
    args=dict(event_id='evt_'+uuid.uuid4().hex,event_type='payment_intent.succeeded',idempotency_key=uuid.uuid4().hex,payload_hash='a'*64,transaction_id=tid)
    if operation=='replay':assert await DeliveryService(db).record_stripe_webhook_idempotency(**args)
    dlq=None
    if operation.startswith('dlq_'):
        await DeliveryService(db).fail_delivery(tid,reason='transport',error_message='failure')
        dlq=await db.scalar(text('select id from delivery_dead_letter_queue where transaction_id=:id'),{'id':tid})
        if operation=='dlq_quarantine':
            await DeliveryService(db).process_dlq_retry(dlq)
            await DeliveryService(db).process_dlq_retry(dlq)
    ch['amount_refunded']=2500
    r=refund(ch,2500,uuid.uuid4().hex)
    event=await signed_event(db,ch)
    await admit_order_refund(db,event);await db.commit()
    refund_committed=asyncio.Event()
    if operation=='helper' and not refund_first:
        actual_idempotency=DeliveryService.record_stripe_webhook_idempotency
        async def committed_idempotency(self,**kwargs):
            result=await actual_idempotency(self,**kwargs)
            await asyncio.wait_for(refund_committed.wait(),5)
            return result
        monkeypatch.setattr(DeliveryService,'record_stripe_webhook_idempotency',committed_idempotency)
    async def effects(session):
        result=await apply_order_refund_effects(session,event=event,provider_payment=pi,provider_charge=ch,provider_refunds=[r])
        await session.commit()
        refund_committed.set()
        return result
    async def access(session):
        service=DeliveryService(session)
        try:
            if operation=='token':return await service.generate_delivery_token(tid,buyer_id=claims.buyer_id)
            if operation in ('idempotency','replay'):return await service.record_stripe_webhook_idempotency(**args)
            if operation=='helper':
                from app.api.v1.endpoints import webhooks
                async def dependency():yield session
                monkeypatch.setattr(webhooks,'get_async_db',dependency)
                return await webhooks._create_delivery_for_payment(args['event_id'],pi)
            if operation=='fail_dlq':return await service.fail_delivery(tid,reason='transport',error_message='failure')
            return await service.process_dlq_retry(dlq)
        except HTTPException as exc:
            await session.rollback()
            return exc
    async with AsyncSession(db.bind,expire_on_commit=False) as other,AsyncSession(db.bind) as observer:
        p1=await db.scalar(text('select pg_backend_pid()'));p2=await other.scalar(text('select pg_backend_pid()'))
        await db.execute(text('select id from orders where id=:id for update'),{'id':oid})
        task=asyncio.create_task(access(other) if refund_first else effects(other))
        try:
            async with asyncio.timeout(5):
                while not await observer.scalar(text('select :a=ANY(pg_blocking_pids(:b))'),{'a':p1,'b':p2}):await asyncio.sleep(.01)
            # The waiter has not taken the transaction or child first.
            await db.execute(text("set local lock_timeout='500ms'"))
            await db.execute(text('select id from transactions where id=:id for update'),{'id':tid})
            first=await effects(db) if refund_first else await access(db)
            second=await asyncio.wait_for(task,5)
            result=second if refund_first else first
            if refund_first:assert isinstance(result,HTTPException) and result.status_code==410
            elif operation=='helper':
                # The actual helper has two commits: its idempotency admission
                # wins first, then refund wins before create_delivery_record.
                assert isinstance(result,HTTPException) and result.status_code==410
                assert await db.scalar(text('select order_id from stripe_webhook_idempotency where event_id=:id'),{'id':args['event_id']})==oid
                assert await db.scalar(text("select metadata->>'delivery_record_created' from transactions where id=:id"),{'id':tid}) is None
            else:assert not isinstance(result,HTTPException)
        finally:
            await db.rollback()
            try:await asyncio.wait_for(asyncio.shield(task),5)
            except Exception:
                if not task.done():task.cancel()
                await asyncio.gather(task,return_exceptions=True)
            await other.rollback()
    assert await db.scalar(text('select status from transactions where id=:id'),{'id':tid})=='refunded'
    before=await f7_snapshot(db,oid,tid);await db.commit()
    assert isinstance(await access(db),HTTPException)
    assert await f7_snapshot(db,oid,tid)==before


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['missing_reverse','ambiguous_reverse','changed_link','unlinked_becomes_linked','foreign_order','duplicate_payment'])
async def test_f7_binding_refusal_no_new_authority(db,monkeypatch,mode):
    from fastapi import HTTPException
    from app.services.delivery_service import DeliveryService
    oid,tid,pi,ch,token,claims=await f7_delivery(db)
    other_oid,other_tid,_,_=await purchase(db,'fulfilling')
    if mode=='missing_reverse':await db.execute(text('update orders set transaction_id=null where id=:id'),{'id':oid})
    if mode=='ambiguous_reverse':await db.execute(text('update orders set transaction_id=:tid where id=:id'),{'id':other_oid,'tid':tid})
    if mode=='foreign_order':await db.execute(text('update transactions set order_id=:oid where id=:id'),{'id':tid,'oid':other_oid})
    if mode=='duplicate_payment':
        before=await f7_snapshot(db,oid,tid)
        other_before=await f7_snapshot(db,other_oid,other_tid)
        with pytest.raises(DBAPIError) as refused:
            async with db.begin_nested():
                await db.execute(text('update orders set stripe_payment_intent_id=:pi where id=:id'),{'id':other_oid,'pi':pi['id']})
        assert refused.value.orig.sqlstate=='23505'
        assert 'uq_s1714_order_payment_intent' in str(refused.value.orig)
        assert await f7_snapshot(db,oid,tid)==before
        assert await f7_snapshot(db,other_oid,other_tid)==other_before
        return
    if mode=='unlinked_becomes_linked':
        await db.execute(text('update orders set transaction_id=null,stripe_payment_intent_id=null where id=:id'),{'id':oid})
        await db.execute(text('update transactions set order_id=null where id=:id'),{'id':tid})
    await db.commit()
    snapshots=[]
    if mode in ('changed_link','unlinked_becomes_linked'):
        original=DeliveryService._get_transaction
        async def changed(self,target):
            result=await original(self,target)
            # This is the actual nonlocking discovery boundary; change only the
            # owned fixture before the service takes its first writer lock.
            if target==tid and not snapshots:
                await db.execute(text('update orders set transaction_id=:tx,stripe_payment_intent_id=:pi where id=:id'),
                                 {'id':oid,'tx':tid if mode=='unlinked_becomes_linked' else None,'pi':pi['id']})
                await db.execute(text('update transactions set order_id=:oid where id=:id'),{'id':tid,'oid':oid if mode=='unlinked_becomes_linked' else None})
                await db.commit()
                snapshots.append(await f7_snapshot(db,oid,tid));await db.commit()
            return result
        monkeypatch.setattr(DeliveryService,'_get_transaction',changed)
    before=await f7_snapshot(db,oid,tid);await db.commit()
    with pytest.raises(HTTPException) as exc:await DeliveryService(db).generate_delivery_token(tid,buyer_id=claims.buyer_id)
    assert exc.value.status_code==409
    await db.rollback()
    assert await f7_snapshot(db,oid,tid)==(snapshots[0] if snapshots else before)


@pytest.mark.asyncio
@pytest.mark.parametrize('refund_during_publish',[False,True])
async def test_f7_real_enqueue_commit_publication_and_revalidation(db,monkeypatch,refund_during_publish):
    from fastapi import HTTPException
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.services.delivery_service import DeliveryService
    from app.services.trust_event_bus import trust_event_bus
    oid,tid,pi,ch,token,claims=await f7_delivery(db)
    seller=await db.scalar(text('select seller_id from transactions where id=:id'),{'id':tid})
    device='f7-device-'+uuid.uuid4().hex
    await db.execute(text("insert into devices (id,user_id,device_id,vectoraiz_version,os_type,is_active) values (:id,:user,:device,'1.23.3','linux',true)"),{'id':uuid.uuid4(),'user':seller,'device':device})
    await db.commit()
    published=[]
    async def publish(message):
        assert not db.in_transaction(), 'No checked-out connection across publication'
        assert message.related_order_id==oid and message.related_transaction_id==tid
        async with AsyncSession(db.bind) as check:
            await check.execute(text('select id from orders where id=:id for update nowait'),{'id':oid})
            await check.execute(text('select id from transactions where id=:id for update nowait'),{'id':tid})
            assert await check.scalar(text('select count(*) from trust_outbound_messages where id=:id'),{'id':message.id})==1
            await check.rollback()
        published.append(message.id)
        if refund_during_publish:
            async with AsyncSession(db.bind,expire_on_commit=False) as refund_db:
                await f7_apply_full(refund_db,pi,ch)
        return True
    monkeypatch.setattr(trust_event_bus,'publish_message',publish)
    if refund_during_publish:
        with pytest.raises(HTTPException) as exc:await DeliveryService(db).create_delivery_record(tid)
        assert exc.value.status_code==410
        await db.rollback()
        assert await db.scalar(text('select status from transactions where id=:id'),{'id':tid})=='refunded'
        before=await f7_snapshot(db,oid,tid);await db.commit()
        # A queued device request is not authority at the actual buyer consumer.
        with pytest.raises(HTTPException):await DeliveryService(db).validate_token(token['token'])
        await db.rollback();assert await f7_snapshot(db,oid,tid)==before
        assert not await db.scalar(text("select count(*) from delivery_audit_log where transaction_id=:id and event_type='delivery_queued'"),{'id':tid})
    else:
        await DeliveryService(db).create_delivery_record(tid)
        assert await db.scalar(text("select count(*) from delivery_audit_log where transaction_id=:id and event_type='delivery_queued'"),{'id':tid})==1
    assert len(published)==1


@pytest.mark.asyncio
@pytest.mark.parametrize('phase',['normal','replay','refund'])
async def test_f7_actual_payment_helper_omitted_order_id(db,monkeypatch,phase):
    from sqlalchemy.ext.asyncio import AsyncSession
    from fastapi import HTTPException
    from app.api.v1.endpoints import webhooks
    oid,tid,pi,ch,token,claims=await f7_delivery(db)
    async def sessions():
        async with AsyncSession(db.bind,expire_on_commit=False) as session:yield session
    monkeypatch.setattr(webhooks,'get_async_db',sessions)
    event='evt_'+uuid.uuid4().hex
    if phase!='normal':await webhooks._create_delivery_for_payment(event,pi)
    if phase=='refund':await f7_apply_full(db,pi,ch)
    before=await f7_snapshot(db,oid,tid);await db.commit()
    if phase=='refund':
        with pytest.raises(HTTPException):await webhooks._create_delivery_for_payment(event,pi)
        assert await f7_snapshot(db,oid,tid)==before
    else:
        await webhooks._create_delivery_for_payment(event,pi)
        row=(await db.execute(text('select transaction_id,order_id from stripe_webhook_idempotency where event_id=:id'),{'id':event})).one()
        assert tuple(row)==(tid,oid)
        if phase=='replay':assert await f7_snapshot(db,oid,tid)==before


@pytest.mark.asyncio
async def test_f7_genuine_signed_payment_webhook_delivery_entry(db,monkeypatch):
    import time
    from test_refund_webhook_protocol import signed_post
    from app.core import stripe_async
    oid,tid,pi,ch,token,claims=await f7_delivery(db)
    async def provider(fn,*args,**kwargs):
        assert fn.__name__=='retrieve'
        assert args[0] in (pi['id'],ch['id'])
        return pi if args[0]==pi['id'] else ch
    monkeypatch.setattr(stripe_async,'run_stripe',provider)
    event={'id':'evt_'+uuid.uuid4().hex,'object':'event','created':int(time.time()),'type':'payment_intent.succeeded','livemode':False,'data':{'object':pi}}
    response=await signed_post(db,monkeypatch,event)
    assert response.status_code==200,response.text
    assert await db.scalar(text('select order_id from stripe_webhook_idempotency where event_id=:id'),{'id':event['id']})==oid
    assert await db.scalar(text("select metadata->>'delivery_record_created' from transactions where id=:id"),{'id':tid})=='true'
    assert await db.scalar(text('select count(*) from payments where stripe_payment_intent_id=:pi'),{'pi':pi['id']})==1


@pytest.mark.asyncio
@pytest.mark.parametrize('wrong_buyer',[False,True])
async def test_f7_actual_authenticated_token_route(db,wrong_buyer):
    from fastapi import FastAPI
    from httpx import AsyncClient,ASGITransport
    from app.api.v1.endpoints import deliveries
    from app.core.security import create_access_token
    from app.core.database import get_async_db
    oid,tid,pi,ch,token,claims=await f7_delivery(db)
    buyer=claims.buyer_id
    if wrong_buyer:
        buyer=await db.scalar(text('select seller_id from transactions where id=:id'),{'id':tid})
    before=await f7_snapshot(db,oid,tid);await db.commit()
    app=FastAPI();app.include_router(deliveries.router)
    async def database():yield db
    app.dependency_overrides[get_async_db]=database
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        response=await client.post(f'/deliveries/{tid}/token',headers={'Authorization':'Bearer '+create_access_token({'sub':str(buyer)})})
    if wrong_buyer:
        assert response.status_code==403,response.text
        await db.rollback();assert await f7_snapshot(db,oid,tid)==before
    else:
        assert response.status_code==200,response.text
        assert response.json()['token']==token['token']


@pytest.mark.asyncio
@pytest.mark.parametrize('chunk_size',[16384,32768,65536,131072,262144])
async def test_f7_actual_reader_concrete_bound(db,tmp_path,chunk_size):
    from app.services.delivery_service import DeliveryService,MAX_CHUNK_BYTES
    data=b'x'*(chunk_size*2+7);path=tmp_path/'bounded.bin';path.write_bytes(data)
    reader=DeliveryService(db)._open_vz_stream({'descriptor':{'source_path':str(path),'stream_chunk_size':chunk_size}},3,len(data)-2)
    try:chunks=[chunk async for chunk in reader]
    finally:await reader.aclose()
    assert b''.join(chunks)==data[3:-1]
    assert max(map(len,chunks))==chunk_size<=MAX_CHUNK_BYTES


@pytest.mark.asyncio
@pytest.mark.parametrize('callback',['progress','finalize','fail'])
@pytest.mark.parametrize('mutation',['attempt','jti','expired'])
async def test_f7_stale_callbacks_preserve_every_snapshot(db,callback,mutation):
    from fastapi import HTTPException
    from app.services.delivery_service import DeliveryService
    oid,tid,pi,ch,token,claims=await f7_delivery(db)
    svc=DeliveryService(db)
    await svc._record_range_progress(transaction_id=tid,attempt=claims.attempt,jti=claims.jti,start=0,end=3)
    if mutation=='expired':
        await db.execute(text("update transactions set delivery_expires_at=now()-interval '1s' where id=:id"),{'id':tid})
    else:
        new={'active_attempt':claims.attempt+1 if mutation=='attempt' else claims.attempt,'jti':uuid.uuid4().hex if mutation=='jti' else claims.jti,'ranges':[[0,3]]}
        await db.execute(text("update transactions set metadata=jsonb_set(metadata,'{delivery}',cast(:state as jsonb)) where id=:id"),{'id':tid,'state':json.dumps(new)})
    await db.commit();before=await f7_snapshot(db,oid,tid);await db.commit()
    with pytest.raises(HTTPException) as exc:
        if callback=='progress':await svc._record_range_progress(transaction_id=tid,attempt=claims.attempt,jti=claims.jti,start=0,end=3)
        elif callback=='finalize':await svc._finalize_stream_if_complete(tid,claims,200)
        else:await svc.fail_delivery(tid,reason='late',error_message='late',attempt=claims.attempt,jti=claims.jti)
    assert exc.value.status_code==(401 if mutation=='expired' else 410)
    await db.rollback();assert await f7_snapshot(db,oid,tid)==before


@pytest.mark.asyncio
@pytest.mark.parametrize('conflict',['replay','payload','event','transaction','order'])
async def test_f7_idempotency_conflict_and_omitted_parent_replay(db,conflict):
    from fastapi import HTTPException
    from app.services.delivery_service import DeliveryService
    oid,tid,pi,ch,token,claims=await f7_delivery(db)
    args=dict(event_id='evt_'+uuid.uuid4().hex,event_type='payment_intent.succeeded',idempotency_key=uuid.uuid4().hex,payload_hash='a'*64,transaction_id=tid)
    svc=DeliveryService(db)
    assert await svc.record_stripe_webhook_idempotency(**args)
    before=await f7_snapshot(db,oid,tid);await db.commit()
    if conflict=='replay':
        del args['transaction_id']
        assert await svc.record_stripe_webhook_idempotency(**args) is False
    else:
        if conflict=='payload':args['payload_hash']='b'*64
        if conflict=='event':args['event_id']='evt_'+uuid.uuid4().hex
        if conflict=='transaction':args['transaction_id']=uuid.uuid4()
        if conflict=='order':args['order_id']=uuid.uuid4()
        with pytest.raises(HTTPException) as exc:await svc.record_stripe_webhook_idempotency(**args)
        assert exc.value.status_code==409
        await db.rollback()
    assert await f7_snapshot(db,oid,tid)==before


@pytest.mark.asyncio
async def test_f7_exhausted_new_attempt_preserves_active_credential(db):
    from fastapi import HTTPException
    from app.services.delivery_service import DeliveryService
    oid,tid,pi,ch,token,claims=await f7_delivery(db)
    await db.execute(text('update transactions set delivery_max_attempts=delivery_attempts_used where id=:id'),{'id':tid})
    await db.commit();before=await f7_snapshot(db,oid,tid);await db.commit()
    with pytest.raises(HTTPException) as exc:await DeliveryService(db).generate_delivery_token(tid,buyer_id=claims.buyer_id,reuse_active_attempt=False)
    assert exc.value.status_code==409
    await db.rollback();assert await f7_snapshot(db,oid,tid)==before
    assert (await DeliveryService(db).validate_token(token['token']))[0].jti==claims.jti


@pytest.mark.asyncio
@pytest.mark.parametrize('partial',[False,True])
async def test_f7_normal_and_partial_dispute_remains_a_restriction(db,partial):
    from fastapi import HTTPException
    from app.services.delivery_service import DeliveryService
    oid,tid,pi,ch,token,claims=await f7_delivery(db)
    svc=DeliveryService(db)
    await svc._record_range_progress(transaction_id=tid,attempt=claims.attempt,jti=claims.jti,start=0,end=3)
    await svc._finalize_stream_if_complete(tid,claims,200)
    if partial:
        ch['amount_refunded']=333
        await process(db,await signed_event(db,ch),pi,ch,[refund(ch,333,uuid.uuid4().hex)])
    before=await f7_snapshot(db,oid,tid);await db.commit()
    assert (await svc.dispute_delivery(tid,actor_type='buyer',actor_id=claims.buyer_id,category='quality',reason='test dispute'))['status']=='disputed'
    after=await f7_snapshot(db,oid,tid)
    for field in ('orders','order_money_states','payments','refunds','journals','journal_lines','agent_spend'):assert after[field]==before[field]
    assert after['transactions'][0]['delivery_delivered_at']==before['transactions'][0]['delivery_delivered_at']
    with pytest.raises(HTTPException):await svc.validate_token(token['token'])
    await db.rollback();assert await f7_snapshot(db,oid,tid)==after


@pytest.mark.asyncio
@pytest.mark.parametrize('provider_status', ['succeeded','processing','requires_payment_method','requires_confirmation','requires_action','requires_capture','canceled','unexpected'])
async def test_durable_agent_provider_status_and_repeat(db,monkeypatch,provider_status):
    from fastapi import HTTPException
    from test_refund_webhook_protocol import owned_notifications
    svc,tx,key,pi,ch,calls=await agent_checkout_candidate(db,monkeypatch,provider_status=provider_status)
    async with owned_notifications(db.bind):
        if provider_status in {'succeeded','processing'}:
            result=await svc.create_agent_checkout(tx['id'],key)
            assert result['checkout_id']==pi['id'] and result['status']=='agent_payment_pending'
        else:
            with pytest.raises(HTTPException) as refused:
                await svc.create_agent_checkout(tx['id'],key)
            assert refused.value.status_code==(422 if provider_status in {'requires_action','canceled'} else 409)
    row=(await db.execute(text('SELECT * FROM transactions WHERE id=:id'),{'id':tx['id']})).mappings().one()
    attempt=row['metadata']['canonical_agent_attempt_v1']
    assert len(attempt)==28 and attempt['original_order_id']==str(row['order_id'])
    assert await db.scalar(text('SELECT count(*) FROM orders WHERE transaction_id=:id'),{'id':tx['id']})==1
    assert len([c for c in calls if c[0]=='create'])==1
    assert len([c for c in calls if c[0]=='cancel'])==(1 if provider_status=='requires_action' else 0)
    assert await db.scalar(text('SELECT spend_used FROM agent_api_keys WHERE id=:id'),{'id':key})==(0 if provider_status in {'requires_action','canceled'} else 2500)
    original_id=row['order_id']
    await db.rollback()
    if provider_status in {'succeeded','processing'}:
        again=await svc.create_agent_checkout(tx['id'],key)
        assert again['order_id']==str(original_id)
    else:
        with pytest.raises(HTTPException) as repeated:
            await svc.create_agent_checkout(tx['id'],key)
        assert repeated.value.status_code==(422 if provider_status in {'requires_action','canceled'} else 409)
    assert len([c for c in calls if c[0]=='create'])==1
    assert len([c for c in calls if c[0]=='cancel'])==(1 if provider_status=='requires_action' else 0)
    if provider_status in {'requires_action','canceled'}:
        assert attempt['state']=='cancelled_reconciled' and attempt['spend_release_state']=='released'
        assert len(attempt['release_evidence'])==7
        assert await db.scalar(text("SELECT count(*) FROM agent_audit_log WHERE transaction_id=:id AND http_status=422"),{'id':tx['id']})==1


@pytest.mark.asyncio
@pytest.mark.parametrize('boundary', ['prepared', 'provider_response', 'bound'])
async def test_durable_agent_signed_success_original_identity_recovery(db,monkeypatch,boundary):
    from fastapi import HTTPException
    from test_refund_webhook_protocol import owned_notifications,signed_post
    from app.models.transaction import Transaction
    from app.services.order_money_service import AGENT_ATTEMPT_KEY
    svc,tx,key,pi,ch,calls=await agent_checkout_candidate(db,monkeypatch,provider_status='succeeded')
    import stripe
    if boundary=='prepared':
        def lost_response(**kwargs):
            calls.append(('create',kwargs.copy()));pi['metadata']=kwargs['metadata'].copy()
            raise RuntimeError('controlled response loss after provider creation')
        monkeypatch.setattr(stripe.PaymentIntent,'create',lost_response)
    original=svc._apply_agent_observation
    if boundary=='provider_response':
        async def lost_binding(*args,**kwargs):
            raise RuntimeError('controlled binding transaction failure')
        monkeypatch.setattr(svc,'_apply_agent_observation',lost_binding)
    async with owned_notifications(db.bind):
        if boundary=='bound':
            await svc.create_agent_checkout(tx['id'],key)
        else:
            with pytest.raises(HTTPException) as refused:
                await svc.create_agent_checkout(tx['id'],key)
            assert refused.value.status_code==409
    monkeypatch.setattr(svc,'_apply_agent_observation',original)
    before=(await db.execute(text('SELECT order_id,metadata FROM transactions WHERE id=:id'),{'id':tx['id']})).mappings().one()
    oid=before['order_id'];attempt_id=before['metadata'][AGENT_ATTEMPT_KEY]['attempt_id']
    assert await db.scalar(text('SELECT count(*) FROM order_money_states WHERE order_id=:id'),{'id':oid})==0
    event={'id':'evt_'+uuid.uuid4().hex,'object':'event','created':int(datetime.now(timezone.utc).timestamp()),
        'type':'payment_intent.succeeded','livemode':False,'data':{'object':dict(pi)}}
    await db.rollback()
    from app.api.v1.endpoints import webhooks
    original_billing=webhooks._billing_service.handle_stripe_event
    async def traced(*args,**kwargs):
        try:
            return await original_billing(*args,**kwargs)
        except Exception:
            import traceback
            traceback.print_exc()
            raise
    monkeypatch.setattr(webhooks._billing_service,'handle_stripe_event',traced)
    response=await signed_post(db,monkeypatch,event)
    assert response.status_code==200,response.text
    await db.rollback()
    row=(await db.execute(text('SELECT * FROM transactions WHERE id=:id'),{'id':tx['id']})).mappings().one()
    assert row['order_id']==oid and row['stripe_payment_intent_id']==pi['id']
    assert row['metadata'][AGENT_ATTEMPT_KEY]['attempt_id']==attempt_id
    assert row['metadata'][AGENT_ATTEMPT_KEY]['state']=='completed'
    assert row['paid_at'] is not None
    assert await db.scalar(text('SELECT count(*) FROM payments WHERE stripe_payment_intent_id=:pi'),{'pi':pi['id']})==1
    snapshot=await f6_snapshot(db,oid,tx['id'],key)
    await db.rollback()
    assert (await signed_post(db,monkeypatch,event)).status_code==200
    await db.rollback()
    assert await f6_snapshot(db,oid,tx['id'],key)==snapshot
    cached=await svc.create_agent_checkout(tx['id'],key)
    assert cached['order_id']==str(oid) and cached['checkout_id']==pi['id']
    assert len([c for c in calls if c[0]=='create'])==1
    assert not [c for c in calls if c[0]=='cancel']


async def durable_prepared_candidate(db,monkeypatch):
    from fastapi import HTTPException
    from test_refund_webhook_protocol import owned_notifications
    import stripe
    svc,tx,key,pi,ch,calls=await agent_checkout_candidate(db,monkeypatch,provider_status='succeeded')
    def lose(**kwargs):
        calls.append(('create',kwargs.copy()));pi['metadata']=kwargs['metadata'].copy()
        raise RuntimeError('owned provider response lost')
    monkeypatch.setattr(stripe.PaymentIntent,'create',lose)
    async with owned_notifications(db.bind):
        with pytest.raises(HTTPException) as exc:await svc.create_agent_checkout(tx['id'],key)
    assert exc.value.status_code==409
    row=(await db.execute(text('SELECT order_id,metadata FROM transactions WHERE id=:id'),{'id':tx['id']})).mappings().one()
    await db.rollback()
    return svc,tx,key,pi,ch,calls,row['order_id'],row['metadata']['canonical_agent_attempt_v1']


@pytest.mark.asyncio
@pytest.mark.parametrize('boundary',['before_prepare_commit','after_prepare_commit','before_binding_commit','after_binding_commit'])
async def test_durable_agent_commit_acknowledgement_loss(db,monkeypatch,boundary):
    from fastapi import HTTPException
    from test_refund_webhook_protocol import owned_notifications
    svc,tx,key,pi,ch,calls=await agent_checkout_candidate(db,monkeypatch,provider_status='succeeded')
    original=db.commit;seen=[]
    async def interrupted():
        await db.flush()
        row=(await db.execute(text('SELECT metadata FROM transactions WHERE id=:id'),{'id':tx['id']})).scalar_one()
        attempt=(row or {}).get('canonical_agent_attempt_v1')
        phase='prepare' if attempt and attempt['state']=='prepared_unknown' else 'binding'
        if phase in boundary and not seen:
            seen.append(phase)
            if boundary.startswith('after'):await original()
            raise ConnectionError('controlled commit acknowledgement loss '+boundary)
        return await original()
    monkeypatch.setattr(db,'commit',interrupted)
    async with owned_notifications(db.bind):
        with pytest.raises((HTTPException,ConnectionError)):
            await svc.create_agent_checkout(tx['id'],key)
    monkeypatch.setattr(db,'commit',original)
    await db.rollback();assert seen
    count=await db.scalar(text('SELECT count(*) FROM orders WHERE transaction_id=:id'),{'id':tx['id']})
    assert count==(0 if boundary=='before_prepare_commit' else 1)
    before_calls=len([c for c in calls if c[0]=='create'])
    if boundary!='before_prepare_commit':
        row=(await db.execute(text('SELECT order_id,metadata FROM transactions WHERE id=:id'),{'id':tx['id']})).mappings().one()
        await db.rollback()
        try:result=await svc.create_agent_checkout(tx['id'],key)
        except HTTPException as exc:assert exc.status_code in (409,503)
        else:assert result['order_id']==str(row['order_id'])
        assert len([c for c in calls if c[0]=='create'])==before_calls
        assert await db.scalar(text('SELECT count(*) FROM orders WHERE transaction_id=:id'),{'id':tx['id']})==1
    assert await db.scalar(text('SELECT spend_used FROM agent_api_keys WHERE id=:id'),{'id':key})==2500
    assert not [c for c in calls if c[0]=='cancel']


@pytest.mark.asyncio
async def test_durable_agent_two_preparations_one_order_and_dispatch(db,monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.services.transaction_service import TransactionService
    from test_refund_webhook_protocol import owned_notifications
    from fastapi import HTTPException
    svc,tx,key,pi,ch,calls=await agent_checkout_candidate(db,monkeypatch,provider_status='processing')
    await db.rollback()
    original=TransactionService._prepare_agent_checkout
    import asyncio
    arrivals=[];barrier=asyncio.Event()
    async def together(self,*args,**kwargs):
        arrivals.append(True)
        if len(arrivals)==2:barrier.set()
        await asyncio.wait_for(barrier.wait(),2)
        return await original(self,*args,**kwargs)
    monkeypatch.setattr(TransactionService,'_prepare_agent_checkout',together)
    async def contender():
        async with AsyncSession(db.bind,expire_on_commit=False) as session:
            try:return await TransactionService(session).create_agent_checkout(tx['id'],key)
            except Exception as exc:return exc
    async with owned_notifications(db.bind):results=await asyncio.gather(contender(),contender())
    assert len(arrivals)==2
    winners=[r for r in results if isinstance(r,dict)]
    assert len(winners)<=1,repr(results)
    for refusal in [r for r in results if not isinstance(r,dict)]:
        assert isinstance(refusal,HTTPException) and refusal.status_code in (409,503),repr(results)
    if not winners:
        # Simultaneous FK KEY SHARE upgrades may both time out. Both candidate
        # transactions are known rolled back and neither dispatched a provider.
        assert not [c for c in calls if c[0]=='create']
        assert await db.scalar(text('SELECT count(*) FROM orders WHERE transaction_id=:id'),{'id':tx['id']})==0
        await db.rollback()
        monkeypatch.setattr(TransactionService,'_prepare_agent_checkout',original)
        async with owned_notifications(db.bind):await svc.create_agent_checkout(tx['id'],key)
    assert len([c for c in calls if c[0]=='create'])==1
    assert await db.scalar(text('SELECT count(*) FROM orders WHERE transaction_id=:id'),{'id':tx['id']})==1
    assert await db.scalar(text('SELECT spend_used FROM agent_api_keys WHERE id=:id'),{'id':key})==2500
    row=(await db.execute(text('SELECT order_id,metadata FROM transactions WHERE id=:id'),{'id':tx['id']})).mappings().one()
    assert row['metadata']['canonical_agent_attempt_v1']['original_order_id']==str(row['order_id'])


@pytest.mark.asyncio
async def test_durable_agent_signed_capture_before_provider_return(db,monkeypatch):
    import stripe
    from app.core import stripe_async
    from test_refund_webhook_protocol import owned_notifications,signed_post
    svc,tx,key,pi,ch,calls=await agent_checkout_candidate(db,monkeypatch,provider_status='succeeded')
    run=stripe_async.run_stripe;responses=[]
    async def callback(function,*args,**kwargs):
        value=await run(function,*args,**kwargs)
        if function is stripe.PaymentIntent.create:
            event={'id':'evt_'+uuid.uuid4().hex,'object':'event','type':'payment_intent.succeeded','livemode':False,
                'created':int(datetime.now(timezone.utc).timestamp()),'data':{'object':dict(pi)}}
            response=await signed_post(db,monkeypatch,event);responses.append(response.status_code)
            assert response.status_code==200,response.text
        return value
    monkeypatch.setattr(stripe_async,'run_stripe',callback)
    async with owned_notifications(db.bind):result=await svc.create_agent_checkout(tx['id'],key)
    assert responses==[200] and result['checkout_id']==pi['id']
    row=(await db.execute(text('SELECT order_id,metadata FROM transactions WHERE id=:id'),{'id':tx['id']})).mappings().one()
    assert row['metadata']['canonical_agent_attempt_v1']['state']=='completed'
    assert await db.scalar(text('SELECT count(*) FROM payments WHERE stripe_payment_intent_id=:pi'),{'pi':pi['id']})==1
    assert len([c for c in calls if c[0]=='create'])==1


@pytest.mark.asyncio
@pytest.mark.parametrize('state',['prepared_unknown','response_observed','bound_pending','cancellation_unknown','conflict_reconciliation','cancelled_reconciled','completed'])
async def test_durable_agent_actual_cleanup_excludes_every_state(db,monkeypatch,state):
    import inspect,stripe
    from contextlib import asynccontextmanager
    from sqlalchemy.ext.asyncio import AsyncSession
    from fastapi import HTTPException
    from app.tasks import scheduled
    from test_refund_webhook_protocol import owned_notifications,signed_post
    status={'response_observed':'requires_payment_method','bound_pending':'processing','cancellation_unknown':'requires_action',
        'conflict_reconciliation':'unexpected','cancelled_reconciled':'canceled','completed':'succeeded'}.get(state,'succeeded')
    if state=='prepared_unknown':
        svc,tx,key,pi,ch,calls,oid,attempt=await durable_prepared_candidate(db,monkeypatch)
    else:
        svc,tx,key,pi,ch,calls=await agent_checkout_candidate(db,monkeypatch,provider_status=status)
        if state=='cancellation_unknown':
            def unknown(*args,**kwargs):calls.append(('cancel',args));raise RuntimeError('owned cancellation unknown')
            monkeypatch.setattr(stripe.PaymentIntent,'cancel',unknown)
        async with owned_notifications(db.bind):
            try:await svc.create_agent_checkout(tx['id'],key)
            except HTTPException as exc:assert exc.status_code in (409,422)
        oid=await db.scalar(text('SELECT order_id FROM transactions WHERE id=:id'),{'id':tx['id']})
        await db.rollback()
        if state=='completed':
            event={'id':'evt_'+uuid.uuid4().hex,'object':'event','type':'payment_intent.succeeded','livemode':False,
                'created':int(datetime.now(timezone.utc).timestamp()),'data':{'object':dict(pi)}}
            assert (await signed_post(db,monkeypatch,event)).status_code==200
    await db.execute(text("UPDATE transactions SET created_at=NOW()-INTERVAL '2 hours' WHERE id=:id"),{'id':tx['id']})
    await db.commit()
    row=(await db.execute(text('SELECT metadata FROM transactions WHERE id=:id'),{'id':tx['id']})).scalar_one()
    assert row['canonical_agent_attempt_v1']['state']==state
    before=await f6_snapshot(db,oid,tx['id'],key);await db.rollback()
    @asynccontextmanager
    async def owned():
        async with AsyncSession(db.bind) as session:yield session
    monkeypatch.setattr(scheduled,'AsyncSessionLocal',owned)
    fn=inspect.unwrap(scheduled.cleanup_stuck_agent_transactions.run)
    await fn(None) if len(inspect.signature(fn).parameters) else await fn()
    assert await f6_snapshot(db,oid,tx['id'],key)==before
    # Direct writer admission is also refused, including terminal noncandidates.
    await db.rollback()
    assert await svc.lock_stale_agent_payment(tx['id'],oid) is None
    await db.rollback()


@pytest.mark.asyncio
@pytest.mark.parametrize('field', sorted(__import__('app.services.order_money_service',fromlist=['AGENT_ATTEMPT_FIELDS']).AGENT_ATTEMPT_FIELDS))
async def test_durable_agent_closed_record_missing_field_refuses_without_effects(db,monkeypatch,field):
    from fastapi import HTTPException
    from app.services.order_money_service import AGENT_ATTEMPT_KEY
    svc,tx,key,pi,ch,calls,oid,attempt=await durable_prepared_candidate(db,monkeypatch)
    del attempt[field]
    await db.execute(text('UPDATE transactions SET metadata=jsonb_set(metadata,CAST(:path AS text[]),CAST(:record AS jsonb)) WHERE id=:id'),
        {'path':[AGENT_ATTEMPT_KEY],'record':json.dumps(attempt),'id':tx['id']})
    await db.commit();before=await f6_snapshot(db,oid,tx['id'],key);await db.rollback()
    with pytest.raises(HTTPException) as exc:await svc.create_agent_checkout(tx['id'],key)
    assert exc.value.status_code==409
    assert await f6_snapshot(db,oid,tx['id'],key)==before
    assert len([c for c in calls if c[0]=='create'])==1 and not [c for c in calls if c[0]=='cancel']


@pytest.mark.asyncio
@pytest.mark.parametrize('field,bad',[('version',True),('revision',0),('revision',2147483648),('amount_cents',True),
    ('currency','USD'),('buyer_id','not-a-uuid'),('prepared_at','2026-09-12T00:00:00Z'),('state',[]),
    ('customer_id','cus whitespace'),('livemode',1),('request_metadata',{}),('spend_release_state','released'),
    ('release_evidence',{}),('extra_key','arbitrary')])
async def test_durable_agent_closed_record_malformed_field_refuses(db,monkeypatch,field,bad):
    from fastapi import HTTPException
    svc,tx,key,pi,ch,calls,oid,attempt=await durable_prepared_candidate(db,monkeypatch)
    attempt[field]=bad
    await db.execute(text("UPDATE transactions SET metadata=jsonb_set(metadata,'{canonical_agent_attempt_v1}',CAST(:record AS jsonb)) WHERE id=:id"),{'record':json.dumps(attempt),'id':tx['id']})
    await db.commit();before=await f6_snapshot(db,oid,tx['id'],key);await db.rollback()
    with pytest.raises(HTTPException) as exc:await svc.create_agent_checkout(tx['id'],key)
    assert exc.value.status_code==409
    assert await f6_snapshot(db,oid,tx['id'],key)==before


@pytest.mark.asyncio
@pytest.mark.parametrize('field,bad',[('customer','cus_foreign'),('payment_method','pm_foreign'),('amount',2501),
    ('currency','eur'),('livemode',True),('metadata',{}),('amount_received',True),('amount_capturable',None),
    ('status',None),('status','cancelled'),('on_behalf_of','acct_foreign')])
async def test_durable_agent_foreign_or_incomplete_response_never_cancels(db,monkeypatch,field,bad):
    from fastapi import HTTPException
    from test_refund_webhook_protocol import owned_notifications
    svc,tx,key,pi,ch,calls=await agent_checkout_candidate(db,monkeypatch,provider_status='requires_action')
    # The actual create boundary echoes request metadata; mutate its returned
    # object after that echo to exercise the installed scalar adapter.
    import stripe
    original=stripe.PaymentIntent.create
    def foreign(**kwargs):
        result=original(**kwargs);result[field]=bad;return result
    monkeypatch.setattr(stripe.PaymentIntent,'create',foreign)
    async with owned_notifications(db.bind):
        with pytest.raises(HTTPException) as exc:await svc.create_agent_checkout(tx['id'],key)
    assert exc.value.status_code==409
    assert not [c for c in calls if c[0]=='cancel']
    row=(await db.execute(text('SELECT order_id,stripe_payment_intent_id,metadata FROM transactions WHERE id=:id'),{'id':tx['id']})).mappings().one()
    assert row['metadata']['canonical_agent_attempt_v1']['state']=='conflict_reconciliation'
    assert row['stripe_payment_intent_id'] is None
    assert await db.scalar(text('SELECT spend_used FROM agent_api_keys WHERE id=:id'),{'id':key})==2500
    assert await db.scalar(text('SELECT count(*) FROM order_money_states WHERE order_id=:id'),{'id':row['order_id']})==0


async def canonical_initial_pair(db, *, mode='checkout_completion', asymmetric=False):
    from app.services.order_money_service import ExpectedPaymentBinding
    oid,tid,pi,ch=await purchase(db,'checkout_pending')
    sid='cs_'+uuid.uuid4().hex
    await db.execute(text("UPDATE orders SET status='created',stripe_checkout_session_id=:sid,stripe_payment_intent_id=:pi WHERE id=:id"),
        {'sid':sid if mode!='direct_payment_completion' else None,'pi':pi['id'] if asymmetric else None,'id':oid})
    await db.execute(text("UPDATE transactions SET status='checkout_pending',stripe_payment_intent_id=NULL WHERE id=:id"),{'id':tid})
    row=(await db.execute(text('SELECT * FROM orders WHERE id=:id'),{'id':oid})).mappings().one()
    b=ExpectedPaymentBinding(uuid.UUID(str(oid)),uuid.UUID(str(tid)),row['stripe_checkout_session_id'],
        sid if mode!='direct_payment_completion' else None,pi['id'],2500,'USD',uuid.UUID(str(row['buyer_id'])),
        uuid.UUID(str(row['seller_id'])),uuid.UUID(str(row['listing_id'])),125,2375)
    await db.commit()
    return oid,tid,pi,ch,b


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['checkout_completion','direct_payment_completion','signed_capture_recovery','agent_attempt_completion'])
@pytest.mark.parametrize('asymmetric',[False,True])
async def test_canonical_initial_four_mode_state_admission(db,mode,asymmetric):
    from app.services.order_money_service import bind_initial_order_payment_intent
    oid,tid,pi,ch,b=await canonical_initial_pair(db,mode=mode,asymmetric=asymmetric)
    before=await f7_snapshot(db,oid,tid);await db.rollback()
    allowed=mode=='checkout_completion' or (mode=='direct_payment_completion' and asymmetric)
    if allowed:
        await bind_initial_order_payment_intent(db,order_id=oid,payment_intent_id=pi['id'],expected_transaction_id=tid,mode=mode,expected_binding=b)
        await db.commit()
        assert await db.scalar(text('SELECT stripe_payment_intent_id FROM transactions WHERE id=:id'),{'id':tid})==pi['id']
        assert await db.scalar(text('SELECT stripe_payment_intent_id FROM orders WHERE id=:id'),{'id':oid})==pi['id']
        assert await db.scalar(text('SELECT count(*) FROM order_money_states WHERE order_id=:id'),{'id':oid})==0
    else:
        with pytest.raises(OrderMoneyConflict):
            await bind_initial_order_payment_intent(db,order_id=oid,payment_intent_id=pi['id'],expected_transaction_id=tid,mode=mode,expected_binding=b)
        await db.rollback();assert await f7_snapshot(db,oid,tid)==before


@pytest.mark.asyncio
@pytest.mark.parametrize('field',['order_id','transaction_id','stored_checkout_session_id','signed_checkout_session_id','signed_payment_intent_id',
    'signed_amount_cents','signed_currency','buyer_id','seller_id','listing_id','platform_fee_cents','seller_amount_cents'])
async def test_canonical_expected_binding_every_fact_refuses_without_partial_state(db,field):
    from dataclasses import replace
    from app.services.order_money_service import bind_initial_order_payment_intent
    oid,tid,pi,ch,b=await canonical_initial_pair(db)
    before=await f7_snapshot(db,oid,tid);await db.rollback()
    value=getattr(b,field)
    changed=uuid.uuid4() if isinstance(value,uuid.UUID) else value+1 if type(value) is int else 'EUR' if field=='signed_currency' else value+'_foreign'
    with pytest.raises(OrderMoneyConflict):
        bad=replace(b,**{field:changed})
        await bind_initial_order_payment_intent(db,order_id=oid,payment_intent_id=pi['id'],expected_transaction_id=tid,mode='checkout_completion',expected_binding=bad)
    await db.rollback();assert await f7_snapshot(db,oid,tid)==before


@pytest.mark.asyncio
@pytest.mark.parametrize('fault',['none','missing_session','wrong_session','revoked','money_exists','provider_metadata','provider_currency'])
async def test_canonical_original_failed_signed_capture_recovery(db,monkeypatch,fault):
    from test_refund_webhook_protocol import signed_post
    import stripe
    oid,tid,pi,ch,b=await canonical_initial_pair(db,asymmetric=True)
    # Faithfully stage the historic completed checkout with its dedicated Tx PI
    # missing. No Payment/MoneyState/journal is fabricated for the recovery.
    await db.execute(text("UPDATE orders SET status='pending_delivery',paid_at=NOW() WHERE id=:id"),{'id':oid})
    await db.execute(text("UPDATE transactions SET status='paid',paid_at=NOW() WHERE id=:id"),{'id':tid})
    checkout={'id':'evt_'+uuid.uuid4().hex,'type':'checkout.session.completed','livemode':False,
        'data':{'object':{'id':b.stored_checkout_session_id,'payment_intent':pi['id'],'metadata':pi['metadata']}}}
    await db.execute(text("INSERT INTO stripe_events(stripe_event_id,event_type,payload_json,signature_valid,status) VALUES(:id,'checkout.session.completed',CAST(:payload AS jsonb),true,'completed')"),{'id':checkout['id'],'payload':json.dumps(checkout)})
    if fault=='missing_session':await db.execute(text('UPDATE orders SET stripe_checkout_session_id=NULL WHERE id=:id'),{'id':oid})
    if fault=='wrong_session':await db.execute(text("UPDATE orders SET stripe_checkout_session_id='cs_foreign' WHERE id=:id"),{'id':oid})
    if fault=='revoked':await db.execute(text('UPDATE orders SET revoked=true WHERE id=:id'),{'id':oid})
    if fault=='money_exists':
        # Adversarial empty authority, explicitly not a normal finance fixture.
        await db.execute(text('INSERT INTO order_money_states(order_id,transaction_id) VALUES(:oid,:tid)'),{'oid':oid,'tid':tid})
    event={'id':'evt_'+uuid.uuid4().hex,'object':'event','type':'payment_intent.succeeded','livemode':False,
        'created':int(datetime.now(timezone.utc).timestamp()),'data':{'object':dict(pi)}}
    await db.commit()
    original_pi=pi.copy()
    if fault=='provider_metadata':pi={**pi,'metadata':{**pi['metadata'],'order_id':str(uuid.uuid4())}}
    if fault=='provider_currency':pi={**pi,'currency':'eur'}
    monkeypatch.setattr(stripe.PaymentIntent,'retrieve',lambda ident:pi.copy())
    monkeypatch.setattr(stripe.Charge,'retrieve',lambda ident:ch.copy())
    response=await signed_post(db,monkeypatch,event)
    assert response.status_code==(200 if fault=='none' else 500),response.text
    await db.rollback()
    if fault!='none':
        assert await db.scalar(text('SELECT stripe_payment_intent_id FROM transactions WHERE id=:id'),{'id':tid}) is None
        assert await db.scalar(text('SELECT count(*) FROM payments WHERE stripe_payment_intent_id=:pi'),{'pi':pi['id']})==0
        assert await db.scalar(text('SELECT status FROM stripe_events WHERE stripe_event_id=:id'),{'id':event['id']})=='failed'
        return
    assert await db.scalar(text('SELECT stripe_payment_intent_id FROM transactions WHERE id=:id'),{'id':tid})==pi['id']
    assert await db.scalar(text('SELECT count(*) FROM payments WHERE stripe_payment_intent_id=:pi'),{'pi':pi['id']})==1
    snapshot=await f7_snapshot(db,oid,tid);await db.rollback()
    assert (await signed_post(db,monkeypatch,event)).status_code==200
    await db.rollback();assert await f7_snapshot(db,oid,tid)==snapshot


@pytest.mark.asyncio
@pytest.mark.parametrize('condition',['received','capturable','insufficient','rollback','concurrent'])
async def test_durable_agent_terminal_release_liability_and_atomicity(db,monkeypatch,condition):
    import asyncio,stripe
    from fastapi import HTTPException
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.services.transaction_service import TransactionService
    from test_refund_webhook_protocol import owned_notifications
    svc,tx,key,pi,ch,calls=await agent_checkout_candidate(db,monkeypatch,provider_status='requires_action')
    def unknown(*args,**kwargs):calls.append(('cancel',args));raise RuntimeError('controlled cancel outcome unknown')
    monkeypatch.setattr(stripe.PaymentIntent,'cancel',unknown)
    async with owned_notifications(db.bind):
        with pytest.raises(HTTPException) as exc:await svc.create_agent_checkout(tx['id'],key)
    assert exc.value.status_code==409
    oid=await db.scalar(text('SELECT order_id FROM transactions WHERE id=:id'),{'id':tx['id']})
    pi.update(status='canceled',amount_received=1 if condition=='received' else 0,amount_capturable=1 if condition=='capturable' else 0)
    if condition=='insufficient':
        await db.execute(text('UPDATE agent_api_keys SET spend_used=2499 WHERE id=:id'),{'id':key});await db.commit()
    before=await f6_snapshot(db,oid,tx['id'],key);await db.rollback()
    original=db.commit
    if condition=='rollback':
        async def fail():raise ConnectionError('release commit failed before commit')
        monkeypatch.setattr(db,'commit',fail)
    if condition=='concurrent':
        gate=asyncio.Event();arrivals=[];original_apply=TransactionService._apply_agent_observation
        async def together(self,*args,**kwargs):
            arrivals.append(True)
            if len(arrivals)==2:gate.set()
            await asyncio.wait_for(gate.wait(),2)
            return await original_apply(self,*args,**kwargs)
        monkeypatch.setattr(TransactionService,'_apply_agent_observation',together)
        async def run():
            async with AsyncSession(db.bind,expire_on_commit=False) as own:
                try:await TransactionService(own).reconcile_agent_checkout(tx['id'],key)
                except HTTPException as exc:return exc.status_code
        results=await asyncio.gather(run(),run())
        assert results==[422,422]
        assert await db.scalar(text('SELECT spend_used FROM agent_api_keys WHERE id=:id'),{'id':key})==0
        assert await db.scalar(text('SELECT count(*) FROM agent_audit_log WHERE transaction_id=:id AND http_status=422'),{'id':tx['id']})==1
    else:
        with pytest.raises(HTTPException) as exc:await svc.reconcile_agent_checkout(tx['id'],key)
        assert exc.value.status_code==(503 if condition=='rollback' else 409)
        monkeypatch.setattr(db,'commit',original)
        assert await f6_snapshot(db,oid,tx['id'],key)==before
    assert len([c for c in calls if c[0]=='create'])==1 and len([c for c in calls if c[0]=='cancel'])==1


@pytest.mark.asyncio
@pytest.mark.parametrize('amount',[333,2500])
async def test_durable_agent_captured_refund_preserves_attempt_and_consumed_spend(db,monkeypatch,amount):
    from fastapi import HTTPException
    from test_refund_webhook_protocol import owned_notifications,signed_post
    svc,tx,key,pi,ch,calls=await agent_checkout_candidate(db,monkeypatch,provider_status='succeeded')
    async with owned_notifications(db.bind):await svc.create_agent_checkout(tx['id'],key)
    oid=await db.scalar(text('SELECT order_id FROM transactions WHERE id=:id'),{'id':tx['id']});await db.rollback()
    event={'id':'evt_'+uuid.uuid4().hex,'object':'event','type':'payment_intent.succeeded','livemode':False,
        'created':int(datetime.now(timezone.utc).timestamp()),'data':{'object':dict(pi)}}
    assert (await signed_post(db,monkeypatch,event)).status_code==200
    record=(await db.execute(text("SELECT metadata->'canonical_agent_attempt_v1' FROM transactions WHERE id=:id"),{'id':tx['id']})).scalar_one()
    assert record['state']=='completed' and record['spend_release_state']=='held'
    # The actual signed success also invokes the normal delivery writer.
    assert await db.scalar(text("SELECT (metadata->>'delivery_record_created')::boolean FROM transactions WHERE id=:id"),{'id':tx['id']}) is True
    assert await db.scalar(text("SELECT count(*) FROM order_events WHERE order_id=:id AND event_type='paid'"),{'id':oid})==1
    assert await db.scalar(text('SELECT access_expires_at IS NOT NULL FROM orders WHERE id=:id'),{'id':oid}) is True
    ch['amount_refunded']=amount;r=refund(ch,amount,uuid.uuid4().hex);event2=await signed_event(db,ch)
    await process(db,event2,pi,ch,[r]);await process(db,event2,pi,ch,[r])
    after=await db.scalar(text("SELECT metadata->'canonical_agent_attempt_v1' FROM transactions WHERE id=:id"),{'id':tx['id']})
    assert after==record
    assert await db.scalar(text('SELECT spend_used FROM agent_api_keys WHERE id=:id'),{'id':key})==2500-amount
    before=await f7_snapshot(db,oid,tx['id']);await db.rollback()
    with pytest.raises(HTTPException) as exc:await svc.reconcile_agent_checkout(tx['id'],key)
    assert exc.value.status_code==409
    assert await f7_snapshot(db,oid,tx['id'])==before
    assert not [c for c in calls if c[0]=='cancel']


@pytest.mark.asyncio
@pytest.mark.parametrize('table',['orders','transactions','agent_api_keys'])
async def test_durable_agent_real_lock_timeout_returns_503_without_release(db,monkeypatch,table,record_property):
    import asyncio,time
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.services.transaction_service import TransactionService
    from fastapi import HTTPException
    from test_refund_webhook_protocol import owned_notifications
    svc,tx,key,pi,ch,calls=await agent_checkout_candidate(db,monkeypatch,provider_status='processing')
    async with owned_notifications(db.bind):await svc.create_agent_checkout(tx['id'],key)
    oid=await db.scalar(text('SELECT order_id FROM transactions WHERE id=:id'),{'id':tx['id']})
    before=await f6_snapshot(db,oid,tx['id'],key);await db.rollback()
    pi.update(status='canceled',amount_received=0,amount_capturable=0)
    ident={'orders':oid,'transactions':tx['id'],'agent_api_keys':key}[table]
    await db.execute(text('SELECT id FROM '+table+' WHERE id=:id FOR UPDATE'),{'id':ident})
    start=time.monotonic()
    async with AsyncSession(db.bind,expire_on_commit=False) as contender:
        with pytest.raises(HTTPException) as exc:
            await TransactionService(contender).reconcile_agent_checkout(tx['id'],key)
        assert exc.value.status_code==503
        assert exc.value.detail['code']=='AGENT_PAYMENT_RECONCILIATION_UNAVAILABLE'
    elapsed=time.monotonic()-start
    assert .20<=elapsed<2.5
    record_property('measured_lock_refusal_seconds',elapsed)
    await db.rollback();assert await f6_snapshot(db,oid,tx['id'],key)==before
    assert not [c for c in calls if c[0]=='cancel']


@pytest.mark.asyncio
@pytest.mark.parametrize('status',['succeeded','processing','requires_payment_method','requires_confirmation','requires_action','requires_capture','canceled','unexpected'])
async def test_durable_agent_signed_failure_requires_original_terminal_provider_proof(db,monkeypatch,status):
    from test_refund_webhook_protocol import signed_post
    svc,tx,key,pi,ch,calls,oid,attempt=await durable_prepared_candidate(db,monkeypatch)
    pi.update(status=status,amount_received=2500 if status=='succeeded' else 0,amount_capturable=2500 if status=='requires_capture' else 0)
    event={'id':'evt_'+uuid.uuid4().hex,'object':'event','type':'payment_intent.payment_failed','livemode':False,
        'created':int(datetime.now(timezone.utc).timestamp()),'data':{'object':dict(pi)}}
    response=await signed_post(db,monkeypatch,event)
    assert response.status_code==(200 if status=='canceled' else 500),response.text
    await db.rollback()
    assert await db.scalar(text('SELECT spend_used FROM agent_api_keys WHERE id=:id'),{'id':key})==(0 if status=='canceled' else 2500)
    assert await db.scalar(text('SELECT count(*) FROM order_money_states WHERE order_id=:id'),{'id':oid})==0
    if status=='canceled':
        before=await f6_snapshot(db,oid,tx['id'],key);await db.rollback()
        assert (await signed_post(db,monkeypatch,event)).status_code==200
        await db.rollback();assert await f6_snapshot(db,oid,tx['id'],key)==before
    else:
        assert await db.scalar(text('SELECT status FROM stripe_events WHERE stripe_event_id=:id'),{'id':event['id']})=='failed'
        assert await db.scalar(text('SELECT stripe_payment_intent_id FROM transactions WHERE id=:id'),{'id':tx['id']}) is None
    assert not [c for c in calls if c[0]=='cancel']
    assert len([c for c in calls if c[0]=='create'])==1


@pytest.mark.asyncio
async def test_durable_agent_distinct_signed_successes_one_capture_and_paid_event(db,monkeypatch):
    from test_refund_webhook_protocol import signed_post
    svc,tx,key,pi,ch,calls,oid,attempt=await durable_prepared_candidate(db,monkeypatch)
    committed=None
    for _ in range(2):
        event={'id':'evt_'+uuid.uuid4().hex,'object':'event','type':'payment_intent.succeeded','livemode':False,
            'created':int(datetime.now(timezone.utc).timestamp()),'data':{'object':dict(pi)}}
        assert (await signed_post(db,monkeypatch,event)).status_code==200
        await db.rollback()
        record=await db.scalar(text("SELECT metadata->'canonical_agent_attempt_v1' FROM transactions WHERE id=:id"),{'id':tx['id']})
        if committed is None:committed=record
        else:assert record==committed
        assert await db.scalar(text('SELECT count(*) FROM payments WHERE stripe_payment_intent_id=:pi'),{'pi':pi['id']})==1
        assert await db.scalar(text("SELECT count(*) FROM order_events WHERE order_id=:id AND event_type='paid'"),{'id':oid})==1
        await db.rollback()
    assert committed['state']=='completed' and len([c for c in calls if c[0]=='create'])==1


@pytest.mark.asyncio
@pytest.mark.parametrize('winner',['order','transaction'])
async def test_durable_agent_native_collision_arbitrates_before_foreign_cancellation(db,monkeypatch,winner):
    from fastapi import HTTPException
    from test_refund_webhook_protocol import owned_notifications
    import stripe
    svc,tx,key,pi,ch,calls=await agent_checkout_candidate(db,monkeypatch,provider_status='requires_action')
    seed=(await db.execute(text('SELECT id,transaction_id,stripe_payment_intent_id FROM orders WHERE listing_id=:id'),{'id':tx['listing_id']})).mappings().one()
    collision=seed['stripe_payment_intent_id']
    if winner=='transaction':
        # Adversarial pre-existing asymmetric winner; no capture is claimed.
        collision='pi_'+uuid.uuid4().hex
        await db.execute(text('UPDATE transactions SET stripe_payment_intent_id=:pi WHERE id=:id'),{'pi':collision,'id':seed['transaction_id']})
        await db.commit()
    seed_before=await f7_snapshot(db,seed['id'],seed['transaction_id']);await db.rollback()
    original=stripe.PaymentIntent.create
    def reused(**kwargs):result=original(**kwargs);result['id']=collision;return result
    monkeypatch.setattr(stripe.PaymentIntent,'create',reused)
    async with owned_notifications(db.bind):
        with pytest.raises(HTTPException) as exc:await svc.create_agent_checkout(tx['id'],key)
    assert exc.value.status_code==409
    assert exc.value.detail['code']=='AGENT_PAYMENT_RECONCILIATION_REQUIRED'
    causes=[];cause=exc.value
    while cause is not None:causes.append(cause);cause=cause.__cause__
    assert any(getattr(getattr(c,'orig',None),'sqlstate',None)=='23505' for c in causes)
    assert not [c for c in calls if c[0]=='cancel']
    assert await f7_snapshot(db,seed['id'],seed['transaction_id'])==seed_before
    row=(await db.execute(text('SELECT order_id,stripe_payment_intent_id,metadata FROM transactions WHERE id=:id'),{'id':tx['id']})).mappings().one()
    assert row['stripe_payment_intent_id'] is None
    assert row['metadata']['canonical_agent_attempt_v1']['observed_payment_intent_id']==collision
    assert row['metadata']['canonical_agent_attempt_v1']['state']=='conflict_reconciliation'
    assert await db.scalar(text('SELECT stripe_payment_intent_id FROM orders WHERE id=:id'),{'id':row['order_id']}) is None
    assert await db.scalar(text('SELECT spend_used FROM agent_api_keys WHERE id=:id'),{'id':key})==2500


@pytest.mark.asyncio
@pytest.mark.parametrize('point',['before','after'])
async def test_durable_agent_cancellation_acknowledgement_never_retries_write(db,monkeypatch,point):
    from fastapi import HTTPException
    from test_refund_webhook_protocol import owned_notifications
    import stripe
    svc,tx,key,pi,ch,calls=await agent_checkout_candidate(db,monkeypatch,provider_status='requires_action')
    original=stripe.PaymentIntent.cancel
    def interrupted(ident,**kwargs):
        if point=='after':original(ident,**kwargs)
        else:calls.append(('cancel',ident))
        raise ConnectionError('controlled cancellation acknowledgement loss')
    monkeypatch.setattr(stripe.PaymentIntent,'cancel',interrupted)
    async with owned_notifications(db.bind):
        with pytest.raises(HTTPException) as exc:await svc.create_agent_checkout(tx['id'],key)
    assert exc.value.status_code==409
    assert await db.scalar(text('SELECT spend_used FROM agent_api_keys WHERE id=:id'),{'id':key})==2500
    await db.rollback()
    with pytest.raises(HTTPException) as repeat:await svc.create_agent_checkout(tx['id'],key)
    assert repeat.value.status_code==(422 if point=='after' else 409)
    assert len([c for c in calls if c[0]=='cancel'])==1 and len([c for c in calls if c[0]=='create'])==1


@pytest.mark.asyncio
async def test_durable_agent_delivery_confirmation_settlement_preserve_exact_record(db,monkeypatch):
    from test_refund_webhook_protocol import owned_notifications,signed_post
    from app.services.delivery_service import DeliveryService
    from app.services.settlement_service import SettlementService
    from app.core.config import settings
    from app.core import stripe_async
    import stripe
    svc,tx,key,pi,ch,calls=await agent_checkout_candidate(db,monkeypatch,provider_status='succeeded')
    async with owned_notifications(db.bind):await svc.create_agent_checkout(tx['id'],key)
    event={'id':'evt_'+uuid.uuid4().hex,'object':'event','type':'payment_intent.succeeded','livemode':False,
        'created':int(datetime.now(timezone.utc).timestamp()),'data':{'object':dict(pi)}}
    assert (await signed_post(db,monkeypatch,event)).status_code==200
    record=await db.scalar(text("SELECT metadata->'canonical_agent_attempt_v1' FROM transactions WHERE id=:id"),{'id':tx['id']})
    await db.execute(text("UPDATE transactions SET metadata=jsonb_set(metadata,'{descriptor}',CAST(:descriptor AS jsonb)) WHERE id=:id"),{'id':tx['id'],'descriptor':json.dumps({'expected_bytes':4})})
    await db.commit()
    delivery=DeliveryService(db)
    token=await delivery.generate_delivery_token(tx['id'],buyer_id=tx['buyer_id'])
    claims,_=await delivery.validate_token(token['token'])
    await delivery._record_range_progress(transaction_id=tx['id'],attempt=claims.attempt,jti=claims.jti,start=0,end=3)
    await delivery._finalize_stream_if_complete(tx['id'],claims,200)
    assert (await delivery.confirm_delivery(tx['id'],actor_type='buyer',actor_id=tx['buyer_id']))['status']=='confirmed'
    assert await db.scalar(text("SELECT metadata->'canonical_agent_attempt_v1' FROM transactions WHERE id=:id"),{'id':tx['id']})==record
    # Only the existing eligibility clock is advanced in the owned test fixture.
    await db.execute(text("UPDATE transaction_events SET created_at=NOW()-INTERVAL '49 hours' WHERE transaction_id=:id AND to_status='confirmed'"),{'id':tx['id']});await db.commit()
    original=stripe_async.run_stripe;transfers=[]
    async def provider(fn,*args,**kwargs):
        if fn==stripe.Transfer.create:
            transfer={k:v for k,v in kwargs.items() if k!='idempotency_key'}
            transfer.update(id='tr_'+uuid.uuid4().hex,reversed=False,amount_reversed=0,livemode=False)
            transfers.append(transfer);return transfer
        if fn==stripe.Refund.list:return {'data':[],'has_more':False}
        return await original(fn,*args,**kwargs)
    monkeypatch.setattr(stripe_async,'run_stripe',provider)
    monkeypatch.setattr(settings,'ORDER_PAYOUT_DISPATCH_ENABLED',True)
    result=await SettlementService(db).settle(tx['id'])
    assert result['status']=='succeeded',result
    assert len(transfers)==1
    assert await db.scalar(text("SELECT metadata->'canonical_agent_attempt_v1' FROM transactions WHERE id=:id"),{'id':tx['id']})==record
    cached=await svc.create_agent_checkout(tx['id'],key)
    assert cached['status']=='settled' and cached['checkout_id']==pi['id']
    assert len([c for c in calls if c[0]=='create'])==1


async def durable_actual_state(db,monkeypatch,state):
    from fastapi import HTTPException
    from test_refund_webhook_protocol import signed_post,owned_notifications
    import stripe
    if state=='prepared_unknown':return await durable_prepared_candidate(db,monkeypatch)
    status={'response_observed':'requires_payment_method','bound_pending':'processing','cancellation_unknown':'requires_action',
        'conflict_reconciliation':'unexpected','cancelled_reconciled':'canceled','completed':'succeeded'}[state]
    svc,tx,key,pi,ch,calls=await agent_checkout_candidate(db,monkeypatch,provider_status=status)
    if state=='cancellation_unknown':
        def unavailable(*args,**kwargs):raise RuntimeError('controlled unresolved cancellation')
        monkeypatch.setattr(stripe.PaymentIntent,'cancel',unavailable)
    async with owned_notifications(db.bind):
        try:await svc.create_agent_checkout(tx['id'],key)
        except HTTPException as exc:assert exc.status_code in (409,422)
    if state=='completed':
        event={'id':'evt_'+uuid.uuid4().hex,'object':'event','type':'payment_intent.succeeded','livemode':False,
            'created':int(datetime.now(timezone.utc).timestamp()),'data':{'object':dict(pi)}}
        assert (await signed_post(db,monkeypatch,event)).status_code==200
    row=(await db.execute(text('SELECT order_id,metadata FROM transactions WHERE id=:id'),{'id':tx['id']})).mappings().one()
    attempt=row['metadata']['canonical_agent_attempt_v1'];assert attempt['state']==state
    await db.rollback()
    return svc,tx,key,pi,ch,calls,row['order_id'],attempt


@pytest.mark.asyncio
@pytest.mark.parametrize('source',['prepared_unknown','response_observed','bound_pending','cancellation_unknown','conflict_reconciliation','completed','cancelled_reconciled'])
@pytest.mark.parametrize('target',['prepared_unknown','response_observed','bound_pending','cancellation_unknown','conflict_reconciliation','completed','cancelled_reconciled'])
async def test_durable_agent_complete_transition_matrix(db,monkeypatch,source,target):
    from app.services.order_money_service import (_locked_initial_pair,ExpectedPaymentBinding,agent_provider_evidence,
        bind_initial_order_payment_intent_sync,transition_agent_attempt_sync)
    from test_refund_webhook_protocol import signed_post
    allowed={
        'prepared_unknown':{'response_observed','bound_pending','cancellation_unknown','conflict_reconciliation','cancelled_reconciled'},
        'response_observed':{'response_observed','bound_pending','cancellation_unknown','conflict_reconciliation','cancelled_reconciled'},
        'bound_pending':{'bound_pending','response_observed','conflict_reconciliation','completed','cancelled_reconciled'},
        'cancellation_unknown':{'cancellation_unknown','bound_pending','conflict_reconciliation','cancelled_reconciled'},
        'conflict_reconciliation':{'conflict_reconciliation','response_observed','bound_pending','cancelled_reconciled'},
        'completed':{'completed'},'cancelled_reconciled':{'cancelled_reconciled'}}
    svc,tx,key,pi,ch,calls,oid,original=await durable_actual_state(db,monkeypatch,source)
    if target=='completed' and source=='bound_pending':
        pi.update(status='succeeded',amount_received=2500)
        event={'id':'evt_'+uuid.uuid4().hex,'object':'event','type':'payment_intent.succeeded','livemode':False,
            'created':int(datetime.now(timezone.utc).timestamp()),'data':{'object':dict(pi)}}
        assert (await signed_post(db,monkeypatch,event)).status_code==200
        assert await db.scalar(text("SELECT metadata->'canonical_agent_attempt_v1'->>'state' FROM transactions WHERE id=:id"),{'id':tx['id']})=='completed'
        return
    pi.update(status={'bound_pending':'succeeded','response_observed':'requires_confirmation','cancellation_unknown':'requires_action',
        'cancelled_reconciled':'canceled','completed':'succeeded'}.get(target,'unexpected'),amount_received=0,amount_capturable=0)
    evidence=agent_provider_evidence(pi,source='provider_read')
    before=await f7_snapshot(db,oid,tx['id']);await db.rollback()
    def apply(sync):
        order,linked=_locked_initial_pair(sync,oid)
        if target in allowed[source] and source not in {'completed','cancelled_reconciled'} and target!='conflict_reconciliation':
            b=ExpectedPaymentBinding(uuid.UUID(str(oid)),uuid.UUID(str(tx['id'])),None,None,pi['id'],2500,'USD',
                uuid.UUID(str(order.buyer_id)),uuid.UUID(str(order.seller_id)),uuid.UUID(str(order.listing_id)),125,2375)
            bind_initial_order_payment_intent_sync(sync,order_id=oid,payment_intent_id=pi['id'],expected_transaction_id=tx['id'],
                mode='agent_attempt_completion',expected_binding=b,expected_agent_attempt_id=uuid.UUID(original['attempt_id']),
                expected_agent_attempt_revision=original['revision'],provider_evidence=evidence)
        return transition_agent_attempt_sync(sync,order,linked,state=target,evidence=evidence,release=target=='cancelled_reconciled')
    if target not in allowed[source]:
        with pytest.raises(OrderMoneyConflict):await db.run_sync(apply)
        await db.rollback();assert await f7_snapshot(db,oid,tx['id'])==before
    else:
        result=await db.run_sync(apply);await db.commit()
        assert result['state']==target
        assert result['revision']==original['revision']+(0 if source in {'completed','cancelled_reconciled'} else 1)
        mutable={'revision','state','observed_payment_intent_id','observed_provider_status','observed_at','evidence_source','spend_release_state','release_evidence'}
        assert {k:v for k,v in result.items() if k not in mutable}=={k:v for k,v in original.items() if k not in mutable}


@pytest.mark.asyncio
@pytest.mark.parametrize('condition',['duplicate','stale','overflow','cancel_processing'])
async def test_durable_agent_observation_revision_and_cancellation_progression(db,monkeypatch,condition):
    from dataclasses import replace
    from datetime import timedelta
    from app.services.order_money_service import (_locked_initial_pair,agent_provider_evidence,transition_agent_attempt_sync,agent_timestamp)
    state='cancellation_unknown' if condition=='cancel_processing' else 'bound_pending'
    svc,tx,key,pi,ch,calls,oid,attempt=await durable_actual_state(db,monkeypatch,state)
    pi['status']='processing'
    evidence=agent_provider_evidence(pi,source=attempt['evidence_source'])
    evidence=replace(evidence,observed_at=attempt['observed_at'])
    if condition=='stale':
        evidence=replace(evidence,observed_at=(agent_timestamp(attempt['observed_at'])-timedelta(microseconds=1)).strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
    if condition=='overflow':
        attempt['revision']=2147483647
        await db.execute(text("UPDATE transactions SET metadata=jsonb_set(metadata,'{canonical_agent_attempt_v1}',CAST(:record AS jsonb)) WHERE id=:id"),{'id':tx['id'],'record':json.dumps(attempt)})
        await db.commit()
        evidence=agent_provider_evidence(pi,source='provider_read')
    before=await f7_snapshot(db,oid,tx['id']);await db.rollback()
    def apply(sync):
        order,linked=_locked_initial_pair(sync,oid)
        return transition_agent_attempt_sync(sync,order,linked,state='bound_pending',evidence=evidence)
    if condition=='duplicate':
        assert (await db.run_sync(apply))['revision']==attempt['revision']
        await db.commit()
    else:
        with pytest.raises(OrderMoneyConflict):await db.run_sync(apply)
        await db.rollback()
    assert await f7_snapshot(db,oid,tx['id'])==before


@pytest.mark.asyncio
@pytest.mark.parametrize('newer',['capture','refund','cancel','cancel_duplicate'])
async def test_durable_agent_old_observation_after_committed_money_barrier(db,monkeypatch,newer):
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession
    from fastapi import HTTPException
    from app.services.transaction_service import TransactionService
    from test_refund_webhook_protocol import owned_notifications,signed_post
    svc,tx,key,pi,ch,calls=await agent_checkout_candidate(db,monkeypatch,provider_status='processing')
    async with owned_notifications(db.bind):await svc.create_agent_checkout(tx['id'],key)
    oid=await db.scalar(text('SELECT order_id FROM transactions WHERE id=:id'),{'id':tx['id']})
    await db.rollback()
    if newer=='cancel_duplicate':pi.update(status='canceled',amount_received=0,amount_capturable=0)
    reached,resume=asyncio.Event(),asyncio.Event()
    original=TransactionService._apply_agent_observation
    observations=[]
    async def pause(self,*args,**kwargs):
        observations.append(args[2]);reached.set()
        await asyncio.wait_for(resume.wait(),5)
        return await original(self,*args,**kwargs)
    monkeypatch.setattr(TransactionService,'_apply_agent_observation',pause)
    async def old_reader():
        async with AsyncSession(db.bind,expire_on_commit=False) as own:
            try:return await TransactionService(own).reconcile_agent_checkout(tx['id'],key)
            except HTTPException as exc:return exc.status_code
    reader=asyncio.create_task(old_reader())
    try:
        await asyncio.wait_for(reached.wait(),3)
        assert observations[0].provider_status==('canceled' if newer=='cancel_duplicate' else 'processing')
        pi.update(status='canceled' if newer in {'cancel','cancel_duplicate'} else 'succeeded',amount_received=0 if newer in {'cancel','cancel_duplicate'} else 2500,amount_capturable=0)
        event={'id':'evt_'+uuid.uuid4().hex,'object':'event','type':'payment_intent.payment_failed' if newer in {'cancel','cancel_duplicate'} else 'payment_intent.succeeded','livemode':False,
            'created':int(datetime.now(timezone.utc).timestamp()),'data':{'object':dict(pi)}}
        assert (await signed_post(db,monkeypatch,event)).status_code==200
        await db.rollback()
        if newer=='refund':
            ch['amount_refunded']=2500
            event2=await signed_event(db,ch)
            await process(db,event2,pi,ch,[refund(ch,2500,uuid.uuid4().hex)])
        before=await f6_snapshot(db,oid,tx['id'],key);await db.rollback()
        resume.set()
        result=await asyncio.wait_for(reader,3)
        assert result==(422 if newer=='cancel_duplicate' else 409),result
        assert await f6_snapshot(db,oid,tx['id'],key)==before
        assert len([c for c in calls if c[0]=='create'])==1
        assert not [c for c in calls if c[0]=='cancel']
        assert await db.scalar(text('SELECT spend_used FROM agent_api_keys WHERE id=:id'),{'id':key})==(2500 if newer=='capture' else 0)
    finally:
        resume.set()
        if not reader.done():reader.cancel()
        await asyncio.gather(reader,return_exceptions=True)
