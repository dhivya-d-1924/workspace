"""
Feature-level generators that sit on top of analyzers.py.
Each function returns a JSON-serialisable dict ready for the API response.
"""
import ast
import re
import textwrap

from . import analyzers


# --------------------------------------------------------------------------
# Explain code
# --------------------------------------------------------------------------
def explain_code(code: str, language: str) -> dict:
    if language == "python":
        structure = analyzers.python_structure_summary(code)
        if "error" in structure:
            return {"summary": "Could not parse the code.", "error": structure["error"]}

        lines = []
        if structure["imports"]:
            lines.append(f"This module imports: {', '.join(structure['imports'][:10])}.")
        if structure["classes"]:
            for c in structure["classes"]:
                method_names = ", ".join(m["name"] for m in c["methods"]) or "no methods"
                lines.append(f"Class `{c['name']}` defines {len(c['methods'])} method(s): {method_names}.")
        top_level_fns = [f for f in structure["functions"] if not f["owner"]]
        for f in top_level_fns:
            args = ", ".join(f["args"]) or "no arguments"
            ret = "returns a value" if f["returns_value"] else "does not return a value"
            doc = f" Docstring: \"{f['docstring'].splitlines()[0]}\"" if f["docstring"] else " (no docstring)"
            lines.append(f"Function `{f['name']}({args})` {ret}.{doc}")
        if not lines:
            lines.append("This file contains only top-level statements (a script), no functions or classes were detected.")

        complexity = analyzers.python_complexity(code)
        overview = (
            f"Overall this file defines {len(structure['functions'])} function(s) and "
            f"{len(structure['classes'])} class(es), with an average cyclomatic complexity of "
            f"{complexity.get('average_complexity', 0)}."
        )
        return {"summary": overview, "details": lines, "structure": structure}

    # Generic language: heuristic summary
    line_count = len(code.splitlines())
    func_matches = re.findall(r'\bfunction\s+(\w+)|\b(\w+)\s*\([^)]*\)\s*\{', code)
    func_names = [n for pair in func_matches for n in pair if n][:10]
    loops = len(re.findall(r'\b(for|while)\b', code))
    conditionals = len(re.findall(r'\b(if|switch|case)\b', code))
    summary = (
        f"This {language} snippet is {line_count} line(s) long, references roughly "
        f"{len(func_names)} function(s)/method(s), contains {loops} loop construct(s) and "
        f"{conditionals} conditional construct(s)."
    )
    details = [f"Detected identifiers that look like functions: {', '.join(func_names)}"] if func_names else []
    return {"summary": summary, "details": details}


# --------------------------------------------------------------------------
# Find bugs / Fix bugs
# --------------------------------------------------------------------------
def find_bugs(code: str, language: str) -> dict:
    bugs = analyzers.find_python_bugs(code) if language == "python" else analyzers.find_generic_bugs(code, language)
    severity_counts = {}
    for b in bugs:
        severity_counts[b["severity"]] = severity_counts.get(b["severity"], 0) + 1
    return {"bugs": bugs, "total": len(bugs), "by_severity": severity_counts}


PY_FIXES = [
    (re.compile(r'==\s*None\b'), "is None"),
    (re.compile(r'!=\s*None\b'), "is not None"),
    (re.compile(r'except\s*:'), "except Exception:"),
]

GENERIC_FIXES = [
    (re.compile(r'==\s*null\b'), "=== null"),
    (re.compile(r'(?<![=!<>])==(?!=)'), "==="),
    (re.compile(r'\bvar\s+'), "let "),
]


