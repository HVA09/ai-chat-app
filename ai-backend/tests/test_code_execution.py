"""اختبارات المفسّر الآمن."""
from app.services.tools.code_execution import (
    CodeExecutionError,
    execute_python_code,
    extract_code_request,
)


def test_extract_code_command():
    assert extract_code_request("/python print(2 + 3)") == "print(2 + 3)"
    assert extract_code_request("/py print(7 * 6)") == "print(7 * 6)"
    assert extract_code_request("print(2 + 3)") is None


def test_safe_python_execution():
    result = execute_python_code(
        "values = [1, 2, 3, 4]\nprint(sum(values))\nprint(mean(values))"
    )
    assert "10" in result
    assert "2.5" in result


def test_safe_python_rejects_imports():
    try:
        execute_python_code("import os\nos.system('echo hacked')")
    except CodeExecutionError:
        pass
    else:
        raise AssertionError("unsafe import was accepted")


def test_safe_python_rejects_attribute_access():
    try:
        execute_python_code("().__class__.__mro__")
    except CodeExecutionError:
        pass
    else:
        raise AssertionError("unsafe attribute access was accepted")


def test_safe_python_rejects_blocked_builtins():
    try:
        execute_python_code("print(open('/etc/passwd').read())")
    except CodeExecutionError:
        pass
    else:
        raise AssertionError("blocked builtin was accepted")


def test_safe_python_timeout():
    try:
        execute_python_code("while True: pass")
    except CodeExecutionError as exc:
        assert "المهلة" in str(exc)
    else:
        raise AssertionError("infinite loop was accepted")


def test_safe_python_rejects_dunder_import_and_dynamic_evaluation():
    for code in (
        "__import__('os')",
        "eval('2 + 2')",
        "getattr(str, '__class__')",
        "print(__builtins__)",
    ):
        try:
            execute_python_code(code)
        except CodeExecutionError:
            pass
        else:
            raise AssertionError(f"unsafe dynamic access was accepted: {code}")


def test_safe_python_rejects_comprehensions_and_callable_attributes():
    for code in (
        "print([x for x in range(3)])",
        "print(str.upper('hello'))",
        "print((1).__class__)",
    ):
        try:
            execute_python_code(code)
        except CodeExecutionError:
            pass
        else:
            raise AssertionError(f"unsafe syntax was accepted: {code}")


def test_safe_python_limits_output_size():
    result = execute_python_code("print('x' * 20000)")
    assert len(result) <= 12000
