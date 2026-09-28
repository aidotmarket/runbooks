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

## r4 additions (GLM r3 findings), 2026-09-28T21:19:38Z

```sql
select o.id, o.status, o.transaction_id is null as direct_path, o.stripe_payment_intent_id like 'pi\_e2e%' as mock_pi, (bu.is_test or su.is_test) as test_actor, o.created_at, o.auto_confirm_at from orders o join users bu on bu.id=o.buyer_id join users su on su.id=o.seller_id where o.transaction_id is null and o.stripe_payment_intent_id like 'pi\_%' order by o.created_at
```
```
```

```sql
select t.id tx_id, t.order_id, t.status, t.created_at, o.confirmed_at, o.auto_confirm_at, t.amount_cents, t.seller_amount_cents, (t.buyer_id=bu.id) and bu.email='max@ai.market' buyer_is_max_ai_market, su.email='max@kisa.cat' seller_is_max_kisa, (bu.is_test or su.is_test) test_actor from transactions t join orders o on o.id=t.order_id join users bu on bu.id=t.buyer_id join users su on su.id=t.seller_id where t.status in ('paid','delivered','confirmed','settled','completed') and not coalesce(t.metadata,'{}'::jsonb) @> '{"e2e_synthetic": true}'::jsonb order by t.created_at
```
```
733ded10-00ca-4619-8a51-716fc2df89c4 | 7489fdd2-012b-4a05-80a9-e4a5577342fa | confirmed | 2026-09-10 15:05:38.44532+00 | 2026-09-17 16:10:00.0197+00 | 2026-09-17 15:30:26.979746+00 | 2500 | 2375 | t | t | f
ed6074fd-617f-45a7-84ea-a20301a026be | c91951ed-d22d-4407-b7ec-23873688520a | confirmed | 2026-09-10 15:34:33.792044+00 | 2026-09-17 16:10:00.080739+00 | 2026-09-17 15:35:00.678947+00 | 2500 | 2375 | t | t | f
26f9cf07-87d2-4e09-8590-3d1786d30d66 | 60a8e739-1754-467d-91f6-703037894895 | delivered | 2026-09-28 19:18:14.757051+00 |  | 2026-10-05 19:19:13.306619+00 | 2500 | 2375 | t | t | f
```

```sql
select r.order_id, r.status, r.amount_cents from refunds r join transactions t on t.order_id=r.order_id where t.status in ('paid','delivered','confirmed','settled','completed')
```
```
```

```sql
select o.id, o.disputed_at, o.dispute_resolved_at from orders o join transactions t on t.order_id=o.id where t.status in ('paid','delivered','confirmed','settled','completed') and o.disputed_at is not null
```
```
e12c2434-6fae-4f02-9ca7-5fbc7b59022e | 2026-09-26 23:41:13.476297+00 | 2026-09-26 23:41:58.937272+00
a56de7b1-9660-4586-9b33-17d1858c85aa | 2026-09-26 23:36:24.786631+00 | 2026-09-26 23:36:46.547907+00
```

```sql
select stripe_event_id, event_type, status, processed_at from stripe_events where payload_json::text like '%pi_3UKk4uRucxd97j0A1o8h1ysM%' or payload_json::text like '%pi_3UE9Y%' or payload_json::text like '%pi_3UEA0%' order by processed_at
```
```
evt_1UKk4yRucxd97j0ApCBfmqRY | checkout.session.completed | completed | 2026-09-28 19:19:13.197988+00
evt_3UKk4uRucxd97j0A1YRYrpK7 | payment_intent.succeeded | failed | 2026-09-28 20:18:42.723211+00
```

Stripe replay procedure (operator, after the column repair deploys): the live endpoint retries failed events automatically for up to 3 days (evt_3UKk4uRucxd97j0A1YRYrpK7 created 2026-09-28 19:19Z, so automatic retries run until about 2026-10-01 19:19Z). If the window lapses: POST https://api.stripe.com/v1/events/evt_3UKk4uRucxd97j0A1YRYrpK7/retry with webhook_endpoint=<prod endpoint id> using the live secret key from Infisical prod (human-approved, same shape as s1656/s1761-refund-ops.py retry-capture). Acceptance: the stripe_events row status=completed, and payments has a succeeded row for the PI.

## r5 addition (CC F1: other 20260318_001 artifacts), 2026-09-28T22:25:04Z

```sql
select to_regclass('public.delivery_audit_log')
```
```
delivery_audit_log
```

```sql
select column_name||':'||data_type from information_schema.columns where table_schema='public' and table_name='delivery_audit_log' order by ordinal_position
```
```
id:uuid
transaction_id:uuid
order_id:uuid
event_type:character varying
actor_type:character varying
actor_id:uuid
attempt_no:integer
jwt_jti:character varying
trust_session_id:uuid
trust_device_id:uuid
correlation_id:uuid
http_status_code:integer
range_start:bigint
range_end:bigint
bytes_count:bigint
is_terminal:boolean
payload:jsonb
created_at:timestamp with time zone
```

```sql
select indexname from pg_indexes where tablename='delivery_audit_log' order by 1
```
```
delivery_audit_log_pkey
ix_delivery_audit_log_event_type
ix_delivery_audit_log_transaction_created
```

```sql
select conname, contype from pg_constraint where conrelid='public.delivery_audit_log'::regclass order by 1
```
```
delivery_audit_log_pkey | p
```

Conclusion: delivery_audit_log exists in prod with the migration's columns and both indexes; outcome A (the 11 transactions columns plus their checks and indexes) is sufficient for the create_delivery_record path.
