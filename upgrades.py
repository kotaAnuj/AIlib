"""
================================================================================
FILE: AILib/upgrades.py
PURPOSE: Critical upgrades for AILib - Better context, caching, rollback
ADD THIS TO YOUR EXISTING FILES
================================================================================
"""

import json
import pickle
import hashlib
import shutil
from pathlib import Path
from typing import Dict, List
from datetime import datetime


# ============================================================================
# UPGRADE 1: BETTER CONTEXT MANAGER
# ============================================================================
# ADD THIS TO ailib_core.py

class ContextBuilder:
    """
    Builds rich context for AI by reading existing files
    This makes AI aware of what code already exists
    """
    
    def __init__(self, dev_manager, project_root):
        self.dev_manager = dev_manager
        self.project_root = Path(project_root)
    
    def build_rich_context(self, schema) -> Dict:
        """
        Build comprehensive context with file contents
        
        Returns:
            {
                "language": "python",
                "framework": "flask",
                "files": {
                    "src/app.py": {
                        "content": "...first 1000 chars...",
                        "functions": ["main", "setup"],
                        "classes": ["App"],
                        "lines": 50
                    }
                }
            }
        """
        from code_editor import CodeAnalyzer
        
        context = {
            "language": schema.language if schema else "python",
            "framework": schema.framework if schema else "none",
            "files": {}
        }
        
        # Find all relevant code files
        patterns = {
            "python": "**/*.py",
            "javascript": "**/*.js",
            "typescript": "**/*.ts"
        }
        
        pattern = patterns.get(context["language"], "**/*.py")
        
        for file_path in self.project_root.glob(pattern):
            # Skip irrelevant directories
            if any(skip in str(file_path) for skip in [".ailib", "venv", "node_modules", "__pycache__"]):
                continue
            
            try:
                rel_path = str(file_path.relative_to(self.project_root))
                
                # Read file
                result = self.dev_manager.fs.read_file(rel_path)
                if not result['success']:
                    continue
                
                content = result['content']
                
                # Analyze structure (for Python)
                file_info = {
                    "size": len(content),
                    "lines": len(content.split('\n')),
                    "content_preview": content[:1000]  # First 1000 chars
                }
                
                if context["language"] == "python":
                    analyzer = CodeAnalyzer()
                    elements = analyzer.parse_python(content)
                    
                    file_info["functions"] = [e.name for e in elements if e.type == 'function']
                    file_info["classes"] = [e.name for e in elements if e.type == 'class']
                
                context["files"][rel_path] = file_info
            
            except Exception as e:
                # Skip files that can't be read
                continue
        
        return context


# ============================================================================
# UPGRADE 2: AI RESPONSE CACHE
# ============================================================================
# ADD THIS TO ai_engine.py

class AICache:
    """
    Caches AI responses to save API calls and money
    """
    
    def __init__(self, cache_dir: str = ".ailib/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Stats
        self.hits = 0
        self.misses = 0
    
    def _get_cache_key(self, prompt: str, context: str = "") -> str:
        """Generate cache key from prompt + context"""
        combined = f"{prompt}::{context}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def get(self, prompt: str, context: str = "") -> Dict:
        """Get cached response"""
        cache_key = self._get_cache_key(prompt, context)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cached = pickle.load(f)
                
                # Check if cache is recent (within 7 days)
                age_days = (datetime.now() - cached['timestamp']).days
                if age_days < 7:
                    self.hits += 1
                    print(f"  💾 Using cached response (saved API call)")
                    return cached['data']
            except:
                pass
        
        self.misses += 1
        return None
    
    def set(self, prompt: str, context: str, data: Dict):
        """Cache a response"""
        cache_key = self._get_cache_key(prompt, context)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        cached = {
            'timestamp': datetime.now(),
            'data': data
        }
        
        with open(cache_file, 'wb') as f:
            pickle.dump(cached, f)
    
    def clear(self):
        """Clear all cache"""
        for cache_file in self.cache_dir.glob("*.pkl"):
            cache_file.unlink()
        
        self.hits = 0
        self.misses = 0
    
    def stats(self) -> Dict:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total,
            "hit_rate": f"{hit_rate:.1f}%",
            "cache_size": len(list(self.cache_dir.glob("*.pkl")))
        }


# ============================================================================
# UPGRADE 3: BACKUP & ROLLBACK SYSTEM
# ============================================================================
# ADD THIS TO ailib_core.py

