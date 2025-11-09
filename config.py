"""
================================================================================
FILE: AILib/config.py
PURPOSE: Configuration management for AILib
FEATURES:
  - API key storage and retrieval
  - Project settings management
  - Secure credential handling
================================================================================
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict


class AILibConfig:
    """
    Manages AILib configuration including API keys and project settings
    
    Configuration is stored in:
    - workspace/.ailib/config.json (API keys, settings)
    - workspace/.ailib/project.json (Project-specific config)
    """
    
    def __init__(self, project_root: str = "."):
        """
        Initialize configuration manager
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root).resolve()
        self.config_dir = self.project_root / ".ailib"
        self.config_file = self.config_dir / "config.json"
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize config file if it doesn't exist
        if not self.config_file.exists():
            self._init_config()
    
    def _init_config(self):
        """Initialize default configuration"""
        default_config = {
            "version": "4.0",
            "api_keys": {
                "gemini": None,
                "openai": None,
                "anthropic": None
            },
            "settings": {
                "cache_enabled": True,
                "auto_install_dependencies": True,
                "default_language": "python",
                "max_cache_age_days": 7,
                "rate_limit_per_minute": 50
            },
            "created": self._get_timestamp()
        }
        
        self._save_config(default_config)
    
    def _load_config(self) -> Dict:
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Error loading config: {e}")
            return {}
    
    def _save_config(self, config: Dict):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"⚠️  Error saving config: {e}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    # ========== API KEY MANAGEMENT ==========
    
    def set_api_key(self, provider: str, api_key: str) -> bool:
        """
        Set API key for a provider
        
        Args:
            provider: Provider name (gemini, openai, anthropic)
            api_key: API key string
        
        Returns:
            True if successful, False otherwise
        """
        try:
            config = self._load_config()
            
            if "api_keys" not in config:
                config["api_keys"] = {}
            
            config["api_keys"][provider.lower()] = api_key
            config["last_updated"] = self._get_timestamp()
            
            self._save_config(config)
            return True
        
        except Exception as e:
            print(f"⚠️  Error setting API key: {e}")
            return False
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a provider
        
        Args:
            provider: Provider name (gemini, openai, anthropic)
        
        Returns:
            API key string or None if not found
        """
        try:
            config = self._load_config()
            return config.get("api_keys", {}).get(provider.lower())
        except:
            return None
    
    def remove_api_key(self, provider: str) -> bool:
        """Remove API key for a provider"""
        try:
            config = self._load_config()
            
            if "api_keys" in config and provider.lower() in config["api_keys"]:
                config["api_keys"][provider.lower()] = None
                config["last_updated"] = self._get_timestamp()
                self._save_config(config)
                return True
            
            return False
        except:
            return False
    
    def has_api_key(self, provider: str) -> bool:
        """Check if API key is set for provider"""
        api_key = self.get_api_key(provider)
        return api_key is not None and len(api_key) > 0
    
    # ========== SETTINGS MANAGEMENT ==========
    
    def get_setting(self, key: str, default=None):
        """Get a configuration setting"""
        try:
            config = self._load_config()
            return config.get("settings", {}).get(key, default)
        except:
            return default
    
    def set_setting(self, key: str, value) -> bool:
        """Set a configuration setting"""
        try:
            config = self._load_config()
            
            if "settings" not in config:
                config["settings"] = {}
            
            config["settings"][key] = value
            config["last_updated"] = self._get_timestamp()
            
            self._save_config(config)
            return True
        except:
            return False
    
    def get_all_settings(self) -> Dict:
        """Get all settings"""
        try:
            config = self._load_config()
            return config.get("settings", {})
        except:
            return {}
    
    # ========== UTILITY METHODS ==========
    
    def reset_config(self):
        """Reset configuration to defaults"""
        self._init_config()
    
    def export_config(self, filepath: str, include_api_keys: bool = False) -> bool:
        """
        Export configuration to file
        
        Args:
            filepath: Path to export file
            include_api_keys: Whether to include API keys (security risk!)
        
        Returns:
            True if successful
        """
        try:
            config = self._load_config()
            
            if not include_api_keys:
                # Remove API keys for security
                if "api_keys" in config:
                    config["api_keys"] = {k: "***HIDDEN***" for k in config["api_keys"]}
            
            with open(filepath, 'w') as f:
                json.dump(config, f, indent=2)
            
            return True
        except:
            return False
    
    def get_config_path(self) -> str:
        """Get path to configuration file"""
        return str(self.config_file)
    
    def config_exists(self) -> bool:
        """Check if configuration file exists"""
        return self.config_file.exists()


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("AILib Configuration Manager Demo")
    print("="*70)
    
    # Initialize config
    config = AILibConfig(project_root="./test_workspace")
    
    print("\n[Test 1] Set API Key")
    success = config.set_api_key("gemini", "AIzaSyCy3JRWw7sS6-1A0fFBT2UzEBx-us2F95w")
    print(f"  ✓ API key set: {success}")
    
    print("\n[Test 2] Retrieve API Key")
    api_key = config.get_api_key("gemini")
    print(f"  ✓ API key: {api_key[:20]}..." if api_key else "  ✗ No API key found")
    
    print("\n[Test 3] Check if API key exists")
    has_key = config.has_api_key("gemini")
    print(f"  ✓ Has Gemini key: {has_key}")
    
    print("\n[Test 4] Settings Management")
    config.set_setting("cache_enabled", True)
    config.set_setting("default_language", "python")
    cache_enabled = config.get_setting("cache_enabled")
    print(f"  ✓ Cache enabled: {cache_enabled}")
    
    print("\n[Test 5] Get All Settings")
    settings = config.get_all_settings()
    print(f"  ✓ Settings: {json.dumps(settings, indent=2)}")
    
    print("\n[Test 6] Export Config (without API keys)")
    success = config.export_config("./test_workspace/config_export.json", include_api_keys=False)
    print(f"  ✓ Export successful: {success}")
    
    print("\n[Test 7] Configuration Path")
    path = config.get_config_path()
    print(f"  ✓ Config location: {path}")
    
    print("\n" + "="*70)
    print("✓ Configuration Manager Demo Complete!")
    print("="*70)