def fix_bugs(code: str, language: str) -> dict:
    """Applies deterministic, safe textual fixes and reports what changed."""
    fixed = code
    changes = []
    fixes = PY_FIXES if language == "python" else GENERIC_FIXES

    for pattern, replacement in fixes:
        def _sub(m, replacement=replacement):
            return replacement
        new_fixed, count = pattern.subn(replacement, fixed)
        if count:
            changes.append(f"Replaced {count} occurrence(s) of pattern '{pattern.pattern}' with '{replacement}'.")
            fixed = new_fixed

    # mutable default arg fix (python) - rewrite `def f(x=[])` -> `def f(x=None)` + guard note
    if language == "python":
        mutable_default = re.compile(r'(def\s+\w+\([^)]*?)(\w+)\s*=\s*(\[\]|\{\}|set\(\))')
        def _mut_sub(m):
            changes.append(f"Changed mutable default for '{m.group(2)}' to None (add a None-check inside the function).")
            return f"{m.group(1)}{m.group(2)}=None"
        fixed = mutable_default.sub(_mut_sub, fixed)

    bugs_before = find_bugs(code, language)["total"]
    bugs_after = find_bugs(fixed, language)["total"]

    return {
        "fixed_code": fixed,
        "changes": changes if changes else ["No automatically-fixable patterns were found; manual review recommended."],
        "bugs_before": bugs_before,
        "bugs_after": bugs_after,
    }


# --------------------------------------------------------------------------
# Optimize code
# --------------------------------------------------------------------------
def optimize_code(code: str, language: str) -> dict:
    suggestions = []

    # nested loop detection -> potential O(n^2)+
    if language == "python":
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.For, ast.While)):
                    nested = [n for n in ast.walk(node) if isinstance(n, (ast.For, ast.While)) and n is not node]
                    if nested:
                        suggestions.append({
                            "line": node.lineno, "type": "nested_loop",
                            "message": "Nested loop detected — check for an O(n²) or worse pattern; "
                                       "consider a hash map/set lookup or itertools to flatten the logic.",
                        })
            if re.search(r'for .* in .*:\s*\n\s*\w+\s*=\s*\w+\s*\+\s*\[', code):
                suggestions.append({"line": None, "type": "list_concat_in_loop",
                                     "message": "List concatenation inside a loop is O(n) per iteration — use .append() or a list comprehension."})
            if re.search(r'for .* in .*:\s*\n\s*\w+\s*\+=\s*["\']', code):
                suggestions.append({"line": None, "type": "string_concat_in_loop",
                                     "message": "String concatenation with '+=' inside a loop is O(n²) overall — build a list and ''.join() it."})
            if re.search(r'\.append\(.*\)\s*\n.*sort\(\)', code):
                suggestions.append({"line": None, "type": "repeated_sort",
                                     "message": "Sorting after every append is wasteful — consider a heap (heapq) if you need ongoing order."})
            if "range(len(" in code:
                suggestions.append({"line": None, "type": "range_len",
                                     "message": "`range(len(x))` followed by `x[i]` can usually be replaced with `enumerate(x)` for clarity/speed."})
        except SyntaxError as e:
            return {"suggestions": [], "error": f"Syntax error at line {e.lineno}: {e.msg}"}
    else:
        if re.search(r'for\s*\([^)]*\)\s*\{[^{}]*for\s*\(', code, re.S):
            suggestions.append({"line": None, "type": "nested_loop", "message": "Nested loops detected — verify time complexity and consider a map/set for lookups."})
        if re.search(r'\+\s*=?\s*["\'].*["\'].*for', code):
            suggestions.append({"line": None, "type": "string_concat_in_loop", "message": "Repeated string concatenation in a loop is inefficient — use an array/buffer and join at the end."})
        if "document.getElementById" in code and code.count("document.getElementById") > 3:
            suggestions.append({"line": None, "type": "dom_lookup", "message": "Multiple repeated DOM lookups — cache the element reference in a variable."})

    complexity = analyzers.python_complexity(code) if language == "python" else analyzers.generic_complexity(code, language)
    for f in complexity.get("functions", []):
        if f["complexity"] > 10:
            suggestions.append({
                "line": f.get("lineno"), "type": "high_complexity",
                "message": f"Function '{f['name']}' has cyclomatic complexity {f['complexity']} — consider splitting it into smaller functions.",
            })

    if not suggestions:
        suggestions.append({"line": None, "type": "none", "message": "No obvious performance anti-patterns detected by static analysis."})

    return {"suggestions": suggestions, "complexity": complexity}


