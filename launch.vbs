Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd /d C:\Users\Administrator\.qclaw\workspace\stock-monitor && python -m streamlit run app.py --server.port 8512 --server.headless true", 0, False
Set WshShell = Nothing
