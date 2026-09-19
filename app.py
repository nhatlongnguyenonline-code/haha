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

#--- CẤU HÌNH GIAO DIỆN PREMIUM LIGHT MODE KHÓA CHÍNH GIỮA ---
st.set_page_config(page_title="Trợ Lý AI Thông Minh", page_icon="🐦‍🔥", layout="centered")

st.markdown("""
    <style>
    /* 🎨 NGHỆ THUẬT PHOENIX: TRANG TRÍ 5 SỌC GRADIENT CHẠY DỌC ĐỐI XỨNG HAI BÊN */
    .stApp::before {
        content: "" !important;
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 25px !important;
        height: 100vh !important;
        background: linear-gradient(180deg, #EF4444, #F97316, #FBBF24, #3B82F6, #8B5CF6) !important;
        z-index: 9999 !important;
        box-shadow: 3px 0 15px rgba(239, 68, 68, 0.2) !important;
    }
    .stApp::after {
        content: "" !important;
        position: fixed !important;
        top: 0 !important;
        right: 0 !important;
        width: 25px !important;
        height: 100vh !important;
        background: linear-gradient(180deg, #8B5CF6, #3B82F6, #FBBF24, #F97316, #EF4444) !important;
        z-index: 9999 !important;
        box-shadow: -3px 0 15px rgba(59, 130, 246, 0.15) !important;
    }

    /* 🎨 NGHỆ THUẬT PHOENIX: TRANG TRÍ CHỖ TRỐNG SIDEBAR MÀU SẮC NHẸ NHÀNG */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F8FAFC 0%, #FFF7ED 100%) !important;
        border-right: 1px solid #FED7AA !important;
    }
    
    /* Tô điểm nhẹ nhàng cho khung bong bóng hội thoại chat */
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

    /* KHÓA CHẶT Ô GÕ CÂU HỎI NHỎ GỌN Ở CHÍNH GIỮA MÀN HÌNH */
    .stChatInput {
        position: fixed !important; bottom: 30px !important; left: 50% !important;
        transform: translateX(-50%) !important; z-index: 999 !important;
        width: 100% !important; max-width: 550px !important;
        display: flex !important; justify-content: center !important;
    }
    .stChatInput [data-testid="stChatInputCurrentContainer"] {
        width: 100% !important; border: 2px solid #3B82F6 !important;
        border-radius: 24px !important; background-color: #F8FAFC !important;
        padding: 4px 10px !important;
        box-shadow: 0 10px 30px -5px rgba(59, 130, 246, 0.2) !important;
    }
    .stChatInput textarea { color: #1F2937 !important; font-size: 0.95rem !important; font-weight: 500 !important; }
    .stChatInput button { background-color: #3B82F6 !important; color: white !important; border-radius: 50% !important; }
    
    /* Ẩn icon mặc định thô sơ hệ thống */
    [data-testid="stHeaderHeading"] svg, [data-testid="stHeaderHeading"] div, [data-testid="stElementContainer"] h1 svg {
        display: none !important;
    }
    [data-testid="stChatMessageAvatar"] { border-radius: 50% !important; display: flex !important; align-items: center !important; justify-content: center !important; font-size: 1.2rem !important; }

    /* TIÊU ĐỀ CHUYỂN MÀU GRADIENT PHOENIX */
    .premium-title-container { display: flex; align-items: center; justify-content: center; gap: 12px; margin-top: 1.5rem; margin-bottom: 4px; }
    .premium-logo { font-size: 2.5rem; }
    .premium-text { font-size: 2.3rem; font-weight: 800; letter-spacing: -0.5px; background: linear-gradient(90deg, #EF4444, #3B82F6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .sub-title { text-align: center; color: #64748B !important; font-size: 0.95rem; margin-bottom: 1.5rem; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="premium-title-container"><span class="premium-logo">🐦‍🔥</span><span class="premium-text">TRỢ LÝ AI TOÀN NĂNG</span></div>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Hệ thống đọc hiểu kiến thức, phân tích hình ảnh và tra cứu Internet</p>', unsafe_allow_html=True)

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.warning("⚠️ Hệ thống đang chờ cấu hình mã GEMINI_API_KEY ngầm trong mục Secrets!")
    st.stop()

if "ai_client" not in st.session_state:
    try:
        st.session_state.ai_client = genai.Client(api_key=API_KEY)
        st.session_state.chat_session = st.session_state.ai_client.chats.create(model="gemini-2.5-flash")
    except Exception as e:
        st.error(f"Lỗi khởi tạo bộ não AI: {e}")
def search_the_web_ddg(query, max_results=3):
    """Khôi phục: Tự động tra cứu tìm kiếm 3 nguồn web tham khảo phong phú như ban đầu."""
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
            st.session_state.chat_session = st.session_state.ai_client.chats.create(model="gemini-2.5-flash")
            st.rerun()

# Hiển thị lại toàn bộ lịch sử các tin nhắn cũ từ session_state
for message in st.session_state.messages:
    avt_emoji = "👤" if message["role"] == "user" else "🐦‍🔥"
    with st.chat_message(message["role"], avatar=avt_emoji): 
        st.markdown(message["content"])

# Nhận tin nhắn mới từ người dùng
if user_input := st.chat_input("Nhập câu hỏi hoặc yêu cầu phân tích ảnh tại đây..."):
    # Lưu và hiển thị ngay lập tức câu hỏi của User
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"): 
        st.markdown(user_input)

    cau_hoi_clean = user_input.lower().strip()
    keywords = ["ở đâu", "thành phố", "giá", "thời tiết", "mấy độ", "bao nhiêu", "hôm nay", "tin tức", "ai là", "sự kiện", "trường thcs", "là gì", "dịch", "nghĩa là gì"]
    need_web = any(word in cau_hoi_clean for word in keywords)

    combined_context = ""
    sources = []
    
    # Tra cứu Internet nếu phát hiện từ khóa cần thiết
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

    prompt_payload = f"[HỆ THỐNG]: Dựa trên dữ liệu thực tế Internet: {combined_context}\nCÂU HỎI NGƯỜI DÙNG: {user_input}" if combined_context else user_input

    # Tạo khung bong bóng hội thoại cho AI và xử lý sinh nội dung
    with st.chat_message("assistant", avatar="🐦‍🔥"):
        message_placeholder = st.empty()
        with st.spinner("🤖 AI đang suy nghĩ..."):
            try:
                if uploaded_file:
                    response = st.session_state.ai_client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[Image.open(uploaded_file), prompt_payload],
                        config=types.GenerateContentConfig(temperature=creativity)
                    )
                else:
                    response = st.session_state.chat_session.send_message(prompt_payload, config={"temperature": creativity})
                
                ai_response = response.text.strip()
                if sources: 
                    ai_response += "\n\n---\n🌐 **Nguồn liên kết tham cứu:**\n" + "\n".join([f"- {src}" for src in sources])
                
                # In trực tiếp kết quả ra màn hình thông qua placeholder
                message_placeholder.markdown(ai_response)
                
                # Lưu câu trả lời của AI vào bộ nhớ lịch sử
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
            except Exception as e:
                message_placeholder.markdown(f"❌ Hệ thống bận: {e}. Bạn vui lòng thử gõ lại câu hỏi nhé!")