# --------------------------------------------------------------------------
# Generate code (template-driven, keyword-matched)
# --------------------------------------------------------------------------
CODE_TEMPLATES = {
    "python": {
        "rest_endpoint": '''from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET", "POST"])
def {name}(request):
    """{description}"""
    if request.method == "GET":
        return Response({{"message": "list {name}"}})
    # POST
    data = request.data
    return Response({{"message": "created", "data": data}}, status=201)
''',
        "class": '''class {class_name}:
    """{description}"""

    def __init__(self, {args}):
{init_body}

    def __repr__(self):
        return f"{class_name}({repr_fields})"
''',
        "function": '''def {name}({args}):
    """{description}

    Args:
{arg_docs}
    Returns:
        TODO: describe the return value.
    """
    # TODO: implement {name}
    raise NotImplementedError
''',
        "sort": '''def {name}(items):
    """Sorts `items` using an efficient comparison sort (Timsort via sorted())."""
    return sorted(items)
''',
        "binary_search": '''def {name}(sorted_items, target):
    """Binary search: returns the index of target in sorted_items, or -1 if absent."""
    low, high = 0, len(sorted_items) - 1
    while low <= high:
        mid = (low + high) // 2
        if sorted_items[mid] == target:
            return mid
        if sorted_items[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
''',
    },
    "javascript": {
        "rest_endpoint": '''app.route('/{name}')
  .get((req, res) => {{
    // {description}
    res.json({{ message: 'list {name}' }});
  }})
  .post((req, res) => {{
    const data = req.body;
    res.status(201).json({{ message: 'created', data }});
  }});
''',
        "class": '''class {class_name} {{
  // {description}
  constructor({args}) {{
{init_body}
  }}
}}
''',
        "function": '''/**
 * {description}
 */
function {name}({args}) {{
  // TODO: implement {name}
  throw new Error('Not implemented');
}}
''',
    },
}


def generate_code(prompt: str, language: str) -> dict:
    prompt_l = prompt.lower()
    language = language if language in CODE_TEMPLATES else "python"
    templates = CODE_TEMPLATES[language]

    name = _slugify_identifier(prompt)

    if any(k in prompt_l for k in ["rest api", "endpoint", "api route", "http route"]):
        code = templates["rest_endpoint"].format(name=name or "resource", description=prompt.strip())
        kind = "rest_endpoint"
    elif "binary search" in prompt_l:
        code = templates.get("binary_search", templates["function"]).format(name=name or "binary_search")
        kind = "binary_search"
    elif "sort" in prompt_l and language == "python":
        code = templates["sort"].format(name=name or "sort_items")
        kind = "sort"
    elif any(k in prompt_l for k in ["class", "model", "object representing"]):
        class_name = "".join(w.capitalize() for w in re.findall(r'[A-Za-z]+', prompt))[:40] or "GeneratedClass"
        fields = _guess_fields(prompt)
        args = ", ".join(fields) if language == "python" else ", ".join(fields)
        init_body = "\n".join(f"        self.{f} = {f}" for f in fields) if language == "python" else "\n".join(f"    this.{f} = {f};" for f in fields)
        repr_fields = ", ".join(f"{f}={{self.{f}!r}}" for f in fields) if language == "python" else ""
        code = templates["class"].format(class_name=class_name, description=prompt.strip(), args=args, init_body=init_body or ("        pass" if language == "python" else "    // no fields"), repr_fields=repr_fields)
        kind = "class"
    else:
        args = ", ".join(_guess_args(prompt)) or "*args, **kwargs" if language == "python" else "args"
        arg_docs = "\n".join(f"        {a}: TODO describe." for a in args.split(", ")) if language == "python" else ""
        code = templates["function"].format(name=name or "generated_function", description=prompt.strip(), args=args, arg_docs=arg_docs or "        (none)")
        kind = "function"

    return {"code": code, "language": language, "template_used": kind,
            "note": "Generated from a rule-based template engine. Review and adapt before use."}


def _slugify_identifier(text: str) -> str:
    words = re.findall(r'[A-Za-z0-9]+', text.lower())
    stop = {"a", "an", "the", "to", "for", "of", "that", "function", "generate", "create", "write", "me", "please"}
    words = [w for w in words if w not in stop][:5]
    return "_".join(words) if words else ""


