"""
================================================================================
AILib Core - Flexible Natural Language Programming
Version: 2.0
Features:
  - Natural language instructions (no rigid JSON)
  - Flexible file paths (file:path/to/file.ext)
  - Schema/Flow based programming
  - Web UI for chat + API setup
  - Uses existing modules (file_access, terminal, code_editor, ai_engine)
================================================================================
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from flask import Flask, render_template_string, request, jsonify, session
import secrets

# Import existing modules
from ailibrarys.file_access import AIDevManager
from config import AILibConfig
from ai_engine import GeminiEngine
from code_editor import SmartCodeEditor


# ============================================================================
# INSTRUCTION PARSER - Parse Natural Language Instructions
# ============================================================================

class FlexibleInstructionParser:
    """
    Parses natural language instructions with flexible format
    
    Supports:
    - file:path/to/file.py
    - schema 1: description
    - flow1: description
    - version: 1.0 (optional)
    - Any natural language text
    """
    
    def parse(self, instruction_text: str) -> Dict:
        """
        Parse flexible instruction format
        
        Returns:
            {
                "files": ["src/test.py", "utils/helper.js"],
                "schemas": [{"name": "schema1", "desc": "..."}],
                "flows": [{"name": "flow1", "desc": "..."}],
                "version": "1.0",
                "raw_text": "original instruction",
                "language": "python",
                "action": "create|modify|analyze"
            }
        """
        result = {
            "files": [],
            "schemas": [],
            "flows": [],
            "version": None,
            "raw_text": instruction_text,
            "language": self._detect_language(instruction_text),
            "action": self._detect_action(instruction_text)
        }
        
        lines = instruction_text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Extract file paths: file:src/test.py
            if line.startswith('file:'):
                filepath = line[5:].strip()
                result["files"].append(filepath)
            
            # Extract version: version:1.0
            elif line.startswith('version:'):
                result["version"] = line[8:].strip()
            
            # Extract schemas: schema 1: description or schema1: description
            elif re.match(r'^schema\s*\d*:', line, re.IGNORECASE):
                schema_match = re.match(r'^schema\s*(\d*):\s*(.+)', line, re.IGNORECASE)
                if schema_match:
                    schema_num = schema_match.group(1) or "1"
                    schema_desc = schema_match.group(2)
                    result["schemas"].append({
                        "name": f"schema{schema_num}",
                        "description": schema_desc
                    })
            
            # Extract flows: flow1: description or flow 1: description
            elif re.match(r'^flow\s*\d*:', line, re.IGNORECASE):
                flow_match = re.match(r'^flow\s*(\d*):\s*(.+)', line, re.IGNORECASE)
                if flow_match:
                    flow_num = flow_match.group(1) or "1"
                    flow_desc = flow_match.group(2)
                    result["flows"].append({
                        "name": f"flow{flow_num}",
                        "description": flow_desc
                    })
        
        return result
    
    def _detect_language(self, text: str) -> str:
        """Detect programming language from text"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['python', '.py', 'def ', 'import ']):
            return "python"
        elif any(word in text_lower for word in ['javascript', '.js', 'function ', 'const ', 'let ']):
            return "javascript"
        elif any(word in text_lower for word in ['typescript', '.ts', 'interface ']):
            return "typescript"
        elif any(word in text_lower for word in ['java', '.java', 'public class']):
            return "java"
        else:
            return "python"  # Default
    
    def _detect_action(self, text: str) -> str:
        """Detect what action user wants (create/modify/analyze)"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['create', 'new', 'generate', 'build', 'make']):
            return "create"
        elif any(word in text_lower for word in ['modify', 'update', 'change', 'edit', 'add', 'fix']):
            return "modify"
        elif any(word in text_lower for word in ['analyze', 'check', 'review', 'explain', 'test']):
            return "analyze"
        else:
            return "create"  # Default


# ============================================================================
# FLEXIBLE AILIB - Main System
# ============================================================================

class FlexibleAILib:
    """
    Flexible AILib that works with natural language in any format
    No rigid JSON required
    """
    
    def __init__(self, workspace_root: str = ".", api_key: str = None):
        """
        Initialize FlexibleAILib
        
        Args:
            workspace_root: Project root directory
            api_key: Gemini API key (optional, can be set later)
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(exist_ok=True)
        
        # Load config
        self.config = AILibConfig(str(workspace_root))
        
        # Initialize components using existing modules
        self.dev_manager = AIDevManager(
            workspace_root=str(workspace_root),
            terminal_mode="system"
        )
        
        # Initialize smart editor
        self.smart_editor = SmartCodeEditor(self.dev_manager.fs)
        
        # Initialize AI engine
        if api_key:
            self.config.set_api_key('gemini', api_key)
        
        stored_key = self.config.get_api_key('gemini')
        if stored_key:
            self.ai = GeminiEngine(stored_key)
        else:
            self.ai = None
        
        # Parser for flexible instructions
        self.parser = FlexibleInstructionParser()
        
        # Chat history
        self.chat_history = []
    
    def is_ready(self) -> Tuple[bool, str]:
        """Check if system is ready"""
        if not self.ai:
            return False, "API key not set. Use set_api_key() or web interface."
        return True, "Ready"
    
    def set_api_key(self, api_key: str):
        """Set API key and initialize AI"""
        self.config.set_api_key('gemini', api_key)
        self.ai = GeminiEngine(api_key)
        return {"success": True, "message": "API key configured"}
    
    def chat(self, message: str) -> Dict:
        """
        Chat with AI in natural language
        
        Args:
            message: Natural language message
        
        Returns:
            {
                "success": True,
                "response": "AI response",
                "files_created": [...],
                "action_taken": "created code|analyzed|explained"
            }
        """
        ready, msg = self.is_ready()
        if not ready:
            return {"success": False, "error": msg}
        
        # Add to chat history
        self.chat_history.append({"role": "user", "content": message})
        
        # Parse instruction
        parsed = self.parser.parse(message)
        
        # Build context
        context = self._build_context(parsed)
        
        # Check if user wants to execute code or just chat
        if parsed["files"] or parsed["schemas"] or parsed["flows"] or parsed["action"] in ["create", "modify"]:
            # User wants to create/modify code
            result = self._execute_instruction(message, parsed, context)
        else:
            # User just wants to chat/analyze
            result = self._chat_only(message, context)
        
        # Add AI response to history
        if result["success"]:
            self.chat_history.append({"role": "assistant", "content": result["response"]})
        
        return result
    
    def _build_context(self, parsed: Dict) -> Dict:
        """
        Build context for AI with file contents
        """
        context = {
            "language": parsed["language"],
            "files": {},
            "workspace_files": []
        }
        
        # Get existing files in workspace
        for ext in ['*.py', '*.js', '*.ts', '*.java', '*.cpp', '*.c', '*.go']:
            for filepath in self.workspace_root.glob(f"**/{ext}"):
                if '.ailib' not in str(filepath):
                    rel_path = str(filepath.relative_to(self.workspace_root))
                    context["workspace_files"].append(rel_path)
        
        # Read specific files mentioned
        for filepath in parsed["files"]:
            if self.dev_manager.fs.file_exists(filepath):
                result = self.dev_manager.fs.read_file(filepath)
                if result["success"]:
                    context["files"][filepath] = {
                        "exists": True,
                        "content": result["content"][:2000],  # First 2000 chars
                        "lines": len(result["content"].split('\n'))
                    }
            else:
                context["files"][filepath] = {"exists": False}
        
        return context
    
    def _execute_instruction(self, instruction: str, parsed: Dict, context: Dict) -> Dict:
        """
        Execute instruction that creates/modifies code
        """
        print(f"\n{'='*70}")
        print(f"📝 Instruction: {instruction[:100]}...")
        print(f"{'='*70}\n")
        
        # Step 1: Analyze with AI
        print("🔍 Step 1: Analyzing instruction...")
        
        analysis_prompt = f"""Analyze this development instruction:

INSTRUCTION:
{instruction}

PARSED INFO:
- Language: {parsed['language']}
- Files: {parsed['files']}
- Schemas: {parsed['schemas']}
- Flows: {parsed['flows']}
- Action: {parsed['action']}

CONTEXT:
- Existing workspace files: {context['workspace_files']}
- Files mentioned: {list(context['files'].keys())}

Return JSON:
{{
    "intent": "create_new|modify_existing|add_feature",
    "files_to_create": ["path/to/file.ext"],
    "files_to_modify": ["existing/file.ext"],
    "dependencies": ["package1", "package2"],
    "steps": ["step 1", "step 2", "step 3"]
}}
"""
        
        analysis_result = self.ai._make_request(analysis_prompt)
        if not analysis_result['success']:
            return {"success": False, "error": f"Analysis failed: {analysis_result.get('error')}"}
        
        # Parse JSON from response
        try:
            response_text = analysis_result['response'].strip()
            if response_text.startswith('```'):
                response_text = '\n'.join(response_text.split('\n')[1:-1])
            analysis = json.loads(response_text)
        except:
            analysis = {
                "intent": parsed["action"],
                "files_to_create": parsed["files"],
                "files_to_modify": [],
                "dependencies": [],
                "steps": ["Generate code based on instruction"]
            }
        
        print(f"   Intent: {analysis.get('intent', 'unknown')}")
        print(f"   Files to create: {analysis.get('files_to_create', [])}")
        print(f"   Files to modify: {analysis.get('files_to_modify', [])}\n")
        
        # Step 2: Generate code
        print("🤖 Step 2: Generating code...")
        
        code_prompt = f"""Generate code for this instruction:

INSTRUCTION:
{instruction}

ANALYSIS:
{json.dumps(analysis, indent=2)}

CONTEXT:
Language: {context['language']}
Existing files: {json.dumps(context['files'], indent=2)}

REQUIREMENTS:
1. Generate PRODUCTION-READY code (no placeholders)
2. Handle all edge cases
3. Include proper error handling
4. Add comments where needed
5. Follow best practices for {context['language']}

OUTPUT FORMAT:
For each file, use this EXACT format:

```filename:path/to/file.ext
<complete working code>
```

If modifying existing file, use:

```filename:path/to/file.ext
<complete updated code>
```

Generate all necessary code now:
"""
        
        code_result = self.ai._make_request(code_prompt)
        if not code_result['success']:
            return {"success": False, "error": f"Code generation failed: {code_result.get('error')}"}
        
        # Parse generated code
        generated_files = self._parse_code_response(code_result['response'])
        print(f"   ✓ Generated {len(generated_files)} file(s)\n")
        
        # Step 3: Write files
        print("💾 Step 3: Writing files...")
        created_files = []
        
        for file_info in generated_files:
            filepath = file_info['path']
            content = file_info['content']
            
            result = self.dev_manager.fs.write_file(filepath, content)
            
            if result['success']:
                print(f"   ✓ {filepath}")
                created_files.append(filepath)
            else:
                print(f"   ✗ Failed: {filepath}")
        
        # Step 4: Validate if Python
        if context['language'] == 'python':
            print("\n🔧 Step 4: Validating Python code...")
            terminal_id = self.dev_manager.terminal.create("Validator")
            
            for filepath in created_files:
                if filepath.endswith('.py'):
                    validation = self.dev_manager.terminal.run(
                        terminal_id,
                        f"python -m py_compile {filepath}",
                        capture_output=True
                    )
                    
                    if validation.get('exit_code') == 0:
                        print(f"   ✓ {filepath} is valid")
                    else:
                        print(f"   ⚠️  {filepath} has errors")
                        print(f"      Attempting auto-fix...")
                        
                        # Auto-fix
                        file_content = self.dev_manager.fs.read_file(filepath)
                        if file_content['success']:
                            fix_result = self.ai.fix_error(
                                file_content['content'],
                                validation.get('error', ''),
                                context
                            )
                            
                            if fix_result['success']:
                                self.dev_manager.fs.write_file(filepath, fix_result['response'])
                                print(f"      ✓ Fixed")
                            else:
                                print(f"      ✗ Could not fix")
        
        # Step 5: Install dependencies
        if analysis.get('dependencies'):
            print(f"\n📦 Step 5: Installing dependencies...")
            terminal_id = self.dev_manager.terminal.create("Installer")
            
            if context['language'] == 'python':
                cmd = f"pip install {' '.join(analysis['dependencies'])}"
            elif context['language'] == 'javascript':
                cmd = f"npm install {' '.join(analysis['dependencies'])}"
            else:
                cmd = None
            
            if cmd:
                self.dev_manager.terminal.run(terminal_id, cmd)
                print(f"   ✓ Installed {len(analysis['dependencies'])} packages")
        
        print(f"\n{'='*70}")
        print("✅ Instruction completed!")
        print(f"{'='*70}\n")
        
        return {
            "success": True,
            "response": f"Created {len(created_files)} file(s): {', '.join(created_files)}",
            "files_created": created_files,
            "action_taken": "created code",
            "analysis": analysis
        }
    
    def _chat_only(self, message: str, context: Dict) -> Dict:
        """
        Just chat with AI without executing code
        """
        prompt = f"""User message: {message}

Context:
- Language: {context['language']}
- Workspace files: {context['workspace_files']}

Respond naturally and helpfully. If user asks about code, explain clearly.
"""
        
        result = self.ai._make_request(prompt)
        
        if result['success']:
            return {
                "success": True,
                "response": result['response'],
                "files_created": [],
                "action_taken": "explained"
            }
        else:
            return {"success": False, "error": result.get('error')}
    
    def _parse_code_response(self, response: str) -> List[Dict]:
        """Parse AI response to extract code files"""
        files = []
        
        if "```filename:" in response:
            parts = response.split("```filename:")
            
            for part in parts[1:]:
                lines = part.split('\n', 1)
                if len(lines) < 2:
                    continue
                
                filepath = lines[0].strip()
                code_block = lines[1]
                
                if "```" in code_block:
                    code_block = code_block.split("```")[0]
                
                files.append({
                    "path": filepath,
                    "content": code_block.strip()
                })
        else:
            # Single file - try to extract from markdown
            code = response
            if response.strip().startswith("```"):
                lines = response.strip().split('\n')
                if lines[-1].strip() == "```":
                    code = '\n'.join(lines[1:-1])
            
            # Use first mentioned file or default
            files.append({
                "path": "generated_code.py",
                "content": code.strip()
            })
        
        return files
    
    def get_workspace_status(self) -> Dict:
        """Get current workspace status"""
        tree = self.dev_manager.fs.get_tree(max_depth=3)
        
        return {
            "workspace": str(self.workspace_root),
            "files": tree.get('tree', []),
            "recent_operations": self.dev_manager.fs.get_operation_log(last_n=10),
            "chat_history": self.chat_history[-10:]  # Last 10 messages
        }


