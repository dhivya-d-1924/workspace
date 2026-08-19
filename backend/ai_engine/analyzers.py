"""
Deterministic, rule-based code analysis engine.

This module performs *real* static analysis (not placeholder text):
- Python: full AST traversal for bug patterns, cyclomatic complexity,
  quality scoring and docstring/test scaffolding.
- Other languages: regex/heuristic analysis covering the same categories,
  since a full AST/parser per language is out of scope for this platform.

It is intentionally dependency-light (stdlib `ast` + `re` only) so the
platform works fully offline. `ai_client.py` can optionally layer a real
LLM on top of these results for richer natural-language explanations.
"""
import ast
import re
from collections import Counter

# --------------------------------------------------------------------------
# Shared regex heuristics (language agnostic-ish)
# --------------------------------------------------------------------------
SECRET_PATTERNS = [
    (re.compile(r'(?i)(api[_-]?key|secret|token|password|passwd|pwd)\s*[:=]\s*["\'][^"\']{4,}["\']'),
     "Hardcoded credential", "high"),
    (re.compile(r'(?i)aws_secret_access_key\s*[:=]'), "Hardcoded AWS secret", "critical"),
    (re.compile(r'-----BEGIN (RSA|EC|DSA|OPENSSH)? ?PRIVATE KEY-----'), "Embedded private key", "critical"),
]

SECURITY_PATTERNS = [
    (re.compile(r'\beval\s*\('), "Use of eval() can execute arbitrary code", "high"),
    (re.compile(r'\bexec\s*\('), "Use of exec() can execute arbitrary code", "high"),
    (re.compile(r'\bos\.system\s*\('), "os.system() call may allow shell injection", "high"),
    (re.compile(r'subprocess\.\w+\([^)]*shell\s*=\s*True'), "subprocess with shell=True is injection-prone", "high"),
    (re.compile(r'\bpickle\.load\s*\('), "pickle.load() on untrusted data allows code execution", "critical"),
    (re.compile(r'\byaml\.load\s*\((?!.*Loader)'), "yaml.load() without a safe Loader can execute code", "high"),
    (re.compile(r'(?i)select\s+.*\+\s*["\']|["\']\s*\+\s*\w+\s*\+\s*["\'].*(select|insert|update|delete)', re.I),
     "Possible SQL injection via string concatenation", "critical"),
    (re.compile(r'\.format\s*\(.*\)\s*.*(SELECT|INSERT|UPDATE|DELETE)', re.I),
     "Possible SQL injection via string formatting in a query", "high"),
    (re.compile(r'innerHTML\s*='), "Assigning to innerHTML can enable XSS", "medium"),
    (re.compile(r'\bmd5\s*\(|\bMD5\b'), "MD5 is not a secure hash for passwords", "medium"),
    (re.compile(r'\bDEBUG\s*=\s*True'), "Debug mode should not be enabled in production", "low"),
    (re.compile(r'verify\s*=\s*False'), "TLS certificate verification disabled", "medium"),
]


def scan_secrets_and_security(code: str) -> list:
    issues = []
    lines = code.splitlines()
    for i, line in enumerate(lines, start=1):
        for pattern, message, severity in SECRET_PATTERNS + SECURITY_PATTERNS:
            if pattern.search(line):
                issues.append({"line": i, "message": message, "severity": severity, "snippet": line.strip()[:120]})
    return issues


