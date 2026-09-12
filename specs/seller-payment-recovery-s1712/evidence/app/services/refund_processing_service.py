"""S1714 order capture and caller-owned atomic refund effects.

Provider I/O is outside SQL transactions. Admission commits independently;
HTTP integration must await effects commit before acknowledging a refund.
"""
from datetime import datetime, timezone
import hashlib
import json
import re
from uuid import UUID

from sqlalchemy import select, text
from app.core.config import settings
from app.models.finance import BillingEntity, GLAccount, JournalEntry, Payment, Refund
from app.models.order_money_state import OrderMoneyState
from app.services.finance.engine import FinanceEngine
from app.services.order_money_service import (
    OrderMoneyConflict, canonical_digest, lock_order_money, resolve_order_id,
)

ORDER_MONEY_PROTOCOL_VERSION = 1


class OrderMoneyProtocolUnavailable(RuntimeError):
    pass


# Frozen catalog contract of the approved additive schema. Validation includes
# enabled guards and their actual function bodies, not merely a version marker.
CATALOG_SQL = """
select 'column' kind, table_name || '.' || column_name identity,
       data_type || ':' || coalesce(character_maximum_length::text,'') || ':' || is_nullable definition
from information_schema.columns where table_schema='public' and (
 table_name in ('order_money_states','s1681_refund_test_authorities') or
 table_name='refunds' and column_name in ('effects_applied_at','order_id','transaction_id','agent_spend_delta_cents','marketplace_fee_refund_cents','marketplace_seller_refund_cents') or
 table_name='stripe_events' and column_name like 'refund_%')
union all
select 'constraint', c.relname || '.' || con.conname,
       pg_get_constraintdef(con.oid,true) || ':' || con.convalidated::text
from pg_constraint con join pg_class c on c.oid=con.conrelid join pg_namespace n on n.oid=c.relnamespace
where n.nspname='public' and (c.relname in ('order_money_states','s1681_refund_test_authorities') or con.conname like '%s1714%' or c.relname='payments' and con.conname='ck_payments_status')
and (n.nspname,c.relname,con.conname) not in (
 ('public','orders','uq_s1714_order_payment_intent'),
 ('public','transactions','uq_s1714_transaction_payment_intent'))
union all
select 'trigger',t.tgname,pg_get_triggerdef(t.oid) || ':' || t.tgenabled::text || ':' || p.prosrc
from pg_trigger t join pg_proc p on p.oid=t.tgfoid join pg_namespace n on n.oid=p.pronamespace
where n.nspname='public' and t.tgname in ('trg_s1714_money_immutable','trg_s1714_authority_immutable','trg_sync_order_to_transaction')
order by 1,2
"""
CATALOG_SHA256 = '3139d7fff567e782c12fc3fb2f27e4592bee7437ddb4b5c2f9529a1f8fdba1b5'

# Separate, mandatory extension. Resolve the public base relations themselves;
# neither a constraint name nor an index name supplies attachment authority.
CANONICAL_PI_CATALOG_SQL = """
SELECT expected.table_name, expected.constraint_name,
       c.conrelid = base.oid AS constraint_on_base,
       c.contype::text, c.convalidated, c.condeferrable, c.condeferred,
       c.conkey = ARRAY[a.attnum]::smallint[] AS constraint_key,
       a.attnotnull, a.attisdropped,
       pg_catalog.format_type(a.atttypid,a.atttypmod) AS column_type,
       i.indexrelid = c.conindid AS supporting_index,
       i.indrelid = base.oid AS index_on_base,
       ix.relname AS index_name, ns.nspname AS index_schema,
       i.indisunique, i.indisvalid, i.indisready, i.indimmediate,
       i.indnatts, i.indnkeyatts,
       i.indkey::text = a.attnum::text AS index_key,
       i.indexprs IS NULL AS no_expression, i.indpred IS NULL AS no_predicate,
       i.indnullsnotdistinct
FROM (VALUES ('orders','uq_s1714_order_payment_intent'),
             ('transactions','uq_s1714_transaction_payment_intent'))
     AS expected(table_name,constraint_name)
LEFT JOIN pg_class base ON base.oid =
    to_regclass('public.' || expected.table_name) AND base.relkind='r'
LEFT JOIN pg_constraint c ON c.conrelid=base.oid
    AND c.conname=expected.constraint_name
LEFT JOIN pg_attribute a ON a.attrelid=base.oid
    AND a.attname='stripe_payment_intent_id' AND a.attnum>0
LEFT JOIN pg_index i ON i.indexrelid=c.conindid
LEFT JOIN pg_class ix ON ix.oid=c.conindid
LEFT JOIN pg_namespace ns ON ns.oid=ix.relnamespace
ORDER BY expected.table_name,expected.constraint_name
"""


def _assert_canonical_pi_extension(rows):
    expected = [
        (table, name, True, 'u', True, False, False, True, False, False,
         'character varying(255)', True, True, name, 'public',
         True, True, True, True, 1, 1, True, True, True, False)
        for table, name in (
            ('orders', 'uq_s1714_order_payment_intent'),
            ('transactions', 'uq_s1714_transaction_payment_intent'))
    ]
    if [tuple(row) for row in rows] != expected:
        raise OrderMoneyProtocolUnavailable('Canonical PI constraint/index extension mismatch')


