"""Common order money locks. Transaction ownership stays with callers.

The event row, when present, must already be locked before entering here.
Never acquire another event after the order. Readiness lookups are nonlocking.
"""
from dataclasses import dataclass
from contextlib import contextmanager
from functools import wraps
import hashlib
import json
from uuid import UUID

from sqlalchemy import or_, select, text
from app.models.order import Order
from app.models.transaction import Transaction
from app.models.order_money_state import OrderMoneyState
from app.models.finance import Payment, Refund
from app.models.agent_api_key import AgentAPIKey


# Explicit blocking order for the participating order-money writers. FK checks
# on unchanged parent keys take KEY SHARE, which is compatible with non-key
# UPDATE. The order/transaction cycle therefore requires owning both before
# updating status or creating authority/refund/audit children.
LOCK_ORDER = ('stripe_events','orders','transactions','order_money_states','payments',
              'refunds','agent_api_keys','accounting_periods','gl_accounts','journal_entries')
# Catalog-verified implicit edges (see executable PostgreSQL catalog/barrier tests):
# stripe_events.refund_order_id -> orders; orders status trigger -> transactions
# -> transaction_events; authority -> orders/transactions/Payment/journal/entity;
# Payment -> user/entity/invoice/journal; Refund -> order/tx/Payment/entity/invoice/
# journal; agent -> party; period/account -> entity; journal -> period/entity;
# journal_lines -> account/journal. Entity/party/user/listing identities are not
# changed by this protocol. New Payment/Refund parent FK checks run before GL.
# Journal guards read period/lines/account/entity without FOR UPDATE; the period
# and GL locks are acquired before journal INSERT/post and remain caller-owned.
# Billing generic callers: own event -> Payment -> Refund (refund only), then
# period -> sorted GL -> journal. Credits topup is prelocked before GL below.
# Never acquire a second event from an order writer or provider I/O under locks.


def assert_lock_sequence(sequence):
    held=set()
    last=-1
    for node in sequence:
        if node in held:
            continue
        rank=LOCK_ORDER.index(node)
        if rank<last:
            raise OrderMoneyConflict('Reversed order money lock edge')
        held.add(node)
        last=rank


class OrderMoneyConflict(ValueError):
    """Contradictory historical binding requires reconciliation, not guessing."""


@contextmanager
def payment_database_deadline(db, *, retain_until_commit=False):
    """Bound the entire caller-owned DB phase, including its final commit.

    The connection value is only a nested time budget, never payment authority.
    Provider calls must take place outside this context.
    """
    import time
    from sqlalchemy import event
    connection = db.connection()
    connection_info = connection.info
    previous = connection_info.get('canonical_payment_deadline')
    deadline = min(previous, time.monotonic() + 5) if previous is not None else time.monotonic() + 5
    connection_info['canonical_payment_deadline'] = deadline
    connection.execute(text("SET LOCAL lock_timeout='250ms'"))
    connection.execute(text("SET LOCAL idle_in_transaction_session_timeout='2000ms'"))
    def bounded(conn, cursor, statement, parameters, context, executemany):
        remaining = int((deadline - time.monotonic()) * 1000)
        if remaining <= 0:
            raise OrderMoneyConflict('Payment database deadline exceeded')
        cursor.execute("SET LOCAL statement_timeout='" + str(min(2000, remaining)) + "ms'")
    event.listen(connection, 'before_cursor_execute', bounded)
    try:
        yield
        if time.monotonic() >= deadline:
            raise OrderMoneyConflict('Payment database deadline exceeded')
    finally:
        def clean():
            event.remove(connection, 'before_cursor_execute', bounded)
            if previous is None:
                connection_info.pop('canonical_payment_deadline', None)
            else:
                connection_info['canonical_payment_deadline'] = previous
        if retain_until_commit and not connection.closed and db.in_transaction():
            # The caller owns commit. Keep the decreasing budget on its exact
            # transaction, including flush/commit; no payment facts are stored.
            active = True
            def before_commit(session):
                if active and time.monotonic() >= deadline:
                    raise OrderMoneyConflict('Payment database deadline exceeded')
            def ended(session, transaction):
                nonlocal active
                if active and transaction.parent is None:
                    active = False
                    clean()
                    # Removing this event while it dispatches is unsafe; it is
                    # registered once and becomes inert after this transaction.
            event.listen(db, 'before_commit', before_commit)
            event.listen(db, 'after_transaction_end', ended)
        else:
            clean()


def bounded_payment_method(function):
    """Async service method whose complete work is a database-only phase."""
    @wraps(function)
    async def bounded(self, *args, **kwargs):
        import asyncio
        manager = None
        try:
            async with asyncio.timeout(5):
                def start(sync):
                    context = payment_database_deadline(sync, retain_until_commit=True)
                    context.__enter__()
                    return context
                manager = await self.db.run_sync(start)
                return await function(self, *args, **kwargs)
        except BaseException:
            await self.db.rollback()
            raise
        finally:
            if manager is not None:
                await self.db.run_sync(lambda sync: manager.__exit__(None, None, None))
    return bounded



from contextlib import asynccontextmanager

@asynccontextmanager
async def payment_database_phase(db):
    import asyncio
    manager=None
    try:
        async with asyncio.timeout(5):
            def start(sync):
                context=payment_database_deadline(sync,retain_until_commit=True)
                context.__enter__()
                return context
            manager=await db.run_sync(start)
            yield
    except BaseException:
        await db.rollback()
        raise
    finally:
        if manager is not None:
            await db.run_sync(lambda sync: manager.__exit__(None,None,None))

def canonical_digest(value):
    def check(v):
        if v is None or type(v) is bool or (type(v) is int and abs(v) <= 9007199254740991):
            return
        if type(v) is str and v.isascii():
            return
        if type(v) is list:
            for item in v:
                check(item)
            return
        if type(v) is dict and all(type(k) is str and k.isascii() for k in v):
            for item in v.values():
                check(item)
            return
        raise OrderMoneyConflict('Noncanonical money receipt')
    check(value)
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),
                                    ensure_ascii=True,allow_nan=False).encode('ascii')).hexdigest()


@dataclass
class LockedOrderMoney:
    order: Order
    transaction: Transaction | None
    state: OrderMoneyState
    payment: Payment | None
    refunds: list[Refund]
    agent_key: AgentAPIKey | None


def validate_order_binding(order, transaction):
    values = (order.amount_cents, order.platform_fee_cents, order.seller_amount_cents)
    if (any(type(v) is not int or v < 0 for v in values) or values[0] <= 0 or
            values[0] != values[1] + values[2] or order.currency.upper() != 'USD' or
            not order.stripe_payment_intent_id):
        raise OrderMoneyConflict('Invalid order money binding')
    if transaction is not None:
        fields = ('buyer_id','seller_id','listing_id','amount_cents','platform_fee_cents',
                  'seller_amount_cents','stripe_payment_intent_id')
        if (transaction.order_id != order.id or any(getattr(order,f) != getattr(transaction,f) for f in fields)
                or transaction.currency.upper() != order.currency.upper()):
            raise OrderMoneyConflict('Order/transaction reverse binding mismatch')



