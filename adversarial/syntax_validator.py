import ast

FORBIDDEN_IMPORT_ROOTS = {"LLMPlayer", "PhasedEngine"}


def _format_syntax_error(exc: SyntaxError) -> str:
    line = exc.lineno or 0
    column = exc.offset or 0
    return f"syntax error: {exc.msg} (line {line}, column {column})"


def validate_python(code: str) -> tuple[bool, str]:
    try:
        ast.parse(code)
    except SyntaxError as exc:
        return False, _format_syntax_error(exc)
    return True, ""


def validate_no_forbidden_imports(code: str) -> tuple[bool, str]:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, _format_syntax_error(exc)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in FORBIDDEN_IMPORT_ROOTS:
                    return False, f"imports forbidden module: {alias.name}"
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".", 1)[0]
            if root in FORBIDDEN_IMPORT_ROOTS:
                return False, f"imports forbidden module: {node.module}"

    return True, ""


def validate_patch(filename: str, code: str) -> tuple[bool, str]:
    is_valid, message = validate_python(code)
    if not is_valid:
        return False, f"{filename}: {message}"

    is_valid, message = validate_no_forbidden_imports(code)
    if not is_valid:
        return False, f"{filename}: {message}"

    return True, ""
