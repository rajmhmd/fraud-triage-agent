"""v1 tools — what the agent could already do before the challenge.

The agent can look up a card and its recent transactions and reason about
amount, MCC and channel. It has NO way to reason about geography: it sees
"Dubai" and "London" as strings, so it cannot tell whether two card-present
transactions are physically possible for one cardholder.
"""
import json
from functools import lru_cache

from strands import tool

from . import config


@lru_cache(maxsize=1)
def _store() -> dict:
    with open(config.TRANSACTIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


@tool
def get_card_profile(card_id: str) -> dict:
    """Get the profile of a card: masked PAN, home city and any travel notice.

    Args:
        card_id: Internal card reference, e.g. "CARD-001". Never a full PAN.
    """
    card = _store()["cards"].get(card_id)
    if card is None:
        return {"status": "error", "content": [{"text": f"Unknown card_id {card_id}"}]}
    return {"status": "success", "content": [{"json": {"card_id": card_id, **card}}]}


@tool
def get_recent_transactions(card_id: str, limit: int = 10) -> dict:
    """List a card's most recent transactions, newest last.

    Each transaction has txn_id, timestamp_utc, amount, currency, merchant,
    mcc, channel (POS_CHIP, POS_CONTACTLESS, ECOM) and merchant_location.

    Args:
        card_id: Internal card reference, e.g. "CARD-001".
        limit: Maximum number of transactions to return (default 10).
    """
    txns = [t for t in _store()["transactions"] if t["card_id"] == card_id]
    txns.sort(key=lambda t: t["timestamp_utc"])
    return {"status": "success", "content": [{"json": {"transactions": txns[-limit:]}}]}


BASE_TOOLS = [get_card_profile, get_recent_transactions]
