import streamlit as st
import sys
from datetime import datetime
from pathlib import Path
import io
import tempfile
import os

# 設定頁面
st.set_page_config(
    page_title="Google Drive PDF 合併工具",
    page_icon="📄",
    layout="wide"
)

# 匯入 Google Drive 相關套件
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    import pickle
    from PIL import Image
    from pypdf import PdfReader, PdfWriter
    try:
        from pypdf import PdfMerger
    except ImportError:
        from pypdf import PdfWriter as PdfMerger
except ImportError as e:
    st.error(f"❌ 缺少必要套件: {e}")
    st.info("請先執行: bash setup_web.sh")
    st.stop()

# ============ 設定區 ============
# 優先使用 Streamlit Secrets（雲端部署），其次 config.py（本地），最後預設值
try:
    # 嘗試從 Streamlit Secrets 讀取
    FOLDER_ID = st.secrets.get("FOLDER_ID", "1FSq4zxAMfpk0Zxw2fte8reRn2yvgLw6n")
    PROCESSED_FOLDER = st.secrets.get("PROCESSED_FOLDER", "已處理")
    DEFAULT_PASSWORDS = [st.secrets.get("PASSWORD1", "93509136"), st.secrets.get("PASSWORD2", "93509157")]
    SUPPORTED_IMAGES = ['.jpg', '.jpeg', '.png', '.heic', '.heif']
    SUPPORTED_PDFS = ['.pdf']
    SCOPES = ['https://www.googleapis.com/auth/drive']
except:
    # 本地執行時從 config.py 讀取
    try:
        from config import (
            FOLDER_ID,
            PROCESSED_FOLDER,
            PASSWORDS as DEFAULT_PASSWORDS,
            SUPPORTED_IMAGES,
            SUPPORTED_PDFS,
            SCOPES
        )
    except ImportError:
        # 使用預設值
        FOLDER_ID = "1FSq4zxAMfpk0Zxw2fte8reRn2yvgLw6n"
        PROCESSED_FOLDER = "已處理"
        DEFAULT_PASSWORDS = ["93509136", "93509157"]
        SUPPORTED_IMAGES = ['.jpg', '.jpeg', '.png', '.heic', '.heif']
        SUPPORTED_PDFS = ['.pdf']
        SCOPES = ['https://www.googleapis.com/auth/drive']

# ============ Google Drive 功能 ============

@st.cache_resource
def get_google_drive_service():
    """取得 Google Drive 服務連線"""
    # 檢查是否在 Streamlit Cloud（有 secrets）
    if "credentials" in st.secrets:
        # 使用 Service Account（Streamlit Cloud）
        from google.oauth2 import service_account
        
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["credentials"],
            scopes=SCOPES
        )
        return build('drive', 'v3', credentials=credentials)
    else:
        # 本地執行，使用 OAuth
        creds = None
        token_path = Path.home() / '.google_drive_token.pickle'
        
        if token_path.exists():
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                credentials_path = Path(__file__).parent / 'credentials.json'
                if not credentials_path.exists():
                    st.error("❌ 找不到 credentials.json 檔案！")
                    st.info("💡 本地執行需要 credentials.json，或在 Streamlit Cloud 設定 Secrets")
                    st.stop()
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), SCOPES)
                creds = flow.run_local_server(port=8502)
            
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return build('drive', 'v3', credentials=creds)

def get_folder_info(service, folder_id):
    """取得資料夾資訊"""
    try:
        folder = service.files().get(fileId=folder_id, fields='id, name').execute()
        return folder
    except Exception as e:
        return None

def list_files_in_folder(service, folder_id):
    """列出資料夾中的所有檔案"""
    query = f"'{folder_id}' in parents and trashed=false"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, mimeType, size, modifiedTime)',
        orderBy='name',
        supportsAllDrives=True,  # ← 支援共享雲端硬碟
        includeItemsFromAllDrives=True  # ← 包含共享雲端硬碟的項目
    ).execute()
    return results.get('files', [])

