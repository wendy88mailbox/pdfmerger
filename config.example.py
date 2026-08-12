# ============ 範例配置文件 ============
# 複製這個檔案為 config.py，並填入您自己的設定

# Google Drive 設定
FOLDER_ID = "YOUR_FOLDER_ID_HERE"  # 替換成您的 Google Drive 資料夾 ID
PROCESSED_FOLDER = "已處理"          # 處理完的檔案移到這個資料夾

# PDF 密碼（如果您的 PDF 有密碼保護）
PASSWORDS = ["password1", "password2"]  # 替換成您的 PDF 密碼

# 支援的檔案格式（通常不需要修改）
SUPPORTED_IMAGES = ['.jpg', '.jpeg', '.png', '.heic', '.heif']
SUPPORTED_PDFS = ['.pdf']

# Google Drive API 設定（不需要修改）
SCOPES = ['https://www.googleapis.com/auth/drive']
