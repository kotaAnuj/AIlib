"""
================================================================================
FILE: AILib/ailib_core.py (FULLY UPGRADED v4.0 - SCHEMA-AWARE)
PURPOSE: Complete self-managing AI development system with English programming
NEW FEATURES:
  - Schema file creation and editing in UI
  - Real-time code preview
  - English-to-code conversion interface
  - Multi-language schema templates
  - Live syntax validation
  - Generated code viewer
================================================================================
"""

import json
import re
import time
import threading
import secrets
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from flask import Flask, render_template_string, request, jsonify, session
from flask_cors import CORS
from pynput import keyboard

# Import upgraded modules
from ailibrarys.file_access import AIDevManager
from config import AILibConfig
from ai_engine import GeminiEngine
from code_editor import SmartCodeEditor


# ============================================================================
# KEYBOARD LISTENER - Detect Shift+Enter
# ============================================================================

class ShiftEnterListener:
    """Listens for Shift+Enter key combination"""
    
    def __init__(self, on_trigger_callback):
        self.on_trigger_callback = on_trigger_callback
        self.shift_pressed = False
        self.listener = None
        self.active = False
    
    def start(self):
        self.active = True
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()
        print("⌨️  Keyboard listener started - Press Shift+Enter to trigger AI")
    
    def stop(self):
        self.active = False
        if self.listener:
            self.listener.stop()
        print("⌨️  Keyboard listener stopped")
    
    def _on_press(self, key):
        if not self.active:
            return
        
        try:
            if key == keyboard.Key.shift or key == keyboard.Key.shift_r:
                self.shift_pressed = True
            elif key == keyboard.Key.enter and self.shift_pressed:
                print("\n⚡ Shift+Enter detected! Triggering AI update...")
                threading.Thread(target=self.on_trigger_callback, daemon=True).start()
        except AttributeError:
            pass
    
    def _on_release(self, key):
        try:
            if key == keyboard.Key.shift or key == keyboard.Key.shift_r:
                self.shift_pressed = False
        except AttributeError:
            pass


# ============================================================================
# PROJECT MANAGER - Enhanced for schema projects
# ============================================================================

class ProjectManager:
    """Manages project initialization and configuration"""
    
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.config_file = self.workspace_root / ".ailib" / "project.json"
    
    def initialize_project(self, name: str, language: str, framework: str, description: str = "") -> Dict:
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        
        project_config = {
            "name": name,
            "description": description,
            "language": language,
            "framework": framework,
            "created": time.time(),
            "version": "1.0.0",
            "status": "initialized",
            "schema_mode": True  # NEW: Enable schema mode
        }
        
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(project_config, f, indent=2)
        
        return {
            "success": True,
            "project": project_config,
            "path": str(self.workspace_root)
        }
    
    def load_project(self) -> Optional[Dict]:
        if not self.config_file.exists():
            return None
        with open(self.config_file, 'r') as f:
            return json.load(f)
    
    def update_status(self, status: str):
        project = self.load_project()
        if project:
            project["status"] = status
            project["last_updated"] = time.time()
            with open(self.config_file, 'w') as f:
                json.dump(project, f, indent=2)


# ============================================================================
# SCHEMA TEMPLATE MANAGER - Provides example schemas
# ============================================================================

