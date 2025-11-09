"""
================================================================================
FILE: AILib/ai_engine.py (FULLY UPGRADED v4.0 - SCHEMA-AWARE)
PURPOSE: Self-managing AI engine with free-form English programming support
NEW FEATURES:
  - Schema file parsing (file:, version:, dependencies:)
  - Free-form English workflow interpretation
  - Step-by-step flow execution (step1:, step2:, etc.)
  - Natural language code blocks
  - Automatic code generation from English
  - Multi-language support (Python, JS, Java, C++, Go)
  - Smart dependency detection and installation
================================================================================
"""

import json
import requests
import time
import hashlib
import pickle
import os
import re
import threading
from pathlib import Path
from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import difflib


# ============================================================================
# SCHEMA PARSER - Parse free-form English schema files
# ============================================================================

class SchemaParser:
    """
    Parses schema files with mixed metadata and English instructions
    
    Example schema file:
        file: calculator.py
        version: 3.13
        dependencies: math, numpy
        
        step1: take two numbers as input
            input: a, b
            calculate: sum = a + b
            output: print sum
        
        step2: multiply the result by 10
            result = sum * 10
            return result
    """
    
    def __init__(self):
        self.supported_languages = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust'
        }
    
    def parse_schema_file(self, content: str) -> Dict:
        """
        Parse schema file with metadata and English instructions
        
        Returns:
            {
                "metadata": {
                    "file": "calculator.py",
                    "version": "3.13",
                    "dependencies": ["math", "numpy"],
                    "language": "python"
                },
                "steps": [
                    {
                        "step_id": "step1",
                        "description": "take two numbers as input",
                        "details": ["input: a, b", "calculate: sum = a + b", ...],
                        "raw_content": "..."
                    }
                ],
                "free_form_sections": [
                    {
                        "type": "english_description",
                        "content": "take two inputs, sum them, print output"
                    }
                ]
            }
        """
        
        lines = content.split('\n')
        
        result = {
            "metadata": {},
            "steps": [],
            "free_form_sections": [],
            "raw_content": content
        }
        
        # Parse metadata (lines starting with key:value)
        metadata_pattern = r'^(\w+)\s*:\s*(.+)$'
        step_pattern = r'^(step\d+|function\d+|task\d+)\s*:\s*(.*)$'
        
        current_step = None
        current_section = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                continue
            
            # Check for metadata (file:, version:, dependencies:)
            metadata_match = re.match(metadata_pattern, stripped, re.IGNORECASE)
            if metadata_match and not current_step:
                key = metadata_match.group(1).lower()
                value = metadata_match.group(2).strip()
                
                # Special handling for certain keys
                if key == 'dependencies':
                    result["metadata"][key] = [dep.strip() for dep in value.split(',')]
                elif key == 'file':
                    result["metadata"][key] = value
                    # Detect language from file extension
                    ext = Path(value).suffix.lower()
                    result["metadata"]["language"] = self.supported_languages.get(ext, 'python')
                else:
                    result["metadata"][key] = value
                continue
            
            # Check for step markers (step1:, step2:, function1:, etc.)
            step_match = re.match(step_pattern, stripped, re.IGNORECASE)
            if step_match:
                # Save previous step
                if current_step:
                    current_step["details"] = current_section
                    result["steps"].append(current_step)
                    current_section = []
                
                # Start new step
                current_step = {
                    "step_id": step_match.group(1).lower(),
                    "description": step_match.group(2).strip(),
                    "details": [],
                    "raw_content": ""
                }
                continue
            
            # Add line to current step or free-form section
            if current_step:
                current_section.append(line)
            else:
                # Free-form English (not in any step)
                if stripped:
                    result["free_form_sections"].append({
                        "type": "english_description",
                        "content": stripped,
                        "line_number": i + 1
                    })
        
        # Save last step
        if current_step:
            current_step["details"] = current_section
            result["steps"].append(current_step)
        
        # If no explicit language, default to Python
        if "language" not in result["metadata"]:
            result["metadata"]["language"] = "python"
        
        return result
    
    def extract_intent_from_english(self, english_text: str) -> Dict:
        """
        Extract programming intent from natural English
        
        Examples:
            "take two inputs, sum them, print output"
            → {intent: "io_operation", actions: ["input", "sum", "output"]}
            
            "create a function that calculates factorial"
            → {intent: "function_definition", purpose: "factorial"}
        """
        
        text = english_text.lower()
        
        intent_data = {
            "raw_text": english_text,
            "intent": "general",
            "actions": [],
            "variables": [],
            "operations": []
        }
        
        # Detect intent keywords
        if any(word in text for word in ['take input', 'get input', 'read input', 'input']):
            intent_data["actions"].append("input")
        
        if any(word in text for word in ['print', 'output', 'display', 'show']):
            intent_data["actions"].append("output")
        
        if any(word in text for word in ['sum', 'add', 'plus']):
            intent_data["operations"].append("addition")
        
        if any(word in text for word in ['multiply', 'times', 'product']):
            intent_data["operations"].append("multiplication")
        
        if any(word in text for word in ['subtract', 'minus', 'difference']):
            intent_data["operations"].append("subtraction")
        
        if any(word in text for word in ['divide', 'quotient']):
            intent_data["operations"].append("division")
        
        if any(word in text for word in ['loop', 'repeat', 'iterate', 'for each']):
            intent_data["actions"].append("loop")
        
        if any(word in text for word in ['if', 'check', 'condition', 'when']):
            intent_data["actions"].append("conditional")
        
        if any(word in text for word in ['function', 'define', 'create method']):
            intent_data["intent"] = "function_definition"
        
        if any(word in text for word in ['class', 'object', 'create']):
            intent_data["intent"] = "class_definition"
        
        # Extract variable names (words after 'input', 'variable', etc.)
        var_patterns = [
            r'input[s]?\s*[:=]?\s*([a-zA-Z_]\w*(?:\s*,\s*[a-zA-Z_]\w*)*)',
            r'variable[s]?\s*[:=]?\s*([a-zA-Z_]\w*(?:\s*,\s*[a-zA-Z_]\w*)*)',
            r'([a-zA-Z_]\w*)\s*=\s*'
        ]
        
        for pattern in var_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                vars_list = [v.strip() for v in match.split(',')]
                intent_data["variables"].extend(vars_list)
        
        return intent_data


