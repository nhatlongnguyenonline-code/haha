import warnings
import sys
import os
import requests
import httpx
import time
import json
import bcrypt
import numpy as np
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from google import genai
from google.genai import types  
from PIL import Image  
import streamlit as st

warnings.filterwarnings("ignore")

#--- CẤU HÌNH GIAO DIỆN PREMIUM LIGHT MODE KHÓA CHÍNH GIỮA ---
st.set_page_config(page_title="Trợ Lý AI Thông Minh", page_icon="🐦‍🔥", layout="centered")

st.markdown("""
    <style>
    .stApp::before {
        content: "" !important; position: fixed !important; top: 0 !important; left: 0 !important; width: 25px !important; height: 100vh !important;
        background: linear-gradient(180deg, #EF4444, #F97316, #FBBF24, #3B82F6, #8B5CF6) !important; z-index: 9999 !important; box-shadow: 3px 0 15px rgba(239, 68, 68, 0.2) !important;
    }
    .stApp::after {
        content: "" !important; position: fixed !important; top: 0 !important; right: 0 !important; width: 25px !important; height: 100vh !important;
        background: linear-gradient(180deg, #8B5CF6, #3B82F6, #FBBF24, #F97316, #EF4444) !important; z-index: 9999 !important; box-shadow: -3px 0 15px rgba(59, 130, 246, 0.15) !important;
    }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #F8FAFC 0%, #FFF7ED 100%) !important; border-right: 1px solid #FED7AA !important; }
    [data-testid="stChatMessage"] { border-radius: 18px !important; margin-bottom: 16px !important; padding: 16px 20px !important; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03) !important; }
    [data-testid="stChatMessageAssistant"] { background-color: #FFFDFA !important; border: 1px solid #FFE4E6 !important; }
    [data-testid="stChatMessageUser"] { background-color: #F0F6FF !important; border: 1px solid #DBEAFE !important; }
    .stChatInput { position: fixed !important; bottom: 30px !important; left: 50% !important; transform: translateX(-50%) !important; z-index: 999 !important; width: 100% !important; max-width: 550px !important; display: flex !important; justify-content: center !important; }
    .stChatInput [data-testid="stChatInputCurrentContainer"] { width: 100% !important; border: 2px solid #3B82F6 !important; border-radius: 24px !important; background-color: #F8FAFC !important; padding: 4px 10px !important; box-shadow: 0 10px 30px -5px rgba(59, 130, 246, 0.2) !important; }
    .stChatInput textarea { color: #1F2937 !important; font-size: 0.95rem !important; font-weight: 500 !important; }
    .stChatInput button { background-color: #3B82F6 !important; color: white !important; border-radius: 50% !important; }
    [data-testid="stHeaderHeading"] svg, [data-testid="stHeaderHeading"] div, [data-testid="stElementContainer"] h1 svg { display: none !important; }
    [data-testid="stChatMessageAvatar"] { border-radius: 50% !important; display: flex !important; align-items: center !important; justify-content: center !important; font-size: 1.2rem !important; }
    .premium-title-container { display: flex; align-items: center; justify-content: center; gap: 12px; margin-top: 1.5rem; margin-bottom: 4px; }
    .premium-logo { font-size: 2.5rem; }
    .premium-text { font-size: 2.3rem; font-weight: 800; letter-spacing: -0.5px; background: linear-gradient(90deg, #EF4444, #3B82F6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .sub-title { text-align: center; color: #64748B !important; font-size: 0.95rem; margin-bottom: 1.5rem; }
    .login-box { padding: 20px; border-radius: 12px; background: #FFFDFB; border: 1px solid #FFE4E6; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="premium-title-container"><span class="premium-logo">🐦‍🔥</span><span class="premium-text">TRỢ LÝ AI TOÀN NĂNG</span></div>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Hệ thống đọc hiểu kiến thức, phân tích hình ảnh và tra cứu Internet</p>', unsafe_allow_html=True)

# Khai báo các tệp lưu trữ dữ liệu vĩnh viễn trên Server
DB_FILE = "users_database.json"
HISTORY_FILE = "chat_history_database.json"

def load_user_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def save_user_db(db_data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(db_data, f, ensure_ascii=False, indent=4)

def load_all_chat_histories():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def save_all_chat_histories(history_data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f: json.dump(history_data, f, ensure_ascii=False, indent=4)

user_db = load_user_db()
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.warning("⚠️ Hệ thống đang chờ cấu hình mã GEMINI_API_KEY ngầm trong mục Secrets!")
    st.stop()

if "ai_client" not in st.session_state:
    try: st.session_state.ai_client = genai.Client(api_key=API_KEY)
    except Exception as e: st.error(f"Lỗi khởi tạo bộ não AI: {e}")

def get_embedding(text):
    try:
        response = st.session_state.ai_client.models.embed_content(model="text-embedding-004", contents=text)
        return response.embeddings.values
    except: return None

# --- KIỂM TRA PHIÊN ĐĂNG NHẬP QUA THAM SỐ URL ---
url_params = st.query_params
logged_in_user = url_params.get("user", None)

if logged_in_user is None:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["🔒 Đăng Nhập", "📝 Đăng Ký Tài Khoản", "🌐 Google Login"])
    
    with tab1:
        st.subheader("Đăng nhập hệ thống")
        lin_user = st.text_input("Tên đăng nhập", key="lin_u")
        lin_pass = st.text_input("Mật khẩu", type="password", key="lin_p")
        if st.button("Đăng Nhập Khách", use_container_width=True, type="primary"):
            if lin_user in user_db:
                stored_hashed = user_db[lin_user].encode('utf-8')
                if bcrypt.checkpw(lin_pass.encode('utf-8'), stored_hashed):
                    st.query_params["user"] = lin_user
                    st.success(f"🎉 Chào mừng {lin_user} quay trở lại!")
                    st.rerun()
                else: st.error("❌ Sai mật khẩu, vui lòng kiểm tra lại.")
            else: st.error("❌ Tài khoản không tồn tại. Hãy qua tab Đăng Ký.")
            
    with tab2:
        st.subheader("Tạo tài khoản mới")
        reg_user = st.text_input("Tên đăng nhập mới", key="reg_u")
        reg_pass = st.text_input("Mật khẩu mới", type="password", key="reg_p")
        if st.button("Xác Nhận Đăng Ký", use_container_width=True):
            if reg_user.strip() == "" or reg_pass.strip() == "":
                st.warning("⚠️ Không được để trống tài khoản hoặc mật khẩu.")
            elif reg_user in user_db: st.error("❌ Tên đăng nhập này đã được sử dụng.")
            else:
                hashed_p = bcrypt.hashpw(reg_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                user_db[reg_user] = hashed_p
                save_user_db(user_db)
                st.success("📝 Đăng ký thành công! Hãy quay lại tab Đăng Nhập.")
                
    with tab3:
        st.subheader("Đăng nhập nhanh an toàn")
        if st.button("🔴 Đăng nhập bằng Google", use_container_width=True):
            st.query_params["user"] = "google_user"
            st.success("🎉 Đăng nhập Google thành công!")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

u_id = logged_in_user
pages_key = f"chat_pages_{u_id}"      
active_page_key = f"active_page_{u_id}" 
cache_key = f"cache_{u_id}"

all_histories = load_all_chat_histories()

# --- LOGIC TỰ ĐỘNG TẠO TRANG CHAT MỚI KHI RESTART/F5 TRANG ---
if pages_key not in st.session_state:
    if u_id in all_histories and all_histories[u_id]:
        existing_pages = all_histories[u_id]
        new_page_index = len(existing_pages) + 1
        new_page_name = f"Trang Chat {new_page_index}"
        
        existing_pages[new_page_name] = []
        st.session_state[pages_key] = existing_pages
        
        all_histories[u_id] = existing_pages
        save_all_chat_histories(all_histories)
        st.session_state[active_page_key] = new_page_name
    else:
        st.session_state[pages_key] = {"Trang Chat 1": []}
        all_histories[u_id] = st.session_state[pages_key]
        save_all_chat_histories(all_histories)
        st.session_state[active_page_key] = "Trang Chat 1"

if active_page_key not in st.session_state:
    st.session_state[active_page_key] = list(st.session_state[pages_key].keys())[-1]
if cache_key not in st.session_state:
    st.session_state[cache_key] = []

current_page = st.session_state[active_page_key]
with st.sidebar:
    st.markdown(f"### 👤 TÀI KHOẢN: **{u_id.upper()}**")
    if st.button("🚪 Đăng Xuất Hệ Thống", use_container_width=True, type="secondary"):
        st.query_params.clear()
        st.rerun()
    st.markdown("---")
    
    st.markdown("### 💬 QUẢN LÝ PHÒNG CHAT")
    if st.button("➕ Tạo trang chat mới", use_container_width=True, type="primary"):
        new_page_index = len(st.session_state[pages_key]) + 1
        new_page_name = f"Trang Chat {new_page_index}"
        st.session_state[pages_key][new_page_name] = []
        all_histories[u_id] = st.session_state[pages_key]
        save_all_chat_histories(all_histories)
        st.session_state[active_page_key] = new_page_name
        st.rerun()
        
    page_options = list(st.session_state[pages_key].keys())
    if current_page not in page_options: current_page = page_options[-1]
    selected_page = st.selectbox("Chọn trang hội thoại đang xem:", page_options, index=page_options.index(current_page))
    if selected_page != current_page:
        st.session_state[active_page_key] = selected_page
        st.rerun()
        
    # --- TÍNH NĂNG ĐỔI TÊN PHÒNG CHAT CHỦ ĐỘNG ---
    if f"rename_mode_{u_id}" not in st.session_state:
        st.session_state[f"rename_mode_{u_id}"] = False
        
    if not st.session_state[f"rename_mode_{u_id}"]:
        if st.button("✏️ Đổi tên trang này", use_container_width=True):
            st.session_state[f"rename_mode_{u_id}"] = True
            st.rerun()
    else:
        new_title = st.text_input("Nhập tên mới cho trang chat:", value=current_page)
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button("✅ Lưu tên", use_container_width=True, type="primary"):
                if new_title.strip() != "" and new_title != current_page:
                    updated_pages = {}
                    for k, v in st.session_state[pages_key].items():
                        if k == current_page: updated_pages[new_title.strip()] = v
                        else: updated_pages[k] = v
                    
                    st.session_state[pages_key] = updated_pages
                    st.session_state[active_page_key] = new_title.strip()
                    
                    all_histories[u_id] = updated_pages
                    save_all_chat_histories(all_histories)
                    
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
    
    # --- BỘ ĐÔI NÚT XÓA SONG SONG NẰM CÙNG MỘT DÒNG ---
    st.markdown("### 📂 NHẬT KÝ TRANG HIỆN TẠI")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑 ... Dọn tin", use_container_width=True):
            st.session_state[pages_key][current_page] = []
            all_histories[u_id] = st.session_state[pages_key]
            save_all_chat_histories(all_histories)
            st.rerun()
    with col2:
        if len(page_options) > 1:
            if st.button("❌ Xóa trang", use_container_width=True):
                del st.session_state[pages_key][current_page]
                all_histories[u_id] = st.session_state[pages_key]
                save_all_chat_histories(all_histories)
                st.session_state[active_page_key] = list(st.session_state[pages_key].keys())[-1]
                st.rerun()
        else:
            st.caption("🔒 Giữ lại 1 trang.")
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

# Hiển thị lịch sử hội thoại của trang đang chọn
for message in st.session_state[pages_key][current_page]:
    avt_emoji = "👤" if message["role"] == "user" else "🐦‍🔥"
    with st.chat_message(message["role"], avatar=avt_emoji): st.markdown(message["content"])

if user_input := st.chat_input("Nhập câu hỏi hoặc yêu cầu phân tích ảnh tại đây..."):
    st.session_state[pages_key][current_page].append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"): st.markdown(user_input)

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
            st.caption(f"⚡ *Phản hồi ngay lập tức từ cache của {current_page}*")
            st.session_state[pages_key][current_page].append({"role": "assistant", "content": cached_answer})
            all_histories[u_id] = st.session_state[pages_key]
            save_all_chat_histories(all_histories)
    else:
        cau_hoi_clean = user_input.lower().strip()
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
            with st.status("🔍 Đang kết nối mạng và tra cứu thông tin thực tế rộng...", expanded=False) as status:
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
                f"Bạn là Trợ lý AI Toàn năng. Dưới đây là thông tin cập nhật từ Internet để tham khảo (nếu có liên quan):\n"
                f"{combined_context}\n\n"
                f"Yêu cầu: Hãy trả lời câu hỏi sau của người dùng một cách chi tiết và mở rộng nhất. "
                f"Nếu thông tin Internet trên chưa đủ hoặc không liên quan, hãy chủ động sử dụng toàn bộ kiến thức nội tại của bạn để giải thích đầy đủ cho người dùng.\n"
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
                all_histories[u_id] = st.session_state[pages_key]
                save_all_chat_histories(all_histories)
                
                if not uploaded_file:
                    new_embedding = get_embedding(user_input)
                    if new_embedding is not None:
                        st.session_state[cache_key].append({
                            "embedding": new_embedding, "question": user_input, "answer": ai_response
                        })
            except Exception as e:
                st.markdown(f"❌ Hệ thống bận: {e}. Bạn vui lòng thử gõ lại câu hỏi nhé!")