def _catalog_digest(rows):
    # PostgreSQL may distribute this exact text-array cast when parsing the
    # same declared CHECK. Recognize only these two equivalent renderings.
    rows = [list(row) for row in rows]
    for row in rows:
        if row[:2] == ['constraint', 'stripe_events.ck_s1714_event_phase'] and row[2] == "CHECK (refund_phase IS NULL OR (refund_phase::text = ANY (ARRAY['admitted'::character varying::text, 'applied'::character varying::text, 'reconciliation'::character varying::text]))):true":
            row[2] = "CHECK (refund_phase IS NULL OR (refund_phase::text = ANY (ARRAY['admitted'::character varying, 'applied'::character varying, 'reconciliation'::character varying]::text[]))):true"
    return hashlib.sha256(json.dumps([list(row) for row in rows],separators=(',',':')).encode()).hexdigest()


# F2 frozen catalog contract. Keep migration and runtime copies identical.
POSTED_OLD_BODY = """BEGIN
    IF OLD.status = 'posted' OR OLD.posted_at IS NOT NULL THEN
        RAISE EXCEPTION 'posted journal entries are immutable';
    END IF;
    RETURN OLD;
END;"""
POSTED_BODY = """BEGIN
    IF OLD.status = 'posted' OR OLD.posted_at IS NOT NULL THEN
        RAISE EXCEPTION 'posted journal entries are immutable';
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END;"""
POSTED_GUARDS = (
    ('journal_entries', 'trg_immutable_posted_entries', 'finance_prevent_posted_entry_mutation', 27),
    ('journal_entries', 'trg_closed_period_guard', 'finance_guard_closed_period', 23),
    ('journal_entries', 'trg_balanced_on_post', 'finance_validate_journal_posting', 23),
    ('journal_lines', 'trg_immutable_posted_lines', 'finance_prevent_posted_line_mutation', 27),
    ('journal_lines', 'trg_line_entity_consistency', 'finance_guard_line_account_entity', 23),
)


def posting_guard_report(db):
    # Schema-qualified identity and OID attachment query deliberately have no
    # table filter. A second attachment anywhere makes the contract invalid.
    functions = db.execute(text("""select p.oid, p.proname, p.prosrc,
        p.prorettype='pg_catalog.trigger'::regtype as returns_trigger,
        l.lanname, p.prosecdef, p.prokind::text as prokind, p.proconfig
        from pg_proc p join pg_namespace n on n.oid=p.pronamespace
        join pg_language l on l.oid=p.prolang
        where n.nspname='public' and p.pronargs=0 and p.proname=ANY(:names)
    """), {'names':[g[2] for g in POSTED_GUARDS]}).mappings().all()
    by_name = {f['proname']:f for f in functions}
    errors, guards = [], []
    body_state = 'missing'
    attachments = 0
    for table, name, function, tgtype in POSTED_GUARDS:
        f = by_name.get(function)
        if f is None:
            errors.append('missing function: public.' + function)
            continue
        if (not f['returns_trigger'] or f['lanname'] != 'plpgsql' or f['prosecdef']
                or f['prokind'] != 'f' or f['proconfig'] is not None):
            errors.append('function metadata: public.' + function)
        rows = db.execute(text("""select t.tgname,n.nspname,c.relname,t.tgfoid,
            t.tgtype,t.tgenabled::text as tgenabled,t.tgisinternal,t.tgqual is null as no_when,
            t.tgattr::text as columns,t.tgnargs,octet_length(t.tgargs) as arg_bytes,
            t.tgconstraint,t.tgdeferrable,t.tginitdeferred,
            t.tgoldtable,t.tgnewtable
            from pg_trigger t join pg_class c on c.oid=t.tgrelid
            join pg_namespace n on n.oid=c.relnamespace
            where (n.nspname='public' and c.relname=:table and t.tgname=:name)
                or (:target and t.tgfoid=:oid and not t.tgisinternal)
            order by n.nspname,c.relname,t.tgname
        """), {'table':table,'name':name,'oid':f['oid'],
                 'target':function==POSTED_GUARDS[0][2]}).mappings().all()
        expected = (name,'public',table,f['oid'],tgtype,'O',False,True,'',0,0,0,False,False,None,None)
        if len(rows) != 1 or tuple(rows[0].values()) != expected:
            errors.append('trigger binding: public.' + table + '.' + name)
        if function == POSTED_GUARDS[0][2]:
            attachments = db.execute(text('select count(*) from pg_trigger where tgfoid=:oid and not tgisinternal'), {'oid':f['oid']}).scalar_one()
            if attachments != 1:
                errors.append('posted function attachment count')
            normalized = ' '.join(f['prosrc'].split())
            body_state = ('corrected' if normalized == ' '.join(POSTED_BODY.split()) else
                          'old' if normalized == ' '.join(POSTED_OLD_BODY.split()) else 'unknown')
            if body_state == 'unknown':
                errors.append('unrecognized posted function body')
        guards.append({'function':dict(f),'attachments':[dict(r) for r in rows]})
    return {'body':body_state,'sole_attachment_count':attachments,'errors':errors,
            'corrected_ready':not errors and body_state=='corrected','guards':guards}


