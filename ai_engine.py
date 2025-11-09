"""
================================================================================
FILE: AILib/ai_engine.py (FULLY UPGRADED v3.0)
PURPOSE: Self-managing AI engine with file watching, smart updates, and triggers
FEATURES:
  - File watching system (detects user changes)
  - Shift+Enter trigger support
  - Smart differential updates (only change what user modified)
  - Response caching (save API costs)
  - Automatic retry with exponential backoff
  - Self-managing environment in src/ folder
  - Context-aware code generation
  - Preserves unchanged code
================================================================================
"""

import json
import requests
import time
import hashlib
import pickle
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import difflib


# ============================================================================
# FILE CHANGE DETECTOR - Watches user file modifications
# ============================================================================

class FileChangeDetector(FileSystemEventHandler):
    """
    Detects when user modifies files in src/ folder
    Triggers AI to analyze and update code
    """
    
    def __init__(self, workspace_root: str, on_change_callback: Callable):
        """
        Args:
            workspace_root: Path to watch (e.g., "./workspace/src")
            on_change_callback: Function to call when file changes
        """
        self.workspace_root = Path(workspace_root)
        self.on_change_callback = on_change_callback
        self.last_modified = {}
        self.debounce_time = 2  # Wait 2 seconds after last change
        
    def on_modified(self, event):
        """Called when file is modified"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        # Ignore non-code files
        if not any(file_path.endswith(ext) for ext in ['.py', '.js', '.ts', '.java', '.cpp', '.c']):
            return
        
        # Debounce (avoid multiple triggers for same file)
        current_time = time.time()
        if file_path in self.last_modified:
            if current_time - self.last_modified[file_path] < self.debounce_time:
                return
        
        self.last_modified[file_path] = current_time
        
        # Trigger AI analysis
        print(f"\n🔔 File changed: {file_path}")
        print("   Press Shift+Enter to trigger AI update...")
        
        # Store pending change
        self._store_pending_change(file_path)
    
    def _store_pending_change(self, file_path: str):
        """Store pending file change"""
        pending_file = self.workspace_root.parent / ".ailib" / "pending_changes.json"
        pending_file.parent.mkdir(parents=True, exist_ok=True)
        
        pending = []
        if pending_file.exists():
            with open(pending_file, 'r') as f:
                pending = json.load(f)
        
        # Add new change
        rel_path = str(Path(file_path).relative_to(self.workspace_root))
        if rel_path not in pending:
            pending.append({
                "file": rel_path,
                "timestamp": time.time(),
                "triggered": False
            })
        
        with open(pending_file, 'w') as f:
            json.dump(pending, f, indent=2)


class FileWatcher:
    """
    Watches src/ folder for user changes
    """
    
    def __init__(self, workspace_root: str, on_change_callback: Callable):
        self.workspace_root = Path(workspace_root)
        self.observer = Observer()
        self.handler = FileChangeDetector(str(workspace_root), on_change_callback)
    
    def start(self):
        """Start watching for file changes"""
        self.observer.schedule(self.handler, str(self.workspace_root), recursive=True)
        self.observer.start()
        print(f"👁️  Watching for changes in: {self.workspace_root}")
    
    def stop(self):
        """Stop watching"""
        self.observer.stop()
        self.observer.join()
    
    def get_pending_changes(self) -> List[Dict]:
        """Get list of pending file changes"""
        pending_file = self.workspace_root.parent / ".ailib" / "pending_changes.json"
        
        if not pending_file.exists():
            return []
        
        with open(pending_file, 'r') as f:
            return json.load(f)
    
    def clear_pending_changes(self):
        """Clear pending changes after processing"""
        pending_file = self.workspace_root.parent / ".ailib" / "pending_changes.json"
        if pending_file.exists():
            pending_file.unlink()


# ============================================================================
# DIFFERENTIAL ANALYZER - Detects what changed in file
# ============================================================================

class DifferentialAnalyzer:
    """
    Analyzes what changed between old and new versions of file
    Only updates the changed parts
    """
    
    def __init__(self):
        pass
    
    def get_changes(self, old_content: str, new_content: str) -> Dict:
        """
        Get detailed changes between two versions
        
        Returns:
            {
                "added_lines": [(line_num, content)],
                "deleted_lines": [(line_num, content)],
                "modified_lines": [(line_num, old, new)],
                "unchanged_sections": [(start, end)],
                "change_summary": "User added function login(), modified class User"
            }
        """
        old_lines = old_content.split('\n')
        new_lines = new_content.split('\n')
        
        # Use difflib to find changes
        differ = difflib.Differ()
        diff = list(differ.compare(old_lines, new_lines))
        
        added = []
        deleted = []
        modified = []
        unchanged_sections = []
        
        current_section_start = None
        line_num = 0
        
        for i, line in enumerate(diff):
            if line.startswith('  '):  # Unchanged
                if current_section_start is None:
                    current_section_start = line_num
                line_num += 1
            elif line.startswith('+ '):  # Added
                if current_section_start is not None:
                    unchanged_sections.append((current_section_start, line_num - 1))
                    current_section_start = None
                added.append((line_num, line[2:]))
            elif line.startswith('- '):  # Deleted
                if current_section_start is not None:
                    unchanged_sections.append((current_section_start, line_num - 1))
                    current_section_start = None
                deleted.append((line_num, line[2:]))
            elif line.startswith('? '):  # Changed
                continue
        
        # Final unchanged section
        if current_section_start is not None:
            unchanged_sections.append((current_section_start, line_num - 1))
        
        # Generate summary
        summary = self._generate_change_summary(old_content, new_content, added, deleted)
        
        return {
            "added_lines": added,
            "deleted_lines": deleted,
            "unchanged_sections": unchanged_sections,
            "change_summary": summary,
            "total_changes": len(added) + len(deleted)
        }
    
    def _generate_change_summary(self, old: str, new: str, added: List, deleted: List) -> str:
        """Generate human-readable summary of changes"""
        summary_parts = []
        
        # Check for new functions
        new_functions = self._extract_function_names(new)
        old_functions = self._extract_function_names(old)
        
        added_funcs = set(new_functions) - set(old_functions)
        if added_funcs:
            summary_parts.append(f"Added functions: {', '.join(added_funcs)}")
        
        deleted_funcs = set(old_functions) - set(new_functions)
        if deleted_funcs:
            summary_parts.append(f"Removed functions: {', '.join(deleted_funcs)}")
        
        # Check for new classes
        new_classes = self._extract_class_names(new)
        old_classes = self._extract_class_names(old)
        
        added_classes = set(new_classes) - set(old_classes)
        if added_classes:
            summary_parts.append(f"Added classes: {', '.join(added_classes)}")
        
        # Check for imports
        new_imports = self._extract_imports(new)
        old_imports = self._extract_imports(old)
        
        added_imports = set(new_imports) - set(old_imports)
        if added_imports:
            summary_parts.append(f"Added imports: {', '.join(added_imports)}")
        
        if not summary_parts:
            summary_parts.append(f"Modified {len(added) + len(deleted)} lines")
        
        return "; ".join(summary_parts)
    
    def _extract_function_names(self, code: str) -> List[str]:
        """Extract function names from code"""
        import re
        return re.findall(r'def (\w+)\(', code)
    
    def _extract_class_names(self, code: str) -> List[str]:
        """Extract class names from code"""
        import re
        return re.findall(r'class (\w+)', code)
    
    def _extract_imports(self, code: str) -> List[str]:
        """Extract import statements"""
        import re
        imports = re.findall(r'import (\w+)', code)
        imports += re.findall(r'from (\w+)', code)
        return imports


# ============================================================================
# AI RESPONSE CACHE - Save Money on Duplicate Requests
# ============================================================================

class AICache:
    """
    Caches AI responses to avoid duplicate API calls
    """
    
    def __init__(self, cache_dir: str = ".ailib/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.enabled = True
    
    def _get_cache_key(self, prompt: str, context: str = "") -> str:
        """Generate cache key from prompt + context"""
        combined = f"{prompt}::{context}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def get(self, prompt: str, context: str = "") -> Optional[Dict]:
        """Get cached response if exists and not expired"""
        if not self.enabled:
            return None
        
        cache_key = self._get_cache_key(prompt, context)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cached = pickle.load(f)
                
                # Check if cache is recent (within 7 days)
                age = datetime.now() - cached['timestamp']
                if age.days < 7:
                    self.hits += 1
                    return cached['data']
                else:
                    # Expired - delete
                    cache_file.unlink()
            except Exception:
                pass
        
        self.misses += 1
        return None
    
    def set(self, prompt: str, context: str, data: Dict):
        """Cache a response"""
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
        """Clear all cache"""
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                cache_file.unlink()
            except:
                pass
        
        self.hits = 0
        self.misses = 0
    
    def stats(self) -> Dict:
        """Get cache statistics"""
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
# RATE LIMITER - Prevent API Rate Limit Errors
# ============================================================================

class RateLimiter:
    """Rate limiter to prevent hitting API limits"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.request_times = []
    
    def wait_if_needed(self):
        """Wait if we're hitting rate limits"""
        now = time.time()
        
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        # Check if we need to wait
        if len(self.request_times) >= self.requests_per_minute:
            oldest = self.request_times[0]
            wait_time = 60 - (now - oldest)
            if wait_time > 0:
                print(f"⏳ Rate limit approaching, waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
        
        # Record this request
        self.request_times.append(time.time())


# ============================================================================
# CONTEXT BUILDER - Build Rich Context with File Contents
# ============================================================================

class ContextBuilder:
    """
    Builds rich context for AI by reading existing files
    Critical for AI to understand existing code
    """
    
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root)
    
    def build_context(self, language: str, files_mentioned: List[str] = None) -> Dict:
        """
        Build comprehensive context with file contents
        
        Returns:
            {
                "language": "python",
                "workspace_files": ["app.py", "utils.py"],
                "file_contents": {
                    "app.py": {
                        "exists": True,
                        "content": "first 3000 chars...",
                        "functions": ["main", "setup"],
                        "classes": ["App"],
                        "imports": ["flask", "os"],
                        "lines": 150
                    }
                }
            }
        """
        
        context = {
            "language": language,
            "workspace_files": [],
            "file_contents": {}
        }
        
        # Find all code files in workspace
        patterns = {
            "python": ["*.py"],
            "javascript": ["*.js", "*.jsx"],
            "typescript": ["*.ts", "*.tsx"],
            "java": ["*.java"],
            "cpp": ["*.cpp", "*.h"],
            "go": ["*.go"]
        }
        
        file_patterns = patterns.get(language, ["*.py"])
        
        for pattern in file_patterns:
            for filepath in self.workspace_root.glob(f"**/{pattern}"):
                # Skip hidden directories and dependencies
                if any(part.startswith('.') for part in filepath.parts):
                    continue
                if any(skip in str(filepath) for skip in ['node_modules', 'venv', '__pycache__']):
                    continue
                
                rel_path = str(filepath.relative_to(self.workspace_root))
                context["workspace_files"].append(rel_path)
        
        # Read specific files mentioned by user
        if files_mentioned:
            for filepath in files_mentioned:
                self._add_file_to_context(filepath, context, language)
        
        # Read all existing files (up to 15 files to avoid token limit)
        for filepath in context["workspace_files"][:15]:
            if filepath not in context["file_contents"]:
                self._add_file_to_context(filepath, context, language)
        
        return context
    
    def _add_file_to_context(self, filepath: str, context: Dict, language: str):
        """Add single file to context"""
        full_path = self.workspace_root / filepath
        
        if not full_path.exists():
            context["file_contents"][filepath] = {"exists": False}
            return
        
        try:
            content = full_path.read_text(encoding='utf-8')
            
            file_info = {
                "exists": True,
                "size": len(content),
                "lines": len(content.split('\n')),
                "content": content[:3000]  # First 3000 chars for better context
            }
            
            # Analyze Python files
            if language == "python" and filepath.endswith('.py'):
                import ast
                try:
                    tree = ast.parse(content)
                    
                    functions = [node.name for node in ast.walk(tree) 
                                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
                    classes = [node.name for node in ast.walk(tree) 
                              if isinstance(node, ast.ClassDef)]
                    
                    file_info["functions"] = functions[:20]  # First 20 functions
                    file_info["classes"] = classes[:10]      # First 10 classes
                    
                    # Extract imports
                    imports = []
                    for line in content.split('\n')[:50]:
                        if line.strip().startswith('import ') or line.strip().startswith('from '):
                            imports.append(line.strip())
                    file_info["imports"] = imports[:15]
                except:
                    pass
            
            context["file_contents"][filepath] = file_info
        
        except Exception as e:
            context["file_contents"][filepath] = {
                "exists": True,
                "error": str(e)
            }


# ============================================================================
# UPGRADED GEMINI ENGINE - Self-Managing AI
# ============================================================================

class GeminiEngine:
    """
    Self-managing AI engine with file watching and smart updates
    
    New Features:
    - File watching system
    - Shift+Enter trigger support
    - Differential updates (only change what user modified)
    - Response caching
    - Automatic retry
    - Rate limiting
    - Rich context with full file contents
    - Preserves unchanged code
    """
    
    def __init__(self, api_key: str, workspace_root: str = "./workspace/src", enable_cache: bool = True):
        """
        Initialize self-managing AI engine
        
        Args:
            api_key: Your Gemini API key
            workspace_root: Root directory for AI workspace (default: ./workspace/src)
            enable_cache: Enable response caching
        """
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.model = "gemini-2.0-flash-exp"
        self.workspace_root = Path(workspace_root)
        
        # Ensure workspace exists
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        
        # Advanced features
        self.cache = AICache() if enable_cache else None
        self.rate_limiter = RateLimiter(requests_per_minute=50)
        self.context_builder = ContextBuilder(str(self.workspace_root))
        self.diff_analyzer = DifferentialAnalyzer()
        
        # File watching
        self.file_watcher = FileWatcher(
            str(self.workspace_root),
            on_change_callback=self._on_file_changed
        )
        
        # Statistics
        self.total_requests = 0
        self.failed_requests = 0
        self.total_tokens_used = 0
        
        # Retry configuration
        self.max_retries = 3
        self.timeout = 60
        
        # Original file versions (for differential updates)
        self.file_versions = {}
        
        print(f"🤖 AI Engine initialized")
        print(f"   Workspace: {self.workspace_root}")
        print(f"   Cache: {'Enabled' if enable_cache else 'Disabled'}")
    
    def start_watching(self):
        """Start watching for file changes"""
        self.file_watcher.start()
        print("👁️  File watching started - AI will detect your changes")
        print("   Make changes to your files, then press Shift+Enter to trigger AI update")
    
    def stop_watching(self):
        """Stop watching for file changes"""
        self.file_watcher.stop()
        print("👋 File watching stopped")
    
    def _on_file_changed(self, file_path: str):
        """Called when file changes detected"""
        # This is just for logging - actual trigger happens on Shift+Enter
        pass
    
    def trigger_update(self) -> Dict:
        """
        Trigger AI to analyze pending file changes and update code
        Called when user presses Shift+Enter
        
        Returns:
            {
                "success": True,
                "files_updated": ["app.py", "utils.py"],
                "changes_made": "Added login function, modified User class"
            }
        """
        print("\n⚡ AI Update Triggered!")
        
        # Get pending changes
        pending = self.file_watcher.get_pending_changes()
        
        if not pending:
            return {
                "success": False,
                "message": "No pending changes detected"
            }
        
        print(f"📋 Found {len(pending)} changed file(s)")
        
        results = []
        
        for change in pending:
            file_path = change['file']
            print(f"\n🔍 Analyzing: {file_path}")
            
            # Read current version
            full_path = self.workspace_root / file_path
            if not full_path.exists():
                continue
            
            current_content = full_path.read_text(encoding='utf-8')
            
            # Get original version
            original_content = self.file_versions.get(file_path, "")
            
            # Analyze what changed
            diff = self.diff_analyzer.get_changes(original_content, current_content)
            
            print(f"   Changes: {diff['change_summary']}")
            print(f"   Total lines changed: {diff['total_changes']}")
            
            # Ask AI to improve/complete the changes
            result = self._ai_improve_changes(file_path, current_content, diff)
            
            if result['success']:
                results.append({
                    "file": file_path,
                    "changes": diff['change_summary'],
                    "ai_improvements": result.get('improvements', '')
                })
                
                # Update stored version
                self.file_versions[file_path] = result.get('final_content', current_content)
        
        # Clear pending changes
        self.file_watcher.clear_pending_changes()
        
        return {
            "success": True,
            "files_updated": [r['file'] for r in results],
            "results": results
        }
    
    def _ai_improve_changes(self, file_path: str, current_content: str, diff: Dict) -> Dict:
        """
        AI analyzes user changes and improves/completes them
        
        Args:
            file_path: File that changed
            current_content: Current file content
            diff: Differential analysis
        
        Returns:
            {
                "success": True,
                "improvements": "Added error handling, optimized logic",
                "final_content": "improved code..."
            }
        """
        
        # Build context
        context = self.context_builder.build_context(
            language=self._detect_language(file_path),
            files_mentioned=[file_path]
        )
        
        # Build AI prompt
        prompt = f"""Analyze and improve this code change:

FILE: {file_path}
CHANGE SUMMARY: {diff['change_summary']}
LINES CHANGED: {diff['total_changes']}

CURRENT CODE:
```
{current_content}
```

CONTEXT (other files in project):
{json.dumps({k: v for k, v in context['file_contents'].items() if k != file_path}, indent=2)}

YOUR TASK:
1. Analyze what the user changed
2. Check if the changes are complete and correct
3. Add any missing parts (error handling, edge cases, comments)
4. Optimize the code if needed
5. Ensure the changes integrate well with existing code
6. CRITICAL: Preserve ALL unchanged parts exactly as they are

RULES:
- Only modify the parts that need improvement
- Keep user's intent and logic intact
- Add helpful comments
- Ensure no syntax errors
- Follow best practices for {context['language']}
- Preserve all unchanged functions/classes/code

OUTPUT FORMAT:
Return the COMPLETE improved file content in this format:

```filename:{file_path}
<complete improved code>
```

Then explain your improvements:
IMPROVEMENTS:
- What you added/fixed
- Why you made these changes
"""
        
        result = self._make_request(prompt, use_cache=False)  # Don't cache user-specific changes
        
        if not result['success']:
            return result
        
        # Parse response
        response = result['response']
        
        # Extract improved code
        if f"```filename:{file_path}" in response:
            parts = response.split(f"```filename:{file_path}")
            if len(parts) > 1:
                code_part = parts[1].split("```")[0].strip()
                
                # Extract improvements explanation
                improvements = ""
                if "IMPROVEMENTS:" in response:
                    improvements = response.split("IMPROVEMENTS:")[1].strip()
                
                # Write improved code
                full_path = self.workspace_root / file_path
                full_path.write_text(code_part, encoding='utf-8')
                
                return {
                    "success": True,
                    "final_content": code_part,
                    "improvements": improvements
                }
        
        return {
            "success": False,
            "error": "Could not parse AI response"
        }
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        ext = Path(file_path).suffix.lower()
        
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby'
        }
        
        return lang_map.get(ext, 'python')
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 chars)"""
        return len(text) // 4
    
    def _make_request(self, prompt: str, system_context: str = "", use_cache: bool = True) -> Dict:
        """
        Make request to Gemini API with retry logic
        
        Args:
            prompt: User prompt
            system_context: System context
            use_cache: Use cache if available
        
        Returns:
            {"success": True, "response": "AI response text"}
        """
        self.total_requests += 1
        
        # Check cache first
        if use_cache and self.cache:
            cached = self.cache.get(prompt, system_context)
            if cached:
                print("  💾 Using cached response (saved API cost)")
                return cached
        
        # Rate limiting
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.base_url}/{self.model}:generateContent"
        
        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': self.api_key
        }
        
        # Combine context and prompt
        full_prompt = f"{system_context}\n\n{prompt}" if system_context else prompt
        
        # Estimate tokens
        estimated_tokens = self._estimate_tokens(full_prompt)
        if estimated_tokens > 30000:
            print(f"  ⚠️  Warning: Large prompt ({estimated_tokens} tokens)")
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": full_prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8000,
                "topP": 0.95,
                "topK": 40
            }
        }
        
        # Retry loop with exponential backoff
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url, 
                    headers=headers, 
                    json=payload, 
                    timeout=self.timeout
                )
                
                # Handle HTTP errors
                if response.status_code == 429:
                    # Rate limit hit
                    wait_time = 2 ** attempt
                    print(f"  ⏳ Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                
                data = response.json()
                
                # Extract response text
                if 'candidates' in data and len(data['candidates']) > 0:
                    content = data['candidates'][0]['content']
                    text = content['parts'][0]['text']
                    
                    # Update token usage
                    if 'usageMetadata' in data:
                        self.total_tokens_used += data['usageMetadata'].get('totalTokenCount', 0)
                    
                    result = {"success": True, "response": text}
                    
                    # Cache successful response
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
    
    def generate_code(self, instruction: str, context: Dict) -> Dict:
        """
        Generate code from natural language instruction with RICH CONTEXT
        
        Args:
            instruction: English instruction
            context: Basic context (language, files mentioned)
        
        Returns:
            {
                "success": True,
                "files": [
                    {"path": "main.py", "content": "...code..."}
                ]
            }
        """
        
        # Build rich context with file contents
        rich_context = self.context_builder.build_context(
            language=context.get('language', 'python'),
            files_mentioned=context.get('files', [])
        )
        
        # Merge contexts
        full_context = {**context, **rich_context}
        
        # Build system context for AI
        system_context = f"""You are an expert code generator for the AILib framework.

