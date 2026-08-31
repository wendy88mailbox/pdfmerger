import streamlit as st

st.title("🔍 服務帳號空間診斷")

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["credentials"],
        scopes=['https://www.googleapis.com/auth/drive']
    )
    service = build('drive', 'v3', credentials=credentials)
    
    st.success("✅ 已連接到 Google Drive")
    
    # 查詢服務帳號的儲存空間資訊
    st.subheader("📊 儲存空間資訊")
    
    try:
        about = service.about().get(fields='storageQuota, user').execute()
        
        st.write("### 服務帳號資訊")
        if 'user' in about:
            st.json(about['user'])
        
        st.write("### 儲存配額")
        if 'storageQuota' in about:
            quota = about['storageQuota']
            
            limit = int(quota.get('limit', 0))
            usage = int(quota.get('usage', 0))
            usageInDrive = int(quota.get('usageInDrive', 0))
            
            if limit > 0:
                st.metric("總配額", f"{limit / 1024 / 1024 / 1024:.2f} GB")
                st.metric("已使用", f"{usage / 1024 / 1024 / 1024:.2f} GB")
                st.metric("Drive 使用", f"{usageInDrive / 1024 / 1024 / 1024:.2f} GB")
                
                remaining = limit - usage
                st.metric("剩餘空間", f"{remaining / 1024 / 1024 / 1024:.2f} GB")
                
                # 顯示使用率
                usage_percent = (usage / limit) * 100
                st.progress(usage_percent / 100)
                st.write(f"使用率：{usage_percent:.1f}%")
                
                if usage_percent > 90:
                    st.error("⚠️ 空間快用完了！這可能是上傳失敗的原因！")
                elif usage_percent > 70:
                    st.warning("⚠️ 空間使用超過 70%")
                else:
                    st.success("✅ 空間充足")
            else:
                st.error("❌ 服務帳號沒有儲存配額（limit = 0）")
                st.info("💡 這就是問題所在！服務帳號根本沒有儲存空間！")
        else:
            st.error("❌ 無法取得儲存配額資訊")
            st.info("💡 這表示服務帳號可能沒有儲存空間")
    
    except Exception as e:
        st.error(f"❌ 查詢失敗: {e}")
        import traceback
        st.code(traceback.format_exc())
    
    # 列出服務帳號自己的檔案
    st.subheader("📁 服務帳號的檔案")
    
    try:
        results = service.files().list(
            pageSize=20,
            fields='files(id, name, size, createdTime)',
            orderBy='createdTime desc'
        ).execute()
        
        files = results.get('files', [])
        
        if files:
            st.write(f"找到 {len(files)} 個檔案")
            for f in files:
                size_mb = int(f.get('size', 0)) / 1024 / 1024
                st.text(f"📄 {f['name']} ({size_mb:.2f} MB) - {f.get('createdTime', '')[:10]}")
        else:
            st.info("服務帳號的 Drive 是空的")
    
    except Exception as e:
        st.error(f"列出檔案失敗: {e}")

except Exception as e:
    st.error(f"初始化失敗: {e}")
    import traceback
    st.code(traceback.format_exc())
