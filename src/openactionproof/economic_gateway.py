"""Trusted synchronous host adapter for budget admission and observed cost.

No external payment capability, actor sandbox, or authenticated observer transport.
"""
from dataclasses import dataclass
import hashlib
import json
import sqlite3

from .economic import BudgetError, EconomicLedger, _amount, _digest, _identifier


@dataclass(frozen=True)
class EconomicIntent:
    request_id: str
    capability: str
    payload_sha256: str
    currency: str
    maximum: int

    def digest(self):
        _identifier(self.request_id)
        _identifier(self.capability)
        _digest(self.payload_sha256)
        _amount(self.maximum, 1)
        if type(self.currency) is not str or len(self.currency) != 3 or not self.currency.isascii() or not self.currency.isupper() or not self.currency.isalpha():
            raise BudgetError('invalid currency')
        fields = ['oap.economic-intent.v1', self.request_id, self.capability,
                  self.payload_sha256, self.currency, self.maximum]
        return hashlib.sha256(json.dumps(fields, separators=(',', ':'), ensure_ascii=True).encode('ascii')).hexdigest()


@dataclass(frozen=True)
class CostObservation:
    request_id: str
    intent_sha256: str
    currency: str
    actual: int
    evidence_sha256: str


@dataclass(frozen=True)
class GatewayResult:
    status: str
    actor_status: str = 'NOT_INVOKED'


def execute_budgeted(*, ledger: EconomicLedger, intent: EconomicIntent, execute, observe):
    """Host pins intent and selects trusted callbacks; only a new hold calls actor.

    An actor return is never used as cost evidence. Unknown, invalid or oversized
    observations retain the hold. No automatic retries or zero-effect releases.
    A settled cost is not proof of action success. Observer must establish final
    cost independently and bind it to this exact operation; this is a typed local
    interface, not authentication. Callbacks must complete synchronously.
    """
    if type(intent) is not EconomicIntent or not callable(execute) or not callable(observe):
        return GatewayResult('DENIED')
    try:
        digest = intent.digest()
        if intent.currency != ledger.currency:
            return GatewayResult('DENIED')
        admission = ledger.reserve(intent.request_id, digest, intent.maximum)
    except BudgetError:
        return GatewayResult('DENIED')
    except sqlite3.Error:
        return GatewayResult('STORAGE_UNAVAILABLE')
    if admission != 'CREATED':
        return GatewayResult(admission)
    try:
        execute(intent)
        actor_status = 'RETURNED'
    except Exception:
        actor_status = 'RAISED'
    try:
        evidence = observe(intent)
        if (type(evidence) is not CostObservation or evidence.request_id != intent.request_id
                or evidence.intent_sha256 != digest or evidence.currency != intent.currency):
            return GatewayResult('PENDING_RECONCILIATION', actor_status)
        ledger.settle(intent.request_id, evidence.actual, evidence.evidence_sha256)
    except Exception:
        return GatewayResult('PENDING_RECONCILIATION', actor_status)
    return GatewayResult('COST_RECORDED', actor_status)
