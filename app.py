import warnings
import sys
import os
import requests
import time
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from google import genai  # Sử dụng thư viện SDK thế hệ mới của Google
import streamlit as st

warnings.filterwarnings("ignore")

#--- 1. CẤU HÌNH GIAO DIỆN ĐỒ HỌA CAO CẤP (CYBERCHAT) ---
st.set_page_config(page_title="CyberChat Gemini API", page_icon="🔮", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #E2E8F0; }
    .stChatInput [data-testid="stChatInputCurrentContainer"] {
        border: 1px solid #3F83F8 !important; border-radius: 20px !important; background-color: #1A1F2C !important;
    }
    .main-title {
        font-size: 2.5rem; font-weight: 800; background: linear-gradient(90deg, #3B82F6, #8B5CF6);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; margin-bottom: 0px;
    }
    .sub-title { text-align: center; color: #94A3B8; font-size: 0.95rem; margin-bottom: 2rem; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">🔮 CYBERCHAT GEMINI API</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Trợ lý AI sử dụng bộ bộ não Gemini chính thức kết hợp tìm kiếm Internet diện rộng</p>', unsafe_allow_html=True)

# Lấy API Key từ mục Secrets bảo mật của Streamlit Cloud
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.warning("⚠️ Hệ thống đang chờ cấu hình mã GEMINI_API_KEY ngầm trong mục Secrets!")
    st.stop()

# Khởi tạo bộ não AI Client thế hệ mới bằng SDK google-genai
if "ai_client" not in st.session_state:
    try:
        st.session_state.ai_client = genai.Client(api_key=API_KEY)
        # Sử dụng mô hình gemini-2.5-flash chuẩn toàn cầu, chạy siêu tốc và ổn định tuyệt đối
        st.session_state.chat_session = st.session_state.ai_client.chats.create(model="gemini-3.6-flash")
    except Exception as e:
        st.error(f"Lỗi kết nối bộ não AI: {e}. Vui lòng kiểm tra lại Key trong mục Secrets.")

#--- 2. CÁC HÀM XỬ LÝ TÌM KIẾM & CÀO WEB DIỆN RỘNG ---
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
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            for element in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
                element.decompose()
            text = soup.get_text(separator=' ')
            return ' '.join(text.split())[:1500]
    except: pass
    return ""

if "messages" not in st.session_state:
    st.session_state.messages = []

#--- 3. THANH SIDEBAR QUẢN LÝ ỨNG DỤNG ---
with st.sidebar:
    st.markdown("### 🛠️ ĐIỀU KHIỂN CHATBOT")
    creativity = st.slider("🧠 Độ sáng tạo của AI", min_value=0.1, max_value=1.0, value=0.3, step=0.1)
    st.markdown("---")
    st.markdown("### 📂 QUẢN LÝ DỮ LIỆU")
    if st.session_state.messages:
        chat_history_text = "NHẬT KÝ HỘI THOẠI CYBERCHAT AI\n" + "="*50 + "\n"
        for msg in st.session_state.messages:
            role_name = "Bạn" if msg["role"] == "user" else "AI Trợ Lý"
            chat_history_text += f"\n[ {role_name} ]: {msg['content']}\n"
        st.download_button(label="📥 Tải lịch sử chat (.txt)", data=chat_history_text, file_name="CyberChat_History.txt", mime="text/plain", use_container_width=True)
        if st.button("🗑️ Xóa toàn bộ cuộc trò chuyện", use_container_width=True):
            st.session_state.messages = []
            st.session_state.chat_session = st.session_state.ai_client.chats.create(model="gemini-2.5-flash")
            st.rerun()
    else:
        st.caption("Trò chuyện với AI để kích hoạt tính năng tải tệp lịch sử.")

# Hiển thị lịch sử bong bóng chat cũ lên màn hình web
for message in st.session_state.messages:
    avatar_icon = "👤" if message["role"] == "user" else "🔮"
    with st.chat_message(message["role"], avatar=avatar_icon): 
        st.markdown(message["content"])

#--- 4. KHUNG NHẬP LIỆU VÀ XỬ LÝ LOGIC ---
if user_input := st.chat_input("Nhập câu hỏi hoặc yêu cầu tra cứu internet vào đây..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"): 
        st.markdown(user_input)

    cau_hoi_clean = user_input.lower().strip()
    keywords = ["ở đâu", "thành phố", "giá", "thời tiết", "mấy độ", "bao nhiêu", "hôm nay", "tin tức", "ai là", "sự kiện", "trường thcs", "là gì", "dịch", "nghĩa là gì"]
    need_web = any(word in cau_hoi_clean for word in keywords)

    combined_context = ""
    sources = []
    
    if need_web:
        with st.status("🔍 Hệ thống đang kết nối Internet diện rộng và tìm kiếm dữ liệu...", expanded=True) as status:
            web_links = search_the_web_ddg(user_input)
            if web_links:
                for link in web_links:
                    content = extract_web_content(link)
                    if content:
                        combined_context += f"\n--- Nguồn thông tin: {link} ---\n{content}\n"
                        sources.append(link)
                status.update(label=" Tìm kiếm dữ liệu mạng thành công!", state="complete", expanded=False)

    if combined_context:
        prompt = f"""
        [HỆ THỐNG]: Dưới đây là thông tin thực tế mới nhất từ Internet. Hãy đọc hiểu và trả lời cụ thể câu hỏi của người dùng bằng tiếng Việt. Tuyệt đối không được bịa đặt thông tin.
        DỮ LIỆU INTERNET: {combined_context}
        CÂU HỎI NGƯỜI DÙNG: {user_input}
        """
    else:
        prompt = user_input

    with st.chat_message("assistant", avatar="🔮"):
        message_placeholder = st.empty()
        try:
            # Gửi tin nhắn vào phiên chat sử dụng thư viện SDK thế hệ mới
            response = st.session_state.chat_session.send_message(
                prompt,
                config={"temperature": creativity}
            )
            ai_response = response.text.strip()
            
            if sources:
                ai_response += "\n\n---\n🌐 **Nguồn liên kết tra cứu:**\n" + "\n".join([f"- {src}" for src in sources])
            
            # Hiệu ứng chạy chữ chạy từng từ giống ChatGPT
            full_response = ""
            for chunk in ai_response.split(" "):
                full_response += chunk + " "
                time.sleep(0.03)
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            error_msg = f"❌ Máy chủ phản hồi chậm hoặc API bận: {e}. Bạn vui lòng nhấn Enter câu hỏi lại sau vài giây nhé!"
            message_placeholder.markdown(error_msg)