# --------------------------------------------------------------------------
# Python-specific deep analysis (uses the real `ast` module)
# --------------------------------------------------------------------------
class PythonComplexityVisitor(ast.NodeVisitor):
    """Computes McCabe cyclomatic complexity per function: 1 + number of branch points."""

    DECISION_NODES = (
        ast.If, ast.For, ast.While, ast.Try, ast.With,
        ast.BoolOp, ast.IfExp, ast.ExceptHandler, ast.Assert,
    )

    def __init__(self):
        self.results = []  # list of {name, complexity, lineno}
        self._stack = []

    def _enter_function(self, node):
        self._stack.append({"name": node.name, "complexity": 1, "lineno": node.lineno})
        self.generic_visit(node)
        finished = self._stack.pop()
        self.results.append(finished)

    def visit_FunctionDef(self, node):
        self._enter_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._enter_function(node)

    def generic_visit(self, node):
        if self._stack and isinstance(node, self.DECISION_NODES):
            self._stack[-1]["complexity"] += 1
        super().generic_visit(node)


def python_complexity(code: str):
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"error": f"Syntax error at line {e.lineno}: {e.msg}", "functions": []}
    visitor = PythonComplexityVisitor()
    visitor.visit(tree)
    functions = sorted(visitor.results, key=lambda f: -f["complexity"])
    for f in functions:
        f["rating"] = _complexity_rating(f["complexity"])
    avg = round(sum(f["complexity"] for f in functions) / len(functions), 2) if functions else 0
    return {"functions": functions, "average_complexity": avg, "max_complexity": max((f["complexity"] for f in functions), default=0)}


def _complexity_rating(score):
    if score <= 5:
        return "simple"
    if score <= 10:
        return "moderate"
    if score <= 20:
        return "complex"
    return "very complex"


PY_BUG_PATTERNS = {
    "mutable_default_arg": "Mutable default argument (list/dict/set) is shared across calls.",
    "bare_except": "Bare 'except:' catches everything, including KeyboardInterrupt/SystemExit.",
    "eq_none": "Comparing to None with '==' — use 'is None' instead.",
    "unused_variable": "Variable assigned but never used.",
    "broad_except": "Catching 'Exception' broadly can hide real bugs; catch specific exceptions.",
    "self_missing": "Instance method is missing 'self' as the first parameter.",
    "shadowed_builtin": "Parameter/variable shadows a Python builtin name.",
}

BUILTIN_NAMES = {"list", "dict", "str", "type", "id", "input", "map", "filter", "sum", "min", "max", "len"}


def find_python_bugs(code: str):
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [{"line": e.lineno or 0, "type": "syntax_error", "message": f"{e.msg}", "severity": "critical"}]

    bugs = []
    assigned_names = {}
    used_names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used_names.add(node.id)

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults + node.args.kw_defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    bugs.append({
                        "line": node.lineno, "type": "mutable_default_arg",
                        "message": f"{PY_BUG_PATTERNS['mutable_default_arg']} (function '{node.name}')",
                        "severity": "high",
                    })
            args = [a.arg for a in node.args.args]
            if args and args[0] != "self" and node.name != "__new__":
                # heuristic only, skip static/classmethods by checking decorators
                decorator_names = [d.id if isinstance(d, ast.Name) else getattr(d, "attr", "") for d in node.decorator_list]
                if "staticmethod" not in decorator_names and "classmethod" not in decorator_names:
                    pass  # can't reliably tell if this is a method vs a plain function without class context
            for arg in args:
                if arg in BUILTIN_NAMES:
                    bugs.append({
                        "line": node.lineno, "type": "shadowed_builtin",
                        "message": f"{PY_BUG_PATTERNS['shadowed_builtin']}: '{arg}' in function '{node.name}'",
                        "severity": "low",
                    })

        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                bugs.append({"line": node.lineno, "type": "bare_except", "message": PY_BUG_PATTERNS["bare_except"], "severity": "medium"})
            elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                bugs.append({"line": node.lineno, "type": "broad_except", "message": PY_BUG_PATTERNS["broad_except"], "severity": "low"})

        if isinstance(node, ast.Compare):
            for op, comparator in zip(node.ops, node.comparators):
                if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(comparator, ast.Constant) and comparator.value is None:
                    bugs.append({"line": node.lineno, "type": "eq_none", "message": PY_BUG_PATTERNS["eq_none"], "severity": "low"})

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigned_names.setdefault(target.id, node.lineno)

    for name, lineno in assigned_names.items():
        if name not in used_names and not name.startswith("_"):
            bugs.append({"line": lineno, "type": "unused_variable", "message": f"{PY_BUG_PATTERNS['unused_variable']} ('{name}')", "severity": "info"})

    bugs.extend(scan_secrets_and_security(code))
    return sorted(bugs, key=lambda b: b["line"])


