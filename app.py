import warnings
import sys
import os
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from google import genai
import streamlit as st

warnings.filterwarnings("ignore")

#--- GIAO DIỆN ĐỒ HỌA WEB BẰNG STREAMLIT ---
st.set_page_config(page_title="AI Tra Cứu Toàn Năng", page_icon="🤖", layout="centered")
st.title("🤖 TRỢ LÝ AI TRA CỨU INTERNET")
st.caption("🚀 Phiên bản chatbot thông minh chạy trên máy chủ độc lập Streamlit Cloud v2026")

# Lấy API Key bảo mật từ cài đặt nâng cao
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.warning("⚠️ Hệ thống đang chờ cấu hình mã API Key ngầm. Vui lòng kiểm tra lại mục Secrets!")
    st.stop()

# Khởi tạo bộ não AI Client của Google
if "ai_client" not in st.session_state:
    try:
        st.session_state.ai_client = genai.Client(api_key=API_KEY)
        st.session_state.chat_session = st.session_state.ai_client.chats.create(model="gemini-3.6-flash")
    except Exception as e:
        st.error(f"Lỗi kết nối bộ não AI: {e}")

#--- CÁC HÀM XỬ LÝ TÌM KIẾM & CÀO WEB ---
def search_the_web_ddg(query, max_results=3):
    urls = []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            for r in results:
                urls.append(r['href'])
    except:
        pass
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
    except:
        pass
    return ""

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_input := st.chat_input("Nhập câu hỏi của bạn vào đây..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    cau_hoi_clean = user_input.lower().strip()
    keywords = ["ở đâu", "thành phố", "giá", "thời tiết", "mấy độ", "bao nhiêu", "hôm nay", "tin tức", "ai là", "sự kiện", "trường thcs", "là gì", "dịch", "nghĩa là gì"]
    need_web = any(word in cau_hoi_clean for word in keywords)

    combined_context = ""
    sources = []
    
    if need_web:
        with st.spinner("🔍 Đang tự động kết nối Internet diện rộng và tra cứu thông tin thực tế..."):
            web_links = search_the_web_ddg(user_input)
            if web_links:
                for link in web_links:
                    content = extract_web_content(link)
                    if content:
                        combined_context += f"\n--- Dữ liệu thực tế từ trang: {link} ---\n{content}\n"
                        sources.append(link)

    if combined_context:
        prompt = f"""
        [HỆ THỐNG]: Dưới đây là thông tin thực tế từ Internet. Hãy đọc hiểu và trả lời cụ thể, chính xác câu hỏi của người dùng bằng tiếng Việt.
        DỮ LIỆU INTERNET: {combined_context}
        CÂU HỎI NGƯỜI DÙNG: {user_input}
        """
    else:
        prompt = user_input

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("🤖 AI đang suy nghĩ câu trả lời..."):
            try:
                response = st.session_state.chat_session.send_message(prompt)
                ai_response = response.text.strip()
                if sources:
                    ai_response += "\n\n🌐 **Nguồn liên kết tra cứu:**\n" + "\n".join([f"- {src}" for src in sources])
                message_placeholder.markdown(ai_response)
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
            except Exception as e:
                error_msg = f"❌ Hệ thống bận: {e}"
                message_placeholder.markdown(error_msg)
