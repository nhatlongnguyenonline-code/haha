import warnings
import os
import time
import json
import hashlib
import secrets
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
    page_title="Trợ Lý AI & Cộng Đồng",
    page_icon="🐦‍🔥",
    layout="centered",
)

AI_MODEL = st.secrets.get("GEMINI_MODEL", "gemini-3.6-flash")
EMBEDDING_MODEL = st.secrets.get("EMBEDDING_MODEL", "gemini-embedding-001")
CACHE_THRESHOLD = float(st.secrets.get("CACHE_THRESHOLD", 0.85))
SESSION_DAYS = int(st.secrets.get("SESSION_DAYS", 30))
MAX_WEB_RESULTS = int(st.secrets.get("MAX_WEB_RESULTS", 3))
MAX_PAGE_TEXT = int(st.secrets.get("MAX_PAGE_TEXT", 2500))

# ============================================================
# GIAO DIỆN & NÂNG CẤP ĐỒ HỌA (ADVANCED UI/UX)
# ============================================================
st.markdown(
    """
    <style>
    /* CSS Nền chung */
    .main {
        background-color: #FAFAFA !important;
    }

    /* Sidebar thiết kế phong cách Glassmorphism */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #F1F5F9 100%) !important;
        border-right: 1px solid #E2E8F0 !important;
        box-shadow: 4px 0 15px rgba(0, 0, 0, 0.02) !important;
    }

    /* Tùy chỉnh Bong Bóng Chat */
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

    /* Avatar Chatbot & Người dùng */
    [data-testid="stChatMessageAvatar"] {
        border-radius: 50% !important;
        border: 2px solid #3B82F6 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
        transition: transform 0.2s ease !important;
    }
    [data-testid="stChatMessageAvatar"]:hover {
        transform: scale(1.1) !important;
    }

    /* Thanh Nhập Tin Nhắn Nổi Đẳng Cấp */
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
        transition: all 0.3s ease !important;
    }

    .stChatInput [data-testid="stChatInputCurrentContainer"]:focus-within {
        box-shadow: 0 12px 40px rgba(59, 130, 246, 0.35) !important;
        border-color: #2563EB !important;
    }

    .stChatInput textarea {
        color: #0F172A !important;
        font-size: 0.98rem !important;
        font-weight: 500 !important;
    }

    /* Tiêu Đề Nổi Bật */
    .premium-title-container {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 14px;
        margin-top: 1rem;
        margin-bottom: 6px;
    }
    .premium-logo { 
        font-size: 2.8rem;
        filter: drop-shadow(0 4px 8px rgba(0,0,0,0.15));
    }
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
        font-weight: 500;
        margin-bottom: 1.5rem;
    }

    /* Nút Bấm Đẹp Mắt */
    .stButton button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    .stButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
    }

    /* Khung Đăng Nhập & Social Card */
    .login-box {
        padding: 28px;
        border-radius: 20px;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .social-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    .social-user {
        font-weight: 700;
        color: #2563EB;
        font-size: 0.9rem;
    }
    .social-time {
        font-size: 0.75rem;
        color: #94A3B8;
        float: right;
    }

    /* Ẩn bớt hiệu ứng thừa của Streamlit */
    [data-testid="stHeaderHeading"] svg,
    [data-testid="stElementContainer"] h1 svg {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# TIỆN ÍCH CHUNG
# ============================================================
def safe_error_message(exc):
    """Không hiển thị secret/token trong thông báo lỗi."""
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


def sha256_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

# ============================================================
# KẾT NỐI SECRETS / SUPABASE / GEMINI
# ============================================================
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
        st.error(f"❌ Không thể khởi tạo Gemini: {safe_error_message(exc)}")
        st.stop()

# ============================================================
# EMBEDDING / CACHE
# ============================================================
def get_embedding(text):
    if not text or not text.strip():
        return None
    try:
        response = st.session_state.ai_client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text.strip(),
        )
        if not response.embeddings:
            return None
        values = response.embeddings[0].values
        return np.asarray(values, dtype=np.float32) if values else None
    except Exception:
        return None


def cosine_similarity(a, b):
    try:
        a = np.asarray(a, dtype=np.float32)
        b = np.asarray(b, dtype=np.float32)
        if a.size == 0 or b.size == 0 or a.shape != b.shape:
            return -1.0
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0:
            return -1.0
        return float(np.dot(a, b) / denom)
    except Exception:
        return -1.0

# ============================================================
# SESSION LOGIN
# ============================================================
if "global_token_registry" not in st.session_state:
    st.session_state.global_token_registry = {}

url_token = st.query_params.get("token")
logged_in_user = None

if url_token:
    logged_in_user = st.session_state.global_token_registry.get(url_token)

# ============================================================
# ĐĂNG NHẬP / ĐĂNG KÝ
# ============================================================
if logged_in_user is None:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🔒 Đăng Nhập", "📝 Đăng Ký Tài Khoản"])

    with tab1:
        st.subheader("Đăng nhập hệ thống")
        lin_user = st.text_input("Tên đăng nhập", key="lin_u").strip()
        lin_pass = st.text_input("Mật khẩu", type="password", key="lin_p")

        if st.button("Đăng Nhập", use_container_width=True, type="primary"):
            if not lin_user or not lin_pass:
                st.warning("⚠️ Vui lòng nhập đầy đủ tài khoản và mật khẩu.")
            else:
                try:
                    res = (
                        supabase.table("users")
                        .select("username,password")
                        .eq("username", lin_user)
                        .limit(1)
                        .execute()
                    )
                    if not res.data:
                        st.error("❌ Tài khoản không tồn tại.")
                    else:
                        stored_hash = res.data[0].get("password", "")
                        valid = False
                        try:
                            valid = bcrypt.checkpw(
                                lin_pass.encode("utf-8"),
                                stored_hash.encode("utf-8"),
                            )
                        except (ValueError, TypeError):
                            valid = False

                        if valid:
                            secure_token = secrets.token_urlsafe(32)
                            st.session_state.global_token_registry[secure_token] = lin_user
                            st.query_params["token"] = secure_token
                            st.rerun()
                        else:
                            st.error("❌ Sai mật khẩu.")
                except Exception as exc:
                    st.error(f"❌ Lỗi đăng nhập: {safe_error_message(exc)}")

    with tab2:
        st.subheader("Tạo tài khoản mới")
        reg_user = st.text_input("Tên đăng nhập mới", key="reg_u").strip()
        reg_pass = st.text_input("Mật khẩu mới", type="password", key="reg_p")
        reg_pass2 = st.text_input("Nhập lại mật khẩu", type="password", key="reg_p2")

        if st.button("Xác Nhận Đăng Ký", use_container_width=True):
            if not reg_user or not reg_pass.strip():
                st.warning("⚠️ Không được để trống tài khoản hoặc mật khẩu.")
            elif len(reg_user) < 3:
                st.warning("⚠️ Tên đăng nhập cần ít nhất 3 ký tự.")
            elif len(reg_pass) < 6:
                st.warning("⚠️ Mật khẩu cần ít nhất 6 ký tự.")
            elif reg_pass != reg_pass2:
                st.error("❌ Hai mật khẩu không giống nhau.")
            else:
                try:
                    check_res = (
                        supabase.table("users")
                        .select("username")
                        .eq("username", reg_user)
                        .limit(1)
                        .execute()
                    )
                    if check_res.data:
                        st.error("❌ Tên đăng nhập này đã được sử dụng.")
                    else:
                        hashed_p = bcrypt.hashpw(
                            reg_pass.encode("utf-8"), bcrypt.gensalt()
                        ).decode("utf-8")
                        supabase.table("users").insert({
                            "username": reg_user,
                            "password": hashed_p,
                            "display_name": reg_user,
                        }).execute()
                        st.success("✅ Đăng ký thành công! Hãy đăng nhập.")
                except Exception as exc:
                    st.error(f"❌ Không thể đăng ký: {safe_error_message(exc)}")

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ============================================================
# STATE CỦA USER
# ============================================================
u_id = logged_in_user
pages_key = f"chat_pages_{u_id}"
active_page_key = f"active_page_{u_id}"
cache_key = f"cache_{u_id}"

# ============================================================
# SUPABASE CHAT HELPERS
# ============================================================
def download_supabase_history(username):
    pages = {}
    try:
        res = (
            supabase.table("chat_histories")
            .select("page_name,history_data")
            .eq("username", username)
            .execute()
        )
        for row in res.data or []:
            page_name = row.get("page_name")
            if page_name:
                pages[page_name] = normalize_history(row.get("history_data"))
    except Exception as exc:
        st.error(f"❌ Không tải được lịch sử chat: {safe_error_message(exc)}")
    return pages


def upload_single_page_supabase(username, page_name, data_list):
    try:
        supabase.table("chat_histories").upsert(
            {
                "username": username,
                "page_name": page_name,
                "history_data": normalize_history(data_list),
            },
            on_conflict="username,page_name",
        ).execute()
        return True
    except Exception as exc:
        st.error(f"❌ Không lưu được lịch sử: {safe_error_message(exc)}")
        return False

# ============================================================
# LOAD CHAT PAGES
# ============================================================
if pages_key not in st.session_state:
    db_pages = download_supabase_history(u_id)
    if not db_pages:
        db_pages = {"Trang Chat 1": []}
        upload_single_page_supabase(u_id, "Trang Chat 1", [])
    st.session_state[pages_key] = db_pages

if active_page_key not in st.session_state:
    st.session_state[active_page_key] = list(st.session_state[pages_key].keys())[-1]

if cache_key not in st.session_state:
    st.session_state[cache_key] = []

current_page = st.session_state[active_page_key]
if current_page not in st.session_state[pages_key]:
    current_page = list(st.session_state[pages_key].keys())[-1]
    st.session_state[active_page_key] = current_page

# ============================================================
# USER INFO
# ============================================================
try:
    user_info_res = (
        supabase.table("users")
        .select("display_name")
        .eq("username", u_id)
        .limit(1)
        .execute()
    )
    display_name = (
        user_info_res.data[0].get("display_name") or u_id
        if user_info_res.data else u_id
    )
except Exception:
    display_name = u_id

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown(f"### 👤 TÀI KHOẢN: **{display_name.upper()}**")

    rename_user_key = f"rename_user_mode_{u_id}"
    if rename_user_key not in st.session_state:
        st.session_state[rename_user_key] = False

    if not st.session_state[rename_user_key]:
        if st.button("✏️ Đổi tên hiển thị", use_container_width=True):
            st.session_state[rename_user_key] = True
            st.rerun()
    else:
        new_name = st.text_input("Nhập tên hiển thị mới:", value=display_name).strip()
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            if st.button("💾 Lưu tên", use_container_width=True, type="primary"):
                if new_name:
                    try:
                        supabase.table("users").update({"display_name": new_name}).eq(
                            "username", u_id
                        ).execute()
                    except Exception as exc:
                        st.error(f"❌ Không đổi được tên: {safe_error_message(exc)}")
                st.session_state[rename_user_key] = False
                st.rerun()
        with col_u2:
            if st.button("Hủy", use_container_width=True):
                st.session_state[rename_user_key] = False
                st.rerun()

    if st.button("🚪 Đăng Xuất Hệ Thống", use_container_width=True):
        token = st.query_params.get("token")
        if token:
            st.session_state.global_token_registry.pop(token, None)
        st.query_params.clear()
        for key in list(st.session_state.keys()):
            if key.startswith(("chat_pages_", "active_page_", "cache_", "ai_session_", "rename_")):
                del st.session_state[key]
        st.rerun()

    st.markdown("---")
    st.markdown("### 💬 QUẢN LÝ PHÒNG CHAT AI")

    if st.button("➕ Tạo trang chat mới", use_container_width=True, type="primary"):
        pages = st.session_state[pages_key]
        new_page_name = next_page_name(pages)
        pages[new_page_name] = []
        upload_single_page_supabase(u_id, new_page_name, [])
        st.session_state[active_page_key] = new_page_name
        st.rerun()

    page_options = list(st.session_state[pages_key].keys())
    selected_page = st.selectbox(
        "Chọn trang hội thoại đang xem:",
        page_options,
        index=page_options.index(current_page),
    )
    if selected_page != current_page:
        st.session_state[active_page_key] = selected_page
        st.rerun()

    rename_page_key = f"rename_mode_{u_id}"
    if rename_page_key not in st.session_state:
        st.session_state[rename_page_key] = False

    if not st.session_state[rename_page_key]:
        if st.button("✏️ Đổi tên trang này", use_container_width=True):
            st.session_state[rename_page_key] = True
            st.rerun()
    else:
        new_title = st.text_input("Nhập tên mới:", value=current_page).strip()
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button("✅ Lưu tên", use_container_width=True, type="primary"):
                if not new_title:
                    st.warning("Tên trang không được để trống.")
                elif new_title == current_page:
                    st.session_state[rename_page_key] = False
                    st.rerun()
                elif new_title in st.session_state[pages_key]:
                    st.error("❌ Tên trang đã tồn tại.")
                else:
                    old_history = st.session_state[pages_key][current_page]
                    try:
                        supabase.table("chat_histories").delete().eq("username", u_id).eq(
                            "page_name", current_page
                        ).execute()
                        upload_single_page_supabase(u_id, new_title, old_history)
                        st.session_state[pages_key][new_title] = st.session_state[pages_key].pop(current_page)
                        st.session_state[active_page_key] = new_title
                        st.session_state.pop(f"ai_session_{u_id}_{current_page}", None)
                    except Exception as exc:
                        st.error(f"❌ Không đổi được tên trang: {safe_error_message(exc)}")
                    st.session_state[rename_page_key] = False
                    st.rerun()
        with col_r2:
            if st.button("❌ Hủy", use_container_width=True):
                st.session_state[rename_page_key] = False
                st.rerun()

    st.markdown("---")
    st.markdown("### 🎵 NHẠC CHILL THƯ GIÃN")
    LOFI_URL = "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3"
    st.markdown("☕ **Lofi Study Chill**")
    st.audio(LOFI_URL, format="audio/mp3", loop=True)

    st.markdown("---")
    st.markdown("### ⚙️ CÀI ĐẶT CHATBOT")
    creativity = st.slider(
        "🧠 Độ nhạy bén / Sáng tạo",
        min_value=0.1,
        max_value=1.0,
        value=0.3,
        step=0.1,
    )

    st.markdown("---")
    st.markdown("### 📸 PHÂN TÍCH HÌNH ẢNH")
    uploaded_file = st.file_uploader(
        "Tải ảnh lên tại đây...",
        type=["png", "jpg", "jpeg", "webp"],
    )
    if uploaded_file:
        try:
            preview = Image.open(uploaded_file)
            st.image(preview, caption="Ảnh đã chọn", use_container_width=True)
        except Exception:
            st.error("❌ File ảnh không hợp lệ.")
            uploaded_file = None

    st.markdown("---")
    st.markdown("### 📂 NHẬT KÝ TRANG HIỆN TẠI")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑 Dọn tin", use_container_width=True):
            st.session_state[pages_key][current_page] = []
            upload_single_page_supabase(u_id, current_page, [])
            st.session_state.pop(f"ai_session_{u_id}_{current_page}", None)
            st.rerun()

    with col2:
        if len(page_options) > 1:
            if st.button("❌ Xóa trang", use_container_width=True):
                try:
                    supabase.table("chat_histories").delete().eq("username", u_id).eq(
                        "page_name", current_page
                    ).execute()
                    del st.session_state[pages_key][current_page]
                    st.session_state[active_page_key] = list(st.session_state[pages_key].keys())[-1]
                    st.session_state.pop(f"ai_session_{u_id}_{current_page}", None)
                    st.rerun()
                except Exception as exc:
                    st.error(f"❌ Không xóa được trang: {safe_error_message(exc)}")
        else:
            st.caption("🔒 Giữ lại 1 trang.")

# ============================================================
# WEB SEARCH
# ============================================================
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None


def search_the_web_ddg(query, max_results=MAX_WEB_RESULTS):
    if DDGS is None:
        return []
    urls = []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        for result in results:
            href = result.get("href") if isinstance(result, dict) else None
            if href and href.startswith(("http://", "https://")):
                urls.append(href)
    except Exception:
        return []
    return urls


def extract_web_content(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return ""

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/153.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=6, allow_redirects=True)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            return ""

        soup = BeautifulSoup(response.content, "html.parser")
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
            element.decompose()
        text = " ".join(soup.get_text(" ").split())
        return text[:MAX_PAGE_TEXT]
    except Exception:
        return ""

# ============================================================
# TITLE
# ============================================================
st.markdown(
    """
    <div class="premium-title-container">
        <span class="premium-logo">🐦‍🔥</span>
        <span class="premium-text">TRỢ LÝ AI & CỘNG ĐỒNG</span>
    </div>
    <div class="sub-title">Tích hợp AI Chatbot, Phòng Chat Chung & Bảng Tin Prompt</div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# PHÂN CHIA TABS: AI CHAT vs CHAT CỘNG ĐỒNG vs BẢNG TIN PROMPT
# ============================================================
tab_ai, tab_public, tab_community = st.tabs([
    "🤖 Chat Với AI", 
    "💬 Chat Cộng Đồng", 
    "🌟 Bảng Tin Prompt"
])

# ------------------------------------------------------------
# TAB 1: CHAT VỚI AI (Logic gốc của bạn)
# ------------------------------------------------------------
with tab_ai:
    # Hiển thị lịch sử chat AI
    for message in st.session_state[pages_key][current_page]:
        avatar = "👤" if message["role"] == "user" else "🐦‍🔥"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # Nút chia sẻ câu trả lời cuối cùng lên Bảng tin cộng đồng
    if st.session_state[pages_key][current_page]:
        hist = st.session_state[pages_key][current_page]
        if len(hist) >= 2 and hist[-1]["role"] == "assistant":
            if st.button("📤 Chia sẻ câu trả lời hay nhất này lên Bảng Tin Prompt", use_container_width=True):
                try:
                    last_prompt = hist[-2]["content"]
                    last_answer = hist[-1]["content"]
                    supabase.table("community_prompts").insert({
                        "username": display_name,
                        "prompt": last_prompt,
                        "ai_response": last_answer,
                    }).execute()
                    st.success("🎉 Đã chia sẻ thành công lên Bảng Tin Prompt!")
                except Exception as exc:
                    st.error(f"❌ Lỗi chia sẻ: {safe_error_message(exc)}")

    # Nhập câu hỏi mới cho AI
    if user_input := st.chat_input("Nhập câu hỏi hoặc yêu cầu phân tích ảnh tại đây..."):
        user_input = user_input.strip()
        if not user_input:
            st.stop()

        current_history = st.session_state[pages_key][current_page]
        current_history.append({"role": "user", "content": user_input})

        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)

        # Cache Semantic
        cache_hit = False
        cached_answer = ""

        if not uploaded_file and st.session_state[cache_key]:
            current_embedding = get_embedding(user_input)
            if current_embedding is not None:
                best_score = -1.0
                best_match = None
                for item in st.session_state[cache_key]:
                    score = cosine_similarity(current_embedding, item.get("embedding"))
                    if score > best_score:
                        best_score = score
                        best_match = item
                if best_match is not None and best_score >= CACHE_THRESHOLD:
                    cache_hit = True
                    cached_answer = best_match["answer"]

        if cache_hit:
            with st.chat_message("assistant", avatar="🐦‍🔥"):
                st.markdown(cached_answer)
                st.caption(f"⚡ Phản hồi từ semantic cache ({CACHE_THRESHOLD:.2f})")

            current_history.append({"role": "assistant", "content": cached_answer})
            upload_single_page_supabase(u_id, current_page, current_history)
            st.stop()

        # Web Context
        cau_hoi_clean = user_input.lower()
        keywords = [
            "ở đâu", "thành phố", "giá", "thời tiết", "mấy độ", "bao nhiêu",
            "hôm nay", "tin tức", "ai là", "sự kiện", "trường thcs", "là gì",
            "dịch", "nghĩa là gì", "mới nhất", "vừa qua", "hiện tại", "năm nay",
            "tuần này", "tháng này", "vừa mới", "gần đây", "ngày mai", "hôm qua",
            "giá vàng", "xăng dầu", "cổ phiếu", "tỷ giá", "usd", "bitcoin", "crypto",
            "thị trường", "tỷ số", "trận đấu", "bóng đá", "ngoại hạng anh",
            "champions league", "kết quả", "lịch thi đấu", "drama", "scandal", "showbiz",
            "bản cập nhật", "vừa ra mắt", "ios", "android", "review", "đập hộp",
            "mở bán", "update", "thông số", "mô hình"
        ]
        need_web = any(word in cau_hoi_clean for word in keywords)

        combined_context = ""
        sources = []

        if need_web and not uploaded_file:
            with st.status("🔍 Đang tra cứu thông tin thực tế...", expanded=False) as status:
                web_links = search_the_web_ddg(user_input)
                for link in web_links:
                    content = extract_web_content(link)
                    if content:
                        combined_context += f"\n--- Nguồn tham khảo: {link} ---\n{content}\n"
                        sources.append(link)
                status.update(
                    label="✅ Đã đọc dữ liệu web." if sources else "⚠️ Không lấy được nguồn web.",
                    state="complete" if sources else "error",
                )

        if combined_context:
            prompt_payload = (
                "Bạn là Trợ lý AI Toàn năng. Hãy trả lời bằng tiếng Việt nếu người dùng hỏi bằng tiếng Việt. "
                "Dữ liệu web bên dưới chỉ là nguồn tham khảo; không được tự bịa thông tin không có trong dữ liệu hoặc kiến thức của bạn. "
                "Nếu nguồn mâu thuẫn hoặc không đủ chắc chắn, hãy nói rõ điều đó.\n\n"
                f"DỮ LIỆU WEB:\n{combined_context}\n\n"
                f"CÂU HỎI:\n{user_input}"
            )
        else:
            prompt_payload = user_input

        # Gemini Response
        with st.chat_message("assistant", avatar="🐦‍🔥"):
            try:
                config = types.GenerateContentConfig(
                    temperature=float(creativity),
                )

                if uploaded_file:
                    uploaded_file.seek(0)
                    image = Image.open(uploaded_file).convert("RGB")
                    response_stream = st.session_state.ai_client.models.generate_content_stream(
                        model=AI_MODEL,
                        contents=[image, prompt_payload],
                        config=config,
                    )
                else:
                    chat_session_key = f"ai_session_{u_id}_{current_page}"
                    if chat_session_key not in st.session_state:
                        st.session_state[chat_session_key] = st.session_state.ai_client.chats.create(
                            model=AI_MODEL,
                            config=config,
                        )
                    response_stream = st.session_state[chat_session_key].send_message_stream(
                        message=prompt_payload,
                        config=config,
                    )

                def response_generator():
                    for chunk in response_stream:
                        text = getattr(chunk, "text", None)
                        if text:
                            yield text

                ai_response = st.write_stream(response_generator())
                ai_response = ai_response if isinstance(ai_response, str) else str(ai_response or "")

                if not ai_response.strip():
                    ai_response = "⚠️ AI không trả về nội dung. Bạn hãy thử lại."
                    st.warning(ai_response)

                if sources:
                    source_text = "\n\n---\n🌐 **Nguồn tham khảo:**\n" + "\n".join(
                        f"- {src}" for src in sources
                    )
                    st.markdown(source_text)
                    ai_response += source_text

                current_history.append({"role": "assistant", "content": ai_response})
                upload_single_page_supabase(u_id, current_page, current_history)

                if not uploaded_file and not sources:
                    new_embedding = get_embedding(user_input)
                    if new_embedding is not None:
                        st.session_state[cache_key].append({
                            "embedding": new_embedding,
                            "question": user_input,
                            "answer": ai_response,
                            "created_at": time.time(),
                        })
                        st.session_state[cache_key] = st.session_state[cache_key][-100:]

            except Exception as exc:
                error_text = safe_error_message(exc)
                error_message = f"❌ Hệ thống AI gặp lỗi: {error_text}"
                st.error(error_message)
                if current_history and current_history[-1].get("role") == "user":
                    current_history.pop()