class SchemaTemplateManager:
    """Manages schema templates for different use cases"""
    
    @staticmethod
    def get_templates() -> Dict[str, Dict]:
        return {
            "calculator": {
                "name": "Simple Calculator",
                "description": "Basic calculator with multiple operations",
                "content": """file: calculator.py
version: 3.13
dependencies: none

step1: take two numbers as input
    input: a, b
    prompt user for numbers

step2: ask user for operation
    options: add, subtract, multiply, divide
    get user choice

step3: perform calculation
    if add: result = a + b
    if subtract: result = a - b
    if multiply: result = a * b
    if divide: result = a / b (check b != 0)

step4: display result
    print the result
    format nicely
"""
            },
            "file_processor": {
                "name": "File Processor",
                "description": "Read and process text files",
                "content": """file: file_processor.py
version: 3.13
dependencies: os, pathlib

step1: get filename from user
    input: filename
    validate file exists

step2: read file contents
    open file in read mode
    store contents in variable

step3: process contents
    count lines
    count words
    count characters

step4: display statistics
    print total lines
    print total words
    print total characters
"""
            },
            "web_scraper": {
                "name": "Web Scraper",
                "description": "Simple web scraping tool",
                "content": """file: scraper.py
version: 3.13
dependencies: requests, beautifulsoup4

step1: get URL from user
    input: url
    validate URL format

step2: fetch webpage
    use requests.get
    handle connection errors

step3: parse HTML
    use BeautifulSoup
    extract all links
    extract all headings

step4: save results
    write to output file
    format as JSON
"""
            },
            "data_analyzer": {
                "name": "Data Analyzer",
                "description": "Analyze CSV data",
                "content": """file: analyzer.py
version: 3.13
dependencies: pandas, matplotlib

step1: load CSV file
    input: filename
    read using pandas

step2: calculate statistics
    mean, median, mode
    standard deviation
    min and max values

step3: create visualization
    generate histogram
    create bar chart
    save as PNG

step4: export report
    save statistics to file
    include chart image
"""
            },
            "api_client": {
                "name": "REST API Client",
                "description": "Make API requests and handle responses",
                "content": """file: api_client.py
version: 3.13
dependencies: requests, json

step1: setup API configuration
    base_url: https://api.example.com
    headers: Authorization, Content-Type

step2: create request function
    input: endpoint, method, data
    build full URL
    add headers

step3: make request
    send HTTP request
    handle timeout
    catch errors

step4: process response
    parse JSON
    validate status code
    return data
"""
            },
            "game": {
                "name": "Number Guessing Game",
                "description": "Simple interactive game",
                "content": """file: game.py
version: 3.13
dependencies: random

step1: generate random number
    range: 1 to 100
    store secret number

step2: game loop
    get user guess
    validate input is number

step3: check guess
    if too high: tell user
    if too low: tell user
    if correct: congratulate and exit

step4: track attempts
    count number of guesses
    display final score
"""
            }
        }
    
    @staticmethod
    def get_template(template_id: str) -> Optional[str]:
        templates = SchemaTemplateManager.get_templates()
        return templates.get(template_id, {}).get("content")


# ============================================================================
# UPGRADED AILIB - Schema-Aware System
# ============================================================================

