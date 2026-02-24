@echo off
echo Setting up Incognish...

python -m venv venv
call venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium

echo.
echo Setup complete!
echo Run the app with: venv\Scripts\activate ^&^& python run.py
pause
