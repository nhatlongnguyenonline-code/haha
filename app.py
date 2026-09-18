import warnings
import sys
import os
import requests
import time
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from google import genai
import streamlit as st

warnings.filterwarnings("ignore")

#--- 1. CẤU HÌNH GIAO DIỆN ĐỒ HỌA DỄ NHÌN (MODERN SLATE) ---
st.set_page_config(page_title="Trợ Lý AI Thông Minh", page_icon="🤖", layout="centered")

# Nhúng mã CSS tinh chỉnh màu sắc dịu mắt, làm nổi bật khung gõ câu hỏi
st.markdown("""
    <style>
    /* Màu nền tổng thể dịu mắt, chữ sáng rõ ràng */
    .stApp {
        background-color: #111827;
        color: #F3F4F6;
    }
    
    /* LÀM NỔI BẬT KHUNG VIẾT CÂU HỎI */
    .stChatInput {
        position: fixed;
        bottom: 20px;
        left: 0;
        right: 0;
        z-index: 999;
    }
    .stChatInput [data-testid="stChatInputCurrentContainer"] {
        border: 2px solid #3B82F6 !important; /* Viền xanh dương đậm nổi bật */
        border-radius: 16px !important;
        background-color: #1F2937 !important; /* Nền ô gõ tối vừa phải để tương phản với chữ */
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25) !important; /* Đổ bóng phát sáng nhẹ để dễ nhận biết */
    }
    .stChatInput textarea {
        color: #FFFFFF !important; /* Chữ bạn gõ sẽ có màu trắng tinh cực rõ */
        font-size: 1rem !important;
    }

    /* TIÊU ĐỀ RÕ RÀNG */
    .main-title {
        font-size: 2.3rem;
        font-weight: 700;
        color: #3B82F6;
        text-align: center;
        margin-top: 1rem;
        margin-bottom: 5px;
    }
    .sub-title {
        text-align: center;
        color: #9CA3AF;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">🤖 TRỢ LÝ AI TOÀN NĂNG</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Hệ thống đọc hiểu kiến thức và tra cứu thông tin Internet diện rộng</p>', unsafe_allow_html=True)

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

#--- 3. THANH SIDEBAR BÊN TRÁI GỌN GÀNG ---
with st.sidebar:
    st.markdown("### ⚙️ CÀI ĐẶT CHATBOT")
    creativity = st.slider("🧠 Độ nhạy bén / Sáng tạo", min_value=0.1, max_value=1.0, value=0.3, step=0.1)
    st.markdown("---")
    st.markdown("### 📂 NHẬT KÝ")
    if st.session_state.messages:
        chat_history_text = "NHẬT KÝ HỘI THOẠI AI\n" + "="*50 + "\n"
        for msg in st.session_state.messages:
            role_name = "Bạn" if msg["role"] == "user" else "AI Trợ Lý"
            chat_history_text += f"\n[ {role_name} ]: {msg['content']}\n"
        st.download_button(label="📥 Tải lịch sử chat (.txt)", data=chat_history_text, file_name="AI_Chat_History.txt", mime="text/plain", use_container_width=True)
        if st.button("🗑️ Xóa cuộc trò chuyện", use_container_width=True):
            st.session_state.messages = []
            st.session_state.chat_session = st.session_state.ai_client.chats.create(model="gemini-3.6-flash")
            st.rerun()
    else:
        st.caption("Chưa có đoạn chat nào để tải về.")

# Hiển thị lịch sử bong bóng chat cũ lên màn hình web
for message in st.session_state.messages:
    avatar_icon = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar_icon): 
        st.markdown(message["content"])

#--- 4. KHUNG NHẬP LIỆU VÀ XỬ LÝ LOGIC ---
# Ô nhập liệu có gợi ý chữ to rõ ràng ở dưới cùng màn hình
if user_input := st.chat_input("HÃY GÕ CÂU HỎI CỦA BẠN VÀO ĐÂY VÀ ẤN ENTER..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"): 
        st.markdown(user_input)

    cau_hoi_clean = user_input.lower().strip()
    keywords = ["ở đâu", "thành phố", "giá", "thời tiết", "mấy độ", "bao nhiêu", "hôm nay", "tin tức", "ai là", "sự kiện", "trường thcs", "là gì", "dịch", "nghĩa là gì"]
    need_web = any(word in cau_hoi_clean for word in keywords)

    combined_context = ""
    sources = []
    
    if need_web:
        with st.status("🔍 Đang kết nối mạng và tìm kiếm thông tin thực tế...", expanded=False) as status:
            web_links = search_the_web_ddg(user_input)
            if web_links:
                for link in web_links:
                    content = extract_web_content(link)
                    if content:
                        combined_context += f"\n--- Nguồn thông tin: {link} ---\n{content}\n"
                        sources.append(link)
                status.update(label=" Đọc dữ liệu mạng thành công!", state="complete")

    if combined_context:
        prompt = f"""
        [HỆ THỐNG]: Dưới đây là thông tin thực tế mới nhất từ Internet. Hãy đọc hiểu và trả lời cụ thể câu hỏi của người dùng bằng tiếng Việt. Tuyệt đối không được bịa đặt thông tin.
        DỮ LIỆU INTERNET: {combined_context}
        CÂU HỎI NGƯỜI DÙNG: {user_input}
        """
    else:
        prompt = user_input

    with st.chat_message("assistant", avatar="🤖"):
        message_placeholder = st.empty()
        try:
            response = st.session_state.chat_session.send_message(
                prompt,
                config={"temperature": creativity}
            )
            ai_response = response.text.strip()
            
            if sources:
                ai_response += "\n\n---\n🌐 **Nguồn liên kết tra cứu:**\n" + "\n".join([f"- {src}" for src in sources])
            
            # Hiệu ứng gõ chữ từng từ mượt mà trực quan
            full_response = ""
            for chunk in ai_response.split(" "):
                full_response += chunk + " "
                time.sleep(0.02)
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            error_msg = f"❌ Hệ thống bận: {e}. Bạn vui lòng nhấn Enter câu hỏi lại sau vài giây nhé!"
            message_placeholder.markdown(error_msg)
