import re
import math
from decimal import Decimal, InvalidOperation, ROUND_UP, ROUND_DOWN, ROUND_HALF_UP
from typing import Optional, Tuple

from lvgenerator.models.global_constants import global_constants


def _aufrunden(value: float, decimals: int = 0) -> float:
    """Excel-like ROUNDUP: rounds away from zero."""
    factor = 10 ** decimals
    if value >= 0:
        return math.ceil(value * factor) / factor
    else:
        return math.floor(value * factor) / factor


def _abrunden(value: float, decimals: int = 0) -> float:
    """Excel-like ROUNDDOWN: rounds toward zero."""
    factor = 10 ** decimals
    if value >= 0:
        return math.floor(value * factor) / factor
    else:
        return math.ceil(value * factor) / factor


def _runden(value: float, decimals: int = 0) -> float:
    """German alias for round (kaufmaennisches Runden)."""
    return round(value, decimals)


def evaluate_formula(formula: str) -> Tuple[Optional[Decimal], Optional[str]]:
    """
    Evaluate a mathematical formula with support for global constants and functions.

    Returns:
        Tuple of (result, error_message).
        On success: (Decimal, None)
        On failure: (None, error_string)

    Supported:
    - Basic arithmetic: +, -, *, /, **, ()
    - Functions: ROUND/RUNDEN, AUFRUNDEN, ABRUNDEN, CEIL, FLOOR,
                 ABS, SQRT, SIN, COS, TAN, LOG, LOG10, MIN, MAX
    - Constants: PI, E, and user-defined global constants
    """
    if not formula.strip():
        return None, None

    try:
        # Replace constants (case-insensitive)
        expr = formula.upper()
        for name, (value, _desc) in global_constants.get_all_constants().items():
            expr = re.sub(r'\b' + re.escape(name) + r'\b', str(value), expr)

        # Replace function names with Python equivalents
        function_mappings = {
            'AUFRUNDEN': '_aufrunden',
            'ABRUNDEN': '_abrunden',
            'RUNDEN': '_runden',
            'ROUND': '_runden',
            'CEIL': 'math.ceil',
            'FLOOR': 'math.floor',
            'ABS': 'abs',
            'SQRT': 'math.sqrt',
            'SIN': 'math.sin',
            'COS': 'math.cos',
            'TAN': 'math.tan',
            'LOG': 'math.log',
            'LOG10': 'math.log10',
            'MIN': 'min',
            'MAX': 'max',
        }

        for func, replacement in function_mappings.items():
            expr = re.sub(r'\b' + re.escape(func) + r'\(', replacement + '(', expr)

        # Restricted evaluation environment
        allowed_names = {
            "math": math,
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "_aufrunden": _aufrunden,
            "_abrunden": _abrunden,
            "_runden": _runden,
        }

        result = eval(expr, {"__builtins__": {}}, allowed_names)

        if isinstance(result, (int, float)):
            return Decimal(str(result)), None
        elif isinstance(result, Decimal):
            return result, None
        else:
            return None, "Ergebnis ist keine Zahl"

    except SyntaxError:
        return None, "Syntaxfehler in der Formel"
    except NameError as e:
        name = str(e).split("'")[1] if "'" in str(e) else str(e)
        return None, f"Unbekannter Name: {name}"
    except ZeroDivisionError:
        return None, "Division durch Null"
    except TypeError as e:
        return None, f"Typfehler: {e}"
    except (InvalidOperation, ValueError, OverflowError):
        return None, "Ungültiger Zahlenwert"
    except Exception:
        return None, "Fehler bei der Auswertung"
