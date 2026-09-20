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
import streamlit as sb
from bs4 import BeautifulSoup
from PIL import Image
from google import genai
from google.genai import types
from supabase import create_client, Client

warnings.filterwarnings("ignore")

# ============================================================
# CẤU HÌNH TRANG STREAMLIT
# ============================================================
sb.set_page_config(
    page_title="Trợ Lý AI Tra Cứu Internet & Zalo Style",
    page_icon="🐦‍🔥",
    layout="wide",
)

AI_MODEL = sb.secrets.get("GEMINI_MODEL", "gemini-3.6-flash")
EMBEDDING_MODEL = sb.secrets.get("EMBEDDING_MODEL", "gemini-embedding-001")
CACHE_THRESHOLD = float(sb.secrets.get("CACHE_THRESHOLD", 0.85))
MAX_WEB_RESULTS = int(sb.secrets.get("MAX_WEB_RESULTS", 3))
MAX_PAGE_TEXT = int(sb.secrets.get("MAX_PAGE_TEXT", 2500))

DEFAULT_AVATAR = "https://www.w3schools.com/howto/img_avatar.png"
AI_AVATAR_EMOJI = "🐦‍🔥"

# ============================================================
# GIAO DIỆN & HIỆU ỨNG GRADIENT CAO CẤP (ZALO & AI STYLE)
# ============================================================
sb.markdown(
    """
    <style>
    .main {
        background-color: #F8FAFC !important;
    }
    [data-testid="sbSidebar"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #F1F5F9 100%) !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    [data-testid="sbChatMessage"] {
        border-radius: 16px !important;
        margin-bottom: 14px !important;
        padding: 14px 18px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }
    
    /* Hiệu ứng Gradient cho tiêu đề chính */
    .premium-title-container {
        display: flex;
        align-items: center;
        justify-content: flex-start;
        gap: 12px;
        margin-top: 0.5rem;
        margin-bottom: 2px;
    }
    .premium-logo { 
        font-size: 2.4rem;
    }
    .premium-gradient-text {
        font-size: 2.1rem;
        font-weight: 800;
        background: linear-gradient(135deg, #FF4B2B 0%, #FF416C 50%, #0068FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
    }
    .sub-title {
        text-align: left;
        color: #64748B !important;
        font-size: 0.95rem;
        font-weight: 500;
        margin-bottom: 1.5rem;
        margin-left: 3.8rem;
    }
    .sbButton button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease-in-out;
    }
    .login-box {
        max-width: 480px;
        margin: 40px auto;
        padding: 30px;
        border-radius: 20px;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        box-shadow: 0 12px 30px rgba(0,0,0,0.06);
    }
    .social-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 14px 18px;
        margin-bottom: 10px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
        display: flex;
        gap: 12px;
        align-items: center;
        transition: transform 0.15s ease;
    }
    .social-card:hover {
        border-color: #CBD5E1;
        box-shadow: 0 4px 12px rgba(0,0,0,0.04);
    }
    .social-user {
        font-weight: 700;
        color: #0068FF;
        font-size: 0.95rem;
    }
    .social-time {
        font-size: 0.75rem;
        color: #94A3B8;
        margin-left: auto;
    }
    .user-avatar-img {
        width: 42px;
        height: 42px;
        border-radius: 50%;
        object-fit: cover !important;
        border: 2px solid #0068FF;
        flex-shrink: 0;
    }
    .profile-card {
        text-align: center;
        padding: 12px 0;
    }
    .profile-avatar {
        width: 84px;
        height: 84px;
        border-radius: 50%;
        object-fit: cover !important;
        border: 3px solid #0068FF;
        box-shadow: 0 6px 15px rgba(0,104,255,0.15);
        margin: 0 auto 10px auto;
        display: block;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# TIỆN ÍCH CHUNG
# ============================================================
def safe_error_message(exc):
    text = str(exc).replace("\n", " ")
    for secret_name in ("GEMINI_API_KEY", "SUPABASE_KEY", "SUPABASE_URL"):
        secret_value = sb.secrets.get(secret_name, "")
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

# ============================================================
# KẾT NỐI SECRETS / SUPABASE / GEMINI
# ============================================================
missing = [k for k in ("SUPABASE_URL", "SUPABASE_KEY", "GEMINI_API_KEY") if not sb.secrets.get(k)]
if missing:
    sb.error("⚠️ Thiếu cấu hình Secrets: " + ", ".join(missing))
    sb.stop()

try:
    supabase: Client = create_client(sb.secrets["SUPABASE_URL"], sb.secrets["SUPABASE_KEY"])
except Exception as exc:
    sb.error(f"❌ Không thể kết nối Supabase: {safe_error_message(exc)}")
    sb.stop()

if "ai_client" not in sb.session_state:
    try:
        sb.session_state.ai_client = genai.Client(api_key=sb.secrets["GEMINI_API_KEY"])
    except Exception as exc:
        sb.error(f"❌ Không thể khởi tạo Gemini: {safe_error_message(exc)}")
        sb.stop()

# ============================================================
# EMBEDDING / CACHE
# ============================================================
def get_embedding(text):
    if not text or not text.strip():
        return None
    try:
        response = sb.session_state.ai_client.models.embed_content(
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
if "global_token_registry" not in sb.session_state:
    sb.session_state.global_token_registry = {}

url_token = sb.query_params.get("token")
logged_in_user = None

if url_token:
    logged_in_user = sb.session_state.global_token_registry.get(url_token)

if logged_in_user is None:
    sb.markdown('<div class="login-box">', unsafe_allow_html=True)
    tab_l1, tab_l2 = sb.tabs(["🔒 Đăng Nhập", "📝 Đăng Ký Tài Khoản"])

    with tab_l1:
        sb.subheader("Đăng nhập hệ thống")
        lin_user = sb.text_input("Tên đăng nhập", key="lin_u").strip()
        lin_pass = sb.text_input("Mật khẩu", type="password", key="lin_p")

        if sb.button("Đăng Nhập", use_container_width=True, type="primary"):
            if not lin_user or not lin_pass:
                sb.warning("⚠️ Vui lòng nhập đầy đủ tài khoản và mật khẩu.")
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
                        sb.error("❌ Tài khoản không tồn tại.")
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
                            sb.session_state.global_token_registry[secure_token] = lin_user
                            sb.query_params["token"] = secure_token
                            sb.rerun()
                        else:
                            sb.error("❌ Sai mật khẩu.")
                except Exception as exc:
                    sb.error(f"❌ Lỗi đăng nhập: {safe_error_message(exc)}")

    with tab_l2:
        sb.subheader("Tạo tài khoản mới")
        reg_user = sb.text_input("Tên đăng nhập mới", key="reg_u").strip()
        reg_pass = sb.text_input("Mật khẩu mới", type="password", key="reg_p")
        reg_pass2 = sb.text_input("Nhập lại mật khẩu", type="password", key="reg_p2")

        if sb.button("Xác Nhận Đăng Ký", use_container_width=True):
            if not reg_user or not reg_pass.strip():
                sb.warning("⚠️ Không được để trống tài khoản hoặc mật khẩu.")
            elif len(reg_user) < 3:
                sb.warning("⚠️ Tên đăng nhập cần ít nhất 3 ký tự.")
            elif len(reg_pass) < 6:
                sb.warning("⚠️ Mật khẩu cần ít nhất 6 ký tự.")
            elif reg_pass != reg_pass2:
                sb.error("❌ Hai mật khẩu không giống nhau.")
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
                        sb.error("❌ Tên đăng nhập này đã được sử dụng.")
                    else:
                        hashed_p = bcrypt.hashpw(
                            reg_pass.encode("utf-8"), bcrypt.gensalt()
                        ).decode("utf-8")
                        supabase.table("users").insert({
                            "username": reg_user,
                            "password": hashed_p,
                            "display_name": reg_user,
                            "avatar_url": DEFAULT_AVATAR
                        }).execute()
                        sb.success("✅ Đăng ký thành công! Hãy đăng nhập.")
                except Exception as exc:
                    sb.error(f"❌ Không thể đăng ký: {safe_error_message(exc)}")

    sb.markdown('</div>', unsafe_allow_html=True)
    sb.stop()

# ============================================================
# STATE CỦA USER
# ============================================================
u_id = logged_in_user
pages_key = f"chat_pages_{u_id}"
active_page_key = f"active_page_{u_id}"
cache_key = f"cache_{u_id}"
hidden_public_msgs_key = f"hidden_public_msgs_{u_id}"

if hidden_public_msgs_key not in sb.session_state:
    sb.session_state[hidden_public_msgs_key] = set()

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
        sb.error(f"❌ Không tải được lịch sử chat: {safe_error_message(exc)}")
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
        sb.error(f"❌ Không lưu được lịch sử: {safe_error_message(exc)}")
        return False

if pages_key not in sb.session_state:
    db_pages = download_supabase_history(u_id)
    if not db_pages:
        db_pages = {"Trang Chat 1": []}
        upload_single_page_supabase(u_id, "Trang Chat 1", [])
    sb.session_state[pages_key] = db_pages

if active_page_key not in sb.session_state:
    sb.session_state[active_page_key] = list(sb.session_state[pages_key].keys())[-1]

if cache_key not in sb.session_state:
    sb.session_state[cache_key] = []

current_page = sb.session_state[active_page_key]
if current_page not in sb.session_state[pages_key]:
    current_page = list(sb.session_state[pages_key].keys())[-1]
    sb.session_state[active_page_key] = current_page

display_name = u_id
avatar_url = DEFAULT_AVATAR

try:
    user_info_res = (
        supabase.table("users")
        .select("display_name, avatar_url")
        .eq("username", u_id)
        .limit(1)
        .execute()
    )
    if user_info_res.data:
        data_user = user_info_res.data[0]
        display_name = data_user.get("display_name") or u_id
        avatar_url = data_user.get("avatar_url") or DEFAULT_AVATAR
except Exception:
    pass

# ============================================================
# SIDEBAR
# ============================================================
with sb.sidebar:
    sb.markdown(
        f"""
        <div class="profile-card">
            <img src="{avatar_url}" class="profile-avatar" />
            <h3 style="margin: 0; color: #0F172A; font-size: 1.15rem;">{display_name.upper()}</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with sb.popover("🖼️ Đổi Avatar"):
        uploaded_avatar = sb.file_uploader("Chọn ảnh từ máy...", type=["jpg", "png", "jpeg", "webp"], key="avatar_file")
        if uploaded_avatar and sb.button("Lưu Avatar Mới", type="primary", use_container_width=True):
            try:
                image = Image.open(uploaded_avatar)
                width, height = image.size
                min_dim = min(width, height)
                left = (width - min_dim) / 2
                top = (height - min_dim) / 2
                right = (width + min_dim) / 2
                bottom = (height + min_dim) / 2
                
                cropped_img = image.crop((left, top, right, bottom))
                
                img_byte_arr = io.BytesIO()
                cropped_img.save(img_byte_arr, format='PNG')
                file_bytes = img_byte_arr.getvalue()

                file_path = f"{u_id}_{int(time.time())}.png"

                supabase.storage.from_("avatars").upload(
                    file_path, 
                    file_bytes, 
                    {"content-type": "image/png"}
                )
                
                public_avatar_url = supabase.storage.from_("avatars").get_public_url(file_path)
                supabase.table("users").update({"avatar_url": public_avatar_url}).eq("username", u_id).execute()
                sb.success("✅ Cập nhật avatar thành công!")
                sb.rerun()
            except Exception as exc:
                sb.error(f"❌ Lỗi tải avatar: {safe_error_message(exc)}")

    rename_user_key = f"rename_user_mode_{u_id}"
    if rename_user_key not in sb.session_state:
        sb.session_state[rename_user_key] = False

    if not sb.session_state[rename_user_key]:
        if sb.button("✏️ Đổi tên hiển thị", use_container_width=True):
            sb.session_state[rename_user_key] = True
            sb.rerun()
    else:
        new_name = sb.text_input("Nhập tên hiển thị mới:", value=display_name).strip()
        col_u1, col_u2 = sb.columns(2)
        with col_u1:
            if sb.button("💾 Lưu tên", use_container_width=True, type="primary"):
                if new_name:
                    try:
                        supabase.table("users").update({"display_name": new_name}).eq(
                            "username", u_id
                        ).execute()
                    except Exception as exc:
                        sb.error(f"❌ Không đổi được tên: {safe_error_message(exc)}")
                sb.session_state[rename_user_key] = False
                sb.rerun()
        with col_u2:
            if sb.button("Hủy", use_container_width=True):
                sb.session_state[rename_user_key] = False
                sb.rerun()

    if sb.button("🚪 Đăng Xuất Hệ Thống", use_container_width=True):
        token = sb.query_params.get("token")
        if token:
            sb.session_state.global_token_registry.pop(token, None)
        sb.query_params.clear()
        for key in list(sb.session_state.keys()):
            if key.startswith(("chat_pages_", "active_page_", "cache_", "ai_session_", "rename_", "hidden_public_msgs_")):
                del sb.session_state[key]
        sb.rerun()

    sb.markdown("---")
    sb.markdown("### 💬 QUẢN LÝ PHÒNG CHAT AI")

    if sb.button("➕ Tạo trang chat mới", use_container_width=True, type="primary"):
        pages = sb.session_state[pages_key]
        new_page_name = next_page_name(pages)
        pages[new_page_name] = []
        upload_single_page_supabase(u_id, new_page_name, [])
        sb.session_state[active_page_key] = new_page_name
        sb.rerun()

    page_options = list(sb.session_state[pages_key].keys())
    selected_page = sb.selectbox(
        "Chọn trang hội thoại đang xem:",
        page_options,
        index=page_options.index(current_page),
    )
    if selected_page != current_page:
        sb.session_state[active_page_key] = selected_page
        sb.rerun()

    rename_page_key = f"rename_mode_{u_id}"
    if rename_page_key not in sb.session_state:
        sb.session_state[rename_page_key] = False

    if not sb.session_state[rename_page_key]:
        if sb.button("✏️ Đổi tên trang này", use_container_width=True):
            sb.session_state[rename_page_key] = True
            sb.rerun()
    else:
        new_title = sb.text_input("Nhập tên mới:", value=current_page).strip()
        col_r1, col_r2 = sb.columns(2)
        with col_r1:
            if sb.button("✅ Lưu tên", use_container_width=True, type="primary"):
                if not new_title:
                    sb.warning("Tên trang không được để trống.")
                elif new_title == current_page:
                    sb.session_state[rename_page_key] = False
                    sb.rerun()
                elif new_title in sb.session_state[pages_key]:
                    sb.error("❌ Tên trang đã tồn tại.")
                else:
                    old_history = sb.session_state[pages_key][current_page]
                    try:
                        supabase.table("chat_histories").delete().eq("username", u_id).eq(
                            "page_name", current_page
                        ).execute()
                        upload_single_page_supabase(u_id, new_title, old_history)
                        sb.session_state[pages_key][new_title] = sb.session_state[pages_key].pop(current_page)
                        sb.session_state[active_page_key] = new_title
                        sb.session_state.pop(f"ai_session_{u_id}_{current_page}", None)
                    except Exception as exc:
                        sb.error(f"❌ Không đổi được tên trang: {safe_error_message(exc)}")
                    sb.session_state[rename_page_key] = False
                    sb.rerun()
        with col_r2:
            if sb.button("❌ Hủy", use_container_width=True):
                sb.session_state[rename_page_key] = False
                sb.rerun()

    sb.markdown("---")
    sb.markdown("### 🎵 NHẠC CHILL THƯ GIÃN")
    LOFI_URL = "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3"
    sb.markdown("☕ **Lofi Study Chill**")
    sb.audio(LOFI_URL, format="audio/mp3", loop=True)

    sb.markdown("---")
    sb.markdown("### ⚙️ CÀI ĐẶT CHATBOT")
    creativity = sb.slider(
        "🧠 Độ nhạy bén / Sáng tạo",
        min_value=0.1,
        max_value=1.0,
        value=0.3,
        step=0.1,
    )

    sb.markdown("---")
    sb.markdown("### 📸 PHÂN TÍCH HÌNH ẢNH")
    uploaded_file = sb.file_uploader(
        "Tải ảnh lên tại đây...",
        type=["png", "jpg", "jpeg", "webp"],
    )
    if uploaded_file:
        try:
            preview = Image.open(uploaded_file)
            sb.image(preview, caption="Ảnh đã chọn", use_container_width=True)
        except Exception:
            sb.error("❌ File ảnh không hợp lệ.")
            uploaded_file = None

    sb.markdown("---")
    sb.markdown("### 📂 NHẬT KÝ TRANG HIỆN TẠI")
    col1, col2 = sb.columns(2)
    with col1:
        if sb.button("🗑 Dọn tin", use_container_width=True):
            sb.session_state[pages_key][current_page] = []
            upload_single_page_supabase(u_id, current_page, [])
            sb.session_state.pop(f"ai_session_{u_id}_{current_page}", None)
            sb.rerun()

    with col2:
        if len(page_options) > 1:
            if sb.button("❌ Xóa trang", use_container_width=True):
                try:
                    supabase.table("chat_histories").delete().eq("username", u_id).eq(
                        "page_name", current_page
                    ).execute()
                    del sb.session_state[pages_key][current_page]
                    sb.session_state[active_page_key] = list(sb.session_state[pages_key].keys())[-1]
                    sb.session_state.pop(f"ai_session_{u_id}_{current_page}", None)
                    sb.rerun()
                except Exception as exc:
                    sb.error(f"❌ Không xóa được trang: {safe_error_message(exc)}")
        else:
            sb.caption("🔒 Giữ lại 1 trang.")

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
# TITLE (GRADIENT & PHƯỢNG HOÀNG 🐦‍🔥)
# ============================================================
sb.markdown(
    """
    <div class="premium-title-container">
        <span class="premium-logo">🐦‍🔥</span>
        <span class="premium-gradient-text">TRỢ LÝ AI TRA CỨU INTERNET</span>
    </div>
    <div class="sub-title">🚀 Phiên bản chatbot thông minh chạy trên máy chủ độc lập Streamlit Cloud v2026</div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# TABS CHÍNH
# ============================================================
tab_ai, tab_public, tab_dm = sb.tabs([
    "🤖 Chat Với AI", 
    "💬 Chat Cộng Đồng",
    "🔒 Tin Nhắn Riêng Tư (Zalo Style)"
])

# ------------------------------------------------------------
# TAB 1: CHAT VỚI AI
# ------------------------------------------------------------
with tab_ai:
    # 1. Lịch sử tin nhắn được render ở trên (Streamlit tự động ghim `st.chat_input` xuống dưới cùng màn hình)
    for message in sb.session_state[pages_key][current_page]:
        current_avatar = avatar_url if message["role"] == "user" else AI_AVATAR_EMOJI
        with sb.chat_message(message["role"], avatar=current_avatar):
            sb.markdown(message["content"])

    # 2. Thanh nhập câu hỏi chuẩn chat_input tự động bám đáy
    if user_input := sb.chat_input("Nhập câu hỏi của bạn vào đây..."):
        user_input = user_input.strip()
        if not user_input:
            sb.stop()

        current_history = sb.session_state[pages_key][current_page]
        current_history.append({"role": "user", "content": user_input})

        with sb.chat_message("user", avatar=avatar_url):
            sb.markdown(user_input)

        cache_hit = False
        cached_answer = ""

        if not uploaded_file and sb.session_state[cache_key]:
            current_embedding = get_embedding(user_input)
            if current_embedding is not None:
                best_score = -1.0
                best_match = None
                for item in sb.session_state[cache_key]:
                    score = cosine_similarity(current_embedding, item.get("embedding"))
                    if score > best_score:
                        best_score = score
                        best_match = item
                if best_match is not None and best_score >= CACHE_THRESHOLD:
                    cache_hit = True
                    cached_answer = best_match["answer"]

        if cache_hit:
            with sb.chat_message("assistant", avatar=AI_AVATAR_EMOJI):
                sb.markdown(cached_answer)
                sb.caption(f"⚡ Phản hồi từ semantic cache ({CACHE_THRESHOLD:.2f})")

            current_history.append({"role": "assistant", "content": cached_answer})
            upload_single_page_supabase(u_id, current_page, current_history)
            sb.stop()

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
            with sb.status("🔍 Đang tra cứu thông tin thực tế...", expanded=False) as status:
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

        with sb.chat_message("assistant", avatar=AI_AVATAR_EMOJI):
            try:
                config = types.GenerateContentConfig(
                    temperature=float(creativity),
                )

                if uploaded_file:
                    uploaded_file.seek(0)
                    image = Image.open(uploaded_file).convert("RGB")
                    response_stream = sb.session_state.ai_client.models.generate_content_stream(
                        model=AI_MODEL,
                        contents=[image, prompt_payload],
                        config=config,
                    )
                else:
                    chat_session_key = f"ai_session_{u_id}_{current_page}"
                    if chat_session_key not in sb.session_state:
                        sb.session_state[chat_session_key] = sb.session_state.ai_client.chats.create(
                            model=AI_MODEL,
                            config=config,
                        )
                    response_stream = sb.session_state[chat_session_key].send_message_stream(
                        message=prompt_payload,
                        config=config,
                    )

                def response_generator():
                    for chunk in response_stream:
                        text = getattr(chunk, "text", None)
                        if text:
                            yield text

                ai_response = sb.write_stream(response_generator())
                ai_response = ai_response if isinstance(ai_response, str) else str(ai_response or "")

                if not ai_response.strip():
                    ai_response = "⚠️ AI không trả về nội dung. Bạn hãy thử lại."
                    sb.warning(ai_response)

                if sources:
                    source_text = "\n\n---\n🌐 **Nguồn tham khảo:**\n" + "\n".join(
                        f"- {src}" for src in sources
                    )
                    sb.markdown(source_text)
                    ai_response += source_text

                current_history.append({"role": "assistant", "content": ai_response})
                upload_single_page_supabase(u_id, current_page, current_history)

                if not uploaded_file and not sources:
                    new_embedding = get_embedding(user_input)
                    if new_embedding is not None:
                        sb.session_state[cache_key].append({
                            "embedding": new_embedding,
                            "question": user_input,
                            "answer": ai_response,
                            "created_at": time.time(),
                        })
                        sb.session_state[cache_key] = sb.session_state[cache_key][-100:]

            except Exception as exc:
                error_text = safe_error_message(exc)
                error_message = f"❌ Hệ thống AI gặp lỗi: {error_text}"
                sb.error(error_message)
                if current_history and current_history[-1].get("role") == "user":
                    current_history.pop()

# ------------------------------------------------------------
# TAB 2: CHAT CỘNG ĐỒNG
# ------------------------------------------------------------
with tab_public:
    sb.caption("💬 Khung chat chung (Tự động xóa tin nhắn sau 10 phút). Nhấn nút 'Làm mới' để cập nhật tin nhắn mới nhất.")

    col_btn_refresh1, col_btn_clear1 = sb.columns([1, 1])
    with col_btn_refresh1:
        if sb.button("🔄 Làm mới tin nhắn cộng đồng", use_container_width=True):
            sb.rerun()
    with col_btn_clear1:
        if sb.button("🗑️ Xóa lịch sử hiển thị của tôi", use_container_width=True, type="secondary"):
            try:
                res_all = supabase.table("public_messages").select("id").execute()
                if res_all.data:
                    for msg_item in res_all.data:
                        sb.session_state[hidden_public_msgs_key].add(msg_item.get("id"))
                sb.success("✅ Đã xóa sạch lịch sử chat phía giao diện của bạn.")
                sb.rerun()
            except Exception as exc:
                sb.error(f"❌ Không thể thực hiện: {safe_error_message(exc)}")

    try:
        ten_mins_ago = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        supabase.table("public_messages").delete().lt("created_at", ten_mins_ago).execute()
    except Exception:
        pass

    with sb.form("public_chat_form", clear_on_submit=True):
        pub_msg = sb.text_input("Viết tin nhắn gửi tới mọi người...", key="pub_input")
        send_btn = sb.form_submit_button("🚀 Gửi Tin Nhắn", type="primary")
        if send_btn and pub_msg.strip():
            try:
                supabase.table("public_messages").insert({
                    "username": display_name,
                    "message": pub_msg.strip(),
                    "avatar_url": avatar_url,
                }).execute()
                sb.rerun()
            except Exception as exc:
                sb.error(f"❌ Không gửi được tin nhắn: {safe_error_message(exc)}")

    sb.markdown("---")
    
    try:
        res_pub = (
            supabase.table("public_messages")
            .select("*")
            .order("id", desc=True)
            .limit(40)
            .execute()
        )
        messages_list = res_pub.data or []
        
        visible_messages = [
            m for m in messages_list 
            if m.get("id") not in sb.session_state[hidden_public_msgs_key]
        ]

        if not visible_messages:
            sb.info("Chưa có tin nhắn nào hoặc bạn đã xóa toàn bộ hiển thị.")
        else:
            for item in visible_messages:
                msg_id = item.get("id")
                msg_user = item.get("username")
                time_str = item.get("created_at", "")[:16].replace("T", " ")
                item_avatar = item.get("avatar_url") or DEFAULT_AVATAR
                msg_text = item.get("message")

                col_msg, col_action = sb.columns([6, 1])
                with col_msg:
                    sb.markdown(
                        f"""
                        <div class="social-card" style="margin-bottom: 2px;">
                            <img src="{item_avatar}" class="user-avatar-img" />
                            <div style="flex-grow: 1;">
                                <span class="social-user">{msg_user}</span>
                                <span class="social-time">🕒 {time_str}</span>
                                <div style="margin-top: 4px; color: #334155;">{msg_text}</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col_action:
                    if msg_user == display_name:
                        if sb.button("Thu hồi", key=f"revoke_{msg_id}", help="Thu hồi tin nhắn này với mọi người"):
                            try:
                                supabase.table("public_messages").delete().eq("id", msg_id).execute()
                                sb.rerun()
                            except Exception as exc:
                                sb.error(f"Lỗi: {safe_error_message(exc)}")
                    else:
                        if sb.button("Ẩn", key=f"hide_{msg_id}", help="Ẩn tin nhắn này ở màn hình của bạn"):
                            sb.session_state[hidden_public_msgs_key].add(msg_id)
                            sb.rerun()

    except Exception as exc:
        sb.error(f"❌ Lỗi tải tin nhắn cộng đồng: {safe_error_message(exc)}")

# ------------------------------------------------------------
# TAB 3: TIN NHẮN RIÊNG 1-1 (ZALO STYLE & KẾT BẠN)
# ------------------------------------------------------------
with tab_dm:
    try:
        users_res = supabase.table("users").select("username, display_name, avatar_url").execute()
        all_users = users_res.data or []
        other_users = [u for u in all_users if u["username"] != u_id]
    except Exception:
        other_users = []

    try:
        friend_res = supabase.table("friendships").select("*").or_(f"sender.eq.{u_id},receiver.eq.{u_id}").execute()
        friendships_data = friend_res.data or []
    except Exception:
        friendships_data = []

    friend_list = []
    pending_requests = []
    sent_requests = []

    for f in friendships_data:
        s = f.get("sender")
        r = f.get("receiver")
        status = f.get("status")

        if status == "accepted":
            if s == u_id:
                friend_list.append(r)
            else:
                friend_list.append(s)
        elif status == "pending":
            if r == u_id:
                pending_requests.append((f.get("id"), s))
            elif s == u_id:
                sent_requests.append(r)

    sub_tab_chat, sub_tab_contacts = sb.tabs(["💬 Trò Chuyện", "👥 Danh Bạ & Kết Bạn"])

    with sub_tab_contacts:
        sb.markdown("#### 📥 Lời mời kết bạn chờ duyệt")
        if not pending_requests:
            sb.caption("Không có lời mời kết bạn nào đang chờ.")
        else:
            for req_id, sender_username in pending_requests:
                sender_info = next((u for u in other_users if u["username"] == sender_username), {"display_name": sender_username, "avatar_url": DEFAULT_AVATAR})
                s_name = sender_info.get("display_name") or sender_username
                s_ava = sender_info.get("avatar_url") or DEFAULT_AVATAR

                c1, c2, c3 = sb.columns([3, 1, 1])
                with c1:
                    sb.markdown(
                        f"""
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <img src="{s_ava}" style="width: 35px; height: 35px; border-radius: 50%; object-fit: cover;" />
                            <b>{s_name}</b> muốn kết bạn với bạn.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with c2:
                    if sb.button("Đồng ý", key=f"accept_{req_id}", type="primary", use_container_width=True):
                        try:
                            supabase.table("friendships").update({"status": "accepted"}).eq("id", req_id).execute()
                            sb.success("✅ Đã chấp nhận kết bạn!")
                            sb.rerun()
                        except Exception as exc:
                            sb.error(f"Lỗi: {safe_error_message(exc)}")
                with c3:
                    if sb.button("Từ chối", key=f"reject_{req_id}", use_container_width=True):
                        try:
                            supabase.table("friendships").delete().eq("id", req_id).execute()
                            sb.info("Đã từ chối lời mời.")
                            sb.rerun()
                        except Exception as exc:
                            sb.error(f"Lỗi: {safe_error_message(exc)}")

        sb.markdown("---")
        sb.markdown("#### 🔍 Tìm kiếm người dùng & Kết bạn")
        search_query = sb.text_input("Nhập tên đăng nhập hoặc tên hiển thị để tìm kiếm:", key="search_user_input").strip()

        if search_query:
            matched_users = [
                u for u in other_users 
                if search_query.lower() in u["username"].lower() or search_query.lower() in u.get("display_name", "").lower()
            ]
            if not matched_users:
                sb.info("Không tìm thấy người dùng phù hợp.")
            else:
                for mu in matched_users:
                    mu_username = mu["username"]
                    mu_dname = mu.get("display_name") or mu_username
                    mu_ava = mu.get("avatar_url") or DEFAULT_AVATAR

                    is_friend = mu_username in friend_list
                    is_sent_pending = mu_username in sent_requests

                    c_u1, c_u2 = sb.columns([4, 2])
                    with c_u1:
                        sb.markdown(
                            f"""
                            <div style="display: flex; align-items: center; gap: 10px; padding: 6px 0;">
                                <img src="{mu_ava}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover;" />
                                <div>
                                    <div style="font-weight: 700;">{mu_dname}</div>
                                    <div style="font-size: 0.8rem; color: #64748B;">@{mu_username}</div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with c_u2:
                        sb.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
                        if is_friend:
                            sb.markdown("✅ **Đã là bạn bè**")
                        elif is_sent_pending:
                            sb.markdown("⏳ **Đã gửi lời mời**")
                        else:
                            if sb.button("➕ Kết bạn", key=f"add_friend_{mu_username}", type="primary"):
                                try:
                                    supabase.table("friendships").insert({
                                        "sender": u_id,
                                        "receiver": mu_username,
                                        "status": "pending"
                                    }).execute()
                                    sb.success("Đã gửi lời mời kết bạn!")
                                    sb.rerun()
                                except Exception as exc:
                                    sb.error(f"Lỗi: {safe_error_message(exc)}")

    with sub_tab_chat:
        if not friend_list:
            sb.info("📭 Danh sách bạn bè trống. Hãy sang tab **'Danh Bạ & Kết Bạn'** để tìm và kết bạn với người khác trước khi nhắn tin!")
        else:
            friend_options = {
                (next((u.get("display_name") or u["username"] for u in other_users if u["username"] == f), f)): f 
                for f in friend_list
            }
            selected_dname = sb.selectbox("Chọn bạn bè để trò chuyện:", list(friend_options.keys()), key="select_friend_chat")
            selected_receiver = friend_options[selected_dname]

            sb.markdown("---")

            receiver_info = next((u for u in other_users if u["username"] == selected_receiver), {"display_name": selected_receiver, "avatar_url": DEFAULT_AVATAR})
            rec_dname = receiver_info.get("display_name") or selected_receiver
            rec_ava = receiver_info.get("avatar_url") or DEFAULT_AVATAR

            sb.markdown(
                f"""
                <div style="display: flex; align-items: center; gap: 12px; padding: 10px 14px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.02);">
                    <img src="{rec_ava}" style="width: 45px; height: 45px; border-radius: 50%; object-fit: cover; border: 2px solid #0068FF;" />
                    <div>
                        <div style="font-weight: 700; color: #0F172A; font-size: 1.05rem;">{rec_dname}</div>
                        <div style="font-size: 0.8rem; color: #10B981;">● Bạn bè</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            chat_container = sb.container(height=400)
            with chat_container:
                try:
                    res_dm = (
                        supabase.table("private_messages")
                        .select("*")
                        .or_(f"sender.eq.{u_id},receiver.eq.{u_id}")
                        .order("created_at", desc=False)
                        .execute()
                    )
                    raw_dm_list = res_dm.data or []
                    
                    dm_list = [
                        m for m in raw_dm_list 
                        if (m.get("sender") == u_id and m.get("receiver") == selected_receiver) or 
                           (m.get("sender") == selected_receiver and m.get("receiver") == u_id)
                    ]

                    if not dm_list:
                        sb.info(f"Chưa có tin nhắn nào với {rec_dname}. Hãy gửi lời chào đầu tiên!")
                    else:
                        for msg in dm_list:
                            m_sender = msg.get("sender")
                            m_text = msg.get("message")
                            m_time = msg.get("created_at", "")[11:16]
                            m_avatar = msg.get("avatar_url") or DEFAULT_AVATAR

                            is_me = (m_sender == u_id)
                            flex_dir = "row-reverse" if is_me else "row"
                            bg_bubble = "#0068FF" if is_me else "#E4E6EB"
                            text_color = "#FFFFFF" if is_me else "#050505"
                            align_text = "right" if is_me else "left"

                            sb.markdown(
                                f"""
                                <div style="display: flex; flex-direction: {flex_dir}; gap: 8px; margin-bottom: 10px; align-items: flex-end;">
                                    <img src="{m_avatar}" style="width: 30px; height: 30px; border-radius: 50%; object-fit: cover;" />
                                    <div style="max-width: 65%;">
                                        <div style="background: {bg_bubble}; color: {text_color}; padding: 10px 14px; border-radius: 18px; font-size: 0.95rem; word-break: break-word; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                                            {m_text}
                                        </div>
                                        <div style="font-size: 0.7rem; color: #94A3B8; margin-top: 2px; text-align: {align_text};">{m_time}</div>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                except Exception as exc:
                    sb.error(f"❌ Lỗi tải tin nhắn: {safe_error_message(exc)}")

            input_key = f"widget_dm_input_{selected_receiver}"
            if input_key not in sb.session_state:
                sb.session_state[input_key] = ""

            def submit_dm_action():
                val = sb.session_state.get(input_key, "").strip()
                if val:
                    try:
                        supabase.table("private_messages").insert({
                            "sender": u_id,
                            "receiver": selected_receiver,
                            "message": val,
                            "avatar_url": avatar_url,
                        }).execute()
                        sb.session_state[input_key] = ""
                    except Exception as exc:
                        sb.error(f"❌ Không gửi được: {safe_error_message(exc)}")

            with sb.form(key=f"dm_form_{selected_receiver}", clear_on_submit=True):
                col_input, col_refresh, col_send = sb.columns([4, 1, 1])
                with col_input:
                    sb.text_input(
                        "Nhập tin nhắn...", 
                        placeholder=f"Nhắn gì đó cho {rec_dname}...", 
                        label_visibility="collapsed",
                        key=input_key
                    )
                with col_refresh:
                    sb.markdown("<div style='height: 2px;'></div>", unsafe_allow_html=True)
                    refresh_btn = sb.form_submit_button("🔄 Tải lại", use_container_width=True)
                with col_send:
                    sb.markdown("<div style='height: 2px;'></div>", unsafe_allow_html=True)
                    dm_send_btn = sb.form_submit_button("Gửi ➔", use_container_width=True, type="primary", on_click=submit_dm_action)

                if refresh_btn:
                    sb.rerun()
