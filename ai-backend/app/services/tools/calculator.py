"""آلة حاسبة آمنة تعتمد على AST ولا تستخدم eval()."""
from __future__ import annotations

import ast
import math
import operator
from numbers import Real

MAX_EXPRESSION_LENGTH = 120
MAX_ABS_VALUE = 1e100
MAX_POWER_EXPONENT = 100


class CalculatorError(ValueError):
    """خطأ في صيغة أو تنفيذ العملية الحسابية."""


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def extract_calculator_expression(message: str) -> str | None:
    """يرجع التعبير إذا كانت الرسالة أمر آلة حاسبة، وإلا None."""
    text = message.strip()
    prefixes = ("/calc", "/calculate")
    for prefix in prefixes:
        if text == prefix:
            return ""
        if text.startswith(prefix + " "):
            return text[len(prefix) + 1 :].strip()
    return None


def _validate_number(value: Real) -> float | int:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise CalculatorError("استخدم أرقامًا وعمليات حسابية فقط.")
    numeric = float(value)
    if not math.isfinite(numeric) or abs(numeric) > MAX_ABS_VALUE:
        raise CalculatorError("النتيجة كبيرة جدًا أو غير صالحة.")
    return value


def _eval(node: ast.AST) -> float | int:
    if isinstance(node, ast.Expression):
        return _eval(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise CalculatorError("استخدم أرقامًا وعمليات حسابية فقط.")
        return _validate_number(node.value)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _validate_number(_UNARY_OPERATORS[type(node.op)](_eval(node.operand)))

    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _eval(node.left)
        right = _eval(node.right)

        if isinstance(node.op, ast.Pow):
            if not isinstance(right, (int, float)) or abs(float(right)) > MAX_POWER_EXPONENT:
                raise CalculatorError("الأسّ كبير جدًا.")
        try:
            result = _BINARY_OPERATORS[type(node.op)](left, right)
        except ZeroDivisionError as exc:
            raise CalculatorError("لا يمكن القسمة على صفر.") from exc
        except (OverflowError, ValueError) as exc:
            raise CalculatorError("تعذر تنفيذ العملية الحسابية.") from exc

        return _validate_number(result)

    raise CalculatorError("المسموح أرقام و + - * / // % ** والأقواس فقط.")


def calculate_expression(expression: str) -> str:
    """يحسب التعبير الحسابي الآمن ويرجع نتيجة جاهزة للعرض."""
    expression = expression.strip()
    if not expression:
        raise CalculatorError("اكتب تعبيرًا بعد /calc، مثل: /calc (12 + 8) * 3")

    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise CalculatorError("التعبير طويل جدًا.")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise CalculatorError("صيغة الحساب غير صحيحة.") from exc

    result = _eval(tree)
    if isinstance(result, float) and result.is_integer():
        return str(int(result))
    return str(result)