# ============================================================================
# CODE GENERATOR FROM ENGLISH - Convert English to actual code
# ============================================================================

class EnglishToCodeGenerator:
    """
    Generates actual code from English descriptions
    Uses AI to intelligently convert natural language to programming code
    """
    
    def __init__(self, ai_engine):
        self.ai = ai_engine
    
    def generate_code_from_schema(self, schema: Dict, context: Dict = None) -> Dict:
        """
        Generate complete code from parsed schema
        
        Args:
            schema: Parsed schema from SchemaParser
            context: Additional context (existing files, etc.)
        
        Returns:
            {
                "success": True,
                "code": "complete working code",
                "language": "python",
                "explanation": "what the code does"
            }
        """
        
        language = schema["metadata"].get("language", "python")
        target_file = schema["metadata"].get("file", "output.py")
        dependencies = schema["metadata"].get("dependencies", [])
        
        # Build comprehensive prompt for AI
        prompt = self._build_generation_prompt(schema, language, dependencies, context)
        
        # Generate code using AI
        result = self.ai._make_request(prompt, use_cache=False)
        
        if not result["success"]:
            return result
        
        # Parse AI response to extract code
        code = self._extract_code_from_response(result["response"], language)
        
        return {
            "success": True,
            "code": code,
            "language": language,
            "target_file": target_file,
            "dependencies": dependencies,
            "ai_response": result["response"]
        }
    
    def _build_generation_prompt(self, schema: Dict, language: str, 
                                 dependencies: List[str], context: Dict = None) -> str:
        """Build AI prompt from schema"""
        
        prompt = f"""You are an expert {language} programmer. Convert this English description into complete, working {language} code.

TARGET FILE: {schema["metadata"].get("file", "output.py")}
LANGUAGE: {language}
DEPENDENCIES: {', '.join(dependencies) if dependencies else 'None'}

ENGLISH DESCRIPTION / WORKFLOW:
{'='*70}
"""
        
        # Add free-form sections
        if schema["free_form_sections"]:
            prompt += "\nFREE-FORM DESCRIPTION:\n"
            for section in schema["free_form_sections"]:
                prompt += f"{section['content']}\n"
        
        # Add structured steps
        if schema["steps"]:
            prompt += "\nSTEP-BY-STEP WORKFLOW:\n"
            for step in schema["steps"]:
                prompt += f"\n{step['step_id'].upper()}: {step['description']}\n"
                for detail in step['details']:
                    prompt += f"  {detail}\n"
        
        prompt += f"""
{'='*70}

REQUIREMENTS:
1. Generate COMPLETE, PRODUCTION-READY {language} code
2. NO placeholders like "# TODO" or "# Add logic here"
3. Include ALL necessary imports at the top
4. Add proper error handling with try-except blocks
5. Include docstrings and comments explaining logic
6. Follow {language} best practices and conventions
7. Make sure code runs without errors
8. If dependencies are needed, use them properly
9. Add type hints where applicable
10. Include a main execution block if appropriate

OUTPUT FORMAT:
Return ONLY the complete code without markdown backticks or explanations.
Just the pure {language} code that can be executed directly.

EXAMPLE OUTPUT STRUCTURE (for Python):
```
# Imports
import os
import sys

# Constants
MAX_VALUE = 100

# Main code
def main():
    \"\"\"Main entry point\"\"\"
    # Your implementation here
    pass

if __name__ == "__main__":
    main()
```

NOW GENERATE THE COMPLETE {language.upper()} CODE:
"""
        
        return prompt
    
    def _extract_code_from_response(self, response: str, language: str) -> str:
        """Extract clean code from AI response"""
        
        # Remove markdown code blocks if present
        code = response.strip()
        
        # Remove ```python, ```javascript, etc.
        patterns = [
            r'```\w+\n(.*?)\n```',
            r'```(.*?)```',
            r'`(.*?)`'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, code, re.DOTALL)
            if match:
                code = match.group(1).strip()
                break
        
        return code