class BackupManager:
    """
    Creates backups before risky operations
    Can rollback on failure
    """
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / ".ailib" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, label: str = None) -> str:
        """
        Create backup of entire project
        
        Returns:
            backup_id: Unique ID for this backup
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = f"{timestamp}_{label}" if label else timestamp
        
        backup_path = self.backup_dir / backup_id
        
        # Copy all files except .ailib directory
        for item in self.project_root.iterdir():
            if item.name == ".ailib":
                continue
            
            dest = backup_path / item.name
            
            if item.is_file():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest)
            elif item.is_dir():
                shutil.copytree(item, dest, ignore=shutil.ignore_patterns('*.pyc', '__pycache__'))
        
        print(f"  💾 Backup created: {backup_id}")
        
        # Keep only last 10 backups
        self._cleanup_old_backups(keep=10)
        
        return backup_id
    
    def restore_backup(self, backup_id: str) -> bool:
        """
        Restore project from backup
        
        Args:
            backup_id: ID returned from create_backup()
        
        Returns:
            True if successful
        """
        backup_path = self.backup_dir / backup_id
        
        if not backup_path.exists():
            print(f"  ❌ Backup not found: {backup_id}")
            return False
        
        # Remove current files (except .ailib)
        for item in self.project_root.iterdir():
            if item.name == ".ailib":
                continue
            
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        
        # Restore from backup
        for item in backup_path.iterdir():
            dest = self.project_root / item.name
            
            if item.is_file():
                shutil.copy2(item, dest)
            elif item.is_dir():
                shutil.copytree(item, dest)
        
        print(f"  ✅ Restored from backup: {backup_id}")
        return True
    
    def list_backups(self) -> List[Dict]:
        """List all available backups"""
        backups = []
        
        for backup_path in sorted(self.backup_dir.iterdir()):
            if backup_path.is_dir():
                # Get backup info
                stat = backup_path.stat()
                
                backups.append({
                    "id": backup_path.name,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "size": sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file())
                })
        
        return backups
    
    def _cleanup_old_backups(self, keep: int = 10):
        """Keep only the most recent N backups"""
        backups = sorted(self.backup_dir.iterdir(), key=lambda p: p.stat().st_ctime)
        
        # Delete oldest backups
        for old_backup in backups[:-keep]:
            if old_backup.is_dir():
                shutil.rmtree(old_backup)


# ============================================================================
# UPGRADE 4: BETTER ERROR MESSAGES
# ============================================================================

class AILibError(Exception):
    """Base exception for AILib"""
    pass


class APIKeyMissingError(AILibError):
    """API key not configured"""
    
    def __str__(self):
        return """
❌ Gemini API Key Not Found!

Get your API key:
  1. Visit: https://makersuite.google.com/app/apikey
  2. Click "Create API Key"
  3. Copy the key

Configure it:
  ailib config YOUR_API_KEY

Or manually edit .ailib/config.json:
  {
    "api_keys": {
      "gemini": "YOUR_KEY_HERE"
    }
  }
"""


class ProjectNotFoundError(AILibError):
    """No project.ailib found"""
    
    def __str__(self):
        return """
❌ No AILib Project Found!

Initialize a new project:
  ailib init my_project

Or create project.ailib manually:
  {
    "name": "my_app",
    "language": "python",
    "framework": "flask",
    "instructions": [
      "Your instructions here"
    ]
  }
"""


class InstructionFailedError(AILibError):
    """Instruction execution failed"""
    
    def __init__(self, instruction: str, error: str):
        self.instruction = instruction
        self.error = error
    
    def __str__(self):
        return f"""
❌ Instruction Failed!

Instruction: {self.instruction}
Error: {self.error}

Troubleshooting:
  1. Check if instruction is clear and specific
  2. Verify API key is valid: ailib config YOUR_KEY
  3. Check internet connection
  4. Review .ailib/execution_log.json for details
"""


# ============================================================================
# HOW TO INTEGRATE THESE UPGRADES
# ============================================================================

"""
INTEGRATION GUIDE:

