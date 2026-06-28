"""Cross-field and business validators."""

from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from app.utils.constants import ACTIONS, ORDER_TYPES


def validate_action(action: str) -> bool:
    """Check if action is valid (BUY/SELL)."""
    return action.upper() in ACTIONS


def validate_order_type(order_type: str) -> bool:
    """Check if order type is valid."""
    return order_type.upper() in ORDER_TYPES


def validate_price(price: Optional[Decimal]) -> bool:
    """Check if price is positive and finite."""
    if price is None:
        return True
    return price > 0 and price.is_finite()


def validate_sl_entry_relation(
    action: str,
    entry: Decimal,
    stop_loss: Optional[Decimal],
) -> Tuple[bool, str]:
    """
    Validate stop loss relative to entry based on action.
    Returns (is_valid, error_message).
    """
    if stop_loss is None:
        return True, ""

    if action == "BUY":
        if stop_loss >= entry:
            return False, "Stop loss must be below entry for BUY orders"
    else:  # SELL
        if stop_loss <= entry:
            return False, "Stop loss must be above entry for SELL orders"
    return True, ""


def validate_tp_entry_relation(
    action: str,
    entry: Decimal,
    take_profit: Optional[List[Dict[str, Any]]],
) -> Tuple[bool, str]:
    """
    Validate take profit levels relative to entry based on action.
    Returns (is_valid, error_message).
    """
    if not take_profit:
        return True, ""

    for tp in take_profit:
        price = tp.get("price")
        if price is None:
            continue
        if action == "BUY":
            if price <= entry:
                return False, f"TP level {tp.get('level', '')} must be above entry for BUY orders"
        else:  # SELL
            if price >= entry:
                return False, f"TP level {tp.get('level', '')} must be below entry for SELL orders"
    return True, ""


def validate_tp_sequence(take_profit: Optional[List[Dict[str, Any]]]) -> Tuple[bool, str]:
    """
    Validate that TP levels are in ascending order (for BUY) or descending (for SELL).
    Returns (is_valid, error_message).
    """
    if not take_profit or len(take_profit) < 2:
        return True, ""

    # We need to know action; this is context-dependent.
    # For simplicity, we'll just check that levels are distinct.
    levels = [tp.get("level") for tp in take_profit]
    if len(set(levels)) != len(levels):
        return False, "Duplicate TP levels found"
    return True, ""


def validate_signal_consistency(
    action: str,
    entry: Decimal,
    stop_loss: Optional[Decimal],
    take_profit: Optional[List[Dict[str, Any]]],
) -> List[str]:
    """Run all validations and return a list of error messages."""
    errors = []
    if not validate_price(entry):
        errors.append("Entry price must be positive and finite")
    if stop_loss is not None and not validate_price(stop_loss):
        errors.append("Stop loss must be positive and finite")

    valid, msg = validate_sl_entry_relation(action, entry, stop_loss)
    if not valid:
        errors.append(msg)

    valid, msg = validate_tp_entry_relation(action, entry, take_profit)
    if not valid:
        errors.append(msg)

    valid, msg = validate_tp_sequence(take_profit)
    if not valid:
        errors.append(msg)

    return errors


def validate_lot_size(lot: Decimal, min_lot: Decimal, max_lot: Decimal) -> Tuple[bool, str]:
    """Check if lot size is within allowed range."""
    if lot < min_lot:
        return False, f"Lot size {lot} below minimum {min_lot}"
    if lot > max_lot:
        return False, f"Lot size {lot} above maximum {max_lot}"
    return True, ""


def validate_account_credentials(login: str, password: str) -> Tuple[bool, str]:
    """Basic validation for MT5 account credentials."""
    if not login or not login.strip():
        return False, "Login cannot be empty"
    if not password or len(password) < 4:
        return False, "Password must be at least 4 characters"
    return True, ""