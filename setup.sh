#!/bin/bash
echo "Setting up Incognish..."

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
playwright install chromium

echo ""
echo "Setup complete!"
echo "Run the app with: source venv/bin/activate && python run.py"
