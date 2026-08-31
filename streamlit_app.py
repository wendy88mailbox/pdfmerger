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

# ============ 定義常數 ============
SUPPORTED_IMAGES = ['.jpg', '.jpeg', '.png', '.heic', '.heif']
SUPPORTED_PDFS = ['.pdf']
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# ============ 初始化 ============
@st.cache_resource
def init_system():
    """系統初始化"""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    
    folder_id = st.secrets.get("FOLDER_ID", "1FSq4zxAMfpk0Zxw2fte8reRn2yvgLw6n")
    passwords = [
        st.secrets.get("PASSWORD1", "93509136"), 
        st.secrets.get("PASSWORD2", "93509157")
    ]
    
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["credentials"],
        scopes=SCOPES
    )
    service = build('drive', 'v3', credentials=credentials)
    
    return service, folder_id, passwords

# ============ Google Drive 功能 ============
def list_files_in_folder(service, folder_id):
    """列出資料夾中的所有檔案"""
    query = f"'{folder_id}' in parents and trashed=false"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, mimeType, size, modifiedTime)',
        orderBy='name',
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    return results.get('files', [])

def download_file(service, file_id, destination_path):
    """從 Google Drive 下載檔案"""
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    
    with open(destination_path, 'wb') as f:
        f.write(fh.getvalue())
    return destination_path

# ============ PDF 處理功能 ============
def unlock_pdf(pdf_path, passwords):
    """解鎖 PDF"""
    from pypdf import PdfReader, PdfWriter
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
    except:
        return pdf_path, None

def image_to_pdf(image_path):
    """圖片轉 PDF"""
    from PIL import Image
    try:
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
    except:
        return None

def merge_pdfs(pdf_files, output_path):
    """合併 PDF"""
    from pypdf import PdfReader, PdfWriter
    try:
        writer = PdfWriter()
        for pdf_file in pdf_files:
            reader = PdfReader(str(pdf_file))
            for page in reader.pages:
                writer.add_page(page)
        with open(output_path, 'wb') as f:
            writer.write(f)
        return True
    except Exception as e:
        st.error(f"❌ 合併失敗: {e}")
        return False

# ============ 主介面 ============
def main():
    st.title("📄 Google Drive PDF 合併工具")
    st.markdown("---")
    
    # 初始化系統
    try:
        with st.spinner("🔧 正在連接 Google Drive..."):
            service, FOLDER_ID, DEFAULT_PASSWORDS = init_system()
        st.success("✅ 已連接到 Google Drive")
    except Exception as e:
        st.error(f"❌ 初始化失敗: {e}")
        st.stop()
    
    # 側邊欄設定
    with st.sidebar:
        st.header("⚙️ 設定")
        st.subheader("🔐 PDF 密碼")
        password1 = st.text_input("密碼 1", value=DEFAULT_PASSWORDS[0], type="password", key="pwd1")
        password2 = st.text_input("密碼 2", value=DEFAULT_PASSWORDS[1], type="password", key="pwd2")
        passwords = [p for p in [password1, password2] if p]
        
        st.subheader("📝 輸出檔名")
        use_date = st.checkbox("加上日期時間", value=True, key="use_date")
        custom_name = st.text_input("自訂前綴", value="合併檔案", key="custom_name")
        
        st.markdown("---")
        st.info("💡 **使用流程**\n\n1️⃣ 上傳檔案到 Google Drive\n2️⃣ 選擇要合併的檔案\n3️⃣ 點擊開始合併\n4️⃣ 下載合併後的 PDF")
    
    st.subheader("📁 檔案清單")
    
    # 列出檔案
    with st.spinner("📥 載入檔案清單..."):
        try:
            files = list_files_in_folder(service, FOLDER_ID)
            supported_files = [f for f in files if Path(f['name']).suffix.lower() in SUPPORTED_PDFS + SUPPORTED_IMAGES]
        except Exception as e:
            st.error(f"❌ 載入檔案失敗: {e}")
            st.stop()
    
    if not supported_files:
        st.warning("⚠️ 資料夾中沒有 PDF 或圖片檔案")
        return
    
    st.write(f"找到 **{len(supported_files)}** 個檔案")
    select_all = st.checkbox("全選", value=True, key="select_all")
    st.markdown("---")
    
    # 顯示檔案列表
    selected_files = []
    for idx, file in enumerate(supported_files):
        col1, col2, col3, col4 = st.columns([1, 4, 2, 2])
        with col1:
            selected = st.checkbox(f"{idx+1}", value=select_all, key=f"file_{idx}", label_visibility="collapsed")
        with col2:
            file_type = "📄 PDF" if Path(file['name']).suffix.lower() in SUPPORTED_PDFS else "📷 圖片"
            st.text(f"{file_type} {file['name']}")
        with col3:
            size_mb = int(file.get('size', 0)) / 1024 / 1024
            st.text(f"{size_mb:.2f} MB" if size_mb > 0 else "-")
        with col4:
            if file.get('modifiedTime'):
                st.text(file['modifiedTime'][:10])
        
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
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 下載檔案
            status_text.text("📥 下載檔案...")
            downloaded_files = []
            for idx, file in enumerate(selected_files):
                progress_bar.progress((idx + 1) / len(selected_files) * 0.3)
                file_path = temp_path / file['name']
                download_file(service, file['id'], file_path)
                downloaded_files.append(file_path)
            
            # 處理檔案
            status_text.text("🔧 處理檔案...")
            pdf_files = []
            unlocked_files = []
            locked_files = []
            
            for idx, file_path in enumerate(downloaded_files):
                progress_bar.progress(0.3 + (idx + 1) / len(downloaded_files) * 0.4)
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
            
            # 合併 PDF
            status_text.text("📑 合併 PDF...")
            progress_bar.progress(0.8)
            
            today = datetime.now().strftime("%Y%m%d-%H%M")
            output_filename = f"{custom_name}-{today}.pdf" if use_date else f"{custom_name}.pdf"
            output_path = temp_path / output_filename
            
            if merge_pdfs(pdf_files, output_path):
                progress_bar.progress(1.0)
                status_text.empty()
                st.success("🎉 合併完成！")
                
                # 下載按鈕
                with open(output_path, 'rb') as f:
                    pdf_data = f.read()
                
                st.download_button(
                    label="📥 下載合併後的 PDF",
                    data=pdf_data,
                    file_name=output_filename,
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
                
                st.info("💡 下載後，原始檔案仍保留在 Google Drive 中")
                
                # 統計資訊
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("📄 合併檔案", output_filename)
                    st.metric("📊 處理檔案數", len(selected_files))
                with col2:
                    if unlocked_files:
                        st.info(f"🔓 已解鎖 {len(unlocked_files)} 個 PDF")
                
                st.balloons()

if __name__ == "__main__":
    main()
