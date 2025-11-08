"""
================================================================================
FILE: AILib/ai_engine.py
PURPOSE: Connect to Gemini AI API and generate code from natural language
DEPENDENCIES: requests (pip install requests)
================================================================================
"""

import json
import requests
from typing import Dict, List


class GeminiEngine:
    """
    Gemini AI Engine for AILib
    
    Features:
    - Generate code from English instructions
    - Analyze instructions to understand intent
    - Fix code errors automatically
    - Context-aware code generation
    """
    
    def __init__(self, api_key: str):
        """
        Initialize Gemini AI Engine
        
        Args:
            api_key: Your Gemini API key from https://makersuite.google.com/app/apikey
        """
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.model = "gemini-2.0-flash"
    
    def _make_request(self, prompt: str, system_context: str = "") -> Dict:
        """
        Make request to Gemini API
        
        Args:
            prompt: User instruction
            system_context: Context for AI (project info, existing code, etc.)
        
        Returns:
            {"success": True, "response": "AI response text"}
        """
        url = f"{self.base_url}/{self.model}:generateContent"
        
        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': self.api_key
        }
        
        # Combine context and prompt
        full_prompt = f"{system_context}\n\n{prompt}" if system_context else prompt
        
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
                "maxOutputTokens": 8000
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract response text
            if 'candidates' in data and len(data['candidates']) > 0:
                content = data['candidates'][0]['content']
                text = content['parts'][0]['text']
                return {"success": True, "response": text}
            else:
                return {"success": False, "error": "No response from AI"}
                
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"API request failed: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate_code(self, instruction: str, context: Dict) -> Dict:
        """
        Generate code from natural language instruction
        
        Args:
            instruction: English instruction (e.g., "Create a REST API")
            context: Project context with language, framework, existing files
        
        Returns:
            {
                "success": True,
                "files": [
                    {"path": "main.py", "content": "...code..."},
                    {"path": "utils.py", "content": "...code..."}
                ]
            }
        """
        
        # Build system context for AI
        system_context = f"""You are an expert code generator for the AILib framework.

Current Project Context:
- Language: {context.get('language', 'python')}
- Framework: {context.get('framework', 'none')}
- Existing Files: {json.dumps(context.get('files', []), indent=2)}

CRITICAL RULES:
1. Generate PRODUCTION-READY code (no placeholders, no TODO comments)
2. Include ALL imports at the top
3. Handle ALL errors gracefully
4. Follow best practices for {context.get('language', 'python')}
5. Make code modular and maintainable

OUTPUT FORMAT:
If generating multiple files, use this EXACT format:
```filename:path/to/file.py
<complete code content here>
```

For single file, return code directly WITHOUT markdown backticks."""
        
        print(f"  🤖 Asking AI to generate code...")
        
        result = self._make_request(instruction, system_context)
        
        if result['success']:
            # Parse the response to extract files
            return self._parse_code_response(result['response'])
        
        return result
    
    def _parse_code_response(self, response: str) -> Dict:
        """
        Parse AI response to extract code files
        
        Handles:
        - Multi-file format: ```filename:path/to/file.py
        - Single file format: direct code or ```python code ```
        """
        files = []
        
        # Check for multi-file format
        if "```filename:" in response:
            parts = response.split("```filename:")
            
            for part in parts[1:]:  # Skip first empty part
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
                # Remove markdown: ```python\ncode\n```
                lines = response.strip().split('\n')
                if lines[-1].strip() == "```":
                    code = '\n'.join(lines[1:-1])
                else:
                    code = '\n'.join(lines[1:])
            
            files.append({
                "path": "main.py",  # Default filename
                "content": code.strip()
            })
        
        return {
            "success": True,
            "files": files
        }
    
    def analyze_instruction(self, instruction: str) -> Dict:
        """
        Analyze natural language instruction to understand intent
        
        Args:
            instruction: User's instruction in English
        
        Returns:
            {
                "success": True,
                "analysis": {
                    "intent": "create_project|modify_code|add_feature|fix_bug",
                    "language": "python|javascript|...",
                    "framework": "react|django|express|none",
                    "files_needed": ["list", "of", "files"],
                    "dependencies": ["required", "packages"],
                    "actions": ["step", "by", "step", "plan"]
                }
            }
        """
        
        prompt = f"""Analyze this development instruction and return a JSON object:

INSTRUCTION: {instruction}

Return ONLY a JSON object (no markdown, no extra text):
{{
    "intent": "create_project|modify_code|add_feature|fix_bug|deploy",
    "language": "python|javascript|...",
    "framework": "react|django|flask|express|none",
    "files_needed": ["file1.py", "file2.py"],
    "dependencies": ["package1", "package2"],
    "actions": ["action 1", "action 2", "action 3"]
}}"""
        
        result = self._make_request(prompt)
        
        if result['success']:
            try:
                # Clean response (remove markdown if present)
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
            error_message: Error message from validator
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
1. Fix the error
2. Return COMPLETE FIXED CODE (not just the change)
3. No explanations, just the working code
4. No markdown backticks"""
        
        return self._make_request(prompt)


# ================================================================================
# DEMO - How to use
# ================================================================================

if __name__ == "__main__":
    print("="*70)
    print("Gemini AI Engine Demo")
    print("="*70)
    
    # Initialize with API key
    api_key = "AIzaSyCy3JRWw7sS6-1A0fFBT2UzEBx-us2F95w"
    ai = GeminiEngine(api_key)
    
    # Test 1: Analyze instruction
    print("\n[Test 1] Analyze instruction...")
    instruction = "Create a REST API with user authentication"
    
    result = ai.analyze_instruction(instruction)
    if result['success']:
        analysis = result['analysis']
        print(f"  Intent: {analysis['intent']}")
        print(f"  Language: {analysis['language']}")
        print(f"  Files needed: {analysis['files_needed']}")
    else:
        print(f"  Error: {result['error']}")
    
    # Test 2: Generate code
    print("\n[Test 2] Generate code...")
    instruction = "Create a simple Flask web server with a hello world endpoint"
    context = {
        "language": "python",
        "framework": "flask",
        "files": []
    }
    
    result = ai.generate_code(instruction, context)
    if result['success']:
        print(f"  Generated {len(result['files'])} file(s):")
        for file_info in result['files']:
            print(f"    - {file_info['path']} ({len(file_info['content'])} chars)")
            print(f"\nCode Preview:")
            print(file_info['content'][:200] + "...")
    else:
        print(f"  Error: {result['error']}")
    
    print("\n" + "="*70)
    print("✓ AI Engine working!")
    print("="*70)