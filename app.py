import warnings
import sys
import os
import requests
import httpx
import time
import json
import bcrypt
import secrets  
import numpy as np
import io
import base64
import urllib.parse
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from google import genai
from google.genai import types  
from PIL import Image  
import streamlit as st
from supabase import create_client, Client

warnings.filterwarnings("ignore")

#--- CẤU HÌNH GIAO DIỆN PREMIUM LIGHT MODE SẠCH SẼ (XÓA GRADIENT HAI BÊN) ---
st.set_page_config(page_title="Trợ Lý AI Toàn Năng", page_icon="🐦‍🔥", layout="centered")
st.markdown("""
    <style>
    /* XÓA HOÀN TOÀN THANH GRADIENT HAI BÊN KHỎI .stApp::before VÀ .stApp::after */
    [data-testid="stSidebar"] { 
        background: linear-gradient(180deg, #F8FAFC 0%, #FFF7ED 100%) !important; 
        border-right: 1px solid #FED7AA !important; 
    }
    [data-testid="stChatMessage"] { 
        border-radius: 18px !important; 
        margin-bottom: 16px !important; 
        padding: 16px 20px !important; 
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03) !important; 
    }
    [data-testid="stChatMessageAssistant"] { 
        background-color: #FFFDFA !important; 
        border: 1px solid #FFE4E6 !important; 
    }
    [data-testid="stChatMessageUser"] { 
        background-color: #F0F6FF !important; 
        border: 1px solid #DBEAFE !important; 
    }
    .stChatInput { 
        position: fixed !important; 
        bottom: 30px !important; 
        left: 50% !important; 
        transform: translateX(-50%) !important; 
        z-index: 999 !important; 
        width: 100% !important; 
        max-width: 550px !important; 
        display: flex !important; 
        justify-content: center !important; 
    }
    .stChatInput [data-testid="stChatInputCurrentContainer"] { 
        width: 100% !important; 
        border: 2px solid #3B82F6 !important; 
        border-radius: 24px !important; 
        background-color: #F8FAFC !important; 
        padding: 4px 10px !important; 
        box-shadow: 0 10px 30px -5px rgba(59, 130, 246, 0.2) !important; 
    }
    .stChatInput textarea { 
        color: #1F2937 !important; 
        font-size: 0.95rem !important; 
        font-weight: 500 !important; 
    }
    .stChatInput button { 
        background-color: #3B82F6 !important; 
        color: white !important; 
        border-radius: 50% !important; 
    }
    [data-testid="stHeaderHeading"] svg, [data-testid="stElementContainer"] h1 svg { 
        display: none !important; 
    }
    [data-testid="stChatMessageAvatar"] { 
        border-radius: 50% !important; 
        display: flex !important; 
        align-items: center !important; 
        justify-content: center !important; 
        font-size: 1.2rem !important; 
    }
    .premium-title-container { 
        display: flex; 
        align-items: center; 
        justify-content: center; 
        gap: 12px; 
        margin-top: 1.5rem; 
        margin-bottom: 4px; 
    }
    .premium-logo { font-size: 2.5rem; }
    .premium-text { 
        font-size: 2.3rem; 
        font-weight: 800; 
        letter-spacing: -0.5px; 
        background: linear-gradient(90deg, #EF4444, #3B82F6); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
    }
    .sub-title { 
        text-align: center; 
        color: #64748B !important; 
        font-size: 0.95rem; 
        margin-bottom: 1.5rem; 
    }
    .login-box { 
        padding: 20px; 
        border-radius: 12px; 
        background: #FFFDFB; 
        border: 1px solid #FFE4E6; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); 
        margin-bottom: 20px; 
    }
    </style>
""", unsafe_allow_html=True)
# Khởi tạo kết nối đám mây Supabase
try:
    SB_URL = st.secrets["SUPABASE_URL"]
    SB_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SB_URL, SB_KEY)
