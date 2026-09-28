# T-891 production evidence (read-only), 2026-09-28T21:01:14Z
Method: DSN from /Users/max/Projects/ai-market/scripts/test-db-dsn.sh (Koskadeux helper, outside the backend repo; see runbooks/data-delivery-p2p.md §3), psql -X with 'set default_transaction_read_only=on'. Railway: `railway variables -e production -s ai-market-backend --json`.

```sql
select version_num from alembic_version
```
```
s1757_users_auth_generation
```

```sql
select column_name, data_type from information_schema.columns where table_schema='public' and table_name='transactions' order by 1
```
```
accepted_at | timestamp with time zone
amount_cents | integer
api_key_id | uuid
buyer_id | uuid
buyer_type | character varying
created_at | timestamp with time zone
currency | character varying
data_request_id | uuid
delivered_at | timestamp with time zone
id | uuid
idempotency_key | character varying
listing_id | uuid
metadata | jsonb
order_id | uuid
origin | character varying
paid_at | timestamp with time zone
party_id | uuid
payment_method | character varying
platform_fee_cents | integer
quoted_at | timestamp with time zone
seller_amount_cents | integer
seller_id | uuid
settled_at | timestamp with time zone
status | character varying
stripe_payment_intent_id | character varying
surface | character varying
tx_number | character varying
updated_at | timestamp with time zone
```

```sql
select indexname from pg_indexes where tablename='transactions' order by 1
```
```
ix_transactions_api_key_id
ix_transactions_buyer_id
ix_transactions_idempotency_key
ix_transactions_order_id
ix_transactions_party_id
ix_transactions_seller_id
ix_transactions_status
ix_transactions_tx_number
transactions_pkey
uq_s1714_transaction_payment_intent
```

```sql
select conname from pg_constraint where conrelid='public.transactions'::regclass order by 1
```
```
chk_transaction_buyer_type
chk_transaction_origin
chk_transaction_status
transactions_api_key_id_fkey
transactions_buyer_id_fkey
transactions_data_request_id_fkey
transactions_listing_id_fkey
transactions_order_id_fkey
transactions_party_id_fkey
transactions_pkey
transactions_seller_id_fkey
uq_s1714_transaction_payment_intent
```

```sql
select tgname from pg_trigger where tgrelid in ('public.orders'::regclass,'public.transactions'::regclass) and not tgisinternal order by 1
```
```
trg_orders_gateway_receipts_insert
trg_orders_gateway_receipts_update
trg_sync_order_to_transaction
trigger_orders_updated_at
trigger_set_order_number
```

```sql
select left(t.id::text,8) tx, t.status, t.amount_cents, t.seller_amount_cents, coalesce(t.metadata->>'e2e_synthetic','-') synthetic, left(coalesce(t.stripe_payment_intent_id,''),8) pi, o.status order_status, coalesce(m.payout_state,'-') payout_state, coalesce(m.refund_applied_cents,0) refunded from transactions t left join orders o on o.id=t.order_id left join order_money_states m on m.order_id=t.order_id where t.status in ('paid','delivered','confirmed','settled','completed') order by t.created_at
```
```
733ded10 | confirmed | 2500 | 2375 | - | pi_3UE9Y | completed | idle | 0
ed6074fd | confirmed | 2500 | 2375 | - | pi_3UEA0 | completed | idle | 0
08210f7f | delivered | 2500 | 2375 | true | pi_e2e_m | delivered | - | 0
e01c0f58 | delivered | 2500 | 2375 | true | pi_e2e_m | delivered | - | 0
09c3e07d | delivered | 2500 | 2375 | true | pi_e2e_m | delivered | idle | 0
bf008f36 | delivered | 2500 | 2375 | true | pi_e2e_m | delivered | idle | 0
26f9cf07 | delivered | 2500 | 2375 | - | pi_3UKk4 | delivered | idle | 0
```

```sql
select count(*) as tx_with_failures from transactions where coalesce((metadata->>'settlement_failures')::int,0) > 0
```
```
0
```

```sql
select count(*) as direct_payout_candidates_now_or_future from orders o where o.transaction_id is null and o.status in ('paid','delivered','completed','confirmed') and o.stripe_payment_intent_id like 'pi_%' and o.stripe_payment_intent_id not like 'pi_e2e%'
```
```
0
```

```sql
select left(o.id::text,8), o.status, o.amount_cents, o.auto_confirm_at from orders o where o.transaction_id is null and o.status in ('paid','delivered','completed','confirmed') and o.stripe_payment_intent_id like 'pi_%' and o.stripe_payment_intent_id not like 'pi_e2e%' order by o.created_at
```
```
```

```sql
select event_type, status, left(coalesce(error_message,''),100) from stripe_events where stripe_event_id='evt_3UKk4uRucxd97j0A1YRYrpK7'
```
```
payment_intent.succeeded | failed | (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedColumn
```

Railway prod flag:
ORDER_PAYOUT_DISPATCH_ENABLED = false