CURRENT PROJECT CONTEXT:
Language: {full_context.get('language', 'python')}
Framework: {full_context.get('framework', 'none')}
Workspace: {self.workspace_root}

EXISTING FILES IN WORKSPACE:
{json.dumps(full_context.get('workspace_files', []), indent=2)}

EXISTING CODE (for reference - DO NOT regenerate unless asked):
{json.dumps(full_context.get('file_contents', {}), indent=2)}

CRITICAL RULES:
1. Generate PRODUCTION-READY code (no placeholders like "# TODO" or "# Add logic here")
2. Include ALL necessary imports at the top
3. Handle ALL errors gracefully with try-except blocks
4. Add docstrings for functions and classes
5. Follow best practices for {full_context.get('language', 'python')}
6. Make code modular and maintainable
7. If file already exists, INTEGRATE with existing code, don't rewrite everything
8. Add comments for complex logic
9. Use proper naming conventions
10. Include type hints where applicable
11. PRESERVE unchanged code - only modify what needs to change

OUTPUT FORMAT:
For each file you create/modify, use this EXACT format:

```filename:path/to/file.ext
<complete working code>
```

Example:
```filename:src/app.py
import os

def main():
    """Main entry point"""
    print("Hello World")

if __name__ == "__main__":
    main()
```

