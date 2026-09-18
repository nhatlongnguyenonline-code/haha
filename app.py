import warnings
import sys
import os
import requests
import time
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from google import genai
from google.genai import types  # Thư viện hỗ trợ nạp dữ liệu ảnh thô
from PIL import Image  # Thư viện xử lý hình ảnh của Python
import streamlit as st

warnings.filterwarnings("ignore")

#--- 1. CẤU HÌNH GIAO DIỆN PREMIUM LIGHT MODE HỖ TRỢ GỬI ẢNH ---
st.set_page_config(page_title="Trợ Lý AI Thông Minh", page_icon="🤖", layout="centered")

# Nhúng mã CSS khóa chặt ô gõ câu hỏi nhỏ gọn ở chính giữa màn hình và làm đẹp giao diện
st.markdown("""
    <style>
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

    /* ĐỊNH DẠNG KHUNG VIẾT CÂU HỎI LUÔN NẰM CỐ ĐỊNH CHÍNH GIỮA MÀN HÌNH */
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

    /* ĐỊNH DẠNG KHUNG TIN NHẮN CHAT BONG BÓNG */
    [data-testid="stChatMessage"] {
        background-color: #F1F5F9 !important;
        border-radius: 16px !important;
        margin-bottom: 12px !important;
        padding: 12px 16px !important;
    }
    [data-testid="stChatMessageUser"] {
        background-color: #EFF6FF !important;
        border: 1px solid #BFDBFE !important;
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
    
    # 📸 KHUNG TẢI ẢNH ĐƯỢC ĐƯA VÀO THANH SIDEBAR ĐỂ KHÔNG BỊ PHÌNH MÀN HÌNH CHÍNH
    st.markdown("### 📸 PHÂN TÍCH HÌNH ẢNH")
    uploaded_file = st.file_uploader("Tải ảnh lên tại đây (.png, .jpg, .jpeg)...", type=["png", "jpg", "jpeg"])
    
    if uploaded_file:
        image_preview = Image.open(uploaded_file)
        st.image(image_preview, caption="Ảnh bạn đã chọn", use_container_width=True)
        st.info("💡 Bây giờ bạn hãy gõ câu hỏi vào ô chat chính để yêu cầu AI phân tích bức ảnh này nhé!")

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

# Hiển thị lịch sử bong bóng chat cũ lên màn hình web
for message in st.session_state.messages:
    avatar_icon = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar_icon): 
        st.markdown(message["content"])

#--- 4. KHUNG NHẬP LIỆU VÀ XỬ LÝ LOGIC ---
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
        prompt_payload = f"""
        [HỆ THỐNG]: Dưới đây là thông tin thực tế từ Internet. Hãy đọc hiểu và trả lời cụ thể câu hỏi của người dùng bằng tiếng Việt.
        DỮ LIỆU INTERNET: {combined_context}
        CÂU HỎI NGƯỜI DÙNG: {user_input}
        """
    else:
        prompt_payload = user_input

    with st.chat_message("assistant", avatar="🤖"):
        message_placeholder = st.empty()
        with st.spinner("🤖 AI đang suy nghĩ câu trả lời..."):
            try:
                if uploaded_file:
                    raw_image = Image.open(uploaded_file)
                    response = st.session_state.ai_client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=[raw_image, prompt_payload],
                        config=types.GenerateContentConfig(temperature=creativity)
                    )
                else:
                    response = st.session_state.chat_session.send_message(
                        prompt_payload,
                        config={"temperature": creativity}
                    )
                
                ai_response = response.text.strip()
                if sources:
                    ai_response += "\n\n---\n🌐 **Nguồn liên kết tra cứu:**\n" + "\n".join([f"- {src}" for src in sources])
                
                full_response = ""
                for chunk in ai_response.split(" "):
                    full_response += chunk + " "
                    time.sleep(0.02)
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                error_msg = f"❌ Hệ thống phản hồi chậm hoặc hết hạn mức API: {e}. Bạn vui lòng thử lại sau vài giây nhé!"
                message_placeholder.markdown(error_msg)
