"""Local economic reservation ledger; trusted caller/storage, not a payment gateway."""
from contextlib import closing, contextmanager
import re
import sqlite3

MAX_AMOUNT = 10**15
TOKEN = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class BudgetError(ValueError):
    """Invalid request, conflict or insufficient budget."""


def _amount(value, minimum=0):
    if type(value) is not int or not minimum <= value <= MAX_AMOUNT:
        raise BudgetError("invalid integer minor-unit amount")


def _identifier(value):
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise BudgetError("invalid identifier")


def _digest(value):
    if not isinstance(value, str) or not DIGEST.fullmatch(value):
        raise BudgetError("expected lowercase SHA-256 reference")


class EconomicLedger:
    """One immutable currency/cap per dedicated DB; never dispatches external work."""

    def __init__(self, path, *, currency, limit):
        if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
            raise BudgetError("invalid currency code format")
        _amount(limit, 1)
        self.path = str(path)
        if self.path == ':memory:' or not self.path:
            raise BudgetError("persistent database path required")
        self.currency, self.limit = currency, limit
        with self._transaction() as con:
            con.execute("CREATE TABLE IF NOT EXISTS economic_config (id INTEGER PRIMARY KEY CHECK(id=1), currency TEXT NOT NULL, cap INTEGER NOT NULL)")
            con.execute("CREATE TABLE IF NOT EXISTS economic_reservations (request_id TEXT PRIMARY KEY, intent TEXT NOT NULL, reserved INTEGER NOT NULL CHECK(reserved>0), state TEXT NOT NULL CHECK(state IN ('RESERVED','SETTLED','RELEASED')), actual INTEGER NOT NULL CHECK(actual>=0 AND actual<=reserved), evidence TEXT)")
            con.execute("INSERT OR IGNORE INTO economic_config VALUES (1,?,?)", (currency, limit))
            self._check_config(con)

    @contextmanager
    def _transaction(self):
        with closing(sqlite3.connect(self.path, timeout=10, isolation_level=None)) as con:
            con.execute("BEGIN IMMEDIATE")
            try:
                yield con
                con.commit()
            except BaseException:
                con.rollback()
                raise

    def _check_config(self, con):
        if con.execute("SELECT currency,cap FROM economic_config WHERE id=1").fetchone() != (self.currency, self.limit):
            raise BudgetError("budget configuration mismatch")

    def _totals(self, con):
        self._check_config(con)
        reserved, spent = con.execute("SELECT COALESCE(SUM(CASE WHEN state='RESERVED' THEN reserved ELSE 0 END),0),COALESCE(SUM(CASE WHEN state='SETTLED' THEN actual ELSE 0 END),0) FROM economic_reservations").fetchone()
        if reserved < 0 or spent < 0 or reserved + spent > self.limit:
            raise BudgetError("ledger invariant violated")
        return reserved, spent

    def snapshot(self):
        with self._transaction() as con:
            reserved, spent = self._totals(con)
            return dict(currency=self.currency, limit=self.limit, reserved=reserved, spent=spent, available=self.limit-reserved-spent)

    def reserve(self, request_id, intent_sha256, amount):
        """CREATED is a reservation, not an execution permit; REPLAY never dispatches."""
        _identifier(request_id)
        _digest(intent_sha256)
        _amount(amount, 1)
        with self._transaction() as con:
            reserved, spent = self._totals(con)
            row = con.execute("SELECT intent,reserved,state FROM economic_reservations WHERE request_id=?", (request_id,)).fetchone()
            if row is not None:
                if row[:2] != (intent_sha256, amount):
                    raise BudgetError("request identity conflict")
                return "REPLAY:" + row[2]
            if amount > self.limit-reserved-spent:
                raise BudgetError("insufficient budget")
            con.execute("INSERT INTO economic_reservations VALUES (?,?,?,'RESERVED',0,NULL)", (request_id, intent_sha256, amount))
            return "CREATED"

    def settle(self, request_id, actual, evidence_sha256):
        """Caller attests known final cost; digest is only a reference, not verified proof."""
        return self._finish(request_id, "SETTLED", actual, evidence_sha256)

    def release(self, request_id, evidence_sha256):
        """Caller attests known zero effect/cost; never release an ambiguous outcome."""
        return self._finish(request_id, "RELEASED", 0, evidence_sha256)

    def _finish(self, request_id, state, actual, evidence):
        _identifier(request_id)
        _amount(actual)
        _digest(evidence)
        with self._transaction() as con:
            self._totals(con)
            row = con.execute("SELECT reserved,state,actual,evidence FROM economic_reservations WHERE request_id=?", (request_id,)).fetchone()
            if row is None:
                raise BudgetError("unknown request")
            if row[1] != "RESERVED":
                if row[1:] == (state, actual, evidence):
                    return "REPLAY:" + state
                raise BudgetError("terminal state conflict")
            if actual > row[0]:
                raise BudgetError("actual exceeds reservation; retain hold for manual reconciliation")
            con.execute("UPDATE economic_reservations SET state=?,actual=?,evidence=? WHERE request_id=?", (state, actual, evidence, request_id))
            self._totals(con)
            return state
