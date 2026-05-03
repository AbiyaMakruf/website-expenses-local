@echo off
chcp 65001 >nul
title Aplikasi Catatan Keuangan
cd /d "%~dp0"

echo Memeriksa dependensi...
pip install -r requirements.txt --quiet

echo.
echo Menjalankan aplikasi...
start "" "http://localhost:8501"
timeout /t 2 /nobreak >nul
streamlit run app.py --server.headless true --server.port 8501
pause