@dataclass(frozen=True, slots=True)
class ExpectedPaymentBinding:
    """Signed/locked facts crossing a session boundary, never a repair flag."""
    order_id: UUID
    transaction_id: UUID
    stored_checkout_session_id: str | None
    signed_checkout_session_id: str | None
    signed_payment_intent_id: str
    signed_amount_cents: int
    signed_currency: str
    buyer_id: UUID
    seller_id: UUID
    listing_id: UUID
    platform_fee_cents: int
    seller_amount_cents: int

    def __post_init__(self):
        for name in ('order_id', 'transaction_id', 'buyer_id', 'seller_id', 'listing_id'):
            if type(getattr(self, name)) is not UUID:
                raise OrderMoneyConflict('Invalid binding UUID')
        for name in ('signed_amount_cents', 'platform_fee_cents', 'seller_amount_cents'):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 2147483647:
                raise OrderMoneyConflict('Invalid binding integer')
        for name in ('stored_checkout_session_id', 'signed_checkout_session_id', 'signed_payment_intent_id'):
            value = getattr(self, name)
            if value is None and name != 'signed_payment_intent_id':
                continue
            _payment_identifier(value)
        if (type(self.signed_currency) is not str or len(self.signed_currency) != 3
                or not all('A' <= c <= 'Z' for c in self.signed_currency)
                or self.signed_amount_cents != self.platform_fee_cents + self.seller_amount_cents):
            raise OrderMoneyConflict('Invalid binding money equation/currency')


def _payment_identifier(value):
    if (type(value) is not str or not 1 <= len(value) <= 255
            or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value)):
        raise OrderMoneyConflict('Invalid payment identifier')
    return value


def _locked_initial_pair(db, order_id):
    order = db.execute(select(Order).where(Order.id == order_id).with_for_update()
                       .execution_options(populate_existing=True)).scalar_one_or_none()
    if order is None:
        raise OrderMoneyConflict('Order not found')
    txs = db.execute(select(Transaction).where(Transaction.order_id == order_id)
                     .order_by(Transaction.id).with_for_update()
                     .execution_options(populate_existing=True)).scalars().all()
    reverse = db.scalar(text('select transaction_id from orders where id=:id'), {'id': order_id})
    if len(txs) > 1 or reverse != (txs[0].id if txs else None):
        raise OrderMoneyConflict('Missing or conflicting order transaction reverse link')
    return order, txs[0] if txs else None


def _initial_history_absent(db, order, tx, *, paid_recovery=False, payment_intent_id=None):
    if (order.revoked or order.refund_amount_cents or order.refunded_at or order.stripe_refund_id
            or order.stripe_transfer_id or order.disputed_at or order.delivered_at
            or order.completed_at or order.confirmed_at or (tx and tx.settled_at)):
        raise OrderMoneyConflict('Payment history prevents initial binding')
    if not paid_recovery and (order.status != 'created' or (tx and tx.status not in {'initiated','checkout_pending','agent_payment_pending'}) or order.paid_at or (tx and tx.paid_at)):
        raise OrderMoneyConflict('Paid history prevents initial binding')
    # These are absence checks, never creating money helpers. Existing rows,
    # even empty authority, require independent reconciliation.
    if db.scalar(select(OrderMoneyState.order_id).where(OrderMoneyState.order_id == order.id).limit(1)):
        raise OrderMoneyConflict('Existing money authority prevents initial binding')
    if db.scalar(select(Payment.id).where(Payment.stripe_payment_intent_id == (payment_intent_id or order.stripe_payment_intent_id)).limit(1)):
        raise OrderMoneyConflict('Existing payment prevents initial binding')
    if db.scalar(select(Refund.id).where(or_(Refund.order_id == order.id,
                 Refund.transaction_id == (tx.id if tx else None))).limit(1)):
        raise OrderMoneyConflict('Existing refund prevents initial binding')
    if db.scalar(text('select exists(select 1 from workspace_refund_test_authorities where order_id=:id)'), {'id': order.id}):
        raise OrderMoneyConflict('Registered history prevents initial binding')


def bind_initial_order_payment_intent_sync(db, *, order_id, payment_intent_id,
        expected_transaction_id, mode, expected_binding=None,
        expected_agent_attempt_id=None, expected_agent_attempt_revision=None,
        provider_evidence=None):
    """Noncreating initial producer; caller owns rollback and commit.

    The event mutex, if applicable, must already be held. No provider work or
    event acquisition occurs here. Every read/write has the remaining DB budget.
    """
    import time
    from sqlalchemy import event
    modes = {'checkout_completion', 'direct_payment_completion',
             'signed_capture_recovery', 'agent_attempt_completion'}
    if mode not in modes:
        raise OrderMoneyConflict('Unknown initial binding mode')
    if mode != 'agent_attempt_completion' and any(v is not None for v in
            (expected_agent_attempt_id, expected_agent_attempt_revision, provider_evidence)):
        raise OrderMoneyConflict('Unexpected agent binding facts')
    _payment_identifier(payment_intent_id)
    phase = payment_database_deadline(db,retain_until_commit=True)
    phase.__enter__()
    connection = db.connection()
    deadline = time.monotonic() + 5
    connection.execute(text("SET LOCAL lock_timeout='250ms'"))
    connection.execute(text("SET LOCAL statement_timeout='2000ms'"))
    def bound(conn, cursor, statement, parameters, context, executemany):
        remaining = int((min(deadline, connection.info.get('canonical_payment_deadline', deadline))-time.monotonic())*1000)
        if remaining <= 0:
            raise OrderMoneyConflict('Initial binding deadline exceeded')
        cursor.execute("SET LOCAL statement_timeout='" + str(min(2000, remaining)) + "ms'")
    event.listen(connection, 'before_cursor_execute', bound)
    try:
        with db.no_autoflush:
            order, tx = _locked_initial_pair(db, order_id)
            if expected_transaction_id != (tx.id if tx else None):
                raise OrderMoneyConflict('Expected reverse binding changed')
            if tx is None:
                if expected_binding is not None or mode != 'checkout_completion':
                    raise OrderMoneyConflict('Legacy binding mode/facts mismatch')
                if order.stripe_payment_intent_id not in (None, payment_intent_id):
                    raise OrderMoneyConflict('Legacy PI conflict')
                if order.status != 'created' and order.stripe_payment_intent_id != payment_intent_id:
                    raise OrderMoneyConflict('Legacy paid history cannot be repaired')
                if order.revoked or order.refund_amount_cents or order.disputed_at:
                    raise OrderMoneyConflict('Legacy financial history prevents paid transition')
                order.stripe_payment_intent_id = payment_intent_id
                db.flush()
                return order, None
            if type(expected_binding) is not ExpectedPaymentBinding:
                raise OrderMoneyConflict('Canonical expected_binding required')
            expected_binding.__post_init__()
            b = expected_binding
            if (b.order_id != order.id or b.transaction_id != tx.id
                    or b.signed_payment_intent_id != payment_intent_id):
                raise OrderMoneyConflict('Expected payment identity changed')
            for name, expected in (('buyer_id', b.buyer_id), ('seller_id', b.seller_id),
                    ('listing_id', b.listing_id), ('amount_cents', b.signed_amount_cents),
                    ('platform_fee_cents', b.platform_fee_cents), ('seller_amount_cents', b.seller_amount_cents)):
                if getattr(order, name) != expected or getattr(tx, name) != expected:
                    raise OrderMoneyConflict('Expected payment facts changed')
            if order.currency.upper() != b.signed_currency or tx.currency.upper() != b.signed_currency:
                raise OrderMoneyConflict('Expected currency changed')
            stored = order.stripe_checkout_session_id
            if stored != b.stored_checkout_session_id:
                raise OrderMoneyConflict('Stored Session changed after validation')
            if mode in {'checkout_completion', 'signed_capture_recovery'}:
                if b.signed_checkout_session_id is None or (stored is not None and stored != b.signed_checkout_session_id):
                    raise OrderMoneyConflict('Signed Session mismatch')
                if mode == 'signed_capture_recovery' and stored is None:
                    raise OrderMoneyConflict('Recovery requires original Session')
            elif b.signed_checkout_session_id is not None:
                raise OrderMoneyConflict('Unexpected signed Session')
            metadata = tx.tx_metadata or {}
            if type(metadata) is not dict or metadata.get('payment_intent_id') not in (None, '', payment_intent_id):
                raise OrderMoneyConflict('Metadata PI conflict')
            opi, tpi = order.stripe_payment_intent_id, tx.stripe_payment_intent_id
            if opi not in (None, payment_intent_id) or tpi not in (None, payment_intent_id):
                raise OrderMoneyConflict('Conflicting non-NULL payment intent')
            if order.revoked or order.refund_amount_cents or order.disputed_at or order.status in {'refunded', 'partially_refunded', 'disputed', 'cancelled'}:
                raise OrderMoneyConflict('Financial history prevents completion')
            if opi == tpi == payment_intent_id:
                validate_order_binding(order, tx)
                if mode == 'agent_attempt_completion':
                    a = validate_agent_pair(order, tx)
                    if (type(expected_agent_attempt_id) is not UUID
                            or str(expected_agent_attempt_id) != a['attempt_id']
                            or type(expected_agent_attempt_revision) is not int
                            or expected_agent_attempt_revision != a['revision']
                            or stored is not None):
                        raise OrderMoneyConflict('Agent correlation/session mismatch')
                    compare_agent_evidence(a, provider_evidence)
                return order, tx
            if opi is None and tpi is not None:
                raise OrderMoneyConflict('Unexplained asymmetric PI history')
            if mode == 'agent_attempt_completion':
                # The attempt protocol must supply complete correlation and evidence;
                # never let this mode become a both-NULL browser repair.
                validate_agent_initial_binding(db, order, tx, expected_agent_attempt_id,
                                               expected_agent_attempt_revision, provider_evidence)
            elif mode == 'checkout_completion':
                if order.status != 'created' or tx.status != 'checkout_pending':
                    raise OrderMoneyConflict('Checkout initial state mismatch')
            elif mode == 'direct_payment_completion':
                if opi != payment_intent_id or order.status != 'created' or tx.status != 'checkout_pending':
                    raise OrderMoneyConflict('Direct call lacks established PI ownership')
            elif (opi != payment_intent_id or order.status not in {'paid', 'pending_delivery'}
                    or tx.status not in {'paid', 'fulfilling'}):
                raise OrderMoneyConflict('Signed recovery state mismatch')
            _initial_history_absent(db, order, tx, paid_recovery=mode == 'signed_capture_recovery', payment_intent_id=payment_intent_id)
            order.stripe_payment_intent_id = payment_intent_id
            tx.stripe_payment_intent_id = payment_intent_id
            db.flush()
            validate_order_binding(order, tx)
            return order, tx
    finally:
        event.remove(connection, 'before_cursor_execute', bound)
        phase.__exit__(None,None,None)