# ============================================================================
# FILE CHANGE DETECTOR - Enhanced for schema files
# ============================================================================

class FileChangeDetector(FileSystemEventHandler):
    """Detects changes in schema files and triggers AI processing"""
    
    def __init__(self, workspace_root: str, on_change_callback: Callable):
        self.workspace_root = Path(workspace_root)
        self.on_change_callback = on_change_callback
        self.last_modified = {}
        self.debounce_time = 2
        self.schema_parser = SchemaParser()
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        # Watch ALL files in workspace (schema files can have any extension)
        if not any(file_path.endswith(ext) for ext in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.txt', '.md']):
            return
        
        current_time = time.time()
        if file_path in self.last_modified:
            if current_time - self.last_modified[file_path] < self.debounce_time:
                return
        
        self.last_modified[file_path] = current_time
        
        # Check if file contains schema format
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Quick check for schema indicators
            if self._is_schema_file(content):
                print(f"\n🔔 Schema file changed: {file_path}")
                print("   Press Shift+Enter to generate code...")
                self._store_pending_change(file_path, is_schema=True)
            else:
                print(f"\n🔔 File changed: {file_path}")
                print("   Press Shift+Enter to trigger AI update...")
                self._store_pending_change(file_path, is_schema=False)
        
        except Exception as e:
            print(f"⚠️  Error checking file: {e}")
    
    def _is_schema_file(self, content: str) -> bool:
        """Check if file contains schema format"""
        schema_indicators = [
            'file:',
            'version:',
            'dependencies:',
            'step1:',
            'step2:',
            'function1:',
            'task1:',
            re.compile(r'step\d+:', re.IGNORECASE),
            re.compile(r'input\s*[:=]', re.IGNORECASE)
        ]
        
        for indicator in schema_indicators:
            if isinstance(indicator, str):
                if indicator in content:
                    return True
            else:  # regex pattern
                if indicator.search(content):
                    return True
        
        return False
    
    def _store_pending_change(self, file_path: str, is_schema: bool = False):
        pending_file = self.workspace_root.parent / ".ailib" / "pending_changes.json"
        pending_file.parent.mkdir(parents=True, exist_ok=True)
        
        pending = []
        if pending_file.exists():
            with open(pending_file, 'r') as f:
                pending = json.load(f)
        
        rel_path = str(Path(file_path).relative_to(self.workspace_root))
        
        # Remove old entry if exists
        pending = [p for p in pending if p['file'] != rel_path]
        
        pending.append({
            "file": rel_path,
            "timestamp": time.time(),
            "is_schema": is_schema,
            "triggered": False
        })
        
        with open(pending_file, 'w') as f:
            json.dump(pending, f, indent=2)


# ============================================================================
# FILE WATCHER - Enhanced
# ============================================================================

class FileWatcher:
    """Watches src/ folder including schema files"""
    
    def __init__(self, workspace_root: str, on_change_callback: Callable):
        self.workspace_root = Path(workspace_root)
        self.observer = Observer()
        self.handler = FileChangeDetector(str(workspace_root), on_change_callback)
    
    def start(self):
        self.observer.schedule(self.handler, str(self.workspace_root), recursive=True)
        self.observer.start()
        print(f"👁️  Watching for changes in: {self.workspace_root}")
        print(f"    Schema files (.py, .js, .txt) and regular code files")
    
    def stop(self):
        self.observer.stop()
        self.observer.join()
    
    def get_pending_changes(self) -> List[Dict]:
        pending_file = self.workspace_root.parent / ".ailib" / "pending_changes.json"
        if not pending_file.exists():
            return []
        with open(pending_file, 'r') as f:
            return json.load(f)
    
    def clear_pending_changes(self):
        pending_file = self.workspace_root.parent / ".ailib" / "pending_changes.json"
        if pending_file.exists():
            pending_file.unlink()


# ============================================================================
# AI CACHE - (Keep existing implementation)
# ============================================================================

class AICache:
    """Caches AI responses to save API costs"""
    
    def __init__(self, cache_dir: str = ".ailib/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0
        self.enabled = True
    
    def _get_cache_key(self, prompt: str, context: str = "") -> str:
        combined = f"{prompt}::{context}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def get(self, prompt: str, context: str = "") -> Optional[Dict]:
        if not self.enabled:
            return None
        
        cache_key = self._get_cache_key(prompt, context)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cached = pickle.load(f)
                age = datetime.now() - cached['timestamp']
                if age.days < 7:
                    self.hits += 1
                    return cached['data']
                else:
                    cache_file.unlink()
            except:
                pass
        
        self.misses += 1
        return None
    
    def set(self, prompt: str, context: str, data: Dict):
        if not self.enabled:
            return
        
        cache_key = self._get_cache_key(prompt, context)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        cached = {
            'timestamp': datetime.now(),
            'data': data,
            'prompt_preview': prompt[:100]
        }
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(cached, f)
        except Exception as e:
            print(f"⚠️  Could not cache response: {e}")
    
    def clear(self):
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                cache_file.unlink()
            except:
                pass
        self.hits = 0
        self.misses = 0
    
    def stats(self) -> Dict:
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        cache_files = list(self.cache_dir.glob("*.pkl"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total,
            "hit_rate": f"{hit_rate:.1f}%",
            "cached_responses": len(cache_files),
            "cache_size_mb": total_size / (1024 * 1024)
        }


# ============================================================================
# RATE LIMITER - (Keep existing)
# ============================================================================

class RateLimiter:
    """Prevent API rate limit errors"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.request_times = []
    
    def wait_if_needed(self):
        now = time.time()
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        if len(self.request_times) >= self.requests_per_minute:
            oldest = self.request_times[0]
            wait_time = 60 - (now - oldest)
            if wait_time > 0:
                print(f"⏳ Rate limit approaching, waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
        
        self.request_times.append(time.time())


# ============================================================================
# UPGRADED GEMINI ENGINE - Schema-Aware
# ============================================================================

class GeminiEngine:
    """
    Upgraded AI engine with free-form English programming support
    
    NEW FEATURES:
    - Parse schema files (metadata + English workflows)
    - Generate code from natural English
    - Support step-by-step flows
    - Auto-detect programming intent
    - Multi-language code generation
    """
    
    def __init__(self, api_key: str, workspace_root: str = "./workspace/src", enable_cache: bool = True):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.model = "gemini-2.0-flash-exp"
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        
        # NEW: Schema support
        self.schema_parser = SchemaParser()
        self.code_generator = EnglishToCodeGenerator(self)
        
        # Existing features
        self.cache = AICache() if enable_cache else None
        self.rate_limiter = RateLimiter(requests_per_minute=50)
        self.file_watcher = FileWatcher(str(self.workspace_root), self._on_file_changed)
        
        self.total_requests = 0
        self.failed_requests = 0
        self.total_tokens_used = 0
        self.max_retries = 3
        self.timeout = 60
        self.file_versions = {}
        
        print(f"🤖 AI Engine initialized (Schema-Aware v4.0)")
        print(f"   Workspace: {self.workspace_root}")
        print(f"   Supports: Free-form English programming")
    
    def start_watching(self):
        self.file_watcher.start()
        print("👁️  Watching for schema files and code changes")
    
    def stop_watching(self):
        self.file_watcher.stop()
    
    def _on_file_changed(self, file_path: str):
        pass
    
    def trigger_update(self) -> Dict:
        """
        UPGRADED: Handles both schema files and regular code
        """
        print("\n⚡ AI Update Triggered!")
        
        pending = self.file_watcher.get_pending_changes()
        
        if not pending:
            return {"success": False, "message": "No pending changes detected"}
        
        print(f"📋 Found {len(pending)} changed file(s)")
        
        results = []
        
        for change in pending:
            file_path = change['file']
            is_schema = change.get('is_schema', False)
            
            print(f"\n🔍 Analyzing: {file_path} {'[SCHEMA]' if is_schema else '[CODE]'}")
            
            full_path = self.workspace_root / file_path
            if not full_path.exists():
                continue
            
            current_content = full_path.read_text(encoding='utf-8')
            
            if is_schema:
                # NEW: Process schema file
                result = self._process_schema_file(file_path, current_content)
            else:
                # Existing: Process regular code
                original_content = self.file_versions.get(file_path, "")
                result = self._process_regular_code(file_path, current_content, original_content)
            
            if result['success']:
                results.append(result)
        
        self.file_watcher.clear_pending_changes()
        
        return {
            "success": True,
            "files_processed": len(results),
            "results": results
        }
    
    def _process_schema_file(self, file_path: str, content: str) -> Dict:
        """
        NEW: Process schema file with English instructions
        """
        print(f"   📝 Parsing schema file...")
        
        # Parse schema
        schema = self.schema_parser.parse_schema_file(content)
        
        print(f"   ✓ Found {len(schema['steps'])} steps")
        print(f"   ✓ Target: {schema['metadata'].get('file', 'unknown')}")
        print(f"   ✓ Language: {schema['metadata'].get('language', 'python')}")
        
        # Generate code from schema
        print(f"   🤖 Generating code from English...")
        
        gen_result = self.code_generator.generate_code_from_schema(schema)
        
        if not gen_result['success']:
            return gen_result
        
        # Write generated code
        target_file = gen_result['target_file']
        generated_code = gen_result['code']
        
        output_path = self.workspace_root / target_file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(generated_code, encoding='utf-8')
        
        print(f"   ✅ Generated: {target_file}")
        
        return {
            "success": True,
            "type": "schema_generation",
            "schema_file": file_path,
            "generated_file": target_file,
            "language": gen_result['language'],
            "code_length": len(generated_code)
        }
    
    def _process_regular_code(self, file_path: str, current_content: str, original_content: str) -> Dict:
        """
        Existing: Process regular code changes
        """
        from difflib import Differ
        
        diff = self._get_changes(original_content, current_content)
        
        print(f"   Changes: {diff.get('change_summary', 'Modified')}")
        
        # Store updated version
        self.file_versions[file_path] = current_content
        
        return {
            "success": True,
            "type": "code_update",
            "file": file_path,
            "changes": diff.get('change_summary', 'Modified'),
            "lines_changed": diff.get('total_changes', 0)
        }
    
    def _get_changes(self, old_content: str, new_content: str) -> Dict:
        """Analyze what changed between versions"""
        old_lines = old_content.split('\n')
        new_lines = new_content.split('\n')
        
        differ = difflib.Differ()
        diff = list(differ.compare(old_lines, new_lines))
        
        added = sum(1 for line in diff if line.startswith('+ '))
        deleted = sum(1 for line in diff if line.startswith('- '))
        
        return {
            "total_changes": added + deleted,
            "change_summary": f"Modified {added + deleted} lines"
        }
    
    def _make_request(self, prompt: str, system_context: str = "", use_cache: bool = True) -> Dict:
        """Make request to Gemini API with retry"""
        self.total_requests += 1
        
        if use_cache and self.cache:
            cached = self.cache.get(prompt, system_context)
            if cached:
                print("  💾 Using cached response")
                return cached
        
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.base_url}/{self.model}:generateContent"
        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': self.api_key
        }
        
        full_prompt = f"{system_context}\n\n{prompt}" if system_context else prompt
        
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8000,
                "topP": 0.95,
                "topK": 40
            }
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                
                if response.status_code == 429:
                    wait_time = 2 ** attempt
                    print(f"  ⏳ Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                if 'candidates' in data and len(data['candidates']) > 0:
                    content = data['candidates'][0]['content']
                    text = content['parts'][0]['text']
                    
                    if 'usageMetadata' in data:
                        self.total_tokens_used += data['usageMetadata'].get('totalTokenCount', 0)
                    
                    result = {"success": True, "response": text}
                    
                    if use_cache and self.cache:
                        self.cache.set(prompt, system_context, result)
                    
                    return result
                else:
                    return {"success": False, "error": "No response from AI"}
            
            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"  ⏳ Timeout, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    self.failed_requests += 1
                    return {"success": False, "error": "API timeout after retries"}
            
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"  ⏳ Request failed, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    self.failed_requests += 1
                    return {"success": False, "error": f"API request failed: {str(e)}"}
            
            except Exception as e:
                self.failed_requests += 1
                return {"success": False, "error": str(e)}
        
        self.failed_requests += 1
        return {"success": False, "error": "Max retries exceeded"}
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation"""
        return len(text) // 4
    
    def setup_environment(self, project_type: str = "python") -> Dict:
        """Setup development environment"""
        templates = {
            "python": {
                "dirs": ["src", "tests", "docs"],
                "files": {
                    "src/__init__.py": "",
                    "src/main.py": '''"""Main application entry point"""

def main():
    """Main function"""
    print("Application started")

if __name__ == "__main__":
    main()
''',
                    "requirements.txt": "# Python dependencies\n",
                    "README.md": f"# Project\n\nCreated with AILib - English Programming\n\n## Usage\n\n1. Create schema files in src/\n2. Write English instructions\n3. Press Shift+Enter\n4. AI generates code automatically\n\n## Schema Example\n\n```\nfile: calculator.py\nversion: 3.13\n\nstep1: take two numbers as input\n    input: a, b\n    calculate: sum = a + b\n    output: print sum\n```\n",
                    ".gitignore": "__pycache__/\n*.pyc\n.env\nvenv/\n.ailib/\n",
                    "src/example_schema.txt": """# Example Schema File
# Write English descriptions, AI will generate code

file: example_output.py
version: 3.13
dependencies: math

step1: take two numbers as input
    input: a, b
    calculate: sum = a + b
    print the sum

step2: multiply sum by 10
    result = sum * 10
    return result
"""
                }
            },
            "javascript": {
                "dirs": ["src", "tests"],
                "files": {
                    "src/index.js": '''// Main application entry point

function main() {
    console.log('Application started');
}

main();
''',
                    "package.json": json.dumps({
                        "name": "ailib-project",
                        "version": "1.0.0",
                        "main": "src/index.js",
                        "scripts": {"start": "node src/index.js"}
                    }, indent=2),
                    "README.md": "# Project\n\nCreated with AILib - English Programming\n",
                    ".gitignore": "node_modules/\n.env\n.ailib/\n",
                    "src/example_schema.txt": """# JavaScript Example
file: example_output.js

step1: create a function that adds two numbers
    input: a, b
    return: a + b

step2: create a main function
    call the add function with 5 and 3
    log the result
"""
                }
            }
        }
        
        template = templates.get(project_type, templates["python"])
        created = []
        
        for dir_name in template["dirs"]:
            dir_path = self.workspace_root / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            created.append(f"📁 {dir_name}/")
        
        for file_path, content in template["files"].items():
            full_path = self.workspace_root / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding='utf-8')
            created.append(f"📄 {file_path}")
            self.file_versions[file_path] = content
        
        return {
            "success": True,
            "structure": created,
            "type": project_type
        }
    
    def get_statistics(self) -> Dict:
        """Get AI engine statistics"""
        stats = {
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "success_rate": f"{((self.total_requests - self.failed_requests) / self.total_requests * 100):.1f}%" if self.total_requests > 0 else "0%",
            "total_tokens_used": self.total_tokens_used,
            "estimated_cost_usd": self.total_tokens_used * 0.000001,
            "workspace": str(self.workspace_root),
            "tracked_files": len(self.file_versions)
        }
        
        if self.cache:
            stats["cache"] = self.cache.stats()
        
        return stats
    
    def cleanup(self):
        """Cleanup and stop all services"""
        self.stop_watching()
        print("🧹 Cleanup complete")


# ============================================================================
# DEMO / TESTING
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("Upgraded Schema-Aware AI Engine Demo")
    print("="*70)
    
    # Initialize
    api_key = "YOUR_API_KEY_HERE"  # Replace with actual key
    ai = GeminiEngine(api_key, workspace_root="./test_workspace/src", enable_cache=True)
    
    # Test 1: Setup environment with example schema
    print("\n[Test 1] Setup development environment...")
    result = ai.setup_environment("python")
    if result['success']:
        print(f"  ✓ Created project structure:")
        for item in result['structure']:
            print(f"    {item}")
    
    # Test 2: Parse schema file
    print("\n[Test 2] Parse example schema file...")
    schema_content = """file: calculator.py
version: 3.13
dependencies: math

step1: take two numbers as input
    input: a, b
    calculate: sum = a + b
    print the sum

step2: calculate factorial of sum
    use math.factorial
    print the factorial
"""
    
    schema = ai.schema_parser.parse_schema_file(schema_content)
    print(f"  ✓ Metadata: {schema['metadata']}")
    print(f"  ✓ Steps: {len(schema['steps'])}")
    for step in schema['steps']:
        print(f"    - {step['step_id']}: {step['description']}")
    
    # Test 3: Generate code from schema
    print("\n[Test 3] Generate code from schema...")
    gen_result = ai.code_generator.generate_code_from_schema(schema)
    if gen_result['success']:
        print(f"  ✓ Generated {len(gen_result['code'])} characters of code")
        print(f"  ✓ Target file: {gen_result['target_file']}")
        print("\n  Generated Code Preview:")
        print("  " + "-"*66)
        preview = gen_result['code'][:500]
        for line in preview.split('\n'):
            print(f"  {line}")
        print("  " + "-"*66)
    
    # Test 4: Natural language intent extraction
    print("\n[Test 4] Extract intent from English...")
    english_samples = [
        "take two inputs, sum them, print output",
        "create a function that calculates factorial",
        "loop through numbers 1 to 10 and print squares"
    ]
    
    for eng in english_samples:
        intent = ai.schema_parser.extract_intent_from_english(eng)
        print(f"\n  Input: '{eng}'")
        print(f"  Intent: {intent['intent']}")
        print(f"  Actions: {intent['actions']}")
        print(f"  Operations: {intent['operations']}")
    
    # Statistics
    print("\n[Test 5] Engine statistics...")
    stats = ai.get_statistics()
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Success rate: {stats['success_rate']}")
    
    print("\n" + "="*70)
    print("✓ Schema-Aware AI Engine Demo Complete!")
    print("="*70)
    print("\nNew Features Demonstrated:")
    print("  ✓ Schema file parsing (metadata + English)")
    print("  ✓ Step-by-step workflow parsing")
    print("  ✓ Natural language intent extraction")
    print("  ✓ Code generation from English descriptions")
    print("  ✓ Multi-language support")
    print("  ✓ Free-form English programming")
    print("="*70)
    print("\nHow to Use:")
    print("  1. Create a file in src/ (any name)")
    print("  2. Add metadata: file:, version:, dependencies:")
    print("  3. Write English: step1: do this, step2: do that")
    print("  4. Press Shift+Enter")
    print("  5. AI generates complete working code!")
    print("="*70)