def download_file(service, file_id, destination_path):
    """從 Google Drive 下載檔案"""
    request = service.files().get_media(
        fileId=file_id,
        supportsAllDrives=True  # ← 支援共享雲端硬碟
    )
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    
    with open(destination_path, 'wb') as f:
        f.write(fh.getvalue())
    
    return destination_path

def upload_file(service, file_path, folder_id):
    """上傳檔案到 Google Drive"""
    file_metadata = {
        'name': file_path.name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(str(file_path), resumable=True)
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id',
        supportsAllDrives=True  # ← 支援共享雲端硬碟
    ).execute()
    return file

def move_file(service, file_id, new_parent_id):
    """移動檔案"""
    file = service.files().get(
        fileId=file_id, 
        fields='parents',
        supportsAllDrives=True  # ← 支援共享雲端硬碟
    ).execute()
    previous_parents = ",".join(file.get('parents'))
    
    service.files().update(
        fileId=file_id,
        addParents=new_parent_id,
        removeParents=previous_parents,
        fields='id, parents',
        supportsAllDrives=True  # ← 支援共享雲端硬碟
    ).execute()

def create_folder(service, folder_name, parent_id):
    """建立資料夾"""
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(
        body=file_metadata, 
        fields='id',
        supportsAllDrives=True  # ← 支援共享雲端硬碟
    ).execute()
    return folder

# ============ PDF 處理功能 ============

def unlock_pdf(pdf_path, passwords):
    """解鎖 PDF"""
    try:
        reader = PdfReader(pdf_path)
        if reader.is_encrypted:
            for password in passwords:
                try:
                    if reader.decrypt(password):
                        writer = PdfWriter()
                        for page in reader.pages:
                            writer.add_page(page)
                        
                        unlocked_path = pdf_path.parent / f"unlocked_{pdf_path.name}"
                        with open(unlocked_path, 'wb') as f:
                            writer.write(f)
                        return unlocked_path, password
                except:
                    continue
            return pdf_path, None
        return pdf_path, None
    except Exception as e:
        return pdf_path, None

def image_to_pdf(image_path):
    """圖片轉 PDF"""
    try:
        if image_path.suffix.lower() in ['.heic', '.heif']:
            try:
                import pyheif
                heif_file = pyheif.read(str(image_path))
                image = Image.frombytes(
                    heif_file.mode, 
                    heif_file.size, 
                    heif_file.data,
                    "raw",
                    heif_file.mode,
                    heif_file.stride,
                )
            except ImportError:
                return None
        else:
            image = Image.open(image_path)
        
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        pdf_path = image_path.parent / f"{image_path.stem}.pdf"
        image.save(pdf_path, 'PDF', resolution=100.0)
        return pdf_path
    except Exception as e:
        return None

def merge_pdfs(pdf_files, output_path):
    """合併 PDF"""
    try:
        if 'PdfMerger' in dir() and PdfMerger != PdfWriter:
            merger = PdfMerger()
            for pdf_file in pdf_files:
                merger.append(str(pdf_file))
            merger.write(str(output_path))
            merger.close()
        else:
            writer = PdfWriter()
            for pdf_file in pdf_files:
                reader = PdfReader(str(pdf_file))
                for page in reader.pages:
                    writer.add_page(page)
            with open(output_path, 'wb') as f:
                writer.write(f)
        return True
    except Exception as e:
        st.error(f"合併失敗: {e}")
        return False

# ============ 主介面 ============

