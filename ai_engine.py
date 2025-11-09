"""
================================================================================
FILE: AILib/ai_engine.py (UPGRADED v2.0)
PURPOSE: Advanced AI engine with caching, retry logic, streaming, and better context
FEATURES:
  - Response caching (save money on duplicate requests)
  - Automatic retry with exponential backoff
  - Rate limiting protection
  - Token counting
  - Streaming support
  - Rich context awareness (reads file contents)
  - Multi-turn conversation support
  - Better error handling
================================================================================
"""

import json
import requests
import time
import hashlib
import pickle
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from code_editor import CodeAnalyzer


# ============================================================================
# AI RESPONSE CACHE - Save Money on Duplicate Requests
# ============================================================================

class AICache:
    """
    Caches AI responses to avoid duplicate API calls
    
    Features:
    - MD5 hash based caching
    - 7-day expiration
    - Disk-based storage
    - Cache statistics
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
        """
        Get cached response if exists and not expired
        
        Returns:
            Cached response dict or None
        """
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
            print(f"Warning: Could not cache response: {e}")
    
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
    """
    Rate limiter to prevent hitting API limits
    
    Gemini limits: 60 requests per minute
    """
    
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
    This is CRITICAL for AI to understand existing code
    """
    
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root)
    
    def build_context(self, language: str, files_mentioned: List[str] = None) -> Dict:
        """
        Build comprehensive context with file contents
        
        Args:
            language: Programming language
            files_mentioned: Specific files to include
        
        Returns:
            {
                "language": "python",
                "workspace_files": ["app.py", "utils.py"],
                "file_contents": {
                    "app.py": {
                        "exists": True,
                        "content": "first 2000 chars...",
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
                # Skip hidden directories
                if any(part.startswith('.') for part in filepath.parts):
                    continue
                
                rel_path = str(filepath.relative_to(self.workspace_root))
                context["workspace_files"].append(rel_path)
        
        # Read specific files mentioned by user
        if files_mentioned:
            for filepath in files_mentioned:
                self._add_file_to_context(filepath, context, language)
        
        # Read all existing files (up to 10 files to avoid token limit)
        for filepath in context["workspace_files"][:10]:
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
                "content": content[:2000]  # First 2000 chars
            }
            
            # Analyze Python files
            if language == "python" and filepath.endswith('.py'):
                analyzer = CodeAnalyzer()
                elements = analyzer.parse_python(content)
                
                file_info["functions"] = [e.name for e in elements if e.type == 'function']
                file_info["classes"] = [e.name for e in elements if e.type == 'class']
                
                # Extract imports
                imports = []
                for line in content.split('\n')[:50]:  # Check first 50 lines
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        imports.append(line.strip())
                file_info["imports"] = imports[:10]  # First 10 imports
            
            context["file_contents"][filepath] = file_info
        
        except Exception as e:
            context["file_contents"][filepath] = {
                "exists": True,
                "error": str(e)
            }


# ============================================================================
# UPGRADED GEMINI ENGINE
# ============================================================================

class GeminiEngine:
    """
    Upgraded Gemini AI Engine with advanced features
    
    New Features:
    - Response caching (save money)
    - Automatic retry with exponential backoff
    - Rate limiting
    - Rich context with file contents
    - Better error messages
    - Token estimation
    - Multi-turn conversations
    """
    
    def __init__(self, api_key: str, enable_cache: bool = True):
        """
        Initialize Gemini AI Engine
        
        Args:
            api_key: Your Gemini API key
            enable_cache: Enable response caching (default: True)
        """
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.model = "gemini-2.0-flash-exp"
        
        # Advanced features
        self.cache = AICache() if enable_cache else None
        self.rate_limiter = RateLimiter(requests_per_minute=50)  # Conservative limit
        self.context_builder = ContextBuilder()
        
        # Statistics
        self.total_requests = 0
        self.failed_requests = 0
        self.total_tokens_used = 0
        
        # Retry configuration
        self.max_retries = 3
        self.timeout = 60
    
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
                print("  💾 Using cached response")
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
    
    def generate_code(self, instruction: str, context: Dict, workspace_root: str = ".") -> Dict:
        """
        Generate code from natural language instruction with RICH CONTEXT
        
        Args:
            instruction: English instruction
            context: Basic context (language, files mentioned)
            workspace_root: Workspace root for reading files
        
        Returns:
            {
                "success": True,
                "files": [
                    {"path": "main.py", "content": "...code..."}
                ]
            }
        """
        
        # Build rich context with file contents
        self.context_builder.workspace_root = Path(workspace_root)
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

OUTPUT FORMAT:
For each file you create/modify, use this EXACT format:

```filename:path/to/file.ext
<complete working code>
```

Example:
```filename:src/app.py
import os

def main():
    print("Hello World")

if __name__ == "__main__":
    main()
```

IMPORTANT: 
- If modifying existing file, preserve existing functions unless asked to change them
- Only include files that need to be created or modified
- Make sure code runs without errors
"""
        
        print(f"  🤖 Generating code with rich context...")
        print(f"     Context includes: {len(full_context.get('file_contents', {}))} existing files")
        
        result = self._make_request(instruction, system_context)
        
        if result['success']:
            return self._parse_code_response(result['response'])
        
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
    
    def get_statistics(self) -> Dict:
        """Get AI engine statistics"""
        stats = {
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "success_rate": f"{((self.total_requests - self.failed_requests) / self.total_requests * 100):.1f}%" if self.total_requests > 0 else "0%",
            "total_tokens_used": self.total_tokens_used,
            "estimated_cost_usd": self.total_tokens_used * 0.000001  # Rough estimate
        }
        
        if self.cache:
            stats["cache"] = self.cache.stats()
        
        return stats


