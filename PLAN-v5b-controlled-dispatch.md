# PLAN: V-5b, one controlled live dispatch (S1511 step 11)

Proposal for Max. Nothing here has been run. Written S1636 (mars).

## What this is

The CI-health channel is live in record-only mode. It watches GitHub, decides what it would do, and does nothing. Before we let it act on its own for one repository, the spec requires one controlled live run: one real issue, one real Claude Code triage, real caps, and a receipt that an independent reviewer accepts. The rule stays off the whole time.

## The target

The backend CI failure on main that the channel tracked from 27 to 29 August (411 occurrences, now resolved after the Stripe legacy removal landed and main went green). It is real, it is already closed, and the worker's authority is triage only, so it cannot change anything. It reads, it reasons, it reports one of three exits: triaged, resolved with evidence, or needs Max. If it says resolved with evidence, that matches what we already know, which is a clean check on its judgement.

## The cost

Hard cap 3.00 USD for the run, 8 turns, 10 minutes. These are the reviewed caps already in the deployed policy and the receipt R2 proved they reach the command line. Expected actual cost is well under 1 USD for a triage-only read. If the cap is hit the run fails closed and we still get a receipt, just a failed one.

## How it runs

1. Seed one queued intent for that issue in the production queue, with the exact six reviewed policy fields and the reservation held, the same seeding contract we used for the V-2b and V-3 receipts. The dispatch kill switch stays false and the rule stays dry-run. Nothing else can be admitted.
2. The Titan-1 poller leases it on its normal cadence and runs the real Option A worker.
3. Completion comes back to the same intent with the same nonce and a measured cost.
4. I close the intent, record the completion, and prove the kill switch and rule are still off.
5. Receipt goes to CC and GLM for independent acceptance. Kimi is not needed, this is not a code change.

## What can go wrong

The poller runs as a LaunchAgent and the only thing it can execute is what the queue hands it, so the blast radius is one Claude Code session with a 3 dollar cap. If the worker misbehaves, the breaker counts one failure and nothing else is queued. If the lease expires it goes to outcome unknown and holds its reservation, which is exactly what V-5a proved. Rollback is deleting one queue row.

## What I need from you

A yes on the target and the cost. Once you say go, this is about two hours of work including the review, and no rule is activated until you see the accepted receipt.