def main():
    st.title("📄 Google Drive PDF 合併工具")
    st.markdown("---")
    
    # 側邊欄設定
    with st.sidebar:
        st.header("⚙️ 設定")
        
        # 密碼設定
        st.subheader("🔐 PDF 密碼")
        password1 = st.text_input("密碼 1", value=DEFAULT_PASSWORDS[0] if len(DEFAULT_PASSWORDS) > 0 else "", type="password")
        password2 = st.text_input("密碼 2", value=DEFAULT_PASSWORDS[1] if len(DEFAULT_PASSWORDS) > 1 else "", type="password")
        passwords = [p for p in [password1, password2] if p]
        
        # 檔名設定
        st.subheader("📝 輸出檔名")
        use_date = st.checkbox("加上日期時間", value=True)
        custom_name = st.text_input("自訂前綴", value="合併檔案")
        
        st.markdown("---")
        st.info("💡 **使用流程**\n\n1️⃣ iOS 捷徑上傳檔案\n2️⃣ 選擇要合併的檔案\n3️⃣ 點擊開始合併")
    
    # 連接 Google Drive
    try:
        service = get_google_drive_service()
        
        # 取得資料夾資訊
        folder = get_folder_info(service, FOLDER_ID)
        if not folder:
            st.error("❌ 無法存取共用資料夾，請檢查權限")
            return
        
        st.success(f"✅ 已連接到資料夾: **{folder['name']}**")
        
        # 上傳提示
        with st.expander("📤 如何上傳檔案到 Google Drive？"):
            st.markdown("""
            ### 📱 推薦方式：使用 iOS 捷徑
            
            **您已設定的「上傳發票」捷徑可以：**
            - 📸 一鍵拍照並自動上傳
            - 📷 選擇相簿照片上傳  
            - 🚀 直接上傳到 Google Drive
            - 🗑️ 上傳後自動刪除本地照片
            
            **使用步驟：**
            1. 點選手機主畫面的「上傳發票」圖示
            2. 選擇照片或直接拍照
            3. 自動上傳完成！
            
            ---
            
            ### 🌐 其他上傳方式
            
            **📱 Google Drive App：**
            1. 打開 Google Drive app
            2. 進入「待列印發票」資料夾
            3. 點選右下角「+」按鈕
            4. 選擇「上傳」
            
            **💻 電腦：**
            1. 前往 https://drive.google.com/
            2. 進入「待列印發票」資料夾
            3. 拖曳檔案到網頁即可上傳
            """)
        
        st.markdown("---")
        st.subheader(f"📁 檔案清單")
        
        # 列出所有檔案
        with st.spinner("📥 載入檔案清單..."):
            files = list_files_in_folder(service, FOLDER_ID)
        
        # 過濾支援的檔案
        supported_files = []
        for f in files:
            ext = Path(f['name']).suffix.lower()
            if ext in SUPPORTED_PDFS + SUPPORTED_IMAGES:
                supported_files.append(f)
        
        if not supported_files:
            st.warning("⚠️ 資料夾中沒有 PDF 或圖片檔案")
            st.info("💡 請使用 iOS 捷徑或 Google Drive 上傳檔案")
            return
        
        st.write(f"找到 **{len(supported_files)}** 個檔案")
        
        col1, col2 = st.columns([1, 4])
        with col1:
            select_all = st.checkbox("全選", value=True)
        
        st.markdown("---")
        
        # 顯示檔案並允許選擇
        selected_files = []
        
        for idx, file in enumerate(supported_files):
            col1, col2, col3, col4 = st.columns([1, 4, 2, 2])
            
            with col1:
                if select_all:
                    selected = st.checkbox(f"{idx+1}", value=True, key=f"select_{idx}", label_visibility="collapsed")
                else:
                    selected = st.checkbox(f"{idx+1}", value=False, key=f"select_{idx}", label_visibility="collapsed")
            
            with col2:
                file_type = "📄 PDF" if Path(file['name']).suffix.lower() in SUPPORTED_PDFS else "📷 圖片"
                st.text(f"{file_type} {file['name']}")
            
            with col3:
                size_mb = int(file.get('size', 0)) / 1024 / 1024
                st.text(f"{size_mb:.2f} MB" if size_mb > 0 else "-")
            
            with col4:
                if file.get('modifiedTime'):
                    modified = file['modifiedTime'][:10]
                    st.text(modified)
            
            if selected:
                selected_files.append(file)
        
        st.markdown("---")
        
        # 合併按鈕
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            merge_button = st.button("🚀 開始合併", type="primary", use_container_width=True)
        
        if merge_button:
            if not selected_files:
                st.error("❌ 請至少選擇一個檔案")
                return
            
            # 建立暫存目錄
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # 進度條
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # 下載檔案
                status_text.text("📥 下載檔案...")
                downloaded_files = []
                for idx, file in enumerate(selected_files):
                    progress = (idx + 1) / len(selected_files) * 0.3
                    progress_bar.progress(progress)
                    
                    file_path = temp_path / file['name']
                    download_file(service, file['id'], file_path)
                    downloaded_files.append((file['id'], file_path))
                
                # 處理檔案
                status_text.text("🔧 處理檔案...")
                pdf_files = []
                locked_files = []
                unlocked_files = []
                
                for idx, (file_id, file_path) in enumerate(downloaded_files):
                    progress = 0.3 + (idx + 1) / len(downloaded_files) * 0.3
                    progress_bar.progress(progress)
                    
                    ext = file_path.suffix.lower()
                    
                    if ext in SUPPORTED_IMAGES:
                        pdf_path = image_to_pdf(file_path)
                        if pdf_path:
                            pdf_files.append(pdf_path)
                    elif ext in SUPPORTED_PDFS:
                        unlocked_pdf, used_password = unlock_pdf(file_path, passwords)
                        pdf_files.append(unlocked_pdf)
                        if used_password:
                            unlocked_files.append((file_path.name, used_password))
                        elif unlocked_pdf == file_path:
                            try:
                                reader = PdfReader(file_path)
                                if reader.is_encrypted:
                                    locked_files.append(file_path.name)
                            except:
                                pass
                
                # 合併 PDF
                status_text.text("📑 合併 PDF...")
                progress_bar.progress(0.7)
                
                today = datetime.now().strftime("%Y%m%d-%H%M")
                if use_date:
                    output_filename = f"{custom_name}-{today}.pdf"
                else:
                    output_filename = f"{custom_name}.pdf"
                
                output_path = temp_path / output_filename
                
                if merge_pdfs(pdf_files, output_path):
                    # 上傳回 Google Drive
                    status_text.text("⬆️ 上傳到 Google Drive...")
                    progress_bar.progress(0.9)
                    
                    upload_file(service, output_path, FOLDER_ID)
                    
                    # 移動原始檔案
                    status_text.text("🗂️ 整理檔案...")
                    
                    # 檢查「已處理」資料夾
                    processed_query = f"name='{PROCESSED_FOLDER}' and '{FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                    processed_results = service.files().list(
                        q=processed_query, 
                        fields='files(id)',
                        supportsAllDrives=True,  # ← 支援共享雲端硬碟
                        includeItemsFromAllDrives=True  # ← 包含共享雲端硬碟的項目
                    ).execute()
                    processed_folders = processed_results.get('files', [])
                    
                    if processed_folders:
                        processed_folder_id = processed_folders[0]['id']
                    else:
                        processed_folder = create_folder(service, PROCESSED_FOLDER, FOLDER_ID)
                        processed_folder_id = processed_folder['id']
                    
                    # 移動檔案
                    for file_id, _ in downloaded_files:
                        move_file(service, file_id, processed_folder_id)
                    
                    progress_bar.progress(1.0)
                    status_text.empty()
                    
                    # 顯示結果
                    st.success("🎉 合併完成！")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("合併檔案", output_filename)
                        st.metric("處理檔案數", len(selected_files))
                    
                    with col2:
                        if unlocked_files:
                            st.info(f"🔓 已解鎖 {len(unlocked_files)} 個 PDF")
                            with st.expander("查看詳情"):
                                for fname, pwd in unlocked_files:
                                    st.text(f"✓ {fname} (密碼: {pwd})")
                        
                        if locked_files:
                            st.warning(f"⚠️ {len(locked_files)} 個 PDF 無法解鎖")
                            with st.expander("查看詳情"):
                                for fname in locked_files:
                                    st.text(f"✗ {fname}")
                    
                    st.balloons()
                else:
                    st.error("❌ 合併失敗")
        
    except Exception as e:
        st.error(f"❌ 發生錯誤: {e}")
        import traceback
        with st.expander("查看詳細錯誤"):
            st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
