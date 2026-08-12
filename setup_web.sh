#!/bin/bash
# 網頁版安裝腳本

echo "============================================"
echo "🌐 Google Drive PDF 合併工具 - 網頁版安裝"
echo "============================================"
echo ""

# 檢查 Python
echo "📝 檢查 Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 找不到 Python 3"
    exit 1
fi
echo "✅ $(python3 --version)"
echo ""

# 安裝 Streamlit 和其他套件
echo "📦 安裝網頁版套件..."
echo "   這可能需要幾分鐘..."
echo ""

pip3 install --upgrade \
    streamlit \
    google-auth \
    google-auth-oauthlib \
    google-auth-httplib2 \
    google-api-python-client \
    Pillow \
    pypdf \
    || { echo "❌ 安裝失敗"; exit 1; }

echo ""
echo "✅ 安裝完成！"
echo ""
echo "============================================"
echo "🎉 準備就緒！"
echo "============================================"
echo ""
echo "啟動網頁版："
echo "  ./啟動網頁版.command"
echo ""
echo "或在終端機執行："
echo "  streamlit run streamlit_app.py"
echo ""
