"""مفسّر بايثون محدود وآمن للاستخدام داخل أدوات المساعد.

لا يسمح باستيراد modules أو الوصول إلى الملفات/الشبكة أو تنفيذ eval/exec.
يعمل داخل عملية منفصلة مع مهلة وقيود موارد، ويدعم حسابات وتحويلات
برمجية بسيطة مناسبة للمساعد البرمجي.
"""
from __future__ import annotations

import ast
import base64
import math
import os
import platform
import resource
import statistics
import subprocess
import sys
import textwrap

MAX_CODE_LENGTH = 8_000
MAX_OUTPUT_CHARS = 12_000
MAX_EXECUTION_SECONDS = 2.0
MAX_MEMORY_BYTES = 256 * 1024 * 1024
MAX_FILE_BYTES = 1 * 1024 * 1024
MAX_OPEN_FILES = 16

_SAFE_FUNCTION_NAMES = {
    "abs", "all", "any", "bool", "dict", "enumerate", "float", "int",
    "len", "list", "max", "min", "print", "range", "round", "set",
    "sorted", "str", "sum", "tuple", "zip",
    "sqrt", "sin", "cos", "tan", "log", "exp", "floor", "ceil",
    "factorial", "comb", "perm", "mean", "median", "stdev",
}

_SAFE_GLOBALS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "exp": math.exp,
    "floor": math.floor,
    "ceil": math.ceil,
    "factorial": math.factorial,
    "comb": math.comb,
    "perm": math.perm,
    "mean": statistics.mean,
    "median": statistics.median,
    "stdev": statistics.stdev,
    "pi": math.pi,
    "e": math.e,
}

_ALLOWED_NODES = {
    ast.Module,
    ast.Expr,
    ast.Assign,
    ast.AnnAssign,
    ast.AugAssign,
    ast.If,
    ast.For,
    ast.While,
    ast.Break,
    ast.Continue,
    ast.Pass,
    ast.Constant,
    ast.Name,
    ast.Store,
    ast.Load,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.List,
    ast.Tuple,
    ast.Dict,
    ast.Set,
    ast.Subscript,
    ast.Slice,
    ast.Call,
    ast.keyword,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.UAdd,
    ast.USub,
    ast.Not,
    ast.And,
    ast.Or,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
}

_BLOCKED_NODE_NAMES = {
    "Import",
    "ImportFrom",
    "FunctionDef",
    "AsyncFunctionDef",
    "ClassDef",
    "Lambda",
    "With",
    "AsyncWith",
    "Try",
    "Raise",
    "Assert",
    "Delete",
    "Global",
    "Nonlocal",
    "Yield",
    "YieldFrom",
    "Await",
    "NamedExpr",
    "Match",
}

_BLOCKED_NAMES = {
    "__builtins__",
    "__import__",
    "eval",
    "exec",
    "compile",
    "open",
    "input",
    "breakpoint",
    "globals",
    "locals",
    "vars",
    "getattr",
    "setattr",
    "delattr",
}


class CodeExecutionError(ValueError):
    """خطأ آمن ومفهوم أثناء تنفيذ الكود."""


def extract_code_request(message: str) -> str | None:
    """يرجع كود بايثون إذا كانت الرسالة أمر /python أو /py."""
    text = message.strip()
    for prefix in ("/python", "/py"):
        if text == prefix:
            return ""
        if text.startswith(prefix + " "):
            return text[len(prefix) + 1 :].strip()
    return None


def _validate_tree(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        node_type = type(node)
        if node_type in _BLOCKED_NODE_NAMES or node_type.__name__ in _BLOCKED_NODE_NAMES:
            raise CodeExecutionError("هذا النوع من كود بايثون غير مسموح به.")
        if node_type not in _ALLOWED_NODES:
            raise CodeExecutionError(
                f"العقدة البرمجية {node_type.__name__} غير مسموح بها في المفسّر الآمن."
            )

        if isinstance(node, ast.Name):
            if node.id.startswith("__") or node.id in _BLOCKED_NAMES:
                raise CodeExecutionError("تم رفض اسم محظور لأسباب أمنية.")

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _SAFE_FUNCTION_NAMES:
                raise CodeExecutionError(
                    "استدعاء الدوال محدود إلى مجموعة دوال آمنة فقط."
                )

        if isinstance(node, ast.Subscript):
            # الفهرسة على القوائم/القواميس مسموحة، لكن لا نسمح بكائنات attribute.
            if isinstance(node.value, ast.Name) and node.value.id.startswith("__"):
                raise CodeExecutionError("الوصول إلى كائن داخلي محظور.")

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (bytes, bytearray)):
                raise CodeExecutionError("البيانات الثنائية غير مسموحة.")