AGENT_ATTEMPT_KEY = 'canonical_agent_attempt_v1'
AGENT_ATTEMPT_FIELDS = frozenset(('version attempt_id transaction_id original_order_id api_key_id org_id buyer_id seller_id listing_id provider_idempotency_key amount_cents currency platform_fee_cents seller_amount_cents customer_id payment_method_id provider_account_id livemode request_metadata prepared_at revision state observed_payment_intent_id observed_provider_status observed_at evidence_source spend_release_state release_evidence').split())
AGENT_OBSERVATION_FIELDS = frozenset(('revision state observed_payment_intent_id observed_provider_status observed_at evidence_source spend_release_state release_evidence').split())
AGENT_STATES = frozenset(('prepared_unknown response_observed bound_pending cancellation_unknown cancelled_reconciled conflict_reconciliation completed').split())
AGENT_TRANSITIONS = {
    'prepared_unknown': {'response_observed', 'bound_pending', 'cancellation_unknown', 'conflict_reconciliation', 'cancelled_reconciled'},
    'response_observed': {'bound_pending', 'cancellation_unknown', 'conflict_reconciliation', 'cancelled_reconciled'},
    'bound_pending': {'completed', 'cancelled_reconciled', 'conflict_reconciliation', 'response_observed'},
    'cancellation_unknown': {'cancelled_reconciled', 'bound_pending', 'conflict_reconciliation'},
    'conflict_reconciliation': {'response_observed', 'bound_pending', 'cancelled_reconciled'},
    'completed': set(), 'cancelled_reconciled': set(),
}


def agent_timestamp(value):
    from datetime import datetime, timezone
    if type(value) is not str:
        raise OrderMoneyConflict('Invalid attempt timestamp')
    try:
        parsed = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise OrderMoneyConflict('Invalid attempt timestamp') from exc
    if parsed.strftime('%Y-%m-%dT%H:%M:%S.%fZ') != value:
        raise OrderMoneyConflict('Noncanonical attempt timestamp')
    return parsed


def agent_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def _agent_uuid(value):
    if type(value) is not str:
        raise OrderMoneyConflict('Invalid attempt UUID')
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as exc:
        raise OrderMoneyConflict('Invalid attempt UUID') from exc
    if str(parsed) != value:
        raise OrderMoneyConflict('Noncanonical attempt UUID')
    return parsed


