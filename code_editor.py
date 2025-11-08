"""
================================================================================
FILE: AILib/code_editor.py
PURPOSE: Smart code editing - update functions without rewriting entire file
DEPENDENCIES: Uses YOUR file_access.py for reading/writing files
================================================================================
"""

import ast
import re
from typing import Dict, List, Optional
from dataclasses import dataclass


# ================================================================================
# CODE ELEMENT - Represents a function or class in code
# ================================================================================

@dataclass
class CodeElement:
    """
    Represents a code element (function, class, method)
    
    Attributes:
        type: 'function', 'class', 'method', 'import'
        name: Name of the element
        start_line: Starting line number
        end_line: Ending line number
        content: The actual code
        indentation: Indentation level
    """
    type: str
    name: str
    start_line: int
    end_line: int
    content: str
    indentation: int = 0


# ================================================================================
# CODE ANALYZER - Parse code structure
# ================================================================================

class CodeAnalyzer:
    """
    Analyzes Python code structure using AST (Abstract Syntax Tree)
    
    Features:
    - Find all functions in a file
    - Find all classes in a file
    - Find specific function by name
    - Get line numbers for each element
    """
    
    def __init__(self):
        pass
    
    def parse_python(self, code: str) -> List[CodeElement]:
        """
        Parse Python code into elements (functions, classes)
        
        Args:
            code: Python source code
        
        Returns:
            List of CodeElement objects
        """
        elements = []
        
        try:
            tree = ast.parse(code)
            lines = code.split('\n')
            
            for node in ast.walk(tree):
                # Find functions
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    start = node.lineno - 1
                    end = node.end_lineno if hasattr(node, 'end_lineno') else start + 1
                    
                    elements.append(CodeElement(
                        type='function',
                        name=node.name,
                        start_line=start,
                        end_line=end,
                        content='\n'.join(lines[start:end]),
                        indentation=node.col_offset
                    ))
                
                # Find classes
                elif isinstance(node, ast.ClassDef):
                    start = node.lineno - 1
                    end = node.end_lineno if hasattr(node, 'end_lineno') else start + 1
                    
                    elements.append(CodeElement(
                        type='class',
                        name=node.name,
                        start_line=start,
                        end_line=end,
                        content='\n'.join(lines[start:end]),
                        indentation=node.col_offset
                    ))
        
        except SyntaxError:
            # Code has syntax errors - return empty list
            pass
        
        return elements
    
    def find_element(self, elements: List[CodeElement], name: str) -> Optional[CodeElement]:
        """
        Find a specific element by name
        
        Args:
            elements: List of CodeElement
            name: Name to search for
        
        Returns:
            CodeElement or None if not found
        """
        for elem in elements:
            if elem.name == name:
                return elem
        return None


# ================================================================================
# SMART CODE EDITOR - Modify code intelligently
# ================================================================================