1. ADD TO ai_engine.py (GeminiEngine class):

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "..."
        self.model = "gemini-2.0-flash"
        
        # ADD THIS:
        self.cache = AICache()
    
    def _make_request(self, prompt: str, system_context: str = "") -> Dict:
        # ADD THIS AT START:
        cached = self.cache.get(prompt, system_context)
        if cached:
            return cached
        
        # ... existing API call code ...
        
        # ADD THIS AFTER SUCCESSFUL API CALL:
        if result['success']:
            self.cache.set(prompt, system_context, result)
        
        return result


2. ADD TO ailib_core.py (AILib class):

    def __init__(self, project_root: str = "."):
        # ... existing code ...
        
        # ADD THESE:
        self.context_builder = ContextBuilder(self.dev_manager, project_root)
        self.backup_manager = BackupManager(str(project_root))
    
    def execute_instruction(self, instruction: str) -> Dict:
        # ADD THIS AT START:
        backup_id = self.backup_manager.create_backup(
            label=instruction[:30].replace(" ", "_")
        )
        
        try:
            # ... existing execution code ...
            
            # If error occurs:
            if not result['success']:
                print("  🔄 Rolling back changes...")
                self.backup_manager.restore_backup(backup_id)
                raise InstructionFailedError(instruction, result['error'])
        
        except Exception as e:
            # Rollback on any error
            self.backup_manager.restore_backup(backup_id)
            raise
    
    def _build_context(self):
        # REPLACE OLD build_context with:
        return self.context_builder.build_rich_context(self.schema)


3. ADD BETTER ERROR HANDLING:

    Replace:
        if not self.ai:
            return {"success": False, "error": "API key not set"}
    
    With:
        if not self.ai:
            raise APIKeyMissingError()


4. ADD CLI COMMANDS FOR NEW FEATURES:

    def cli():
        # Add these commands:
        
        elif command == "backup":
            ailib = AILib()
            backup_id = ailib.backup_manager.create_backup("manual")
            print(f"Backup created: {backup_id}")
        
        elif command == "restore":
            backup_id = sys.argv[2] if len(sys.argv) > 2 else None
            ailib = AILib()
            backups = ailib.backup_manager.list_backups()
            
            if not backup_id and backups:
                # Show available backups
                print("Available backups:")
                for b in backups:
                    print(f"  {b['id']} - {b['created']}")
            elif backup_id:
                ailib.backup_manager.restore_backup(backup_id)
        
        elif command == "cache":
            subcommand = sys.argv[2] if len(sys.argv) > 2 else "stats"
            
            ailib = AILib()
            
            if subcommand == "clear":
                ailib.ai.cache.clear()
                print("Cache cleared")
            else:
                stats = ailib.ai.cache.stats()
                print(f"Cache Statistics:")
                print(f"  Hits: {stats['hits']}")
                print(f"  Misses: {stats['misses']}")
                print(f"  Hit Rate: {stats['hit_rate']}")
                print(f"  Cached Responses: {stats['cache_size']}")
"""


# ============================================================================
# TESTING THE UPGRADES
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("Testing AILib Upgrades")
    print("="*70)
    
    # Test 1: Cache
    print("\n[Test 1] AI Cache")
    cache = AICache(cache_dir="./test_cache")
    
    # First request (cache miss)
    result = cache.get("Create Flask app", context="python")
    print(f"  First request: {'HIT' if result else 'MISS'}")
    
    # Save to cache
    cache.set("Create Flask app", "python", {"success": True, "code": "..."})
    
    # Second request (cache hit)
    result = cache.get("Create Flask app", context="python")
    print(f"  Second request: {'HIT' if result else 'MISS'}")
    
    print(f"  Stats: {cache.stats()}")
    
    # Test 2: Backup
    print("\n[Test 2] Backup Manager")
    backup = BackupManager(project_root="./test_backup")
    
    # Create test file
    Path("./test_backup/test.txt").write_text("Original content")
    
    # Create backup
    backup_id = backup.create_backup(label="test")
    print(f"  Created backup: {backup_id}")
    
    # Modify file
    Path("./test_backup/test.txt").write_text("Modified content")
    print(f"  Modified file")
    
    # Restore backup
    backup.restore_backup(backup_id)
    content = Path("./test_backup/test.txt").read_text()
    print(f"  Restored: '{content}'")
    
    # Test 3: Error Messages
    print("\n[Test 3] Better Error Messages")
    try:
        raise APIKeyMissingError()
    except AILibError as e:
        print(str(e))
    
    print("\n" + "="*70)
    print("✓ All upgrades working!")
    print("="*70)