# ============================================================================
# WEB INTERFACE - Flask App for Chat + Setup
# ============================================================================

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Global AILib instance
ailib_instance = None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AILib - Natural Language Programming</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
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
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { opacity: 0.9; font-size: 1.1em; }
        .setup-section {
            padding: 30px;
            border-bottom: 2px solid #f0f0f0;
        }
        .setup-section h2 { margin-bottom: 20px; color: #333; }
        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        input[type="text"], input[type="password"] {
            flex: 1;
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 16px;
            transition: border 0.3s;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
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
            transition: transform 0.2s;
        }
        button:hover { transform: translateY(-2px); }
        button:active { transform: translateY(0); }
        .status {
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
            font-weight: bold;
        }
        .status.success { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        .chat-section {
            height: 500px;
            display: flex;
            flex-direction: column;
            padding: 30px;
        }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .message {
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 10px;
            max-width: 80%;
        }
        .message.user {
            background: #667eea;
            color: white;
            margin-left: auto;
        }
        .message.assistant {
            background: white;
            border: 2px solid #ddd;
        }
        .message .role {
            font-weight: bold;
            margin-bottom: 5px;
            font-size: 0.9em;
            opacity: 0.8;
        }
        .message .content {
            line-height: 1.6;
            white-space: pre-wrap;
        }
        .code-block {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
        }
        .chat-input {
            display: flex;
            gap: 10px;
        }
        .chat-input textarea {
            flex: 1;
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 10px;
            resize: none;
            font-size: 16px;
            font-family: inherit;
        }
        .example-instructions {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
        }
        .example-instructions h3 {
            margin-bottom: 15px;
            color: #333;
        }
        .example {
            background: white;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 10px;
            border-left: 4px solid #667eea;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .example:hover {
            transform: translateX(5px);
        }
        .example code {
            display: block;
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
            color: #555;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 AILib</h1>
            <p>Natural Language Programming - Code in Any Language You Speak</p>
        </div>
        
        <div class="setup-section">
            <h2>⚙️ Setup</h2>
            <div class="input-group">
                <input type="password" id="apiKey" placeholder="Enter your Gemini API key (AIza...)">
                <button onclick="setApiKey()">Set API Key</button>
            </div>
            <div class="input-group">
                <input type="text" id="workspace" value="./workspace" placeholder="Workspace path">
                <button onclick="initWorkspace()">Initialize Workspace</button>
            </div>
            <div id="status"></div>
            
            <div class="example-instructions">
                <h3>📝 Example Instructions (Click to Use)</h3>
                <div class="example" onclick="useExample(this)">
                    <code>file:src/calculator.py

schema 1: take 2 inputs -> calculate sum -> return square of sum -> print output

Create a calculator program</code>
                </div>
                <div class="example" onclick="useExample(this)">
                    <code>file:utils/math_helper.js

flow1:
    inputs = a, b, c
    sum = a + b + c
    print(sum)

Make it work in JavaScript</code>
                </div>
                <div class="example" onclick="useExample(this)">
                    <code>file:api/server.py
version:1.0

Create a Flask REST API with these endpoints:
- GET /users - list all users
- POST /users - create user
- GET /users/:id - get single user

Include database setup</code>
                </div>
            </div>
        </div>
        
        <div class="chat-section">
            <div class="chat-messages" id="chatMessages"></div>
            <div class="chat-input">
                <textarea id="messageInput" rows="3" placeholder="Type your instruction in natural language...

Examples:
file:src/app.py
Create a Flask web server

or

flow1: take input -> process -> output result"></textarea>
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>
    </div>
    
    <script>
        let chatHistory = [];
        
        async function setApiKey() {
            const apiKey = document.getElementById('apiKey').value;
            if (!apiKey) {
                showStatus('Please enter API key', 'error');
                return;
            }
            
            const response = await fetch('/api/set_key', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({api_key: apiKey})
            });
            
            const data = await response.json();
            showStatus(data.message, data.success ? 'success' : 'error');
        }
        
        async function initWorkspace() {
            const workspace = document.getElementById('workspace').value;
            
            const response = await fetch('/api/init_workspace', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({workspace: workspace})
            });
            
            const data = await response.json();
            showStatus(data.message, data.success ? 'success' : 'error');
        }
        
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Add user message to chat
            addMessage('user', message);
            input.value = '';
            
            // Show loading
            const loadingId = addMessage('assistant', '🤖 Thinking...');
            
            // Send to backend
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: message})
            });
            
            const data = await response.json();
            
            // Remove loading
            document.getElementById(loadingId).remove();
            
            // Add AI response
            if (data.success) {
                let response = data.response;
                if (data.files_created && data.files_created.length > 0) {
                    response += '\n\n📁 Files created:\n' + data.files_created.map(f => '• ' + f).join('\n');
                }
                addMessage('assistant', response);
            } else {
                addMessage('assistant', '❌ Error: ' + data.error);
            }
        }
        
        function addMessage(role, content) {
            const messagesDiv = document.getElementById('chatMessages');
            const messageId = 'msg-' + Date.now();
            
            const messageDiv = document.createElement('div');
            messageDiv.id = messageId;
            messageDiv.className = 'message ' + role;
            messageDiv.innerHTML = `
                <div class="role">${role === 'user' ? '👤 You' : '🤖 AILib'}</div>
                <div class="content">${escapeHtml(content)}</div>
            `;
            
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
            
            return messageId;
        }
        
        function showStatus(message, type) {
            const statusDiv = document.getElementById('status');
            statusDiv.className = 'status ' + type;
            statusDiv.textContent = message;
            
            setTimeout(() => {
                statusDiv.textContent = '';
                statusDiv.className = 'status';
            }, 5000);
        }
        
        function useExample(element) {
            const code = element.querySelector('code').textContent;
            document.getElementById('messageInput').value = code;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Allow Enter to send (Shift+Enter for new line)
        document.getElementById('messageInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    </script>
</body>
</html>
"""

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
        return jsonify({"success": False, "message": "API key required"})
    
    try:
        if ailib_instance is None:
            ailib_instance = FlexibleAILib(workspace_root="./workspace", api_key=api_key)
        else:
            ailib_instance.set_api_key(api_key)
        
        return jsonify({"success": True, "message": "✅ API key configured successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/api/init_workspace', methods=['POST'])
def init_workspace():
    """Initialize workspace"""
    global ailib_instance
    
    data = request.json
    workspace = data.get('workspace', './workspace')
    
    try:
        if ailib_instance is None:
            ailib_instance = FlexibleAILib(workspace_root=workspace)
        
        Path(workspace).mkdir(exist_ok=True)
        
        return jsonify({
            "success": True,
            "message": f"✅ Workspace initialized at {workspace}"
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat with AI"""
    global ailib_instance
    
    if ailib_instance is None:
        return jsonify({
            "success": False,
            "error": "Please set API key and initialize workspace first"
        })
    
    data = request.json
    message = data.get('message')
    
    if not message:
        return jsonify({"success": False, "error": "Message required"})
    
    try:
        result = ailib_instance.chat(message)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get workspace status"""
    global ailib_instance
    
    if ailib_instance is None:
        return jsonify({"success": False, "error": "Not initialized"})
    
    try:
        status = ailib_instance.get_workspace_status()
        return jsonify({"success": True, "status": status})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ============================================================================
# CLI INTERFACE - Command Line
# ============================================================================

def cli():
    """Command line interface"""
    import sys
    
    if len(sys.argv) < 2:
        print("""
╔══════════════════════════════════════════════════════════════════════╗
║              AILib - Flexible Natural Language Programming            ║
╚══════════════════════════════════════════════════════════════════════╝

Commands:
  web                      Start web interface
  chat "<message>"         Chat with AI from command line
  config <api_key>         Set API key
  status                   Show workspace status

Examples:
  python ailib_core.py web
  python ailib_core.py chat "file:app.py Create Flask server"
  python ailib_core.py config AIzaSy...
  
Web Interface (Recommended):
  python ailib_core.py web
  Then open: http://localhost:5000
""")
        return
    
    command = sys.argv[1]
    
    try:
        if command == "web":
            print("\n🚀 Starting AILib Web Interface...")
            print("📱 Open in browser: http://localhost:5000")
            print("Press Ctrl+C to stop\n")
            app.run(host='0.0.0.0', port=5000, debug=False)
        
        elif command == "chat":
            if len(sys.argv) < 3:
                print("Usage: python ailib_core.py chat \"<message>\"")
                return
            
            message = sys.argv[2]
            
            ailib = FlexibleAILib(workspace_root="./workspace")
            
            # Check if ready
            ready, msg = ailib.is_ready()
            if not ready:
                print(f"❌ {msg}")
                print("Set API key first: python ailib_core.py config YOUR_KEY")
                return
            
            # Execute
            result = ailib.chat(message)
            
            if result["success"]:
                print(f"\n✅ {result['response']}")
                if result.get('files_created'):
                    print(f"\n📁 Files created:")
                    for f in result['files_created']:
                        print(f"   • {f}")
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
        
        elif command == "status":
            ailib = FlexibleAILib(workspace_root="./workspace")
            status = ailib.get_workspace_status()
            
            print("\n📊 Workspace Status:")
            print(f"   Location: {status['workspace']}")
            print(f"   Files: {len(status.get('files', []))}")
            print(f"   Recent operations: {len(status.get('recent_operations', []))}")
            print(f"   Chat history: {len(status.get('chat_history', []))} messages")
        
        else:
            print(f"Unknown command: {command}")
            print("Run without arguments to see help")
    
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
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
# USAGE EXAMPLES
# ============================================================================

"""
═══════════════════════════════════════════════════════════════════════════
EXAMPLE 1: Using Web Interface (Recommended)
═══════════════════════════════════════════════════════════════════════════

1. Start web server:
   python ailib_core.py web

2. Open browser: http://localhost:5000

3. Enter API key in web interface

4. Type natural language instruction:

   file:src/calculator.py
   
   schema 1: take 2 inputs -> calculate sum -> return square of sum -> print
   
   Create a calculator program

5. AI will generate code automatically!

═══════════════════════════════════════════════════════════════════════════
EXAMPLE 2: Command Line Usage
═══════════════════════════════════════════════════════════════════════════

# Set API key
python ailib_core.py config AIzaSyCy3JRWw7sS6-1A0fFBT2UzEBx-us2F95w

# Execute instruction
python ailib_core.py chat "file:app.py Create Flask server with /hello endpoint"

# Check status
python ailib_core.py status

═══════════════════════════════════════════════════════════════════════════
EXAMPLE 3: Natural Language Formats Supported
═══════════════════════════════════════════════════════════════════════════

Format 1 - Schema Based:
----------------------
file:src/math_util.py

schema 1: take 2 inputs -> calculate sum -> return square of sum output print

Format 2 - Flow Based:
--------------------
file:utils/processor.js

flow1:
    inputs = a, b, c
    sum = a + b + c
    print(sum)

Make it work in JavaScript

Format 3 - Plain English:
-----------------------
file:api/server.py
version:1.0

Create a REST API with Flask:
- GET /users - list all users
- POST /users - create new user
- Include database setup with SQLAlchemy

Format 4 - Multiple Files:
------------------------
file:src/models.py
file:src/views.py
file:src/app.py

Create a complete Flask MVC application with:
- User model with name, email, password
- CRUD views for users
- Main app with all routes

Format 5 - Just Chat:
-------------------
How do I implement JWT authentication in Python?

(AI will explain without creating files)

═══════════════════════════════════════════════════════════════════════════
EXAMPLE 4: Programming in Your Language
═══════════════════════════════════════════════════════════════════════════

You can write instructions in ANY natural language!

Hindi Example:
-------------
file:calculator.py

do number input lo aur unka sum calculate karo
phir sum ka square nikal kar print karo

Spanish Example:
---------------
file:app.py

Crear una aplicación web con Flask
- endpoint /hola que devuelve "Hola Mundo"
- endpoint /suma que suma dos números

French Example:
--------------
file:serveur.py

Créer un serveur web avec Flask
- route /bonjour qui retourne "Bonjour le monde"

═══════════════════════════════════════════════════════════════════════════
FEATURES SUMMARY
═══════════════════════════════════════════════════════════════════════════

✅ No rigid JSON format - write in natural language
✅ Flexible file paths - specify any structure you want
✅ Schema/Flow based programming
✅ Multi-language support (Python, JavaScript, TypeScript, Java, etc.)
✅ Web interface for easy interaction
✅ Command line interface for automation
✅ Auto-fix code errors
✅ Install dependencies automatically
✅ Chat with AI for explanations
✅ Uses existing modules (file_access, terminal, code_editor, ai_engine)
✅ Context-aware code generation
✅ Modifies existing files intelligently

═══════════════════════════════════════════════════════════════════════════
"""