class SmartCodeEditor:
    """
    Smart code editor that modifies code without rewriting entire files
    
    Uses YOUR FileSystem from file_access.py
    
    Features:
    - Update single function (keep rest of file unchanged)
    - Add new method to existing class
    - Add import statement
    - Rename function across file
    
    Example:
        editor = SmartCodeEditor(fs_manager)
        editor.update_function("app.py", "login", new_code)
    """
    
    def __init__(self, fs_manager):
        """
        Initialize editor
        
        Args:
            fs_manager: FileSystem instance from YOUR file_access.py
        """
        self.fs = fs_manager
        self.analyzer = CodeAnalyzer()
    
    # ============================================================================
    # UPDATE FUNCTION - Replace single function in file
    # ============================================================================
    
    def update_function(self, filepath: str, function_name: str, 
                       new_implementation: str) -> Dict:
        """
        Update ONLY a specific function without touching rest of file
        
        Args:
            filepath: Path to file (e.g., "app.py")
            function_name: Name of function to update (e.g., "login")
            new_implementation: New function code
        
        Returns:
            {"success": True, "changes": {...}}
        
        Example:
            new_code = '''def login(username, password):
                return authenticate(username, password)
            '''
            editor.update_function("auth.py", "login", new_code)
        """
        
        # Read current file using YOUR FileSystem
        result = self.fs.read_file(filepath)
        if not result['success']:
            return result
        
        code = result['content']
        lines = code.split('\n')
        
        # Parse code to find the function
        elements = self.analyzer.parse_python(code)
        func = self.analyzer.find_element(elements, function_name)
        
        if not func:
            return {
                "success": False,
                "error": f"Function '{function_name}' not found in {filepath}"
            }
        
        # Preserve original indentation
        new_lines = new_implementation.split('\n')
        indent = ' ' * func.indentation
        indented_new = '\n'.join(
            indent + line if line.strip() else line 
            for line in new_lines
        )
        
        # Replace ONLY the function (keep everything else)
        new_code_lines = (
            lines[:func.start_line] +      # Everything before function
            [indented_new] +                # New function
            lines[func.end_line:]           # Everything after function
        )
        
        new_code = '\n'.join(new_code_lines)
        
        # Write back using YOUR FileSystem
        write_result = self.fs.write_file(filepath, new_code)
        
        if write_result['success']:
            return {
                "success": True,
                "changes": {
                    "function": function_name,
                    "lines_replaced": func.end_line - func.start_line,
                    "file": filepath
                }
            }
        
        return write_result
    
    # ============================================================================
    # ADD METHOD TO CLASS - Add new method to existing class
    # ============================================================================
    
    def add_method_to_class(self, filepath: str, class_name: str, 
                           method_code: str) -> Dict:
        """
        Add new method to existing class
        
        Args:
            filepath: File containing the class
            class_name: Name of class
            method_code: New method code
        
        Returns:
            {"success": True}
        
        Example:
            method = '''def get_email(self):
                return f"{self.username}@example.com"
            '''
            editor.add_method_to_class("models.py", "User", method)
        """
        
        result = self.fs.read_file(filepath)
        if not result['success']:
            return result
        
        code = result['content']
        lines = code.split('\n')
        
        # Find the class
        elements = self.analyzer.parse_python(code)
        cls = self.analyzer.find_element(elements, class_name)
        
        if not cls:
            return {"success": False, "error": f"Class '{class_name}' not found"}
        
        # Insert method at end of class
        insert_at = cls.end_line - 1
        
        # Add proper indentation (class level + 4 spaces)
        indent = ' ' * (cls.indentation + 4)
        method_lines = [
            indent + line if line.strip() else line 
            for line in method_code.split('\n')
        ]
        
        # Insert into code
        new_code_lines = (
            lines[:insert_at] +
            [''] +                  # Blank line before method
            method_lines +
            lines[insert_at:]
        )
        
        return self.fs.write_file(filepath, '\n'.join(new_code_lines))
    
    # ============================================================================
    # ADD IMPORT - Add import if not exists
    # ============================================================================
    
    def add_import(self, filepath: str, import_statement: str) -> Dict:
        """
        Add import statement to file (only if not already present)
        
        Args:
            filepath: File path
            import_statement: Import line (e.g., "import json")
        
        Returns:
            {"success": True, "skipped": False}
        
        Example:
            editor.add_import("app.py", "import json")
            editor.add_import("app.py", "from flask import Flask")
        """
        
        result = self.fs.read_file(filepath)
        if not result['success']:
            return result
        
        code = result['content']
        
        # Check if import already exists
        if import_statement in code:
            return {
                "success": True,
                "skipped": True,
                "message": "Import already exists"
            }
        
        lines = code.split('\n')
        
        # Find where to insert (after other imports)
        insert_at = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')):
                insert_at = i + 1
            elif line.strip() and not line.strip().startswith('#'):
                # Found first non-import, non-comment line
                break
        
        # Insert import
        lines.insert(insert_at, import_statement)
        
        return self.fs.write_file(filepath, '\n'.join(lines))
    
    # ============================================================================
    # RENAME FUNCTION - Rename function and all its calls
    # ============================================================================
    
    def rename_function(self, filepath: str, old_name: str, new_name: str) -> Dict:
        """
        Rename function definition AND all its calls in the file
        
        Args:
            filepath: File path
            old_name: Current function name
            new_name: New function name
        
        Returns:
            {"success": True, "changes": {"definitions": 1, "calls": 5}}
        
        Example:
            editor.rename_function("app.py", "authenticate", "login_user")
        """
        
        result = self.fs.read_file(filepath)
        if not result['success']:
            return result
        
        code = result['content']
        
        # Replace function definition: def old_name( -> def new_name(
        def_pattern = rf'\bdef {re.escape(old_name)}\b'
        def_count = len(re.findall(def_pattern, code))
        
        if def_count == 0:
            return {"success": False, "error": f"Function '{old_name}' not found"}
        
        new_code = re.sub(def_pattern, f'def {new_name}', code)
        
        # Replace all function calls: old_name( -> new_name(
        call_pattern = rf'\b{re.escape(old_name)}\('
        call_count = len(re.findall(call_pattern, code))
        new_code = re.sub(call_pattern, f'{new_name}(', new_code)
        
        result = self.fs.write_file(filepath, new_code)
        
        if result['success']:
            result['changes'] = {
                "definitions_renamed": def_count,
                "calls_updated": call_count
            }
        
        return result


