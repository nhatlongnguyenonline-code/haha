import warnings
import sys
import os
import requests
import time
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from groq import Groq  # Sử dụng thư viện chính thức của Groq ổn định vĩnh viễn
import streamlit as st

warnings.filterwarnings("ignore")

#--- 1. CẤU HÌNH GIAO DIỆN ĐỒ HỌA CAO CẤP ---
st.set_page_config(page_title="CyberChat Groq AI", page_icon="🔮", layout="centered")

# Nhúng mã CSS làm đẹp giao diện màu tối sang trọng
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #E2E8F0; }
    .stChatInput [data-testid="stChatInputCurrentContainer"] {
        border: 1px solid #3F83F8 !important; border-radius: 20px !important; background-color: #1A1F2C !important;
    }
    .main-title {
        font-size: 2.5rem; font-weight: 800; background: linear-gradient(90deg, #10B981, #3B82F6);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; margin-bottom: 0px;
    }
    .sub-title { text-align: center; color: #94A3B8; font-size: 0.95rem; margin-bottom: 2rem; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">🔮 CYBERCHAT GROQ BẤT TỬ</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Trợ lý AI siêu tốc sử dụng bộ não Llama thế hệ mới kết hợp tìm kiếm Internet</p>', unsafe_allow_html=True)

# Lấy API Key từ mục Secrets bảo mật của Streamlit Cloud
try:
    API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.warning("⚠️ Hệ thống đang chờ cấu hình mã GROQ_API_KEY ngầm trong mục Secrets!")
    st.stop()

# Khởi tạo bộ não AI Client của Groq
if "groq_client" not in st.session_state:
    try:
        st.session_state.groq_client = Groq(api_key=API_KEY)
    except Exception as e:
        st.error(f"Lỗi kết nối bộ não AI: {e}")

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
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            for element in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
                element.decompose()
            return ' '.join(soup.get_text().split())[:1500]
    except: pass
    return ""

if "messages" not in st.session_state:
    st.session_state.messages = []

#--- 3. THANH SIDEBAR QUẢN LÝ ---
with st.sidebar:
    st.markdown("### 🛠️ ĐIỀU KHIỂN")
    creativity = st.slider("🧠 Độ sáng tạo", min_value=0.1, max_value=1.0, value=0.3, step=0.1)
    st.markdown("---")
    if st.session_state.messages:
        chat_history_text = "NHẬT KÝ HỘI THOẠI\n" + "="*50 + "\n"
        for msg in st.session_state.messages:
            role_name = "Bạn" if msg["role"] == "user" else "AI"
            chat_history_text += f"\n[ {role_name} ]: {msg['content']}\n"
        st.download_button(label="📥 Tải lịch sử chat (.txt)", data=chat_history_text, file_name="Chat_History.txt", mime="text/plain", use_container_width=True)
        if st.button("🗑️ Xóa cuộc trò chuyện", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

# Hiển thị lịch sử bong bóng chat lên màn hình web
for message in st.session_state.messages:
    avatar_icon = "👤" if message["role"] == "user" else "🔮"
    with st.chat_message(message["role"], avatar=avatar_icon): 
        st.markdown(message["content"])

#--- 4. NHẬP LIỆU VÀ XỬ LÝ LOGIC ---
if user_input := st.chat_input("Nhập câu hỏi hoặc yêu cầu tra cứu internet vào đây..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"): 
        st.markdown(user_input)

    # Phân loại câu hỏi thông minh tự kích hoạt tra cứu internet diện rộng
    cau_hoi_clean = user_input.lower().strip()
    keywords = ["ở đâu", "thành phố", "giá", "thời tiết", "mấy độ", "bao nhiêu", "hôm nay", "tin tức", "ai là", "sự kiện", "trường thcs", "là gì", "dịch", "nghĩa là gì"]
    need_web = any(word in cau_hoi_clean for word in keywords)

    combined_context = ""
    sources = []
    
    if need_web:
        with st.status("🔍 Hệ thống đang kết nối Internet và tìm kiếm dữ liệu...", expanded=True) as status:
            web_links = search_the_web_ddg(user_input)
            if web_links:
                for link in web_links:
                    content = extract_web_content(link)
                    if content:
                        combined_context += f"\n--- Nguồn: {link} ---\n{content}\n"
                        sources.append(link)
                status.update(label=" Tìm kiếm dữ liệu mạng thành công!", state="complete", expanded=False)

    # Đóng gói cấu trúc gói tin gửi lên máy chủ Groq
    messages_payload = [
        {"role": "system", "content": "Bạn là trợ lý AI thông minh, luôn trả lời bằng tiếng Việt một cách cụ thể, logic, chính xác 100%. Nếu có dữ liệu internet được cung cấp, hãy tổng hợp dựa trên dữ liệu đó."}
    ]
    
    # Nạp toàn bộ lịch sử trò chuyện cũ
    for msg in st.session_state.messages[:-1]:
        messages_payload.append({"role": msg["role"], "content": msg["content"]})
    
    # Nạp câu hỏi hiện tại kết hợp ngữ cảnh mạng
    current_content = user_input
    if combined_context:
        current_content = f"DỮ LIỆU INTERNET THU THẬP ĐƯỢC:\n{combined_context}\n\nCÂU HỎI NGƯỜI DÙNG: {user_input}"
    messages_payload.append({"role": "user", "content": current_content})

    with st.chat_message("assistant", avatar="🔮"):
        message_placeholder = st.empty()
        
        # Danh sách các mô hình hoạt động tốt nhất hiện tại của Groq để quét dự phòng chống lỗi 404
        available_models = [
            "llama-3.3-70b-specdec",
            "llama-3.2-11b-vision-preview",
            "gemma2-9b-it",
            "llama3-8b-8192"
        ]
        
        ai_response = ""
        # Thử chạy từng mô hình, nếu lỗi tự nhảy sang mô hình tiếp theo
        for model_name in available_models:
            try:
                completion = st.session_state.groq_client.chat.completions.create(
                    model=model_name,
                    messages=messages_payload,
                    temperature=creativity,
                )
                ai_response = completion.choices.message.content.strip()
                break # Nếu thành công thì ngắt vòng lặp ngay
            except Exception as model_error:
                continue # Nếu mô hình bị 404 hoặc bận, tự động nhảy sang mô hình tiếp theo trong danh sách
                
        if ai_response:
            # Gắn link nguồn bài báo vào cuối văn bản trả về nếu có tìm kiếm mạng
            if sources:
                ai_response += "\n\n---\n🌐 **Nguồn liên kết tra cứu:**\n" + "\n".join([f"- {src}" for src in sources])
            
            # Hiệu ứng chạy chữ từng từ mượt mà của ChatGPT
            full_response = ""
            for chunk in ai_response.split(" "):
                full_response += chunk + " "
                time.sleep(0.02)
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        else:
            message_placeholder.markdown("❌ Máy chủ Groq hiện tại đang bảo trì tất cả các dòng mô hình miễn phí hoặc API Key bị cấu hình sai. Bạn vui lòng kiểm tra lại Key trong mục Secrets nhé!")