def _guess_fields(text: str):
    common = re.findall(r'\b(name|id|email|price|title|description|amount|date|status|user|age|quantity)\b', text.lower())
    seen = []
    for w in common:
        if w not in seen:
            seen.append(w)
    return seen[:6] or ["id", "name"]


def _guess_args(text: str):
    return _guess_fields(text)[:4] or ["value"]


# --------------------------------------------------------------------------
# Convert code between languages (subset: python <-> javascript scaffolding)
# --------------------------------------------------------------------------
def convert_code(code: str, source_lang: str, target_lang: str) -> dict:
    if source_lang == "python" and target_lang in ("javascript", "typescript"):
        converted = _python_to_js(code)
        note = "Best-effort structural conversion (def/print/self/None/True-False/snake_case). Review types, imports and language-specific idioms."
    elif source_lang in ("javascript", "typescript") and target_lang == "python":
        converted = _js_to_python(code)
        note = "Best-effort structural conversion (function/console.log/this/const-let-var). Review types, imports and idioms."
    else:
        converted = code
        note = f"Automatic conversion between {source_lang} and {target_lang} is not supported by the offline engine; only structural python<->javascript conversion is available. Returning the original code for manual porting."

    return {"converted_code": converted, "source_language": source_lang, "target_language": target_lang, "note": note}


def _python_to_js(code: str) -> str:
    out = code
    out = re.sub(r'def\s+(\w+)\s*\(self,?\s*', r'\1(', out)
    out = re.sub(r'def\s+(\w+)\s*\(', r'function \1(', out)
    out = re.sub(r'\bself\.', 'this.', out)
    out = re.sub(r'\bNone\b', 'null', out)
    out = re.sub(r'\bTrue\b', 'true', out)
    out = re.sub(r'\bFalse\b', 'false', out)
    out = re.sub(r'\bprint\((.*)\)', r'console.log(\1)', out)
    out = re.sub(r'\belif\b', '} else if', out)
    out = re.sub(r'\belse:\s*$', '} else {', out, flags=re.M)
    out = re.sub(r':\s*$', ' {', out, flags=re.M)
    out = re.sub(r'#', '//', out)
    lines = out.splitlines()
    return "\n".join(lines) + "\n// NOTE: auto-converted — braces/semicolons/indentation need manual review."


def _js_to_python(code: str) -> str:
    out = code
    out = re.sub(r'function\s+(\w+)\s*\(', r'def \1(', out)
    out = re.sub(r'\bthis\.', 'self.', out)
    out = re.sub(r'\bnull\b|\bundefined\b', 'None', out)
    out = re.sub(r'\btrue\b', 'True', out)
    out = re.sub(r'\bfalse\b', 'False', out)
    out = re.sub(r'console\.log\((.*)\);?', r'print(\1)', out)
    out = re.sub(r'\b(const|let|var)\s+', '', out)
    out = re.sub(r'//', '#', out)
    out = re.sub(r'[{};]', '', out)
    return out + "\n# NOTE: auto-converted — indentation and control-flow blocks need manual review."


# --------------------------------------------------------------------------
# Comments & documentation
# --------------------------------------------------------------------------
def generate_comments(code: str, language: str) -> dict:
    if language != "python":
        lines = code.splitlines()
        commented = []
        func_re = re.compile(r'^\s*(function\s+\w+|const\s+\w+\s*=\s*\(.*\)\s*=>|\w+\s*\([^)]*\)\s*\{)')
        for line in lines:
            if func_re.match(line):
                commented.append("// TODO: document this function")
            commented.append(line)
        return {"commented_code": "\n".join(commented), "note": "Heuristic pass — a comment placeholder was added above each detected function."}

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"commented_code": code, "error": f"Syntax error at line {e.lineno}: {e.msg}"}

    lines = code.splitlines()
    insertions = {}  # lineno (1-indexed, insert before) -> comment text
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not ast.get_docstring(node):
                args = ", ".join(a.arg for a in node.args.args if a.arg != "self")
                insertions[node.lineno] = f"# {node.name}({args}): TODO describe what this function does."
        elif isinstance(node, ast.ClassDef):
            if not ast.get_docstring(node):
                insertions[node.lineno] = f"# Class {node.name}: TODO describe the purpose of this class."

    out = []
    for i, line in enumerate(lines, start=1):
        if i in insertions:
            indent = re.match(r'^(\s*)', line).group(1)
            out.append(f"{indent}{insertions[i]}")
        out.append(line)

    return {"commented_code": "\n".join(out), "comments_added": len(insertions)}


