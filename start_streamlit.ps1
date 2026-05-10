cd C:\Users\Administrator\.qclaw\workspace\stock-monitor
$env:STREAMLIT_SERVER_HEADLESS = "true"
python -m streamlit run app.py --server.port 8511
