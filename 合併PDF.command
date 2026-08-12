#!/bin/bash
# 合併PDF - 雙擊執行檔

# 取得腳本所在目錄
cd "$(dirname "$0")"

# 執行 Python 腳本
python3 merge_google_drive_pdf.py

# 完成後等待使用者按鍵
echo ""
read -p "按 Enter 鍵關閉視窗..."