def assert_order_money_protocol_ready_sync(db, *, required_version=1):
    if required_version != 1 or settings.BILLING_ENTITY_CODE != 'AIM_WY_LLC':
        raise OrderMoneyProtocolUnavailable('Unsupported order money protocol/entity')
    try:
        from alembic.script import ScriptDirectory
        from pathlib import Path
        script = ScriptDirectory(str(Path(__file__).resolve().parents[2] / 'alembic'))
        versions = db.execute(text('select version_num from alembic_version')).scalars().all()
        if not any('s1714_order_money_v1' in {r.revision for r in script.walk_revisions(base='base',head=v)} for v in versions):
            raise OrderMoneyProtocolUnavailable('Required order money migration ancestry absent')
        if not any('s1714_canonical_pi_binding_v1' in {r.revision for r in script.walk_revisions(base='base',head=v)} for v in versions):
            raise OrderMoneyProtocolUnavailable('Required canonical PI migration ancestry absent')
        _assert_canonical_pi_extension(db.execute(text(CANONICAL_PI_CATALOG_SQL)).all())
        if _catalog_digest(db.execute(text(CATALOG_SQL)).all()) != CATALOG_SHA256:
            raise OrderMoneyProtocolUnavailable('Order money schema/guard definition mismatch')
        if not posting_guard_report(db)['corrected_ready']:
            raise OrderMoneyProtocolUnavailable('F2 posting guard unavailable')
        entities = db.execute(text("select id from billing_entities where code='AIM_WY_LLC' and is_active and merchant_of_record and country_code='US' and currency='USD'")).scalars().all()
        if len(entities) != 1:
            raise OrderMoneyProtocolUnavailable('Exact marketplace merchant unavailable')
        eid = entities[0]
        rows = db.execute(text('select code,name,account_type,normal_balance,is_active,system_managed,allow_manual_posting from gl_accounts where entity_id=:eid and code in (\'1000\',\'2110\',\'4000\',\'5100\') order by code'), {'eid':eid}).all()
        expected = [(c,*v,True,True,False) for c,v in sorted(FinanceEngine.MARKETPLACE_CHART.items())]
        if [tuple(r) for r in rows] != expected:
            raise OrderMoneyProtocolUnavailable('Exact marketplace chart unavailable')
        if db.execute(text('''select exists(select 1 from order_money_states where
            protocol_version<>1 or billing_entity_id is not null and billing_entity_id<>:eid or
            billing_entity_id is null and (capture_payment_id is not null or capture_journal_entry_id is not null
            or payout_journal_entry_id is not null or request_json is not null or stripe_transfer_id is not null or refund_applied_cents>0))'''),{'eid':eid}).scalar_one():
            raise OrderMoneyProtocolUnavailable('Invalid immutable authority entity binding')
        return eid
    except OrderMoneyProtocolUnavailable:
        raise
    except Exception as exc:
        raise OrderMoneyProtocolUnavailable('Order money schema readiness unavailable') from exc


async def assert_order_money_protocol_ready(db, *, required_version=1):
    return await db.run_sync(lambda sync: assert_order_money_protocol_ready_sync(sync,required_version=required_version))


def _identity(value, prefix):
    if type(value) is not str or not re.fullmatch(prefix + r'_[A-Za-z0-9]+',value):
        raise OrderMoneyConflict('Invalid provider identity')
    return value


def validate_captured_facts(order, transaction, provider_payment, provider_charge):
    pi, ch = provider_payment, provider_charge
    _identity(pi.get('id'),'pi')
    _identity(ch.get('id'),'ch')
    if (pi.get('id') != order.stripe_payment_intent_id or pi.get('status') != 'succeeded' or
        pi.get('latest_charge') != ch.get('id') or ch.get('payment_intent') != pi.get('id') or
        ch.get('paid') is not True or ch.get('captured') is not True or
        type(pi.get('livemode')) is not bool or pi.get('livemode') != ch.get('livemode') or
        pi.get('livemode') == settings.STRIPE_TEST_MODE or pi.get('on_behalf_of') or ch.get('on_behalf_of') or
        pi.get('transfer_data') or ch.get('transfer_data') or
        pi.get('currency') != 'usd' or ch.get('currency') != 'usd' or
        pi.get('customer') != ch.get('customer')):
        raise OrderMoneyConflict('Authoritative capture identity/scope mismatch')
    for value in (pi.get('amount'),pi.get('amount_received'),ch.get('amount'),ch.get('amount_captured')):
        if type(value) is not int or value != order.amount_cents or value <= 0:
            raise OrderMoneyConflict('Authoritative capture gross mismatch')
    for obj in (pi,ch):
        meta = obj.get('metadata') or {}
        if meta.get('order_id') and meta['order_id'] != str(order.id):
            raise OrderMoneyConflict('Provider order binding mismatch')
        if meta.get('transaction_id') and (transaction is None or meta['transaction_id'] != str(transaction.id)):
            raise OrderMoneyConflict('Provider transaction binding mismatch')
    if type(ch.get('created')) is not int or ch['created'] <= 0:
        raise OrderMoneyConflict('Capture received_at unavailable')


