import warnings
import sys
import os
import requests
import time
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from google import genai
from google.genai import types  
from PIL import Image  
import streamlit as st

warnings.filterwarnings("ignore")

#--- 1. CẤU HÌNH GIAO DIỆN PREMIUM LIGHT MODE KHÓA CHÍNH GIỮA ---
st.set_page_config(page_title="Trợ Lý AI Thông Minh", page_icon="🤖", layout="centered")

st.markdown("""
    <style>
    /* Nền tổng thể màu trắng sạch sẽ, chữ màu đen đậm rõ nét */
    .stApp {
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    h1, h2, h3, p, span, label, .stMarkdown {
        color: #1F2937 !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    [data-testid="stSidebar"] * {
        color: #1F2937 !important;
    }

    /* KHÓA Ô GÕ CÂU HỎI CHÍNH GIỮA MÀN HÌNH */
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
        box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.15) !important;
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

    /* KHUNG TIN NHẮN CHAT BO GÓC MỀM MẠI DỄ NHÌN */
    [data-testid="stChatMessage"] {
        border-radius: 16px !important;
        margin-bottom: 16px !important;
        padding: 16px 20px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
    }
    [data-testid="stChatMessageAssistant"] {
        background-color: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
    }
    [data-testid="stChatMessageUser"] {
        background-color: #F0F6FF !important;
        border: 1px solid #DBEAFE !important;
    }
    
    /* Làm đẹp vòng tròn bọc quanh biểu tượng Emoji */
    [data-testid="stChatMessageAvatar"] {
        border-radius: 50% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 1.2rem !important;
    }

    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E3A8A !important;
        text-align: center;
        margin-top: 1.5rem;
        margin-bottom: 4px;
    }
    .sub-title {
        text-align: center;
        color: #64748B !important;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">🤖 TRỢ LÝ AI TOÀN NĂNG</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Hệ thống đọc hiểu kiến thức, phân tích hình ảnh và tra cứu Internet</p>', unsafe_allow_html=True)

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.warning("⚠️ Hệ thống đang chờ cấu hình mã GEMINI_API_KEY ngầm trong mục Secrets!")
    st.stop()

if "ai_client" not in st.session_state:
    try:
        st.session_state.ai_client = genai.Client(api_key=API_KEY)
        st.session_state.chat_session = st.session_state.ai_client.chats.create(model="gemini-3.6-flash")
    except Exception as e:
        st.error(f"Lỗi bộ não AI: {e}")

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
            for element in soup(["script", "style", "nav", "footer", "header", "aside", "form"]): element.decompose()
            return ' '.join(soup.get_text().split())[:1500]
    except: pass
    return ""

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.markdown("### ⚙️ CÀI ĐẶT CHATBOT")
    creativity = st.slider("🧠 Độ nhạy bén / Sáng tạo", min_value=0.1, max_value=1.0, value=0.3, step=0.1)
    st.markdown("---")
    st.markdown("### 📸 PHÂN TÍCH HÌNH ẢNH")
    uploaded_file = st.file_uploader("Tải ảnh lên tại đây...", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        st.image(Image.open(uploaded_file), caption="Ảnh đã chọn", use_container_width=True)
        st.info("💡 Hãy gõ câu hỏi vào ô chat để yêu cầu AI phân tích ảnh này.")
    st.markdown("---")
    st.markdown("### 📂 NHẬT KÝ")
    if st.session_state.messages:
        chat_history_text = "NHẬT KÝ HỘI THOẠI AI\n" + "="*50 + "\n"
        for msg in st.session_state.messages: chat_history_text += f"\n[ {msg['role'].upper()} ]: {msg['content']}\n"
        st.download_button(label="📥 Tải lịch sử chat (.txt)", data=chat_history_text, file_name="AI_Chat_History.txt", mime="text/plain", use_container_width=True)
        if st.button("🗑️ Xóa cuộc trò chuyện", use_container_width=True):
            st.session_state.messages = []
            st.session_state.chat_session = st.session_state.ai_client.chats.create(model="gemini-3.6-flash")
            st.rerun()

# Đổi sang emoji Phượng hoàng lửa tái sinh (🐦‍🔥) cho tin nhắn cũ
for message in st.session_state.messages:
    avt_emoji = "👤" if message["role"] == "user" else "🐦‍🔥"
    with st.chat_message(message["role"], avatar=avt_emoji): 
        st.markdown(message["content"])

# Khung nhận câu hỏi mới
if user_input := st.chat_input("Nhập câu hỏi hoặc yêu cầu phân tích ảnh tại đây..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"): 
        st.markdown(user_input)

    cau_hoi_clean = user_input.lower().strip()
    keywords = ["ở đâu", "thành phố", "giá", "thời tiết", "mấy độ", "bao nhiêu", "hôm nay", "tin tức", "ai là", "sự kiện", "trường thcs", "là gì", "dịch", "nghĩa là gì"]
    need_web = any(word in cau_hoi_clean for word in keywords)

    combined_context = ""
    sources = []
    
    if need_web and not uploaded_file:
        with st.status("🔍 Đang tìm kiếm thông tin thực tế...", expanded=False) as status:
            web_links = search_the_web_ddg(user_input)
            if web_links:
                for link in web_links:
                    content = extract_web_content(link)
                    if content:
                        combined_context += f"\n--- Nguồn: {link} ---\n{content}\n"
                        sources.append(link)
                status.update(label=" Đọc dữ liệu thành công!", state="complete")

    prompt_payload = f"[HỆ THỐNG]: Dựa trên Internet: {combined_context}\nCÂU HỎI: {user_input}" if combined_context else user_input

    # Đổi sang emoji Phượng hoàng lửa tái sinh (🐦‍🔥) cho câu trả lời mới tinh
    with st.chat_message("assistant", avatar="🐦‍🔥"):
        message_placeholder = st.empty()
        with st.spinner("🤖 AI đang suy nghĩ..."):
            try:
                if uploaded_file:
                    response = st.session_state.ai_client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=[Image.open(uploaded_file), prompt_payload],
                        config=types.GenerateContentConfig(temperature=creativity)
                    )
                else:
                    response = st.session_state.chat_session.send_message(prompt_payload, config={"temperature": creativity})
                
                ai_response = response.text.strip()
                if sources: 
                    ai_response += "\n\n---\n🌐 **Nguồn:**\n" + "\n".join([f"- {src}" for src in sources])
                
                message_placeholder.markdown(ai_response)
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                st.rerun()
            except Exception as e:
                message_placeholder.markdown(f"❌ Hệ thống bận: {e}. Vui lòng thử lại sau vài giây.")