def generate_documentation(code: str, language: str) -> dict:
    if language != "python":
        return {
            "markdown": f"# Documentation\n\nAutomatic deep documentation is only available for Python in the offline engine. "
                        f"Detected roughly {len(re.findall(r'function ', code))} function(s) in this {language} file — "
                        f"add JSDoc/Docblocks and re-run once a language-specific parser is configured.",
        }

    structure = analyzers.python_structure_summary(code)
    if "error" in structure:
        return {"markdown": f"# Documentation\n\nCould not parse file: {structure['error']}"}

    md = ["# Module Documentation\n"]
    if structure["imports"]:
        md.append("## Imports\n" + "\n".join(f"- `{i}`" for i in structure["imports"]) + "\n")

    if structure["classes"]:
        md.append("## Classes\n")
        for c in structure["classes"]:
            bases = f"({', '.join(c['bases'])})" if c["bases"] else ""
            md.append(f"### `class {c['name']}{bases}`\n")
            for m in c["methods"]:
                args = ", ".join(m["args"])
                md.append(f"- **`{m['name']}({args})`** — " + (m["docstring"].splitlines()[0] if m["docstring"] else "_no docstring provided_"))
            md.append("")

    top_level = [f for f in structure["functions"] if not f["owner"]]
    if top_level:
        md.append("## Functions\n")
        for f in top_level:
            args = ", ".join(f["args"])
            ret = " → returns a value" if f["returns_value"] else ""
            md.append(f"### `{f['name']}({args})`{ret}\n")
            md.append(f["docstring"] if f["docstring"] else "_No docstring provided — TODO: describe behaviour, parameters and return value._")
            md.append("")

    return {"markdown": "\n".join(md)}


# --------------------------------------------------------------------------
# Generate test cases
# --------------------------------------------------------------------------
def generate_test_cases(code: str, language: str) -> dict:
    if language != "python":
        return {
            "tests": "// Automatic test scaffolding is only available for Python in the offline engine.\n"
                     "// Consider Jest/Mocha for JS/TS: describe('<function>', () => { it('does X', () => { ... }); });",
            "framework": "n/a",
        }

    structure = analyzers.python_structure_summary(code)
    if "error" in structure:
        return {"tests": "", "error": structure["error"]}

    top_level = [f for f in structure["functions"] if not f["owner"]]
    if not top_level:
        return {"tests": "# No top-level functions were found to generate tests for.", "framework": "pytest"}

    module_hint = "your_module"
    lines = [f"import pytest\nfrom {module_hint} import (" + ", ".join(f["name"] for f in top_level) + ")\n"]
    for f in top_level:
        args_sig = ", ".join(f"{a}=None" for a in f["args"])
        lines.append(f"def test_{f['name']}_basic():")
        lines.append(f"    # TODO: replace None placeholders with realistic input values")
        if f["returns_value"]:
            lines.append(f"    result = {f['name']}({args_sig})")
            lines.append(f"    assert result is not None  # TODO: assert the actual expected value")
        else:
            lines.append(f"    {f['name']}({args_sig})  # TODO: assert side effects (state, mocks, output)")
        lines.append("")
        lines.append(f"def test_{f['name']}_edge_cases():")
        lines.append(f"    # TODO: add boundary/None/empty/invalid-input cases for '{f['name']}'")
        lines.append(f"    pass")
        lines.append("")

    return {"tests": "\n".join(lines), "framework": "pytest", "functions_covered": [f["name"] for f in top_level]}


