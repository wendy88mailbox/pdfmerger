# Google Drive PDF 合併工具

自動從 Google Drive 下載、解鎖、合併 PDF 和圖片的工具。

## 功能特色

✨ **自動化處理**
- 從 Google Drive 自動下載檔案
- 支援密碼保護的 PDF（自動解鎖）
- 圖片自動轉換為 PDF（JPG, PNG, HEIC）
- 自動合併所有檔案
- 上傳回 Google Drive
- 原始檔案自動整理到「已處理」資料夾

📱 **雙版本**
- 命令列版本：快速批次處理
- 網頁版：美觀的圖形界面，支援選擇性合併

🔐 **安全**
- 本地執行，不上傳資料到第三方
- 支援 Google OAuth 2.0 認證
- 密碼僅儲存在本地

## 系統需求

- macOS 10.13 或更新
- Python 3.7+
- Google 帳號

## 快速開始

### 1. 安裝套件

命令列版本：
```bash
bash setup.sh
```

網頁版：
```bash
bash setup_web.sh
```

### 2. 設定 Google API

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立新專案
3. 啟用 Google Drive API
4. 建立 OAuth 2.0 憑證（選擇「電腦版應用程式」）
5. 下載 JSON 檔案，重新命名為 `credentials.json`
6. 放到專案資料夾中

詳細步驟請參考 `README.txt`

### 3. 設定配置

```bash
cp config.example.py config.py
```

編輯 `config.py`，填入您的設定：
- Google Drive 資料夾 ID
- PDF 密碼（如果有）

### 4. 執行

命令列版本：
```bash
./合併PDF.command
```

網頁版：
```bash
./啟動網頁版.command
```

## 使用方式

### 命令列版本

1. 將檔案放到指定的 Google Drive 資料夾
2. 雙擊「合併PDF.command」或執行：
   ```bash
   python3 merge_google_drive_pdf.py
   ```
3. 等待處理完成
4. 檢查 Google Drive 中的合併檔案

### 網頁版

1. 啟動網頁版：
   ```bash
   ./啟動網頁版.command
   ```
2. 瀏覽器會自動開啟 `http://localhost:8501`
3. 勾選要合併的檔案
4. 點擊「開始合併」
5. 等待完成

**區域網路存取：**
其他裝置可以透過 Network URL 存取（顯示在終端機）

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `merge_google_drive_pdf.py` | 命令列版本主程式 |
| `streamlit_app.py` | 網頁版主程式 |
| `config.py` | 配置檔（敏感資訊，不上傳） |
| `config.example.py` | 配置範例 |
| `credentials.json` | Google API 憑證（不上傳） |
| `setup.sh` | 命令列版本安裝腳本 |
| `setup_web.sh` | 網頁版安裝腳本 |
| `合併PDF.command` | 命令列版本啟動檔 |
| `啟動網頁版.command` | 網頁版啟動檔 |

## 配置說明

編輯 `config.py`：

```python
# Google Drive 資料夾 ID
# 從資料夾連結取得：https://drive.google.com/drive/folders/[FOLDER_ID]
FOLDER_ID = "YOUR_FOLDER_ID_HERE"

# 處理完畢後移動到的資料夾名稱
PROCESSED_FOLDER = "已處理"

# PDF 密碼（可以設定多組）
PASSWORDS = ["password1", "password2"]
```

## 常見問題

### Q: 如何取得 Google Drive 資料夾 ID？

A: 在 Google Drive 中打開資料夾，網址列中 `folders/` 後面的字串就是 ID。

### Q: 可以處理有密碼的 PDF 嗎？

A: 可以！在 `config.py` 中設定密碼即可。

### Q: 支援哪些圖片格式？

A: JPG, PNG, HEIC, HEIF

### Q: 網頁版可以在手機上用嗎？

A: 可以！只要在同一個 Wi-Fi 網路，手機瀏覽器輸入 Network URL 即可。

### Q: 處理後的檔案會被刪除嗎？

A: 不會！原始檔案會移到「已處理」資料夾保存。

## 安全性

⚠️ **重要提醒**

- `credentials.json` 包含您的 Google API 憑證，**絕對不要公開**
- `config.py` 包含您的密碼和資料夾 ID，**不要上傳到 GitHub**
- `.gitignore` 已設定好，會自動排除敏感檔案

如果不小心上傳了：
1. 立即到 GitHub 刪除 repository
2. 到 Google Cloud Console 刪除並重新建立憑證
3. 修改所有密碼

## 進階使用

### 修改檔名格式

編輯主程式中的日期格式：
```python
today = datetime.now().strftime("%Y%m%d-%H%M")
```

### 自訂輸出資料夾

修改 `config.py` 中的 `PROCESSED_FOLDER`

### 新增支援的檔案格式

編輯 `config.py`：
```python
SUPPORTED_IMAGES = ['.jpg', '.jpeg', '.png', '.heic', '.heif', '.webp']
```

## 授權

MIT License

## 貢獻

歡迎提交 Issue 或 Pull Request！

## 作者

Built with ❤️ for PDF merging automation

---

📚 **更多文件**
- 詳細安裝說明：`README.txt`
- 網頁版使用：`網頁版使用說明.txt`
- 同事使用指南：`同事使用指南.txt`
- 管理者指南：`管理者指南.txt`
