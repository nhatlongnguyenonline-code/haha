import warnings
import sys
import os
import requests
import time
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import streamlit as st

warnings.filterwarnings("ignore")

#--- 1. CẤU HÌNH GIAO DIỆN ĐỒ HỌA CAO CẤP ---
st.set_page_config(page_title="CyberChat AI", page_icon="🔮", layout="centered")

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

st.markdown('<h1 class="main-title">🔮 CYBERCHAT BẤT TỬ</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Trợ lý AI siêu tốc kết hợp tìm kiếm Internet diện rộng (Không cần API Key)</p>', unsafe_allow_html=True)

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

def call_free_ai_brain(text_prompt):
    """Gọi bộ não AI thông minh thông qua các cổng máy chủ mở dùng chung (Không cần điền Key)."""
    # Sử dụng hệ thống endpoint mở rộng của các dòng mô hình Llama-3/Qwen lớn
    url = "https://chub.ai"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": "meta-llama/llama-3-8b-instruct:free",
        "messages": [{"role": "user", "content": text_prompt}],
        "temperature": 0.3
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=12)
        if response.status_code == 200:
            return response.json()['choices']['message']['content']
    except:
        pass
        
    # Máy chủ dự phòng cấp 2 nếu cổng 1 nghẽn mạng
    try:
        fallback_url = "https://chatsandbox.com"
        fb_payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": text_prompt}]
        }
        res = requests.post(fallback_url, json=fb_payload, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()['choices']['message']['content']
    except:
        pass
        
    return "Chào bạn! Hiện tại kết nối mạng xử lý ngôn ngữ đang phản hồi chậm, bạn hãy thử gõ lại câu hỏi nhé!"

if "messages" not in st.session_state:
    st.session_state.messages = []

#--- 3. THANH SIDEBAR QUẢN LÝ ---
with st.sidebar:
    st.markdown("### 🛠️ ĐIỀU KHIỂN")
    st.caption("Ứng dụng đang vận hành trên máy chủ đám mây độc lập an toàn.")
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
    keywords = ["ở đâu", "thành phố", "giá", "thời tiết", "mấy độ", "bao nhiêu", "hôm nay", "tin tức", "ai là", "sự kiện", "trường thcs", "là gì", "dịch", "nghĩa là gì", "ko", "không"]
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

    # Tạo prompt chất lượng cao truyền vào bộ não AI
    if combined_context:
        prompt = f"""
        Bạn là một trợ lý AI chủ động và cực kỳ thông minh. Nhiệm vụ của bạn là đọc thông tin tìm kiếm từ Internet dưới đây để xử lý và trả lời cụ thể câu hỏi của người dùng bằng tiếng Việt.
        Yêu cầu: Trả lời tự nhiên, chính xác theo dữ liệu, không bê nguyên văn chữ thô.
        
        DỮ LIỆU INTERNET THU THẬP ĐƯỢC:
        {combined_context}

        CÂU HỎI NGƯỜI DÙNG: {user_input}
        """
    else:
        prompt = f"Bạn là một trợ lý AI thân thiện. Hãy trả lời câu hỏi sau một cách cụ thể, chính xác bằng tiếng Việt: {user_input}"

    with st.chat_message("assistant", avatar="🔮"):
        message_placeholder = st.empty()
        
        # Gọi bộ não AI xử lý không cần điền key
        ai_response = call_free_ai_brain(prompt)
        
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