# --------------------------------------------------------------------------
# Generate SQL from natural language
# --------------------------------------------------------------------------
AGG_WORDS = {"count": "COUNT(*)", "total": "SUM", "sum": "SUM", "average": "AVG", "avg": "AVG", "maximum": "MAX", "max": "MAX", "minimum": "MIN", "min": "MIN"}


def generate_sql(prompt: str, schema: dict | None = None) -> dict:
    """
    schema, if provided, looks like: {"users": ["id", "name", "email", "created_at"], ...}
    Falls back to guessing a table name from the prompt when no schema is given.
    """
    prompt_l = prompt.lower().strip()
    schema = schema or {}

    table = _match_table(prompt_l, schema)
    columns = schema.get(table, ["*"]) if table else ["*"]

    where_clauses = []
    m = re.search(r'where\s+(\w+)\s*(=|>|<|>=|<=|!=)\s*["\']?([\w\-@.]+)["\']?', prompt_l)
    if m:
        where_clauses.append(f"{m.group(1)} {m.group(2)} '{m.group(3)}'")
    m2 = re.search(r'(\w+)\s+(?:is|equals?)\s+["\']?([\w\-@.]+)["\']?', prompt_l)
    if m2 and not where_clauses:
        where_clauses.append(f"{m2.group(1)} = '{m2.group(2)}'")

    order = ""
    m3 = re.search(r'(?:sort|order)(?:ed)?\s+by\s+(\w+)\s*(asc|desc)?', prompt_l)
    if m3:
        order = f" ORDER BY {m3.group(1)} {m3.group(2).upper() if m3.group(2) else 'ASC'}"

    limit = ""
    m4 = re.search(r'(?:top|first|limit)\s+(\d+)', prompt_l)
    if m4:
        limit = f" LIMIT {m4.group(1)}"

    agg = next((sql for word, sql in AGG_WORDS.items() if word in prompt_l), None)

    if any(k in prompt_l for k in ["delete", "remove"]) and table:
        sql = f"DELETE FROM {table}" + (f" WHERE {' AND '.join(where_clauses)}" if where_clauses else "")
    elif any(k in prompt_l for k in ["update", "change", "set"]) and table:
        sql = f"UPDATE {table} SET <column> = <value>" + (f" WHERE {' AND '.join(where_clauses)}" if where_clauses else "")
    elif any(k in prompt_l for k in ["insert", "add", "create a new", "add a new"]) and table:
        cols = [c for c in columns if c != "*"] or ["column1", "column2"]
        placeholders = ", ".join(f"'<{c}>'" for c in cols)
        sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
    elif agg and table:
        sql = f"SELECT {agg} FROM {table}" + (f" WHERE {' AND '.join(where_clauses)}" if where_clauses else "")
    elif table:
        select_cols = ", ".join(columns) if columns != ["*"] else "*"
        sql = f"SELECT {select_cols} FROM {table}" + (f" WHERE {' AND '.join(where_clauses)}" if where_clauses else "") + order + limit
    else:
        sql = "-- Could not confidently detect a table name. Please mention the table (e.g. 'from the users table') or supply a schema."

    return {"sql": sql, "detected_table": table, "note": "Generated via rule-based NL→SQL parsing. Always review generated SQL before executing it against production data."}


def _match_table(prompt_l: str, schema: dict):
    for table_name in schema.keys():
        if table_name.lower() in prompt_l or table_name.lower().rstrip("s") in prompt_l:
            return table_name
    m = re.search(r'from (?:the )?(\w+) table|(\w+)\s+table|in (\w+)\b', prompt_l)
    if m:
        return next((g for g in m.groups() if g), None)
    m2 = re.search(r'\b(users?|orders?|products?|customers?|employees?|payments?|invoices?)\b', prompt_l)
    if m2:
        word = m2.group(1)
        return word if word.endswith("s") else word + "s"
    return None


