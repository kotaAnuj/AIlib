"""
================================================================================
FILE: AILib/ailib_core.py (FULLY UPGRADED v3.0)
PURPOSE: Complete self-managing AI development system with web UI
FEATURES:
  - Web UI for setup only (API key, project config)
  - AI manages src/ folder autonomously
  - File watching with Shift+Enter trigger
  - Smart differential updates
  - Real-time status updates
  - Complete environment management
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

# Import our upgraded modules
from ailibrarys.file_access import AIDevManager
from config import AILibConfig
from ai_engine import GeminiEngine
from code_editor import SmartCodeEditor


# ============================================================================
# KEYBOARD LISTENER - Detect Shift+Enter
# ============================================================================

class ShiftEnterListener:
    """
    Listens for Shift+Enter key combination
    Triggers AI update when pressed
    """
    
    def __init__(self, on_trigger_callback):
        self.on_trigger_callback = on_trigger_callback
        self.shift_pressed = False
        self.listener = None
        self.active = False
    
    def start(self):
        """Start listening for Shift+Enter"""
        self.active = True
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()
        print("⌨️  Keyboard listener started - Press Shift+Enter to trigger AI")
    
    def stop(self):
        """Stop listening"""
        self.active = False
        if self.listener:
            self.listener.stop()
        print("⌨️  Keyboard listener stopped")
    
    def _on_press(self, key):
        """Called when key is pressed"""
        if not self.active:
            return
        
        try:
            # Check for Shift key
            if key == keyboard.Key.shift or key == keyboard.Key.shift_r:
                self.shift_pressed = True
            
            # Check for Enter key while Shift is held
            elif key == keyboard.Key.enter and self.shift_pressed:
                print("\n⚡ Shift+Enter detected! Triggering AI update...")
                # Call the callback in a separate thread to not block
                threading.Thread(target=self.on_trigger_callback, daemon=True).start()
        
        except AttributeError:
            pass
    
    def _on_release(self, key):
        """Called when key is released"""
        try:
            if key == keyboard.Key.shift or key == keyboard.Key.shift_r:
                self.shift_pressed = False
        except AttributeError:
            pass


# ============================================================================
# PROJECT MANAGER - Handles project lifecycle
# ============================================================================

class ProjectManager:
    """
    Manages project initialization, configuration, and status
    """
    
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.config_file = self.workspace_root / ".ailib" / "project.json"
    
    def initialize_project(self, name: str, language: str, framework: str, description: str = "") -> Dict:
        """
        Initialize new project
        
        Args:
            name: Project name
            language: Programming language
            framework: Framework (flask, react, etc.)
            description: Project description
        
        Returns:
            {"success": True, "project": {...}}
        """
        
        # Create workspace structure
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        
        # Create project config
        project_config = {
            "name": name,
            "description": description,
            "language": language,
            "framework": framework,
            "created": time.time(),
            "version": "1.0.0",
            "status": "initialized"
        }
        
        # Save config
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(project_config, f, indent=2)
        
        return {
            "success": True,
            "project": project_config,
            "path": str(self.workspace_root)
        }
    
    def load_project(self) -> Optional[Dict]:
        """Load existing project config"""
        if not self.config_file.exists():
            return None
        
        with open(self.config_file, 'r') as f:
            return json.load(f)
    
    def update_status(self, status: str):
        """Update project status"""
        project = self.load_project()
        if project:
            project["status"] = status
            project["last_updated"] = time.time()
            
            with open(self.config_file, 'w') as f:
                json.dump(project, f, indent=2)


# ============================================================================
# UPGRADED AILIB - Self-Managing AI System
# ============================================================================

class UpgradedAILib:
    """
    Complete self-managing AI development system
    
    Features:
    - Web UI for setup only
    - AI manages src/ folder
    - File watching with Shift+Enter trigger
    - Smart differential updates
    - Real-time status
    """
    
    def __init__(self, workspace_root: str = "./workspace"):
        """
        Initialize AI development system
        
        Args:
            workspace_root: Root directory for workspace
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(exist_ok=True)
        
        # Core components
        self.config = AILibConfig(str(self.workspace_root))
        self.project_manager = ProjectManager(str(self.workspace_root))
        
        # AI engine (initialized after API key is set)
        self.ai = None
        
        # Dev manager for terminal and file access
        self.dev_manager = AIDevManager(
            workspace_root=str(self.workspace_root / "src"),
            terminal_mode="system"
        )
        
        # Smart editor
        self.smart_editor = SmartCodeEditor(self.dev_manager.fs)
        
        # Keyboard listener for Shift+Enter
        self.keyboard_listener = None
        
        # Status tracking
        self.status = {
            "initialized": False,
            "ai_ready": False,
            "watching": False,
            "pending_changes": 0,
            "last_trigger": None
        }
        
        # Activity log
        self.activity_log = []
    
    def _log_activity(self, message: str, type: str = "info"):
        """Log activity for UI display"""
        self.activity_log.append({
            "timestamp": time.time(),
            "message": message,
            "type": type
        })
        
        # Keep only last 50 activities
        if len(self.activity_log) > 50:
            self.activity_log = self.activity_log[-50:]
    
    def is_ready(self) -> Tuple[bool, str]:
        """Check if system is ready"""
        if not self.ai:
            return False, "API key not set"
        
        project = self.project_manager.load_project()
        if not project:
            return False, "Project not initialized"
        
        return True, "Ready"
    
    def set_api_key(self, api_key: str) -> Dict:
        """
        Set API key and initialize AI
        
        Args:
            api_key: Gemini API key
        
        Returns:
            {"success": True, "message": "..."}
        """
        try:
            self.config.set_api_key('gemini', api_key)
            
            # Initialize AI engine with workspace/src as root
            src_path = self.workspace_root / "src"
            self.ai = GeminiEngine(api_key, workspace_root=str(src_path), enable_cache=True)
            
            self.status["ai_ready"] = True
            self._log_activity("✅ API key configured and AI engine initialized", "success")
            
            return {
                "success": True,
                "message": "API key configured successfully"
            }
        
        except Exception as e:
            self._log_activity(f"❌ Failed to configure API key: {str(e)}", "error")
            return {
                "success": False,
                "error": str(e)
            }
    
    def initialize_project(self, name: str, language: str, framework: str, description: str = "") -> Dict:
        """
        Initialize new project and setup environment
        
        Args:
            name: Project name
            language: Programming language
            framework: Framework
            description: Project description
        
        Returns:
            {"success": True, "project": {...}, "structure": [...]}
        """
        
        if not self.ai:
            return {"success": False, "error": "API key not set"}
        
        try:
            # Initialize project config
            result = self.project_manager.initialize_project(name, language, framework, description)
            
            if not result["success"]:
                return result
            
            # Setup development environment in src/ folder
            env_result = self.ai.setup_environment(language)
            
            if not env_result["success"]:
                return env_result
            
            self.status["initialized"] = True
            self._log_activity(f"✅ Project '{name}' initialized with {language}/{framework}", "success")
            
            # Start file watching
            self.start_watching()
            
            # Start keyboard listener
            self.start_keyboard_listener()
            
            return {
                "success": True,
                "project": result["project"],
                "structure": env_result["structure"],
                "path": str(self.workspace_root)
            }
        
        except Exception as e:
            self._log_activity(f"❌ Project initialization failed: {str(e)}", "error")
            return {
                "success": False,
                "error": str(e)
            }
    
    def start_watching(self):
        """Start watching for file changes"""
        if not self.ai:
            return
        
        self.ai.start_watching()
        self.status["watching"] = True
        self._log_activity("👁️  File watching started", "info")
    
    def stop_watching(self):
        """Stop watching for file changes"""
        if self.ai:
            self.ai.stop_watching()
        
        self.status["watching"] = False
        self._log_activity("🛑 File watching stopped", "info")
    
    def start_keyboard_listener(self):
        """Start listening for Shift+Enter"""
        if self.keyboard_listener:
            return
        
        self.keyboard_listener = ShiftEnterListener(self._on_shift_enter_pressed)
        self.keyboard_listener.start()
        self._log_activity("⌨️  Keyboard listener started (Shift+Enter to trigger)", "info")
    
    def stop_keyboard_listener(self):
        """Stop keyboard listener"""
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
            self._log_activity("⌨️  Keyboard listener stopped", "info")
    
    def _on_shift_enter_pressed(self):
        """Called when Shift+Enter is pressed"""
        self._log_activity("⚡ Shift+Enter pressed - triggering AI update...", "info")
        result = self.trigger_ai_update()
        
        if result["success"]:
            self._log_activity(
                f"✅ AI update complete - {len(result.get('files_updated', []))} file(s) updated",
                "success"
            )
        else:
            self._log_activity(
                f"⚠️  {result.get('message', 'No changes')}",
                "warning"
            )
    
    def trigger_ai_update(self) -> Dict:
        """
        Trigger AI to analyze and update pending changes
        Called when Shift+Enter is pressed
        
        Returns:
            {
                "success": True,
                "files_updated": [...],
                "results": [...]
            }
        """
        
        if not self.ai:
            return {"success": False, "error": "AI not initialized"}
        
        self.status["last_trigger"] = time.time()
        
        result = self.ai.trigger_update()
        
        return result
    
    def get_pending_changes(self) -> List[Dict]:
        """Get list of pending file changes"""
        if not self.ai:
            return []
        
        return self.ai.file_watcher.get_pending_changes()
    
    def execute_instruction(self, instruction: str) -> Dict:
        """
        Execute natural language instruction
        
        Args:
            instruction: Natural language instruction
        
        Returns:
            {"success": True, "files_created": [...], "message": "..."}
        """
        
        if not self.ai:
            return {"success": False, "error": "AI not initialized"}
        
        ready, msg = self.is_ready()
        if not ready:
            return {"success": False, "error": msg}
        
        self._log_activity(f"📝 Executing: {instruction[:100]}...", "info")
        
        try:
            # Analyze instruction
            analysis = self.ai.analyze_instruction(instruction)
            
            if not analysis["success"]:
                return analysis
            
            intent = analysis["analysis"]
            
            # Build context
            context = {
                "language": intent.get("language", "python"),
                "framework": intent.get("framework", "none"),
                "files": intent.get("files_needed", [])
            }
            
            # Generate code
            result = self.ai.generate_code(instruction, context)
            
            if not result["success"]:
                return result
            
            # Write files to workspace
            created_files = []
            
            for file_info in result["files"]:
                filepath = file_info["path"]
                content = file_info["content"]
                
                # Ensure file is in src/ directory
                if not filepath.startswith("src/"):
                    filepath = f"src/{filepath}"
                
                write_result = self.dev_manager.fs.write_file(filepath, content)
                
                if write_result["success"]:
                    created_files.append(filepath)
                    self._log_activity(f"📄 Created: {filepath}", "success")
            
            # Install dependencies if needed
            if intent.get("dependencies"):
                self._install_dependencies(intent["dependencies"], context["language"])
            
            return {
                "success": True,
                "files_created": created_files,
                "message": f"Created {len(created_files)} file(s)",
                "analysis": intent
            }
        
        except Exception as e:
            self._log_activity(f"❌ Instruction failed: {str(e)}", "error")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _install_dependencies(self, dependencies: List[str], language: str):
        """Install project dependencies"""
        terminal_id = self.dev_manager.terminal.create("Package Installer")
        
        if language == "python":
            cmd = f"pip install {' '.join(dependencies)}"
        elif language in ["javascript", "typescript"]:
            cmd = f"npm install {' '.join(dependencies)}"
        else:
            return
        
        self._log_activity(f"📦 Installing dependencies: {', '.join(dependencies)}", "info")
        
        result = self.dev_manager.terminal.run(terminal_id, cmd, capture_output=True)
        
        if result.get("success"):
            self._log_activity(f"✅ Installed {len(dependencies)} package(s)", "success")
        else:
            self._log_activity(f"⚠️  Package installation had issues", "warning")
    
    def get_status(self) -> Dict:
        """Get current system status"""
        
        # Update pending changes count
        pending = self.get_pending_changes()
        self.status["pending_changes"] = len(pending)
        
        # Get AI statistics
        ai_stats = {}
        if self.ai:
            ai_stats = self.ai.get_statistics()
        
        # Get project info
        project = self.project_manager.load_project()
        
        # Get workspace tree
        tree = self.dev_manager.fs.get_tree(max_depth=2)
        
        return {
            "status": self.status,
            "project": project,
            "ai_stats": ai_stats,
            "workspace": str(self.workspace_root),
            "workspace_tree": tree.get("tree", []),
            "activity_log": self.activity_log[-10:],  # Last 10 activities
            "pending_changes": pending
        }
    
    def cleanup(self):
        """Cleanup and stop all services"""
        self.stop_watching()
        self.stop_keyboard_listener()
        if self.ai:
            self.ai.cleanup()
        
        self._log_activity("🧹 System cleanup complete", "info")


