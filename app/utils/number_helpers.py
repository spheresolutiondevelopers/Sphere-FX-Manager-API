"""Numeric utilities for financial calculations."""

from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Union, Optional
import math

# Set Decimal precision high enough for financial calculations
getcontext().prec = 28


def decimal_from_float(value: float) -> Decimal:
    """Convert a float to Decimal safely."""
    return Decimal(str(value))


def decimal_round(value: Union[Decimal, float], places: int = 2) -> Decimal:
    """Round a Decimal to a specified number of decimal places."""
    if isinstance(value, float):
        value = Decimal(str(value))
    rounding = Decimal('0.1') ** places
    return value.quantize(rounding, rounding=ROUND_HALF_UP)


def pip_value(symbol: str, lot_size: Decimal, pip_multiplier: Decimal = Decimal('0.0001')) -> Decimal:
    """
    Calculate the pip value for a given symbol and lot size.
    Assumes pip multiplier is 0.0001 for most forex pairs.
    For JPY pairs, multiplier is 0.01.
    """
    # For simplicity, we just apply the multiplier
    return lot_size * pip_multiplier


def compute_rr(entry: Decimal, exit_price: Decimal, stop_loss: Decimal) -> Decimal:
    """
    Compute risk-reward ratio.
    Formula: |exit - entry| / |stop_loss - entry|
    """
    if stop_loss == entry:
        return Decimal('0')
    risk = abs(stop_loss - entry)
    reward = abs(exit_price - entry)
    if risk == 0:
        return Decimal('0')
    return reward / risk


def normalize_lot(lot: Decimal, min_lot: Decimal, max_lot: Decimal, step: Decimal = Decimal('0.01')) -> Decimal:
    """
    Normalize lot size to be within min/max and rounded to step.
    """
    if lot < min_lot:
        lot = min_lot
    if lot > max_lot:
        lot = max_lot
    # Round to step
    return decimal_round(lot / step) * step


def compute_pnl(
    action: str,  # BUY or SELL
    entry: Decimal,
    exit_price: Decimal,
    lot_size: Decimal,
    pip_multiplier: Decimal = Decimal('0.0001'),
) -> Decimal:
    """
    Compute profit/loss for a trade.
    """
    if action.upper() == "BUY":
        diff = exit_price - entry
    else:  # SELL
        diff = entry - exit_price
    return diff * lot_size / pip_multiplier


def format_currency(value: Decimal, currency: str = "USD") -> str:
    """Format a Decimal as a currency string."""
    prefix = "$" if currency == "USD" else "€" if currency == "EUR" else "£" if currency == "GBP" else currency
    sign = "-" if value < 0 else ""
    return f"{sign}{prefix}{abs(value):,.2f}"


def format_pips(value: Decimal) -> str:
    """Format a value as pips (positive or negative with sign)."""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}p"


def percent_change(old: Decimal, new: Decimal) -> Decimal:
    """Compute percentage change from old to new."""
    if old == 0:
        return Decimal('0')
    return ((new - old) / old) * 100