class UpgradedAILib:
    """Complete self-managing AI development system with English programming"""
    
    def __init__(self, workspace_root: str = "./workspace"):
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(exist_ok=True)
        
        self.config = AILibConfig(str(self.workspace_root))
        self.project_manager = ProjectManager(str(self.workspace_root))
        self.ai = None
        
        self.dev_manager = AIDevManager(
            workspace_root=str(self.workspace_root / "src"),
            terminal_mode="system"
        )
        
        self.smart_editor = SmartCodeEditor(self.dev_manager.fs)
        self.keyboard_listener = None
        
        self.status = {
            "initialized": False,
            "ai_ready": False,
            "watching": False,
            "pending_changes": 0,
            "last_trigger": None,
            "schema_mode": True  # NEW
        }
        
        self.activity_log = []
        self.generated_files = {}  # NEW: Track schema → generated code mapping
    
    def _log_activity(self, message: str, type: str = "info"):
        self.activity_log.append({
            "timestamp": time.time(),
            "message": message,
            "type": type
        })
        if len(self.activity_log) > 50:
            self.activity_log = self.activity_log[-50:]
    
    def is_ready(self) -> Tuple[bool, str]:
        if not self.ai:
            return False, "API key not set"
        project = self.project_manager.load_project()
        if not project:
            return False, "Project not initialized"
        return True, "Ready"
    
    def set_api_key(self, api_key: str) -> Dict:
        try:
            self.config.set_api_key('gemini', api_key)
            src_path = self.workspace_root / "src"
            self.ai = GeminiEngine(api_key, workspace_root=str(src_path), enable_cache=True)
            
            self.status["ai_ready"] = True
            self._log_activity("✅ API key configured and AI engine initialized", "success")
            
            return {"success": True, "message": "API key configured successfully"}
        except Exception as e:
            self._log_activity(f"❌ Failed to configure API key: {str(e)}", "error")
            return {"success": False, "error": str(e)}
    
    def initialize_project(self, name: str, language: str, framework: str, description: str = "") -> Dict:
        if not self.ai:
            return {"success": False, "error": "API key not set"}
        
        try:
            result = self.project_manager.initialize_project(name, language, framework, description)
            if not result["success"]:
                return result
            
            env_result = self.ai.setup_environment(language)
            if not env_result["success"]:
                return env_result
            
            self.status["initialized"] = True
            self._log_activity(f"✅ Project '{name}' initialized with {language}/{framework}", "success")
            
            self.start_watching()
            self.start_keyboard_listener()
            
            return {
                "success": True,
                "project": result["project"],
                "structure": env_result["structure"],
                "path": str(self.workspace_root)
            }
        except Exception as e:
            self._log_activity(f"❌ Project initialization failed: {str(e)}", "error")
            return {"success": False, "error": str(e)}
    
    def start_watching(self):
        if not self.ai:
            return
        self.ai.start_watching()
        self.status["watching"] = True
        self._log_activity("👁️  File watching started (including schema files)", "info")
    
    def stop_watching(self):
        if self.ai:
            self.ai.stop_watching()
        self.status["watching"] = False
        self._log_activity("🛑 File watching stopped", "info")
    
    def start_keyboard_listener(self):
        if self.keyboard_listener:
            return
        self.keyboard_listener = ShiftEnterListener(self._on_shift_enter_pressed)
        self.keyboard_listener.start()
        self._log_activity("⌨️  Keyboard listener started (Shift+Enter to trigger)", "info")
    
    def stop_keyboard_listener(self):
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
            self._log_activity("⌨️  Keyboard listener stopped", "info")
    
    def _on_shift_enter_pressed(self):
        self._log_activity("⚡ Shift+Enter pressed - triggering AI update...", "info")
        result = self.trigger_ai_update()
        
        if result["success"]:
            self._log_activity(
                f"✅ AI update complete - {result.get('files_processed', 0)} file(s) processed",
                "success"
            )
        else:
            self._log_activity(
                f"⚠️  {result.get('message', 'No changes')}",
                "warning"
            )
    
    def trigger_ai_update(self) -> Dict:
        """Trigger AI to process pending changes (schema or code)"""
        if not self.ai:
            return {"success": False, "error": "AI not initialized"}
        
        self.status["last_trigger"] = time.time()
        result = self.ai.trigger_update()
        
        # Track generated files
        if result.get("success") and result.get("results"):
            for res in result["results"]:
                if res.get("type") == "schema_generation":
                    schema_file = res.get("schema_file")
                    generated_file = res.get("generated_file")
                    self.generated_files[schema_file] = {
                        "generated": generated_file,
                        "timestamp": time.time(),
                        "language": res.get("language")
                    }
        
        return result
    
    def get_pending_changes(self) -> List[Dict]:
        if not self.ai:
            return []
        return self.ai.file_watcher.get_pending_changes()
    
    def create_schema_file(self, filename: str, content: str) -> Dict:
        """NEW: Create a schema file in workspace"""
        try:
            filepath = f"src/{filename}"
            result = self.dev_manager.fs.write_file(filepath, content)
            
            if result["success"]:
                self._log_activity(f"📝 Created schema file: {filename}", "success")
                return {
                    "success": True,
                    "file": filepath,
                    "message": f"Schema file '{filename}' created successfully"
                }
            return result
        except Exception as e:
            self._log_activity(f"❌ Failed to create schema: {str(e)}", "error")
            return {"success": False, "error": str(e)}
    
    def read_schema_file(self, filename: str) -> Dict:
        """NEW: Read a schema file"""
        try:
            filepath = f"src/{filename}"
            result = self.dev_manager.fs.read_file(filepath)
            
            if result["success"]:
                # Parse the schema
                if self.ai:
                    parsed = self.ai.schema_parser.parse_schema_file(result["content"])
                    result["parsed_schema"] = parsed
            
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_generated_code(self, schema_file: str) -> Dict:
        """NEW: Get code generated from schema file"""
        if schema_file in self.generated_files:
            gen_info = self.generated_files[schema_file]
            generated_file = gen_info["generated"]
            
            result = self.dev_manager.fs.read_file(f"src/{generated_file}")
            if result["success"]:
                result["generation_info"] = gen_info
                return result
        
        return {"success": False, "error": "No generated code found"}
    
    def list_schema_files(self) -> List[Dict]:
        """NEW: List all schema files in workspace"""
        result = self.dev_manager.fs.list_directory("src", pattern="**/*")
        
        if not result["success"]:
            return []
        
        schema_files = []
        
        for file_info in result.get("files", []):
            filepath = file_info["path"]
            
            # Read file and check if it's a schema
            read_result = self.dev_manager.fs.read_file(filepath)
            if read_result["success"]:
                content = read_result["content"]
                
                # Quick check for schema format
                if any(indicator in content for indicator in ['file:', 'step1:', 'step2:']):
                    schema_files.append({
                        "name": file_info["name"],
                        "path": filepath,
                        "size": file_info["size"],
                        "has_generated": filepath in self.generated_files
                    })
        
        return schema_files
    
    def execute_instruction(self, instruction: str) -> Dict:
        """Execute natural language instruction (existing functionality)"""
        if not self.ai:
            return {"success": False, "error": "AI not initialized"}
        
        ready, msg = self.is_ready()
        if not ready:
            return {"success": False, "error": msg}
        
        self._log_activity(f"📝 Executing: {instruction[:100]}...", "info")
        
        try:
            # This uses the existing code generation (not schema-based)
            analysis = self.ai.analyze_instruction(instruction)
            
            if not analysis.get("success"):
                return analysis
            
            intent = analysis["analysis"]
            context = {
                "language": intent.get("language", "python"),
                "framework": intent.get("framework", "none"),
                "files": intent.get("files_needed", [])
            }
            
            # Note: This needs to be implemented in ai_engine.py
            # For now, return a placeholder
            return {
                "success": False,
                "error": "Use schema files for code generation. Click 'Create Schema' tab."
            }
        
        except Exception as e:
            self._log_activity(f"❌ Instruction failed: {str(e)}", "error")
            return {"success": False, "error": str(e)}
    
    def get_status(self) -> Dict:
        pending = self.get_pending_changes()
        self.status["pending_changes"] = len(pending)
        
        ai_stats = {}
        if self.ai:
            ai_stats = self.ai.get_statistics()
        
        project = self.project_manager.load_project()
        tree = self.dev_manager.fs.get_tree(max_depth=2)
        
        return {
            "status": self.status,
            "project": project,
            "ai_stats": ai_stats,
            "workspace": str(self.workspace_root),
            "workspace_tree": tree.get("tree", []),
            "activity_log": self.activity_log[-10:],
            "pending_changes": pending,
            "generated_files": self.generated_files
        }
    
    def cleanup(self):
        self.stop_watching()
        self.stop_keyboard_listener()
        if self.ai:
            self.ai.cleanup()
        self._log_activity("🧹 System cleanup complete", "info")


