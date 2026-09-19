import warnings
import sys
import os
import requests
import time
import numpy as np  # Thêm numpy để tính toán khoảng cách ngữ nghĩa giữa các câu hỏi
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
        st.session_state.chat_session = st.session_state.ai_client.chats.create(model="gemini-3.6-flash")
    except Exception as e:
        st.error(f"Lỗi khởi tạo bộ não AI: {e}")

# Hàm dùng mô hình Google để biến đổi câu văn thành Vector dạng toán học để so sánh ý nghĩa
def get_embedding(text):
    try:
        response = st.session_state.ai_client.models.embed_content(
            model="text-embedding-004",
            contents=text
        )
        return response.embeddings.values
    except:
        return None
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

# Khởi tạo kho lưu trữ Semantic Cache rỗng trong Session ngầm
if "semantic_cache" not in st.session_state:
    st.session_state.semantic_cache = []

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

    # --- ĐỘNG CƠ KIỂM TRA SEMANTIC CACHE ---
    cache_hit = False
    cached_answer = ""
    
    if not uploaded_file:
        current_embedding = get_embedding(user_input)
        if current_embedding is not None:
            best_score = -1
            best_match = None
            
            for item in st.session_state.semantic_cache:
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

    # Nếu trùng ngữ nghĩa -> Trả kết quả ngay lập tức (0.01 giây)
    if cache_hit:
        with st.chat_message("assistant", avatar="🐦‍🔥"):
            st.markdown(cached_answer)
            st.caption("⚡ *Phản hồi ngay lập tức từ bộ nhớ đệm thông minh (Semantic Cache hit)*")
            st.session_state.messages.append({"role": "assistant", "content": cached_answer})
    
    # Nếu chưa có trong cache -> Chạy luồng xử lý chính
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

        # 🟢 --- CẬP NHẬT PROMPT PAYLOAD MỀM DẺO MỚI (TỐI ƯU TẬN GỐC TƯ DUY AI) ---
        if combined_context:
            prompt_payload = (
                f"Bạn là Trợ lý AI Toàn năng. Dưới đây là thông tin cập nhật từ Internet để tham khảo (nếu có liên quan):\n"
                f"{combined_context}\n\n"
                f"Yêu cầu: Hãy trả lời câu hỏi sau của người dùng một cách chi tiết và mở rộng nhất. "
                f"Nếu thông tin Internet trên chưa đủ hoặc không liên quan, hãy chủ động sử dụng toàn bộ kiến thức nội tại của bạn để giải thích đầy đủ cho người dùng.\n"
                f"CÂU HỎI: {user_input}"
            )
        else:
            prompt_payload = user_input

        with st.chat_message("assistant", avatar="🐦‍🔥"):
            try:
                def response_generator():
                    if uploaded_file:
                        response_stream = st.session_state.ai_client.models.generate_content_stream(
                            model='gemini-3.6-flash',
                            contents=[Image.open(uploaded_file), prompt_payload],
                            config=types.GenerateContentConfig(temperature=creativity)
                        )
                    else:
                        response_stream = st.session_state.chat_session.send_message_stream(
                            prompt_payload, 
                            config={"temperature": creativity}
                        )
                    for chunk in response_stream:
                        yield chunk.text

                ai_response = st.write_stream(response_generator())
                
                if sources:
                    source_text = "\n\n---\n🌐 **Nguồn liên kết tham cứu:**\n" + "\n".join([f"- {src}" for src in sources])
                    st.markdown(source_text)
                    ai_response += source_text
                
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
                # Lưu vào bộ đệm cache câu trả lời chất lượng vừa tạo
                if not uploaded_file:
                    new_embedding = get_embedding(user_input)
                    if new_embedding is not None:
                        st.session_state.semantic_cache.append({
                            "embedding": new_embedding,
                            "question": user_input,
                            "answer": ai_response
                        })
                
            except Exception as e:
                st.markdown(f"❌ Hệ thống bận: {e}. Bạn vui lòng thử gõ lại câu hỏi nhé!")
