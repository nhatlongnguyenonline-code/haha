import warnings
import os
import time
import json
import hashlib
import secrets
import io
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import numpy as np
import requests
import bcrypt
import streamlit as st
from bs4 import BeautifulSoup
from PIL import Image
from google import genai
from google.genai import types
from supabase import create_client, Client

warnings.filterwarnings("ignore")

# ============================================================
# CẤU HÌNH
# ============================================================
st.set_page_config(
    page_title="Trợ Lý AI Toàn Năng",
    page_icon="🐦‍🔥",
    layout="centered",
)

AI_MODEL = st.secrets.get("GEMINI_MODEL", "gemini-3.6-flash")
IMAGEN_MODEL = st.secrets.get("IMAGEN_MODEL", "imagen-3.0-generate-002")
EMBEDDING_MODEL = st.secrets.get("EMBEDDING_MODEL", "gemini-embedding-001")
CACHE_THRESHOLD = float(st.secrets.get("CACHE_THRESHOLD", 0.85))
SESSION_DAYS = int(st.secrets.get("SESSION_DAYS", 30))
MAX_WEB_RESULTS = int(st.secrets.get("MAX_WEB_RESULTS", 3))
MAX_PAGE_TEXT = int(st.secrets.get("MAX_PAGE_TEXT", 2500))

