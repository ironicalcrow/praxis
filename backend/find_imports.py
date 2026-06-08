import ast
import os
import sys

stdlib = sys.stdlib_module_names
imports = set()

for root, _, files in os.walk('.'):
    for f in files:
        if f.endswith('.py'):
            with open(os.path.join(root, f), 'r', encoding='utf-8') as file:
                try:
                    tree = ast.parse(file.read(), filename=f)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                base = alias.name.split('.')[0]
                                if base not in stdlib and base != 'app':
                                    imports.add(base)
                        elif isinstance(node, ast.ImportFrom):
                            if node.level == 0 and node.module:
                                base = node.module.split('.')[0]
                                if base not in stdlib and base != 'app':
                                    imports.add(base)
                except SyntaxError:
                    pass

print(sorted(list(imports)))
