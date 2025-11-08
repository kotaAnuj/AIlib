"""
================================================================================
FILE: AILib/config.py
PURPOSE: Manage API keys and project configuration
DEPENDENCIES: None (standalone)
================================================================================
"""

import json
from pathlib import Path
from typing import Dict, Optional


class AILibConfig:
    """
    Manages AILib configuration:
    - API keys for AI providers (Gemini, OpenAI, etc.)
    - Project settings
    - User preferences
    
    Configuration is stored in: .ailib/config.json
    """
    
    def __init__(self, project_root: str = "."):
        """
        Initialize configuration manager
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.config_file = self.project_root / ".ailib" / "config.json"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load configuration from file"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {
            "api_keys": {},
            "settings": {
                "auto_fix": True,
                "auto_test": True,
                "max_retries": 3
            }
        }
    
    def save_config(self, config: Dict = None):
        """Save configuration to file"""
        if config is None:
            config = self.config
        
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        self.config = config
        print(f"✓ Configuration saved to {self.config_file}")
    
    def set_api_key(self, provider: str, api_key: str):
        """
        Set API key for AI provider
        
        Args:
            provider: "gemini", "openai", "claude", etc.
            api_key: API key string
        
        Example:
            config.set_api_key("gemini", "AIzaSy...")
        """
        if 'api_keys' not in self.config:
            self.config['api_keys'] = {}
        
        self.config['api_keys'][provider] = api_key
        self.save_config(self.config)
        print(f"✓ {provider} API key configured")
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for provider
        
        Args:
            provider: AI provider name
        
        Returns:
            API key string or None if not configured
        """
        return self.config.get('api_keys', {}).get(provider)
    
    def get_setting(self, key: str, default=None):
        """Get a setting value"""
        return self.config.get('settings', {}).get(key, default)
    
    def set_setting(self, key: str, value):
        """Set a setting value"""
        if 'settings' not in self.config:
            self.config['settings'] = {}
        
        self.config['settings'][key] = value
        self.save_config(self.config)


# ================================================================================
# DEMO - How to use
# ================================================================================

if __name__ == "__main__":
    print("="*70)
    print("AILib Config Demo")
    print("="*70)
    
    # Create config manager
    config = AILibConfig(project_root="./test_project")
    
    # Set API key
    config.set_api_key("gemini", "AIzaSyCy3JRWw7sS6-1A0fFBT2UzEBx-us2F95w")
    
    # Get API key
    key = config.get_api_key("gemini")
    print(f"\nAPI Key: {key[:20]}...")
    
    # Set settings
    config.set_setting("auto_fix", True)
    config.set_setting("max_retries", 5)
    
    # Get settings
    auto_fix = config.get_setting("auto_fix")
    print(f"Auto-fix enabled: {auto_fix}")
    
    print("\n✓ Configuration ready!")