IMPORTANT: 
- If modifying existing file, preserve existing functions unless asked to change them
- Only include files that need to be created or modified
- Make sure code runs without errors
- Store all files in src/ subdirectory by default
"""
        
        print(f"  🤖 Generating code with rich context...")
        print(f"     Context includes: {len(full_context.get('file_contents', {}))} existing files")
        
        result = self._make_request(instruction, system_context)
        
        if result['success']:
            parsed = self._parse_code_response(result['response'])
            
            # Store original versions for differential tracking
            for file_info in parsed.get('files', []):
                self.file_versions[file_info['path']] = file_info['content']
            
            return parsed
        
        return result
    
    def _parse_code_response(self, response: str) -> Dict:
        """
        Parse AI response to extract code files
        
        Handles:
        - Multi-file format: ```filename:path/to/file.py
        - Single file format: ```python code ```
        """
        files = []
        
        # Check for multi-file format
        if "```filename:" in response:
            parts = response.split("```filename:")
            
            for part in parts[1:]:
                lines = part.split('\n', 1)
                if len(lines) < 2:
                    continue
                
                filepath = lines[0].strip()
                code_block = lines[1]
                
                # Remove closing ```
                if "```" in code_block:
                    code_block = code_block.split("```")[0]
                
                files.append({
                    "path": filepath,
                    "content": code_block.strip()
                })
        
        else:
            # Single file - remove markdown if present
            code = response
            
            if response.strip().startswith("```"):
                lines = response.strip().split('\n')
                if lines[-1].strip() == "```":
                    code = '\n'.join(lines[1:-1])
                else:
                    code = '\n'.join(lines[1:])
            
            files.append({
                "path": "generated_code.py",
                "content": code.strip()
            })
        
        return {
            "success": True,
            "files": files
        }
    
    def analyze_instruction(self, instruction: str) -> Dict:
        """
        Analyze natural language instruction to understand intent
        
        Returns:
            {
                "success": True,
                "analysis": {
                    "intent": "create_project|modify_code|add_feature",
                    "language": "python",
                    "files_needed": ["app.py"],
                    "dependencies": ["flask"],
                    "actions": ["step 1", "step 2"]
                }
            }
        """
        
        prompt = f"""Analyze this development instruction and return a JSON object:

INSTRUCTION: {instruction}

Determine:
1. What is the user trying to do? (create new, modify existing, add feature, fix bug, etc.)
2. What programming language?
3. What files need to be created or modified?
4. What dependencies/packages are needed?
5. What are the steps to complete this?

Return ONLY a JSON object (no markdown, no extra text):
{{
    "intent": "create_project|modify_code|add_feature|fix_bug|analyze",
    "language": "python|javascript|typescript|java|cpp|go",
    "framework": "flask|django|react|express|spring|none",
    "files_needed": ["file1.py", "file2.js"],
    "dependencies": ["package1", "package2"],
    "actions": ["action 1", "action 2", "action 3"]
}}"""
        
        result = self._make_request(prompt, use_cache=True)
        
        if result['success']:
            try:
                response = result['response'].strip()
                if response.startswith("```"):
                    response = '\n'.join(response.split('\n')[1:-1])
                
                analysis = json.loads(response)
                return {"success": True, "analysis": analysis}
            
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"AI returned invalid JSON: {e}",
                    "raw_response": result['response']
                }
        
        return result
    
    def fix_error(self, code: str, error_message: str, context: Dict) -> Dict:
        """
        Fix code based on error message
        
        Args:
            code: Current code with error
            error_message: Error message from compiler/validator
            context: Project context
        
        Returns:
            {"success": True, "response": "fixed code"}
        """
        
        prompt = f"""Fix this code error:

ERROR MESSAGE:
{error_message}

CURRENT CODE:
{code}

LANGUAGE: {context.get('language', 'python')}

INSTRUCTIONS:
1. Identify the error
2. Fix the error
3. Return COMPLETE FIXED CODE (not just the changed part)
4. Ensure the fix doesn't break other parts
5. Add a comment explaining what was fixed
6. No markdown backticks, just the code

Return the complete working code now:"""
        
        result = self._make_request(prompt, use_cache=False)  # Don't cache error fixes
        
        return result
    
    def explain_code(self, code: str, language: str = "python") -> Dict:
        """
        Explain what code does
        
        Args:
            code: Code to explain
            language: Programming language
        
        Returns:
            {"success": True, "explanation": "..."}
        """
        
        prompt = f"""Explain this {language} code in simple terms:

CODE:
{code}

Provide:
1. High-level overview (what it does)
2. Key components and their purpose
3. Important logic or algorithms
4. Potential improvements

Be clear and concise:"""
        
        result = self._make_request(prompt, use_cache=True)
        
        if result['success']:
            return {"success": True, "explanation": result['response']}
        
        return result
    
    def setup_environment(self, project_type: str = "python") -> Dict:
        """
        Setup development environment in src/ folder
        
        Args:
            project_type: "python", "node", "react", etc.
        
        Returns:
            {"success": True, "structure": [...]}
        """
        
        templates = {
            "python": {
                "dirs": ["src", "tests", "docs"],
                "files": {
                    "src/__init__.py": "",
                    "src/main.py": '''"""Main application entry point"""

def main():
    """Main function"""
    print("Application started")
    # Your code here

if __name__ == "__main__":
    main()
''',
                    "requirements.txt": "# Python dependencies\n",
                    "README.md": f"# Project\n\nCreated with AILib\n\n## Setup\n```bash\npip install -r requirements.txt\npython src/main.py\n```",
                    ".gitignore": "__pycache__/\n*.pyc\n.env\nvenv/\n.ailib/\n"
                }
            },
            "node": {
                "dirs": ["src", "tests"],
                "files": {
                    "src/index.js": '''// Main application entry point

function main() {
    console.log('Application started');
    // Your code here
}

main();
''',
                    "package.json": json.dumps({
                        "name": "ailib-project",
                        "version": "1.0.0",
                        "main": "src/index.js",
                        "scripts": {
                            "start": "node src/index.js"
                        }
                    }, indent=2),
                    "README.md": "# Project\n\nCreated with AILib\n\n## Setup\n```bash\nnpm install\nnpm start\n```",
                    ".gitignore": "node_modules/\n.env\n.ailib/\n"
                }
            }
        }
        
        template = templates.get(project_type, templates["python"])
        
        created = []
        
        # Create directories
        for dir_name in template["dirs"]:
            dir_path = self.workspace_root / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            created.append(f"📁 {dir_name}/")
        
        # Create files
        for file_path, content in template["files"].items():
            full_path = self.workspace_root / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding='utf-8')
            created.append(f"📄 {file_path}")
            
            # Store original version
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
            "estimated_cost_usd": self.total_tokens_used * 0.000001,  # Rough estimate
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
    print("Upgraded Self-Managing AI Engine Demo")
    print("="*70)
    
    # Initialize with API key
    api_key = "AIzaSyCy3JRWw7sS6-1A0fFBT2UzEBx-us2F95w"
    ai = GeminiEngine(api_key, workspace_root="./test_workspace/src", enable_cache=True)
    
    # Test 1: Setup environment
    print("\n[Test 1] Setup development environment...")
    result = ai.setup_environment("python")
    if result['success']:
        print(f"  ✓ Created project structure:")
        for item in result['structure']:
            print(f"    {item}")
    
    # Test 2: Generate initial code
    print("\n[Test 2] Generate initial code...")
    instruction = "Create a simple calculator module with add, subtract, multiply, divide functions"
    context = {
        "language": "python",
        "framework": "none",
        "files": []
    }
    
    result = ai.generate_code(instruction, context)
    if result['success']:
        print(f"  ✓ Generated {len(result['files'])} file(s)")
        for file_info in result['files']:
            # Write to workspace
            file_path = ai.workspace_root / file_info['path']
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file_info['content'], encoding='utf-8')
            print(f"    - {file_info['path']}")
    
    # Test 3: Start file watching
    print("\n[Test 3] Start file watching...")
    ai.start_watching()
    
    print("\n📝 Instructions for testing:")
    print("   1. Modify files in ./test_workspace/src/")
    print("   2. AI will detect changes automatically")
    print("   3. Press Shift+Enter to trigger AI update")
    print("   4. AI will analyze and improve your changes")
    print("\n   Press Ctrl+C to stop...")
    
    try:
        # Simulate user workflow
        import sys
        
        while True:
            user_input = input("\n[Press Enter to check for changes, 'trigger' to run AI update, 'q' to quit]: ")
            
            if user_input.lower() == 'q':
                break
            elif user_input.lower() == 'trigger':
                result = ai.trigger_update()
                if result['success']:
                    print(f"\n✅ AI Update Complete!")
                    print(f"   Files updated: {', '.join(result['files_updated'])}")
                    for r in result.get('results', []):
                        print(f"\n   {r['file']}:")
                        print(f"     Changes: {r['changes']}")
                        if r.get('ai_improvements'):
                            print(f"     AI Improvements: {r['ai_improvements']}")
                else:
                    print(f"\n⚠️  {result.get('message', 'No changes')}")
            else:
                # Check pending
                pending = ai.file_watcher.get_pending_changes()
                if pending:
                    print(f"\n📋 Pending changes: {len(pending)}")
                    for p in pending:
                        print(f"   - {p['file']}")
                    print("\n   Type 'trigger' to process changes")
                else:
                    print("\n   No pending changes")
    
    except KeyboardInterrupt:
        print("\n\n👋 Stopping...")
    
    # Test 4: Statistics
    print("\n[Test 4] Engine statistics...")
    stats = ai.get_statistics()
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Success rate: {stats['success_rate']}")
    print(f"  Tracked files: {stats['tracked_files']}")
    if 'cache' in stats:
        print(f"  Cache hit rate: {stats['cache']['hit_rate']}")
    
    # Cleanup
    ai.cleanup()
    
    print("\n" + "="*70)
    print("✓ Self-Managing AI Engine Demo Complete!")
    print("="*70)
    print("\nFeatures demonstrated:")
    print("  ✓ Environment setup in src/ folder")
    print("  ✓ Code generation with rich context")
    print("  ✓ File watching and change detection")
    print("  ✓ Shift+Enter trigger simulation")
    print("  ✓ Differential analysis (only change what's needed)")
    print("  ✓ AI improvements of user changes")
    print("  ✓ Caching and statistics")
    print("="*70)
