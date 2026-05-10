@echo off
cd /d "C:\Users\Administrator\.qclaw\workspace\stock-monitor"
start /b python -m streamlit run app.py --server.port 8510 > nul 2>&1
echo Streamlit started on port 8510
timeout /t 3 > nul
curl -s http://localhost:8510 | findstr "title"