# ============================================================================
# WEB INTERFACE - Flask App with Schema Support
# ============================================================================

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
CORS(app)

ailib_instance = None

# HTML Template (Enhanced with Schema UI)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AILib - English Programming System</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 { 
            font-size: 2.5em; 
            margin-bottom: 10px;
            animation: fadeIn 1s;
        }
        
        .header p { opacity: 0.9; font-size: 1.1em; }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .tabs {
            display: flex;
            background: #f5f5f5;
            border-bottom: 2px solid #ddd;
            overflow-x: auto;
        }
        
        .tab {
            flex: 1;
            min-width: 150px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            background: #f5f5f5;
            border: none;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.3s;
        }
        
        .tab:hover { background: #e0e0e0; }
        
        .tab.active {
            background: white;
            border-bottom: 3px solid #667eea;
            color: #667eea;
        }
        
        .tab-content {
            display: none;
            padding: 30px;
            max-height: calc(100vh - 300px);
            overflow-y: auto;
        }
        
        .tab-content.active {
            display: block;
            animation: slideIn 0.3s;
        }
        
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        
        .section {
            margin-bottom: 30px;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
        }
        
        .section h2 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.5em;
        }
        
        .input-group {
            margin-bottom: 15px;
        }
        
        .input-group label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 600;
        }
        
        input[type="text"],
        input[type="password"],
        select,
        textarea {
            width: 100%;
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 16px;
            transition: border 0.3s;
            font-family: inherit;
        }
        
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        textarea {
            resize: vertical;
            min-height: 150px;
            font-family: 'Courier New', monospace;
        }
        
        button {
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        button:active { transform: translateY(0); }
        button:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        
        .status-box {
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
            font-weight: bold;
            animation: slideDown 0.3s;
        }
        
        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .status-box.success {
            background: #d4edda;
            color: #155724;
            border-left: 4px solid #28a745;
        }
        
        .status-box.error {
            background: #f8d7da;
            color: #721c24;
            border-left: 4px solid #dc3545;
        }
        
        .status-box.info {
            background: #d1ecf1;
            color: #0c5460;
            border-left: 4px solid #17a2b8;
        }
        
        .status-box.warning {
            background: #fff3cd;
            color: #856404;
            border-left: 4px solid #ffc107;
        }
        
        .template-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .template-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            border: 2px solid #ddd;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .template-card:hover {
            border-color: #667eea;
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.2);
        }
        
        .template-card h3 {
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .template-card p {
            color: #666;
            font-size: 0.9em;
        }
        
        .code-preview {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 10px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            overflow-x: auto;
            max-height: 500px;
            overflow-y: auto;
        }
        
        .schema-list {
            list-style: none;
        }
        
        .schema-item {
            background: white;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .schema-item:hover {
            transform: translateX(5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .schema-item .badge {
            display: inline-block;
            padding: 5px 10px;
            background: #28a745;
            color: white;
            border-radius: 5px;
            font-size: 0.8em;
            margin-left: 10px;
        }
        
        .two-column {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        
        @media (max-width: 768px) {
            .two-column { grid-template-columns: 1fr; }
        }
        
        .help-box {
            background: #e8f4f8;
            border-left: 4px solid #17a2b8;
            padding: 15px;
            border-radius: 5px;
            margin-top: 15px;
        }
        
        .help-box h4 {
            color: #0c5460;
            margin-bottom: 10px;
        }
        
        .help-box code {
            background: #fff;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 AILib v4.0</h1>
            <p>English Programming System - Write Code in Plain English</p>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('setup')">⚙️ Setup</button>
            <button class="tab" onclick="showTab('schema')">📝 Create Schema</button>
            <button class="tab" onclick="showTab('my-schemas')">📂 My Schemas</button>
            <button class="tab" onclick="showTab('status')">📊 Status</button>
        </div>
        
        <!-- Setup Tab -->
        <div id="setup-tab" class="tab-content active">
            <div class="section">
                <h2>1️⃣ Configure API Key</h2>
                <div class="input-group">
                    <label>Gemini API Key</label>
                    <input type="password" id="apiKey" placeholder="AIza...">
                </div>
                <button onclick="setApiKey()">Set API Key</button>
                <div id="apiStatus"></div>
            </div>
            
            <div class="section">
                <h2>2️⃣ Initialize Project</h2>
                <div class="input-group">
                    <label>Project Name</label>
                    <input type="text" id="projectName" placeholder="my-english-project">
                </div>
                <div class="input-group">
                    <label>Programming Language</label>
                    <select id="language">
                        <option value="python">Python</option>
                        <option value="javascript">JavaScript</option>
                        <option value="typescript">TypeScript</option>
                        <option value="java">Java</option>
                        <option value="cpp">C++</option>
                        <option value="go">Go</option>
                    </select>
                </div>
                <div class="input-group">
                    <label>Framework</label>
                    <select id="framework">
                        <option value="none">None</option>
                        <option value="flask">Flask</option>
                        <option value="django">Django</option>
                        <option value="react">React</option>
                        <option value="express">Express</option>
                        <option value="spring">Spring</option>
                    </select>
                </div>
                <div class="input-group">
                    <label>Description (Optional)</label>
                    <textarea id="description" rows="3" placeholder="Describe your project..."></textarea>
                </div>
                <button onclick="initializeProject()">Initialize Project</button>
                <div id="projectStatus"></div>
            </div>
            
            <div class="help-box">
                <h4>📖 How to Use AILib</h4>
                <p>1. Set your API key and initialize project</p>
                <p>2. Go to "Create Schema" tab</p>
                <p>3. Choose a template or write your own English instructions</p>
                <p>4. Save the schema file</p>
                <p>5. Press <strong>Shift + Enter</strong> to generate code</p>
                <p>6. Check "My Schemas" tab to see generated code</p>
            </div>
        </div>
        
        <!-- Create Schema Tab -->
        <div id="schema-tab" class="tab-content">
            <div class="section">
                <h2>📝 Create New Schema File</h2>
                
                <div class="input-group">
                    <label>Schema Filename</label>
                    <input type="text" id="schemaFilename" placeholder="my_app_schema.txt">
                </div>
                
                <div class="input-group">
                    <label>Choose Template (Optional)</label>
                    <div class="template-grid" id="templateGrid">
                        <!-- Templates loaded dynamically -->
                    </div>
                </div>
                
                <div class="input-group">
                    <label>Write Your English Instructions</label>
                    <textarea id="schemaContent" rows="20" placeholder="Example:

file: calculator.py
version: 3.13
dependencies: math

step1: take two numbers as input
    input: a, b
    prompt user for numbers

step2: calculate sum
    result = a + b
    
step3: display result
    print the result
"></textarea>
                </div>
                
                <button onclick="createSchema()">💾 Save Schema File</button>
                <button onclick="clearSchema()" style="background: #6c757d;">🗑️ Clear</button>
                <div id="schemaStatus"></div>
            </div>
            
            <div class="help-box">
                <h4>✍️ Schema File Format</h4>
                <p><strong>Metadata (optional):</strong></p>
                <p><code>file: output_filename.py</code> - Target file to generate</p>
                <p><code>version: 3.13</code> - Language version</p>
                <p><code>dependencies: math, numpy</code> - Required packages</p>
                <br>
                <p><strong>Steps (write in English):</strong></p>
                <p><code>step1: what to do</code></p>
                <p><code>    details here</code></p>
                <p><code>    more details</code></p>
                <br>
                <p><strong>Or just write free-form English:</strong></p>
                <p>"take two inputs, sum them, print the output"</p>
            </div>
        </div>
        
        <!-- My Schemas Tab -->
        <div id="my-schemas-tab" class="tab-content">
            <div class="section">
                <h2>📂 Your Schema Files</h2>
                <button onclick="refreshSchemas()">🔄 Refresh</button>
                <div id="schemaList" style="margin-top: 20px;">
                    <!-- Loaded dynamically -->
                </div>
            </div>
            
            <div class="two-column" style="margin-top: 20px;">
                <div class="section">
                    <h2>📝 Schema Content</h2>
                    <div id="selectedSchemaContent" class="code-preview">
                        Select a schema file to view
                    </div>
                </div>
                
                <div class="section">
                    <h2>💻 Generated Code</h2>
                    <div id="generatedCodeContent" class="code-preview">
                        Press Shift+Enter to generate code
                    </div>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 20px;">
                <button class="trigger-button" onclick="triggerAiUpdate()" style="font-size: 1.3em; padding: 20px 50px;">
                    ⚡ Generate Code (Shift+Enter)
                </button>
            </div>
        </div>
        
        <!-- Status Tab -->
        <div id="status-tab" class="tab-content">
            <div class="section">
                <h2>📊 System Status</h2>
                <div class="stats-grid" id="statsGrid">
                    Loading...
                </div>
            </div>
            
            <div class="section">
                <h2>📝 Activity Log</h2>
                <div class="activity-log" id="activityLog">
                    Loading...
                </div>
            </div>
            
            <div class="section">
                <h2>🤖 AI Statistics</h2>
                <div id="aiStats">
                    Loading...
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let currentSelectedSchema = null;
        
        // Tab switching
        function showTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            document.getElementById(tabName + '-tab').classList.add('active');
            event.target.classList.add('active');
            
            if (tabName === 'status') {
                refreshStatus();
            } else if (tabName === 'my-schemas') {
                refreshSchemas();
            } else if (tabName === 'schema') {
                loadTemplates();
            }
        }
        
        // API Key
        async function setApiKey() {
            const apiKey = document.getElementById('apiKey').value;
            if (!apiKey) {
                showStatus('apiStatus', 'Please enter API key', 'error');
                return;
            }
            
            const response = await fetch('/api/set_key', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({api_key: apiKey})
            });
            
            const data = await response.json();
            showStatus('apiStatus', data.message || data.error, data.success ? 'success' : 'error');
        }
        
        // Initialize Project
        async function initializeProject() {
            const name = document.getElementById('projectName').value;
            const language = document.getElementById('language').value;
            const framework = document.getElementById('framework').value;
            const description = document.getElementById('description').value;
            
            if (!name) {
                showStatus('projectStatus', 'Please enter project name', 'error');
                return;
            }
            
            showStatus('projectStatus', 'Initializing project...', 'info');
            
            const response = await fetch('/api/init_project', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    name: name,
                    language: language,
                    framework: framework,
                    description: description
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                let message = `✅ Project initialized!<br>`;
                message += `📁 Location: ${data.path}<br>`;
                message += `📄 Files created:<br>`;
                data.structure.forEach(item => {
                    message += `&nbsp;&nbsp;${item}<br>`;
                });
                message += `<br>🎉 Ready! Go to "Create Schema" tab`;
                showStatus('projectStatus', message, 'success');
            } else {
                showStatus('projectStatus', data.error, 'error');
            }
        }
        
        // Load Templates
        async function loadTemplates() {
            const response = await fetch('/api/templates');
            const data = await response.json();
            
            if (data.success) {
                const grid = document.getElementById('templateGrid');
                grid.innerHTML = '';
                
                for (const [id, template] of Object.entries(data.templates)) {
                    const card = document.createElement('div');
                    card.className = 'template-card';
                    card.innerHTML = `
                        <h3>${template.name}</h3>
                        <p>${template.description}</p>
                    `;
                    card.onclick = () => loadTemplate(id);
                    grid.appendChild(card);
                }
            }
        }
        
        async function loadTemplate(templateId) {
            const response = await fetch(`/api/template/${templateId}`);
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('schemaContent').value = data.content;
                showStatus('schemaStatus', `Template loaded: ${data.name}`, 'success');
            }
        }
        
        // Create Schema
        async function createSchema() {
            const filename = document.getElementById('schemaFilename').value;
            const content = document.getElementById('schemaContent').value;
            
            if (!filename) {
                showStatus('schemaStatus', 'Please enter filename', 'error');
                return;
            }
            
            if (!content) {
                showStatus('schemaStatus', 'Please write schema content', 'error');
                return;
            }
            
            showStatus('schemaStatus', 'Creating schema file...', 'info');
            
            const response = await fetch('/api/create_schema', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    filename: filename,
                    content: content
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showStatus('schemaStatus', 
                    `✅ Schema created: ${filename}<br>Now press Shift+Enter to generate code!`, 
                    'success'
                );
            } else {
                showStatus('schemaStatus', data.error, 'error');
            }
        }
        
        function clearSchema() {
            document.getElementById('schemaContent').value = '';
            document.getElementById('schemaFilename').value = '';
        }
        
        // Refresh Schemas List
        async function refreshSchemas() {
            const response = await fetch('/api/schemas');
            const data = await response.json();
            
            if (data.success) {
                const list = document.getElementById('schemaList');
                
                if (data.schemas.length === 0) {
                    list.innerHTML = '<p style="color: #666;">No schema files yet. Create one in "Create Schema" tab.</p>';
                    return;
                }
                
                list.innerHTML = '<ul class="schema-list">';
                
                data.schemas.forEach(schema => {
                    const li = document.createElement('li');
                    li.className = 'schema-item';
                    li.innerHTML = `
                        📄 ${schema.name}
                        ${schema.has_generated ? '<span class="badge">✓ Generated</span>' : ''}
                    `;
                    li.onclick = () => viewSchema(schema.path);
                    list.querySelector('ul').appendChild(li);
                });
            }
        }
        
        // View Schema
        async function viewSchema(filepath) {
            currentSelectedSchema = filepath;
            
            // Load schema content
            const response = await fetch('/api/read_schema', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({filename: filepath})
            });
            
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('selectedSchemaContent').textContent = data.content;
                
                // Try to load generated code
                const genResponse = await fetch('/api/generated_code', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({schema_file: filepath})
                });
                
                const genData = await genResponse.json();
                
                if (genData.success) {
                    document.getElementById('generatedCodeContent').textContent = genData.content;
                } else {
                    document.getElementById('generatedCodeContent').textContent = 
                        'No generated code yet.\nPress Shift+Enter to generate!';
                }
            }
        }
        
        // Trigger AI Update
        async function triggerAiUpdate() {
            showStatus('schemaStatus', '⚡ Generating code from schemas...', 'info');
            
            const response = await fetch('/api/trigger', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });
            
            const data = await response.json();
            
            if (data.success) {
                let message = `✅ Code generation complete!<br>`;
                message += `📄 Files processed: ${data.files_processed}<br>`;
                
                if (data.results && data.results.length > 0) {
                    message += `<br>Results:<br>`;
                    data.results.forEach(r => {
                        if (r.type === 'schema_generation') {
                            message += `&nbsp;&nbsp;✓ ${r.schema_file} → ${r.generated_file}<br>`;
                        }
                    });
                }
                
                showStatus('schemaStatus', message, 'success');
                
                // Refresh view if schema is selected
                if (currentSelectedSchema) {
                    setTimeout(() => viewSchema(currentSelectedSchema), 1000);
                }
            } else {
                showStatus('schemaStatus', data.message || data.error, 'warning');
            }
        }
        
        // Refresh Status
        async function refreshStatus() {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            if (data.success) {
                const stats = data.status.status || {};
                const aiStats = data.status.ai_stats || {};
                
                let statsHtml = `
                    <div class="stat-card">
                        <div class="stat-label">AI Ready</div>
                        <div class="stat-value">${stats.ai_ready ? '✅' : '❌'}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Watching</div>
                        <div class="stat-value">${stats.watching ? '👁️' : '🔴'}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Schema Mode</div>
                        <div class="stat-value">${stats.schema_mode ? '✅' : '❌'}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Total Requests</div>
                        <div class="stat-value">${aiStats.total_requests || 0}</div>
                    </div>
                `;
                
                document.getElementById('statsGrid').innerHTML = statsHtml;
                
                // Activity log
                const activities = data.status.activity_log || [];
                let activityHtml = '';
                activities.reverse().forEach(activity => {
                    const time = new Date(activity.timestamp * 1000).toLocaleTimeString();
                    activityHtml += `
                        <div class="activity-item ${activity.type}">
                            <div class="activity-time">${time}</div>
                            <div>${activity.message}</div>
                        </div>
                    `;
                });
                document.getElementById('activityLog').innerHTML = activityHtml || 'No activity yet';
                
                // AI stats
                let aiStatsHtml = '<div class="stats-grid">';
                if (aiStats.cache) {
                    aiStatsHtml += `
                        <div class="stat-card">
                            <div class="stat-label">Cache Hit Rate</div>
                            <div class="stat-value">${aiStats.cache.hit_rate}</div>
                        </div>
                    `;
                }
                aiStatsHtml += `
                    <div class="stat-card">
                        <div class="stat-label">Success Rate</div>
                        <div class="stat-value">${aiStats.success_rate || '0%'}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Tokens Used</div>
                        <div class="stat-value">${aiStats.total_tokens_used || 0}</div>
                    </div>
                </div>`;
                
                document.getElementById('aiStats').innerHTML = aiStatsHtml;
            }
        }
        
        // Helper function
        function showStatus(elementId, message, type) {
            const element = document.getElementById(elementId);
            element.innerHTML = `<div class="status-box ${type}">${message}</div>`;
            
            if (type === 'success') {
                setTimeout(() => {
                    element.innerHTML = '';
                }, 5000);
            }
        }
        
        // Auto-refresh
        setInterval(() => {
            const activeTab = document.querySelector('.tab-content.active').id;
            if (activeTab === 'status-tab') {
                refreshStatus();
            }
        }, 5000);
        
        // Load templates on page load
        setTimeout(loadTemplates, 1000);
    </script>
