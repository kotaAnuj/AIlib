# 🚀 AILib v4.0 - Complete Setup Guide

## English Programming System - Setup & Usage

---

## 📁 Project Structure

```
AILib/
├── ai_engine.py           # Upgraded AI engine with schema support
├── ailib_core.py          # Main web interface and orchestration
├── config.py              # Configuration manager
├── code_editor.py         # Smart code editing utilities
├── requirements.txt       # Python dependencies
├── ailibrarys/
│   ├── __init__.py
│   ├── file_access.py    # File system & terminal manager
│   └── terminal.py        # Terminal control
└── workspace/             # YOUR PROJECTS GO HERE
    ├── .ailib/           # Configuration (auto-created)
    └── src/              # Your schema files and generated code
```

---

## ⚙️ Installation

### Step 1: Prerequisites

- **Python 3.8+** installed
- **pip** package manager
- **Gemini API Key** (get from: https://makersuite.google.com/app/apikey)

### Step 2: Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Step 3: Verify Installation

```bash
python ailib_core.py
```

You should see the help menu.

---

## 🎯 Quick Start

### 1. Start Web Interface

```bash
python ailib_core.py web
```

### 2. Open Browser

Navigate to: **http://localhost:5000**

### 3. Configure API Key

- Go to **"Setup"** tab
- Enter your Gemini API key
- Click **"Set API Key"**

### 4. Initialize Project

- Enter project name (e.g., "my_calculator")
- Select language (Python, JavaScript, etc.)
- Select framework (optional)
- Click **"Initialize Project"**

### 5. Create Your First Schema

- Go to **"Create Schema"** tab
- Choose a template or write your own
- Example schema:

```
file: calculator.py
version: 3.13

step1: take two numbers as input
    input: a, b
    prompt user for numbers

step2: calculate sum
    result = a + b
    
step3: display result
    print the result
```

- Click **"Save Schema File"**

### 6. Generate Code

- Press **Shift + Enter** (anywhere)
- Or click **"Generate Code"** button
- AI will convert your English to working code!

### 7. View Generated Code

- Go to **"My Schemas"** tab
- Click on your schema file
- See generated code on the right side

---

## 📝 Writing Schema Files

### Basic Format

```
file: output_filename.py
version: 3.13
dependencies: math, requests

step1: describe what to do
    details here
    more details

step2: next step
    implementation details
```

### Metadata (Optional)

- `file:` - Output filename (e.g., `calculator.py`)
- `version:` - Language version (e.g., `3.13`)
- `dependencies:` - Required packages (comma-separated)

### Steps

- Use `step1:`, `step2:`, etc.
- Or use `function1:`, `task1:`, etc.
- Write in plain English
- Add implementation details with indentation

### Free-Form English

You can also just write plain English without steps:

```
Take two numbers from user.
Add them together.
Print the result.
```

---

## 💡 Example Schemas

### Example 1: Simple Calculator

```
file: calculator.py
version: 3.13

step1: take two numbers as input
    input: a, b
    validate they are numbers

step2: ask user for operation
    options: add, subtract, multiply, divide

step3: perform calculation
    if add: result = a + b
    if subtract: result = a - b
    if multiply: result = a * b
    if divide: result = a / b (check b != 0)

step4: display result
    print formatted result
```

### Example 2: File Processor

```
file: file_processor.py
version: 3.13
dependencies: pathlib

step1: get filename from user
    input: filename
    check file exists

step2: read file contents
    open in read mode

step3: count statistics
    count lines
    count words
    count characters

step4: display statistics
    print all counts
```

### Example 3: Web Scraper

```
file: scraper.py
version: 3.13
dependencies: requests, beautifulsoup4

step1: get URL from user
    validate URL format

step2: fetch webpage
    use requests.get
    handle errors

step3: parse HTML
    use BeautifulSoup
    extract links and headings

step4: save results
    write to JSON file
```

---

## ⌨️ Keyboard Shortcuts

- **Shift + Enter** - Generate code from schemas
- **Ctrl + C** - Stop web server

---

## 🔧 Advanced Configuration

### Custom Settings

Edit `workspace/.ailib/config.json`:

```json
{
  "settings": {
    "cache_enabled": true,
    "auto_install_dependencies": true,
    "default_language": "python",
    "max_cache_age_days": 7,
    "rate_limit_per_minute": 50
  }
}
```

### Multiple API Keys

You can set multiple AI provider keys:

```python
from config import AILibConfig

config = AILibConfig()
config.set_api_key("gemini", "your_gemini_key")
config.set_api_key("openai", "your_openai_key")
```

---

## 📊 Supported Languages

- ✅ Python (.py)
- ✅ JavaScript (.js)
- ✅ TypeScript (.ts)
- ✅ Java (.java)
- ✅ C++ (.cpp)
- ✅ Go (.go)
- ✅ Rust (.rs)

---

## 🐛 Troubleshooting

### Issue: "API key not set"

**Solution:** Go to Setup tab and enter your Gemini API key

### Issue: "Extension not responding" (for VS Code terminal)

**Solution:** AILib uses system terminal by default. No action needed.

### Issue: "pynput permission denied"

**Solution:** On macOS, grant accessibility permissions:
- System Preferences → Security & Privacy → Privacy → Accessibility
- Add Terminal/Python

### Issue: Code generation fails

**Solution:**
1. Check your API key is valid
2. Check internet connection
3. Verify schema format is correct
4. Check Activity Log in Status tab

### Issue: Generated code has errors

**Solution:**
1. Be more specific in your schema
2. Add more implementation details
3. Specify edge cases and error handling

---

## 📚 Best Practices

### Writing Good Schemas

1. **Be Specific** - Detail every step clearly
2. **Include Error Handling** - Mention edge cases
3. **Add Type Information** - Specify data types
4. **Use Examples** - Give sample inputs/outputs
5. **Organize Steps** - Break complex tasks into smaller steps

### Example of Good vs Bad Schema

❌ **Bad:**
```
make a calculator
```

✅ **Good:**
```
file: calculator.py

step1: get two numbers from user
    use input() function
    convert to float
    validate input is numeric

step2: get operation from user
    options: +, -, *, /
    validate choice

step3: calculate result
    handle division by zero
    round to 2 decimal places

step4: display result
    format: "X operation Y = Result"
```

---

## 🚀 Next Steps

1. **Explore Templates** - Try all built-in templates
2. **Create Complex Projects** - Build multi-file applications
3. **Experiment with Languages** - Try JavaScript, Java, etc.
4. **Share Your Schemas** - Help others learn
5. **Contribute** - Improve AILib for everyone

---

## 📞 Support

- Check Activity Log in Status tab
- Review generated code for errors
- Be specific in your English descriptions
- Add more implementation details if needed

---

## 🎉 Success Tips

1. Start with simple schemas
2. Use templates as reference
3. Add detailed steps
4. Test generated code
5. Iterate and improve

**Happy English Programming! 🚀**
