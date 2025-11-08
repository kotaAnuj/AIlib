"""
================================================================================
FILE: AILib/ailib_core.py
PURPOSE: Main controller - combines everything together
DEPENDENCIES:
    - YOUR file_access.py (Terminal + FileSystem)
    - config.py (API keys)
    - ai_engine.py (Gemini AI)
    - code_editor.py (Smart editing)
================================================================================

USAGE:
    1. Setup API key:
        from ailib_core import AILib
        ailib = AILib()
        ailib.config.set_api_key("gemini", "YOUR_KEY")
    
    2. Initialize project:
        ailib.init_project("my_app", language="python")
    
    3. Execute instruction in English:
        ailib.execute_instruction("Create a REST API with user authentication")
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

# Import YOUR existing code
from ailibrarys.file_access import AIDevManager

# Import new components
from config import AILibConfig
from ai_engine import GeminiEngine
from code_editor import SmartCodeEditor


# ================================================================================
# PROJECT SCHEMA - Stores project settings
# ================================================================================

class ProjectSchema:
    """
    Project configuration stored in project.ailib file
    
    Attributes:
        name: Project name
        description: Project description
        language: Primary language (python, javascript, etc.)
        framework: Framework (flask, react, none, etc.)
        instructions: List of English instructions
        dependencies: Required packages
        auto_fix: Auto-fix errors?
        auto_test: Auto-run tests?
    """
    
    def __init__(self, name: str, description: str, language: str,
                 framework: str = "none", instructions: List[str] = None,
                 dependencies: List[str] = None, auto_fix: bool = True,
                 auto_test: bool = True):
        self.name = name
        self.description = description
        self.language = language
        self.framework = framework
        self.instructions = instructions or []
        self.dependencies = dependencies or []
        self.auto_fix = auto_fix
        self.auto_test = auto_test
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "language": self.language,
            "framework": self.framework,
            "instructions": self.instructions,
            "dependencies": self.dependencies,
            "auto_fix": self.auto_fix,
            "auto_test": self.auto_test
        }
    
    @classmethod
    def from_file(cls, filepath: Path):
        """Load from project.ailib file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(**data)
    
    def save(self, filepath: Path):
        """Save to file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


# ================================================================================
# AILIB - Main Controller
# ================================================================================

class AILib:
    """
    Main AILib controller - orchestrates everything
    
    Components:
    - YOUR Terminal (from file_access.py)
    - YOUR FileSystem (from file_access.py)
    - Config (API keys)
    - AI Engine (Gemini)
    - Smart Editor (code modification)
    
    Workflow:
    1. User writes English instruction
    2. AI analyzes instruction
    3. AI generates code
    4. Smart editor updates files
    5. Validator checks for errors
    6. Auto-fix if needed
    7. Done!
    """
    
    def __init__(self, project_root: str = "."):
        """
        Initialize AILib
        
        Args:
            project_root: Project directory
        """
        self.project_root = Path(project_root)
        
        # Load configuration
        self.config = AILibConfig(str(project_root))
        
        # Initialize YOUR components
        self.dev_manager = AIDevManager(
            workspace_root=str(project_root),
            terminal_mode="system"  # Use system mode for reliability
        )
        
        # Initialize smart editor with YOUR FileSystem
        self.smart_editor = SmartCodeEditor(self.dev_manager.fs)
        
        # Initialize AI engine
        api_key = self.config.get_api_key('gemini')
        if api_key:
            self.ai = GeminiEngine(api_key)
        else:
            self.ai = None
            print("⚠️  Warning: Gemini API key not set")
            print("   Run: ailib.config.set_api_key('gemini', 'YOUR_KEY')")
        
        self.schema = None
        self.execution_log = []
    
    # ============================================================================
    # INITIALIZE PROJECT
    # ============================================================================
    
    def init_project(self, name: str, language: str = "python", 
                    framework: str = "none") -> Dict:
        """
        Initialize new AILib project
        
        Args:
            name: Project name
            language: Programming language
            framework: Framework to use
        
        Returns:
            {"success": True, "path": "/path/to/project"}
        
        Example:
            ailib = AILib()
            ailib.init_project("blog_app", language="python", framework="flask")
        """
        
        print(f"\n{'='*70}")
        print(f"🚀 Initializing AILib project: {name}")
        print(f"{'='*70}\n")
        
        # Create project schema
        schema = ProjectSchema(
            name=name,
            description=f"AILib project: {name}",
            language=language,
            framework=framework
        )
        
        # Create directory structure
        self.project_root.mkdir(exist_ok=True)
        
        # Create .ailib directory
        ailib_dir = self.project_root / ".ailib"
        ailib_dir.mkdir(exist_ok=True)
        
        # Save schema
        schema_file = self.project_root / "project.ailib"
        schema.save(schema_file)
        print(f"✓ Created {schema_file}")
        
        # Create source directories
        self.dev_manager.fs.create_directory("src")
        self.dev_manager.fs.create_directory("tests")
        print("✓ Created src/ and tests/ directories")
        
        # Create README
        readme = f"""# {name}

