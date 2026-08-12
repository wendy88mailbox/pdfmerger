#!/bin/bash
# 安裝腳本 - Google Drive PDF 合併工具

echo "============================================"
echo "🚀 Google Drive PDF 合併工具 - 安裝程式"
echo "============================================"
echo ""

# 檢查 Python
echo "📝 檢查 Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 找不到 Python 3"
    echo "請先安裝 Python 3: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✅ 找到: $PYTHON_VERSION"
echo ""

# 檢查 pip
echo "📝 檢查 pip..."
if ! command -v pip3 &> /dev/null; then
    echo "❌ 找不到 pip3"
    echo "請先安裝 pip"
    exit 1
fi
echo "✅ pip3 已安裝"
echo ""

# 安裝套件
echo "📦 安裝必要套件..."
echo "   這可能需要幾分鐘，請稍候..."
echo ""

pip3 install --upgrade \
    google-auth \
    google-auth-oauthlib \
    google-auth-httplib2 \
    google-api-python-client \
    Pillow \
    pypdf \
    || { echo "❌ 安裝失敗"; exit 1; }

echo ""
echo "✅ 所有套件安裝完成！"
echo ""

# 檢查是否已有 credentials.json
if [ -f "credentials.json" ]; then
    echo "✅ 找到 credentials.json"
else
    echo "⚠️  尚未設定 Google API credentials.json"
    echo ""
    echo "📋 接下來請："
    echo "1. 前往 Google Cloud Console"
    echo "2. 下載 credentials.json"
    echo "3. 將檔案放在此資料夾中"
    echo ""
    echo "詳細步驟請參考 README.txt"
fi

echo ""
echo "============================================"
echo "🎉 安裝完成！"
echo "============================================"
echo ""
echo "接下來："
echo "1. 設定 Google API (參考 README.txt)"
echo "2. 執行: ./合併PDF.command"
echo ""
