@echo off
chcp 65001 > nul
cd /d "%~dp0"

if not exist .env (
  echo [setup] Creating .env with a new SECRET_KEY...
  python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32)); print('GTM_CONTAINER_ID='); print('FLASK_DEBUG=1')" > .env
)

echo [setup] Installing packages...
python -m pip install -r requirements.txt --quiet

echo [setup] Preparing database...
python init_db.py

echo [run] Open http://localhost:5000 in your browser. Press Ctrl+C to stop.
python app.py
pause