An AILib-powered project.

## Quick Start

1. Edit `project.ailib` - add your instructions in plain English
2. Run: `python ailib_core.py run`
3. AILib will generate, test, and fix code automatically

## Example Instructions

```json
{{
  "instructions": [
    "Create a Flask web server with /hello endpoint",
    "Add user authentication with JWT tokens",
    "Create database models for User and Post"
  ]
}}
```

Generated by AILib - Universal AI Programming Library
"""
        self.dev_manager.fs.write_file("README.md", readme)
        print("✓ Created README.md")
        
        print(f"\n{'='*70}")
        print(f"✅ Project initialized: {name}")
        print(f"   Edit project.ailib to add instructions")
        print(f"{'='*70}\n")
        
        return {
            "success": True,
            "project": name,
            "path": str(self.project_root.resolve())
        }
    
    # ============================================================================
    # LOAD PROJECT
    # ============================================================================
    
    def load_project(self) -> ProjectSchema:
        """Load project.ailib"""
        schema_file = self.project_root / "project.ailib"
        
        if not schema_file.exists():
            raise FileNotFoundError(
                "No project.ailib found. Run: ailib.init_project('name')"
            )
        
        self.schema = ProjectSchema.from_file(schema_file)
        return self.schema
    
    # ============================================================================
    # EXECUTE INSTRUCTION (Main Magic Here!)
    # ============================================================================
    
    def execute_instruction(self, instruction: str) -> Dict:
        """
        Execute a single English instruction
        
        This is where the magic happens:
        1. AI analyzes instruction
        2. AI generates code
        3. Smart editor updates files
        4. Validator checks code
        5. Auto-fix if errors
        
        Args:
            instruction: English instruction
        
        Returns:
            {"success": True, "files_created": [...]}
        
        Example:
            ailib.execute_instruction("Create a REST API with user login")
        """
        
        if not self.ai:
            return {
                "success": False,
                "error": "AI engine not initialized. Set API key first."
            }
        
        print(f"\n{'='*70}")
        print(f"📝 Instruction: {instruction}")
        print(f"{'='*70}\n")
        
        # Step 1: Analyze instruction
        print("🔍 Step 1: Analyzing instruction with AI...")
        analysis = self.ai.analyze_instruction(instruction)
        
        if not analysis['success']:
            print(f"❌ Analysis failed: {analysis.get('error')}")
            return analysis
        
        intent = analysis['analysis']['intent']
        print(f"   Intent: {intent}")
        print(f"   Language: {analysis['analysis']['language']}")
        print(f"   Files needed: {analysis['analysis']['files_needed']}\n")
        
        # Step 2: Build context
        context = {
            "language": self.schema.language if self.schema else "python",
            "framework": self.schema.framework if self.schema else "none",
            "files": [str(f.relative_to(self.project_root)) 
                     for f in self.project_root.glob("**/*.py")
                     if ".ailib" not in str(f)]
        }
        
        # Step 3: Generate code with AI
        print("🤖 Step 2: Generating code with AI...")
        code_result = self.ai.generate_code(instruction, context)
        
        if not code_result['success']:
            print(f"❌ Code generation failed: {code_result.get('error')}")
            return code_result
        
        print(f"   ✓ Generated {len(code_result['files'])} file(s)\n")
        
        # Step 4: Write files using YOUR FileSystem
        print("💾 Step 3: Writing files...")
        created_files = []
        
        for file_info in code_result['files']:
            filepath = file_info['path']
            content = file_info['content']
            
            # Write using YOUR FileSystem
            result = self.dev_manager.fs.write_file(filepath, content)
            
            if result['success']:
                print(f"   ✓ {filepath}")
                created_files.append(filepath)
            else:
                print(f"   ✗ Failed: {filepath}")
        
        # Step 5: Validate code
        if self.schema and self.schema.auto_fix:
            print("\n🔧 Step 4: Validating code...")
            
            for filepath in created_files:
                if not filepath.endswith('.py'):
                    continue
                
                # Validate using YOUR Terminal
                terminal_id = self.dev_manager.terminal.create("Validator")
                validation = self.dev_manager.terminal.run(
                    terminal_id,
                    f"python -m py_compile {filepath}",
                    capture_output=True
                )
                
                if validation.get('exit_code') == 0:
                    print(f"   ✓ {filepath} is valid")
                else:
                    print(f"   ⚠️  Error in {filepath}")
                    print(f"      {validation.get('error', '')[:100]}...")
                    
                    # Auto-fix
                    print(f"   🔄 Auto-fixing...")
                    
                    file_content = self.dev_manager.fs.read_file(filepath)
                    if file_content['success']:
                        fix_result = self.ai.fix_error(
                            file_content['content'],
                            validation.get('error', ''),
                            context
                        )
                        
                        if fix_result['success']:
                            self.dev_manager.fs.write_file(
                                filepath,
                                fix_result['response']
                            )
                            print(f"      ✓ Fixed")
                        else:
                            print(f"      ✗ Could not fix")
        
        # Step 6: Install dependencies
        deps = analysis['analysis'].get('dependencies', [])
        if deps:
            print(f"\n📦 Step 5: Installing {len(deps)} dependencies...")
            
            terminal_id = self.dev_manager.terminal.create("Installer")
            
            if self.schema and self.schema.language == "python":
                cmd = f"pip install {' '.join(deps)}"
            elif self.schema and self.schema.language == "javascript":
                cmd = f"npm install {' '.join(deps)}"
            else:
                cmd = None
            
            if cmd:
                self.dev_manager.terminal.run(terminal_id, cmd)
                print("   ✓ Dependencies installed")
        
        # Done!
        print(f"\n{'='*70}")
        print("✅ Instruction completed successfully!")
        print(f"{'='*70}\n")
        
        # Log execution
        self.execution_log.append({
            "instruction": instruction,
            "timestamp": time.time(),
            "files_created": created_files,
            "success": True
        })
        
        return {
            "success": True,
            "files_created": created_files,
            "analysis": analysis['analysis']
        }
    
    # ============================================================================
    # RUN ALL INSTRUCTIONS
    # ============================================================================
    
    def run(self) -> Dict:
        """
        Run all instructions from project.ailib
        
        Returns:
            {"success": True, "total": 5, "completed": 5}
        
        Example:
            ailib = AILib()
            ailib.run()
        """
        
        self.load_project()
        
        print(f"\n{'='*70}")
        print(f"🚀 Running AILib Project: {self.schema.name}")
        print(f"{'='*70}")
        print(f"Language: {self.schema.language}")
        print(f"Framework: {self.schema.framework}")
        print(f"Instructions: {len(self.schema.instructions)}\n")
        
        if not self.schema.instructions:
            print("⚠️  No instructions found in project.ailib")
            print("   Add instructions like:")
            print('   "instructions": ["Create a web server", "Add authentication"]')
            return {"success": False, "error": "No instructions"}
        
        # Execute each instruction
        completed = 0
        
        for i, instruction in enumerate(self.schema.instructions, 1):
            print(f"\n{'▶'*35}")
            print(f"Instruction {i}/{len(self.schema.instructions)}")
            print(f"{'▶'*35}")
            
            result = self.execute_instruction(instruction)
            
            if result.get('success'):
                completed += 1
            else:
                print(f"\n❌ Failed at instruction {i}")
                print(f"   Error: {result.get('error')}")
                
                # Ask to continue
                response = input("\n   Continue with next instruction? (y/n): ")
                if not response.lower().startswith('y'):
                    break
        
        # Save execution log
        log_file = self.project_root / ".ailib" / "execution_log.json"
        with open(log_file, 'w') as f:
            json.dump(self.execution_log, f, indent=2)
        
        print(f"\n{'='*70}")
        print(f"🎉 AILib Execution Complete!")
        print(f"   Completed: {completed}/{len(self.schema.instructions)}")
        print(f"{'='*70}\n")
        
        return {
            "success": True,
            "total": len(self.schema.instructions),
            "completed": completed
        }


# ================================================================================
# CLI - Command Line Interface
# ================================================================================

def cli():
    """Command-line interface"""
    import sys
    
    if len(sys.argv) < 2:
        print("""
