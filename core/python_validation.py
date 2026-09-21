"""Validate narrow AI name/import claims against complete Python source."""
import ast
import re


def contradicted_symbol_claim(issue, record):
    if record.get("language") != "python" or not record.get("success"):
        return None
    title = issue.get("title", "")
    match = re.search(r"[`'\"]([A-Za-z_]\w*)[`'\"]", title)
    if not match:
        return None
    name = match.group(1)
    undefined_claim = bool(re.search(r"undefined\s+(?:function|name|symbol)", title, re.I))
    unused_claim = bool(re.search(r"unused\s+import", title, re.I))
    if not (undefined_claim or unused_claim):
        return None
    try:
        from pyflakes.checker import Checker
        from pyflakes.messages import UndefinedName, UndefinedLocal, UnusedImport
        tree = ast.parse(record["content"])
        messages = Checker(tree, filename=record.get("path", "<source>")).messages
    except (ImportError, KeyError, SyntaxError, ValueError, TypeError, RecursionError):
        return None  # Missing evidence cannot establish that an AI claim is false.

    loads = [node for node in ast.walk(tree) if isinstance(node, ast.Name)
             and isinstance(node.ctx, ast.Load) and node.id == name]
    if undefined_claim:
        definitions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                       and node.name == name]
        unresolved = [m for m in messages if isinstance(m, (UndefinedName, UndefinedLocal))
                      and m.message_args[0] == name]
        if definitions and loads and not unresolved:
            return f"Complete file defines {name} at line {definitions[0].lineno}; scope analysis resolves its references."
    if unused_claim:
        imports = []
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    binding = alias.asname or (alias.name.split('.')[0] if isinstance(node, ast.Import) else alias.name)
                    if binding == name:
                        imports.append(node)
        # Pyflakes accounts for local shadowing; a same-spelled local variable is
        # not evidence that the module's import is used.
        unused = [m for m in messages if isinstance(m, UnusedImport)
                  and any(m.lineno == node.lineno for node in imports)]
        if imports and loads and not unused:
            return f"Complete-file scope analysis confirms that imported {name} is used (reference at line {loads[0].lineno})."
    return None
