import ast
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open('otomatik_katil.py', encoding='utf-8') as f:
    tree = ast.parse(f.read())

for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if 'worker' in node.name.lower():
            print(f"{node.name}: lines {node.lineno} to {getattr(node, 'end_lineno', '?')}")