except:
    st.warning("⚠️ Hệ thống đang chờ cấu hình SUPABASE_URL và SUPABASE_KEY ngầm trong Secrets!")
    st.stop()

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.warning("⚠️ Hệ thống đang chờ cấu hình mã GEMINI_API_KEY ngầm trong Secrets!")
    st.stop()

if "ai_client" not in st.session_state:
    try: st.session_state.ai_client = genai.Client(api_key=API_KEY)
    except Exception as e: st.error(f"Lỗi khởi tạo bộ não AI: {e}")

def get_embedding(text):
    try:
        response = st.session_state.ai_client.models.embed_content(model="text-embedding-004", contents=text)
        return response.embeddings.values
    except: return None

if "global_token_registry" not in st.session_state:
    st.session_state.global_token_registry = {}

url_params = st.query_params
current_url_token = url_params.get("token", None)

logged_in_user = None
if current_url_token and current_url_token in st.session_state.global_token_registry:
    logged_in_user = st.session_state.global_token_registry[current_url_token]

if logged_in_user is None:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🔒 Đăng Nhập", "📝 Đăng Ký Tài Khoản"])
    
    with tab1:
        st.subheader("Đăng nhập hệ thống")
        lin_user = st.text_input("Tên đăng nhập", key="lin_u").strip()
        lin_pass = st.text_input("Mật khẩu", type="password", key="lin_p")
        if st.button("Đăng Nhập Khách", use_container_width=True, type="primary"):
            res = supabase.table("users").select("*").eq("username", lin_user).execute()
            if res.data:
                user_data = res.data[0] if isinstance(res.data, list) else res.data
                if bcrypt.checkpw(lin_pass.encode('utf-8'), user_data["password"].encode('utf-8')):
                    secure_token = secrets.token_urlsafe(16)
                    st.session_state.global_token_registry[secure_token] = lin_user
                    st.query_params["token"] = secure_token
                    st.success(f"🎉 Chào mừng {lin_user} quay trở lại!")
                    st.rerun()
                else: st.error("❌ Sai mật khẩu, vui lòng kiểm tra lại.")
            else: st.error("❌ Tài khoản không tồn tại. Hãy qua tab Đăng Ký.")
            
    with tab2:
        st.subheader("Tạo tài khoản mới")
        reg_user = st.text_input("Tên đăng nhập mới", key="reg_u").strip()
        reg_pass = st.text_input("Mật khẩu mới", type="password", key="reg_p")
        if st.button("Xác Nhận Đăng Ký", use_container_width=True):
            if reg_user == "" or reg_pass.strip() == "":
                st.warning("⚠️ Không được để trống tài khoản hoặc mật khẩu.")
            else:
                check_res = supabase.table("users").select("username").eq("username", reg_user).execute()
                if check_res.data: st.error("❌ Tên đăng nhập này đã được sử dụng.")
                else:
                    hashed_p = bcrypt.hashpw(reg_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    supabase.table("users").insert({
                        "username": reg_user, "password": hashed_p, "display_name": reg_user
                    }).execute()
                    st.success("📝 Đăng ký thành công! Hãy quay lại tab Đăng Nhập.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()
u_id = logged_in_user
pages_key = f"chat_pages_{u_id}"      
active_page_key = f"active_page_{u_id}" 
cache_key = f"cache_{u_id}"

def download_supabase_history(username):
    pages = {}
    res = supabase.table("chat_histories").select("*").eq("username", username).execute()
    if res.data:
        for row in res.data:
            pages[row["page_name"]] = row["history_data"]
    return pages

def upload_single_page_supabase(username, page_name, data_list):
    supabase.table("chat_histories").upsert({
        "username": username, "page_name": page_name, "history_data": data_list
    }).execute()

if pages_key not in st.session_state:
    db_pages = download_supabase_history(u_id)
    if db_pages:
        new_page_index = len(db_pages) + 1
        new_page_name = f"Trang Chat {new_page_index}"
        db_pages[new_page_name] = []
        st.session_state[pages_key] = db_pages
        upload_single_page_supabase(u_id, new_page_name, [])
        st.session_state[active_page_key] = new_page_name
    else:
        st.session_state[pages_key] = {"Trang Chat 1": []}
        upload_single_page_supabase(u_id, "Trang Chat 1", [])
        st.session_state[active_page_key] = "Trang Chat 1"

if active_page_key not in st.session_state:
    st.session_state[active_page_key] = list(st.session_state[pages_key].keys())[-1]
if cache_key not in st.session_state:
    st.session_state[cache_key] = []

current_page = st.session_state[active_page_key]
user_info_res = supabase.table("users").select("display_name").eq("username", u_id).execute()
display_name = user_info_res.data[0]["display_name"] if user_info_res.data else u_id

with st.sidebar:
    st.markdown(f"### 👤 TÀI KHOẢN: **{display_name.upper()}**")
    if f"rename_user_mode_{u_id}" not in st.session_state:
        st.session_state[f"rename_user_mode_{u_id}"] = False
        
    if not st.session_state[f"rename_user_mode_{u_id}"]:
        if st.button("✏️ Đổi tên hiển thị", use_container_width=True):
            st.session_state[f"rename_user_mode_{u_id}"] = True
            st.rerun()
    else:
        new_name = st.text_input("Nhập tên hiển thị mới:", value=display_name).strip()
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            if st.button("💾 Lưu tên", use_container_width=True, type="primary"):
                if new_name != "":
                    supabase.table("users").update({"display_name": new_name}).eq("username", u_id).execute()
                st.session_state[f"rename_user_mode_{u_id}"] = False
                st.rerun()
        with col_u2:
            if st.button("Cancel", use_container_width=True):
                st.session_state[f"rename_user_mode_{u_id}"] = False
                st.rerun()
                
    if st.button("🚪 Đăng Xuất Hệ Thống", use_container_width=True, type="secondary"):
        if current_url_token in st.session_state.global_token_registry:
            del st.session_state.global_token_registry[current_url_token]
        st.query_params.clear()
        st.rerun()
        
    st.markdown("---")
    st.markdown("### 💬 QUẢN LÝ PHÒNG CHAT")
    if st.button("➕ Tạo trang chat mới", use_container_width=True, type="primary"):
        new_page_index = len(st.session_state[pages_key]) + 1
        new_page_name = f"Trang Chat {new_page_index}"
        st.session_state[pages_key][new_page_name] = []
        upload_single_page_supabase(u_id, new_page_name, [])
        st.session_state[active_page_key] = new_page_name
        st.rerun()
        
    page_options = list(st.session_state[pages_key].keys())
    if current_page not in page_options: current_page = page_options[-1]
    selected_page = st.selectbox("Chọn trang hội thoại đang xem:", page_options, index=page_options.index(current_page))
    if selected_page != current_page:
        st.session_state[active_page_key] = selected_page
        st.rerun()
        
    if f"rename_mode_{u_id}" not in st.session_state:
        st.session_state[f"rename_mode_{u_id}"] = False
        
    if not st.session_state[f"rename_mode_{u_id}"]:
        if st.button("✏️ Đổi tên trang này", use_container_width=True):
            st.session_state[f"rename_mode_{u_id}"] = True
            st.rerun()
    else:
        new_title = st.text_input("Nhập tên mới:", value=current_page).strip()
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button("✅ Lưu tên", use_container_width=True, type="primary"):
                if new_title != "" and new_title != current_page:
                    supabase.table("chat_histories").delete().eq("username", u_id).eq("page_name", current_page).execute()
                    upload_single_page_supabase(u_id, new_title, st.session_state[pages_key][current_page])
                    st.session_state[pages_key][new_title] = st.session_state[pages_key].pop(current_page)
                    st.session_state[active_page_key] = new_title
                st.session_state[f"rename_mode_{u_id}"] = False
                st.rerun()
        with col_r2:
            if st.button("❌ Hủy", use_container_width=True):
                st.session_state[f"rename_mode_{u_id}"] = False
                st.rerun()
        
    st.markdown("---")
    st.markdown("### ⚙️ CÀI ĐẶT CHATBOT")
    creativity = st.slider("🧠 Độ nhạy bén / Sáng tạo", min_value=0.1, max_value=1.0, value=0.3, step=0.1)
    st.markdown("---")
    st.markdown("### 📸 PHÂN TÍCH HÌNH ẢNH")
    uploaded_file = st.file_uploader("Tải ảnh lên tại đây...", type=["png", "jpg", "jpeg"])
    if uploaded_file: st.image(Image.open(uploaded_file), caption="Ảnh đã chọn", use_container_width=True)
    st.markdown("---")
    
    st.markdown("### 📂 NHẬT KÝ TRANG HIỆN TẠI")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑 ... Dọn tin", use_container_width=True):
            st.session_state[pages_key][current_page] = []
            upload_single_page_supabase(u_id, current_page, [])
            st.rerun()
    with col2:
        if len(page_options) > 1:
            if st.button("❌ Xóa trang", use_container_width=True):
                supabase.table("chat_histories").delete().eq("username", u_id).eq("page_name", current_page).execute()
                del st.session_state[pages_key][current_page]
                st.session_state[active_page_key] = list(st.session_state[pages_key].keys())[-1]
                st.rerun()
        else: st.caption("🔒 Giữ lại 1 trang.")
def search_the_web_ddg(query, max_results=3):
    urls = []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            for r in results: urls.append(r['href'])
    except: pass
    return urls

def extract_web_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=4)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            for element in soup(["script", "style", "nav", "footer", "header", "aside", "form"]): element.decompose()
            return ' '.join(soup.get_text().split())[:1500]
    except: pass
    return ""

st.markdown(f"""
    <div class="premium-title-container">
        <span class="premium-logo">🐦‍🔥</span>
        <span class="premium-text">TRỢ LÝ AI TOÀN NĂNG</span>
    </div>
    <div class="sub-title">Hệ thống AI Chatbot tích hợp siêu lõi Gemini 3.6, Đám mây Supabase và Siêu lõi FLUX</div>
""", unsafe_allow_html=True)

# Hiển thị lịch sử hội thoại (Xử lý thông minh nếu dữ liệu tin nhắn lưu là ảnh Base64)
for message in st.session_state[pages_key][current_page]:
    avt_emoji = "👤" if message["role"] == "user" else "🐦‍🔥"
    with st.chat_message(message["role"], avatar=avt_emoji):
        if message["content"].startswith("data:image/png;base64,"):
            base64_data = message["content"].split(",")
            img_bytes = base64.b64decode(base64_data[1] if len(base64_data) > 1 else base64_data[0])
            st.image(Image.open(io.BytesIO(img_bytes)))
        else:
            st.markdown(message["content"])

if user_input := st.chat_input("Nhập câu hỏi, yêu cầu phân tích ảnh hoặc yêu cầu vẽ tranh tại đây..."):
    st.session_state[pages_key][current_page].append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"): st.markdown(user_input)
    cau_hoi_clean = user_input.lower().strip()
    
    # 1. BỘ LỌC TỪ KHÓA KÍCH HOẠT ĐỘNG CƠ SINH ẢNH MIỄN PHÍ QUA HUGGING FACE FLUX
    image_keywords = ["vẽ", "tạo ảnh", "tạo hình", "bức tranh", "bức ảnh", "hình ảnh về", "vẽ tranh", "generate image", "create an image"]
    is_image_request = any(word in cau_hoi_clean for word in image_keywords)
    if is_image_request and not uploaded_file:
        with st.chat_message("assistant", avatar="🐦‍🔥"):
            with st.status("🎨 Đang dịch mô tả và kích hoạt lõi FLUX xử lý ảnh nghệ thuật...", expanded=True) as status:
                try:
                    # Sử dụng Gemini 3.6 dịch mô tả tiếng Việt sang tiếng Anh chuyên sâu cho mô hình nghệ thuật FLUX
                    translation_prompt = (
                        "Translate this image description into a highly detailed, high-quality cinematic prompt for FLUX image generation. "
                        f"Return ONLY the English prompt, no extra text, no quotes: {user_input}"
                    )
                    translated_response = st.session_state.ai_client.models.generate_content(
                        model='gemini-3.6-flash', contents=translation_prompt
                    )
                    english_prompt = translated_response.text.strip().replace("\n", " ").replace("\r", " ")
                    
                    # Sử dụng cổng API của siêu mô hình FLUX thế hệ mới
                    API_URL = "https://huggingface.co"
                    headers = {}
                    if "HF_TOKEN" in st.secrets:
                        headers["Authorization"] = f"Bearer {st.secrets['HF_TOKEN']}"
                    
                    payload = {"inputs": english_prompt}
                    img_response = requests.post(API_URL, headers=headers, json=payload, timeout=45)
                    
                    # Kiểm tra dữ liệu ảnh trả về từ cổng chính Hugging Face
                    if img_response.status_code == 200 and b"internal_server_error" not in img_response.content and b"error" not in img_response.content:
                        image_raw = Image.open(io.BytesIO(img_response.content))
                        st.image(image_raw, caption=f"🎨 Tác phẩm đỉnh cao từ lõi FLUX: {user_input}")
                        
                        # Mã hóa chuỗi nhị phân sang Base64 để ghi vĩnh viễn lên mây Supabase
                        img_str = base64.b64encode(img_response.content).decode()
                        db_payload = f"data:image/png;base64,{img_str}"
                        st.session_state[pages_key][current_page].append({"role": "assistant", "content": db_payload})
                        upload_single_page_supabase(u_id, current_page, st.session_state[pages_key][current_page])
                        status.update(label="🎨 Siêu lõi FLUX đã hoàn thành bức vẽ nghệ thuật xuất sắc!", state="complete")
                    else:
                        # VÁ LỖI TẬN GỐC: Kích hoạt Cổng dự phòng gửi ngầm dữ liệu an toàn qua urllib tách biệt host
                        backup_base = "https://pollinations.ai"
                        safe_prompt = urllib.parse.quote(english_prompt)
                        final_backup_url = f"{backup_base}{safe_prompt}?width=1024&height=1024&nologo=true&seed={secrets.randbelow(99999)}"
                        
                        backup_res = requests.get(final_backup_url, timeout=30)
                        if backup_res.status_code == 200:
                            image_raw = Image.open(io.BytesIO(backup_res.content))
                            st.image(image_raw, caption=f"🎨 Tác phẩm hoàn thành (Cổng tối ưu): {user_input}")
                            
                            img_str = base64.b64encode(backup_res.content).decode()
                            db_payload = f"data:image/png;base64,{img_str}"
                            st.session_state[pages_key][current_page].append({"role": "assistant", "content": db_payload})
                            upload_single_page_supabase(u_id, current_page, st.session_state[pages_key][current_page])
                            status.update(label="🎨 Đã hoàn thành bức vẽ nghệ thuật qua cổng tối ưu hóa dữ liệu!", state="complete")
                        else:
                            raise Exception("Cả hai cổng sinh ảnh đám mây hiện tại đều đang bận xử lý.")
                except Exception as img_err:
                    status.update(label="❌ Lỗi tạo ảnh!", state="error")
                    st.markdown(f"Hệ thống không thể vẽ ảnh lúc này: {img_err}")
    else:
        # 2. LUỒNG XỬ LÝ VĂN BẢN VÀ TRA CỨU WEB MẶC ĐỊNH SỬ DỤNG DUY NHẤT LÕI GEMINI 3.6
        cache_hit = False
        cached_answer = ""
        if not uploaded_file:
            current_embedding = get_embedding(user_input)
            if current_embedding is not None:
                best_score = -1
                best_match = None
                for item in st.session_state[cache_key]:
                    dot_product = np.dot(current_embedding, item["embedding"])
                    norm_a = np.linalg.norm(current_embedding)
                    norm_b = np.linalg.norm(item["embedding"])
                    similarity = dot_product / (norm_a * norm_b)
                    if similarity > best_score:
                        best_score = similarity
                        best_match = item
                if best_score >= 0.85 and best_match is not None:
                    cache_hit = True
                    cached_answer = best_match["answer"]

        if cache_hit:
            with st.chat_message("assistant", avatar="🐦‍🔥"):
                st.markdown(cached_answer)
                st.caption(f"⚡ *Phản hồi từ cache của {current_page}*")
                st.session_state[pages_key][current_page].append({"role": "assistant", "content": cached_answer})
                upload_single_page_supabase(u_id, current_page, st.session_state[pages_key][current_page])
        else:
            keywords = [
                "ở đâu", "thành phố", "giá", "thời tiết", "mấy độ", "bao nhiêu", "hôm nay", "tin tức", "ai là", "sự kiện", "trường thcs", "là gì", "dịch", "nghĩa là gì",
                "mới nhất", "vừa qua", "hiện tại", "năm nay", "tuần này", "tháng này", "vừa mới", "gần đây", "ngày mai", "hôm qua",
                "giá vàng", "xăng dầu", "cổ phiếu", "tỷ giá", "usd", "bitcoin", "crypto", "thị trường",
                "tỷ số", "trận đấu", "bóng đá", "ngoại hạng anh", "champions league", "kết quả", "lịch thi đấu", "drama", "scandal", "showbiz",
                "bản cập nhật", "vừa ra mắt", "ios", "android", "review", "đập hộp", "mở bán", "update", "thông số", "mô hình"
            ]
            need_web = any(word in cau_hoi_clean for word in keywords)
            combined_context = ""
            sources = []
            
            if need_web and not uploaded_file:
                with st.status("🔍 Đang tra cứu thông tin thực tế rộng...", expanded=False) as status:
                    web_links = search_the_web_ddg(user_input)
                    if web_links:
                        for link in web_links:
                            content = extract_web_content(link)
                            if content:
                                combined_context += f"\n--- Nguồn tham khảo: {link} ---\n{content}\n"
                                sources.append(link)
                        status.update(label=" Đọc dữ liệu thành công!", state="complete")

            if combined_context:
                prompt_payload = (
                    f"Bạn là Trợ lý AI Toàn năng. Dưới đây là thông tin cập nhật từ Internet để tham khảo:\n"
                    f"{combined_context}\n\n"
                    f"Yêu cầu: Trả lời chi tiết dựa trên thông tin này hoặc kiến thức nội tại.\n"
                    f"CÂU HỎI: {user_input}"
                )
            else: prompt_payload = user_input

            with st.chat_message("assistant", avatar="🐦‍🔥"):
                try:
                    chat_session_key = f"ai_session_{u_id}_{current_page}"
                    if chat_session_key not in st.session_state:
                        st.session_state[chat_session_key] = st.session_state.ai_client.chats.create(model="gemini-3.6-flash")

                    def response_generator():
                        if uploaded_file:
                            response_stream = st.session_state.ai_client.models.generate_content_stream(
                                model='gemini-3.6-flash',
                                contents=[Image.open(uploaded_file), prompt_payload],
                                config=types.GenerateContentConfig(temperature=creativity)
                            )
                        else:
                            response_stream = st.session_state[chat_session_key].send_message_stream(prompt_payload, config={"temperature": creativity})
                        for chunk in response_stream: yield chunk.text

                    ai_response = st.write_stream(response_generator())
                    if sources:
                        source_text = "\n\n---\n🌐 **Nguồn liên kết tham cứu:**\n" + "\n".join([f"- {src}" for src in sources])
                        st.markdown(source_text)
                        ai_response += source_text
                    
                    st.session_state[pages_key][current_page].append({"role": "assistant", "content": ai_response})
                    upload_single_page_supabase(u_id, current_page, st.session_state[pages_key][current_page])
                    
                    if not uploaded_file:
                        new_embedding = get_embedding(user_input)
                        if new_embedding is not None:
                            st.session_state[cache_key].append({
                                "embedding": new_embedding, "question": user_input, "answer": ai_response
                            })
                except Exception as e:
                    st.markdown(f"❌ Hệ thống bận: {e}. Bạn vui lòng thử lại nhé!")