GENERIC_BUG_PATTERNS = [
    (re.compile(r'==\s*null\b'), "Loose null comparison — consider strict equality.", "low"),
    (re.compile(r'\bvar\s+\w+'), "'var' has function scope; prefer 'let'/'const'.", "info"),
    (re.compile(r'==(?!=)'), "Loose equality '==' can cause type coercion bugs — consider '==='.", "low"),
    (re.compile(r'console\.log\('), "Leftover console.log statement.", "info"),
    (re.compile(r'catch\s*\(\s*\w*\s*\)\s*\{\s*\}'), "Empty catch block silently swallows errors.", "medium"),
    (re.compile(r'TODO|FIXME|XXX'), "Unresolved TODO/FIXME marker.", "info"),
]


def find_generic_bugs(code: str, language: str):
    bugs = []
    lines = code.splitlines()
    patterns = GENERIC_BUG_PATTERNS
    if language in ("javascript", "typescript"):
        pass  # patterns already tuned toward JS/TS
    for i, line in enumerate(lines, start=1):
        for pattern, message, severity in patterns:
            if pattern.search(line):
                bugs.append({"line": i, "type": "pattern", "message": message, "severity": severity, "snippet": line.strip()[:120]})
    bugs.extend(scan_secrets_and_security(code))
    return sorted(bugs, key=lambda b: b["line"])


def generic_complexity(code: str, language: str):
    """Rough cyclomatic-complexity approximation via branch keyword counting."""
    branch_keywords = r'\b(if|for|while|case|catch|elif|else if|&&|\|\|)\b'
    functions = []
    func_pattern = re.compile(
        r'(?:function\s+(\w+)\s*\(|(\w+)\s*=\s*(?:async\s*)?\(?.*?\)?\s*=>|(?:public|private|protected)?\s*\w[\w<>\[\]]*\s+(\w+)\s*\([^)]*\)\s*\{)'
    )
    matches = list(func_pattern.finditer(code))
    if not matches:
        total_branches = len(re.findall(branch_keywords, code))
        return {"functions": [], "average_complexity": total_branches + 1, "max_complexity": total_branches + 1}

    for idx, m in enumerate(matches):
        name = next((g for g in m.groups() if g), "anonymous")
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(code)
        body = code[start:end]
        complexity = 1 + len(re.findall(branch_keywords, body))
        lineno = code[:m.start()].count("\n") + 1
        functions.append({"name": name, "complexity": complexity, "lineno": lineno, "rating": _complexity_rating(complexity)})

    avg = round(sum(f["complexity"] for f in functions) / len(functions), 2) if functions else 0
    return {"functions": functions, "average_complexity": avg, "max_complexity": max((f["complexity"] for f in functions), default=0)}


