#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import ast
import sys


class ModelConfigRemover(ast.NodeTransformer):
    def __init__(self) -> None:
        self.modified = False

    def is_rootmodel_class(self, node: ast.ClassDef) -> bool:
        """Check if the class inherits from RootModel."""
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == 'RootModel':
                return True
            elif isinstance(base, ast.Subscript):
                if (
                    isinstance(base.value, ast.Name)
                    and base.value.id == 'RootModel'
                ):
                    return True
        return False

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        """Visit class definitions and remove model_config if class inherits from RootModel."""
        if self.is_rootmodel_class(node):
            # Filter out model_config assignments
            new_body = []
            for item in node.body:
                if isinstance(item, ast.Assign):
                    targets = item.targets
                    if len(targets) == 1 and isinstance(targets[0], ast.Name):
                        if targets[0].id != 'model_config':
                            new_body.append(item)
                else:
                    new_body.append(item)

                if len(new_body) != len(node.body):
                    self.modified = True

            node.body = new_body

        return node


def process_file(filename: str) -> None:
    """Process a Python file to remove model_config from RootModel classes."""
    with open(filename) as f:
        source = f.read()

    tree = ast.parse(source)

    transformer = ModelConfigRemover()
    modified_tree = transformer.visit(tree)

    if transformer.modified:
        ast.fix_missing_locations(modified_tree)
        modified_source = ast.unparse(modified_tree)
        with open(filename, 'w') as f:
            f.write(modified_source)
        print(
            f'Modified {filename}: Removed model_config from RootModel classes'
        )
    else:
        print(f'No modifications needed in {filename}')


def main() -> None:
    if len(sys.argv) != 2:
        print('Usage: python script.py <filename>')
        sys.exit(1)

    filename = sys.argv[1]
    try:
        process_file(filename)
    except Exception as e:
        print(f'Error processing {filename}: {str(e)}')
        sys.exit(1)


if __name__ == '__main__':
    main()