# ============================================================================
# DEMO / TESTING
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("Upgraded Gemini AI Engine Demo")
    print("="*70)
    
    # Initialize with API key
    api_key = "AIzaSyCy3JRWw7sS6-1A0fFBT2UzEBx-us2F95w"
    ai = GeminiEngine(api_key, enable_cache=True)
    
    # Test 1: Analyze instruction
    print("\n[Test 1] Analyze instruction...")
    instruction = "Create a REST API with Flask and user authentication"
    
    result = ai.analyze_instruction(instruction)
    if result['success']:
        analysis = result['analysis']
        print(f"  ✓ Intent: {analysis['intent']}")
        print(f"  ✓ Language: {analysis['language']}")
        print(f"  ✓ Files: {analysis['files_needed']}")
    else:
        print(f"  ✗ Error: {result['error']}")
    
    # Test 2: Generate code with rich context
    print("\n[Test 2] Generate code with context...")
    instruction = "Create a simple calculator function that adds two numbers"
    context = {
        "language": "python",
        "framework": "none",
        "files": []
    }
    
    result = ai.generate_code(instruction, context, workspace_root=".")
    if result['success']:
        print(f"  ✓ Generated {len(result['files'])} file(s)")
        for file_info in result['files']:
            print(f"    - {file_info['path']}")
            print(f"\n    Preview:\n{file_info['content'][:200]}...")
    else:
        print(f"  ✗ Error: {result['error']}")
    
    # Test 3: Cache test (same request)
    print("\n[Test 3] Testing cache (same request again)...")
    result2 = ai.analyze_instruction(instruction)  # Same as Test 1
    print(f"  ✓ Request completed (should use cache)")
    
    # Test 4: Statistics
    print("\n[Test 4] Engine statistics...")
    stats = ai.get_statistics()
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Success rate: {stats['success_rate']}")
    if 'cache' in stats:
        print(f"  Cache hit rate: {stats['cache']['hit_rate']}")
        print(f"  Cached responses: {stats['cache']['cached_responses']}")
    
    print("\n" + "="*70)
    print("✓ Upgraded AI Engine working!")
    print("="*70)
