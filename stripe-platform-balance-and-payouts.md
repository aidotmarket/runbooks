---
title: Stripe platform balance and payouts
owner: vulcan
last_verified: '2026-09-29'
aliases:
  - Stripe platform balance
  - platform payout schedule
  - Stripe top-up
  - add funds to Stripe
  - insufficient available funds
error_signatures:
  - insufficient available funds
---

# Stripe platform balance and payouts

Read the production Stripe platform balance, manage its payout schedule, and guide a human operator through adding funds when seller Transfers lack available funds. These procedures were verified on 2026-09-29 for T-2026-000891.

## Read balance and schedule

Run this read-only, headless command from the backend checkout. It uses the Railway production service's Stripe key without printing it:

```sh
cd /Users/max/Projects/ai-market/ai-market-backend
railway run -e production --service ai-market-backend -- .venv/bin/python - <<'EOF'
import os, stripe
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]   # never print it
b = stripe.Balance.retrieve(); print(b.available, b.pending)
for t in stripe.BalanceTransaction.list(limit=15).data: print(t.created, t.type, t.amount, t.net, t.status, t.available_on)
print(stripe.Account.retrieve().settings.payouts.schedule)
EOF
```

Use attribute access for Stripe objects, for example `t.description`. In this SDK version, `StripeObject` has no `.get()`; calling it raises `AttributeError: get`.

## Platform payout schedule

The platform's own payout schedule is Dashboard-only; the Stripe API refuses changes to it. Go to **Stripe Dashboard → Settings → Linked accounts and payouts → Settlement and transfer rules → Payout schedule**. The entry URL is <https://dashboard.stripe.com/settings/payouts>, which redirects to `/settings/settlement`.

At Max's explicit request, the schedule was changed to **Manual** on 2026-09-29 at about 15:50Z. The API readback was `interval=manual, delay_days=2`. Keep it Manual: an automatic weekly Monday sweep emptied the available balance with the 2026-09-14 $47.94 payout, and seller Transfers then failed with `insufficient available funds` (T-2026-000891). The minimum-balance option requires automatic payouts and is unavailable under Manual. An agent may change this account setting only on Max's explicit request in chat.

## Add funds to the payments balance

Only a human operator may initiate a top-up; agents must not move money. A platform Stripe admin with 2FA goes to **Dashboard → Balance → Add to balance → Payments balance**, enters the amount, and selects a verified bank account. Funding is from a bank account, not a card. First use of an unverified bank account requires microdeposit verification, usually 1–2 business days.

For USD in the US, Stripe estimates ACH debit at about 5 days, ACH credit at 1–3 days, and wire at 1–5 days. On 2026-09-29 the Dashboard said top-up funds would be available after 5 business days. A top-up does not automatically retry failed Transfers; re-run them after funds become available. Under a Manual schedule, proceeds from later sales remain in the balance and can fund a re-run without a top-up. See [Stripe's top-up guide](https://docs.stripe.com/connect/top-ups).

## When it breaks

- `insufficient available funds`: read the available balance and payout schedule above. After available funds arrive, re-run the failed Transfer; a top-up alone will not retry it.
- `AttributeError: get`: use Stripe object attributes, not `.get()`.
- `Failed to fetch ... backboard.railway.com/graphql/v2 ... operation timed out`: retry the Railway command once. This timeout alone does not establish a database or Stripe outage.

For application settlement recovery, see [ai-market-backend: Model-table drift and money-path recovery](ai-market-backend.md#model-table-drift-and-money-path-recovery). For test mode, see [Money Path Test Environment](money-path-test-environment.md).