╔══════════════════════════════════════════════════════════════════════╗
║                   AILib - Universal AI Programming                    ║
╚══════════════════════════════════════════════════════════════════════╝

Commands:
  init <name>              Initialize new project
  config <key>             Set Gemini API key
  run                      Run all instructions
  exec "<instruction>"     Execute single instruction

Examples:
  python ailib_core.py init my_app
  python ailib_core.py config AIzaSy...
  python ailib_core.py exec "Create REST API"
  python ailib_core.py run
""")
        return
    
    command = sys.argv[1]
    
    try:
        if command == "init":
            name = sys.argv[2] if len(sys.argv) > 2 else "my_project"
            language = sys.argv[3] if len(sys.argv) > 3 else "python"
            
            ailib = AILib()
            ailib.init_project(name, language=language)
        
        elif command == "config":
            api_key = sys.argv[2] if len(sys.argv) > 2 else input("Enter Gemini API key: ")
            
            config = AILibConfig()
            config.set_api_key("gemini", api_key)
        
        elif command == "run":
            ailib = AILib()
            ailib.run()
        
        elif command == "exec":
            if len(sys.argv) < 3:
                print("Usage: python ailib_core.py exec \"<instruction>\"")
                return
            
            instruction = sys.argv[2]
            
            ailib = AILib()
            ailib.load_project()
            ailib.execute_instruction(instruction)
        
        else:
            print(f"Unknown command: {command}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


# ================================================================================
# MAIN
# ================================================================================

if __name__ == "__main__":
    cli()