def validate_agent_attempt(value):
    if type(value) is not dict or set(value) != AGENT_ATTEMPT_FIELDS:
        raise OrderMoneyConflict('Invalid durable attempt shape')
    for name in ('attempt_id', 'transaction_id', 'original_order_id', 'api_key_id', 'org_id', 'buyer_id', 'seller_id', 'listing_id'):
        raw = value[name]
        _agent_uuid(raw)
    for name in ('version', 'revision', 'amount_cents', 'platform_fee_cents', 'seller_amount_cents'):
        raw = value[name]
        if type(raw) is not int or not 0 <= raw <= 2147483647:
            raise OrderMoneyConflict('Invalid attempt integer')
    if value['version'] != 1 or value['revision'] < 1:
        raise OrderMoneyConflict('Unknown attempt version/revision')
    if (type(value['state']) is not str or value['state'] not in AGENT_STATES
            or type(value['spend_release_state']) is not str or value['spend_release_state'] not in {'held', 'released'}
            or type(value['livemode']) is not bool or type(value['currency']) is not str
            or len(value['currency']) != 3 or not all('a' <= c <= 'z' for c in value['currency'])
            or value['amount_cents'] != value['platform_fee_cents'] + value['seller_amount_cents']):
        raise OrderMoneyConflict('Invalid attempt state/money/context')
    for name in ('customer_id', 'payment_method_id', 'provider_idempotency_key'):
        _payment_identifier(value[name])
    if value['provider_account_id'] is not None:
        _payment_identifier(value['provider_account_id'])
    if value['provider_idempotency_key'] != value['api_key_id'] + ':' + value['transaction_id']:
        raise OrderMoneyConflict('Attempt idempotency identity mismatch')
    expected_meta = {'transaction_id': value['transaction_id'], 'order_id': value['original_order_id'],
                     'api_key_id': value['api_key_id'], 'buyer_type': 'agent'}
    if type(value['request_metadata']) is not dict or value['request_metadata'] != expected_meta:
        raise OrderMoneyConflict('Attempt metadata identity mismatch')
    agent_timestamp(value['prepared_at'])
    observation = [value[n] for n in ('observed_payment_intent_id', 'observed_provider_status', 'observed_at')]
    if value['evidence_source'] is None:
        if any(v is not None for v in observation):
            raise OrderMoneyConflict('Partial attempt observation')
    else:
        if type(value['evidence_source']) is not str or value['evidence_source'] not in {'create_response', 'signed_event_and_provider_read', 'provider_read'}:
            raise OrderMoneyConflict('Unknown evidence source')
        _payment_identifier(observation[0]); _payment_identifier(observation[1]); agent_timestamp(observation[2])
        if observation[2] < value['prepared_at']:
            raise OrderMoneyConflict('Observation precedes preparation')
    if value['state']=='prepared_unknown' and value['evidence_source'] is not None:
        raise OrderMoneyConflict('Prepared attempt already has an observation')
    if value['state'] not in {'prepared_unknown','conflict_reconciliation'} and value['evidence_source'] is None:
        raise OrderMoneyConflict('Attempt state requires a complete observation')
    if value['state']=='completed' and (value['observed_provider_status']!='succeeded'
            or value['evidence_source']!='signed_event_and_provider_read'):
        raise OrderMoneyConflict('Completed attempt requires original signed capture')
    released = value['state'] == 'cancelled_reconciled'
    if (value['spend_release_state'] == 'released') != released or (value['release_evidence'] is not None) != released:
        raise OrderMoneyConflict('Attempt release state mismatch')
    if released:
        r = value['release_evidence']
        if type(r) is not dict or set(r) != {'reconciliation_id','payment_intent_id','provider_status','amount_received_cents','observed_at','committed_at','source'}:
            raise OrderMoneyConflict('Invalid release certificate')
        _agent_uuid(r['reconciliation_id'])
        if (r['payment_intent_id'] != value['observed_payment_intent_id']
                or r['provider_status'] != 'cancelled' or type(r['amount_received_cents']) is not int
                or r['amount_received_cents'] != 0 or r['source'] != 'provider_read'
                or value['observed_provider_status'] != 'canceled' or value['evidence_source'] != 'provider_read'
                or r['observed_at'] != value['observed_at']):
            raise OrderMoneyConflict('Invalid release evidence')
        agent_timestamp(r['observed_at']); agent_timestamp(r['committed_at'])
        if r['observed_at'] > r['committed_at'] or r['observed_at'] < value['prepared_at']:
            raise OrderMoneyConflict('Invalid release observation ordering')
    return value


@dataclass(frozen=True, slots=True)
class AgentProviderEvidence:
    source: str
    payment_intent_id: str
    provider_status: str
    amount_cents: int
    currency: str
    customer_id: str
    payment_method_id: str
    provider_account_id: str | None
    livemode: bool
    metadata: tuple
    observed_at: str
    signed_event_id: str | None
    amount_received_cents: int
    amount_capturable_cents: int

    def __post_init__(self):
        if type(self.source) is not str or self.source not in {'create_response','provider_read','signed_event_and_provider_read'}:
            raise OrderMoneyConflict('Invalid provider evidence source')
        for name in ('payment_intent_id','provider_status','customer_id','payment_method_id'):
            _payment_identifier(getattr(self, name))
        if self.provider_account_id is not None: _payment_identifier(self.provider_account_id)
        if (self.signed_event_id is None) != (self.source != 'signed_event_and_provider_read'):
            raise OrderMoneyConflict('Signed evidence event identity mismatch')
        if self.signed_event_id is not None: _payment_identifier(self.signed_event_id)
        for n in ('amount_cents','amount_received_cents','amount_capturable_cents'):
            v = getattr(self, n)
            if type(v) is not int or not 0 <= v <= 2147483647:
                raise OrderMoneyConflict('Invalid provider amount')
        if type(self.livemode) is not bool or type(self.currency) is not str or len(self.currency) != 3 or not all('a' <= c <= 'z' for c in self.currency):
            raise OrderMoneyConflict('Invalid provider context')
        if type(self.metadata) is not tuple or any(type(x) is not tuple or len(x) != 2
                or type(x[0]) is not str or type(x[1]) is not str for x in self.metadata):
            raise OrderMoneyConflict('Provider metadata is not immutable')
        data = dict(self.metadata)
        if len(data) != 4 or len(self.metadata) != 4 or set(data) != {'transaction_id','order_id','api_key_id','buyer_type'} or data['buyer_type'] != 'agent':
            raise OrderMoneyConflict('Invalid provider metadata')
        for n in ('transaction_id','order_id','api_key_id'):
            _agent_uuid(data[n])
        agent_timestamp(self.observed_at)


def agent_provider_evidence(obj, *, source, account=None, signed_event_id=None):
    """Trusted SDK boundary: expanded references supply their explicit id only."""
    from collections.abc import Mapping
    def identifier(value):
        if isinstance(value, Mapping): value = value.get('id')
        return _payment_identifier(value)
    if not isinstance(obj, Mapping) or not isinstance(obj.get('metadata'), Mapping):
        raise OrderMoneyConflict('Missing provider evidence')
    if obj.get('on_behalf_of') or obj.get('transfer_data'):
        raise OrderMoneyConflict('Unexpected agent provider account context')
    return AgentProviderEvidence(source, identifier(obj.get('id')), obj.get('status'),
        obj.get('amount'), obj.get('currency'), identifier(obj.get('customer')),
        identifier(obj.get('payment_method')), account, obj.get('livemode'),
        tuple(sorted(obj['metadata'].items())), agent_now(), signed_event_id,
        obj.get('amount_received'), obj.get('amount_capturable'))


def compare_agent_evidence(attempt, evidence):
    validate_agent_attempt(attempt)
    if type(evidence) is not AgentProviderEvidence:
        raise OrderMoneyConflict('Complete provider evidence required')
    evidence.__post_init__()
    for a, e in (('amount_cents','amount_cents'),('currency','currency'),('customer_id','customer_id'),
                 ('payment_method_id','payment_method_id'),('provider_account_id','provider_account_id'),('livemode','livemode')):
        if attempt[a] != getattr(evidence,e): raise OrderMoneyConflict('Original provider request mismatch')
    if dict(evidence.metadata) != attempt['request_metadata']:
        raise OrderMoneyConflict('Original provider metadata mismatch')
    if attempt['observed_payment_intent_id'] not in (None, evidence.payment_intent_id):
        raise OrderMoneyConflict('Original observed PI cannot be replaced')
    if evidence.observed_at < (attempt['observed_at'] or attempt['prepared_at']):
        if not (attempt['state'] in {'completed','cancelled_reconciled'}
                and evidence.provider_status == attempt['observed_provider_status']):
            raise OrderMoneyConflict('Stale provider observation')