# --------------------------------------------------------------------------
# Code quality score (0-100) — works for any language
# --------------------------------------------------------------------------
def quality_score(code: str, language: str, bugs=None, security_issues=None, complexity=None):
    lines = [l for l in code.splitlines() if l.strip()]
    if not lines:
        return {"score": 0, "grade": "F", "breakdown": {}, "notes": ["Empty file."]}

    comment_markers = ("#", "//", "/*", "*", '"""', "'''")
    comment_lines = sum(1 for l in lines if l.strip().startswith(comment_markers))
    comment_ratio = comment_lines / len(lines)

    long_lines = sum(1 for l in lines if len(l) > 100)
    avg_line_len = sum(len(l) for l in lines) / len(lines)

    bugs = bugs or []
    security_issues = security_issues or []
    complexity = complexity or {"average_complexity": 1, "max_complexity": 1}

    # --- sub-scores (each out of 100) ---
    comment_score = min(100, comment_ratio * 400)  # ~25% comments => 100
    length_score = max(0, 100 - long_lines * 5 - max(0, avg_line_len - 80) * 0.5)
    bug_penalty = sum({"critical": 25, "high": 15, "medium": 8, "low": 3, "info": 1}.get(b.get("severity", "low"), 3) for b in bugs)
    bug_score = max(0, 100 - bug_penalty)
    security_penalty = sum({"critical": 40, "high": 25, "medium": 12, "low": 5}.get(s.get("severity", "low"), 5) for s in security_issues)
    security_score = max(0, 100 - security_penalty)
    complexity_score = max(0, 100 - max(0, complexity.get("average_complexity", 1) - 5) * 8)

    weights = {"bugs": 0.30, "security": 0.30, "complexity": 0.20, "comments": 0.10, "formatting": 0.10}
    final = (
        bug_score * weights["bugs"]
        + security_score * weights["security"]
        + complexity_score * weights["complexity"]
        + comment_score * weights["comments"]
        + length_score * weights["formatting"]
    )
    final = round(max(0, min(100, final)), 1)

    grade = "A" if final >= 90 else "B" if final >= 80 else "C" if final >= 70 else "D" if final >= 60 else "F"

    notes = []
    if comment_ratio < 0.05:
        notes.append("Very few comments — consider documenting complex logic.")
    if long_lines:
        notes.append(f"{long_lines} line(s) exceed 100 characters.")
    if complexity.get("max_complexity", 0) > 10:
        notes.append("At least one function has high cyclomatic complexity — consider refactoring.")
    if security_issues:
        notes.append(f"{len(security_issues)} potential security issue(s) detected.")
    if bugs:
        notes.append(f"{len(bugs)} potential bug/code-smell pattern(s) detected.")
    if not notes:
        notes.append("Code looks clean by static-analysis heuristics.")

    return {
        "score": final,
        "grade": grade,
        "breakdown": {
            "bug_score": round(bug_score, 1),
            "security_score": round(security_score, 1),
            "complexity_score": round(complexity_score, 1),
            "comment_score": round(comment_score, 1),
            "formatting_score": round(length_score, 1),
        },
        "notes": notes,
    }


# --------------------------------------------------------------------------
# Explanation, docstrings, tests (Python uses ast, others use regex fallback)
# --------------------------------------------------------------------------
def python_structure_summary(code: str):
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"error": f"Syntax error at line {e.lineno}: {e.msg}"}

    functions, classes, imports = [], [], []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not _is_method(tree, node):
            functions.append(_describe_function(node))
        elif isinstance(node, ast.ClassDef):
            methods = [_describe_function(n) for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            classes.append({"name": node.name, "lineno": node.lineno, "methods": methods, "bases": [_name_of(b) for b in node.bases]})
        elif isinstance(node, ast.Import):
            imports.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")

    # also include methods nested in classes as functions-of-interest for docs
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for n in node.body:
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append(_describe_function(n, owner=node.name))

    return {"functions": functions, "classes": classes, "imports": sorted(set(imports))}


def _is_method(tree, func_node):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and func_node in node.body:
            return True
    return False


def _name_of(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return "object"


def _describe_function(node, owner=None):
    args = [a.arg for a in node.args.args]
    returns_something = any(isinstance(n, ast.Return) and n.value is not None for n in ast.walk(node))
    docstring = ast.get_docstring(node)
    return {
        "name": node.name,
        "owner": owner,
        "lineno": node.lineno,
        "args": args,
        "has_docstring": bool(docstring),
        "docstring": docstring,
        "returns_value": returns_something,
        "is_async": isinstance(node, ast.AsyncFunctionDef),
    }