# ============================================================
# GIAO DIỆN & NÂNG CẤP ĐỒ HỌA
# ============================================================
st.markdown(
    """
    <style>
    .main { background-color: #FAFAFA !important; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #F1F5F9 100%) !important;
        border-right: 1px solid #E2E8F0 !important;
        box-shadow: 4px 0 15px rgba(0, 0, 0, 0.02) !important;
    }
    [data-testid="stChatMessage"] {
        border-radius: 20px !important;
        margin-bottom: 18px !important;
        padding: 18px 22px !important;
        transition: all 0.2s ease-in-out !important;
    }
    [data-testid="stChatMessageAssistant"] {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03) !important;
    }
    [data-testid="stChatMessageUser"] {
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%) !important;
        border: 1px solid #BFDBFE !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.05) !important;
    }
    [data-testid="stChatMessageAvatar"] {
        border-radius: 50% !important;
        border: 2px solid #3B82F6 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
    }
    .stChatInput {
        position: fixed !important;
        bottom: 25px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        z-index: 999 !important;
        width: 100% !important;
        max-width: 650px !important;
    }
    .stChatInput [data-testid="stChatInputCurrentContainer"] {
        border: 2px solid #3B82F6 !important;
        border-radius: 28px !important;
        background: #FFFFFF !important;
        padding: 6px 14px !important;
        box-shadow: 0 12px 35px rgba(59, 130, 246, 0.18) !important;
    }
    .premium-title-container {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 14px;
        margin-top: 1rem;
        margin-bottom: 6px;
    }
    .premium-logo { font-size: 2.8rem; }
    .premium-text {
        font-size: 2.4rem;
        font-weight: 900;
        letter-spacing: -0.5px;
        background: linear-gradient(90deg, #2563EB 0%, #7C3AED 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-title {
        text-align: center;
        color: #64748B !important;
        font-size: 0.95rem;
        margin-bottom: 2rem;
    }
    .stButton button { border-radius: 12px !important; font-weight: 600 !important; }
    .login-box {
        padding: 28px;
        border-radius: 20px;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# TIỆN ÍCH CHUNG & KẾT NỐI
# ============================================================
def safe_error_message(exc):
    text = str(exc).replace("\n", " ")
    for secret_name in ("GEMINI_API_KEY", "SUPABASE_KEY", "SUPABASE_URL"):
        secret_value = st.secrets.get(secret_name, "")
        if secret_value:
            text = text.replace(str(secret_value), "[REDACTED]")
    return text[:500]

def normalize_history(value):
    if not isinstance(value, list):
        return []
    cleaned = []
    for item in value:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            cleaned.append({"role": role, "content": content})
    return cleaned

def next_page_name(pages):
    index = 1
    while f"Trang Chat {index}" in pages:
        index += 1
    return f"Trang Chat {index}"

missing = [k for k in ("SUPABASE_URL", "SUPABASE_KEY", "GEMINI_API_KEY") if not st.secrets.get(k)]
if missing:
    st.error("⚠️ Thiếu cấu hình Secrets: " + ", ".join(missing))
    st.stop()

try:
    supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as exc:
    st.error(f"❌ Không thể kết nối Supabase: {safe_error_message(exc)}")
    st.stop()

if "ai_client" not in st.session_state:
    try:
        st.session_state.ai_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception as exc:
        st.error(f"❌ Không thể khởi tạo Gemini Client: {safe_error_message(exc)}")
        st.stop()

# ============================================================
# SESSION LOGIN
# ============================================================
if "global_token_registry" not in st.session_state:
    st.session_state.global_token_registry = {}

url_token = st.query_params.get("token")
logged_in_user = st.session_state.global_token_registry.get(url_token) if url_token else None

if logged_in_user is None:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🔒 Đăng Nhập", "📝 Đăng Ký Tài Khoản"])
    with tab1:
        st.subheader("Đăng nhập hệ thống")
        lin_user = st.text_input("Tên đăng nhập", key="lin_u").strip()
        lin_pass = st.text_input("Mật khẩu", type="password", key="lin_p")
        if st.button("Đăng Nhập", use_container_width=True, type="primary"):
            if lin_user and lin_pass:
                try:
                    res = supabase.table("users").select("username,password").eq("username", lin_user).limit(1).execute()
                    if res.data and bcrypt.checkpw(lin_pass.encode("utf-8"), res.data[0].get("password", "").encode("utf-8")):
                        secure_token = secrets.token_urlsafe(32)
                        st.session_state.global_token_registry[secure_token] = lin_user
                        st.query_params["token"] = secure_token
                        st.rerun()
                    else:
                        st.error("❌ Sai tài khoản hoặc mật khẩu.")
                except Exception as exc:
                    st.error(f"❌ Lỗi: {safe_error_message(exc)}")
    with tab2:
        st.subheader("Tạo tài khoản mới")
        reg_user = st.text_input("Tên đăng nhập mới", key="reg_u").strip()
        reg_pass = st.text_input("Mật khẩu mới", type="password", key="reg_p")
        if st.button("Xác Nhận Đăng Ký", use_container_width=True):
            if reg_user and len(reg_pass) >= 6:
                try:
                    hashed_p = bcrypt.hashpw(reg_pass.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                    supabase.table("users").insert({"username": reg_user, "password": hashed_p, "display_name": reg_user}).execute()
                    st.success("✅ Đăng ký thành công!")
                except Exception as exc:
                    st.error(f"❌ Lỗi: {safe_error_message(exc)}")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ============================================================
# STATE CỦA USER
# ============================================================
u_id = logged_in_user
pages_key = f"chat_pages_{u_id}"
active_page_key = f"active_page_{u_id}"

def download_supabase_history(username):
    pages = {}
    try:
        res = supabase.table("chat_histories").select("page_name,history_data").eq("username", username).execute()
        for row in res.data or []:
            if row.get("page_name"):
                pages[row["page_name"]] = normalize_history(row.get("history_data"))
    except Exception:
        pass
    return pages

def upload_single_page_supabase(username, page_name, data_list):
    try:
        supabase.table("chat_histories").upsert({
            "username": username,
            "page_name": page_name,
            "history_data": normalize_history(data_list),
        }, on_conflict="username,page_name").execute()
    except Exception:
        pass

if pages_key not in st.session_state:
    db_pages = download_supabase_history(u_id)
    if not db_pages:
        db_pages = {"Trang Chat 1": []}
        upload_single_page_supabase(u_id, "Trang Chat 1", [])
    st.session_state[pages_key] = db_pages

if active_page_key not in st.session_state:
    st.session_state[active_page_key] = list(st.session_state[pages_key].keys())[-1]

current_page = st.session_state[active_page_key]

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown(f"### 👤 TÀI KHOẢN: **{u_id.upper()}**")
    if st.button("🚪 Đăng Xuất", use_container_width=True):
        st.query_params.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("### 💬 PHÒNG CHAT")
    if st.button("➕ Trang Chat Mới", use_container_width=True, type="primary"):
        new_p = next_page_name(st.session_state[pages_key])
        st.session_state[pages_key][new_p] = []
        upload_single_page_supabase(u_id, new_p, [])
        st.session_state[active_page_key] = new_p
        st.rerun()

    st.markdown("---")
    st.markdown("### 🎵 NHẠC CHILL THƯ GIÃN")
    st.markdown("☕ **Lofi Study Chill**")
    st.audio("https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3", format="audio/mp3", loop=True)

# ============================================================
# TITLE & LỊCH SỬ CHAT
# ============================================================
st.markdown(
    """
    <div class="premium-title-container">
        <span class="premium-logo">🐦‍🔥</span>
        <span class="premium-text">TRỢ LÝ AI TOÀN NĂNG</span>
    </div>
    <div class="sub-title">Tích hợp Gemini 3.6 Flash & Google Imagen 3</div>
    """,
    unsafe_allow_html=True,
)

for message in st.session_state[pages_key][current_page]:
    avatar = "👤" if message["role"] == "user" else "🐦‍🔥"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# ============================================================
# XỬ LÝ CÂU HỎI MỚI / TẠO ẢNH
# ============================================================
if user_input := st.chat_input("Nhập tin nhắn hoặc 'Vẽ [mô tả]' để tạo ảnh..."):
    user_input = user_input.strip()
    if not user_input:
        st.stop()

    current_history = st.session_state[pages_key][current_page]
    current_history.append({"role": "user", "content": user_input})

    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    # Kiếm tra xem người dùng có yêu cầu vẽ / tạo ảnh không
    image_keywords = ["vẽ", "tạo ảnh", "sinh ảnh", "tạo hình ảnh", "draw", "generate image", "image of"]
    is_image_request = any(user_input.lower().startswith(kw) or f" {kw} " in f" {user_input.lower()} " for kw in image_keywords)

    with st.chat_message("assistant", avatar="🐦‍🔥"):
        if is_image_request:
            # ----------------------------------------------------
            # TẠO ẢNH BẰNG GOOGLE IMAGEN 3
            # ----------------------------------------------------
            with st.spinner("🎨 Đang dùng Google Imagen 3 vẽ bức ảnh cho bạn..."):
                try:
                    result = st.session_state.ai_client.models.generate_images(
                        model=IMAGEN_MODEL,
                        prompt=user_input,
                        config=types.GenerateImagesConfig(
                            number_of_images=1,
                            output_mime_type="image/jpeg",
                            aspect_ratio="1:1", # Có thể đổi: "1:1", "3:4", "4:3", "16:9"
                        )
                    )
                    
                    if result.generated_images:
                        generated_image = result.generated_images[0]
                        image_bytes = generated_image.image.image_bytes
                        image = Image.open(io.BytesIO(image_bytes))

                        # Hiển thị ảnh trên giao diện
                        st.image(image, caption=f"🖼 Bức ảnh tạo từ câu lệnh: '{user_input}'", use_container_width=True)
                        
                        response_text = f"✅ Đã tạo ảnh thành công cho yêu cầu: **'{user_input}'**"
                        current_history.append({"role": "assistant", "content": response_text})
                        upload_single_page_supabase(u_id, current_page, current_history)
                    else:
                        st.error("❌ Không thể tạo ảnh từ yêu cầu này.")
                except Exception as exc:
                    st.error(f"❌ Lỗi khi sinh ảnh với Imagen: {safe_error_message(exc)}")
        else:
            # ----------------------------------------------------
            # TRẢ LỜI VĂN BẢN VỚI GEMINI
            # ----------------------------------------------------
            try:
                response = st.session_state.ai_client.models.generate_content(
                    model=AI_MODEL,
                    contents=user_input,
                )
                ai_text = response.text or "⚠️ Không có phản hồi."
                st.markdown(ai_text)
                current_history.append({"role": "assistant", "content": ai_text})
                upload_single_page_supabase(u_id, current_page, current_history)
            except Exception as exc:
                st.error(f"❌ Lỗi AI: {safe_error_message(exc)}")