def validate_agent_pair(order, tx):
    metadata = tx.tx_metadata
    if type(metadata) is not dict or AGENT_ATTEMPT_KEY not in metadata:
        raise OrderMoneyConflict('Durable original attempt required')
    a = validate_agent_attempt(metadata[AGENT_ATTEMPT_KEY])
    if (a['original_order_id'] != str(order.id) or a['transaction_id'] != str(tx.id)
            or tx.order_id != order.id or tx.buyer_type != 'agent' or tx.api_key_id is None
            or a['api_key_id'] != str(tx.api_key_id) or a['org_id'] != str(tx.party_id)):
        raise OrderMoneyConflict('Attempt reverse/agent ownership mismatch')
    for n in ('buyer_id','seller_id','listing_id'):
        if a[n] != str(getattr(order,n)) or a[n] != str(getattr(tx,n)):
            raise OrderMoneyConflict('Attempt actor mismatch')
    for n in ('amount_cents','platform_fee_cents','seller_amount_cents'):
        if a[n] != getattr(order,n) or a[n] != getattr(tx,n):
            raise OrderMoneyConflict('Attempt money mismatch')
    if a['currency'].upper() != order.currency.upper() or a['currency'].upper() != tx.currency.upper():
        raise OrderMoneyConflict('Attempt currency mismatch')
    return a



def validate_agent_completed_capture(db, order, tx):
    """Read existing capture authority only; never repair a cached purchase."""
    validate_order_binding(order,tx)
    state=db.execute(select(OrderMoneyState).where(OrderMoneyState.order_id==order.id)
        .with_for_update().execution_options(populate_existing=True)).scalar_one_or_none()
    if (state is None or state.transaction_id!=tx.id or state.protocol_version!=1
            or state.capture_payment_id is None or state.capture_journal_entry_id is None
            or state.independent_revocation or state.refund_applied_cents or state.reconciliation_reason):
        raise OrderMoneyConflict('Completed attempt lacks coherent capture authority')
    payment=db.execute(select(Payment).where(Payment.id==state.capture_payment_id)
        .with_for_update().execution_options(populate_existing=True)).scalar_one_or_none()
    if (payment is None or payment.stripe_payment_intent_id!=order.stripe_payment_intent_id
            or payment.journal_entry_id!=state.capture_journal_entry_id or payment.entity_id!=state.billing_entity_id
            or payment.customer_id!=order.buyer_id or payment.amount_cents!=order.amount_cents or payment.currency.upper()!=order.currency.upper()
            or payment.status!='succeeded' or not payment.stripe_charge_id or tx.paid_at is None
            or tx.status not in {'paid','fulfilling','delivered','confirmed','settled','in_escrow'}):
        raise OrderMoneyConflict('Completed attempt capture binding changed')
    if not db.scalar(text("SELECT EXISTS(SELECT 1 FROM journal_entries WHERE id=:id AND status='posted' AND posted_at IS NOT NULL AND entity_id=:entity AND source_id=:payment AND source_ref=:ref)"),
            {'id':state.capture_journal_entry_id,'entity':state.billing_entity_id,'payment':payment.id,'ref':'marketplace_payment:'+order.stripe_payment_intent_id}):
        raise OrderMoneyConflict('Completed attempt journal binding changed')
    if db.scalar(text("SELECT EXISTS(SELECT 1 FROM stripe_events WHERE refund_phase='admitted' AND (refund_order_id=:id OR refund_payment_intent_id=:pi))"),{'id':order.id,'pi':order.stripe_payment_intent_id}):
        raise OrderMoneyConflict('Completed attempt has pending refund authority')

def validate_agent_initial_binding(db, order, tx, attempt_id, revision, evidence):
    a = validate_agent_pair(order,tx)
    if type(attempt_id) is not UUID or str(attempt_id) != a['attempt_id'] or type(revision) is not int or revision != a['revision']:
        raise OrderMoneyConflict('Attempt correlation/revision changed')
    compare_agent_evidence(a,evidence)
    if (order.status != 'created' or tx.status != 'initiated' or order.stripe_checkout_session_id is not None
            or a['state'] not in {'prepared_unknown','response_observed','conflict_reconciliation'}):
        raise OrderMoneyConflict('Agent initial state mismatch')


def transition_agent_attempt_sync(db, order, tx, *, state, evidence, release=False):
    """Caller already owns Order then Transaction; one metadata/counter protocol."""
    from uuid import uuid4
    a = validate_agent_pair(order,tx)
    compare_agent_evidence(a,evidence)
    if a['state'] in {'completed','cancelled_reconciled'}:
        if a['state'] != state:
            raise OrderMoneyConflict('Terminal attempt is immutable')
        return a
    if state != a['state'] and state not in AGENT_TRANSITIONS[a['state']]:
        raise OrderMoneyConflict('Invalid attempt transition')
    if state == a['state']:
        observation = (a['observed_payment_intent_id'], a['observed_provider_status'],
                       a['observed_at'], a['evidence_source'])
        incoming = (evidence.payment_intent_id, evidence.provider_status,
                    evidence.observed_at, evidence.source)
        if observation == incoming:
            return a
        if a['observed_at'] is not None and evidence.observed_at <= a['observed_at']:
            raise OrderMoneyConflict('Self-observation must be newer')
    if a['revision'] >= 2147483647:
        raise OrderMoneyConflict('Attempt revision overflow')
    if state=='completed':
        validate_agent_completed_capture(db,order,tx)
    updated = dict(a)
    updated.update(state=state, revision=a['revision']+1,
        observed_payment_intent_id=evidence.payment_intent_id,
        observed_provider_status=evidence.provider_status, observed_at=evidence.observed_at,
        evidence_source=evidence.source)
    if release:
        if (state != 'cancelled_reconciled' or evidence.source != 'provider_read'
                or evidence.provider_status != 'canceled' or evidence.amount_received_cents != 0
                or evidence.amount_capturable_cents != 0 or a['spend_release_state'] != 'held'):
            raise OrderMoneyConflict('Owned terminal no-liability proof required')
        _initial_history_absent(db,order,tx)
        validate_order_binding(order, tx)
        if order.stripe_payment_intent_id != evidence.payment_intent_id:
            raise OrderMoneyConflict('Release requires original bound PI')
        before_status = tx.status
        # The status trigger may touch Transaction; execute before the key lock.
        order.status = 'cancelled'
        db.flush()
        key = db.execute(select(AgentAPIKey).where(AgentAPIKey.id == tx.api_key_id)
                         .with_for_update().execution_options(populate_existing=True)).scalar_one_or_none()
        if key is None or key.org_id != tx.party_id or type(key.spend_used) is not int or key.spend_used < tx.amount_cents:
            raise OrderMoneyConflict('Insufficient or foreign reserved spend')
        key.spend_used -= tx.amount_cents
        tx.status = 'agent_payment_failed'
        updated['spend_release_state'] = 'released'
        updated['release_evidence'] = dict(reconciliation_id=str(uuid4()),
            payment_intent_id=evidence.payment_intent_id,provider_status='cancelled',
            amount_received_cents=0,observed_at=evidence.observed_at,committed_at=agent_now(),source='provider_read')
        from app.models.agent_audit_log import AgentAuditLog
        from app.models.transaction import TransactionEvent
        db.add(TransactionEvent(
            transaction_id=tx.id, event_type='status_changed', actor_type='system',
            from_status=before_status, to_status='agent_payment_failed',
            payload={'attempt_id': a['attempt_id'], 'source': 'agent_attempt_reconciliation'}))
        db.add(AgentAuditLog(
            api_key_id=tx.api_key_id, tool_name='checkout', transaction_id=tx.id,
            request_payload={'transaction_id': str(tx.id)},
            response_payload={'status': 'agent_payment_failed', 'attempt_id': a['attempt_id']},
            http_status=422, status='error'))
    elif state == 'cancelled_reconciled':
        raise OrderMoneyConflict('Release transition requires terminal proof')
    validate_agent_attempt(updated)
    tx.tx_metadata = {**tx.tx_metadata, AGENT_ATTEMPT_KEY: updated}
    db.flush()
    return updated