def _build_worker_script(code_b64: str) -> str:
    return textwrap.dedent(
        f"""
        import base64
        import contextlib
        import io
        import math
        import statistics

        code = base64.b64decode({code_b64!r}).decode("utf-8")

        class OutputLimitExceeded(Exception):
            pass

        class LimitedBuffer(io.StringIO):
            def write(self, text):
                if self.tell() + len(text) > {MAX_OUTPUT_CHARS}:
                    raise OutputLimitExceeded()
                return super().write(text)

        output = LimitedBuffer()

        safe_globals = {{
            "__builtins__": {{}},
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "enumerate": enumerate,
            "float": float,
            "int": int,
            "len": len,
            "list": list,
            "max": max,
            "min": min,
            "print": lambda *args, **kwargs: print(*args, **kwargs, file=output),
            "range": range,
            "round": round,
            "set": set,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "zip": zip,
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "exp": math.exp,
            "floor": math.floor,
            "ceil": math.ceil,
            "factorial": math.factorial,
            "comb": math.comb,
            "perm": math.perm,
            "mean": statistics.mean,
            "median": statistics.median,
            "stdev": statistics.stdev,
            "pi": math.pi,
            "e": math.e,
        }}

        try:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                exec(compile(code, "<user-code>", "exec"), safe_globals, safe_globals)
        except OutputLimitExceeded:
            print("توقف التنفيذ لأن الناتج تجاوز الحد المسموح.", file=output)
        except Exception as exc:
            print(f"خطأ: {{type(exc).__name__}}: {{exc}}", file=output)

        print(output.getvalue(), end="")
        """
    )


def _limit_resources() -> None:
    if platform.system() != "Linux":
        return
    # اجعل مهلة subprocess هي الحاجز الأول؛ حد CPU أعلى قليلًا يمنع الإنهاء
    # بإشارة CPU قبل أن نعيد خطأ مهلة واضحًا للمستخدم.
    resource.setrlimit(
        resource.RLIMIT_CPU,
        (int(MAX_EXECUTION_SECONDS) + 2, int(MAX_EXECUTION_SECONDS) + 3),
    )
    resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_FILE_BYTES, MAX_FILE_BYTES))
    resource.setrlimit(resource.RLIMIT_NOFILE, (MAX_OPEN_FILES, MAX_OPEN_FILES))


def execute_python_code(code: str) -> str:
    """ينفذ كودًا محدودًا في عملية منفصلة ويعيد stdout/الأخطاء الآمنة."""
    code = code.strip()
    if not code:
        raise CodeExecutionError(
            "اكتب كود بايثون بعد /python، مثال: /python print(sum([1, 2, 3]))"
        )
    if len(code) > MAX_CODE_LENGTH:
        raise CodeExecutionError(f"الكود أطول من الحد المسموح ({MAX_CODE_LENGTH} حرف).")

    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise CodeExecutionError(f"خطأ نحوي في الكود: {exc.msg}.") from exc

    _validate_tree(tree)

    code_b64 = base64.b64encode(code.encode("utf-8")).decode("ascii")
    worker = _build_worker_script(code_b64)

    try:
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-S", "-c", worker],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=os.getenv("TMPDIR", "/tmp"),
            env={"PYTHONIOENCODING": "utf-8"},
            timeout=MAX_EXECUTION_SECONDS,
            check=False,
            start_new_session=True,
            preexec_fn=_limit_resources if platform.system() == "Linux" else None,
        )
    except subprocess.TimeoutExpired as exc:
        raise CodeExecutionError(
            f"توقف التنفيذ بعد {MAX_EXECUTION_SECONDS:.0f} ثوانٍ بسبب تجاوز المهلة."
        ) from exc
    except OSError as exc:
        raise CodeExecutionError("تعذر تشغيل المفسّر الآمن حاليًا.") from exc

    output = result.stdout.decode("utf-8", errors="replace").strip()
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + "\n… تم اقتطاع الناتج."

    if result.returncode != 0 and not output:
        raise CodeExecutionError("فشل تشغيل المفسّر الآمن.")

    return output or "اكتمل التنفيذ بدون ناتج."