# ================================================================================
# DEMO - How to use
# ================================================================================

if __name__ == "__main__":
    # Import YOUR FileSystem
    from ailibrarys.file_access import FileSystem
    
    print("="*70)
    print("Smart Code Editor Demo")
    print("="*70)
    
    # Setup using YOUR FileSystem
    fs = FileSystem(workspace_root="./test_editor")
    editor = SmartCodeEditor(fs)
    
    # Create a test file
    original_code = '''import os

def greet(name):
    """Say hello"""
    return f"Hello, {name}"

def calculate(x, y):
    """Add numbers"""
    return x + y

class User:
    def __init__(self, name):
        self.name = name
    
    def display(self):
        return self.name
'''
    
    fs.write_file("example.py", original_code)
    print("✓ Created test file\n")
    
    # Test 1: Update single function
    print("[Test 1] Update function 'greet'...")
    new_greet = '''def greet(name):
    """Enhanced greeting"""
    from datetime import datetime
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good evening"
    return f"{greeting}, {name}!"
'''
    
    result = editor.update_function("example.py", "greet", new_greet)
    print(f"  Success: {result['success']}")
    if result['success']:
        print(f"  Lines changed: {result['changes']['lines_replaced']}")
    
    # Test 2: Add method to class
    print("\n[Test 2] Add method to User class...")
    new_method = '''def get_email(self):
    """Get user email"""
    return f"{self.name.lower()}@example.com"
'''
    
    result = editor.add_method_to_class("example.py", "User", new_method)
    print(f"  Success: {result['success']}")
    
    # Test 3: Add import
    print("\n[Test 3] Add import...")
    result = editor.add_import("example.py", "import json")
    print(f"  Success: {result['success']}")
    print(f"  Skipped: {result.get('skipped', False)}")
    
    # Test 4: Rename function
    print("\n[Test 4] Rename function...")
    result = editor.rename_function("example.py", "calculate", "add_numbers")
    print(f"  Success: {result['success']}")
    if result['success'] and 'changes' in result:
        print(f"  Changes: {result['changes']}")
    
    # Show final result
    print("\n[Final Code]")
    final = fs.read_file("example.py")
    print(final['content'])
    
    print("\n" + "="*70)
    print("✓ Smart Code Editor working with YOUR FileSystem!")
    print("="*70)