</body>
</html>
"""

# API Routes

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/set_key', methods=['POST'])
def set_api_key():
    global ailib_instance
    data = request.json
    api_key = data.get('api_key')
    
    if not api_key:
        return jsonify({"success": False, "error": "API key required"})
    
    try:
        if ailib_instance is None:
            ailib_instance = UpgradedAILib(workspace_root="./workspace")
        result = ailib_instance.set_api_key(api_key)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/init_project', methods=['POST'])
def init_project():
    global ailib_instance
    if ailib_instance is None:
        return jsonify({"success": False, "error": "Set API key first"})
    
    data = request.json
    name = data.get('name')
    language = data.get('language', 'python')
    framework = data.get('framework', 'none')
    description = data.get('description', '')
    
    if not name:
        return jsonify({"success": False, "error": "Project name required"})
    
    try:
        result = ailib_instance.initialize_project(name, language, framework, description)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/templates', methods=['GET'])
def get_templates():
    try:
        templates = SchemaTemplateManager.get_templates()
        return jsonify({"success": True, "templates": templates})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/template/<template_id>', methods=['GET'])
def get_template(template_id):
    try:
        templates = SchemaTemplateManager.get_templates()
        if template_id in templates:
            return jsonify({
                "success": True,
                "name": templates[template_id]["name"],
                "content": templates[template_id]["content"]
            })
        return jsonify({"success": False, "error": "Template not found"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/create_schema', methods=['POST'])
def create_schema():
    global ailib_instance
    if ailib_instance is None:
        return jsonify({"success": False, "error": "Initialize project first"})
    
    data = request.json
    filename = data.get('filename')
    content = data.get('content')
    
    if not filename or not content:
        return jsonify({"success": False, "error": "Filename and content required"})
    
    try:
        result = ailib_instance.create_schema_file(filename, content)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/schemas', methods=['GET'])
def list_schemas():
    global ailib_instance
    if ailib_instance is None:
        return jsonify({"success": False, "error": "Initialize project first"})
    
    try:
        schemas = ailib_instance.list_schema_files()
        return jsonify({"success": True, "schemas": schemas})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/read_schema', methods=['POST'])
def read_schema():
    global ailib_instance
    if ailib_instance is None:
        return jsonify({"success": False, "error": "Initialize project first"})
    
    data = request.json
    filename = data.get('filename')
    
    if not filename:
        return jsonify({"success": False, "error": "Filename required"})
    
    try:
        result = ailib_instance.read_schema_file(filename)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/generated_code', methods=['POST'])
def get_generated_code():
    global ailib_instance
    if ailib_instance is None:
        return jsonify({"success": False, "error": "Initialize project first"})
    
    data = request.json
    schema_file = data.get('schema_file')
    
    if not schema_file:
        return jsonify({"success": False, "error": "Schema file required"})
    
    try:
        result = ailib_instance.get_generated_code(schema_file)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/trigger', methods=['POST'])
def trigger_update():
    global ailib_instance
    if ailib_instance is None:
        return jsonify({"success": False, "error": "Initialize project first"})
    
    try:
        result = ailib_instance.trigger_ai_update()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/status', methods=['GET'])
def get_status():
    global ailib_instance
    if ailib_instance is None:
        return jsonify({"success": False, "error": "Not initialized"})
    
    try:
        status = ailib_instance.get_status()
        return jsonify({"success": True, "status": status})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ============================================================================
# CLI INTERFACE
# ============================================================================

def cli():
    import sys
    
    if len(sys.argv) < 2:
        print("""
╔══════════════════════════════════════════════════════════════════════╗
║              AILib v4.0 - English Programming System                  ║
╚══════════════════════════════════════════════════════════════════════╝

Commands:
  web                      Start web interface (recommended)
  
Recommended Usage:
  1. python ailib_core.py web
  2. Open: http://localhost:5000
  3. Set API key and initialize project
  4. Create schema files in English
  5. Press Shift+Enter to generate code
""")
        return
    
    command = sys.argv[1]
    
    try:
        if command == "web":
            print("\n🚀 Starting AILib v4.0 - English Programming System")
            print("📱 Open in browser: http://localhost:5000")
            print("⌨️  Press Shift+Enter to generate code from schemas")
            print("Press Ctrl+C to stop\n")
            app.run(host='0.0.0.0', port=5000, debug=False)
        else:
            print(f"Unknown command: {command}")
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        if ailib_instance:
            ailib_instance.cleanup()
    except Exception as e:
        print(f"\n❌ Error: {e}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    cli()
