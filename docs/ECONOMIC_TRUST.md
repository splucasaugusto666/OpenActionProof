# Economic Trust Infrastructure — experimental reservation ledger

The next product direction is autonomous operational and economic trust for AI agents: authorize an intent, reserve a budget, dispatch through a trusted adapter, independently verify the effect, reconcile cost and preserve evidence. Existing outcome verifiers remain intact. This branch implements the local reservation component and a trusted synchronous host adapter for budgeted execution, not the universal gateway.

## Run locally (no model API or third-party runtime dependency)

From a reviewed checkout, use Python 3.10+:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from openactionproof.economic import EconomicLedger, BudgetError

with TemporaryDirectory() as d:
    ledger = EconomicLedger(Path(d) / "budget.db", currency="BRL", limit=10000, initialize=True)
    intent = "a" * 64  # illustrative digest, not an actual intent
    evidence = "b" * 64  # illustrative reference, not authenticated evidence
    print(ledger.reserve("order-1", intent, 3000))
    print(ledger.reserve("order-1", intent, 3000))
    print(ledger.settle("order-1", 2500, evidence))
    print(ledger.snapshot())
```

Expected: CREATED, REPLAY:RESERVED, SETTLED, then spent=2500 and available=7500. All amounts are integer minor units (centavos for BRL); no floating-point accounting. Currency format is checked, not a full ISO 4217 registry.

## Contract and limitations

Use a dedicated persistent SQLite database controlled by a trusted host. Explicit initialize=True provisions a new file exclusively; reopening requires a valid existing schema version 1. Missing storage fails closed, never silently recreates the ledger. Earlier unversioned branch-only fixtures are not compatible; do not replace or restore active ledgers. Each operation uses BEGIN IMMEDIATE. The invariant is reserved + settled spend <= configured cap. The original request ID, amount and caller-provided intent digest are immutable per ID. Conflicting requests fail; terminal states cannot be reopened. An over-reservation cost report fails and retains its hold for manual reconciliation. Unknown outcomes must not be released, retried or settled automatically. CREATED reserves funds in a local accounting model; it does not authorize or dispatch a payment. REPLAY is historical information, never permission to dispatch again.

The caller is responsible for authenticating evidence, checking authorization, and binding the request to the actual adapter call. Digests are references, not proofs of receipt authenticity or settlement. There is no automatic hold expiry, bank connectivity, real-money custody, external billing cap, identity federation, isolation from direct database writers, distributed exactly-once guarantee, or production security boundary. The ledger cannot stop an external provider from charging more than the reserved amount. A separate trusted dispatcher and independently observed reconciliation are necessary.

## Verification

On Linux, Python 3.13.5, all 18 economic and gateway unittest cases passed twice (0.185 s and 0.218 s), with ResourceWarning treated as an error. Run `PYTHONPATH=src python -W error::ResourceWarning -m unittest discover -s tests -p 'test_economic*.py' -v`. No external funds or service calls were used. Full-suite CI on the earlier PR revision passed Python 3.10, 3.12 and 3.13 (run 45622863443); revised head requires its own CI.

## Next gates

1. Bind trusted dispatch to reservation and reconcile uncertainty with existing read-only observers; do not authorize external effects from the ledger alone.
2. Freeze held-out workload: concurrent processes, abrupt process termination, lock contention, inconsistent receipts, cost overshoot, and external side-effect recovery. Compare against a documented transactional baseline.
3. Add a constrained mock HTTP/SQLite adapter, observable policy decisions, explicit human approval for consequential operations and a local gateway demo.
4. Evaluate MCP and payment-provider adapters against documented APIs in test environments only; independently verify receipts and actual costs before any release claim.
5. Measure time-to-first-value, integration effort and actual adoption before commercial promises.

No TOP 1 claim, no verified market share, and no claim of invention of transactional reservations or idempotency.

## Budgeted host adapter

`EconomicIntent` binds a host-approved request ID, capability, payload digest, currency and maximum amount. `execute_budgeted` reserves before invoking a trusted synchronous callback, and only the first successful reservation may invoke it. A second callback supplies a separately observed final cost bound to the same intent and request. The actor's return value is ignored. Unknown, conflicting, malformed or excessive cost evidence leaves the hold pending reconciliation; no automatic retry or release. A cost record does not prove the intended effect occurred. Existing core outcome and dispatch verifiers are not automatically wired into this adapter yet. Host must enforce that callbacks actually correspond to the pinned intent and obtain independent trustworthy evidence; typed observation fields are not authenticated transport. An actor with direct access to the database or external billing system can bypass the ledger. New IDs are not semantic deduplication. Process death after admission may leave a permanent hold; reconcile only after confirming the actor is no longer in flight. Never retry using a fresh ID to circumvent uncertainty.

Local regression checks: eight concurrent identical requests produce one actor invocation and seven replay statuses; claimed cost is ignored in favor of the separate observer; actor exception can coexist with an observed cost; deleted storage prevents dispatch. No production or financial guarantee.