# ------------------------------------------------------------
# TAB 2: CHAT CỘNG ĐỒNG (Global Lounge)
# ------------------------------------------------------------
with tab_public:
    st.caption("💬 Khung chat chung giữa tất cả các thành viên trong hệ thống.")
    
    col_refresh, _ = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 Tải tin mới", key="ref_pub"):
            st.rerun()

    # Form gửi tin nhắn cộng đồng
    with st.form("public_chat_form", clear_on_submit=True):
        pub_msg = st.text_input("Viết tin nhắn gửi tới mọi người...", key="pub_input")
        send_btn = st.form_submit_button("🚀 Gửi Tin Nhắn", type="primary")
        if send_btn and pub_msg.strip():
            try:
                supabase.table("public_messages").insert({
                    "username": display_name,
                    "message": pub_msg.strip(),
                }).execute()
                st.rerun()
            except Exception as exc:
                st.error(f"❌ Không gửi được tin nhắn: {safe_error_message(exc)}")

    st.markdown("---")
    
    # Tải danh sách 30 tin nhắn mới nhất
    try:
        res_pub = (
            supabase.table("public_messages")
            .select("*")
            .order("id", desc=True)
            .limit(30)
            .execute()
        )
        messages_list = res_pub.data or []
        
        if not messages_list:
            st.info("Chưa có tin nhắn nào. Hãy là người đầu tiên trò chuyện!")
        else:
            for item in messages_list:
                time_str = item.get("created_at", "")[:16].replace("T", " ")
                st.markdown(
                    f"""
                    <div class="social-card">
                        <span class="social-user">👤 {item.get('username')}</span>
                        <span class="social-time">🕒 {time_str}</span>
                        <div style="margin-top: 6px; color: #334155;">{item.get('message')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    except Exception as exc:
        st.error(f"❌ Lỗi tải tin nhắn cộng đồng: {safe_error_message(exc)}")

# ------------------------------------------------------------
# TAB 3: BẢNG TIN PROMPT HỒNG (Community Feed)
# ------------------------------------------------------------
with tab_community:
    st.caption("🌟 Nơi chia sẻ những câu hỏi (Prompt) hay và câu trả lời AI ấn tượng nhất.")

    try:
        res_feed = (
            supabase.table("community_prompts")
            .select("*")
            .order("likes", desc=True)
            .order("id", desc=True)
            .limit(20)
            .execute()
        )
        feed_items = res_feed.data or []

        if not feed_items:
            st.info("Chưa có chia sẻ nào. Trải nghiệm chat AI và bấm nút 'Chia sẻ' ở Tab Chat nhé!")
        else:
            for card in feed_items:
                c_id = card.get("id")
                c_user = card.get("username", "Vô danh")
                c_prompt = card.get("prompt", "")
                c_answer = card.get("ai_response", "")
                c_likes = card.get("likes", 0)

                with st.expander(f"📌 Chia sẻ từ **{c_user}**: *\"{c_prompt[:50]}...\"*"):
                    st.markdown(f"**❓ Câu hỏi / Prompt:**\n> {c_prompt}")
                    st.markdown(f"**🤖 AI Trả lời:**\n{c_answer}")
                    
                    col_like, col_info = st.columns([1, 4])
                    with col_like:
                        if st.button(f"❤️ Thích ({c_likes})", key=f"like_{c_id}"):
                            try:
                                supabase.table("community_prompts").update({
                                    "likes": c_likes + 1
                                }).eq("id", c_id).execute()
                                st.rerun()
                            except Exception:
                                pass
    except Exception as exc:
        st.error(f"❌ Lỗi tải bảng tin Prompt: {safe_error_message(exc)}")