# --------------------------------------------------------------------------
# Explain error messages
# --------------------------------------------------------------------------
ERROR_KB = [
    (re.compile(r'NameError: name \'(\w+)\' is not defined'),
     "The variable/function '{0}' is used before it was defined (or is misspelled, or defined in a different scope).",
     ["Check the spelling of '{0}'.", "Ensure '{0}' is defined/imported before this line runs.", "If it's meant to be a module-level import, add the import statement."]),
    (re.compile(r'TypeError: (.+) takes (\d+) positional argument'),
     "A function was called with the wrong number of arguments.",
     ["Check the function's signature and match the number of positional arguments.", "If using **kwargs is intended, pass them as keyword arguments instead."]),
    (re.compile(r"TypeError: 'NoneType' object is not (subscriptable|iterable|callable)"),
     "A variable that is None was used as if it held a value (e.g. indexed, looped over, or called).",
     ["Trace back where this variable was assigned — a function likely returned None instead of the expected value.", "Add a None-check before using the variable."]),
    (re.compile(r'IndexError: list index out of range'),
     "Code tried to access a list index that doesn't exist.",
     ["Check the list length with len() before indexing.", "Use try/except IndexError, or safe access with .get()-style patterns for dict-like structures."]),
    (re.compile(r'KeyError: \'?(\w+)\'?'),
     "The dictionary key '{0}' does not exist in the dict being accessed.",
     ["Use dict.get('{0}', default) instead of dict['{0}'].", "Verify the key name/spelling and that it was actually set upstream."]),
    (re.compile(r'ZeroDivisionError'),
     "Code attempted to divide by zero.",
     ["Add a guard clause checking the divisor isn't zero before dividing."]),
    (re.compile(r'IndentationError'),
     "Python's indentation (whitespace) is inconsistent — mixing tabs/spaces or misaligned blocks.",
     ["Use a consistent indentation (4 spaces recommended) throughout the file.", "Configure your editor to convert tabs to spaces."]),
    (re.compile(r'ModuleNotFoundError: No module named \'(\w+)\''),
     "The package '{0}' is not installed in the current environment.",
     ["Run: pip install {0}", "Verify you're in the correct virtual environment."]),
    (re.compile(r'ConnectionRefusedError|ECONNREFUSED'),
     "The application could not connect to a service (e.g. database or API) at the given host/port.",
     ["Confirm the target service is running.", "Check the host/port configuration and firewall/network rules."]),
    (re.compile(r'(?:django\.db\.utils\.OperationalError|MySQLdb\.OperationalError).*Access denied'),
     "MySQL rejected the connection due to a wrong username/password.",
     ["Double check DB_USER/DB_PASSWORD in your environment configuration.", "Confirm the MySQL user has privileges on the target database."]),
    (re.compile(r'CORS'),
     "A cross-origin request was blocked by the browser because the server didn't allow it.",
     ["Add the frontend origin to CORS_ALLOWED_ORIGINS on the backend.", "Ensure the request includes the correct headers/credentials mode."]),
    (re.compile(r'401|Unauthorized'),
     "The request was rejected because it lacked valid authentication credentials.",
     ["Confirm the JWT access token is included as 'Authorization: Bearer <token>'.", "The token may be expired — try refreshing it."]),
    (re.compile(r'SyntaxError'),
     "The code has invalid Python syntax at the reported location.",
     ["Check for a missing colon, unmatched bracket/quote, or misplaced keyword near the reported line."]),
]


def explain_error(error_message: str, language: str = "python") -> dict:
    for pattern, explanation_tpl, fixes_tpl in ERROR_KB:
        m = pattern.search(error_message)
        if m:
            groups = m.groups()
            explanation = explanation_tpl.format(*groups) if groups else explanation_tpl
            fixes = [f.format(*groups) if groups else f for f in fixes_tpl]
            return {"matched": True, "explanation": explanation, "suggested_fixes": fixes, "error_type": pattern.pattern.split(":")[0].split("|")[0]}

    return {
        "matched": False,
        "explanation": "This error message doesn't match a known pattern in the offline knowledge base.",
        "suggested_fixes": [
            "Read the last line of the traceback — it names the exception type and message.",
            "The line just above 'Traceback (most recent call last)' entries shows where in your code the failure occurred; start there.",
            "Search the exact error text alongside your language/framework name for known causes.",
        ],
        "error_type": "unknown",
    }