async def ensure_order_capture(db, *, order, transaction, provider_payment, provider_charge, origin, locked=None, _prepare_only=False):
    """Record the immutable original gross, even when refunds arrived first.

    No commit, no provider I/O. Refund callers pass their already acquired full
    lock bundle so capture reconstruction never reverses Refund/agent/GL edges.
    """
    if origin not in {'payment_event','refund_reconciliation'}:
        raise OrderMoneyConflict('Invalid capture origin')
    eid = await assert_order_money_protocol_ready(db)
    money = locked or await lock_order_money(db, order.id)
    order,tx,state = money.order,money.transaction,money.state
    if (transaction.id if transaction else None) != (tx.id if tx else None):
        raise OrderMoneyConflict('Capture transaction changed')
    validate_captured_facts(order,tx,provider_payment,provider_charge)
    if state.billing_entity_id not in (None,eid):
        raise OrderMoneyConflict('Capture entity changed')
    state.billing_entity_id = eid
    pi,ch = provider_payment,provider_charge
    payment = money.payment
    if payment is None:
        # Any previous unbound posting needs explicit reconciliation.
        conflict = (await db.execute(select(JournalEntry.id).where(JournalEntry.source_ref.in_(
            [f'commission:{order.id}',f'marketplace_payment:{pi["id"]}'])))).first()
        if conflict or state.capture_payment_id or state.capture_journal_entry_id:
            raise OrderMoneyConflict('Unbound historical capture requires reconciliation')
        payment = Payment(entity_id=eid,customer_id=order.buyer_id,
            stripe_payment_intent_id=pi['id'],stripe_charge_id=ch['id'],stripe_customer_id=pi.get('customer'),
            amount_cents=order.amount_cents,currency='USD',status='succeeded',payment_type='commission',
            received_at=datetime.fromtimestamp(ch['created'],timezone.utc))
        db.add(payment)
        await db.flush()
        money.payment = payment
    expected = (eid,order.buyer_id,pi['id'],ch['id'],pi.get('customer'),order.amount_cents,'USD','commission')
    actual = (payment.entity_id,payment.customer_id,payment.stripe_payment_intent_id,payment.stripe_charge_id,
              payment.stripe_customer_id,payment.amount_cents,payment.currency,payment.payment_type)
    if actual != expected or state.capture_payment_id not in (None,payment.id):
        raise OrderMoneyConflict('Payment capture binding mismatch')
    if payment.status not in {'succeeded','partially_refunded','refunded','disputed'}:
        raise OrderMoneyConflict('Historical payment status contradicts capture')
    if payment.journal_entry_id and state.capture_journal_entry_id != payment.journal_entry_id:
        raise OrderMoneyConflict('Unbound historical capture journal')
    if _prepare_only:
        return payment
    journal = await FinanceEngine().record_marketplace_capture(db=db,entity_id=eid,payment_id=payment.id,
        stripe_pi_id=pi['id'],gross_cents=order.amount_cents,fee_cents=order.platform_fee_cents,
        seller_cents=order.seller_amount_cents,origin=state.capture_origin or origin)
    if state.capture_journal_entry_id not in (None,journal.id):
        raise OrderMoneyConflict('Capture journal changed')
    payment.journal_entry_id = journal.id
    state.capture_payment_id = payment.id
    state.capture_journal_entry_id = journal.id
    state.capture_origin = state.capture_origin or origin
    await db.flush()
    return payment


def validate_refund_snapshot(payment, charge, refunds):
    """Accept only complete, stable authoritative succeeded sets."""
    seen, total = set(), 0
    for r in refunds:
        rid = _identity(r.get('id'),'re')
        if rid in seen:
            raise OrderMoneyConflict('Duplicate identity across refund pages')
        seen.add(rid)
        if (r.get('charge') != charge['id'] or r.get('payment_intent') != payment['id'] or
            r.get('currency') != 'usd' or type(r.get('amount')) is not int or r['amount']<=0 or
            type(r.get('livemode')) is not bool or r['livemode'] != charge['livemode']):
            raise OrderMoneyConflict('Provider refund binding mismatch')
        if r.get('status') not in {'pending','failed','canceled','succeeded'}:
            raise OrderMoneyConflict('Unknown provider refund status')
        if r['status']=='succeeded':
            total += r['amount']
    if type(charge.get('amount_refunded')) is not int or total != charge['amount_refunded'] or total > charge['amount']:
        raise OrderMoneyConflict('Incomplete or changing provider refund snapshot')
    return total


