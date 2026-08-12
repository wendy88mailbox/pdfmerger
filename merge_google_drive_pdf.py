#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Drive PDF 自動合併工具
自動從 Google Drive 下載、解鎖、合併 PDF 和圖片
"""

import os
import sys
from datetime import datetime
from pathlib import Path
import io

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
    print(f"❌ 缺少必要套件: {e}")
    print("\n請先執行安裝腳本：")
    print("  bash setup.sh\n")
    sys.exit(1)

# ============ 設定區 ============
# 優先使用 config.py（如果存在），否則使用預設值
try:
    from config import (
        FOLDER_ID, 
        PROCESSED_FOLDER, 
        PASSWORDS, 
        SUPPORTED_IMAGES, 
        SUPPORTED_PDFS, 
        SCOPES
    )
    print("✅ 已載入 config.py 設定")
except ImportError:
    # 使用預設值（向後相容）
    FOLDER_ID = "1FSq4zxAMfpk0Zxw2fte8reRn2yvgLw6n"
    FOLDER_NAME = None
    PROCESSED_FOLDER = "已處理"
    PASSWORDS = ["93509136", "93509157"]
    SUPPORTED_IMAGES = ['.jpg', '.jpeg', '.png', '.heic', '.heif']
    SUPPORTED_PDFS = ['.pdf']
    SCOPES = ['https://www.googleapis.com/auth/drive']
    print("⚠️  未找到 config.py，使用預設設定")

# 舊版相容性（如果直接定義在這裡）
FOLDER_NAME = None  # 不使用名稱搜尋，直接用 ID

# Google Drive API 設定
if 'SCOPES' not in locals():
    SCOPES = ['https://www.googleapis.com/auth/drive']

# ============ Google Drive 功能 ============

def get_google_drive_service():
    """取得 Google Drive 服務連線"""
    creds = None
    token_path = Path.home() / '.google_drive_token.pickle'
    
    # 載入已儲存的認證
    if token_path.exists():
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    # 如果沒有有效認證，重新登入
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            credentials_path = Path(__file__).parent / 'credentials.json'
            if not credentials_path.exists():
                print("❌ 找不到 credentials.json 檔案！")
                print("\n請按照 README.txt 的說明設定 Google API")
                sys.exit(1)
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # 儲存認證供下次使用
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('drive', 'v3', credentials=creds)

def find_folder(service, folder_name, parent_id=None):
    """在 Google Drive 中尋找資料夾"""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)'
    ).execute()
    
    items = results.get('files', [])
    return items[0] if items else None

def create_folder(service, folder_name, parent_id=None):
    """在 Google Drive 建立資料夾"""
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]
    
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder

def list_files_in_folder(service, folder_id):
    """列出資料夾中的所有檔案"""
    query = f"'{folder_id}' in parents and trashed=false"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, mimeType)',
        orderBy='name'
    ).execute()
    return results.get('files', [])

def download_file(service, file_id, file_name, destination):
    """從 Google Drive 下載檔案"""
    request = service.files().get_media(fileId=file_id)
    file_path = destination / file_name
    
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    
    with open(file_path, 'wb') as f:
        f.write(fh.getvalue())
    
    return file_path

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
        fields='id'
    ).execute()
    return file

def move_file(service, file_id, new_parent_id):
    """移動檔案到另一個資料夾"""
    file = service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents'))
    
    service.files().update(
        fileId=file_id,
        addParents=new_parent_id,
        removeParents=previous_parents,
        fields='id, parents'
    ).execute()

# ============ PDF 處理功能 ============

def unlock_pdf(pdf_path, passwords):
    """嘗試用提供的密碼解鎖 PDF"""
    try:
        reader = PdfReader(pdf_path)
        if reader.is_encrypted:
            for password in passwords:
                try:
                    if reader.decrypt(password):
                        print(f"  ✅ 已解鎖: {pdf_path.name} (密碼: {password})")
                        writer = PdfWriter()
                        for page in reader.pages:
                            writer.add_page(page)
                        
                        unlocked_path = pdf_path.parent / f"unlocked_{pdf_path.name}"
                        with open(unlocked_path, 'wb') as f:
                            writer.write(f)
                        return unlocked_path
                except:
                    continue
            print(f"  ⚠️  無法解鎖: {pdf_path.name} (密碼不符)")
            return pdf_path
        return pdf_path
    except Exception as e:
        print(f"  ⚠️  處理 PDF 時發生錯誤: {pdf_path.name} - {e}")
        return pdf_path

def image_to_pdf(image_path):
    """將圖片轉換為 PDF"""
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
                print(f"  ⚠️  無法處理 HEIC 格式: {image_path.name}")
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
        print(f"  ✅ 已轉換: {image_path.name} → PDF")
        return pdf_path
    except Exception as e:
        print(f"  ⚠️  轉換圖片失敗: {image_path.name} - {e}")
        return None

def merge_pdfs(pdf_files, output_path):
    """合併多個 PDF 檔案"""
    try:
        # 檢查是否有真正的 PdfMerger
        if 'PdfMerger' in dir() and PdfMerger != PdfWriter:
            # 新版 pypdf (有 PdfMerger)
            merger = PdfMerger()
            for pdf_file in pdf_files:
                try:
                    merger.append(str(pdf_file))
                    print(f"  ✅ 已加入: {pdf_file.name}")
                except Exception as e:
                    print(f"  ⚠️  無法加入: {pdf_file.name} - {e}")
            
            merger.write(str(output_path))
            merger.close()
        else:
            # 舊版 pypdf (用 PdfWriter)
            writer = PdfWriter()
            for pdf_file in pdf_files:
                try:
                    reader = PdfReader(str(pdf_file))
                    for page in reader.pages:
                        writer.add_page(page)
                    print(f"  ✅ 已加入: {pdf_file.name}")
                except Exception as e:
                    print(f"  ⚠️  無法加入: {pdf_file.name} - {e}")
            
            with open(output_path, 'wb') as f:
                writer.write(f)
        
        print(f"\n✅ 合併完成: {output_path.name}")
        return True
    except Exception as e:
        print(f"❌ 合併失敗: {e}")
        return False

# ============ 主程式 ============

def main():
    print("=" * 60)
    print("🚀 Google Drive PDF 自動合併工具")
    print("=" * 60)
    
    temp_dir = Path.home() / '.pdf_merge_temp'
    temp_dir.mkdir(exist_ok=True)
    
    try:
        print("\n📡 連接 Google Drive...")
        service = get_google_drive_service()
        print("✅ 已連接")
        
        # 2. 取得來源資料夾（直接用 ID 或用名稱搜尋）
        if FOLDER_ID:
            # 使用資料夾 ID（共用資料夾）
            print(f"\n📁 使用共用資料夾 ID: {FOLDER_ID}")
            try:
                # 驗證資料夾是否存在且可存取
                folder_info = service.files().get(fileId=FOLDER_ID, fields='id, name').execute()
                source_folder = {'id': FOLDER_ID, 'name': folder_info['name']}
                print(f"✅ 找到資料夾: {source_folder['name']}")
            except Exception as e:
                print(f"❌ 無法存取資料夾 ID: {FOLDER_ID}")
                print(f"   錯誤訊息: {e}")
                print("\n請確認：")
                print("1. 資料夾連結是否正確")
                print("2. 您的 Google 帳號是否有存取權限")
                print("3. 資料夾是否已與您共用")
                sys.exit(1)
        else:
            # 使用資料夾名稱搜尋
            print(f"\n📁 尋找資料夾: {FOLDER_NAME}")
            source_folder = find_folder(service, FOLDER_NAME)
            if not source_folder:
                print(f"❌ 找不到資料夾: {FOLDER_NAME}")
                print("請確認 Google Drive 中有此資料夾")
                sys.exit(1)
            print(f"✅ 找到資料夾: {source_folder['name']}")
        
        print(f"\n📁 檢查資料夾: {PROCESSED_FOLDER}")
        processed_folder = find_folder(service, PROCESSED_FOLDER, source_folder['id'])
        if not processed_folder:
            print(f"   建立新資料夾: {PROCESSED_FOLDER}")
            processed_folder = create_folder(service, PROCESSED_FOLDER, source_folder['id'])
        print(f"✅ 已準備好: {PROCESSED_FOLDER}")
        
        print(f"\n📥 下載檔案...")
        files = list_files_in_folder(service, source_folder['id'])
        files = [f for f in files if f['name'] != PROCESSED_FOLDER]
        
        if not files:
            print("⚠️  資料夾是空的，沒有檔案需要處理")
            sys.exit(0)
        
        print(f"   找到 {len(files)} 個檔案")
        
        downloaded_files = []
        for file in files:
            file_name = file['name']
            file_ext = Path(file_name).suffix.lower()
            
            if file_ext in SUPPORTED_PDFS + SUPPORTED_IMAGES:
                print(f"   ⬇️  {file_name}")
                file_path = download_file(service, file['id'], file_name, temp_dir)
                downloaded_files.append((file['id'], file_path))
        
        if not downloaded_files:
            print("⚠️  沒有找到 PDF 或圖片檔案")
            sys.exit(0)
        
        print(f"\n🔧 處理檔案...")
        pdf_files = []
        
        for file_id, file_path in downloaded_files:
            ext = file_path.suffix.lower()
            
            if ext in SUPPORTED_IMAGES:
                pdf_path = image_to_pdf(file_path)
                if pdf_path:
                    pdf_files.append(pdf_path)
            elif ext in SUPPORTED_PDFS:
                unlocked_pdf = unlock_pdf(file_path, PASSWORDS)
                pdf_files.append(unlocked_pdf)
        
        if not pdf_files:
            print("❌ 沒有可合併的檔案")
            sys.exit(1)
        
        print(f"\n📑 合併 {len(pdf_files)} 個檔案...")
        today = datetime.now().strftime("%Y%m%d-%H%M")
        output_filename = f"合併檔案-{today}.pdf"
        output_path = temp_dir / output_filename
        
        if merge_pdfs(pdf_files, output_path):
            print(f"\n⬆️  上傳到 Google Drive...")
            upload_file(service, output_path, source_folder['id'])
            print(f"✅ 已上傳: {output_filename}")
            
            print(f"\n🗂️  整理檔案...")
            for file_id, _ in downloaded_files:
                move_file(service, file_id, processed_folder['id'])
            print(f"✅ 已移動 {len(downloaded_files)} 個檔案到「{PROCESSED_FOLDER}」")
            
            print("\n" + "=" * 60)
            print("🎉 完成！")
            print(f"✅ 合併檔案: {output_filename}")
            if FOLDER_ID:
                print(f"✅ 位置: Google Drive > {source_folder['name']} (共用資料夾)")
            else:
                print(f"✅ 位置: Google Drive > {FOLDER_NAME}")
            print(f"✅ 原始檔案已移到: {PROCESSED_FOLDER}")
            print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🧹 清理暫存檔案...")
        if temp_dir.exists():
            for file in temp_dir.glob('*'):
                try:
                    file.unlink()
                except:
                    pass
        print("✅ 完成")

if __name__ == '__main__':
    main()
