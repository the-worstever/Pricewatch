# .gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/
env/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# OS
.DS_Store
Thumbs.db

# Output files
*.csv
*.xlsx
*.html
pricewatch_output.*

# Logs
*.log

# Environment variables
.env
.env.local

---

# setup.sh - Quick setup script for Unix/Mac
#!/bin/bash

echo "🔧 Setting up PriceWatch..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then 
    echo "❌ Python 3.10+ required (found $PYTHON_VERSION)"
    exit 1
fi

echo "✓ Python version: $PYTHON_VERSION"

# Check if uv is available
if command -v uv &> /dev/null; then
    echo "✓ Using uv for package management"
    
    # Create virtual environment with uv
    uv venv
    source .venv/bin/activate
    
    # Install base dependencies
    echo "📦 Installing dependencies..."
    uv pip install -e .
    
    # Ask about optional dependencies
    read -p "Install Streamlit web app? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        uv pip install -e ".[streamlit]"
    fi
    
    read -p "Install Excel export support? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        uv pip install -e ".[export]"
    fi
    
    read -p "Install LLM extraction support? (requires Ollama) (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        uv pip install -e ".[llm]"
    fi
    
else
    echo "⚠ uv not found, using pip"
    
    # Create virtual environment with venv
    python3 -m venv .venv
    source .venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install
    echo "📦 Installing dependencies..."
    pip install -e .
    
    # Optional dependencies
    read -p "Install all optional dependencies? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip install -e ".[streamlit,export,llm,dev]"
    fi
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To activate the environment:"
echo "  source .venv/bin/activate"
echo ""
echo "Quick start:"
echo "  pricewatch analyze https://competitor.com/pricing"
echo "  streamlit run streamlit_app/app.py"
echo ""

---

# setup.bat - Quick setup script for Windows
@echo off
echo Setting up PriceWatch...

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python 3 is required but not installed
    exit /b 1
)

echo Creating virtual environment...
python -m venv .venv

echo Activating environment...
call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install --upgrade pip
pip install -e .

echo.
echo Setup complete!
echo.
echo To activate the environment:
echo   .venv\Scripts\activate.bat
echo.
echo Quick start:
echo   pricewatch analyze https://competitor.com/pricing
echo   streamlit run streamlit_app/app.py
echo.

pause