async def read_provider_refunds(payment_intent_id, charge_id):
    import stripe
    from app.core.stripe_async import run_stripe
    pi = await run_stripe(stripe.PaymentIntent.retrieve,payment_intent_id)
    charge = await run_stripe(stripe.Charge.retrieve,charge_id)
    rows, cursor, seen = [], None, set()
    while True:
        args = {'charge':charge_id,'limit':100}
        if cursor:
            args['starting_after'] = cursor
        page = await run_stripe(stripe.Refund.list,**args)
        data = page.get('data')
        if not isinstance(data,list) or type(page.get('has_more')) is not bool:
            raise OrderMoneyConflict('Malformed refund pagination')
        rows.extend(data)
        if not page['has_more']:
            break
        if not data or data[-1].get('id') in seen:
            raise OrderMoneyConflict('Truncated refund pagination')
        cursor = _identity(data[-1].get('id'),'re')
        seen.add(cursor)
    after = await run_stripe(stripe.Charge.retrieve,charge_id)
    fields = ('id','payment_intent','amount','amount_captured','amount_refunded','currency','paid','captured','livemode','customer')
    if any(charge.get(k)!=after.get(k) for k in fields):
        raise OrderMoneyConflict('Provider snapshot changed during pagination')
    validate_refund_snapshot(pi,after,rows)
    return pi,after,rows


def _event_binding(event):
    if event.get('type') != 'charge.refunded' or event.get('account'):
        raise OrderMoneyConflict('Not an admitted platform refund')
    ch = event['data']['object']
    _identity(event.get('id'),'evt')
    _identity(ch.get('id'),'ch')
    _identity(ch.get('payment_intent'),'pi')
    if type(event.get('livemode')) is not bool or event['livemode'] != ch.get('livemode'):
        raise OrderMoneyConflict('Signed event scope mismatch')
    return ch,canonical_digest({'id':event['id'],'charge':ch['id'],
        'payment_intent':ch['payment_intent'],'livemode':event['livemode']})


def admit_order_refund_sync(db, event):
    """Durable admission. Caller must have passed signature/suppression checks."""
    from app.services.order_money_service import resolve_order_id_sync, lock_order_money_sync
    assert_order_money_protocol_ready_sync(db)
    ch,digest = _event_binding(event)
    row = (db.execute(text('select * from stripe_events where stripe_event_id=:eid for update'),{'eid':event['id']})).mappings().one()
    if not row['signature_valid'] or row['payload_json'] != event:
        raise OrderMoneyConflict('Missing signed event provenance')
    oid = resolve_order_id_sync(db,ch['payment_intent'],metadata=ch.get('metadata'))
    if oid:
        lock_order_money_sync(db,oid)
    if row['refund_phase'] is not None:
        if ((row['refund_binding_sha256'],row['refund_payment_intent_id'],row['refund_charge_id']) !=
                (digest,ch['payment_intent'],ch['id']) or row['refund_order_id'] not in (None,oid)):
            raise OrderMoneyConflict('Refund admission binding changed')
        if row['refund_phase']=='applied' and row['refund_order_id']!=oid:
            raise OrderMoneyConflict('Applied finance refund acquired a later order; reconciliation required')
        if row['refund_phase']=='applied':
            db.commit()
            return {'phase':'applied','order_id':oid}
    elif row['status']=='completed':
        db.execute(text("update stripe_events set refund_phase='reconciliation',error_message='legacy_refund_completion' where stripe_event_id=:eid"),{'eid':event['id']})
        db.commit()
        raise OrderMoneyConflict('Legacy refund completion requires reconciliation')
    db.execute(text('''update stripe_events set refund_phase='admitted',
        refund_order_id=:oid,refund_payment_intent_id=:pi,refund_charge_id=:ch,
        refund_binding_sha256=:digest,refund_admitted_at=coalesce(refund_admitted_at,clock_timestamp()),
        status='failed',processed_status='failed',error_message='refund_pending' where stripe_event_id=:eid'''),
        {'oid':oid,'pi':ch['payment_intent'],'ch':ch['id'],'digest':digest,'eid':event['id']})
    db.commit()
    return {'phase':'admitted','order_id':oid}


async def admit_order_refund(db, event):
    return await db.run_sync(lambda sync: admit_order_refund_sync(sync,event))


async def process_order_refund(db, event):
    """Inline request orchestration; admission commit precedes provider I/O."""
    admission = await admit_order_refund(db,event)
    ch,_ = _event_binding(event)
    pi,charge,refunds = await read_provider_refunds(ch['payment_intent'],ch['id'])
    try:
        apply = apply_order_refund_effects if admission['order_id'] is not None else apply_finance_refund_effects
        result = await apply(db,event=event,provider_payment=pi,
            provider_charge=charge,provider_refunds=refunds)
        await db.commit()
        return result
    except BaseException:
        await db.rollback()
        raise


