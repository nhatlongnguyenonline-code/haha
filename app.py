import warnings
import sys
import os
import requests
import time
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import streamlit as st

warnings.filterwarnings("ignore")

#--- 1. CẤU HÌNH GIAO DIỆN ĐỒ HỌA CAO CẤP (CYBERCHAT) ---
st.set_page_config(page_title="CyberChat Open AI", page_icon="🔮", layout="centered")

# Nhúng mã CSS làm đẹp bong bóng chat và giao diện màu tối sang trọng
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #E2E8F0; }
    .stChatInput [data-testid="stChatInputCurrentContainer"] {
        border: 1px solid #3F83F8 !important; border-radius: 20px !important; background-color: #1A1F2C !important;
    }
    .main-title {
        font-size: 2.5rem; font-weight: 800; background: linear-gradient(90deg, #EC4899, #8B5CF6);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; margin-bottom: 0px;
    }
    .sub-title { text-align: center; color: #94A3B8; font-size: 0.95rem; margin-bottom: 2rem; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">🔮 CYBERCHAT OPEN AI</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Trợ lý AI siêu tốc sử dụng bộ não Llama-3 kết hợp tìm kiếm Internet diện rộng</p>', unsafe_allow_html=True)

#--- 2. CÁC HÀM XỬ LÝ TÌM KIẾM & CÀO WEB DIỆN RỘNG ---
def search_the_web_ddg(query, max_results=3):
    """Tìm kiếm từ khóa trên toàn bộ internet thông qua DuckDuckGo."""
    urls = []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            for r in results: urls.append(r['href'])
    except: pass
    return urls

def extract_web_content(url):
    """Truy cập vào URL bài viết và bóc tách lấy dữ liệu chữ sạch."""
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

def call_huggingface_llama(text_prompt):
    """Gọi bộ não AI Llama-3 thông minh qua cổng API mở công cộng của Hugging Face."""
    url = "https://huggingface.co"
    headers = {"Content-Type": "application/json"}
    payload = {
        "inputs": f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{text_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
        "parameters": {"max_new_tokens": 512, "temperature": 0.3}
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            res_json = response.json()
            if isinstance(res_json, list) and 'generated_text' in res_json:
                raw_text = res_json['generated_text']
                if "assistant" in raw_text:
                    return raw_text.split("assistant")[-1].strip()
                return raw_text
    except:
        pass
    return None

if "messages" not in st.session_state:
    st.session_state.messages = []

#--- 3. THANH SIDEBAR QUẢN LÝ ỨNG DỤNG ---
with st.sidebar:
    st.markdown("### 🛠️ ĐIỀU KHIỂN CHATBOT")
    st.caption("Ứng dụng đang vận hành ổn định trên hệ thống máy chủ mã nguồn mở vĩnh viễn.")
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

    # Phân loại câu hỏi tự động kích hoạt tính năng kết nối cào mạng Internet
    cau_hoi_clean = user_input.lower().strip()
    keywords = ["ở đâu", "thành phố", "giá", "thời tiết", "mấy độ", "bao nhiêu", "hôm nay", "tin tức", "ai là", "sự kiện", "trường thcs", "là gì", "dịch", "nghĩa là gì", "ko", "không"]
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

    # Đóng gói Prompt ép bộ não AI xử lý dựa trên thông tin Internet cào về
    if combined_context:
        prompt = f"""
        Nhiệm vụ của bạn là đọc hiểu thông tin tìm kiếm từ Internet dưới đây và trả lời cụ thể câu hỏi của người dùng bằng tiếng Việt.
        Yêu cầu: Trả lời hoàn toàn bằng tiếng Việt, ngắn gọn, cụ thể, đi thẳng vào trọng tâm câu hỏi, tuyệt đối không được tự ý bịa đặt thông tin sai sự thật.
        
        DỮ LIỆU INTERNET THU THẬP ĐƯỢC: 
        {combined_context}
        
        CÂU HỎI HIỆN TẠI CỦA NGƯỜI DÙNG: {user_input}
        """
    else:
        prompt = f"Bạn là trợ lý AI thông minh am hiểu kiến thức. Hãy trả lời câu hỏi sau một cách cụ thể, chính xác bằng tiếng Việt: {user_input}"

    # AI sinh câu trả lời cụ thể dạng hiệu ứng chạy chữ mượt mà
    with st.chat_message("assistant", avatar="🔮"):
        message_placeholder = st.empty()
        
        # Gọi bộ não AI xử lý qua cổng mở công cộng
        ai_response = call_huggingface_llama(prompt)
        
        if ai_response:
            # Nối thêm nguồn link URL uy tín vào giao diện nếu có tra mạng
            if sources:
                ai_response += "\n\n---\n🌐 **Nguồn liên kết tra cứu:**\n" + "\n".join([f"- {src}" for src in sources])
            
            # Tạo hiệu ứng chạy chữ chạy từng từ giống ChatGPT thực thụ
            full_response = ""
            for chunk in ai_response.split(" "):
                full_response += chunk + " "
                time.sleep(0.03)  # Tốc độ gõ chữ tối ưu cực kỳ mượt mà
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        else:
            message_placeholder.markdown("❌ Cổng mạng Hugging Face hiện tại đang bận xử lý. Bạn vui lòng bấm nhấn Enter câu hỏi lại sau vài giây nhé!")