async def bind_initial_order_payment_intent(db, **kwargs):
    import asyncio
    try:
        async with asyncio.timeout(5):
            return await db.run_sync(lambda sync: bind_initial_order_payment_intent_sync(sync, **kwargs))
    except BaseException:
        await db.rollback()
        raise


def resolve_order_id_sync(db, payment_intent_id, *, metadata=None):
    """Nonlocking lookup; every result is validated again under the order lock."""
    ids = (db.execute(select(Order.id).where(Order.stripe_payment_intent_id == payment_intent_id))).scalars().all()
    meta = metadata or {}
    if len(ids) > 1:
        raise OrderMoneyConflict('Multiple orders for payment intent')
    if not ids:
        if meta.get('order_id') or meta.get('transaction_id'):
            raise OrderMoneyConflict('Canonical metadata has no matching order')
        return None
    oid = ids[0]
    if meta.get('order_id') and str(oid) != meta['order_id']:
        raise OrderMoneyConflict('Provider order metadata mismatch')
    if meta.get('transaction_id'):
        txs = (db.execute(select(Transaction.id).where(Transaction.order_id == oid))).scalars().all()
        if len(txs) != 1 or str(txs[0]) != meta['transaction_id']:
            raise OrderMoneyConflict('Provider transaction metadata mismatch')
    return oid



def locate_agent_event_sync(db, obj):
    """Metadata locates a retained attempt; it never authorizes money effects."""
    meta = obj.get('metadata') or {}
    pi = obj.get('id')
    tid = None
    if type(meta) is dict and meta.get('transaction_id'):
        try: tid = UUID(meta['transaction_id'])
        except (ValueError, TypeError, AttributeError): pass
    filters = [Transaction.stripe_payment_intent_id == pi]
    if tid is not None: filters.append(Transaction.id == tid)
    candidates = db.execute(select(Transaction).where(or_(*filters))).scalars().all()
    attempts = [t for t in candidates if type(t.tx_metadata) is dict and AGENT_ATTEMPT_KEY in t.tx_metadata]
    if not attempts: return None
    if len(attempts) != 1: raise OrderMoneyConflict('Ambiguous signed agent attempt')
    tx = attempts[0]
    a = validate_agent_attempt(tx.tx_metadata[AGENT_ATTEMPT_KEY])
    if meta != a['request_metadata'] or a['observed_payment_intent_id'] not in (None,pi):
        raise OrderMoneyConflict('Signed attempt locator mismatch')
    return tx.order_id


async def resolve_order_id(db, payment_intent_id, *, metadata=None):
    return await db.run_sync(lambda sync: resolve_order_id_sync(sync,payment_intent_id,metadata=metadata))