async def apply_order_refund_effects(db, *, event, provider_payment, provider_charge, provider_refunds):
    """All effects flush together; caller commits before sending any HTTP 2xx."""
    await assert_order_money_protocol_ready(db)
    signed,digest = _event_binding(event)
    row = (await db.execute(text('select * from stripe_events where stripe_event_id=:eid for update'),{'eid':event['id']})).mappings().one()
    if (not row['signature_valid'] or row['payload_json'] != event or row['refund_binding_sha256'] != digest or row['refund_phase'] not in {'admitted','applied'} or
            provider_payment.get('id') != signed['payment_intent'] or provider_charge.get('id') != signed['id']):
        raise OrderMoneyConflict('Effects lack matching durable admission')
    oid = await resolve_order_id(db,signed['payment_intent'],metadata=provider_payment.get('metadata'))
    if oid is None or row['refund_order_id'] not in (None,oid):
        raise OrderMoneyConflict('Order refund unresolved')
    money = await lock_order_money(db,oid,refund_ids=[r.get('id') for r in provider_refunds])
    order,tx,state = money.order,money.transaction,money.state
    validate_captured_facts(order,tx,provider_payment,provider_charge)
    total = validate_refund_snapshot(provider_payment,provider_charge,provider_refunds)
    if total < state.refund_applied_cents:
        raise OrderMoneyConflict('Refund total decreased')
    existing = {r.stripe_refund_id:r for r in money.refunds}
    succeeded = {r['id']:r for r in provider_refunds if r['status']=='succeeded'}
    applied_total = 0
    for refund in money.refunds:
        if refund.effects_applied_at is None:
            if refund.status=='succeeded' or refund.journal_entry_id:
                raise OrderMoneyConflict('Unapplied historical refund requires reconciliation')
            continue
        p = succeeded.get(refund.stripe_refund_id)
        if (p is None or refund.amount_cents != p['amount'] or refund.order_id != oid or
                refund.transaction_id != (tx.id if tx else None) or
                refund.payment_id != state.capture_payment_id or refund.entity_id != state.billing_entity_id or
                refund.currency != 'USD' or refund.status!='succeeded' or not refund.journal_entry_id):
            raise OrderMoneyConflict('Applied refund identity changed')
        applied_total += refund.amount_cents
    if applied_total != state.refund_applied_cents:
        raise OrderMoneyConflict('Applied refund aggregate mismatch')
    # Validate every historical allocation and actual posted journal, including
    # applied-event replay. No applied marker can bless a draft or wrong chart.
    historical = sorted((r for r in money.refunds if r.effects_applied_at),
                        key=lambda r:(r.effects_applied_at,r.stripe_refund_id))
    cumulative = seller_total = 0
    historical_journals = []
    for r in historical:
        fee = ((cumulative+r.amount_cents)*order.platform_fee_cents//order.amount_cents -
               cumulative*order.platform_fee_cents//order.amount_cents)
        seller = r.amount_cents-fee
        if r.marketplace_fee_refund_cents!=fee or r.marketplace_seller_refund_cents!=seller:
            raise OrderMoneyConflict('Historical refund allocation changed')
        cumulative += r.amount_cents
        seller_total += seller
        payable = await db.scalar(text("select coalesce(sum(l.debit_cents),0)::bigint from journal_lines l join gl_accounts a on a.id=l.account_id where l.entry_id=:jid and a.code='2110'"),{'jid':r.journal_entry_id})
        historical_journals.append((r,fee,seller,payable))
    if seller_total != state.seller_refunded_cents:
        raise OrderMoneyConflict('Historical seller refund counter changed')
    # Capture validation owns the first finance lock; only after all upstream
    # Refund rows exist may refund journal validation/writing follow it.
    if row['refund_phase']=='applied':
        if row['status']!='completed' or row['processed_status']!='processed':
            raise OrderMoneyConflict('Incomplete applied event state')
        await ensure_order_capture(db,order=order,transaction=tx,provider_payment=provider_payment,
            provider_charge=provider_charge,origin='refund_reconciliation',locked=money)
        for r,fee,seller,payable in historical_journals:
            journal = await FinanceEngine().record_marketplace_refund(db=db,entity_id=state.billing_entity_id,
                refund_id=r.id,stripe_refund_id=r.stripe_refund_id,amount_cents=r.amount_cents,
                fee_refund_cents=fee,seller_refund_cents=seller,remaining_payable_cents=payable)
            if journal.id != r.journal_entry_id:
                raise OrderMoneyConflict('Historical refund journal changed')
        return {'stripe_event_id':event['id'],'processed_status':'processed',
                'refund_total_cents':state.refund_applied_cents,'order_id':str(oid)}
    payment = await ensure_order_capture(db,order=order,transaction=tx,provider_payment=provider_payment,
        provider_charge=provider_charge,origin='refund_reconciliation',locked=money,_prepare_only=True)
    # Reserve every new Refund row before the first refund journal. Parent locks
    # are already owned; no existing Refund lock is acquired after finance locks.
    for rid,p in sorted(succeeded.items()):
        if rid not in existing:
            refund = Refund(entity_id=payment.entity_id,payment_id=payment.id,order_id=oid,
                transaction_id=tx.id if tx else None,stripe_refund_id=rid,amount_cents=p['amount'],
                currency='USD',reason=p.get('reason') or 'requested_by_customer',status='pending',requested_by='system:webhook')
            db.add(refund)
            existing[rid]=refund
    await db.flush()
    payment = await ensure_order_capture(db,order=order,transaction=tx,provider_payment=provider_payment,
        provider_charge=provider_charge,origin='refund_reconciliation',locked=money)
    for r,fee,seller,payable in historical_journals:
        journal = await FinanceEngine().record_marketplace_refund(db=db,entity_id=state.billing_entity_id,
            refund_id=r.id,stripe_refund_id=r.stripe_refund_id,amount_cents=r.amount_cents,
            fee_refund_cents=fee,seller_refund_cents=seller,remaining_payable_cents=payable)
        if journal.id != r.journal_entry_id:
            raise OrderMoneyConflict('Historical refund journal changed')
    completing = None
    now = await db.scalar(text('select clock_timestamp()'))
    for rid,p in sorted(succeeded.items()):
        refund = existing[rid]
        if refund.effects_applied_at:
            continue
        if (refund.amount_cents != p['amount'] or refund.entity_id != payment.entity_id or
            refund.payment_id != payment.id or refund.currency != 'USD' or
            refund.order_id not in (None,oid) or refund.transaction_id not in (None,tx.id if tx else None)):
            raise OrderMoneyConflict('Existing refund binding mismatch')
        before = state.refund_applied_cents
        fee = ((before+refund.amount_cents)*order.platform_fee_cents//order.amount_cents -
               before*order.platform_fee_cents//order.amount_cents)
        seller = refund.amount_cents-fee
        remaining = max(order.seller_amount_cents-state.seller_refunded_cents-state.seller_payout_posted_cents,0)
        journal = await FinanceEngine().record_marketplace_refund(db=db,entity_id=payment.entity_id,
            refund_id=refund.id,stripe_refund_id=rid,amount_cents=refund.amount_cents,
            fee_refund_cents=fee,seller_refund_cents=seller,remaining_payable_cents=remaining)
        refund.order_id=oid
        refund.transaction_id=tx.id if tx else None
        refund.marketplace_fee_refund_cents=fee
        refund.marketplace_seller_refund_cents=seller
        refund.journal_entry_id=journal.id
        refund.status='succeeded'
        refund.effects_applied_at=now
        refund.processed_at=now
        refund.agent_spend_delta_cents=0
        if money.agent_key:
            delta=min(refund.amount_cents,money.agent_key.spend_used)
            money.agent_key.spend_used-=delta
            refund.agent_spend_delta_cents=delta
        state.refund_applied_cents+=refund.amount_cents
        state.seller_refunded_cents+=seller
        state.revision+=1
        completing=rid
    if state.refund_applied_cents != total:
        raise OrderMoneyConflict('Refund aggregate did not converge')
    if total:
        payment.status='refunded' if total==order.amount_cents else 'partially_refunded'
        if state.dispatch_token or state.stripe_transfer_id or order.stripe_transfer_id:
            state.payout_state='reconciliation_required'
            state.reconciliation_reason='refund_after_payout_ownership'
        elif state.payout_state=='reserved':
            state.payout_state='idle'
            state.request_json=None
            state.request_sha256=None
            state.idempotency_key=None
            state.transfer_group=None
        # Trigger requires applied markers and aggregate BEFORE order status.
        await db.flush()
        order.refund_amount_cents=total
        if total==order.amount_cents:
            order.revoked=True
            order.revoked_at=order.revoked_at or now
            order.refunded_at=order.refunded_at or now
            if completing:
                order.stripe_refund_id=completing
            # Explicit status assignment must fire even if a dispute already
            # set this status. SQLAlchemy would elide an unchanged assignment.
            await db.flush()
            await db.execute(text("update orders set status='refunded' where id=:oid"),{'oid':oid})
            await db.refresh(order)
        else:
            order.status='partially_refunded'
    await db.flush()
    await db.execute(text('''update stripe_events set refund_order_id=:oid,refund_phase='applied',
        refund_applied_at=clock_timestamp(),status='completed',processed_status='processed',
        processed_at=clock_timestamp(),error_message=null where stripe_event_id=:eid'''),{'oid':oid,'eid':event['id']})
    return {'stripe_event_id':event['id'],'processed_status':'processed','refund_total_cents':total,'order_id':str(oid)}


async def apply_finance_refund_effects(db, *, event, provider_payment, provider_charge, provider_refunds):
    """Finance-only refund path, with the same durable event and real-ID rules.

    No order authority is fabricated. If an order appeared since admission,
    the canonical processor must handle it on retry under the order lock.
    """
    await assert_order_money_protocol_ready(db)
    signed,digest=_event_binding(event)
    row=(await db.execute(text('select * from stripe_events where stripe_event_id=:id for update'),{'id':event['id']})).mappings().one()
    if (not row['signature_valid'] or row['payload_json']!=event or
            row['refund_binding_sha256']!=digest or row['refund_phase'] not in {'admitted','applied'} or row['refund_order_id'] is not None):
        raise OrderMoneyConflict('Finance refund lacks durable signed binding')
    if await resolve_order_id(db,signed['payment_intent'],metadata=provider_payment.get('metadata')) is not None:
        raise OrderMoneyConflict('Canonical order appeared during finance refund; retry')
    payment=(await db.execute(select(Payment).where(Payment.stripe_payment_intent_id==signed['payment_intent'])
        .with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
    if payment is None:
        raise OrderMoneyConflict('Finance refund original Payment unavailable')
    pi,ch=provider_payment,provider_charge
    if (pi.get('id')!=signed['payment_intent'] or ch.get('id')!=signed['id'] or
            ch.get('id')!=payment.stripe_charge_id or ch.get('payment_intent')!=pi['id'] or
            pi.get('latest_charge')!=ch['id'] or pi.get('status')!='succeeded' or
            ch.get('paid') is not True or ch.get('captured') is not True or
            pi.get('livemode')!=event['livemode'] or ch.get('livemode')!=event['livemode'] or
            event['livemode']==settings.STRIPE_TEST_MODE or pi.get('transfer_data') or ch.get('transfer_data') or
            pi.get('on_behalf_of') or ch.get('on_behalf_of') or
            pi.get('currency')!=payment.currency.lower() or ch.get('currency')!=payment.currency.lower() or
            pi.get('customer')!=payment.stripe_customer_id or ch.get('customer')!=payment.stripe_customer_id or
            any(type(value) is not int or value!=payment.amount_cents for value in
                (pi.get('amount'),pi.get('amount_received'),ch.get('amount'),ch.get('amount_captured')))):
        raise OrderMoneyConflict('Finance refund provider/Payment binding mismatch')
    total=validate_refund_snapshot(pi,ch,provider_refunds)
    existing=(await db.execute(select(Refund).where(Refund.payment_id==payment.id)
        .order_by(Refund.stripe_refund_id,Refund.id).with_for_update().execution_options(populate_existing=True))).scalars().all()
    by_id={r.stripe_refund_id:r for r in existing}
    succeeded={r['id']:r for r in provider_refunds if r['status']=='succeeded'}
    for r in existing:
        if r.status=='succeeded' and r.effects_applied_at is None:
            raise OrderMoneyConflict('Legacy finance refund requires reconciliation')
        if r.effects_applied_at and (r.stripe_refund_id not in succeeded or r.order_id is not None or
                r.amount_cents!=succeeded[r.stripe_refund_id]['amount'] or r.entity_id!=payment.entity_id or
                r.currency!=payment.currency or not r.journal_entry_id):
            raise OrderMoneyConflict('Applied finance refund binding changed')
    for rid,p in sorted(succeeded.items()):
        if rid not in by_id:
            r=Refund(entity_id=payment.entity_id,payment_id=payment.id,stripe_refund_id=rid,
                amount_cents=p['amount'],currency=payment.currency,status='pending',
                reason=p.get('reason') or 'requested_by_customer',requested_by='system:webhook')
            db.add(r)
            by_id[rid]=r
        r=by_id[rid]
        if r.amount_cents!=p['amount'] or r.entity_id!=payment.entity_id or r.currency!=payment.currency or r.order_id:
            raise OrderMoneyConflict('Finance refund allocation changed')
    await db.flush()
    now=await db.scalar(text('select clock_timestamp()'))
    for rid,p in sorted(succeeded.items()):
        r=by_id[rid]
        if r.effects_applied_at:
            journal=await db.get(JournalEntry,r.journal_entry_id)
            if (journal is None or journal.status!='posted' or journal.posted_at is None or
                    journal.entity_id!=payment.entity_id or journal.source_ref!='refund:'+rid or
                    journal.source_type!='reversal'):
                raise OrderMoneyConflict('Finance refund journal not posted or conflicting')
            lines=(await db.execute(text("""select a.entity_id,a.code,l.debit_cents,l.credit_cents,l.currency
                from journal_lines l join gl_accounts a on a.id=l.account_id
                where l.entry_id=:id order by a.code,l.id"""),{'id':journal.id})).all()
            expected=[(payment.entity_id,'1000',0,r.amount_cents,payment.currency),
                      (payment.entity_id,'4000',r.amount_cents,0,payment.currency)]
            if [tuple(line) for line in lines]!=expected:
                raise OrderMoneyConflict('Finance refund journal allocation changed')
            continue
        journal=await FinanceEngine().record_refund(payment_id=payment.id,amount_cents=r.amount_cents,
            reason=r.reason,stripe_refund_id=rid,db=db,entity_id=payment.entity_id)
        await db.refresh(journal)
        if journal.status!='posted' or journal.posted_at is None:
            raise OrderMoneyConflict('Finance refund journal posting rejected')
        r.journal_entry_id=journal.id
        r.status='succeeded'
        r.effects_applied_at=r.processed_at=now
    if total:
        payment.status='refunded' if total==payment.amount_cents else 'partially_refunded'
    await db.flush()
    await db.execute(text("update stripe_events set refund_phase='applied',refund_applied_at=clock_timestamp(),status='completed',processed_status='processed',error_message=null where stripe_event_id=:id"),{'id':event['id']})
    return {'stripe_event_id':event['id'],'processed_status':'processed','refund_total_cents':total}