# ============================================================================
# WEB INTERFACE - Flask App
# ============================================================================

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
CORS(app)

# Global AILib instance
ailib_instance = None

# HTML Template with modern UI
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AILib - Self-Managing AI Development</title>
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
            max-width: 1200px;
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
        
        .header p { 
            opacity: 0.9; 
            font-size: 1.1em;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .tabs {
            display: flex;
            background: #f5f5f5;
            border-bottom: 2px solid #ddd;
        }
        
        .tab {
            flex: 1;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            background: #f5f5f5;
            border: none;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.3s;
        }
        
        .tab:hover {
            background: #e0e0e0;
        }
        
        .tab.active {
            background: white;
            border-bottom: 3px solid #667eea;
            color: #667eea;
        }
        
        .tab-content {
            display: none;
            padding: 30px;
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
        }
        
        input:focus,
        select:focus,
        textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        textarea {
            resize: vertical;
            min-height: 100px;
            font-family: inherit;
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
        
        button:active {
            transform: translateY(0);
        }
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
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
        
        .activity-log {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .activity-item {
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 5px;
            background: white;
            border-left: 3px solid #667eea;
        }
        
        .activity-item.success {
            border-left-color: #28a745;
        }
        
        .activity-item.error {
            border-left-color: #dc3545;
        }
        
        .activity-item.warning {
            border-left-color: #ffc107;
        }
        
        .activity-time {
            font-size: 0.85em;
            color: #888;
            margin-bottom: 5px;
        }
        
        .pending-changes {
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .pending-changes h3 {
            color: #856404;
            margin-bottom: 10px;
        }
        
        .file-list {
            list-style: none;
        }
        
        .file-list li {
            padding: 8px;
            background: white;
            margin-bottom: 5px;
            border-radius: 5px;
            border-left: 3px solid #ffc107;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .stat-label {
            opacity: 0.9;
            font-size: 0.9em;
        }
        
        .trigger-button {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            font-size: 1.2em;
            padding: 20px 40px;
            margin: 20px 0;
            width: 100%;
        }
        
        .keyboard-hint {
            text-align: center;
            color: #666;
            margin-top: 10px;
            font-style: italic;
        }
        
        .workspace-tree {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }
        
        .tree-item {
            padding: 5px;
            margin-left: 20px;
        }
        
        .tree-folder::before {
            content: "📁 ";
        }
        
        .tree-file::before {
            content: "📄 ";
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 AILib</h1>
            <p>Self-Managing AI Development System</p>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('setup')">⚙️ Setup</button>
            <button class="tab" onclick="showTab('workspace')">💻 Workspace</button>
            <button class="tab" onclick="showTab('status')">📊 Status</button>
        </div>
        
        <!-- Setup Tab -->
        <div id="setup-tab" class="tab-content active">
            <div class="section">
                <h2>1️⃣ Configure API Key</h2>
                <div class="input-group">
                    <label>Gemini API Key</label>
                    <input type="password" id="apiKey" placeholder="AIza... (Get from https://makersuite.google.com/app/apikey)">
                </div>
                <button onclick="setApiKey()">Set API Key</button>
                <div id="apiStatus"></div>
            </div>
            
            <div class="section">
                <h2>2️⃣ Initialize Project</h2>
                <div class="input-group">
                    <label>Project Name</label>
                    <input type="text" id="projectName" placeholder="my-awesome-project">
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
                    <textarea id="description" placeholder="Describe your project..."></textarea>
                </div>
                <button onclick="initializeProject()">Initialize Project</button>
                <div id="projectStatus"></div>
            </div>
            
            <div class="section">
                <h2>3️⃣ Start Coding!</h2>
                <p style="color: #666; line-height: 1.6;">
                    Once your project is initialized:
                    <br>1. Navigate to <code style="background:#f5f5f5;padding:3px 6px;border-radius:3px;">workspace/src/</code> folder
                    <br>2. Start coding as you normally would
                    <br>3. When you want AI assistance, press <strong>Shift + Enter</strong>
                    <br>4. AI will analyze your changes and improve them
                </p>
            </div>
        </div>
        
        <!-- Workspace Tab -->
        <div id="workspace-tab" class="tab-content">
            <div class="section">
                <h2>📝 Execute Instruction</h2>
                <div class="input-group">
                    <label>Tell AI what to create</label>
                    <textarea id="instruction" rows="4" placeholder="Example: Create a REST API with Flask that has user authentication"></textarea>
                </div>
                <button onclick="executeInstruction()">Execute Instruction</button>
                <div id="instructionStatus"></div>
            </div>
            
            <div id="pendingChangesSection"></div>
            
            <div class="section">
                <h2>⚡ AI Update Trigger</h2>
                <button class="trigger-button" onclick="triggerAiUpdate()">
                    🤖 Trigger AI Update
                </button>
                <div class="keyboard-hint">
                    💡 Or press Shift + Enter anytime
                </div>
                <div id="triggerStatus"></div>
            </div>
            
            <div class="section">
                <h2>📁 Workspace Structure</h2>
                <div id="workspaceTree" class="workspace-tree">
                    Loading...
                </div>
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
        // Tab switching
        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName + '-tab').classList.add('active');
            event.target.classList.add('active');
            
            // Refresh status tab data when opened
            if (tabName === 'status') {
                refreshStatus();
            } else if (tabName === 'workspace') {
                refreshWorkspace();
            }
        }
        
        // Set API Key
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
                message += `<br>🎉 Start coding in workspace/src/`;
                showStatus('projectStatus', message, 'success');
            } else {
                showStatus('projectStatus', data.error, 'error');
            }
        }
        
        // Execute Instruction
        async function executeInstruction() {
            const instruction = document.getElementById('instruction').value;
            if (!instruction) {
                showStatus('instructionStatus', 'Please enter an instruction', 'error');
                return;
            }
            
            showStatus('instructionStatus', '🤖 AI is working...', 'info');
            
            const response = await fetch('/api/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({instruction: instruction})
            });
            
            const data = await response.json();
            
            if (data.success) {
                let message = `✅ ${data.message}<br>`;
                if (data.files_created && data.files_created.length > 0) {
                    message += `<br>📄 Files created:<br>`;
                    data.files_created.forEach(file => {
                        message += `&nbsp;&nbsp;• ${file}<br>`;
                    });
                }
                showStatus('instructionStatus', message, 'success');
                refreshWorkspace();
            } else {
                showStatus('instructionStatus', data.error, 'error');
            }
        }
        
        // Trigger AI Update
        async function triggerAiUpdate() {
            showStatus('triggerStatus', '⚡ Triggering AI update...', 'info');
            
            const response = await fetch('/api/trigger', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });
            
            const data = await response.json();
            
            if (data.success) {
                let message = `✅ AI update complete!<br>`;
                message += `📄 Files updated: ${data.files_updated.length}<br>`;
                if (data.results && data.results.length > 0) {
                    message += `<br>Changes:<br>`;
                    data.results.forEach(r => {
                        message += `&nbsp;&nbsp;• ${r.file}: ${r.changes}<br>`;
                    });
                }
                showStatus('triggerStatus', message, 'success');
                refreshWorkspace();
            } else {
                showStatus('triggerStatus', data.message || data.error, 'warning');
            }
        }
        
        // Refresh Workspace
        async function refreshWorkspace() {
            // Get pending changes
            const response = await fetch('/api/status');
            const data = await response.json();
            
            if (data.success) {
                // Update pending changes
                const pending = data.status.pending_changes || [];
                if (pending.length > 0) {
                    let html = '<div class="pending-changes">';
                    html += `<h3>⚠️ ${pending.length} Pending Change(s)</h3>`;
                    html += '<p>Files modified (press Shift+Enter to trigger AI):</p>';
                    html += '<ul class="file-list">';
                    pending.forEach(p => {
                        html += `<li>${p.file}</li>`;
                    });
                    html += '</ul></div>';
                    document.getElementById('pendingChangesSection').innerHTML = html;
                } else {
                    document.getElementById('pendingChangesSection').innerHTML = '';
                }
                
                // Update workspace tree
                const tree = data.status.workspace_tree || [];
                let treeHtml = renderTree(tree);
                document.getElementById('workspaceTree').innerHTML = treeHtml || 'No files yet';
            }
        }
        
        // Render workspace tree
        function renderTree(items, level = 0) {
            if (!items || items.length === 0) return '';
            
            let html = '';
            items.forEach(item => {
                const indent = '&nbsp;&nbsp;'.repeat(level);
                const className = item.type === 'dir' ? 'tree-folder' : 'tree-file';
                html += `<div class="tree-item ${className}">${indent}${item.name}</div>`;
                
                if (item.children) {
                    html += renderTree(item.children, level + 1);
                }
            });
            return html;
        }
        
        // Refresh Status
        async function refreshStatus() {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            if (data.success) {
                // Update stats
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
                        <div class="stat-label">Pending Changes</div>
                        <div class="stat-value">${stats.pending_changes || 0}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Total Requests</div>
                        <div class="stat-value">${aiStats.total_requests || 0}</div>
                    </div>
                `;
                
                document.getElementById('statsGrid').innerHTML = statsHtml;
                
                // Update activity log
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
                
                // Update AI stats
                let aiStatsHtml = '<div class="stats-grid">';
                if (aiStats.cache) {
                    aiStatsHtml += `
                        <div class="stat-card">
                            <div class="stat-label">Cache Hit Rate</div>
                            <div class="stat-value">${aiStats.cache.hit_rate}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Cached Responses</div>
                            <div class="stat-value">${aiStats.cache.cached_responses}</div>
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
        
        // Show status message
        function showStatus(elementId, message, type) {
            const element = document.getElementById(elementId);
            element.innerHTML = `<div class="status-box ${type}">${message}</div>`;
            
            // Auto-hide after 5 seconds for success messages
            if (type === 'success') {
                setTimeout(() => {
                    element.innerHTML = '';
                }, 5000);
            }
        }
        
        // Auto-refresh workspace and status every 5 seconds
        setInterval(() => {
            const activeTab = document.querySelector('.tab-content.active').id;
            if (activeTab === 'workspace-tab') {
                refreshWorkspace();
            } else if (activeTab === 'status-tab') {
                refreshStatus();
            }
        }, 5000);
        
        // Initial load
        setTimeout(refreshWorkspace, 1000);
    </script>
</body>
</html>
"""

# API Routes

@app.route('/')
def index():
    """Main page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/set_key', methods=['POST'])
def set_api_key():
    """Set API key"""
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
    """Initialize project"""
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

@app.route('/api/execute', methods=['POST'])
def execute_instruction():
    """Execute natural language instruction"""
    global ailib_instance
    
    if ailib_instance is None:
        return jsonify({"success": False, "error": "Initialize project first"})
    
    data = request.json
    instruction = data.get('instruction')
    
    if not instruction:
        return jsonify({"success": False, "error": "Instruction required"})
    
    try:
        result = ailib_instance.execute_instruction(instruction)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/trigger', methods=['POST'])
def trigger_update():
    """Trigger AI to analyze pending changes"""
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
    """Get system status"""
    global ailib_instance
    
    if ailib_instance is None:
        return jsonify({"success": False, "error": "Not initialized"})
    
    try:
        status = ailib_instance.get_status()
        return jsonify({"success": True, "status": status})
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    """Shutdown system"""
    global ailib_instance
    
    if ailib_instance:
        ailib_instance.cleanup()
    
    return jsonify({"success": True, "message": "System shutdown"})


# ============================================================================
# CLI INTERFACE - Command Line
# ============================================================================

def cli():
    """Command line interface"""
    import sys
    
    if len(sys.argv) < 2:
        print("""
╔══════════════════════════════════════════════════════════════════════╗
║              AILib - Self-Managing AI Development System              ║
╚══════════════════════════════════════════════════════════════════════╝

Commands:
  web                      Start web interface (recommended)
  init <name> <lang>       Initialize project from CLI
  config <api_key>         Set API key from CLI
  status                   Show system status

Examples:
  python ailib_core.py web
  python ailib_core.py init my_app python
  python ailib_core.py config AIzaSy...
  
Recommended Usage:
  1. Start web interface: python ailib_core.py web
  2. Open browser: http://localhost:5000
  3. Configure API key and project
  4. Start coding in workspace/src/
  5. Press Shift+Enter when you want AI help
""")
        return
    
    command = sys.argv[1]
    
    try:
        if command == "web":
            print("\n🚀 Starting AILib Web Interface...")
            print("📱 Open in browser: http://localhost:5000")
            print("⌨️  Press Shift+Enter anytime to trigger AI updates")
            print("Press Ctrl+C to stop\n")
            app.run(host='0.0.0.0', port=5000, debug=False)
        
        elif command == "init":
            if len(sys.argv) < 4:
                print("Usage: python ailib_core.py init <name> <language>")
                return
            
            name = sys.argv[2]
            language = sys.argv[3]
            
            ailib = UpgradedAILib(workspace_root="./workspace")
            
            # Check if API key is set
            api_key = ailib.config.get_api_key('gemini')
            if not api_key:
                print("❌ API key not set. Run: python ailib_core.py config YOUR_KEY")
                return
            
            ailib.set_api_key(api_key)
            result = ailib.initialize_project(name, language, "none")
            
            if result["success"]:
                print(f"\n✅ Project '{name}' initialized!")
                print(f"📁 Location: {result['path']}")
                print("\n📄 Structure:")
                for item in result["structure"]:
                    print(f"   {item}")
                print("\n🎉 Start coding in workspace/src/")
                print("   Run 'python ailib_core.py web' to use web interface")
            else:
                print(f"\n❌ Error: {result.get('error')}")
        
        elif command == "config":
            if len(sys.argv) < 3:
                print("Usage: python ailib_core.py config <api_key>")
                return
            
            api_key = sys.argv[2]
            
            config = AILibConfig(project_root="./workspace")
            config.set_api_key("gemini", api_key)
            
            print("✅ API key configured!")
            print("   Run: python ailib_core.py init <name> <language>")
        
        elif command == "status":
            ailib = UpgradedAILib(workspace_root="./workspace")
            
            api_key = ailib.config.get_api_key('gemini')
            if api_key:
                ailib.set_api_key(api_key)
            
            status = ailib.get_status()
            
            print("\n📊 System Status:")
            print(f"   AI Ready: {'✅' if status['status']['ai_ready'] else '❌'}")
            print(f"   Watching: {'👁️' if status['status']['watching'] else '🔴'}")
            print(f"   Pending Changes: {status['status']['pending_changes']}")
            
            if status.get('project'):
                print(f"\n📁 Project: {status['project']['name']}")
                print(f"   Language: {status['project']['language']}")
                print(f"   Framework: {status['project']['framework']}")
        
        else:
            print(f"Unknown command: {command}")
            print("Run without arguments to see help")
    
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        if ailib_instance:
            ailib_instance.cleanup()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    cli()


# ============================================================================
# USAGE DOCUMENTATION
# ============================================================================

"""
═══════════════════════════════════════════════════════════════════════════
COMPLETE USAGE GUIDE
═══════════════════════════════════════════════════════════════════════════

🚀 QUICK START (3 steps):

1. Start web interface:
   python ailib_core.py web

2. Open browser → http://localhost:5000

3. Complete setup:
   - Enter Gemini API key
   - Create project (name, language, framework)
   - Start coding!

═══════════════════════════════════════════════════════════════════════════
💻 DEVELOPER WORKFLOW:
═══════════════════════════════════════════════════════════════════════════

Step 1: Setup (One-time)
────────────────────────
• Open web UI → http://localhost:5000
• Set API key
• Initialize project
• AI creates workspace/src/ folder

Step 2: Code Normally
────────────────────────
• Navigate to workspace/src/
• Create/edit files as you normally would
• Write your code

Step 3: Get AI Help
────────────────────────
• When you want AI assistance:
  - Save your file
  - Press Shift+Enter
  - AI analyzes your changes
  - AI improves/completes your code
  - Changes are written back

Step 4: Continue Coding
────────────────────────
• Review AI's improvements
• Keep coding
• Press Shift+Enter anytime you need help

═══════════════════════════════════════════════════════════════════════════
🎯 KEY FEATURES:
═══════════════════════════════════════════════════════════════════════════

✅ Web UI for setup only (not for coding)
✅ AI manages src/ folder autonomously  
✅ File watching - AI detects your changes
✅ Shift+Enter trigger - instant AI help
✅ Smart updates - only changes what's needed
✅ Preserves your code - keeps unchanged parts
✅ Context-aware - AI knows your entire project
✅ Multiple languages - Python, JS, TS, Java, C++, Go
✅ Framework support - Flask, Django, React, Express

═══════════════════════════════════════════════════════════════════════════
📝 EXAMPLES:
═══════════════════════════════════════════════════════════════════════════

Example 1: Create Flask API
────────────────────────────
1. Web UI → Execute Instruction:
   "Create a REST API with Flask for user management"

2. AI creates:
   - workspace/src/app.py (Flask server)
   - workspace/src/models.py (User model)
   - workspace/src/routes.py (API routes)
   
3. You modify app.py to add authentication

4. Press Shift+Enter

5. AI analyzes and adds:
   - Error handling
   - JWT token generation
   - Password hashing
   - Input validation

Example 2: Fix Bugs
────────────────────────────
1. You write code with a bug in workspace/src/calculator.py

2. Press Shift+Enter

3. AI detects the bug and fixes it automatically

4. AI adds error handling and edge cases

Example 3: Add Features
────────────────────────────
1. You start implementing a login function

2. You write basic logic

3. Press Shift+Enter

4. AI completes:
   - Database integration
   - Session management
   - Error messages
   - Input validation

═══════════════════════════════════════════════════════════════════════════
⚠️  IMPORTANT NOTES:
═══════════════════════════════════════════════════════════════════════════

• Web UI is ONLY for setup (API key, project config)
• All coding happens in workspace/src/ folder
• AI watches src/ for changes automatically
• Shift+Enter triggers AI analysis
• AI NEVER rewrites unchanged code
• Original code is preserved in version history
• You maintain full control over your code

═══════════════════════════════════════════════════════════════════════════
🔧 ADVANCED:
═══════════════════════════════════════════════════════════════════════════

Manual Trigger via Web UI:
• Open workspace tab
• Click "Trigger AI Update" button
• Or press Shift+Enter (preferred)

Check Pending Changes:
• Web UI → Workspace tab
• Shows list of files you modified
• Shows what changed in each file

View Statistics:
• Web UI → Status tab
• See AI usage stats
• View activity log
• Check cache performance

═══════════════════════════════════════════════════════════════════════════
"""