def lock_order_money_sync(db, order_id, *, refund_ids=()):
    """Order → transaction → authority → Payment → sorted Refund → agent key.

    New authority/Refund FK checks reference parents already locked here.
    Order's AFTER UPDATE trigger takes the linked transaction lock, also already
    owned. Accounting period/GL/journal work may follow; no upstream re-entry.
    """
    order = (db.execute(select(Order).where(Order.id == order_id)
        .with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
    if order is None:
        raise OrderMoneyConflict('Order not found')
    txs = (db.execute(select(Transaction).where(Transaction.order_id == order.id)
        .order_by(Transaction.id).with_for_update().execution_options(populate_existing=True))).scalars().all()
    if len(txs) > 1:
        raise OrderMoneyConflict('Multiple transactions for order')
    tx = txs[0] if txs else None
    reverse = db.scalar(text("select transaction_id from orders where id=:oid"), {'oid':order.id})
    if reverse != (tx.id if tx else None):
        raise OrderMoneyConflict('Missing or conflicting order transaction reverse link')
    validate_order_binding(order,tx)
    ids = (db.execute(select(Order.id).where(Order.stripe_payment_intent_id == order.stripe_payment_intent_id))).scalars().all()
    if ids != [order.id]:
        raise OrderMoneyConflict('Ambiguous payment intent reverse link')
    state = (db.execute(select(OrderMoneyState).where(OrderMoneyState.order_id == order.id)
        .with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
    if state is None:
        state = OrderMoneyState(order_id=order.id, transaction_id=tx.id if tx else None,
            independent_revocation=bool(order.revoked))
        db.add(state)
        db.flush()
    if state.protocol_version != 1 or state.transaction_id != (tx.id if tx else None):
        raise OrderMoneyConflict('Authority transaction/version mismatch')
    payment = (db.execute(select(Payment).where(Payment.stripe_payment_intent_id == order.stripe_payment_intent_id)
        .with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
    filters = [Refund.order_id == order.id, Refund.stripe_refund_id.in_(refund_ids)]
    if payment:
        filters.append(Refund.payment_id == payment.id)
    refunds = (db.execute(select(Refund).where(or_(*filters))
        .order_by(Refund.stripe_refund_id, Refund.id).with_for_update()
        .execution_options(populate_existing=True))).scalars().all()
    key = None
    if tx and tx.api_key_id:
        key = (db.execute(select(AgentAPIKey).where(AgentAPIKey.id == tx.api_key_id)
            .with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
        if key is None or key.org_id != tx.party_id or key.spend_used < 0:
            raise OrderMoneyConflict('Agent spend ownership/counter mismatch')
    return LockedOrderMoney(order,tx,state,payment,list(refunds),key)


async def lock_order_money(db, order_id, *, refund_ids=()):
    return await db.run_sync(lambda sync: lock_order_money_sync(sync, order_id, refund_ids=refund_ids))


async def order_payout_eligibility(db, money, *, destination):
    """All failed money guards precede hold timing, using PostgreSQL UTC time."""
    from datetime import timedelta
    from sqlalchemy import text
    from app.core.config import settings
    order,tx,state,payment = money.order,money.transaction,money.state,money.payment
    reasons=[]
    if not settings.ORDER_PAYOUT_DISPATCH_ENABLED:
        reasons.append('dispatch_disabled')
    if order.revoked or state.independent_revocation:
        reasons.append('revoked')
    if order.status in {'refunded','partially_refunded'} or state.refund_applied_cents>0 or (order.refund_amount_cents or 0)>0:
        reasons.append('refunded')
    if order.status=='disputed' or (order.disputed_at and not order.dispute_resolved_at):
        reasons.append('disputed')
    if state.payout_state not in {'idle','reserved'}:
        reasons.append('payout_'+state.payout_state)
    if state.reconciliation_reason:
        reasons.append('reconciliation_required')
    if order.stripe_transfer_id or state.stripe_transfer_id or order.transfer_status=='completed':
        reasons.append('existing_transfer')
    if (payment is None or payment.status!='succeeded' or not payment.stripe_charge_id or
            state.capture_payment_id != payment.id or not state.capture_journal_entry_id or
            payment.journal_entry_id != state.capture_journal_entry_id or
            state.billing_entity_id != payment.entity_id or payment.customer_id != order.buyer_id or
            payment.amount_cents != order.amount_cents or payment.currency != order.currency.upper()):
        reasons.append('captured_payment_unavailable')
    if any(r.status=='succeeded' and r.effects_applied_at is None for r in money.refunds):
        reasons.append('historical_refund_unreconciled')
    if any(r.status=='succeeded' and r.amount_cents>0 for r in money.refunds):
        reasons.append('refunded')
    if state.capture_journal_entry_id:
        valid_journal = await db.scalar(text("select exists(select 1 from journal_entries where id=:id and status='posted' and posted_at is not null and entity_id=:eid and source_id=:pid and source_ref=:ref)"),
            {'id':state.capture_journal_entry_id,'eid':state.billing_entity_id,'pid':state.capture_payment_id,'ref':'marketplace_payment:'+order.stripe_payment_intent_id})
        if not valid_journal:
            reasons.append('capture_journal_unposted_or_conflicting')
    if not isinstance(destination,str) or not destination.startswith('acct_'):
        reasons.append('connect_destination_unavailable')
    pending = await db.scalar(text('''select exists(select 1 from stripe_events where refund_phase='admitted'
        and (refund_order_id=:oid or refund_payment_intent_id=:pi))'''),
        {'oid':order.id,'pi':order.stripe_payment_intent_id})
    if pending:
        reasons.append('refund_admitted')
    if tx and tx.status!='confirmed':
        reasons.append('transaction_not_confirmed')
    if not tx and order.status!='completed':
        reasons.append('legacy_order_not_completed')
    now = await db.scalar(text('select clock_timestamp()'))
    confirmation=None
    if tx:
        confirmation=(await db.execute(text('''select id,created_at from transaction_events
            where transaction_id=:tid and to_status='confirmed' order by created_at desc,id desc limit 1'''),
            {'tid':tx.id})).mappings().first()
        if not confirmation:
            reasons.append('confirmation_event_missing')
        elif now < confirmation['created_at']+timedelta(hours=48):
            reasons.append('confirmation_hold')
    elif order.escrow_hold_until and now<order.escrow_hold_until:
        reasons.append('legacy_hold')
    return {'eligible':not reasons,'reasons':reasons,'observed_at':now.isoformat(),
            'confirmation_event_id':str(confirmation['id']) if confirmation else None,
            'confirmation_created_at':confirmation['created_at'].isoformat() if confirmation else None,
            'revision':state.revision}


def payout_request(money, destination):
    order, tx = money.order, money.transaction
    if tx:
        metadata = {'transaction_id': str(tx.id), 'tx_number': tx.tx_number,
                    'order_id': str(order.id), 'type': 'settlement'}
        key, group = 'settle_' + tx.tx_number, tx.tx_number
    else:
        metadata = {'order_id': str(order.id), 'order_number': order.order_number, 'type': 'payout'}
        key, group = 'transfer_' + str(order.id), order.order_number
    return dict(amount=order.seller_amount_cents, currency=order.currency.lower(),
                destination=destination, transfer_group=group, metadata=metadata, idempotency_key=key)


def validate_payout_request(money):
    state = money.state
    request = state.request_json
    if (not isinstance(request, dict) or request != payout_request(money, request.get('destination')) or
            not isinstance(request.get('destination'), str) or not request['destination'].startswith('acct_') or
            canonical_digest(request) != state.request_sha256 or
            request['idempotency_key'] != state.idempotency_key or request['transfer_group'] != state.transfer_group):
        raise OrderMoneyConflict('Frozen payout request binding changed')
    return dict(request)


async def audit_money_refusal(db, money, reasons):
    """Deduplicate unchanged scans under the already-owned order lock."""
    payload = {'protocol': 1, 'revision': money.state.revision, 'reasons': sorted(set(reasons))}
    digest = canonical_digest(payload)
    await db.execute(text('''insert into order_events (order_id,event_type,actor_type,metadata)
        select :oid,'status_changed','system',cast(:payload as jsonb)
        where not exists (select 1 from order_events where order_id=:oid
            and metadata->>'money_audit_sha256'=:digest)'''),
        {'oid':money.order.id,'digest':digest,'payload':json.dumps({**payload,'money_audit_sha256':digest})})


def cancel_reservation(money):
    state = money.state
    if state.dispatch_token or state.stripe_transfer_id:
        raise OrderMoneyConflict('Payout ownership cannot be canceled')
    if state.payout_state == 'reserved':
        state.payout_state = 'idle'
        state.request_json = state.request_sha256 = state.idempotency_key = state.transfer_group = None
        state.reserved_at = None
        state.revision += 1


async def reserve_order_payout(db, order_id):
    from app.services.refund_processing_service import assert_order_money_protocol_ready
    from app.domains.crm.core.stripe_connect_identity import get_stripe_connect_identity
    await assert_order_money_protocol_ready(db)
    money = await lock_order_money(db, order_id)
    identity = await get_stripe_connect_identity(money.order.seller_id, db)
    destination = identity.external_id if identity else None
    result = await order_payout_eligibility(db, money, destination=destination)
    if not result['eligible']:
        await audit_money_refusal(db, money, result['reasons'])
        await db.commit()
        return result
    state = money.state
    request = payout_request(money, destination)
    if state.payout_state == 'reserved':
        if validate_payout_request(money) != request:
            raise OrderMoneyConflict('Reserved payout destination changed')
    else:
        state.request_json, state.request_sha256 = request, canonical_digest(request)
        state.idempotency_key, state.transfer_group = request['idempotency_key'], request['transfer_group']
        state.reserved_at = await db.scalar(text('select clock_timestamp()'))
        state.payout_state = 'reserved'
        state.revision += 1
    result.update(revision=state.revision, payment_intent_id=money.order.stripe_payment_intent_id,
                  charge_id=money.payment.stripe_charge_id, request=request)
    await db.commit()
    return result


def validate_transfer(money, transfer):
    request = validate_payout_request(money)
    import re
    if (not isinstance(transfer.get('id'), str) or not re.fullmatch(r'tr_[A-Za-z0-9]+', transfer['id']) or
            transfer.get('reversed') is not False or type(transfer.get('amount_reversed')) is not int or
            transfer['amount_reversed'] != 0):
        raise OrderMoneyConflict('Invalid or reversed provider Transfer')
    for key in ('amount','currency','destination','transfer_group','metadata'):
        if transfer.get(key) != request[key] or (key == 'amount' and type(transfer.get(key)) is not int):
            raise OrderMoneyConflict('Provider Transfer contradicts frozen request')
    from app.core.config import settings
    if type(transfer.get('livemode')) is not bool or transfer['livemode'] == settings.STRIPE_TEST_MODE:
        raise OrderMoneyConflict('Provider Transfer mode mismatch')


async def finalize_order_transfer(db, order_id, token, transfer):
    from app.services.refund_processing_service import assert_order_money_protocol_ready
    from app.services.finance.engine import FinanceEngine
    eid = await assert_order_money_protocol_ready(db)
    money = await lock_order_money(db, order_id)
    state, order, tx = money.state, money.order, money.transaction
    if not token or state.dispatch_token != token or state.billing_entity_id != eid:
        raise OrderMoneyConflict('Transfer has no matching dispatch ownership')
    validate_transfer(money, transfer)
    if state.stripe_transfer_id not in (None,transfer['id']) or order.stripe_transfer_id not in (None,transfer['id']):
        raise OrderMoneyConflict('Different Transfer already recorded')
    remaining = max(order.seller_amount_cents-state.seller_refunded_cents-state.seller_payout_posted_cents,0)
    if state.payout_journal_entry_id:
        # Replay uses original allocation, validated against the immutable journal
        # by the engine. The original payable allocation is read from its lines.
        remaining = await db.scalar(text('''select coalesce(sum(l.debit_cents),0)::bigint from journal_lines l
            join gl_accounts a on a.id=l.account_id where l.entry_id=:jid and a.code='2110' '''),
            {'jid':state.payout_journal_entry_id})
    journal = await FinanceEngine().record_marketplace_transfer(db=db,entity_id=eid,order_id=order.id,
        stripe_transfer_id=transfer['id'],amount_cents=order.seller_amount_cents,remaining_payable_cents=remaining)
    if state.payout_journal_entry_id not in (None,journal.id):
        raise OrderMoneyConflict('Transfer journal changed')
    first = state.stripe_transfer_id is None
    state.payout_journal_entry_id = journal.id
    state.stripe_transfer_id = order.stripe_transfer_id = transfer['id']
    state.seller_payout_posted_cents = order.seller_amount_cents
    order.transfer_status = 'completed'
    state.completed_at = state.completed_at or await db.scalar(text('select clock_timestamp()'))
    pending = await db.scalar(text("select exists(select 1 from stripe_events where refund_phase='admitted' and (refund_order_id=:oid or refund_payment_intent_id=:pi))"), {'oid':order.id,'pi':order.stripe_payment_intent_id})
    restricted = (order.revoked or state.independent_revocation or state.refund_applied_cents or
                  order.status in {'refunded','partially_refunded','disputed'} or pending or state.reconciliation_reason)
    if restricted:
        state.payout_state = 'reconciliation_required'
        state.reconciliation_reason = state.reconciliation_reason or 'restriction_after_payout_ownership'
        await audit_money_refusal(db,money,[state.reconciliation_reason])
    else:
        state.payout_state = 'succeeded'
        if tx and tx.status != 'settled':
            if tx.status != 'confirmed':
                raise OrderMoneyConflict('Transfer transaction no longer confirmed')
            from app.services.transaction_service import get_transaction_service
            await get_transaction_service(db).transition(tx.id,'settled','system',
                payload={'stripe_transfer_id':transfer['id']},commit=False,money=money)
    if first:
        state.revision += 1
        order.transfer_attempts = (order.transfer_attempts or 0)+1
        order.last_transfer_attempt_at = state.completed_at
    await db.flush()
    result = {'status':state.payout_state,'stripe_transfer_id':transfer['id'],'order_id':str(order.id)}
    await db.commit()
    return result


async def dispatch_order_payout(db, order_id):
    """Only this invocation's newly committed token authorizes one create call."""
    from uuid import uuid4
    import stripe
    from app.core.stripe_async import run_stripe
    from app.services.refund_processing_service import read_provider_refunds, validate_captured_facts, validate_refund_snapshot
    reservation = await reserve_order_payout(db,order_id)
    if not reservation['eligible']:
        return {'status':'blocked',**reservation}
    pi,ch,refunds = await read_provider_refunds(reservation['payment_intent_id'],reservation['charge_id'])
    money = await lock_order_money(db,order_id)
    request = reservation['request']
    from app.domains.crm.core.stripe_connect_identity import get_stripe_connect_identity
    identity = await get_stripe_connect_identity(money.order.seller_id,db)
    destination = identity.external_id if identity else None
    result = await order_payout_eligibility(db,money,destination=destination)
    validate_captured_facts(money.order,money.transaction,pi,ch)
    if validate_refund_snapshot(pi,ch,refunds):
        result['reasons'].append('provider_refunded')
    if destination != request['destination']:
        result['reasons'].append('destination_changed')
    if money.state.revision != reservation['revision'] or money.state.payout_state != 'reserved':
        result['reasons'].append('reservation_changed')
    if result['reasons']:
        if money.state.payout_state == 'reserved':
            cancel_reservation(money)
        await audit_money_refusal(db,money,result['reasons'])
        await db.commit()
        return {'status':'blocked',**result,'eligible':False}
    if validate_payout_request(money) != request:
        raise OrderMoneyConflict('Reserved request changed before dispatch')
    token = uuid4()
    money.state.dispatch_token = token
    money.state.payout_state = 'dispatching'
    money.state.dispatch_started_at = await db.scalar(text('select clock_timestamp()'))
    money.state.revision += 1
    await audit_money_refusal(db,money,['dispatching', 'confirmation:'+str(result['confirmation_event_id']),
                                     'confirmed_at:'+str(result['confirmation_created_at'])])
    await db.commit()
    try:
        transfer = await run_stripe(stripe.Transfer.create,**request)
    except Exception as exc:
        await db.rollback()
        money = await lock_order_money(db,order_id)
        if money.state.dispatch_token == token and money.state.payout_state == 'dispatching':
            if isinstance(exc,stripe.error.InvalidRequestError):
                money.state.payout_state = 'rejected'
                money.state.reconciliation_reason = 'provider_rejected_request'
            else:
                money.state.payout_state = 'unknown'
            await db.commit()
        raise
    return await finalize_order_transfer(db,order_id,token,transfer)


async def recover_order_payout(db, order_id):
    """Read-only provider recovery. Zero matches never authorizes a new create."""
    import stripe
    from app.core.stripe_async import run_stripe
    money = await lock_order_money(db,order_id)
    if not money.state.dispatch_token:
        raise OrderMoneyConflict('No dispatched payout to recover')
    request = validate_payout_request(money)
    token, known = money.state.dispatch_token, money.state.stripe_transfer_id
    await db.rollback()
    if known:
        rows = [await run_stripe(stripe.Transfer.retrieve,known)]
    else:
        rows, seen, cursor = [], set(), None
        while True:
            params = dict(transfer_group=request['transfer_group'],destination=request['destination'],limit=100)
            if cursor:
                params['starting_after'] = cursor
            page = await run_stripe(stripe.Transfer.list,**params)
            data = page.get('data')
            if not isinstance(data,list) or type(page.get('has_more')) is not bool:
                raise OrderMoneyConflict('Malformed Transfer pagination')
            for row in data:
                rid = row.get('id')
                if not isinstance(rid,str) or rid in seen:
                    raise OrderMoneyConflict('Repeated Transfer pagination identity')
                seen.add(rid)
                rows.append(row)
            if not page['has_more']:
                break
            if not data:
                raise OrderMoneyConflict('Truncated Transfer pagination')
            cursor = data[-1]['id']
    if len(rows) == 1:
        money = await lock_order_money(db,order_id)
        try:
            validate_transfer(money,rows[0])
        except OrderMoneyConflict:
            money.state.payout_state='reconciliation_required'
            money.state.reconciliation_reason='contradictory_provider_transfer'
            await audit_money_refusal(db,money,[money.state.reconciliation_reason])
            await db.commit()
            return {'status':'reconciliation_required','reason':'contradictory_provider_transfer'}
        await db.rollback()
        return await finalize_order_transfer(db,order_id,token,rows[0])
    money = await lock_order_money(db,order_id)
    if money.state.dispatch_token != token:
        raise OrderMoneyConflict('Recovery ownership changed')
    money.state.payout_state = 'unknown' if not rows and not money.state.reconciliation_reason else 'reconciliation_required'
    if rows:
        money.state.reconciliation_reason = 'multiple_provider_transfers'
        money.state.payout_state = 'reconciliation_required'
    await audit_money_refusal(db,money,['recovery_zero_matches' if not rows else 'multiple_provider_transfers'])
    result = {'status':money.state.payout_state,'matches':len(rows),'order_id':str(order_id)}
    await db.commit()
    return result
