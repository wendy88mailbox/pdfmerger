#!/bin/bash
# 啟動網頁版

# 取得腳本所在目錄
cd "$(dirname "$0")"

echo "============================================"
echo "🌐 啟動 Google Drive PDF 合併工具"
echo "============================================"
echo ""
echo "📱 網頁介面即將開啟..."
echo "💡 按 Ctrl+C 停止伺服器"
echo ""
echo "============================================"
echo ""

# 啟動 Streamlit（使用 python3 -m 確保找到正確的模組）
python3 -m streamlit run streamlit_app.py --server.port 8501 --server.headless false
