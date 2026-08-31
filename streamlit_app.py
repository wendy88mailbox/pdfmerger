import streamlit as st
from datetime import datetime
from pathlib import Path
import io
import tempfile

# 設定頁面
st.set_page_config(
    page_title="Google Drive PDF 合併工具",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Google Drive PDF 合併工具")
st.markdown("---")

# 顯示載入狀態
with st.spinner("🔧 正在初始化..."):
    # 匯入必要套件
    try:
        st.text("📦 載入套件...")
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
        from PIL import Image
        from pypdf import PdfReader, PdfWriter
        st.text("✅ 套件載入完成")
    except ImportError as e:
        st.error(f"❌ 缺少必要套件: {e}")
        st.stop()

    # 讀取設定
    try:
        st.text("🔑 讀取設定...")
        FOLDER_ID = st.secrets.get("FOLDER_ID", "1FSq4zxAMfpk0Zxw2fte8reRn2yvgLw6n")
        DEFAULT_PASSWORDS = [
            st.secrets.get("PASSWORD1", "93509136"), 
            st.secrets.get("PASSWORD2", "93509157")
        ]
        st.text("✅ 設定讀取完成")
    except Exception as e:
        st.error(f"❌ 讀取設定失敗: {e}")
        st.stop()

    # 連接 Google Drive
    try:
        st.text("🔗 連接 Google Drive...")
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["credentials"],
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        service = build('drive', 'v3', credentials=credentials)
        st.text("✅ Google Drive 連接成功")
    except Exception as e:
        st.error(f"❌ Google Drive 連接失敗: {e}")
        import traceback
        with st.expander("查看詳細錯誤"):
            st.code(traceback.format_exc())
        st.stop()

st.success("✅ 系統初始化完成！")

st.info("🎉 如果您看到這個訊息，表示程式可以正常運作！")
st.markdown("請告訴開發者：**系統初始化成功，可以繼續開發完整功能**")

# 簡易功能測試
if st.button("🧪 測試列出檔案"):
    try:
        with st.spinner("📥 讀取檔案清單..."):
            query = f"'{FOLDER_ID}' in parents and trashed=false"
            results = service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=10,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = results.get('files', [])
            st.success(f"✅ 找到 {len(files)} 個檔案")
            
            for f in files:
                st.text(f"📄 {f['name']}")
    except Exception as e:
        st.error(f"❌ 列出檔案失敗: {e}")
        import traceback
        with st.expander("查看詳細錯誤"):
            st.code(traceback.format_exc()) 
 
