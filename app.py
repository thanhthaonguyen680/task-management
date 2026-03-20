# ============================================================
# app.py - Ứng dụng Quản Lý Công Việc
# Sử dụng: Streamlit + Google Sheets (gspread) + Cloudinary + FPDF
# ============================================================

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import cloudinary
import cloudinary.uploader
import uuid
from fpdf import FPDF
import pandas as pd
from datetime import datetime, timedelta
import requests
import tempfile
import os
import json
import hashlib

# ============================================================
# TẢI FONT UNICODE HỖ TRỢ TIẾNG VIỆT
# ============================================================
FONT_DIR   = os.path.join(os.path.dirname(__file__), "fonts")
FONT_REGULAR = os.path.join(FONT_DIR, "DejaVuSans.ttf")
FONT_BOLD    = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")

def _tai_font_neu_chua_co():
    """
    Tự động tải font DejaVuSans về thư mục fonts/ nếu chưa có.
    Dùng jsDelivr CDN để đảm bảo tải đúng file binary TTF.
    """
    os.makedirs(FONT_DIR, exist_ok=True)
    urls = {
        FONT_REGULAR: "https://cdn.jsdelivr.net/npm/dejavu-fonts-ttf@2.37.3/ttf/DejaVuSans.ttf",
        FONT_BOLD:    "https://cdn.jsdelivr.net/npm/dejavu-fonts-ttf@2.37.3/ttf/DejaVuSans-Bold.ttf",
    }
    for duong_dan, url in urls.items():
        if not os.path.exists(duong_dan):
            phan_hoi = requests.get(url, timeout=30)
            phan_hoi.raise_for_status()
            with open(duong_dan, "wb") as f:
                f.write(phan_hoi.content)

# Tải font ngay khi khởi động (chỉ chạy 1 lần vì Streamlit cache module)
_tai_font_neu_chua_co()

# ============================================================
# CẤU HÌNH TRANG ỨNG DỤNG
# ============================================================
st.set_page_config(
    page_title="Quản Lý Công Việc",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS ẩn toolbar + avatar badge trong iframe app
st.markdown(
    """
    <style>
    /* ẩn toolbar Streamlit */
    [data-testid="stToolbar"]      { display: none !important; visibility: hidden !important; }
    [data-testid="stDecoration"]   { display: none !important; visibility: hidden !important; }
    /* ẩn status widget / avatar badge */
    [data-testid="stStatusWidget"] { display: none !important; visibility: hidden !important; }
    [data-testid="stBottom"]       { display: none !important; visibility: hidden !important; }
    /* ẩn theo class name (phòng trường hợp testid thay đổi) */
    [class*="viewerBadge"]         { display: none !important; visibility: hidden !important; }
    [class*="ViewerBadge"]         { display: none !important; visibility: hidden !important; }
    [class*="StatusWidget"]        { display: none !important; visibility: hidden !important; }
    [class*="statusWidget"]        { display: none !important; visibility: hidden !important; }
    [class*="createdBy"]           { display: none !important; visibility: hidden !important; }
    [class*="CreatedBy"]           { display: none !important; visibility: hidden !important; }
    [class*="deployButton"]        { display: none !important; visibility: hidden !important; }
    [class*="manage"]              { display: none !important; visibility: hidden !important; }
    footer                         { display: none !important; visibility: hidden !important; }
    /* ẩn ảnh tròn cứng */
    img[style*="border-radius: 50"] { display: none !important; visibility: hidden !important; }
    img[style*="border-radius:50"]  { display: none !important; visibility: hidden !important; }
    /* ẩn fixed bottom-right badge/avatar */
    iframe[style*="position: fixed"] { display: none !important; }
    iframe[style*="position:fixed"]  { display: none !important; }
    div[style*="position: fixed"][style*="bottom"] img { display: none !important; }
    [class*="badge"], [class*="Badge"], [class*="avatar"], [class*="Avatar"] {
        display: none !important; visibility: hidden !important;
    }
    /* Giảm font placeholder toàn app */
    input::placeholder, textarea::placeholder {
        font-size: 0.78rem !important;
    }
    /* Selectbox: cho text đã chọn xuống hàng, giữ nguyên input */
    /* Control wrapper */
    [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        height: auto !important;
        min-height: 38px !important;
    }
    /* Selected value: div trực tiếp bên trong ValueContainer không phải input */
    /* Baseweb structure: select > div(control) > div(ValueContainer) > div(singleValue) + div(input) */
    [data-testid="stSelectbox"] [data-baseweb="select"] > div > div > div:not([data-testid]) {
        font-size: 0.72rem !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        max-width: calc(100% - 28px) !important;
        direction: rtl !important;
        text-align: left !important;
    }
    /* Class-based fallback */
    [data-testid="stSelectbox"] div[class*="singleValue"],
    [data-testid="stSelectbox"] div[class*="SingleValue"],
    [data-testid="stSelectbox"] div[class*="single-value"] {
        font-size: 0.72rem !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        max-width: calc(100% - 28px) !important;
        direction: rtl !important;
        text-align: left !important;
    }
    /* Dropdown options — cho xuống hàng thay vì cắt ... */
    [data-baseweb="menu"] li,
    [data-baseweb="menu"] [role="option"],
    [data-baseweb="popover"] li,
    [data-baseweb="popover"] [role="option"],
    [role="listbox"] [role="option"],
    ul[data-baseweb="menu"] li,
    [data-baseweb="select-dropdown"] li,
    [data-baseweb="select-dropdown"] [role="option"] {
        white-space: normal !important;
        word-break: break-word !important;
        overflow: visible !important;
        text-overflow: unset !important;
        font-size: 0.72rem !important;
        line-height: 1.3 !important;
        height: auto !important;
        min-height: 32px !important;
        max-height: none !important;
        padding-top: 5px !important;
        padding-bottom: 5px !important;
    }
    /* Tất cả con cháu bên trong option: override bất kỳ inline style nào */
    [data-baseweb="menu"] li *,
    [data-baseweb="menu"] [role="option"] *,
    [role="listbox"] [role="option"] * {
        white-space: normal !important;
        word-break: break-word !important;
        overflow: visible !important;
        text-overflow: unset !important;
        line-height: 1.3 !important;
        max-width: 100% !important;
        font-size: 0.72rem !important;
    }
    /* Span/div text bên trong option cũng cần wrap */
    [data-baseweb="menu"] li span,
    [data-baseweb="menu"] li div,
    [role="listbox"] [role="option"] span,
    [role="listbox"] [role="option"] div {
        white-space: normal !important;
        word-break: break-word !important;
        overflow: visible !important;
        text-overflow: unset !important;
    }
    /* Thêm padding-bottom trên mobile để nội dung không bị avatar badge che khuất */
    @media (max-width: 768px) {
        .main .block-container {
            padding-bottom: 2rem !important;
        }
        section[data-testid="stMain"] > div {
            padding-bottom: 2rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# JS inject CSS vào tất cả frames có thể truy cập
import streamlit.components.v1 as components
components.html(
    """
    <script>
    var HIDE = [
        '[data-testid="stStatusWidget"]',
        '[data-testid="stBottom"]',
        '[data-testid="stDeployButton"]',
        '[data-testid="manage-app-button"]',
        '[data-testid="stToolbar"]',
        '[class*="StatusWidget"]',
        '[class*="statusWidget"]',
        '[class*="viewerBadge"]',
        '[class*="ViewerBadge"]',
        '[class*="deployButton"]',
        '[class*="createdBy"]',
        '[class*="CreatedBy"]',
        'footer',
        'img[style*="border-radius: 50"]',
        'img[style*="border-radius:50"]',
        '[class*="badge"]',
        '[class*="Badge"]',
        '[class*="avatar"]',
        '[class*="Avatar"]',
        'iframe[style*="position: fixed"]',
        'iframe[style*="position:fixed"]',
    ];
    var CSS_RULES = HIDE.map(function(s){ return s+'{display:none!important;visibility:hidden!important}'; }).join('');

    // CSS cho dropdown options wrap 2 hàng (inject vào body vì portal render ngoài DOM chính)
    var DROPDOWN_CSS = [
        '[data-baseweb="menu"] li { white-space:normal!important; word-break:break-word!important; overflow:visible!important; text-overflow:unset!important; height:auto!important; min-height:32px!important; max-height:none!important; padding:5px 10px!important; line-height:1.3!important; font-size:0.72rem!important; }',
        '[data-baseweb="menu"] li * { white-space:normal!important; word-break:break-word!important; overflow:visible!important; text-overflow:unset!important; line-height:1.3!important; max-width:100%!important; font-size:0.72rem!important; }',  
        '[data-baseweb="menu"] li span, [data-baseweb="menu"] li div { white-space:normal!important; word-break:break-word!important; overflow:visible!important; text-overflow:unset!important; }',
        '[role="option"] { white-space:normal!important; word-break:break-word!important; height:auto!important; max-height:none!important; overflow:visible!important; }',
        '[role="option"] * { white-space:normal!important; word-break:break-word!important; overflow:visible!important; text-overflow:unset!important; }',
        '[role="listbox"] { overflow-y:auto!important; }',
        '[data-testid="stSelectbox"] [data-baseweb="select"] [class*="singleValue"] { font-size:0.72rem!important; white-space:nowrap!important; overflow:hidden!important; text-overflow:ellipsis!important; max-width:calc(100% - 28px)!important; }',
        '[data-testid="stSelectbox"] [data-baseweb="select"] [class*="SingleValue"] { font-size:0.72rem!important; white-space:nowrap!important; overflow:hidden!important; text-overflow:ellipsis!important; max-width:calc(100% - 28px)!important; }',
    ].join('');

    function injectCSS(doc) {
        try {
            var id = '__st_hide_v2';
            var existing = doc.getElementById(id);
            if (existing) return;
            var s = doc.createElement('style');
            s.id = id;
            s.textContent = CSS_RULES + DROPDOWN_CSS;
            (doc.head || doc.documentElement).appendChild(s);
        } catch(e) {}
    }

    // Kiểm tra element có nằm trong row công việc con không (marker class "dlgcv...")
    function isInsideCvCmRow(el) {
        try {
            var block = el.closest('[data-testid="stHorizontalBlock"]');
            if (!block) return false;
            return !!block.querySelector('[class*="dlgcv"]');
        } catch(e) { return false; }
    }

    // Fix selectbox NV trong công việc con: bỏ overflow/clip, direction ltr
    function fixCvCmSelectboxes(doc) {
        try {
            doc.querySelectorAll('[data-testid="stHorizontalBlock"]').forEach(function(block) {
                if (!block.querySelector('[class*="dlgcv"]')) return;
                // Tìm tất cả selectbox trong row này
                block.querySelectorAll('[data-testid="stSelectbox"] [data-baseweb="select"]').forEach(function(sel) {
                    // Fix toàn bộ children trực tiếp của baseweb select
                    sel.querySelectorAll('div').forEach(function(div) {
                        div.style.setProperty('overflow', 'visible', 'important');
                        div.style.setProperty('text-overflow', 'clip', 'important');
                        div.style.setProperty('max-width', 'none', 'important');
                        div.style.setProperty('white-space', 'nowrap', 'important');
                        div.style.setProperty('direction', 'ltr', 'important');
                    });
                });
            });
        } catch(e) {}
    }

    // Set font-size nhỏ trực tiếp lên singleValue div (override baseweb inline style)
    function fixSelectedValue(doc) {
        try {
            var sels = [
                '[data-testid="stSelectbox"] [data-baseweb="select"] [class*="singleValue"]',
                '[data-testid="stSelectbox"] [data-baseweb="select"] [class*="SingleValue"]',
            ];
            sels.forEach(function(sel) {
                doc.querySelectorAll(sel).forEach(function(el) {
                    // Bỏ qua NV selectbox trong rows công việc con (hàng 1 layout)
                    if (isInsideCvCmRow(el)) return;
                    // Nhận diện selectbox nhân viên qua wrapper class hoặc label text
                    var stBox = el.closest('[data-testid="stSelectbox"]');
                    var isNvBox = false;
                    if (stBox) {
                        // Kiểm tra wrapper div cv-nv-frag- hoặc cv-nv-row-
                        var wrap = stBox.parentElement;
                        while (wrap) {
                            if (wrap.className && typeof wrap.className === 'string' &&
                                (wrap.className.indexOf('cv-nv-frag-') !== -1 ||
                                 wrap.className.indexOf('cv-nv-row-') !== -1)) {
                                isNvBox = true; break;
                            }
                            if (wrap === doc.body) break;
                            wrap = wrap.parentElement;
                        }
                        // Fallback: kiểm tra label text
                        if (!isNvBox) {
                            var lbl = stBox.querySelector('label');
                            if (lbl && lbl.textContent && lbl.textContent.indexOf('Nh\u00e2n vi\u00ean') !== -1) {
                                isNvBox = true;
                            }
                        }
                    }
                    if (isNvBox) {
                        el.style.setProperty('direction', 'ltr', 'important');
                        el.style.setProperty('overflow', 'visible', 'important');
                        el.style.setProperty('text-overflow', 'clip', 'important');
                        el.style.setProperty('max-width', 'none', 'important');
                        el.style.setProperty('white-space', 'nowrap', 'important');
                        el.style.setProperty('font-size', '0.9rem', 'important');
                        return;
                    }
                    el.style.setProperty('font-size', '0.72rem', 'important');
                    el.style.setProperty('white-space', 'nowrap', 'important');
                    el.style.setProperty('overflow', 'hidden', 'important');
                    el.style.setProperty('text-overflow', 'ellipsis', 'important');
                    el.style.setProperty('max-width', 'calc(100% - 28px)', 'important');
                });
            });
        } catch(e) {}
    }

    // Fix inline styles trên dropdown option items (baseweb dùng inline style vượt qua CSS !important)
    // Chỉ fix trực tiếp li/option và direct children — không đụng input, không querySelectorAll('*')
    function fixDropdownOptions(doc) {
        try {
            // Không chạy khi user đang gõ/xóa trong search input của selectbox
            try {
                var ae = doc.activeElement;
                if (ae && ae.tagName && ae.tagName.toLowerCase() === 'input') return;
                // Kiểm tra window.parent nếu đây là iframe doc
                var pae = window.parent && window.parent.document && window.parent.document.activeElement;
                if (pae && pae.tagName && pae.tagName.toLowerCase() === 'input') return;
            } catch(e) {}
            var sels = [
                '[data-baseweb="menu"] li',
                '[data-baseweb="menu"] [role="option"]',
                '[role="listbox"] [role="option"]',
            ];
            sels.forEach(function(sel) {
                doc.querySelectorAll(sel).forEach(function(el) {
                    el.style.setProperty('white-space', 'normal', 'important');
                    el.style.setProperty('word-break', 'break-word', 'important');
                    el.style.setProperty('overflow', 'visible', 'important');
                    el.style.setProperty('text-overflow', 'unset', 'important');
                    el.style.setProperty('height', 'auto', 'important');
                    el.style.setProperty('max-height', 'none', 'important');
                    el.style.setProperty('font-size', '0.72rem', 'important');
                    el.style.setProperty('line-height', '1.3', 'important');
                    el.style.setProperty('min-height', '28px', 'important');
                    // Chỉ fix direct children (không phải input)
                    for (var i = 0; i < el.children.length; i++) {
                        var child = el.children[i];
                        if (child.tagName && child.tagName.toLowerCase() !== 'input') {
                            child.style.setProperty('white-space', 'normal', 'important');
                            child.style.setProperty('word-break', 'break-word', 'important');
                            child.style.setProperty('overflow', 'visible', 'important');
                            child.style.setProperty('text-overflow', 'unset', 'important');
                            child.style.setProperty('max-width', '100%', 'important');
                            child.style.setProperty('font-size', '0.72rem', 'important');
                        }
                    }
                });
            });
        } catch(e) {}
    }

    function hideElements(doc) {
        try {
            HIDE.forEach(function(sel) {
                try {
                    doc.querySelectorAll(sel).forEach(function(el) {
                        el.style.setProperty('display', 'none', 'important');
                        el.style.setProperty('visibility', 'hidden', 'important');
                    });
                } catch(e) {}
            });
        } catch(e) {}
    }

    // Thử inject vào window.top và tất cả ancestors
    var frames = [];
    try { frames.push(window.document); } catch(e) {}
    try { frames.push(window.parent.document); } catch(e) {}
    try { frames.push(window.parent.parent.document); } catch(e) {}
    try { frames.push(window.top.document); } catch(e) {}

    frames.forEach(function(doc) {
        injectCSS(doc);
        hideElements(doc);
        fixSelectedValue(doc);
        fixCvCmSelectboxes(doc);
    });

    // Chạy sớm sau khi DOM sẵn sàng
    setTimeout(function() {
        frames.forEach(function(doc) { fixSelectedValue(doc); fixCvCmSelectboxes(doc); });
    }, 100);
    setTimeout(function() {
        frames.forEach(function(doc) { fixSelectedValue(doc); fixCvCmSelectboxes(doc); });
    }, 500);

    // MutationObserver để bắt các element được thêm sau
    function observeDoc(doc) {
        try {
            var _fixTimer = null;
            var _menuPresent = false; // track xem menu đã có trong DOM chưa
            var obs = new MutationObserver(function(mutations) {
                injectCSS(doc);
                hideElements(doc);
                // Chỉ fix khi menu MỚI xuất hiện (không có → có)
                // Không chạy lại khi user gõ/xóa bên trong menu đang mở
                var menuNow = !!(doc.querySelector('[data-baseweb="menu"]') || doc.querySelector('[role="listbox"]'));
                if (menuNow && !_menuPresent) {
                    // Menu vừa mở ra → fix một lần sau 30ms
                    _menuPresent = true;
                    clearTimeout(_fixTimer);
                    _fixTimer = setTimeout(function() {
                        fixDropdownOptions(doc);
                        fixSelectedValue(doc);
                    }, 30);
                } else if (!menuNow && _menuPresent) {
                    _menuPresent = false;
                    // Menu vừa đóng → update selected value display
                    setTimeout(function() { fixSelectedValue(doc); fixCvCmSelectboxes(doc); }, 50);
                } else if (!menuNow) {
                    _menuPresent = false;
                }
            });
            obs.observe(doc.documentElement, { childList: true, subtree: true });
        } catch(e) {}
    }

    frames.forEach(function(doc) { observeDoc(doc); });

    // Chạy lại sau 1s và 3s phòng element load chậm
    [1000, 3000, 6000].forEach(function(delay) {
        setTimeout(function() {
            frames.forEach(function(doc) {
                injectCSS(doc);
                hideElements(doc);
                fixDropdownOptions(doc);
                fixSelectedValue(doc);
                fixCvCmSelectboxes(doc);
            });
        }, delay);
    });
    </script>
    """,
    height=1,
)


@st.cache_resource
def _session_store():
    """Lưu session token → thông tin user. Dùng cache_resource để chia sẻ giữa các session."""
    return {}


# ============================================================
# KẾT NỐI GOOGLE SHEETS
# ============================================================
def _xoa_cache_va_thong_bao(loi: Exception):
    """Xóa cache kết nối GSheets để lần sau tự reconnect, trả về thông báo lỗi."""
    for fn in [
        "ket_noi_google_sheets", "_lay_bang_tinh",
        "lay_sheet", "lay_sheet_cong_ty", "lay_sheet_users",
    ]:
        try:
            globals()[fn].clear()
        except Exception:
            pass
    return f"🔌 Mất kết nối mạng — Google Sheets không thể truy cập. Chi tiết: {type(loi).__name__}: {loi}"


@st.cache_resource
def ket_noi_google_sheets():
    """
    Kết nối với Google Sheets sử dụng Service Account Credentials.
    Dùng @st.cache_resource để chỉ kết nối một lần duy nhất.
    """
    pham_vi = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    # Lấy thông tin xác thực từ Streamlit Secrets (file .streamlit/secrets.toml)
    thong_tin_xac_thuc = st.secrets["gcp_service_account"]
    chung_chi = Credentials.from_service_account_info(thong_tin_xac_thuc, scopes=pham_vi)
    khach_hang = gspread.authorize(chung_chi)
    return khach_hang


@st.cache_resource
def _lay_bang_tinh():
    """Trả về đối tượng Spreadsheet, chỉ gọi open() một lần duy nhất."""
    return ket_noi_google_sheets().open("QuanLyCongViec")


@st.cache_resource
def lay_sheet():
    """
    Mở file 'QuanLyCongViec' trên Google Drive và trả về worksheet 'Tasks'.
    Dùng @st.cache_resource để chỉ mở một lần, tái sử dụng đối tượng sheet.
    """
    try:
        return _lay_bang_tinh().worksheet("Tasks")
    except Exception as e:
        raise ConnectionError(_xoa_cache_va_thong_bao(e)) from e


def _lay_sheet_fresh():
    """Lấy worksheet Tasks mới (không cache) — dùng cho các thao tác ghi."""
    try:
        pham_vi = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        thong_tin = st.secrets["gcp_service_account"]
        chung_chi = Credentials.from_service_account_info(thong_tin, scopes=pham_vi)
        gc = gspread.authorize(chung_chi)
        return gc.open("QuanLyCongViec").worksheet("Tasks")
    except Exception:
        # Fallback về cached sheet nếu kết nối mới thất bại
        return lay_sheet()


# ============================================================
# GOOGLE DRIVE (lưu trữ ảnh nghiệm thu) — dùng requests thay httplib2
# ============================================================
GDRIVE_FOLDER_ID = "1-o1gny8zFKQ5NejyUjeinLVdmDpKfWgH"
_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


def _lay_drive_session():
    """Tạo AuthorizedSession mới mỗi lần — dùng requests, không dùng httplib2."""
    from google.oauth2.service_account import Credentials as SACredentials
    from google.auth.transport.requests import AuthorizedSession
    try:
        info = dict(st.secrets["gdrive_service_account"])
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        creds = SACredentials.from_service_account_info(info, scopes=_DRIVE_SCOPES)
    except Exception:
        _base = os.path.dirname(os.path.abspath(__file__))
        creds = SACredentials.from_service_account_file(
            os.path.join(_base, "gdrive_key.json"), scopes=_DRIVE_SCOPES
        )
    return AuthorizedSession(creds)


def tai_anh_len_drive(file_anh) -> str:
    """Upload ảnh lên Google Drive qua requests, set public, trả về thumbnail URL."""
    import io, json as _json
    session = _lay_drive_session()
    file_anh.seek(0)
    content = file_anh.read()
    mime = getattr(file_anh, "type", "image/jpeg")
    name = getattr(file_anh, "name", "image.jpg")

    # Multipart upload trực tiếp — không qua httplib2
    metadata = _json.dumps({"name": name, "parents": [GDRIVE_FOLDER_ID]})
    resp = session.post(
        "https://www.googleapis.com/upload/drive/v3/files"
        "?uploadType=multipart&supportsAllDrives=true&fields=id",
        files={
            "metadata": ("metadata", metadata, "application/json; charset=UTF-8"),
            "file": (name, io.BytesIO(content), mime),
        },
        timeout=60,
    )
    if not resp.ok:
        st.error(f"Drive upload lỗi {resp.status_code}: {resp.text[:500]}")
        st.stop()
    file_id = resp.json()["id"]

    # Set public read
    session.post(
        f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions"
        "?supportsAllDrives=true",
        json={"type": "anyone", "role": "reader"},
        timeout=30,
    )
    # thumbnail URL — lưu vào DB, dùng file_id để fetch khi hiển thị
    return f"https://drive.google.com/thumbnail?id={file_id}&sz=w800"


@st.cache_data(ttl=3600)
def _lay_bytes_anh_drive(file_id: str) -> bytes:
    """Fetch bytes ảnh từ Drive qua service account (cache 1 giờ)."""
    session = _lay_drive_session()
    resp = session.get(
        f"https://www.googleapis.com/drive/v3/files/{file_id}"
        f"?alt=media&supportsAllDrives=true",
        timeout=30,
    )
    resp.raise_for_status()
    return resp.content


def _hien_thi_anh_drive(url: str, **kwargs):
    """Hiển thị ảnh Drive: fetch bytes qua service account thay vì URL trực tiếp."""
    import re
    m = re.search(r"[?&]id=([^&]+)", url)
    if m:
        try:
            data = _lay_bytes_anh_drive(m.group(1))
            st.image(data, **kwargs)
            return
        except Exception:
            pass
    st.image(url, **kwargs)


def cau_hinh_cloudinary():
    """Giữ lại để tương thích — không dùng nữa."""
    pass


def tai_anh_len_cloudinary(file_anh) -> str:
    """Wrapper gọi sang Drive (giữ tên cũ để không cần đổi call sites)."""
    return tai_anh_len_drive(file_anh)


def _tai_media_len_drive(file_obj) -> str:
    """Upload ảnh hoặc video lên Drive. Video → trả view URL; ảnh → thumbnail URL."""
    import re as _re
    url = tai_anh_len_drive(file_obj)
    mime = getattr(file_obj, "type", "")
    if mime.startswith("video/"):
        m = _re.search(r"[?&]id=([^&]+)", url)
        if m:
            return f"https://drive.google.com/file/d/{m.group(1)}/view"
    return url


# ============================================================
# CÁC HÀM THAO TÁC DỮ LIỆU GOOGLE SHEETS
# ============================================================
@st.cache_resource
def lay_sheet_cong_ty():
    """
    Mở sheet 'Companies' — nếu chưa tồn tại thì tự tạo mới.
    Cấu trúc: ID | Cong_Ty | Created_Date
    Dùng @st.cache_resource để tái sử dụng đối tượng sheet.
    """
    try:
        bang_tinh = _lay_bang_tinh()
        try:
            sheet = bang_tinh.worksheet("Companies")
        except gspread.exceptions.WorksheetNotFound:
            sheet = bang_tinh.add_worksheet(title="Companies", rows=200, cols=7)
            sheet.append_row(["ID", "Tên Công Ty", "Địa Chỉ", "Mã Khách Hàng", "Mã Số Thuế", "Ngày Tạo"])
            return sheet
        # Migration: thêm các cột mới nếu chưa có
        headers = sheet.row_values(1)
        if "Địa Chỉ" not in headers:
            sheet.insert_cols([["Địa Chỉ"]], col=3)
            headers = sheet.row_values(1)
        if "Mã Khách Hàng" not in headers:
            # Chèn trước "Ngày Tạo"
            ngay_col = headers.index("Ngày Tạo") + 1 if "Ngày Tạo" in headers else len(headers)
            sheet.insert_cols([["Mã Khách Hàng"]], col=ngay_col)
            headers = sheet.row_values(1)
        if "Mã Số Thuế" not in headers:
            ngay_col = headers.index("Ngày Tạo") + 1 if "Ngày Tạo" in headers else len(headers)
            sheet.insert_cols([["Mã Số Thuế"]], col=ngay_col)
        return sheet
    except (ConnectionError, OSError, Exception) as e:
        raise ConnectionError(_xoa_cache_va_thong_bao(e)) from e


@st.cache_data(ttl=60)
def lay_danh_sach_cong_ty() -> pd.DataFrame:
    """Lấy toàn bộ danh sách công ty từ sheet 'Companies'."""
    _COT = ["ID", "Tên Công Ty", "Địa Chỉ", "Mã Khách Hàng", "Mã Số Thuế", "Ngày Tạo"]
    try:
        sheet = lay_sheet_cong_ty()
    except ConnectionError:
        return pd.DataFrame(columns=_COT)
    try:
        allvals = sheet.get_all_values()
    except Exception as e:
        _xoa_cache_va_thong_bao(e)
        return pd.DataFrame(columns=_COT)
    if len(allvals) <= 1:
        return pd.DataFrame(columns=_COT)
    # Dùng header thực tế từ sheet
    actual_headers = [v.strip() for v in allvals[0]]
    rows = []
    for r in allvals[1:]:
        padded = (r + [""] * len(actual_headers))[:len(actual_headers)]
        if any(padded):
            rows.append(padded)
    df = pd.DataFrame(rows, columns=actual_headers)
    df.rename(columns={"Cong_Ty": "Tên Công Ty", "Created_Date": "Ngày Tạo"}, inplace=True)
    # Đảm bảo đủ cột theo thứ tự chuẩn
    for c in _COT:
        if c not in df.columns:
            df[c] = ""
    return df[_COT]


def them_cong_ty(ten_cong_ty: str, dia_chi: str = "", ma_kh: str = "", ma_so_thue: str = "") -> int:
    """
    Thêm công ty mới vào sheet 'Companies'.

    Args:
        ten_cong_ty: Tên công ty khách hàng
        dia_chi: Địa chỉ công ty
        ma_kh: Mã khách hàng
        ma_so_thue: Mã số thuế

    Returns:
        int: ID vừa tạo
    """
    sheet = lay_sheet_cong_ty()
    id_moi = len(sheet.col_values(1))  # cột A: header + các hàng dữ liệu
    ngay_tao = datetime.now().strftime("%Y-%m-%d")
    sheet.append_row([id_moi, ten_cong_ty, dia_chi, ma_kh, ma_so_thue, ngay_tao])
    lay_danh_sach_cong_ty.clear()
    lay_ten_cac_cong_ty.clear()
    return id_moi


def sua_cong_ty(record_id: str, ten_moi: str, dia_chi: str = "", ma_kh: str = "", ma_so_thue: str = ""):
    sheet = lay_sheet_cong_ty()
    o_tim = sheet.find(str(record_id), in_column=1)
    if o_tim is None:
        raise ValueError(f"Không tìm thấy ID={record_id}.")
    sheet.update_cell(o_tim.row, 2, ten_moi)
    sheet.update_cell(o_tim.row, 3, dia_chi)
    sheet.update_cell(o_tim.row, 4, ma_kh)
    sheet.update_cell(o_tim.row, 5, ma_so_thue)
    lay_danh_sach_cong_ty.clear()
    lay_ten_cac_cong_ty.clear()


def xoa_cong_ty(record_id: str):
    sheet = lay_sheet_cong_ty()
    o_tim = sheet.find(str(record_id), in_column=1)
    if o_tim is None:
        raise ValueError(f"Không tìm thấy ID={record_id}.")
    sheet.delete_rows(o_tim.row)
    lay_danh_sach_cong_ty.clear()
    lay_ten_cac_cong_ty.clear()


@st.cache_data(ttl=60)
def lay_ten_cac_cong_ty() -> list:
    """Trả về danh sách tên công ty để hiển thị trong selectbox."""
    df = lay_danh_sach_cong_ty()
    if df.empty:
        return []
    return df["Tên Công Ty"].dropna().tolist()


# ============================================================
# LOẠI MÁY
# ============================================================
def _lay_sheet_don_gian(ten_sheet: str, tieu_de: list) -> object:
    """Helper chung: mở worksheet (tự tạo nếu chưa có), dùng spreadsheet đã câu hình."""
    try:
        bang_tinh = _lay_bang_tinh()
        try:
            return bang_tinh.worksheet(ten_sheet)
        except gspread.exceptions.WorksheetNotFound:
            sheet = bang_tinh.add_worksheet(title=ten_sheet, rows=500, cols=len(tieu_de) + 1)
            sheet.append_row(tieu_de)
            return sheet
    except gspread.exceptions.WorksheetNotFound:
        raise
    except Exception as e:
        raise ConnectionError(_xoa_cache_va_thong_bao(e)) from e


def _lay_df_don_gian(ten_sheet: str, tieu_de: list) -> pd.DataFrame:
    """Helper chung: đọc toàn bộ dữ liệu về DataFrame. Trả về rỗng nếu mất mạng."""
    try:
        sheet   = _lay_sheet_don_gian(ten_sheet, tieu_de)
        allvals = sheet.get_all_values()
    except (ConnectionError, OSError, Exception) as e:
        _xoa_cache_va_thong_bao(e)
        return pd.DataFrame(columns=tieu_de)
    if len(allvals) <= 1:
        return pd.DataFrame(columns=tieu_de)
    n = len(tieu_de)
    headers = [v.strip() for v in allvals[0][:n]]
    rows = [r[:n] for r in allvals[1:] if any(r[:n])]
    return pd.DataFrame(rows, columns=headers)


def _them_hang_don_gian(ten_sheet: str, tieu_de: list, hang: list) -> int:
    """Helper chung: thêm 1 hàng, trả về ID mới. Raise ConnectionError nếu mất mạng."""
    sheet  = _lay_sheet_don_gian(ten_sheet, tieu_de)
    id_moi = len(sheet.col_values(1))  # số hàng hiện tại (kể cả header) = ID tiếp theo
    sheet.append_row([id_moi] + hang)
    return id_moi


def _sua_hang_don_gian(ten_sheet: str, tieu_de: list, record_id: str, ten_cot: str, gia_tri_moi: str):
    """Helper chung: tìm hàng theo ID (cột 1) rồi cập nhật cột ten_cot."""
    sheet = _lay_sheet_don_gian(ten_sheet, tieu_de)
    o_tim = sheet.find(str(record_id), in_column=1)
    if o_tim is None:
        raise ValueError(f"Không tìm thấy ID={record_id} trong sheet {ten_sheet}.")
    col_idx = tieu_de.index(ten_cot) + 1
    sheet.update_cell(o_tim.row, col_idx, gia_tri_moi)


def _xoa_hang_don_gian(ten_sheet: str, tieu_de: list, record_id: str):
    """Helper chung: tìm hàng theo ID (cột 1) rồi xóa."""
    sheet = _lay_sheet_don_gian(ten_sheet, tieu_de)
    o_tim = sheet.find(str(record_id), in_column=1)
    if o_tim is None:
        raise ValueError(f"Không tìm thấy ID={record_id} trong sheet {ten_sheet}.")
    sheet.delete_rows(o_tim.row)


# ============================================================
# HỆ THỐNG THÔNG BÁO (NOTIFICATIONS)
# ============================================================
_TB_SHEET   = "Notifications"
_TB_HEADERS = ["ID", "Nguoi_Nhan", "Noi_Dung", "Task_ID", "Loai", "Thoi_Gian", "Da_Doc"]


def them_thong_bao(nguoi_nhan: str, noi_dung: str, task_id: int = 0, loai: str = "general"):
    """Thêm 1 thông báo cho người nhận cụ thể vào sheet Notifications."""
    try:
        sheet     = _lay_sheet_don_gian(_TB_SHEET, _TB_HEADERS)
        id_moi    = len(sheet.col_values(1))
        thoi_gian = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([id_moi, nguoi_nhan, noi_dung, str(task_id), loai, thoi_gian, "0"])
    except Exception:
        pass


def them_thong_bao_tat_ca(noi_dung: str, task_id: int = 0, loai: str = "general", tru_nguoi: str = ""):
    """Gửi thông báo cho tất cả nhân viên trong hệ thống (trừ người tạo nếu có)."""
    try:
        df_users = lay_danh_sach_users()
        for _, row in df_users.iterrows():
            ten = str(row.get("HoTen", "")).strip()
            if ten and ten != tru_nguoi:
                them_thong_bao(ten, noi_dung, task_id, loai)
    except Exception:
        pass


def lay_thong_bao_nguoi_dung(ho_ten: str) -> pd.DataFrame:
    """Lấy danh sách thông báo của user trong 2 tuần gần nhất, mới nhất trước."""
    try:
        df = _lay_df_don_gian(_TB_SHEET, _TB_HEADERS)
        if df.empty:
            return df
        df = df[df["Nguoi_Nhan"] == ho_ten].copy()
        # Lọc chỉ thông báo trong 2 tuần gần nhất
        try:
            df["Thoi_Gian"] = pd.to_datetime(df["Thoi_Gian"], errors="coerce")
            nguong = datetime.now() - timedelta(weeks=2)
            df = df[df["Thoi_Gian"] >= nguong]
            df["Thoi_Gian"] = df["Thoi_Gian"].dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
        return df.sort_values("Thoi_Gian", ascending=False).reset_index(drop=True)
    except Exception:
        return pd.DataFrame(columns=_TB_HEADERS)


def xoa_thong_bao_cu():
    """Xóa các thông báo cũ hơn 2 tuần khỏi sheet (chạy định kỳ)."""
    try:
        sheet = _lay_sheet_don_gian(_TB_SHEET, _TB_HEADERS)
        rows = sheet.get_all_values()
        if len(rows) <= 1:
            return
        headers = rows[0]
        idx_time = headers.index("Thoi_Gian")
        nguong = datetime.now() - timedelta(weeks=2)
        # Tìm các hàng cần xóa (từ dưới lên để không lệch index)
        rows_to_delete = []
        for i, row in enumerate(rows[1:], start=2):
            try:
                tg = datetime.strptime(row[idx_time], "%Y-%m-%d %H:%M:%S")
                if tg < nguong:
                    rows_to_delete.append(i)
            except Exception:
                pass
        # Xóa từ dưới lên
        for r in reversed(rows_to_delete):
            sheet.delete_rows(r)
    except Exception:
        pass


def dem_chua_doc(ho_ten: str) -> int:
    """Đếm số thông báo chưa đọc của user."""
    try:
        df = lay_thong_bao_nguoi_dung(ho_ten)
        if df.empty:
            return 0
        return int((df["Da_Doc"] == "0").sum())
    except Exception:
        return 0


def danh_dau_da_doc_tat_ca(ho_ten: str):
    """Đánh dấu tất cả thông báo của user là đã đọc (batch update)."""
    try:
        sheet = _lay_sheet_don_gian(_TB_SHEET, _TB_HEADERS)
        rows  = sheet.get_all_values()
        if len(rows) <= 1:
            return
        headers   = rows[0]
        idx_nhan  = headers.index("Nguoi_Nhan") + 1
        idx_doc   = headers.index("Da_Doc") + 1
        col_letter = chr(64 + idx_doc)
        batch = []
        for i, row in enumerate(rows[1:], start=2):
            nhan = row[idx_nhan - 1] if len(row) >= idx_nhan else ""
            doc  = row[idx_doc  - 1] if len(row) >= idx_doc  else "0"
            if nhan == ho_ten and doc == "0":
                batch.append({"range": f"{col_letter}{i}", "values": [["1"]]})
        if batch:
            sheet.batch_update(batch)
    except Exception:
        pass


# Danh sách trạng thái mặc định (theo quy trình thực tế)
_DS_TRANG_THAI_MAC_DINH = [
    "Đang Kiểm Tra",
    "Đã Phê Duyệt",
    "Đã Báo Giá",
    "Có Đơn",
    "Chờ Giao",
    "Đã Hoàn Thành - Giao Máy",
]

# ---- Loại Máy ----
_TIEUDE_LOAI_MAY = ["ID", "Tên Loại Máy", "Ngày Tạo"]

@st.cache_data(ttl=60)
def lay_danh_sach_loai_may() -> pd.DataFrame:
    return _lay_df_don_gian("LoaiMay", _TIEUDE_LOAI_MAY)

def them_loai_may(ten: str) -> int:
    result = _them_hang_don_gian("LoaiMay", _TIEUDE_LOAI_MAY,
                                 [ten, datetime.now().strftime("%Y-%m-%d")])
    lay_danh_sach_loai_may.clear()
    lay_ten_cac_loai_may.clear()
    return result

def sua_loai_may(record_id: str, ten_moi: str):
    _sua_hang_don_gian("LoaiMay", _TIEUDE_LOAI_MAY, record_id, "Tên Loại Máy", ten_moi)
    lay_danh_sach_loai_may.clear()
    lay_ten_cac_loai_may.clear()

def xoa_loai_may(record_id: str):
    _xoa_hang_don_gian("LoaiMay", _TIEUDE_LOAI_MAY, record_id)
    lay_danh_sach_loai_may.clear()
    lay_ten_cac_loai_may.clear()

@st.cache_data(ttl=60)
def lay_ten_cac_loai_may() -> list:
    df = lay_danh_sach_loai_may()
    return df["Tên Loại Máy"].dropna().tolist() if not df.empty else []


# ---- Tình Trạng ----
_TIEUDE_TINH_TRANG = ["ID", "Tên Tình Trạng", "Ngày Tạo"]

@st.cache_data(ttl=60)
def lay_danh_sach_tinh_trang() -> pd.DataFrame:
    return _lay_df_don_gian("TinhTrang", _TIEUDE_TINH_TRANG)

def them_tinh_trang(ten: str) -> int:
    result = _them_hang_don_gian("TinhTrang", _TIEUDE_TINH_TRANG,
                                 [ten, datetime.now().strftime("%Y-%m-%d")])
    lay_danh_sach_tinh_trang.clear()
    lay_ten_cac_tinh_trang.clear()
    return result

def sua_tinh_trang(record_id: str, ten_moi: str):
    _sua_hang_don_gian("TinhTrang", _TIEUDE_TINH_TRANG, record_id, "Tên Tình Trạng", ten_moi)
    lay_danh_sach_tinh_trang.clear()
    lay_ten_cac_tinh_trang.clear()

def xoa_tinh_trang(record_id: str):
    _xoa_hang_don_gian("TinhTrang", _TIEUDE_TINH_TRANG, record_id)
    lay_danh_sach_tinh_trang.clear()
    lay_ten_cac_tinh_trang.clear()

@st.cache_data(ttl=60)
def lay_ten_cac_tinh_trang() -> list:
    df = lay_danh_sach_tinh_trang()
    return df["Tên Tình Trạng"].dropna().tolist() if not df.empty else []


# ---- Trạng Thái Công Việc (manual list) ----
_TIEUDE_TRANG_THAI = ["ID", "Tên Trạng Thái", "Ngày Tạo"]

@st.cache_data(ttl=60)
def lay_danh_sach_trang_thai_custom() -> pd.DataFrame:
    return _lay_df_don_gian("TrangThai", _TIEUDE_TRANG_THAI)

def them_trang_thai_custom(ten: str) -> int:
    result = _them_hang_don_gian("TrangThai", _TIEUDE_TRANG_THAI,
                                 [ten, datetime.now().strftime("%Y-%m-%d")])
    lay_danh_sach_trang_thai_custom.clear()
    lay_ten_cac_trang_thai.clear()
    return result

@st.cache_data(ttl=60)
def lay_ten_cac_trang_thai() -> list:
    df = lay_danh_sach_trang_thai_custom()
    return df["Tên Trạng Thái"].dropna().tolist() if not df.empty else _DS_TRANG_THAI_MAC_DINH


# ---- Công Đoạn ----
_TIEUDE_CONG_DOAN = ["ID", "Tên Công Đoạn", "Ngày Tạo"]

@st.cache_data(ttl=60)
def lay_danh_sach_cong_doan() -> pd.DataFrame:
    return _lay_df_don_gian("CongDoan", _TIEUDE_CONG_DOAN)

def them_cong_doan(ten: str) -> int:
    result = _them_hang_don_gian("CongDoan", _TIEUDE_CONG_DOAN,
                                 [ten, datetime.now().strftime("%Y-%m-%d")])
    lay_danh_sach_cong_doan.clear()
    lay_ten_cac_cong_doan.clear()
    return result

def sua_cong_doan(record_id: str, ten_moi: str):
    _sua_hang_don_gian("CongDoan", _TIEUDE_CONG_DOAN, record_id, "Tên Công Đoạn", ten_moi)
    lay_danh_sach_cong_doan.clear()
    lay_ten_cac_cong_doan.clear()

def xoa_cong_doan_item(record_id: str):
    _xoa_hang_don_gian("CongDoan", _TIEUDE_CONG_DOAN, record_id)
    lay_danh_sach_cong_doan.clear()
    lay_ten_cac_cong_doan.clear()

@st.cache_data(ttl=60)
def lay_ten_cac_cong_doan() -> list:
    df = lay_danh_sach_cong_doan()
    return df["Tên Công Đoạn"].dropna().tolist() if not df.empty else []


# ---- Người Thực Hiện Công Đoạn ----
_TIEUDE_NGUOI_CD = ["ID", "Họ Tên", "Công Đoạn", "Ngày Tạo"]

@st.cache_data(ttl=60)
def lay_danh_sach_nguoi_cong_doan() -> pd.DataFrame:
    return _lay_df_don_gian("NguoiCongDoan", _TIEUDE_NGUOI_CD)

def them_nguoi_cong_doan(ho_ten: str, cong_doan: str) -> int:
    result = _them_hang_don_gian("NguoiCongDoan", _TIEUDE_NGUOI_CD,
                                 [ho_ten, cong_doan, datetime.now().strftime("%Y-%m-%d")])
    lay_danh_sach_nguoi_cong_doan.clear()
    return result


@st.cache_data(ttl=60)
def lay_danh_sach_cong_viec() -> pd.DataFrame:
    """
    Lấy toàn bộ danh sách công việc từ sheet 'Tasks'.

    Cấu trúc cột Google Sheets:
    A:ID | B:Công Ty | C:Công Số | D:Năm | E:Tên Công Việc | F:Mô Tả
    G:Nhân Viên | H:Trạng Thái | I:Ngày Tạo | J:Hạn Hoàn Thành | K:Link Ảnh | L:Xem Ảnh
    """
    # 23 cột A→W (chỉ lấy đúng số cột này — tránh lỗi duplicate header từ cột trống)
    _HEADERS = [
        "ID", "Công Ty", "Công Số", "Năm", "Tên Công Việc", "Mô Tả",
        "Nhân Viên", "Trạng Thái", "Ngày Tạo", "Hạn Hoàn Thành",
        "Link Ảnh", "Người Phê Duyệt", "Checklist", "Công Việc Con", "Công Đoạn",
        "Loại Máy", "Tình Trạng",
        "Công Suất", "Số Cực", "Mã Số", "Số PO Nội Bộ", "Số PO KH/HĐ", "Số Báo Giá",
        "Ngày Kết Thúc", "Ảnh Đo Lường"
    ]
    _N = len(_HEADERS)
    _COT_TRONG = _HEADERS[:11]  # các cột hiển thị chính
    try:
        sheet   = lay_sheet()
        allvals = sheet.get_all_values()
    except (ConnectionError, OSError, Exception) as _e:
        import traceback
        print(f"[lay_danh_sach_cong_viec ERROR] {_e}\n{traceback.format_exc()}")
        return pd.DataFrame(columns=_COT_TRONG)
    if len(allvals) <= 1:
        return pd.DataFrame(columns=_COT_TRONG)
    # Dùng tên cột cố định (không đọc từ row 1) — tránh lỗi duplicate
    rows = [r[:_N] for r in allvals[1:] if any(r[:_N])]
    # Pad các hàng ngắn hơn _N cột (task cũ tạo trước khi thêm cột mới)
    rows_padded = [r + [""] * (_N - len(r)) for r in rows]
    try:
        df = pd.DataFrame(rows_padded, columns=_HEADERS) if rows_padded else pd.DataFrame(columns=_HEADERS)
    except Exception:
        # Fallback: tạo từng hàng an toàn
        df = pd.DataFrame([dict(zip(_HEADERS, r)) for r in rows_padded]) if rows_padded else pd.DataFrame(columns=_HEADERS)
    # Tương thích ngược: map các cột tiếng Anh cũ nếu cần
    df.rename(columns={
        "Cong_Ty":      "Công Ty",
        "Cong_So":      "Công Số",
        "Nam":          "Năm",
        "Task_Name":    "Tên Công Việc",
        "Description":  "Mô Tả",
        "Assigned_To":  "Nhân Viên",
        "Status":       "Trạng Thái",
        "Created_Date": "Ngày Tạo",
        "Deadline":     "Hạn Hoàn Thành",
        "Image_URL":    "Link Ảnh",
    }, inplace=True)
    if "Trạng Thái" in df.columns:
        df["Trạng Thái"] = df["Trạng Thái"].replace({
            "Todo":  "Chờ Làm",
            "Doing": "Đang Làm",
            "Done":  "Hoàn Thành",
        })
    for col in ["Công Ty", "Công Số", "Năm", "Người Phê Duyệt", "Checklist", "Công Việc Con"]:
        if col not in df.columns:
            df[col] = ""
    return df


def them_cong_viec(ten_task: str, mo_ta: str, nguoi_duoc_giao: str, deadline: str,
                   cong_ty: str = "", cong_so: str = "", nam: str = "",
                   trang_thai: str = "Chờ Làm", nguoi_phe_duyet: str = "",
                   checklist: list = None, cong_viec_con: list = None,
                   cong_doan: str = "", loai_may: str = "", tinh_trang: str = "",
                   cong_suat: str = "", so_cuc: str = "", ma_so: str = "",
                   so_po_noi_bo: str = "", so_po_kh: str = "", so_bao_gia: str = "",
                   ngay_ket_thuc: str = "") -> int:
    """
    Thêm một công việc mới vào cuối sheet.

    Cấu trúc hàng:
    A:ID | B:Cong_Ty | C:Cong_So | D:Nam | E:Task_Name | F:Description
    G:Assigned_To | H:Status | I:Created_Date | J:Deadline | K:Image_URL
    L:Nguoi_Phe_Duyet | M:Checklist (JSON) | N:Cong_Viec_Con (JSON) | O:Cong_Doan
    P:Loai_May | Q:Tinh_Trang | R:Cong_Suat | S:So_Cuc | T:Ma_So
    U:So_PO_Noi_Bo | V:So_PO_KH | W:So_Bao_Gia
    """
    sheet = _lay_sheet_fresh()  # Luôn dùng connection mới cho thao tác ghi
    # ID = max ID hiện tại + 1 (tránh trùng khi dữ liệu có hàng trống hoặc xoá)
    _ids_hien_co = sheet.col_values(1)[1:]  # bỏ header
    _so_ids = [int(x) for x in _ids_hien_co if str(x).strip().isdigit()]
    id_moi   = (max(_so_ids) + 1) if _so_ids else 1
    ngay_tao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    hang_moi = [
        id_moi,                           # A: ID
        cong_ty,                          # B: Công Ty
        cong_so,                          # C: Công Số
        nam,                              # D: Năm
        ten_task,                         # E: Tên Công Việc
        mo_ta,                            # F: Mô Tả
        nguoi_duoc_giao,                  # G: Nhân Viên
        trang_thai,                       # H: Trạng Thái
        ngay_tao,                         # I: Ngày Tạo
        deadline,                         # J: Hạn Hoàn Thành
        "",                               # K: Link Ảnh (để trống)
        nguoi_phe_duyet,                  # L: Người Phê Duyệt
        json.dumps(checklist or [], ensure_ascii=False),      # M: Checklist
        json.dumps(cong_viec_con or [], ensure_ascii=False),  # N: Công Việc Con
        cong_doan,                                            # O: Công Đoạn
        loai_may,                                             # P: Loại Máy
        tinh_trang,                                           # Q: Tình Trạng
        cong_suat,                                            # R: Công Suất
        so_cuc,                                               # S: Số Cực
        ma_so,                                                # T: Mã Số
        so_po_noi_bo,                                         # U: Số PO Nội Bộ
        so_po_kh,                                             # V: Số PO KH/HĐ
        so_bao_gia,                                           # W: Số Báo Giá
        ngay_ket_thuc,                                        # X: Ngày Kết Thúc
        "{}",                                                 # Y: Ảnh Đo Lường (JSON)
    ]

    # Tự tính row tiếp theo
    _so_hang_hien_co = len(sheet.col_values(1))
    _dong_moi = _so_hang_hien_co + 1
    sheet.update(f"A{_dong_moi}:Y{_dong_moi}", [hang_moi])
    # Clear cả lay_sheet cache để lần đọc tiếp theo dùng connection sạch
    lay_sheet.clear()
    _lay_bang_tinh.clear()
    lay_danh_sach_cong_viec.clear()

    # ── Gửi thông báo cho tất cả người dùng ──────────────────────────────
    _tb_task = (
        f"📋 Task mới #{id_moi}: {ten_task}"
        f" | Giao: {nguoi_duoc_giao}"
        + (f" | Công ty: {cong_ty}" if cong_ty else "")
    )
    them_thong_bao_tat_ca(_tb_task, task_id=id_moi, loai="task_moi")
    # Thông báo riêng cho từng người được giao công việc con
    for _cv in (cong_viec_con or []):
        _nv_cv = str(_cv.get("nhan_vien", "")).strip()
        _ten_cv = str(_cv.get("ten", "")).strip()
        if _nv_cv:
            them_thong_bao(
                _nv_cv,
                f"🔧 Bạn được giao việc: {_ten_cv} (Task #{id_moi}: {ten_task})",
                task_id=id_moi,
                loai="cong_viec_con",
            )

    return id_moi


def cap_nhat_trang_thai(task_id: int, trang_thai_moi: str):
    """
    Cập nhật trạng thái (Status) của công việc theo ID.
    """
    sheet = lay_sheet()
    o_tim = sheet.find(str(task_id), in_column=1)
    if o_tim:
        sheet.update_cell(o_tim.row, 8, trang_thai_moi)
        lay_danh_sach_cong_viec.clear()


def cap_nhat_ngay_ket_thuc(task_id: int, ngay_ket_thuc: str):
    """
    Cập nhật Ngày Kết Thúc (cột X, cột 24) của công việc theo ID.
    """
    sheet = lay_sheet()
    o_tim = sheet.find(str(task_id), in_column=1)
    if o_tim:
        sheet.update_cell(o_tim.row, 24, ngay_ket_thuc)
        lay_danh_sach_cong_viec.clear()


def cap_nhat_han_hoan_thanh(task_id: int, han: str):
    """
    Cập nhật Hạn Hoàn Thành (cột J, cột 10) của công việc theo ID.
    """
    sheet = lay_sheet()
    o_tim = sheet.find(str(task_id), in_column=1)
    if o_tim:
        sheet.update_cell(o_tim.row, 10, han)
        lay_danh_sach_cong_viec.clear()


def doc_anh_do_luong(gia_tri: str) -> dict:
    """Parse JSON ảnh đo lường từ cột Y. Trả về dict {label: [url,...]}."""
    if not gia_tri or str(gia_tri).strip() in ("", "{}"):
        return {}
    try:
        return json.loads(str(gia_tri).strip())
    except Exception:
        return {}


def cap_nhat_anh_do_luong(task_id: int, anh_dict: dict):
    """Ghi toàn bộ dict ảnh đo lường (cột Y = col 25) lên Google Sheets."""
    sheet = lay_sheet()
    o_tim = sheet.find(str(task_id), in_column=1)
    if o_tim:
        sheet.update_cell(o_tim.row, 25, json.dumps(anh_dict, ensure_ascii=False))
        lay_danh_sach_cong_viec.clear()


def doc_danh_sach_anh(gia_tri: str) -> list:
    """
    Parse danh sách URL ảnh từ chuỗi lưu trong Google Sheets.
    Hỗ trợ cả dạng JSON array '["url1","url2"]' và URL đơn cũ.
    """
    if not gia_tri:
        return []
    gia_tri = str(gia_tri).strip()
    if gia_tri.startswith("["):
        try:
            danh_sach = json.loads(gia_tri)
            return [u for u in danh_sach if u]
        except Exception:
            return []
    return [gia_tri] if gia_tri else []


def cap_nhat_url_anh(task_id: int, url_anh: str):
    """
    Gắn thêm URL ảnh mới vào danh sách ảnh của task (lưu dạng JSON array).
    Cột K lưu JSON array URLs. Cột L lưu =IMAGE() của ảnh đầu tiên.

    Args:
        task_id: ID công việc cần cập nhật
        url_anh: URL ảnh mới trên Cloudinary
    """
    sheet = lay_sheet()
    o_tim = sheet.find(str(task_id), in_column=1)
    if o_tim:
        so_hang = o_tim.row
        # Lấy danh sách ảnh hiện có
        gia_tri_cu = sheet.cell(so_hang, 11).value or ""
        ds_anh = doc_danh_sach_anh(gia_tri_cu)
        if url_anh not in ds_anh:
            ds_anh.append(url_anh)
        # Lưu JSON array vào cột K (11)
        sheet.update_cell(so_hang, 11, json.dumps(ds_anh, ensure_ascii=False))
        # Cột L (12): =IMAGE() của ảnh đầu tiên để xem trong Google Sheets
        sheet.update(
            [[f'=IMAGE("{ds_anh[0]}")']],
            f"L{so_hang}",
            value_input_option="USER_ENTERED"
        )
        lay_danh_sach_cong_viec.clear()


def xoa_url_anh(task_id: int, url_xoa: str):
    """
    Xoá một URL ảnh khỏi danh sách ảnh của task.
    """
    sheet = lay_sheet()
    o_tim = sheet.find(str(task_id), in_column=1)
    if o_tim:
        so_hang = o_tim.row
        gia_tri_cu = sheet.cell(so_hang, 11).value or ""
        ds_anh = doc_danh_sach_anh(gia_tri_cu)
        ds_anh = [u for u in ds_anh if u != url_xoa]
        sheet.update_cell(so_hang, 11, json.dumps(ds_anh, ensure_ascii=False) if ds_anh else "")
        if ds_anh:
            sheet.update(
                [[f'=IMAGE("{ds_anh[0]}")']],
                f"L{so_hang}",
                value_input_option="USER_ENTERED"
            )
        else:
            sheet.update_cell(so_hang, 12, "")
        lay_danh_sach_cong_viec.clear()


def cap_nhat_checklist(task_id: int, checklist: list):
    """Lưu danh sách checklist (JSON) vào cột M của task."""
    sheet = lay_sheet()
    o_tim = sheet.find(str(task_id), in_column=1)
    if o_tim:
        sheet.update_cell(o_tim.row, 13, json.dumps(checklist, ensure_ascii=False))
        lay_danh_sach_cong_viec.clear()


# ============================================================
# QUẢN LÝ TÀI KHOẢN NGƯỜI DÙNG (USERS SHEET)
# ============================================================
_TIEUDE_USERS = ["ID", "Username", "Password", "HoTen", "NgaySinh", "VaiTro", "NgayTao"]


def _ma_hoa_mat_khau(mat_khau: str) -> str:
    """Hash mật khẩu bằng SHA-256."""
    return hashlib.sha256(mat_khau.encode("utf-8")).hexdigest()


@st.cache_resource
def lay_sheet_users():
    """Mở (hoặc tự tạo) worksheet 'Users' để lưu tài khoản."""
    try:
        bang_tinh = _lay_bang_tinh()
        try:
            sheet = bang_tinh.worksheet("Users")
        except gspread.exceptions.WorksheetNotFound:
            sheet = bang_tinh.add_worksheet(title="Users", rows=500, cols=len(_TIEUDE_USERS) + 1)
            sheet.append_row(_TIEUDE_USERS)
            # Tạo tài khoản admin mặc định ngay khi sheet được tạo lần đầu
            sheet.append_row([
                1,
                "admin",
                _ma_hoa_mat_khau("admin123"),
                "Quản Trị Viên",
                "",
                "admin",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ])
        return sheet
    except Exception as e:
        raise ConnectionError(_xoa_cache_va_thong_bao(e)) from e


@st.cache_data(ttl=30)
def lay_danh_sach_users() -> pd.DataFrame:
    """Đọc toàn bộ danh sách tài khoản từ sheet Users."""
    try:
        sheet = lay_sheet_users()
        allvals = sheet.get_all_values()
    except Exception:
        return pd.DataFrame(columns=_TIEUDE_USERS)
    if len(allvals) <= 1:
        return pd.DataFrame(columns=_TIEUDE_USERS)
    n = len(_TIEUDE_USERS)
    rows = [r[:n] for r in allvals[1:] if any(r[:n])]
    return pd.DataFrame(rows, columns=_TIEUDE_USERS)


def kiem_tra_dang_nhap(username: str, mat_khau: str):
    """
    Kiểm tra thông tin đăng nhập.
    Trả về dict user nếu đúng, None nếu sai.
    """
    df = lay_danh_sach_users()
    if df.empty:
        return None
    pw_hash = _ma_hoa_mat_khau(mat_khau)
    row = df[(df["Username"].str.lower() == username.strip().lower()) &
             (df["Password"] == pw_hash)]
    if row.empty:
        return None
    r = row.iloc[0]
    return {"id": r["ID"], "username": r["Username"],
            "ho_ten": r["HoTen"], "ngay_sinh": r["NgaySinh"],
            "vai_tro": r["VaiTro"]}


def dang_ky_tai_khoan(username: str, mat_khau: str, ho_ten: str,
                      ngay_sinh: str, vai_tro: str = "nhan_vien") -> tuple:
    """
    Đăng ký tài khoản mới.
    Trả về (True, 'OK') nếu thành công, (False, 'lý do') nếu thất bại.
    """
    username = username.strip()
    if not username or not mat_khau or not ho_ten:
        return False, "Vui lòng điền đầy đủ thông tin."
    if len(username) < 3:
        return False, "Username phải có ít nhất 3 ký tự."
    if len(mat_khau) < 6:
        return False, "Mật khẩu phải có ít nhất 6 ký tự."

    # Kiểm tra username đã tồn tại chưa
    df = lay_danh_sach_users()
    if not df.empty and username.lower() in df["Username"].str.lower().tolist():
        return False, "Username đã tồn tại. Vui lòng chọn tên khác."

    sheet = lay_sheet_users()
    id_moi = len(sheet.col_values(1))  # header + data rows
    sheet.append_row([
        id_moi,
        username,
        _ma_hoa_mat_khau(mat_khau),
        ho_ten.strip(),
        ngay_sinh,
        vai_tro,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ])
    # Xóa cache để đọc lại danh sách mới nhất
    lay_danh_sach_users.clear()
    lay_danh_sach_nhan_vien.clear()
    return True, "OK"


def doi_mat_khau(username: str, mat_khau_cu: str, mat_khau_moi: str) -> tuple:
    """
    Đổi mật khẩu cho tài khoản.
    Trả về (True, 'OK') nếu thành công, (False, 'lý do') nếu thất bại.
    """
    if not mat_khau_moi:
        return False, "Vui lòng nhập mật khẩu mới."
    if len(mat_khau_moi) < 6:
        return False, "Mật khẩu mới phải có ít nhất 6 ký tự."

    df = lay_danh_sach_users()
    if df.empty:
        return False, "Không tìm thấy tài khoản."

    pw_hash_cu = _ma_hoa_mat_khau(mat_khau_cu)
    row = df[(df["Username"].str.lower() == username.strip().lower()) &
             (df["Password"] == pw_hash_cu)]
    if row.empty:
        return False, "Mật khẩu hiện tại không đúng."

    sheet = lay_sheet_users()
    o_tim = sheet.find(username.strip(), in_column=2)
    if o_tim is None:
        return False, "Không tìm thấy tài khoản trong hệ thống."

    sheet.update_cell(o_tim.row, 3, _ma_hoa_mat_khau(mat_khau_moi))
    lay_danh_sach_users.clear()
    return True, "OK"


@st.cache_data(ttl=60)
def lay_danh_sach_nhan_vien() -> list:
    """Trả về danh sách Họ Tên nhân viên (đọc từ Users sheet, vai trò nhan_vien)."""
    try:
        df = lay_danh_sach_users()
        if df.empty:
            return []
        # Lấy tất cả người dùng (kể cả admin) để có thể giao việc
        nv = df[df["VaiTro"] == "nhan_vien"]["HoTen"].dropna().tolist()
        return [n for n in nv if n.strip()]
    except Exception:
        return []


# ============================================================
# TẠO PDF BIÊN BẢN NGHIỆM THU
# ============================================================
class PDFNghiemThu(FPDF):
    """
    Class PDF tùy chỉnh, kế thừa FPDF.
    Dùng font DejaVuSans để hiển thị đầy đủ tiếng Việt.
    Header/Footer trống để tự quản lý layout theo mẫu.
    """

    def _add_fonts(self):
        """Nạp font Unicode vào PDF (gọi 1 lần sau khi khởi tạo)."""
        self.add_font("DejaVu", "",  FONT_REGULAR)
        self.add_font("DejaVu", "B", FONT_BOLD)

    def header(self):
        """Không dùng header mặc định — layout được quản lý thủ công."""
        pass

    def footer(self):
        """Số trang nhỏ ở chân trang."""
        self.set_y(-12)
        self.set_font("DejaVu", "", 8)
        self.cell(0, 8, f"Trang {self.page_no()}", align="C")


def _tai_anh_tam(url: str):
    """Tải ảnh từ URL về file tạm, trả về đường dẫn hoặc None nếu lỗi."""
    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return None
        suffix = ".png" if url.lower().endswith(".png") else ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(r.content)
            return f.name
    except Exception:
        return None


def tao_pdf_nghiem_thu(thong_tin_task: dict) -> bytes:
    """
    Tạo file PDF biên bản nghiệm thu theo mẫu Điện Cơ Ngọc Trâm.

    Trang 1 : Header, tiêu đề BBNT, Engine/Customer/Address,
              Thời gian–địa điểm, bảng 12 hạng mục, footer doc.
    Trang 2 : Header doc, 3 bảng điện trở, mỗi bảng có ô ảnh
              (ảnh 1-3 → Stator1, 4-6 → Stator2, 7-9 → Rotor).
    """
    M_LEFT   = 10
    M_TOP    = 10
    USABLE_W = 190

    # ── Parse dữ liệu ──────────────────────────────────────────
    ten_dong_co  = str(thong_tin_task.get("Tên Công Việc", ""))
    khach_hang   = str(thong_tin_task.get("Công Ty", ""))
    cong_so      = str(thong_tin_task.get("Công Số", ""))
    mo_ta        = str(thong_tin_task.get("Mô Tả", ""))
    nhan_vien    = str(thong_tin_task.get("Nhân Viên", ""))
    ngay_tao_str = str(thong_tin_task.get("Ngày Tạo", ""))

    # Ảnh đo lường theo từng nhãn  {"U1–V1": [url,...], ...}
    anh_do_luong = doc_anh_do_luong(str(thong_tin_task.get("Ảnh Đo Lường", "") or ""))

    # Format ngày
    try:
        dt = datetime.strptime(ngay_tao_str[:10], "%Y-%m-%d")
        ngay_en = dt.strftime("%-d %B %Y") if os.name != "nt" else dt.strftime("%d %B %Y").lstrip("0")
        ngay_vi = f"Ngày {dt.day:02d} Tháng {dt.month:02d} Năm {dt.year}"
    except Exception:
        ngay_en = ngay_tao_str
        ngay_vi = ngay_tao_str

    hang_muc = [h.strip() for h in mo_ta.split("\n") if h.strip()]

    # ── Màu sắc ────────────────────────────────────────────────
    BLUE_HDR  = (68,  114, 196)   # tiêu đề bảng (đậm xanh)
    BLUE_CELL = (189, 215, 238)   # ô label pha (xanh nhạt)
    WHITE     = (255, 255, 255)
    BLACK     = (0,   0,   0)
    PURPLE    = (112, 48,  160)   # màu chữ công ty

    # ── Khởi tạo PDF ───────────────────────────────────────────
    pdf = PDFNghiemThu()
    pdf._add_fonts()
    pdf.set_margins(M_LEFT, M_TOP)
    pdf.set_auto_page_break(auto=False)

    # ========================================================= #
    #  TRANG 1                                                  #
    # ========================================================= #
    pdf.add_page()
    W = USABLE_W

    # ── Header công ty ─────────────────────────────────────────
    pdf.set_text_color(*PURPLE)
    pdf.set_font("DejaVu", "B", 13)
    pdf.cell(W, 7, "CÔNG TY TNHH MỘT THÀNH VIÊN ĐIỆN CƠ NGỌC TRÂM",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*BLACK)
    pdf.set_font("DejaVu", "", 8.5)
    pdf.cell(W, 5, "Địa chỉ : 8/5,hẻm 04, tổ 9, khu Kim Sơn, Xã Long Thành, Tỉnh Đồng Nai, Việt Nam",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(W, 5, "Website: ngoctrammotor.com   Mail: ctyngoctram1811@gmail.com",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(W, 5, "MST: 3603238978  DT: 0907 042 043 (Mr.Hiệp) – 0908 062 291 ( Ms.Linh)",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # ── Tiêu đề BBNT ──────────────────────────────────────────
    pdf.set_font("DejaVu", "B", 12)
    pdf.cell(W, 7, "REPAIR ACCEPTANCE CERTIFICATE",
             align="C", new_x="LMARGIN", new_y="NEXT")

    # "BIÊN BẢN NGHIỆM THU" trong khung viền xanh
    y_box = pdf.get_y()
    pdf.set_draw_color(*BLUE_HDR)
    pdf.set_line_width(0.8)
    pdf.set_font("DejaVu", "B", 15)
    pdf.cell(W, 10, "BIÊN BẢN NGHIỆM THU",
             border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_line_width(0.2)
    pdf.set_draw_color(*BLACK)
    pdf.ln(2)

    # ── Bảng Engine / Customer / Address ──────────────────────
    W_LBL = 32   # cột nhãn (EN + VI stacked)
    W_VAL = W - W_LBL
    ROW_H = 11   # chiều cao mỗi hàng

    def _info_row(en: str, vi: str, val: str):
        y0 = pdf.get_y()
        # Vẽ khung 2 ô bằng rect (đảm bảo thẳng hàng)
        pdf.rect(M_LEFT,         y0, W_LBL, ROW_H)
        pdf.rect(M_LEFT + W_LBL, y0, W_VAL, ROW_H)
        # EN text (bold, trên)
        pdf.set_xy(M_LEFT + 1, y0 + 1)
        pdf.set_font("DejaVu", "B", 9)
        pdf.cell(W_LBL - 2, 5, en)
        # VI text (normal, dưới)
        pdf.set_xy(M_LEFT + 1, y0 + 5.5)
        pdf.set_font("DejaVu", "", 8)
        pdf.cell(W_LBL - 2, 5, vi)
        # Value text (căn giữa dọc trong ô)
        pdf.set_xy(M_LEFT + W_LBL + 2, y0 + 1.5)
        pdf.set_font("DejaVu", "", 9)
        pdf.cell(W_VAL - 4, ROW_H - 3, val, align="L")
        # Xuống dòng tiếp theo
        pdf.set_xy(M_LEFT, y0 + ROW_H)

    _info_row("Engine",   "Động cơ",    ten_dong_co)
    _info_row("Customer", "Khách hàng", khach_hang)
    _info_row("Address",  "Địa chỉ",   "")
    pdf.ln(3)

    # ── Section I ─────────────────────────────────────────────
    pdf.set_font("DejaVu", "B", 9.5)
    pdf.cell(W, 6, "I. Time and place of the test / Thời gian và địa điểm kiểm tra",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9.5)
    pdf.cell(W, 6, f"At 7:30 AM on {ngay_en}, at Ngoc Tram Motor",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(W, 6, f"Lúc 7h30 - {ngay_vi} , tại Điện cơ Ngọc Trâm",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # ── Section II: bảng 12 hạng mục ─────────────────────────
    pdf.set_font("DejaVu", "B", 9.5)
    pdf.cell(W, 6, "II. Hạng mục sửa chữa / Hạng mục sửa chữa",
             new_x="LMARGIN", new_y="NEXT")

    # ── Kích thước cố định bảng Section II ──────────────────
    W_STT  = 15
    W_DATE = 35
    W_PASS = 38
    W_HM   = W - W_STT - W_DATE - W_PASS   # 190-15-35-38 = 102

    HDR_H  = 9
    ROW_H2 = 7

    # Tọa độ x tuyệt đối — tính 1 lần, dùng cho cả header lẫn rows
    xSTT  = M_LEFT                          # 10
    xHM   = xSTT  + W_STT                  # 25
    xDATE = xHM   + W_HM                   # 127
    xPASS = xDATE + W_DATE                 # 162

    y_hdr = pdf.get_y()

    # ── Header: vẽ nền trước bằng rect, rồi viền, rồi text ──
    # 1) Fill toàn bộ hàng header một lần
    pdf.set_fill_color(*BLUE_CELL)
    pdf.rect(xSTT, y_hdr, W, HDR_H, style="F")

    # 2) Vẽ viền từng ô bằng rect (không fill, chỉ border)
    pdf.rect(xSTT,  y_hdr, W_STT,  HDR_H)
    pdf.rect(xHM,   y_hdr, W_HM,   HDR_H)
    pdf.rect(xDATE, y_hdr, W_DATE, HDR_H)
    pdf.rect(xPASS, y_hdr, W_PASS, HDR_H)

    # 3) Text header — border=0, set_xy rõ ràng cho từng ô
    pdf.set_font("DejaVu", "B", 8.5)
    pdf.set_text_color(*BLACK)

    pdf.set_xy(xSTT, y_hdr)
    pdf.cell(W_STT, HDR_H, "STT", border=0, align="C")

    pdf.set_xy(xHM, y_hdr)
    pdf.cell(W_HM, HDR_H, "Repair catalog / Hạng mục sửa chữa", border=0, align="C")

    pdf.set_xy(xDATE, y_hdr)
    pdf.cell(W_DATE, HDR_H, "Date / Ngày", border=0, align="C")

    # "Passed / Thông qua" — 2 dòng, không có đường ngăn giữa
    pdf.set_font("DejaVu", "B", 8)
    pdf.set_xy(xPASS, y_hdr + 0.5)
    pdf.cell(W_PASS, HDR_H / 2, "Passed /", border=0, align="C")
    pdf.set_xy(xPASS, y_hdr + HDR_H / 2)
    pdf.cell(W_PASS, HDR_H / 2, "Thông qua", border=0, align="C")

    # ── 12 dòng hạng mục ─────────────────────────────────────
    pdf.set_font("DejaVu", "", 8.5)
    for i in range(1, 13):
        noi_dung = hang_muc[i - 1] if (i - 1) < len(hang_muc) else ""
        y_r = y_hdr + HDR_H + (i - 1) * ROW_H2

        # Viền từng ô
        pdf.rect(xSTT,  y_r, W_STT,  ROW_H2)
        pdf.rect(xHM,   y_r, W_HM,   ROW_H2)
        pdf.rect(xDATE, y_r, W_DATE, ROW_H2)
        pdf.rect(xPASS, y_r, W_PASS, ROW_H2)

        # Text
        pdf.set_xy(xSTT, y_r + 1)
        pdf.cell(W_STT, ROW_H2 - 1, f"{i} -", border=0, align="C")

        pdf.set_xy(xHM, y_r + 1)
        pdf.cell(W_HM, ROW_H2 - 1, noi_dung, border=0, align="L")

    # Đặt cursor xuống dưới bảng
    pdf.set_xy(M_LEFT, y_hdr + HDR_H + 12 * ROW_H2)

    # Định nghĩa W1/W2/W3 dùng chung cho _draw_img_hdr
    BOX_H1 = 8
    BOX_H2 = 8
    W1 = 16   # logo
    W2 = int((W - W1) / 3)
    W3 = W - W1 - W2 - W2

    # ========================================================= #
    #  TRANG ẢNH 1/5 → 5/5                                     #
    # ========================================================= #

    # ── Hàm vẽ header tài liệu cho mỗi trang ảnh ─────────
    def _draw_img_hdr(page_str: str):
        """Vẽ header box 2 hàng bằng nhau, NT span 2 hàng, giống mẫu Excel.
        Dùng rect() cho tất cả viền để đảm bảo thẳng hàng tuyệt đối."""
        RH = BOX_H1   # chiều cao mỗi hàng = 8mm
        y1 = M_TOP
        y2 = M_TOP + RH

        # Tọa độ x cố định cho 4 cột
        xA = M_LEFT           # NT logo
        xB = M_LEFT + W1      # Quotation / Management doc
        xC = M_LEFT + W1 + W2 # Engine number / Edition date
        xD = M_LEFT + W1 + W2 * 2  # Order number / Page

        # ── Vẽ tất cả viền bằng rect() ──────────────────────────
        pdf.rect(xA, y1, W1, RH * 2)   # NT logo span 2 hàng
        pdf.rect(xB, y1, W2, RH)        # Quotation (hàng 1)
        pdf.rect(xC, y1, W2, RH)        # Engine number (hàng 1)
        pdf.rect(xD, y1, W3, RH)        # Order number (hàng 1)
        pdf.rect(xB, y2, W2, RH)        # Management doc (hàng 2)
        pdf.rect(xC, y2, W2, RH)        # Edition date (hàng 2)
        pdf.rect(xD, y2, W3, RH)        # Page (hàng 2)

        # ── NT logo — canh giữa theo chiều dọc 2 hàng ──
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_xy(xA, y1 + RH - 3)
        pdf.cell(W1, 6, "NT", border=0, align="C")

        # ── Hàng 1 — text canh giữa ô ──
        pdf.set_font("DejaVu", "", 7)
        # Quotation
        pdf.set_xy(xB, y1)
        pdf.cell(W2, RH, "Quotation / Báo giá :", border=0, align="C")
        # Engine number
        pdf.set_xy(xC, y1)
        pdf.cell(W2, RH, "Engine number / Số máy :", border=0, align="C")
        # Order number (có giá trị)
        pdf.set_xy(xD, y1)
        pdf.cell(W3, RH, f"Order number / Số ĐH: {cong_so}", border=0, align="C")

        # ── Hàng 2 — mỗi ô chia 2 dòng nhỏ bằng multi_cell ──
        sub_h = RH / 2  # 4mm mỗi sub-row

        # Management doc
        pdf.set_font("DejaVu", "", 6.5)
        pdf.set_xy(xB, y2)
        pdf.cell(W2, sub_h, "Management document / Tài liệu quản lý:", border=0, align="C")
        pdf.set_xy(xB, y2 + sub_h)
        pdf.cell(W2, sub_h, "QT-NT-029-1A", border=0, align="C")

        # Edition date
        pdf.set_xy(xC, y2)
        pdf.cell(W2, sub_h, "Edition date / Ngày ban hành:", border=0, align="C")
        pdf.set_xy(xC, y2 + sub_h)
        pdf.cell(W2, sub_h, "24/04/2025", border=0, align="C")

        # Page
        pdf.set_xy(xD, y2)
        pdf.cell(W3, sub_h, "Page / Trang:", border=0, align="C")
        pdf.set_xy(xD, y2 + sub_h)
        pdf.cell(W3, sub_h, page_str, border=0, align="C")

        # Đặt cursor sau header
        pdf.set_xy(M_LEFT, M_TOP + RH * 2 + 4)

    # ── Hàm vẽ 1 bảng có ô ảnh ─────────────────────────────
    def _bang_co_anh(ten_en: str, ten_vi: str, nhan_pha_display: list,
                     danh_sach_anh_bang: list, img_h: int = 55):
        """
        Vẽ bảng n cột:
          - Dòng 1: tiêu đề full width (xanh đậm/trắng) — bỏ qua nếu ten_en rỗng
          - Dòng 2: n nhãn cột (xanh nhạt)
          - Dòng 3: n ô ảnh (hoặc trống)
        img_h : chiều cao vùng ảnh (mm), điều chỉnh theo số bảng/trang.
        """
        HDR_H  = 8
        LBL_H  = 8
        n = len(nhan_pha_display)
        if n == 0:
            return
        base_w = int(W / n)
        col_ws = [base_w] * (n - 1) + [W - base_w * (n - 1)]
        col_xs = [M_LEFT + sum(col_ws[:i]) for i in range(n)]

        y_start = pdf.get_y()

        # -- Dòng tiêu đề (chỉ vẽ nếu có tên) --
        if ten_en:
            pdf.set_xy(M_LEFT, y_start)
            pdf.set_fill_color(*BLUE_HDR)
            pdf.set_text_color(*WHITE)
            pdf.set_font("DejaVu", "B", 9.5)
            hdr_txt = f"{ten_en} / {ten_vi}" if ten_vi else ten_en
            pdf.cell(W, HDR_H, hdr_txt, border=1, align="C", fill=True,
                     new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*BLACK)
            y_lbl = pdf.get_y()
        else:
            y_lbl = y_start

        # -- Dòng nhãn --
        pdf.set_fill_color(*BLUE_CELL)
        pdf.set_font("DejaVu", "B", 9)
        for idx_p, nhan in enumerate(nhan_pha_display):
            pdf.set_xy(col_xs[idx_p], y_lbl)
            pdf.cell(col_ws[idx_p], LBL_H, nhan, border=1, align="C", fill=True)
        pdf.set_xy(M_LEFT, y_lbl + LBL_H)

        # -- Dòng ô ảnh --
        y_img = pdf.get_y()
        for idx_a in range(n):
            x_img = col_xs[idx_a]
            cw    = col_ws[idx_a]
            pdf.rect(x_img, y_img, cw, img_h)
            if idx_a < len(danh_sach_anh_bang) and danh_sach_anh_bang[idx_a]:
                try:
                    pad = 1
                    pdf.image(danh_sach_anh_bang[idx_a],
                              x=x_img + pad, y=y_img + pad,
                              w=cw - 2*pad, h=img_h - 2*pad)
                except Exception:
                    pass
        pdf.set_xy(M_LEFT, y_img + img_h)
        pdf.ln(4)

    # ── Nhóm theo trang ảnh (trang X/5) ────────────────────
    # Cấu trúc mỗi phần tử: (page_str, img_h, [(ten_en, ten_vi, display_labels, storage_keys)])
    # ten_en = "" → không vẽ header xanh đậm (dùng cho nhóm tiếp theo cùng section)
    IMAGE_PAGES = [
        # Trang 1/5 — Stator + Temperature sensor
        ("1/5", 55, [
            ("Stator 1 coil resistance",
             "Điện trở cuộn dây Stator 1",
             ["U1 – U2", "V1 – V2", "W1 –  W2"],
             ["U1–U2",   "V1–V2",   "W1–W2"]),

            ("Resistance of the temperature sensor",
             "điện trở của cảm biến nhiệt độ",
             ["PTC", "PT100", "HEATER"],
             ["PTC", "PT100", "HEATER"]),
        ]),

        # Trang 2/5 — No-load test (3 sub-bảng chung 1 header xanh đầu)
        ("2/5", 50, [
            ("No-load test",
             "Kiểm tra không tải",
             ["Frequency / Tần số", "Voltage /  Voltage", "Current / Dòng điện"],
             ["Tần số",              "Voltage",             "Dòng điện"]),

            ("",   # không vẽ lại header
             "",
             ["Radial ↔ DE / AS", "Radial ↕ DE / AS", "Axial (X) DE / AS"],
             ["Radial ↔ DE / AS", "Radial ↑ DE / AS", "Axial (X) DE / AS"]),

            ("",
             "",
             ["Radial ↔ NDE / AS", "Radial ↕ NDE / AS", "Axial (X) NDE / AS"],
             ["Radial ↔ NDE / AS", "Radial ↑ NDE / AS", "Axial (X) NDE / AS"]),
        ]),

        # Trang 3/5 — Engine overview + Nắp
        ("3/5", 55, [
            ("Engine overview",
             "Tổng quan động cơ",
             ["Engine / Động cơ", "Nameplate / Bảng tên", "Quạt làm mát / Cooling fan"],
             ["Engine / Động cơ", "Nameplate / Bảng tên", "Quạt làm mát / Cooling fan"]),

            ("Nắp động cơ", "",
             ["DE", "NDE"],
             ["Nắp DE", "Nắp NDE"]),
        ]),

        # Trang 4/5 — Trục, Phớt, Bearing (4 bảng → img_h nhỏ hơn)
        ("4/5", 42, [
            ("Trục động cơ", "",
             ["Bạc đạn DE", "Bạc đạn NDE"],
             ["Bạc đạn DE", "Bạc đạn NDE"]),

            ("",  "",
             ["Phớt", "Đầu ren , chốt lavet", "Cánh quạt làm mát"],
             ["Phớt", "Đầu ren, chốt lavet",  "Cánh quạt làm mát"]),

            ("Phớt chặn", "",
             ["Phớt 1", "Phớt 2"],
             ["Phớt chặn 1", "Phớt chặn 2"]),

            ("Bearing / Vòng bi", "",
             ["DE", "NDE"],
             ["Vòng bi DE", "Vòng bi NDE"]),
        ]),

        # Trang 5/5 — Grease pump, Coil, Cân bằng
        ("5/5", 50, [
            ("Grease pump",
             "Bơm mỡ bôi trơn",
             ["Bearing / Vòng bi", "Grease cap / Mặt gam"],
             ["Vòng bi bơm mỡ",    "Mặt gam"]),

            ("Coil",
             "Cuộn dây",
             ["Vào dây", "Đai đấu"],
             ["Vào dây", "Đai đầu"]),

            ("Cân bằng động", "",
             ["Gá lên máy", "Sau khi cân"],
             ["Gá lên máy", "Sau khi cân"]),
        ]),
    ]

    # ── Tải toàn bộ ảnh về temp files ───────────────────────
    # Làm phẳng IMAGE_PAGES thành danh sách bảng + map index
    _all_tables = []
    for _, _, tables in IMAGE_PAGES:
        for t in tables:
            _all_tables.append(t)

    temp_files_all = []
    all_temps = []
    for _, _, _, storage_keys in _all_tables:
        nhom_paths = []
        for lbl in storage_keys:
            urls = anh_do_luong.get(lbl, [])
            p = _tai_anh_tam(urls[0]) if urls else None
            nhom_paths.append(p)
            if p:
                all_temps.append(p)
        temp_files_all.append(nhom_paths)

    # ── Vẽ từng trang ảnh ───────────────────────────────────
    tbl_idx = 0
    for page_str, img_h, tables in IMAGE_PAGES:
        pdf.add_page()
        _draw_img_hdr(page_str)
        for ten_en, ten_vi, display_labels, _ in tables:
            _bang_co_anh(ten_en, ten_vi, display_labels, temp_files_all[tbl_idx], img_h)
            tbl_idx += 1

    # ── Dọn temp files ───────────────────────────────────────
    for p in all_temps:
        if p and os.path.exists(p):
            try:
                os.unlink(p)
            except Exception:
                pass

    # ── Xuất PDF ─────────────────────────────────────────────
    return bytes(pdf.output())


# ============================================================
# TẠO EXCEL BIÊN BẢN NGHIỆM THU
# ============================================================
def tao_excel_nghiem_thu(thong_tin_task: dict) -> bytes:
    """Tạo file Excel biên bản nghiệm thu theo mẫu Điện Cơ Ngọc Trâm."""
    import io
    from openpyxl import Workbook
    from openpyxl.styles import (Font, PatternFill, Alignment, Border, Side,
                                 GradientFill)
    from openpyxl.utils import get_column_letter

    # ── Parse dữ liệu ──────────────────────────────────────────
    ten_dong_co  = str(thong_tin_task.get("Tên Công Việc", ""))
    khach_hang   = str(thong_tin_task.get("Công Ty", ""))
    cong_so      = str(thong_tin_task.get("Công Số", ""))
    mo_ta        = str(thong_tin_task.get("Mô Tả", ""))
    nhan_vien    = str(thong_tin_task.get("Nhân Viên", ""))
    ngay_tao_str = str(thong_tin_task.get("Ngày Tạo", ""))
    try:
        dt = datetime.strptime(ngay_tao_str[:10], "%Y-%m-%d")
        ngay_en = dt.strftime("%d %B %Y")
        ngay_vi = f"Ngày {dt.day:02d} Tháng {dt.month:02d} Năm {dt.year}"
    except Exception:
        ngay_en = ngay_tao_str
        ngay_vi = ngay_tao_str

    hang_muc = [h.strip() for h in mo_ta.split("\n") if h.strip()]

    # ── Styles ──────────────────────────────────────────────────
    thin  = Side(style="thin",   color="000000")
    thick = Side(style="medium", color="000000")
    brd_all  = Border(left=thin, right=thin, top=thin, bottom=thin)
    brd_thick = Border(left=thick, right=thick, top=thick, bottom=thick)

    BLUE_HDR  = "4472C4"
    BLUE_CELL = "BDD7EE"
    PURPLE    = "70309F"
    WHITE     = "FFFFFF"
    YELLOW    = "FFF2CC"

    def _font(bold=False, size=10, color="000000", italic=False):
        return Font(bold=bold, size=size, color=color, italic=italic,
                    name="Times New Roman")

    def _fill(hex_color):
        return PatternFill("solid", fgColor=hex_color)

    def _align(h="center", v="center", wrap=True):
        return Alignment(horizontal=h, vertical=v, wrap_text=wrap)

    def _set_cell(ws, row, col, value="", bold=False, size=10, color="000000",
                  h_align="center", v_align="center", fill_color=None,
                  border=None, italic=False, wrap=True):
        c = ws.cell(row=row, column=col, value=value)
        c.font      = _font(bold=bold, size=size, color=color, italic=italic)
        c.alignment = _align(h=h_align, v=v_align, wrap=wrap)
        if fill_color:
            c.fill  = _fill(fill_color)
        if border:
            c.border = border
        return c

    # ── Tạo workbook ────────────────────────────────────────────
    wb = Workbook()
    ws = wb.active
    ws.title = "Biên Bản Nghiệm Thu"

    # Độ rộng cột (A=STT, B=Hạng mục, C=Ngày, D=Thông qua)
    ws.column_dimensions["A"].width = 6
    ws.column_dimensions["B"].width = 52
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 18

    row = 1

    # ── Header công ty ──────────────────────────────────────────
    ws.merge_cells(f"A{row}:D{row}")
    _set_cell(ws, row, 1,
              "CÔNG TY TNHH MỘT THÀNH VIÊN ĐIỆN CƠ NGỌC TRÂM",
              bold=True, size=13, color=PURPLE)
    ws.row_dimensions[row].height = 20
    row += 1

    for txt in [
        "Địa chỉ : 8/5, hẻm 04, tổ 9, khu Kim Sơn, Xã Long Thành, Tỉnh Đồng Nai, Việt Nam",
        "Website: ngoctrammotor.com   Mail: ctyngoctram1811@gmail.com",
        "MST: 3603238978  ĐT: 0907 042 043 (Mr.Hiệp) – 0908 062 291 (Ms.Linh)",
    ]:
        ws.merge_cells(f"A{row}:D{row}")
        _set_cell(ws, row, 1, txt, size=9)
        ws.row_dimensions[row].height = 14
        row += 1

    row += 1  # khoảng trống

    # ── Tiêu đề BBNT ────────────────────────────────────────────
    ws.merge_cells(f"A{row}:D{row}")
    _set_cell(ws, row, 1, "REPAIR ACCEPTANCE CERTIFICATE", bold=True, size=12)
    ws.row_dimensions[row].height = 18
    row += 1

    ws.merge_cells(f"A{row}:D{row}")
    c = _set_cell(ws, row, 1, "BIÊN BẢN NGHIỆM THU",
                  bold=True, size=15, fill_color=BLUE_CELL, border=brd_thick)
    ws.row_dimensions[row].height = 22
    row += 1

    row += 1  # khoảng trống

    # ── Bảng thông tin Engine / Customer / Address ──────────────
    for en_lbl, vi_lbl, val in [
        ("Engine",   "Động cơ",    ten_dong_co),
        ("Customer", "Khách hàng", khach_hang),
        ("Address",  "Địa chỉ",   ""),
    ]:
        _set_cell(ws, row, 1, f"{en_lbl} / {vi_lbl}",
                  bold=True, size=9, fill_color=BLUE_CELL, border=brd_all,
                  h_align="left")
        ws.merge_cells(f"B{row}:D{row}")
        _set_cell(ws, row, 2, val, size=10, border=brd_all, h_align="left")
        ws.row_dimensions[row].height = 18
        row += 1

    row += 1

    # ── Section I ────────────────────────────────────────────────
    ws.merge_cells(f"A{row}:D{row}")
    _set_cell(ws, row, 1,
              "I. Time and place of the test / Thời gian và địa điểm kiểm tra",
              bold=True, size=10, h_align="left")
    row += 1

    ws.merge_cells(f"A{row}:D{row}")
    _set_cell(ws, row, 1,
              f"At 7:30 AM on {ngay_en}, at Ngoc Tram Motor",
              size=10, h_align="left")
    row += 1

    ws.merge_cells(f"A{row}:D{row}")
    _set_cell(ws, row, 1,
              f"Lúc 7h30 - {ngay_vi}, tại Điện cơ Ngọc Trâm",
              size=9, h_align="left")
    row += 1
    row += 1

    # ── Section II: Header bảng 12 hạng mục ─────────────────────
    ws.merge_cells(f"A{row}:D{row}")
    _set_cell(ws, row, 1,
              "II. Hạng mục sửa chữa / Repair catalog",
              bold=True, size=10, h_align="left")
    row += 1

    # Header hàng bảng
    for col_i, (txt, width) in enumerate([
        ("STT", 6), ("Repair catalog / Hạng mục sửa chữa", 52),
        ("Date / Ngày", 18), ("Passed / Thông qua", 18)
    ], start=1):
        _set_cell(ws, row, col_i, txt,
                  bold=True, size=9, color=WHITE,
                  fill_color=BLUE_HDR, border=brd_all)
    ws.row_dimensions[row].height = 20
    row += 1

    # 12 dòng hạng mục
    for i in range(1, 13):
        noi_dung = hang_muc[i - 1] if (i - 1) < len(hang_muc) else ""
        fill = YELLOW if i % 2 == 0 else WHITE
        _set_cell(ws, row, 1, f"{i}", size=9, border=brd_all, fill_color=fill)
        _set_cell(ws, row, 2, noi_dung, size=9, border=brd_all,
                  h_align="left", fill_color=fill)
        _set_cell(ws, row, 3, "", size=9, border=brd_all, fill_color=fill)
        _set_cell(ws, row, 4, "", size=9, border=brd_all, fill_color=fill)
        ws.row_dimensions[row].height = 16
        row += 1

    row += 1

    # ── Footer thông tin tài liệu ────────────────────────────────
    footer_data = [
        ("Số Đặt Hàng / Order number", cong_so),
        ("Nhân viên / Technician",     nhan_vien),
        ("Tài liệu quản lý",           "QT-NT-029-1A"),
        ("Ngày ban hành / Edition date", "24/04/2025"),
    ]
    for lbl, val in footer_data:
        _set_cell(ws, row, 1, lbl, bold=True, size=9,
                  fill_color=BLUE_CELL, border=brd_all,
                  h_align="left")
        ws.merge_cells(f"B{row}:D{row}")
        _set_cell(ws, row, 2, val, size=9, border=brd_all, h_align="left")
        ws.row_dimensions[row].height = 16
        row += 1

    # ── Xuất bytes ──────────────────────────────────────────────
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


# ============================================================
# FRAGMENT: CHI TIẾT TASK NHÂN VIÊN (rerun cục bộ khi tick checkbox / đổi trạng thái)
# ============================================================
@st.fragment
def _fragment_chi_tiet_task(hang: dict, ds_trang_thai: list):
    """
    Hiển thị toàn bộ thông tin một task cho nhân viên:
    - Thông tin đầy đủ (công ty, công số, năm, mô tả, hạn, người phê duyệt)
    - Dropdown chọn trạng thái (lưu ngay khi đổi) với CSS badge màu
    - Checklist tương tác (tick → lưu lên Google Sheets)
    - Công việc con (card đẹp)
    - Upload ảnh + xuất PDF
    Dùng @st.fragment nên chỉ rerun vùng này, không reload toàn trang.
    """
    # ── CSS toàn cục cho fragment này ────────────────────────
    st.markdown("""
    <style>
    /* Badge trạng thái */
    .badge-trang-thai {
        display: inline-block;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.3px;
        border: 1.5px solid;
        white-space: nowrap;
    }
    /* Card công việc con */
    .cv-con-card {
        background: #f8f7ff;
        border: 1px solid #e0dcff;
        border-radius: 12px;
        padding: 8px 12px;
        margin-bottom: 4px;
    }
    .cv-con-card.done {
        background: #f0fdf4;
        border-color: #bbf7d0;
        opacity: 0.75;
    }
    .cv-con-meta {
        font-size: 0.8rem;
        color: #6b7280;
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        margin-top: 2px;
        margin-left: 28px;
        padding-bottom: 4px;
    }
    .cv-con-meta span { display:inline-flex; align-items:center; gap:3px; }
    /* Checklist done: giữ nguyên chữ, chỉ tick màu đỏ */
    /* Ghost delete button */
    button[title="Xóa"], button[title="Xóa công việc này"] {
        background: transparent !important;
        border: none !important;
        color: #d1d5db !important;
        box-shadow: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Bảng màu trạng thái ───────────────────────────────────
    _MAU_TRANG_THAI = {
        "Đang Kiểm Tra":           ("#1d4ed8", "#dbeafe"),   # xanh dương
        "Đã Phê Duyệt":            ("#15803d", "#dcfce7"),   # xanh lá
        "Đã Báo Giá":              ("#b45309", "#fef3c7"),   # cam
        "Có Đơn":                  ("#7c3aed", "#ede9fe"),   # tím
        "Chờ Giao":                ("#a16207", "#fef9c3"),   # vàng
        "Đã Hoàn Thành - Giao Máy":("#166534", "#bbf7d0"),   # xanh đậm
        "Đã Xuất Hóa Đơn":        ("#374151", "#f3f4f6"),   # xám
        "Bảo Hành - Trả Lại":     ("#b91c1c", "#fee2e2"),   # đỏ
        "Chờ Làm":                 ("#dc2626", "#fee2e2"),
        "Đang Làm":                ("#d97706", "#fef3c7"),
        "Hoàn Thành":              ("#16a34a", "#dcfce7"),
    }

    task_id    = int(hang.get("ID", 0))
    trang_thai = hang.get("Trạng Thái", "Chờ Làm")
    # Dùng session_state để badge cập nhật ngay khi đổi, không cần rerun
    tt_hien_thi = st.session_state.get(f"tt_select_{task_id}", trang_thai)
    tt_color, tt_bg = _MAU_TRANG_THAI.get(tt_hien_thi, ("#6b7280", "#f3f4f6"))

    # Khởi đầu danh sách ảnh từ hang (nếu chưa có trong session_state)
    _anh_key = f"anh_editable_{task_id}"
    if _anh_key not in st.session_state:
        st.session_state[_anh_key] = doc_danh_sach_anh(str(hang.get("Link Ảnh", "")))

    # ── Thông tin chính + trạng thái (full width, không chia cột) ──────────
    # Trạng thái lên đầu
    st.markdown(
        f'<div style="margin:0 0 6px 0">'
        f'<span class="badge-trang-thai" style="color:{tt_color};background:{tt_bg};border-color:{tt_color}40;">'
        f'{tt_hien_thi}</span></div>',
        unsafe_allow_html=True,
    )
    idx_hien_tai = ds_trang_thai.index(trang_thai) if trang_thai in ds_trang_thai else 0
    tt_moi = st.selectbox(
        "Chọn trạng thái",
        options=ds_trang_thai,
        index=idx_hien_tai,
        key=f"tt_select_{task_id}",
        label_visibility="collapsed",
    )
    if tt_moi != trang_thai:
        with st.spinner("Đang lưu..."):
            cap_nhat_trang_thai(task_id, tt_moi)
            lay_danh_sach_cong_viec.clear()
        # Gửi thông báo cho tất cả khi trạng thái thay đổi
        _ten_task  = hang.get("Tên Công Việc", "")
        _nguoi_doi = st.session_state.get("ho_ten", "")
        _ct        = hang.get("Công Ty", "")
        _tb_tt = (
            f"🔄 **{_nguoi_doi}** đã chuyển công việc "
            f"**{_ten_task}**"
            + (f" ({_ct})" if _ct else "")
            + f" từ **{trang_thai}** → **{tt_moi}**"
        )
        them_thong_bao_tat_ca(_tb_tt, task_id=task_id, loai="trang_thai", tru_nguoi="")

    st.markdown("---")
    # Công ty, Công số, Năm, Hạn, Ngày tạo
    st.markdown(f"🏢 **Công ty:** `{hang.get('Công Ty', '')}`")
    st.markdown(
        f"📄 **Công số:** `{hang.get('Công Số', '')}` &nbsp;·&nbsp; "
        f"📅 **Năm:** `{hang.get('Năm', '')}`"
    )
    if hang.get("Người Phê Duyệt"):
        st.markdown(f"✅ **Người phê duyệt:** `{hang.get('Người Phê Duyệt', '')}`")
    # ── Hạn Hoàn Thành (nhân viên có thể chỉnh) ─────────────────────────────
    _hht_hien_tai = hang.get("Hạn Hoàn Thành", "") or ""
    try:
        from datetime import date as _date
        _hht_default = _date.fromisoformat(_hht_hien_tai.strip()) if _hht_hien_tai.strip() else None
    except Exception:
        _hht_default = None

    _hht_val = st.date_input(
        "📅 Hạn hoàn thành",
        value=_hht_default,
        format="YYYY-MM-DD",
        key=f"hht_{task_id}",
    )
    _hht_str = _hht_val.strftime("%Y-%m-%d") if _hht_val else ""
    if _hht_str != _hht_hien_tai.strip():
        with st.spinner("Đang lưu..."):
            cap_nhat_han_hoan_thanh(task_id, _hht_str)

    st.markdown(f"🕐 **Ngày tạo:** `{hang.get('Ngày Tạo', '')}`")

    # ── Ngày Kết Thúc (nhân viên tự điền) ───────────────────────────────────
    _nkt_hien_tai = hang.get("Ngày Kết Thúc", "") or ""
    try:
        from datetime import date as _date
        _nkt_default = _date.fromisoformat(_nkt_hien_tai.strip()) if _nkt_hien_tai.strip() else None
    except Exception:
        _nkt_default = None

    _nkt_val = st.date_input(
        "📅 Ngày kết thúc",
        value=_nkt_default,
        format="YYYY-MM-DD",
        key=f"nkt_{task_id}",
    )
    _nkt_str = _nkt_val.strftime("%Y-%m-%d") if _nkt_val else ""
    if _nkt_str != _nkt_hien_tai.strip():
        with st.spinner("Đang lưu..."):
            cap_nhat_ngay_ket_thuc(task_id, _nkt_str)

    # ── Thông số kỹ thuật / thương mại ──────────────────────────────────────
    _thong_so = {
        "🔧 Loại Máy":     hang.get("Loại Máy", ""),
        "🛠️ Tình Trạng":   hang.get("Tình Trạng", ""),
        "⚡ Công Suất":    hang.get("Công Suất", ""),
        "🔩 Số Cực":       hang.get("Số Cực", ""),
        "🏷️ Mã Số":        hang.get("Mã Số", ""),
        "📄 Số PO Nội Bộ": hang.get("Số PO Nội Bộ", ""),
        "📋 Số PO KH/HĐ":  hang.get("Số PO KH/HĐ", ""),
        "💰 Số Báo Giá":   hang.get("Số Báo Giá", ""),
    }
    _co_du_lieu = {k: v for k, v in _thong_so.items() if v and str(v).strip()}
    if _co_du_lieu:
        st.markdown("---")
        _ts_html = "<div style='display:grid;grid-template-columns:1fr 1fr;gap:10px 16px;margin:4px 0;'>"
        for _label, _val in _co_du_lieu.items():
            _ts_html += (
                f"<div style='min-width:0;'>"
                f"<div style='font-size:0.75rem;color:#6b7280;font-weight:600;margin-bottom:2px;'>{_label}</div>"
                f"<div style='font-size:0.92rem;color:#09ab3b;font-weight:700;word-break:break-word;font-family:monospace;'>{_val}</div>"
                f"</div>"
            )
        _ts_html += "</div>"
        st.markdown(_ts_html, unsafe_allow_html=True)

    if hang.get("Mô Tả"):
        with st.expander("📝 Xem mô tả chi tiết"):
            st.write(hang.get("Mô Tả", ""))

    st.divider()

    # ── Checklist ─────────────────────────────────────────────
    raw_cl = hang.get("Checklist", "") or "[]"
    try:
        _cl_parsed = json.loads(raw_cl) if raw_cl else []
    except Exception:
        _cl_parsed = []

    _cl_key = f"cl_editable_{task_id}"
    if _cl_key not in st.session_state:
        st.session_state[_cl_key] = [
            ({"text": x, "done": False} if isinstance(x, str) else x)
            for x in _cl_parsed
        ]
    _checklist = st.session_state[_cl_key]

    so_xong = sum(1 for it in _checklist if isinstance(it, dict) and it.get("done"))
    st.markdown(
        f"**☑️ Checklist** &nbsp;<span style='color:#6b7280;font-size:0.82rem;'>{so_xong}/{len(_checklist)} mục</span>",
        unsafe_allow_html=True,
    )

    _mk_cl = f"dlgcl{task_id}"
    st.markdown(f"""<style>
    [data-testid="stHorizontalBlock"]:has(.{_mk_cl}) {{
        flex-wrap: nowrap !important; align-items: center !important; gap: 6px !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{_mk_cl}) > [data-testid="stColumn"]:first-child {{
        flex: 0 0 36px !important; min-width: 36px !important; max-width: 36px !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{_mk_cl}) > [data-testid="stColumn"]:last-child {{
        flex: 1 1 0% !important; min-width: 0 !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{_mk_cl}) [data-testid="stCheckbox"] {{ margin:0 !important; }}
    [data-testid="stHorizontalBlock"]:has(.{_mk_cl}) p {{
        margin: 0 !important; font-size: 0.93rem !important; color: #1e1b4b;
        padding: 4px 2px;
    }}
    </style>""", unsafe_allow_html=True)

    def _cb_cl_done(idx):
        val = st.session_state.get(f"dlg_ck_{task_id}_{idx}", False)
        st.session_state[_cl_key][idx]["done"] = val
        cap_nhat_checklist(task_id, st.session_state[_cl_key])

    for _ci, _cit in enumerate(_checklist):
        if isinstance(_cit, str):
            _cit = {"text": _cit, "done": False}
            _checklist[_ci] = _cit
        _done_v = bool(_cit.get("done", False))
        _txt0   = _cit.get("text", "") or f"Mục {_ci+1}"
        col_ck, col_txt = st.columns([0.5, 9], gap="small")
        with col_ck:
            st.markdown(f"<span class='{_mk_cl}' style='display:none'></span>", unsafe_allow_html=True)
            st.checkbox("", value=_done_v, key=f"dlg_ck_{task_id}_{_ci}",
                        label_visibility="collapsed",
                        on_change=_cb_cl_done, args=(_ci,))
        with col_txt:
            st.markdown(f"<p>{_txt0}</p>", unsafe_allow_html=True)

    st.divider()

    # ── Công việc con ─────────────────────────────────────────
    raw_cv = hang.get("Công Việc Con", "") or "[]"
    try:
        _cv_parsed = json.loads(raw_cv) if raw_cv else []
    except Exception:
        _cv_parsed = []

    _cv_key = f"cv_editable_{task_id}"
    if _cv_key not in st.session_state:
        st.session_state[_cv_key] = [
            {
                "ten":       cv.get("ten", cv.get("Tên", "")),
                "nhan_vien": cv.get("nhan_vien", cv.get("Nhân Viên", cv.get("nguoi", ""))),
                "done":      bool(cv.get("done", False)),
                "anh":       cv.get("anh", []),
            }
            for cv in _cv_parsed if isinstance(cv, dict)
        ]
    ds_cv_con = st.session_state[_cv_key]
    _ds_nv_cv = ["-- Không chọn --"] + lay_danh_sach_nhan_vien()



    _done_cv = sum(1 for cv in ds_cv_con if cv.get("done"))
    st.markdown(
        f"**📋 Công Việc Con** &nbsp;<span style='color:#6b7280;font-size:0.82rem;'>{_done_cv}/{len(ds_cv_con)} hoàn thành</span>",
        unsafe_allow_html=True,
    )

    _mk_cv = f"dlgcv{task_id}"
    st.markdown(f"""<style>
    [data-testid="stHorizontalBlock"]:has(.{_mk_cv}) {{
        flex-wrap: nowrap !important; align-items: center !important; gap: 6px !important;
        margin-bottom: 2px !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{_mk_cv}) > [data-testid="stColumn"]:nth-child(1) {{
        flex: 0 0 32px !important; min-width: 32px !important; max-width: 32px !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{_mk_cv}) > [data-testid="stColumn"]:nth-child(2) {{
        flex: 1 1 0% !important; min-width: 0 !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{_mk_cv}) > [data-testid="stColumn"]:nth-child(3) {{
        flex: 0 0 36px !important; min-width: 36px !important; max-width: 36px !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{_mk_cv}) [data-testid="stCheckbox"] {{ margin: 0 !important; }}
    [data-testid="stHorizontalBlock"]:has(.{_mk_cv}) p {{
        margin: 0 !important; font-size: 0.93rem !important; font-weight: 600;
        color: #1e1b4b; padding: 2px 0;
    }}
    [data-testid="stHorizontalBlock"]:has(.{_mk_cv}) [data-testid="stColumn"]:nth-child(3) button {{
        background: transparent !important; border: none !important;
        box-shadow: none !important; color: #ef4444 !important;
        font-size: 1.1rem !important; padding: 2px 4px !important; min-height: 32px !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{_mk_cv}) [data-testid="stColumn"]:nth-child(3) button:hover {{
        background: #fee2e2 !important; border-radius: 6px !important;
    }}
    .cv-nv-row-{task_id} [data-testid="stSelectbox"] > div > div {{
        font-size: 0.9rem !important; border-color: #e0d7ff !important;
        background: #f5f3ff !important; color: #4c1d95 !important;
        min-height: 34px !important;
    }}
    .cv-nv-row-{task_id} [data-testid="stSelectbox"] [class*="singleValue"],
    .cv-nv-row-{task_id} [data-testid="stSelectbox"] [class*="SingleValue"] {{
        direction: ltr !important; font-size: 0.9rem !important;
        overflow: visible !important; white-space: nowrap !important;
        text-overflow: clip !important; max-width: none !important;
    }}
    .cv-nv-row-{task_id} label {{ font-size: 0.78rem !important; color: #6b7280 !important; }}
    .cv-item-wrap-{task_id} {{
        border-bottom: 1px solid #f3f4f6;
        padding: 4px 0 2px 0; margin-bottom: 0;
    }}
    .cv-item-wrap-{task_id}.done {{ opacity: 0.6; }}
    </style>""", unsafe_allow_html=True)

    def _cb_cv_done(i):
        val = st.session_state.get(f"dlg_cv_ck_{task_id}_{i}", False)
        st.session_state[_cv_key][i]["done"] = val
        if val:
            st.session_state[_cv_key][i]["ngay_hoan_thanh"] = datetime.now().strftime("%Y-%m-%d")
        else:
            st.session_state[_cv_key][i].pop("ngay_hoan_thanh", None)
        _save_cv_to_sheet(task_id, _cv_key)

    def _cb_cv_nv(i):
        val    = st.session_state.get(f"dlg_cv_nv_{task_id}_{i}", "-- Không chọn --")
        nv_cu  = st.session_state[_cv_key][i].get("nhan_vien", "")
        nv_moi = "" if val == "-- Không chọn --" else val
        st.session_state[_cv_key][i]["nhan_vien"] = nv_moi
        # Gửi thông báo nếu nhân viên thay đổi
        if nv_moi and nv_moi != nv_cu:
            ten_cv      = st.session_state[_cv_key][i].get("ten", "")
            nguoi_giao  = st.session_state.get("ho_ten", "")
            ten_task_tb = hang.get("Tên Công Việc", f"Task #{task_id}")
            cong_ty_tb  = hang.get("Công Ty", "")
            _suffix     = f"**{ten_task_tb}**" + (f" ({cong_ty_tb})" if cong_ty_tb else "")
            them_thong_bao(nv_moi,
                f"🔧 Bạn được giao việc: **{ten_cv}** • {_suffix}",
                task_id=task_id, loai="cong_viec_con")
            them_thong_bao_tat_ca(
                f"🔧 **{nguoi_giao}** đã giao **{ten_cv}** cho **{nv_moi}** • {_suffix}",
                task_id=task_id, loai="cong_viec_con", tru_nguoi=nv_moi)
        _save_cv_to_sheet(task_id, _cv_key)

    def _cb_cv_del(i):
        if 0 <= i < len(st.session_state[_cv_key]):
            st.session_state[_cv_key].pop(i)
            for k in list(st.session_state.keys()):
                if k.startswith(f"dlg_cv_nv_{task_id}_"):
                    del st.session_state[k]
            _save_cv_to_sheet(task_id, _cv_key)

    def _cb_del_cv_media(cvi, url_m):
        _cvl = st.session_state.get(_cv_key, [])
        if 0 <= cvi < len(_cvl):
            _cvl[cvi]["anh"] = [u for u in _cvl[cvi].get("anh", []) if u != url_m]
            _save_cv_to_sheet(task_id, _cv_key)

    for _cvi, cv in enumerate(ds_cv_con):
        if not isinstance(cv, dict): continue
        _tcv  = cv.get("ten", f"Việc {_cvi+1}")
        _nvcv = cv.get("nhan_vien", "") or ""
        _dcv  = bool(cv.get("done", False))
        _nv_idx = _ds_nv_cv.index(_nvcv) if _nvcv in _ds_nv_cv else 0
        _wrap_cls = f"cv-item-wrap-{task_id}" + (" done" if _dcv else "")

        st.markdown(f"<div class='{_wrap_cls}'>", unsafe_allow_html=True)
        # Hàng 1: checkbox + tên công việc + nút xóa
        col_ck, col_txt, col_del = st.columns([0.4, 5, 0.5], gap="small")
        with col_ck:
            st.markdown(f"<span class='{_mk_cv}' style='display:none'></span>", unsafe_allow_html=True)
            st.checkbox("", value=_dcv, key=f"dlg_cv_ck_{task_id}_{_cvi}",
                        label_visibility="collapsed",
                        on_change=_cb_cv_done, args=(_cvi,))
        with col_txt:
            st.markdown(f"<p>{_tcv}</p>", unsafe_allow_html=True)
        with col_del:
            st.button("🗑️", key=f"dlg_cv_del_{task_id}_{_cvi}",
                      use_container_width=True,
                      on_click=_cb_cv_del, args=(_cvi,))
        # Hàng 2: selectbox nhân viên full width
        st.markdown(f"<div class='cv-nv-row-{task_id}'>", unsafe_allow_html=True)
        st.selectbox("👤 Nhân viên thực hiện", options=_ds_nv_cv, index=_nv_idx,
                     key=f"dlg_cv_nv_{task_id}_{_cvi}",
                     on_change=_cb_cv_nv, args=(_cvi,))
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Hình / Video cho công việc con ────────────────────
        _cv_media = cv.get("anh", [])
        _exp_lbl = f"📎 Hình/Video ({len(_cv_media)})" if _cv_media else "📎 Thêm hình/video"
        with st.expander(_exp_lbl, expanded=False):
            if _cv_media:
                _cols_m = st.columns(min(len(_cv_media), 3))
                for _mi, _url_m in enumerate(_cv_media):
                    with _cols_m[_mi % 3]:
                        if "/view" in _url_m:
                            st.markdown(f"🎬 [Video {_mi + 1}]({_url_m})", unsafe_allow_html=False)
                        else:
                            _hien_thi_anh_drive(_url_m, use_container_width=True)
                        st.button("🗑️ Xoá", key=f"del_cv_m_{task_id}_{_cvi}_{_mi}",
                                  use_container_width=True,
                                  on_click=_cb_del_cv_media, args=(_cvi, _url_m))
            _up_key_m = f"up_cv_m_{task_id}_{_cvi}"
            st.file_uploader(
                "Chọn hình hoặc video",
                type=["jpg", "jpeg", "png", "mp4", "mov", "avi"],
                accept_multiple_files=True,
                key=_up_key_m,
                label_visibility="collapsed",
            )
            if st.button("📤 Upload", key=f"btn_up_cv_m_{task_id}_{_cvi}", use_container_width=True):
                _files_m = st.session_state.get(_up_key_m) or []
                if _files_m:
                    with st.spinner("Đang upload..."):
                        _cvl = st.session_state.get(_cv_key, [])
                        for _fm in _files_m:
                            _new_url = _tai_media_len_drive(_fm)
                            _cvl[_cvi].setdefault("anh", []).append(_new_url)
                    _save_cv_to_sheet(task_id, _cv_key)
                    st.rerun(scope="fragment")
                else:
                    st.warning("Chưa chọn file!")

    # ── Thêm công việc con từ danh sách ──────────────────────
    _ds_cd_all = ["-- Chọn công đoạn --"] + lay_ten_cac_cong_doan()
    _cv_add_v  = f"dlg_cv_add_v_{task_id}"
    if _cv_add_v not in st.session_state: st.session_state[_cv_add_v] = 0
    _v = st.session_state[_cv_add_v]

    col_cd, col_nv_add, col_btn_add = st.columns([3, 3, 1], vertical_alignment="bottom")
    with col_cd:
        st.selectbox("Công đoạn", options=_ds_cd_all,
                     key=f"dlg_cv_new_cd_{task_id}_{_v}",
                     label_visibility="visible")
    with col_nv_add:
        st.selectbox("Nhân viên", options=_ds_nv_cv,
                     key=f"dlg_cv_new_nv_{task_id}_{_v}",
                     label_visibility="visible")
    with col_btn_add:
        def _cb_cv_add():
            cd_v  = st.session_state.get(f"dlg_cv_new_cd_{task_id}_{_v}", "-- Chọn công đoạn --")
            nv_v  = st.session_state.get(f"dlg_cv_new_nv_{task_id}_{_v}", "-- Không chọn --")
            if cd_v and cd_v != "-- Chọn công đoạn --":
                nv_moi = "" if nv_v == "-- Không chọn --" else nv_v
                st.session_state[_cv_key].append({
                    "ten":       cd_v,
                    "nhan_vien": nv_moi,
                    "done":      False,
                })
                # Gửi thông báo cho nhân viên được giao + broadcast cho tất cả
                if nv_moi:
                    nguoi_giao  = st.session_state.get("ho_ten", "")
                    ten_task_tb = hang.get("Tên Công Việc", f"Task #{task_id}")
                    cong_ty_tb  = hang.get("Công Ty", "")
                    _suffix     = f"**{ten_task_tb}**" + (f" ({cong_ty_tb})" if cong_ty_tb else "")
                    them_thong_bao(nv_moi,
                        f"🔧 Bạn được giao việc: **{cd_v}** • {_suffix}",
                        task_id=task_id, loai="cong_viec_con")
                    them_thong_bao_tat_ca(
                        f"🔧 **{nguoi_giao}** đã giao **{cd_v}** cho **{nv_moi}** • {_suffix}",
                        task_id=task_id, loai="cong_viec_con", tru_nguoi=nv_moi)
                st.session_state[_cv_add_v] += 1
                _save_cv_to_sheet(task_id, _cv_key)
        st.button("＋", key=f"dlg_cv_add_{task_id}",
                  use_container_width=True, on_click=_cb_cv_add)

    st.divider()

    # ── Ảnh đo lường theo từng nhãn ──────────────────────────
    st.markdown("**📐 Ảnh Đo Lường**")


    _do_key = f"do_luong_{task_id}"
    if _do_key not in st.session_state:
        st.session_state[_do_key] = doc_anh_do_luong(str(hang.get("Ảnh Đo Lường", "") or ""))

    _fragment_upload_do_luong(task_id, _do_key)

    # ── Ảnh Nghiệm Thu ───────────────────────────────────────
    st.divider()
    _fragment_upload_anh_nghiem_thu(task_id, _anh_key)

    # PDF
    tt_pdf = st.session_state.get(f"tt_select_{task_id}", trang_thai)
    if tt_pdf == "Đã Hoàn Thành - Giao Máy" or "Hoàn Thành" in tt_pdf:
        st.divider()
        if st.button("📊 Tạo Biên Bản Excel", key=f"pdf_{task_id}", use_container_width=True):
            with st.spinner("Đang tạo Excel..."):
                df_moi = lay_danh_sach_cong_viec()
                rows = df_moi[df_moi["ID"].astype(str) == str(task_id)]
                if not rows.empty:
                    du_lieu_excel = tao_excel_nghiem_thu(rows.iloc[0].to_dict())
                    st.download_button(
                        "💾 Tải Xuống Excel",
                        data=du_lieu_excel,
                        file_name=f"BBNT_task_{task_id}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_pdf_{task_id}",
                        use_container_width=True,
                    )


# ============================================================
# FRAGMENT: CHECKLIST & CÔNG VIỆC CON (rerun cục bộ, không reload toàn trang)
# ============================================================

_FRAGMENT_CSS = """
<style>
.cl-card {
    display: flex; align-items: center; gap: 10px;
    border-radius: 12px; padding: 11px 14px;
    margin-bottom: 4px; border: 1.5px solid #e5e7eb;
    background: #fff; transition: background 0.2s;
}
.cl-card.cl-done {
    background: #f0fdf4; border-color: #86efac;
}
.cl-num {
    flex-shrink: 0; width: 26px; height: 26px; border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 0.68rem; font-weight: 800; color: #fff;
    background: #7c3aed;
}
.cl-card.cl-done .cl-num { background: #16a34a; }
.cl-txt {
    flex: 1; font-size: 0.9rem; color: #1e293b; word-break: break-word;
}
.cl-card.cl-done .cl-txt {
    color: #1e293b;
}
.cl-badge {
    flex-shrink: 0; font-size: 0.68rem; font-weight: 700;
    color: #16a34a; background: #dcfce7;
    padding: 2px 8px; border-radius: 20px;
}
/* Ép 2 nút nằm cùng hàng trên mọi màn hình */
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]) {
    flex-wrap: nowrap !important;
    gap: 6px !important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    min-width: 0 !important;
    flex: 1 1 0 !important;
    width: 50% !important;
}
.cl-btn-row { margin: 0 0 10px 0; gap: 6px; display: flex; }
/* Nút icon nhỏ trong checklist (row có checkbox) */
[data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"]) .stButton > button {
    background: transparent !important;
    border: 1.5px solid #e5e7eb !important;
    box-shadow: none !important;
    color: #6b7280 !important;
    font-size: 1rem !important;
    padding: 3px 6px !important;
    min-height: 32px !important;
    border-radius: 8px !important;
}
[data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"]) .stButton > button:hover {
    background: #f3f4f6 !important;
    border-color: #9ca3af !important;
    transform: none !important;
    box-shadow: none !important;
}
/* CVC card */
.cvc-card {
    border: 1.5px solid #e5e7eb; border-radius: 12px;
    padding: 10px 14px 8px; background: #fafafa;
    margin-bottom: 4px;
}
.cvc-card.cvc-done { background: #f0fdf4; border-color: #86efac; }
.cvc-title { font-size: 0.9rem; font-weight: 700; color: #1e293b; }
.cvc-card.cvc-done .cvc-title { color: #1e293b; }
.cvc-meta { font-size: 0.78rem; color: #64748b; margin-top: 3px; }
.cvc-badge {
    display: inline-block; font-size: 0.68rem; font-weight: 700;
    color: #16a34a; background: #dcfce7;
    padding: 2px 8px; border-radius: 20px; margin-top: 4px;
}
</style>
"""

# 12 mục checklist mặc định cho motor repair
_MAC_DINH_CHECKLIST = [
    {"text": "Quấn",                      "done": False},
    {"text": "Thay bạc đạn trước",         "done": False},
    {"text": "Thay bạc đạn sau",           "done": False},
    {"text": "Thay phốt",                  "done": False},
    {"text": "Đóng sơ mi trước",           "done": False},
    {"text": "Đóng sơ mi sau",             "done": False},
    {"text": "Thay tụ",                    "done": False},
    {"text": "Thay cánh quạt",             "done": False},
    {"text": "Thay dây nguồn/dây điện",    "done": False},
    {"text": "Thay nắp chụp",              "done": False},
    {"text": "Đấp cốt",                    "done": False},
    {"text": "Gia công mới cốt",           "done": False},
]

# Màu nền theo trạng thái (cho board)
_STATUS_BG = {
    "Đang Kiểm Tra":              "#00b4d8",
    "Đã Phê Duyệt":               "#f44336",
    "Đã Báo Giá":                 "#f9c74f",
    "Có Đơn":                     "#4361ee",
    "Chờ Giao":                   "#f8961e",
    "Đã Hoàn Thành - Giao Máy":   "#4caf50",
    "Đã Xuất Hóa Đơn":            "#78909c",
    "Bảo Hành - Trả Lại":         "#9b5de5",
    "Chờ Làm":                    "#ef476f",
    "Đang Làm":                   "#ffd166",
    "Hoàn Thành":                 "#06d6a0",
}

# Màu chữ + nền nhạt cho header kanban board (text_color, bg_color)
_STATUS_HEADER_COLOR = {
    "Đang Kiểm Tra":              ("#0077a8", "#e0f7fc"),
    "Đã Phê Duyệt":               ("#b71c1c", "#fce4e4"),
    "Đã Báo Giá":                 ("#7a5c00", "#fff8dc"),
    "Có Đơn":                     ("#2b3eb5", "#e8ecff"),
    "Chờ Giao":                   ("#b35c00", "#fff3e0"),
    "Đã Hoàn Thành - Giao Máy":   ("#1b5e20", "#e6f4ea"),
    "Đã Xuất Hóa Đơn":            ("#37474f", "#eceff1"),
    "Bảo Hành - Trả Lại":         ("#5e1891", "#f3e5ff"),
    "Chờ Làm":                    ("#b71c1c", "#fce4e4"),
    "Đang Làm":                   ("#7a5c00", "#fff8dc"),
    "Hoàn Thành":                 ("#004d40", "#e0f2f1"),
}


@st.fragment
def _fragment_checklist(key_prefix: str, show_done: bool = True, default_items=None):
    cl_key   = f"{key_prefix}_checklist"
    cl_inp_v = f"{key_prefix}_cl_inp_v"
    if cl_key   not in st.session_state:
        st.session_state[cl_key] = [dict(x) for x in default_items] if default_items else []
    if cl_inp_v not in st.session_state: st.session_state[cl_inp_v] = 0

    st.markdown(_FRAGMENT_CSS, unsafe_allow_html=True)
    st.markdown("**☑️ Checklist**")

    items = st.session_state[cl_key]

    _xoa = None

    # CSS dùng :has() với marker bên trong cột — đây là cách duy nhất hoạt động
    # vì st.markdown div KHÔNG wrap st.columns trong DOM thực tế
    mk = f"clm{key_prefix}"  # class marker ngắn
    st.markdown(f"""<style>
    /* Row chứa marker → luôn nằm ngang, không wrap */
    [data-testid="stHorizontalBlock"]:has(.{mk}) {{
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 4px !important;
    }}
    /* Cột checkbox: cố định 36px */
    [data-testid="stHorizontalBlock"]:has(.{mk}) > [data-testid="stColumn"]:first-child {{
        flex: 0 0 36px !important; min-width: 36px !important; max-width: 36px !important;
        overflow: visible !important;
    }}
    /* Cột text: chiếm phần còn lại */
    [data-testid="stHorizontalBlock"]:has(.{mk}) > [data-testid="stColumn"]:nth-child(2) {{
        flex: 1 1 0% !important; min-width: 0 !important; overflow: hidden !important;
    }}
    /* Cột xóa: cố định 36px */
    [data-testid="stHorizontalBlock"]:has(.{mk}) > [data-testid="stColumn"]:last-child {{
        flex: 0 0 36px !important; min-width: 36px !important; max-width: 36px !important;
    }}
    /* Text input trông như plain text */
    [data-testid="stHorizontalBlock"]:has(.{mk}) [data-testid="stTextInput"] input {{
        border: 1.5px solid transparent !important;
        background: transparent !important; box-shadow: none !important;
        padding: 3px 6px !important; font-size: 0.93rem !important;
        color: #1e1b4b !important; min-height: 32px !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{mk}) [data-testid="stTextInput"] input:focus {{
        border-color: #7c3aed !important; background: white !important;
        border-radius: 6px !important;
        box-shadow: 0 0 0 2px rgba(124,58,237,0.12) !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{mk}) [data-testid="stTextInput"] > div {{
        border: none !important; box-shadow: none !important; background: transparent !important;
    }}
    /* Nút xóa: transparent, đỏ */
    [data-testid="stHorizontalBlock"]:has(.{mk}) [data-testid="stColumn"]:last-child button {{
        background: transparent !important; border: none !important;
        box-shadow: none !important; color: #ef4444 !important;
        font-size: 1.1rem !important; padding: 2px 4px !important;
        min-height: 32px !important; transform: none !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{mk}) [data-testid="stColumn"]:last-child button:hover {{
        background: #fee2e2 !important; border-radius: 6px !important;
        box-shadow: none !important; transform: none !important;
    }}
    /* Bỏ margin thừa của checkbox */
    [data-testid="stHorizontalBlock"]:has(.{mk}) [data-testid="stCheckbox"] {{
        margin: 0 !important;
    }}
    </style>""", unsafe_allow_html=True)

    def _save_cl(i):
        val = st.session_state.get(f"{key_prefix}_cl_txt_{i}", "").strip()
        if val:
            st.session_state[cl_key][i]["text"] = val

    for i, item in enumerate(items):
        txt      = item.get("text", "") or f"Mục {i+1}"
        done_val = bool(item.get("done", False))

        col_ck, col_txt, col_del = st.columns([0.6, 8.5, 0.7], gap="small")
        with col_ck:
            # Marker ở đây để CSS :has() tìm đúng HorizontalBlock này
            st.markdown(f"<span class='{mk}' style='display:none'></span>", unsafe_allow_html=True)
            new_done = st.checkbox(
                "", value=done_val,
                key=f"{key_prefix}_ck_{i}",
                label_visibility="collapsed",
            )
            if new_done != done_val:
                st.session_state[cl_key][i]["done"] = new_done
                st.rerun()
        with col_txt:
            st.text_input(
                "", value=txt,
                key=f"{key_prefix}_cl_txt_{i}",
                label_visibility="collapsed",
                on_change=_save_cl, args=(i,),
            )
        with col_del:
            if st.button("🗑️", key=f"{key_prefix}_cl_del_{i}", use_container_width=True):
                _xoa = i

    if _xoa is not None:
        st.session_state[cl_key].pop(_xoa)
        for k in list(st.session_state.keys()):
            if k.startswith(f"{key_prefix}_cl_txt_"):
                del st.session_state[k]
        st.rerun()

    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
    col_i, col_b = st.columns([5, 2])
    with col_i:
        moi = st.text_input(
            "", placeholder="Nhập tên checklist...",
            key=f"{key_prefix}_cl_inp_{st.session_state[cl_inp_v]}",
            label_visibility="collapsed",
        )
    with col_b:
        if st.button("＋ Thêm", key=f"{key_prefix}_cl_add",
                     use_container_width=True):
            val = st.session_state.get(
                f"{key_prefix}_cl_inp_{st.session_state[cl_inp_v]}", "").strip()
            if val:
                st.session_state[cl_key].append({"text": val, "done": False})
                st.session_state[cl_inp_v] += 1
                st.rerun()



@st.fragment
def _fragment_cong_viec_con(key_prefix: str, ds_nhan_vien: list, show_done: bool = True):
    cv_key      = f"{key_prefix}_cong_viec_con"
    cv_inp_v    = f"{key_prefix}_cv_inp_v"
    cv_seeded   = f"{key_prefix}_cv_seeded"

    # Lần đầu: seed tất cả công đoạn sẵn vào danh sách
    if cv_seeded not in st.session_state:
        ds_cd = lay_ten_cac_cong_doan()
        st.session_state[cv_key]    = [{"ten": cd, "nhan_vien": "", "done": False} for cd in ds_cd]
        st.session_state[cv_inp_v]  = 0
        st.session_state[cv_seeded] = True
    else:
        if cv_key   not in st.session_state: st.session_state[cv_key]   = []
        if cv_inp_v not in st.session_state: st.session_state[cv_inp_v] = 0

    st.markdown(_FRAGMENT_CSS, unsafe_allow_html=True)
    st.markdown("**📋 Công Việc Con**")

    # CSS dùng :has() với marker bên trong cột — không bị override bởi Streamlit mobile wrap
    mk_cv = f"cvcm{key_prefix}"
    nv_opts = ["-- Không chọn --"] + ds_nhan_vien
    st.markdown(f"""<style>
    /* Hàng 1: checkbox + tên + xóa */
    [data-testid="stHorizontalBlock"]:has(.{mk_cv}) {{
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 4px !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{mk_cv}) > [data-testid="stColumn"]:first-child {{
        flex: 0 0 36px !important; min-width: 36px !important; max-width: 36px !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{mk_cv}) > [data-testid="stColumn"]:nth-child(2) {{
        flex: 1 1 0% !important; min-width: 0 !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{mk_cv}) > [data-testid="stColumn"]:last-child {{
        flex: 0 0 36px !important; min-width: 36px !important; max-width: 36px !important;
    }}
    /* Tên công việc trông như plain text */
    [data-testid="stHorizontalBlock"]:has(.{mk_cv}) [data-testid="stTextInput"] input {{
        border: 1.5px solid transparent !important;
        background: transparent !important; box-shadow: none !important;
        padding: 3px 6px !important; font-size: 0.93rem !important;
        color: #1e1b4b !important; min-height: 32px !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{mk_cv}) [data-testid="stTextInput"] input:focus {{
        border-color: #7c3aed !important; background: white !important;
        border-radius: 6px !important;
        box-shadow: 0 0 0 2px rgba(124,58,237,0.12) !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{mk_cv}) [data-testid="stTextInput"] > div {{
        border: none !important; box-shadow: none !important; background: transparent !important;
    }}
    /* Căn checkbox ngang hàng text input */
    [data-testid="stHorizontalBlock"]:has(.{mk_cv}) > [data-testid="stColumn"]:first-child {{
        display: flex !important;
        align-items: center !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{mk_cv}) > [data-testid="stColumn"]:first-child > div {{
        display: flex !important;
        align-items: center !important;
        width: 100% !important;
        height: 100% !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{mk_cv}) [data-testid="stCheckbox"] {{
        margin: 0 !important;
        padding: 0 !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{mk_cv}) [data-testid="stCheckbox"] label {{
        margin: 0 !important; padding: 0 !important;
    }}
    /* Nút xóa: transparent đỏ */
    [data-testid="stHorizontalBlock"]:has(.{mk_cv}) [data-testid="stColumn"]:last-child button {{
        background: transparent !important; border: none !important;
        box-shadow: none !important; color: #ef4444 !important;
        font-size: 1.1rem !important; padding: 2px 4px !important;
        min-height: 32px !important; transform: none !important;
    }}
    [data-testid="stHorizontalBlock"]:has(.{mk_cv}) [data-testid="stColumn"]:last-child button:hover {{
        background: #fee2e2 !important; border-radius: 6px !important;
        box-shadow: none !important; transform: none !important;
    }}
    /* Hàng 2: selectbox nhân viên full width */
    .cv-nv-frag-{key_prefix} [data-testid="stSelectbox"] > div > div {{
        font-size: 0.9rem !important; border-color: #e0d7ff !important;
        background: #f5f3ff !important; color: #4c1d95 !important;
        min-height: 34px !important;
    }}
    .cv-nv-frag-{key_prefix} [data-testid="stSelectbox"] [class*="singleValue"],
    .cv-nv-frag-{key_prefix} [data-testid="stSelectbox"] [class*="SingleValue"] {{
        direction: ltr !important; font-size: 0.9rem !important;
        overflow: visible !important; white-space: nowrap !important;
        text-overflow: clip !important; max-width: none !important;
    }}
    .cv-nv-frag-{key_prefix} label {{ font-size: 0.78rem !important; color: #6b7280 !important; }}
    </style>""", unsafe_allow_html=True)

    _xoa = None
    items_cv = st.session_state[cv_key]

    def _save_cv_ten(i):
        val = st.session_state.get(f"{key_prefix}_cv_txt_{i}", "").strip()
        if val:
            st.session_state[cv_key][i]["ten"] = val

    def _save_cv_nv(i):
        val = st.session_state.get(f"{key_prefix}_cv_nv_sel_{i}", "-- Không chọn --")
        st.session_state[cv_key][i]["nhan_vien"] = "" if val == "-- Không chọn --" else val

    def _save_cv_done(i):
        val = st.session_state.get(f"{key_prefix}_cv_ck_{i}", False)
        st.session_state[cv_key][i]["done"] = val

    for i, cv in enumerate(items_cv):
        done_val = bool(cv.get("done", False))
        ten   = cv.get("ten", "") or f"Việc {i+1}"
        nguoi = cv.get("nhan_vien", cv.get("nguoi", "")) or ""
        nv_idx = nv_opts.index(nguoi) if nguoi in nv_opts else 0

        # Hàng 1: checkbox + tên công việc + nút xóa
        col_ck, col_txt, col_del = st.columns([0.5, 5.5, 0.5], gap="small")
        with col_ck:
            st.markdown(f"<span class='{mk_cv}' style='display:none'></span>", unsafe_allow_html=True)
            st.checkbox(
                "", value=done_val,
                key=f"{key_prefix}_cv_ck_{i}",
                label_visibility="collapsed",
                on_change=_save_cv_done, args=(i,),
            )
        with col_txt:
            st.text_input(
                "", value=ten,
                key=f"{key_prefix}_cv_txt_{i}",
                label_visibility="collapsed",
                on_change=_save_cv_ten, args=(i,),
            )
        with col_del:
            if st.button("🗑️", key=f"{key_prefix}_cv_del_{i}", use_container_width=True):
                _xoa = i
        # Hàng 2: selectbox nhân viên full width
        st.markdown(f"<div class='cv-nv-frag-{key_prefix}'>", unsafe_allow_html=True)
        st.selectbox(
            "👤 Nhân viên thực hiện", options=nv_opts,
            index=nv_idx,
            key=f"{key_prefix}_cv_nv_sel_{i}",
            on_change=_save_cv_nv, args=(i,),
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Hàng 3: upload ảnh cho từng công việc con
        _cv_anh = st.session_state[cv_key][i].get("anh", [])
        _exp_anh_lbl = f"📎 Hình/Video ({len(_cv_anh)})" if _cv_anh else "📎 Thêm hình/video"
        with st.expander(_exp_anh_lbl, expanded=False):
            if _cv_anh:
                _cols_a = st.columns(min(len(_cv_anh), 3))
                for _ai, _url_a in enumerate(_cv_anh):
                    with _cols_a[_ai % 3]:
                        if "/view" in _url_a or _url_a.endswith((".mp4", ".mov", ".avi")):
                            st.markdown(f"🎬 [Video {_ai+1}]({_url_a})")
                        else:
                            _hien_thi_anh_drive(_url_a, use_container_width=True)
                        def _del_cv_anh_frag(idx=i, url=_url_a):
                            _cvl = st.session_state.get(cv_key, [])
                            if 0 <= idx < len(_cvl):
                                _cvl[idx]["anh"] = [u for u in _cvl[idx].get("anh", []) if u != url]
                        st.button("🗑️ Xoá", key=f"{key_prefix}_del_cvanh_{i}_{_ai}",
                                  use_container_width=True,
                                  on_click=_del_cv_anh_frag)
            _up_key_frag = f"{key_prefix}_up_cv_{i}"
            st.file_uploader(
                "Chọn hình hoặc video",
                type=["jpg", "jpeg", "png", "mp4", "mov", "avi"],
                accept_multiple_files=True,
                key=_up_key_frag,
                label_visibility="collapsed",
            )
            if st.button("📤 Upload", key=f"{key_prefix}_btn_up_cv_{i}", use_container_width=True):
                _files = st.session_state.get(_up_key_frag) or []
                if _files:
                    with st.spinner("Đang upload..."):
                        for _fm in _files:
                            _new_url = _tai_media_len_drive(_fm)
                            st.session_state[cv_key][i].setdefault("anh", []).append(_new_url)
                    st.rerun(scope="fragment")
                else:
                    st.warning("Chưa chọn file!")

    if _xoa is not None:
        st.session_state[cv_key].pop(_xoa)
        for k in list(st.session_state.keys()):
            if k.startswith(f"{key_prefix}_cv_txt_") or k.startswith(f"{key_prefix}_cv_nv_sel_"):
                del st.session_state[k]
        st.rerun()

    # Thêm thủ công một mục mới
    st.markdown("<div style='margin-top:6px'></div>", unsafe_allow_html=True)
    st.text_input(
        "", placeholder="Tên công việc con...",
        key=f"{key_prefix}_cv_ten_{st.session_state[cv_inp_v]}",
        label_visibility="collapsed",
    )
    st.markdown(f"<div class='cv-nv-frag-{key_prefix}'>", unsafe_allow_html=True)
    st.selectbox(
        "👤 Nhân viên thực hiện", options=nv_opts,
        key=f"{key_prefix}_cv_nv_{st.session_state[cv_inp_v]}",
    )
    st.markdown("</div>", unsafe_allow_html=True)
    if st.button("＋ Thêm công việc con", key=f"{key_prefix}_cv_add",
                 use_container_width=True):
        ten_val = st.session_state.get(
            f"{key_prefix}_cv_ten_{st.session_state[cv_inp_v]}", "").strip()
        cv_nv   = st.session_state.get(
            f"{key_prefix}_cv_nv_{st.session_state[cv_inp_v]}", "-- Không chọn --")
        if ten_val:
            st.session_state[cv_key].append({
                "ten":       ten_val,
                "nhan_vien": "" if cv_nv == "-- Không chọn --" else cv_nv,
                "done":      False,
            })
            st.session_state[cv_inp_v] += 1
            st.rerun()






# ============================================================
# FRAGMENT: UPLOAD ẢNH (dùng trong dialog để tránh đóng dialog khi rerun)
# ============================================================

def _cb_xoa_anh_nt(task_id, anh_key, url_a):
    """Callback xóa ảnh — chạy trước khi re-render, không cần st.rerun()"""
    xoa_url_anh(task_id, url_a)
    st.session_state[anh_key] = [u for u in st.session_state.get(anh_key, []) if u != url_a]


def _cb_upload_anh_nt(task_id, anh_key, up_key):
    """Callback upload ảnh — chạy trước khi re-render, không cần st.rerun()"""
    files = st.session_state.get(up_key) or []
    if not files:
        return
    new_urls = []
    for f in files:
        url = tai_anh_len_cloudinary(f)
        cap_nhat_url_anh(task_id, url)
        new_urls.append(url)
    st.session_state[anh_key] = st.session_state.get(anh_key, []) + new_urls
    st.session_state[f"_nt_msg_{task_id}"] = f"✅ Đã upload {len(new_urls)} ảnh!"


def _fragment_upload_anh_nghiem_thu(task_id, anh_key: str):
    """Upload ảnh nghiệm thu — explicit button + spinner để hiện ảnh ngay."""
    up_key = f"up_anh_nt_{task_id}"
    ds_anh = st.session_state.get(anh_key, [])
    st.markdown("**📸 Ảnh Nghiệm Thu**")
    if ds_anh:
        st.caption(f"{len(ds_anh)} ảnh đã upload")
        cols_anh = st.columns(min(len(ds_anh), 3))
        for idx_a, url_a in enumerate(ds_anh):
            with cols_anh[idx_a % 3]:
                _hien_thi_anh_drive(url_a, caption=f"Ảnh {idx_a + 1}", use_container_width=True)
                st.button(
                    "🗑️ Xoá", key=f"xoa_anh_{task_id}_{idx_a}",
                    use_container_width=True,
                    on_click=_cb_xoa_anh_nt, args=(task_id, anh_key, url_a),
                )
    else:
        st.caption("Chưa có ảnh nghiệm thu.")

    st.file_uploader(
        "Thêm ảnh (JPG, PNG)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key=up_key,
    )
    if st.button("📤 Upload ảnh", key=f"btn_up_nt_{task_id}", use_container_width=True):
        files = st.session_state.get(up_key) or []
        if files:
            with st.spinner("Đang upload..."):
                new_urls = []
                for f in files:
                    url = tai_anh_len_cloudinary(f)
                    cap_nhat_url_anh(task_id, url)
                    new_urls.append(url)
            st.session_state[anh_key] = st.session_state.get(anh_key, []) + new_urls
            st.rerun(scope="fragment")
        else:
            st.warning("Chưa chọn file!")


_NHOM_DO = [
    # Hình 1
    ("Stator 1 coil resistance / Điện trở cuộn dây Stator 1",
     ["U1–U2", "V1–V2", "W1–W2"]),

    # Hình 2
    ("Resistance of the temperature sensor / Điện trở cảm biến nhiệt độ",
     ["PTC", "PT100", "HEATER"]),
    ("No-load test / Kiểm tra không tải",
     ["Tần số", "Voltage", "Dòng điện",
      "Radial ↔ DE / AS", "Radial ↑ DE / AS", "Axial (X) DE / AS",
      "Radial ↔ NDE / AS", "Radial ↑ NDE / AS", "Axial (X) NDE / AS"]),

    # Hình 3
    ("Engine overview / Tổng quan động cơ",
     ["Engine / Động cơ", "Nameplate / Bảng tên", "Quạt làm mát / Cooling fan"]),
    ("Nắp động cơ",
     ["Nắp DE", "Nắp NDE"]),

    # Hình 4
    ("Trục động cơ",
     ["Bạc đạn DE", "Bạc đạn NDE",
      "Phớt", "Đầu ren, chốt lavet", "Cánh quạt làm mát"]),
    ("Phớt chặn",
     ["Phớt chặn 1", "Phớt chặn 2"]),
    ("Bearing / Vòng bi",
     ["Vòng bi DE", "Vòng bi NDE"]),

    # Hình 5
    ("Grease pump / Bơm mỡ bôi trơn",
     ["Vòng bi bơm mỡ", "Mặt gam"]),
    ("Coil / Cuộn dây",
     ["Vào dây", "Đai đầu"]),
    ("Cân bằng động",
     ["Gá lên máy", "Sau khi cân"]),
]


def _cb_xoa_do(task_id, do_key, label, url_d):
    """Callback xóa ảnh đo lường — không cần st.rerun()"""
    cur = st.session_state[do_key].get(label, [])
    if url_d in cur:
        cur.remove(url_d)
    st.session_state[do_key][label] = cur
    cap_nhat_anh_do_luong(task_id, st.session_state[do_key])


def _cb_upload_do(task_id, do_key, label, up_key, done_key):
    """Callback upload ảnh đo lường — không cần st.rerun()"""
    f_do = st.session_state.get(up_key)
    if f_do is None:
        return
    _file_id = f"{f_do.name}_{f_do.size}"
    if st.session_state.get(done_key) == _file_id:
        return
    st.session_state[done_key] = _file_id
    url_new = tai_anh_len_cloudinary(f_do)
    st.session_state[do_key].setdefault(label, []).append(url_new)
    cap_nhat_anh_do_luong(task_id, st.session_state[do_key])


def _fragment_upload_do_luong(task_id, do_key: str):
    """Upload ảnh đo lường — dùng callback thay vì st.rerun() để dialog không đóng."""
    for nhom_title, labels in _NHOM_DO:
        st.markdown(
            f"<div style='background:#dbeafe;border-radius:8px 8px 0 0;padding:8px 14px;"
            f"font-weight:700;font-size:0.88rem;color:#1e3a8a;margin-top:10px;'>"
            f"{nhom_title}</div>",
            unsafe_allow_html=True,
        )
        for label in labels:
            st.markdown(
                f"<div style='background:#fef9c3;border:1px solid #e5e7eb;padding:6px 14px;"
                f"font-weight:600;font-size:0.85rem;margin-top:4px;border-radius:4px;'>"
                f"📏 {label}</div>",
                unsafe_allow_html=True,
            )
            urls_label = st.session_state[do_key].get(label, [])
            if urls_label:
                # Đã có ảnh — hiển thị + nút xoá, ẩn uploader
                url_d = urls_label[0]
                col_img, col_del = st.columns([3, 1], gap="small")
                with col_img:
                    _hien_thi_anh_drive(url_d, width=120)
                with col_del:
                    st.button(
                        "🗑️ Xoá", key=f"xoa_do_{task_id}_{label}_0",
                        use_container_width=True,
                        on_click=_cb_xoa_do,
                        args=(task_id, do_key, label, url_d),
                    )
            else:
                # Chưa có ảnh — hiển thị uploader (1 file duy nhất)
                up_key   = f"up_do_{task_id}_{label}"
                done_key = f"up_do_done_{task_id}_{label}"
                st.file_uploader(
                    f"Ảnh {label}",
                    type=["jpg", "jpeg", "png"],
                    key=up_key,
                    label_visibility="collapsed",
                    accept_multiple_files=False,
                )
                if st.button("📤 Upload", key=f"btn_do_{task_id}_{label}", use_container_width=True):
                    f_do = st.session_state.get(up_key)
                    if f_do:
                        _fid = f"{f_do.name}_{f_do.size}"
                        if not st.session_state.get(f"{done_key}_{_fid}"):
                            with st.spinner("Đang upload..."):
                                st.session_state[f"{done_key}_{_fid}"] = True
                                url_new = tai_anh_len_cloudinary(f_do)
                                st.session_state[do_key][label] = [url_new]
                            cap_nhat_anh_do_luong(task_id, st.session_state[do_key])
                            st.rerun(scope="fragment")
                    else:
                        st.warning("Chưa chọn file!")


# ─── helper: lưu công việc con về sheet ───────────────────────────────────────
def _parse_date_display(val: str):
    """Chuyển chuỗi DD/MM/YYYY sang date object, trả None nếu lỗi."""
    try:
        return datetime.strptime(str(val)[:10], "%d/%m/%Y").date()
    except Exception:
        return None


def _save_cv_to_sheet(task_id, cv_key):
    data = st.session_state.get(cv_key, [])
    try:
        _sh = lay_sheet()
        _o  = _sh.find(str(task_id), in_column=1)
        if _o:
            _sh.update_cell(_o.row, 14, json.dumps(data, ensure_ascii=False))
            lay_danh_sach_cong_viec.clear()
    except Exception:
        pass


# ============================================================
# KANBAN BOARD HELPER
# ============================================================
@st.dialog("📋 Chi tiết & Chỉnh sửa công việc", width="large")
def _task_dialog(hang_dict, ds_tt):
    """Dialog to hiển thị chi tiết và chỉnh sửa task."""
    tid  = hang_dict.get("ID", "")
    ten  = hang_dict.get("Tên Công Việc", "")
    cty  = hang_dict.get("Công Ty", "")
    tt   = hang_dict.get("Trạng Thái", "")
    mau  = _STATUS_BG.get(tt, "#607d8b")
    mau_fg = "#1a1a1a" if mau in ("#f9c74f", "#ffd166") else "#ffffff"
    dlg_txt, dlg_bg = _STATUS_HEADER_COLOR.get(tt, ("#37474f", "#eceff1"))
    st.markdown(
        f"<div style='background:{dlg_bg};color:{dlg_txt};border-radius:7px;"
        f"padding:6px 14px;font-weight:800;font-size:0.85rem;margin-bottom:10px;"
        f"border:1.5px solid {dlg_txt}44;display:inline-block;'>"
        f"{tt}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"#### {ten}")
    if cty:
        st.caption(f"🏢 {cty}")
    st.divider()
    _fragment_chi_tiet_task(hang_dict, ds_tt)


def _render_kanban_board(df, ds_tt, board_key="kb"):
    """Kanban board: header màu + toggle thu/mở, cards 4 cột/hàng.
    Bấm 📂 → @st.dialog chỉnh sửa.
    """
    import html as _hl
    import re as _re
    _EXCLUDE   = {"Đã Xuất Hóa Đơn", "Bảo Hành - Trả Lại"}
    _COMPLETED = {"Đã Hoàn Thành - Giao Máy", "Hoàn Thành"}
    ds_show = [t for t in ds_tt if t not in _EXCLUDE]
    today = datetime.now().date()
    COLS  = 4  # card per row

    # ── Inject CSS màu cho từng nút toggle ──────────────────
    # Dùng selector theo element-container (wrapper thật của Streamlit)
    css_rules = []
    for tt2 in ds_show:
        txt2, bg2 = _STATUS_HEADER_COLOR.get(tt2, ("#37474f", "#eceff1"))
        safe2     = _re.sub(r"[^a-zA-Z0-9]", "_", tt2)
        mk        = f"kbtog_{board_key}_{safe2}"
        # .element-container:has(.mk) + .element-container button
        sel = (
            f".element-container:has(.{mk}) + .element-container button,"
            f".element-container:has(.{mk}) + .element-container button:hover"
        )
        css_rules.append(
            f"{sel} {{ background:{bg2} !important; color:{txt2} !important;"
            f" border:2px solid {txt2}55 !important; font-weight:800 !important;"
            f" font-size:0.95rem !important; letter-spacing:0.5px !important;"
            f" box-shadow: none !important;"
            f" border-radius:8px !important;"
            f" text-align:left !important; padding:10px 18px !important; }}"
        )
    st.markdown(f"<style>{'  '.join(css_rules)}</style>", unsafe_allow_html=True)

    for tt in ds_show:
        nhom   = df[df["Trạng Thái"] == tt] if not df.empty else df.iloc[0:0]
        so     = len(nhom)
        mau_bg = _STATUS_BG.get(tt, "#607d8b")
        mau_fg = "#1a1a1a" if mau_bg in ("#f9c74f", "#ffd166") else "#ffffff"
        # màu header nhạt có chữ đậm màu
        hdr_txt, hdr_bg = _STATUS_HEADER_COLOR.get(tt, ("#37474f", "#eceff1"))

        # ── Toggle state ──────────────────────────────────────
        _sk = f"{board_key}_open_{tt}"
        if _sk not in st.session_state:
            st.session_state[_sk] = True   # mặc định mở

        is_open = st.session_state[_sk]
        chevron = "▼" if is_open else "▶"
        safe_tt = _re.sub(r"[^a-zA-Z0-9]", "_", tt)
        mk      = f"kbtog_{board_key}_{safe_tt}"

        # ── Header: marker div + full-width button (CSS tô màu) ──
        st.markdown(f"<div class='{mk}' style='display:none'></div>",
                    unsafe_allow_html=True)
        btn_label = f"{chevron}  {tt}  ({so})"
        if st.button(btn_label, key=f"{board_key}_tog_{tt}", use_container_width=True):
            st.session_state[_sk] = not is_open
            st.rerun()

        if not is_open:
            continue

        if nhom.empty:
            st.caption("— Không có công việc nào —")
            continue

        rows_data = [nhom.iloc[i:i+COLS] for i in range(0, len(nhom), COLS)]
        for row_df in rows_data:
            st_cols = st.columns(COLS, gap="small")
            for ci, (_, h) in enumerate(row_df.iterrows()):
                task_id   = h["ID"]
                ten_cv    = str(h.get("Tên Công Việc", "") or "")
                cong_ty   = str(h.get("Công Ty", "") or "")
                nhan_vien = str(h.get("Nhân Viên", "") or "")
                ngay_tao  = str(h.get("Ngày Tạo", ""))[:10]

                is_over = False
                try:
                    dl = str(h.get("Ngày Kết Thúc", "") or "")[:10]
                    if dl and tt not in _COMPLETED:
                        import datetime as _dt
                        is_over = _dt.date.fromisoformat(dl) < today
                except Exception:
                    pass

                anh_lst = doc_danh_sach_anh(str(h.get("Link Ảnh", "") or ""))
                try:
                    cl  = json.loads(str(h.get("Checklist", "") or "[]"))
                    cld = sum(1 for x in cl if isinstance(x, dict) and x.get("done"))
                    clt = len(cl)
                except Exception:
                    cld = clt = 0
                try:
                    cvt = len(json.loads(str(h.get("Công Việc Con", "") or "[]")))
                except Exception:
                    cvt = 0

                with st_cols[ci]:
                    with st.container(border=True):
                        if is_over:
                            st.error("⚠️ Quá hạn", icon="🔴")
                        if anh_lst:
                            st.image(anh_lst[0], use_container_width=True)
                        short = ten_cv[:40] + ("…" if len(ten_cv) > 40 else "")
                        st.markdown(f"**{short}**")
                        meta = []
                        if cong_ty:   meta.append(f"🏢 {cong_ty}")
                        if nhan_vien: meta.append(f"👤 {nhan_vien}")
                        if ngay_tao:  meta.append(f"📅 {ngay_tao}")
                        if anh_lst:   meta.append(f"📷 {len(anh_lst)}")
                        if clt:       meta.append(f"☑️ {cld}/{clt}")
                        if cvt:       meta.append(f"🔹 {cvt}")
                        if meta:
                            st.caption(" · ".join(meta))
                        if st.button("📂 Xem & chỉnh sửa", key=f"kopen_{task_id}", use_container_width=True):
                            _task_dialog(h.to_dict(), ds_tt)


def _render_detail_expanders(df, ds_tt):
    pass  # không còn dùng — chi tiết đã chuyển vào _task_dialog


# ============================================================
# GIAO DIỆN ADMIN
# ============================================================
def giao_dien_admin():
    """Giao diện quản lý dành cho Admin — 4 tab ngang: Cài Đặt / Nhân Viên / Tạo Task / Tổng Quan."""
    st.header("🔧 Bảng Điều Khiển Admin")

    tab_cai_dat, tab_nhan_vien, tab_tao_task, tab_tong_quan, tab_board, tab_cvc, tab_tdtdm = st.tabs(
        ["⚙️  Cài Đặt", "👥  Nhân Viên", "➕  Tạo Công Việc Mới", "📊  Tổng Quan", "🗂️  Bảng Quản Lý", "📋  Công Việc Con", "🔩  Theo Dõi Tiến Độ Máy"]
    )

    # ── Helper: render section quản lý 1 field đơn ───────────────────────────
    def _section_don_gian(
        ten_section: str,
        key_prefix: str,
        lay_df,
        them_func,
        ten_cot: str,
        placeholder: str = "",
        mo_ta_them: str  = "",
        expanded: bool   = False,
        sua_func=None,
        xoa_func=None,
    ):
        with st.expander(ten_section, expanded=expanded):
            with st.form(f"form_{key_prefix}", clear_on_submit=True):
                gia_tri = st.text_input(mo_ta_them or "Tên *", placeholder=placeholder)
                gui = st.form_submit_button("➕ Thêm", use_container_width=True)
                if gui:
                    if not gia_tri.strip():
                        st.error("⛔ Vui lòng nhập tên!")
                    else:
                        try:
                            with st.spinner("Đang lưu..."):
                                id_moi = them_func(gia_tri.strip())
                            st.success(f"✅ Đã thêm #{id_moi}: **{gia_tri}**!")
                        except (ConnectionError, OSError, Exception) as e:
                            st.error(f"🔌 Lưu thất bại — mất kết nối mạng. Hãy thử lại.\n\n`{e}`")
            st.divider()
            try:
                df = lay_df()
                _loi_mang = False
            except Exception as e:
                df = pd.DataFrame()
                _loi_mang = str(e)
            if _loi_mang:
                st.warning("⚠️ Không thể tải dữ liệu — mất kết nối mạng.")
            elif df.empty:
                st.info("ℹ️ Chưa có dữ liệu. Hãy thêm ở form bên trên!")
            else:
                st.markdown(f"**Tổng cộng: {len(df)} mục**")
                for _, row in df.iterrows():
                    rid  = str(row.get("ID", ""))
                    ten  = str(row.get(ten_cot, ""))
                    c1, c2, c3 = st.columns([7, 1, 1])
                    c1.markdown(f"**{ten}**")
                    if sua_func and c2.button("✏️", key=f"btn_edit_{key_prefix}_{rid}", help="Chỉnh sửa"):
                        st.session_state[f"editing_{key_prefix}"] = rid
                        st.session_state.pop(f"deleting_{key_prefix}", None)
                    if xoa_func and c3.button("🗑️", key=f"btn_del_{key_prefix}_{rid}", help="Xóa"):
                        st.session_state[f"deleting_{key_prefix}"] = rid
                        st.session_state.pop(f"editing_{key_prefix}", None)
                    # Form chỉnh sửa inline
                    if sua_func and st.session_state.get(f"editing_{key_prefix}") == rid:
                        with st.form(f"form_edit_{key_prefix}_{rid}"):
                            ten_moi = st.text_input("Tên mới *", value=ten)
                            c_save, c_cancel = st.columns(2)
                            saved    = c_save.form_submit_button("💾 Lưu", type="primary", use_container_width=True)
                            canceled = c_cancel.form_submit_button("❌ Huỷ", use_container_width=True)
                        if saved:
                            if not ten_moi.strip():
                                st.error("⛔ Tên không được để trống!")
                            else:
                                try:
                                    with st.spinner("Đang lưu..."):
                                        sua_func(rid, ten_moi.strip())
                                    st.session_state.pop(f"editing_{key_prefix}", None)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"🔌 Lỗi: {e}")
                        if canceled:
                            st.session_state.pop(f"editing_{key_prefix}", None)
                            st.rerun()
                    # Xác nhận xóa
                    if xoa_func and st.session_state.get(f"deleting_{key_prefix}") == rid:
                        st.warning(f"⚠️ Xác nhận xóa **{ten}**?")
                        c_ok, c_no = st.columns(2)
                        if c_ok.button("✅ Xác nhận xóa", key=f"ok_del_{key_prefix}_{rid}", use_container_width=True):
                            try:
                                with st.spinner("Đang xóa..."):
                                    xoa_func(rid)
                                st.session_state.pop(f"deleting_{key_prefix}", None)
                                st.rerun()
                            except Exception as e:
                                st.error(f"🔌 Lỗi: {e}")
                        if c_no.button("❌ Huỷ", key=f"no_del_{key_prefix}_{rid}", use_container_width=True):
                            st.session_state.pop(f"deleting_{key_prefix}", None)
                            st.rerun()

    # ══════════════════════════════════════════════
    # TAB 1 — CÀI ĐẶT
    # ══════════════════════════════════════════════
    with tab_cai_dat:
        with st.expander("🏢 Quản Lý Công Ty", expanded=False):
            with st.form("form_cong_ty", clear_on_submit=True):
                ten_ct_inp = st.text_input("Tên Công Ty *", placeholder="Ví dụ: Công Ty TNHH ABC")
                dc_inp = st.text_input("Địa Chỉ", placeholder="Ví dụ: 123 Nguyễn Văn Linh, Q.7, TP.HCM")
                col_mkh, col_mst = st.columns(2)
                with col_mkh:
                    ma_kh_inp = st.text_input("Mã Khách Hàng", placeholder="Ví dụ: KH001")
                with col_mst:
                    ma_thue_inp = st.text_input("Mã Số Thuế", placeholder="Ví dụ: 0123456789")
                gui_ct = st.form_submit_button("➕ Thêm", use_container_width=True)
                if gui_ct:
                    if not ten_ct_inp.strip():
                        st.error("⛔ Vui lòng nhập Tên Công Ty!")
                    else:
                        try:
                            with st.spinner("Đang lưu..."):
                                id_ct = them_cong_ty(ten_ct_inp.strip(), dc_inp.strip(), ma_kh_inp.strip(), ma_thue_inp.strip())
                            st.success(f"✅ Đã thêm #{id_ct}: **{ten_ct_inp}**!")
                        except (ConnectionError, OSError, Exception) as e:
                            st.error(f"🔌 Lưu thất bại — mất kết nối mạng. Hãy thử lại.\n\n`{e}`")
            st.divider()
            try:
                df_ct = lay_danh_sach_cong_ty()
                _loi_ct = False
            except Exception as e:
                df_ct = pd.DataFrame()
                _loi_ct = str(e)
            if _loi_ct:
                st.warning("⚠️ Không thể tải dữ liệu — mất kết nối mạng.")
            elif df_ct.empty:
                st.info("ℹ️ Chưa có công ty nào. Hãy thêm ở form bên trên!")
            else:
                st.markdown(f"**Tổng cộng: {len(df_ct)} công ty**")
                for _, row_ct in df_ct.iterrows():
                    rid_ct  = str(row_ct.get("ID", ""))
                    ten_ct  = str(row_ct.get("Tên Công Ty", ""))
                    dc_ct   = str(row_ct.get("Địa Chỉ", ""))
                    mkh_ct  = str(row_ct.get("Mã Khách Hàng", ""))
                    mst_ct  = str(row_ct.get("Mã Số Thuế", ""))
                    c1, c2, c3 = st.columns([7, 1, 1])
                    c1.markdown(f"**{ten_ct}**" + (f"  —  {dc_ct}" if dc_ct else ""))
                    if c2.button("✏️", key=f"btn_edit_ct_{rid_ct}", help="Chỉnh sửa"):
                        st.session_state["editing_ct"] = rid_ct
                        st.session_state.pop("deleting_ct", None)
                    if c3.button("🗑️", key=f"btn_del_ct_{rid_ct}", help="Xóa"):
                        st.session_state["deleting_ct"] = rid_ct
                        st.session_state.pop("editing_ct", None)
                    # Form chỉnh sửa Công Ty
                    if st.session_state.get("editing_ct") == rid_ct:
                        with st.form(f"form_edit_ct_{rid_ct}"):
                            ten_ct_e  = st.text_input("Tên Công Ty *", value=ten_ct)
                            dc_e      = st.text_input("Địa Chỉ", value=dc_ct)
                            col_a, col_b = st.columns(2)
                            mkh_e  = col_a.text_input("Mã Khách Hàng", value=mkh_ct)
                            mst_e  = col_b.text_input("Mã Số Thuế", value=mst_ct)
                            c_s, c_c = st.columns(2)
                            saved_ct    = c_s.form_submit_button("💾 Lưu", type="primary", use_container_width=True)
                            canceled_ct = c_c.form_submit_button("❌ Huỷ", use_container_width=True)
                        if saved_ct:
                            if not ten_ct_e.strip():
                                st.error("⛔ Tên Công Ty không được để trống!")
                            else:
                                try:
                                    with st.spinner("Đang lưu..."):
                                        sua_cong_ty(rid_ct, ten_ct_e.strip(), dc_e.strip(), mkh_e.strip(), mst_e.strip())
                                    st.session_state.pop("editing_ct", None)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"🔌 Lỗi: {e}")
                        if canceled_ct:
                            st.session_state.pop("editing_ct", None)
                            st.rerun()
                    # Xác nhận xóa Công Ty
                    if st.session_state.get("deleting_ct") == rid_ct:
                        st.warning(f"⚠️ Xác nhận xóa **{ten_ct}**?")
                        c_ok, c_no = st.columns(2)
                        if c_ok.button("✅ Xác nhận xóa", key=f"ok_del_ct_{rid_ct}", use_container_width=True):
                            try:
                                with st.spinner("Đang xóa..."):
                                    xoa_cong_ty(rid_ct)
                                st.session_state.pop("deleting_ct", None)
                                st.rerun()
                            except Exception as e:
                                st.error(f"🔌 Lỗi: {e}")
                        if c_no.button("❌ Huỷ", key=f"no_del_ct_{rid_ct}", use_container_width=True):
                            st.session_state.pop("deleting_ct", None)
                            st.rerun()
        _section_don_gian(
            "🔧 Loại Máy", "loai_may",
            lay_danh_sach_loai_may, them_loai_may, "Tên Loại Máy",
            placeholder="Ví dụ: Động Cơ Điện, Máy Bơm...",
            mo_ta_them="Tên Loại Máy *",
            sua_func=sua_loai_may,
            xoa_func=xoa_loai_may,
        )
        _section_don_gian(
            "🛠️ Tình Trạng", "tinh_trang",
            lay_danh_sach_tinh_trang, them_tinh_trang, "Tên Tình Trạng",
            placeholder="Ví dụ: Bảo hành, Sửa chữa, Trả lại...",
            mo_ta_them="Tên Tình Trạng *",
            sua_func=sua_tinh_trang,
            xoa_func=xoa_tinh_trang,
        )

        _section_don_gian(
            "⚙️ Công Đoạn", "cong_doan",
            lay_danh_sach_cong_doan, them_cong_doan, "Tên Công Đoạn",
            placeholder="Ví dụ: Kiểm Tra Đầu Vào, Tháo Rã, Quấn Dây...",
            mo_ta_them="Tên Công Đoạn *",
            sua_func=sua_cong_doan,
            xoa_func=xoa_cong_doan_item,
        )

    # ══════════════════════════════════════════════
    # TAB 2 — NHÂN VIÊN
    # ══════════════════════════════════════════════
    with tab_nhan_vien:
        st.markdown("#### 👥 Danh Sách Nhân Viên Đã Đăng Ký")

        if st.button("🔄 Làm mới", key="adm_nv_refresh"):
            lay_danh_sach_users.clear()
            lay_danh_sach_nhan_vien.clear()
            lay_danh_sach_cong_viec.clear()
            st.rerun()

        df_users = lay_danh_sach_users()
        df_nv_users = df_users[df_users["VaiTro"] == "nhan_vien"].reset_index(drop=True) if not df_users.empty else pd.DataFrame()

        if df_nv_users.empty:
            st.info("ℹ️ Chưa có nhân viên nào đăng ký. Hãy chia sẻ link app để họ tự đăng ký.")
        else:
            # Load tasks once for sub-task lookup
            with st.spinner("Đang tải dữ liệu công việc..."):
                df_all_tasks = lay_danh_sach_cong_viec()

            # ── CSS card nhân viên ──────────────────────────────────────
            st.markdown("""
            <style>
            .nv-summary-card {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 12px 12px 0 0;
                padding: 14px 16px 12px 16px;
                margin-bottom: 0;
                display: flex;
                flex-direction: column;
                gap: 6px;
            }
            .nv-top-row {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .nv-avatar {
                width: 40px; height: 40px;
                border-radius: 50%;
                background: linear-gradient(135deg, #7c3aed, #a78bfa);
                display: flex; align-items: center; justify-content: center;
                font-size: 1.1rem; color: white; font-weight: 700;
                flex-shrink: 0;
            }
            .nv-name { font-weight: 700; font-size: 0.97rem; color: #1e1b4b; }
            .nv-meta { font-size: 0.78rem; color: #6b7280; }
            .nv-badge-row {
                background: #f5f3ff;
                border: 1px solid #e5e7eb;
                border-top: none;
                border-radius: 0 0 12px 12px;
                padding: 6px 16px;
                font-size: 0.78rem;
                color: #7c3aed;
                font-weight: 600;
                margin-bottom: 8px;
            }
            /* Nút đóng trang chi tiết */
            button[kind="secondary"][data-testid*="adm_close_nv"] {
                border-color: #ef4444 !important;
                color: #ef4444 !important;
            }
            </style>
            """, unsafe_allow_html=True)

            # ── Buildindex: task chính + subtask per employee ──────────
            def _dem_task_cua(ho_ten: str):
                """Đếm task chính & subtask của một nhân viên."""
                task_chinh = 0
                subtask = 0
                if not df_all_tasks.empty:
                    task_chinh = len(df_all_tasks[df_all_tasks["Nhân Viên"] == ho_ten])
                    for _, row in df_all_tasks.iterrows():
                        try:
                            ds_cv = json.loads(row.get("Công Việc Con", "") or "[]")
                        except Exception:
                            ds_cv = []
                        for cv in ds_cv:
                            if isinstance(cv, dict):
                                nv_cv = cv.get("nhan_vien", cv.get("Nhân Viên", ""))
                                if nv_cv == ho_ten:
                                    subtask += 1
                return task_chinh, subtask

            st.markdown(f"**Tổng cộng: {len(df_nv_users)} nhân viên**")
            st.markdown("---")

            _ICON_TT_NV = {
                "Đang Kiểm Tra": "🔵", "Đã Phê Duyệt": "🟢",
                "Đã Báo Giá": "🟠", "Có Đơn": "🟣", "Chờ Giao": "🟡",
                "Đã Hoàn Thành - Giao Máy": "✅", "Đã Xuất Hóa Đơn": "⬜",
                "Bảo Hành - Trả Lại": "🔴",
                "Chờ Làm": "🔴", "Đang Làm": "🟡", "Hoàn Thành": "🟢",
            }

            # ── TRANG CHI TIẾT TASK CỦA NHÂN VIÊN ─────────────────────
            adm_xem_nv = st.session_state.get("adm_xem_nv")

            if adm_xem_nv:
                # Nút đóng
                col_close, col_title = st.columns([1, 5])
                with col_close:
                    if st.button("✕ Đóng", key="adm_close_nv", use_container_width=True):
                        st.session_state.pop("adm_xem_nv", None)
                        st.rerun()
                with col_title:
                    tc_d, ts_d = _dem_task_cua(adm_xem_nv)
                    st.markdown(f"### 👤 {adm_xem_nv} &nbsp;·&nbsp; 📋 {tc_d} công việc chính &nbsp;·&nbsp; 🔹 {ts_d} việc con")

                st.divider()

                # Nút làm mới
                if st.button("🔄 Làm mới dữ liệu", key="adm_nv_detail_refresh"):
                    lay_danh_sach_cong_viec.clear()
                    st.rerun()

                ds_tt_adm = lay_ten_cac_trang_thai() or ["Chờ Làm", "Đang Làm", "Hoàn Thành"]

                # ── Task chính ──────────────────────────────────────────
                df_task_chinh = df_all_tasks[
                    df_all_tasks["Nhân Viên"].fillna("").str.strip().str.lower() == adm_xem_nv.lower()
                ].copy() if not df_all_tasks.empty else pd.DataFrame()

                # Lọc theo Công Ty
                ds_ct_filter = df_task_chinh["Công Ty"].dropna().unique().tolist() if not df_task_chinh.empty else []
                if ds_ct_filter:
                    loc_ct = st.multiselect(
                        "🏢 Lọc theo Công Ty",
                        options=ds_ct_filter,
                        placeholder="Hiển thị tất cả...",
                        key="adm_nv_loc_ct",
                    )
                    if loc_ct:
                        df_task_chinh = df_task_chinh[df_task_chinh["Công Ty"].isin(loc_ct)]

                # ── Subtask được giao ───────────────────────────────────
                tasks_co_subtask = []
                if not df_all_tasks.empty:
                    for _, row in df_all_tasks.iterrows():
                        raw = row.get("Công Việc Con", "") or "[]"
                        try:
                            ds_cv = json.loads(raw)
                        except Exception:
                            ds_cv = []
                        my_subtasks = [
                            (i, cv) for i, cv in enumerate(ds_cv)
                            if isinstance(cv, dict)
                            and (cv.get("nguoi") or cv.get("nhan_vien") or "").strip().lower() == adm_xem_nv.lower()
                        ]
                        if my_subtasks:
                            tasks_co_subtask.append((row.to_dict(), ds_cv, my_subtasks))

                # ── Tabs task chính / việc con ──────────────────────────
                tab_tc_d, tab_st_d = st.tabs([
                    f"📌 Công Việc Chính ({len(df_task_chinh)})",
                    f"🔹 Việc Con ({sum(len(m) for _, _, m in tasks_co_subtask)})",
                ])

                with tab_tc_d:
                    if df_task_chinh.empty:
                        st.info("Nhân viên này chưa được giao công việc chính nào.")
                    else:
                        for _, hang in df_task_chinh.iterrows():
                            task_id    = hang["ID"]
                            trang_thai = hang.get("Trạng Thái", "Chờ Làm")
                            icon_tt    = _ICON_TT_NV.get(trang_thai, "⚪")
                            ten_cv     = hang.get("Tên Công Việc", "")
                            cong_ty    = hang.get("Công Ty", "")
                            _force_expand = st.session_state.get(f"expand_{task_id}", False)
                            with st.expander(
                                f"{icon_tt} [{cong_ty}]  {ten_cv}  —  {trang_thai}",
                                expanded=(trang_thai in ["Chờ Làm", "Đang Làm"]) or _force_expand
                            ):
                                if _force_expand:
                                    del st.session_state[f"expand_{task_id}"]
                                _fragment_chi_tiet_task(hang.to_dict(), ds_tt_adm)

                with tab_st_d:
                    if not tasks_co_subtask:
                        st.info("Nhân viên này chưa được giao công việc con nào.")
                    else:
                        st.caption(f"**{sum(len(m) for _,_,m in tasks_co_subtask)} việc con** trong **{len(tasks_co_subtask)} task**")
                        for hang_dict, ds_cv_full, my_subtasks in tasks_co_subtask:
                            tid    = hang_dict["ID"]
                            tt     = hang_dict.get("Trạng Thái", "")
                            icon   = _ICON_TT_NV.get(tt, "⚪")
                            cty    = hang_dict.get("Công Ty", "")
                            ten    = hang_dict.get("Tên Công Việc", "")
                            nv_chu = hang_dict.get("Nhân Viên", "")
                            dl     = hang_dict.get("Hạn Hoàn Thành", "") or hang_dict.get("Deadline", "")
                            mo_ta  = hang_dict.get("Mô Tả", "") or ""
                            all_done = all(cv.get("done", False) for _, cv in my_subtasks)
                            badge    = " ✅" if all_done else ""
                            with st.expander(
                                f"{icon} [{cty}] {ten}  —  {tt}{badge}",
                                expanded=not all_done
                            ):
                                st.markdown(f"**🏢 Công Ty:** {cty}  |  **👤** {nv_chu}  |  **📅** {dl}")
                                if mo_ta:
                                    st.markdown(f"**📝 Mô Tả:** {mo_ta}")
                                for idx_cv, cv in my_subtasks:
                                    ten_cv_sub = cv.get("ten", cv.get("Tên", "—"))
                                    done_sub   = cv.get("done", False)
                                    dl_sub     = cv.get("deadline", cv.get("Deadline", "—"))
                                    if done_sub:
                                        st.markdown(f"✅ ~~{ten_cv_sub}~~ &nbsp; `{dl_sub}`")
                                    else:
                                        st.markdown(f"⏳ **{ten_cv_sub}** &nbsp; `{dl_sub}`")

            else:
                # ── DANH SÁCH CARD NHÂN VIÊN ───────────────────────────
                for _idx_u, u in df_nv_users.iterrows():
                    ho_ten_u  = u["HoTen"]
                    uname     = u["Username"]
                    ns        = u["NgaySinh"]
                    ngay_tao  = u.get("NgayTao", "")[:10]
                    avatar_char = (ho_ten_u[0] if ho_ten_u else "?").upper()
                    tc, ts = _dem_task_cua(ho_ten_u)

                    st.markdown(f"""
                    <div class="nv-summary-card">
                        <div class="nv-top-row">
                            <div class="nv-avatar">{avatar_char}</div>
                            <div class="nv-name">{ho_ten_u}</div>
                        </div>
                        <div class="nv-meta">@{uname} &nbsp;·&nbsp; 🎂 {ns or '—'} &nbsp;·&nbsp; 📅 Tham gia {ngay_tao}</div>
                    </div>
                    <div class="nv-badge-row">📋 {tc} công việc chính &nbsp;|&nbsp; 🔹 {ts} việc con</div>
                    """, unsafe_allow_html=True)
                    if st.button("👁️ Xem chi tiết", key=f"adm_xem_{_idx_u}_{uname}", use_container_width=True):
                        lay_danh_sach_cong_viec.clear()
                        st.session_state["adm_xem_nv"] = ho_ten_u
                        st.rerun()
                    st.markdown("<div style='margin-bottom:6px'></div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    # TAB 3 — TẠO TASK MỚI
    # ══════════════════════════════════════════════
    with tab_tao_task:
        # Hiển thị success message từ lần tạo task trước
        if st.session_state.get("_adm_task_success"):
            st.success(st.session_state.pop("_adm_task_success"))
            st.balloons()

        @st.fragment
        def _fragment_tao_task_admin():
            _ADM_PREFIX   = "adm"
            ds_cong_ty    = lay_ten_cac_cong_ty()
            ds_nhan_vien  = lay_danh_sach_nhan_vien()
            ds_trang_thai = lay_ten_cac_trang_thai() or ["Chờ Làm", "Đang Làm", "Hoàn Thành"]

            if not ds_cong_ty:
                st.warning("⚠️ Chưa có công ty nào! Hãy thêm ở tab **⚙️ Cài Đặt** trước.")

            adm_cong_ty = st.selectbox(
                "🏢 Công Ty Khách Hàng *",
                options=ds_cong_ty if ds_cong_ty else ["(Chưa có công ty)"],
                key="adm_cong_ty",
            )
            adm_phe_duyet = st.selectbox(
                "✅ Người Phê Duyệt",
                options=["-- Không chọn --"] + ds_nhan_vien,
                key="adm_phe_duyet",
            )

            col_tt_top, col_nam = st.columns(2)
            with col_tt_top:
                adm_trang_thai = st.selectbox("📋 Trạng thái", options=ds_trang_thai, key="adm_trang_thai")
            with col_nam:
                adm_nam = st.text_input("Năm *", value=str(datetime.now().year), key="adm_nam")

            col_nv, col_dl = st.columns(2)
            with col_nv:
                adm_nguoi_giao = st.selectbox("👤 Giao cho nhân viên *", options=ds_nhan_vien, key="adm_nguoi_giao")
            with col_dl:
                adm_deadline = st.date_input("📅 Hạn hoàn thành", key="adm_deadline")

            col_lm_adm, col_tt_adm = st.columns(2)
            with col_lm_adm:
                adm_loai_may = st.selectbox(
                    "🔧 Loại Máy",
                    options=["-- Không chọn --"] + lay_ten_cac_loai_may(),
                    key="adm_loai_may",
                )
            with col_tt_adm:
                adm_tinh_trang = st.selectbox(
                    "🛠️ Tình Trạng",
                    options=["-- Không chọn --"] + lay_ten_cac_tinh_trang(),
                    key="adm_tinh_trang",
                )

            col_cs_adm, col_sc_adm = st.columns(2)
            with col_cs_adm:
                adm_cong_suat = st.text_input("⚡ Công Suất", placeholder="VD: 5.5kW", key="adm_cong_suat")
            with col_sc_adm:
                adm_so_cuc = st.text_input("🔩 Số Cực", placeholder="VD: 4P", key="adm_so_cuc")

            col_ms_adm, col_po_adm = st.columns(2)
            with col_ms_adm:
                adm_ma_so = st.text_input("🏷️ Mã Số", placeholder="VD: ABC-001", key="adm_ma_so")
            with col_po_adm:
                adm_so_po_noi_bo = st.text_input("📄 Số PO Nội Bộ", placeholder="VD: PO-2024-001", key="adm_so_po_noi_bo")

            col_kh_adm, col_bg_adm = st.columns(2)
            with col_kh_adm:
                adm_so_po_kh = st.text_input("📋 Số PO KH/HĐ", placeholder="VD: KH-2024-001", key="adm_so_po_kh")
            with col_bg_adm:
                adm_so_bao_gia = st.text_input("💰 Số Báo Giá", placeholder="VD: BG-2024-001", key="adm_so_bao_gia")

            adm_ten_task = st.text_input("📌 Tên công việc *", placeholder="Ví dụ: Sửa chữa động cơ bơm", key="adm_ten_task")
            adm_mo_ta    = st.text_area("📝 Mô tả chi tiết", placeholder="Nhập mô tả, yêu cầu kỹ thuật...", key="adm_mo_ta")

            st.divider()
            _fragment_checklist(_ADM_PREFIX, show_done=False, default_items=_MAC_DINH_CHECKLIST)
            st.divider()
            _fragment_cong_viec_con(_ADM_PREFIX, ds_nhan_vien, show_done=False)
            st.divider()

            if st.button("✅ Tạo Task", use_container_width=True, type="primary", key="adm_submit_task"):
                if not adm_ten_task.strip():
                    st.error("⛔ Vui lòng nhập tên công việc!")
                elif not ds_cong_ty:
                    st.error("⛔ Vui lòng thêm ít nhất một công ty trước!")
                else:
                    phe_duyet_luu = adm_phe_duyet if adm_phe_duyet != "-- Không chọn --" else ""
                    with st.spinner("Đang lưu lên Google Sheets..."):
                        id_moi = them_cong_viec(
                            adm_ten_task.strip(), adm_mo_ta.strip(), adm_nguoi_giao,
                            adm_deadline.strftime("%Y-%m-%d"),
                            cong_ty=adm_cong_ty, cong_so="",
                            nam=adm_nam.strip(), trang_thai=adm_trang_thai,
                            nguoi_phe_duyet=phe_duyet_luu,
                            checklist=list(st.session_state.get(f"{_ADM_PREFIX}_checklist", [])),
                            cong_viec_con=list(st.session_state.get(f"{_ADM_PREFIX}_cong_viec_con", [])),
                            cong_doan="",
                            loai_may=adm_loai_may if adm_loai_may != "-- Không chọn --" else "",
                            tinh_trang=adm_tinh_trang if adm_tinh_trang != "-- Không chọn --" else "",
                            cong_suat=adm_cong_suat.strip(),
                            so_cuc=adm_so_cuc.strip(),
                            ma_so=adm_ma_so.strip(),
                            so_po_noi_bo=adm_so_po_noi_bo.strip(),
                            so_po_kh=adm_so_po_kh.strip(),
                            so_bao_gia=adm_so_bao_gia.strip(),
                        )
                    st.session_state[f"{_ADM_PREFIX}_checklist"]    = []
                    st.session_state[f"{_ADM_PREFIX}_cong_viec_con"] = []
                    st.session_state[f"{_ADM_PREFIX}_cv_seeded"]     = False
                    for _k in ["adm_ten_task", "adm_mo_ta", "adm_cong_suat", "adm_so_cuc",
                               "adm_ma_so", "adm_so_po_noi_bo", "adm_so_po_kh", "adm_so_bao_gia"]:
                        st.session_state.pop(_k, None)
                    lay_danh_sach_cong_viec.clear()
                    st.session_state["_adm_task_success"] = (
                        f"✅ Đã tạo task #{id_moi} thành công! "
                        f"Công ty: **{adm_cong_ty}** | Giao: **{adm_nguoi_giao}**"
                    )
                    st.rerun(scope="app")

        _fragment_tao_task_admin()

    # ══════════════════════════════════════════════
    # TAB 4 — TỔNG QUAN
    # ══════════════════════════════════════════════
    with tab_tong_quan:
        if st.button("🔄 Làm mới dữ liệu", key="adm_lam_moi"):
            lay_danh_sach_cong_viec.clear()
            st.rerun()

        with st.spinner("Đang tải dữ liệu..."):
            df = lay_danh_sach_cong_viec()

        if df.empty:
            st.info("ℹ️ Chưa có công việc nào. Hãy tạo mới ở tab **➕ Tạo Công Việc Mới**!")
        else:
            # ── KPI: Tổng + mỗi trạng thái xuất hiện trong data ──
            ds_tt_data = df["Trạng Thái"].dropna().unique().tolist()
            # Sắp theo thứ tự chuẩn, thêm các trạng thái lạ ở cuối
            _THU_TU = lay_ten_cac_trang_thai() or _DS_TRANG_THAI_MAC_DINH
            ds_tt_sorted = [t for t in _THU_TU if t in ds_tt_data] + \
                           [t for t in ds_tt_data if t not in _THU_TU]

            _ICON_KPI = {
                "Đang Kiểm Tra": "🔵", "Đã Phê Duyệt": "🟢", "Đã Báo Giá": "🟠",
                "Có Đơn": "🟣", "Chờ Giao": "🟡", "Đã Hoàn Thành - Giao Máy": "✅",
                "Đã Xuất Hóa Đơn": "⬜", "Bảo Hành - Trả Lại": "🔴",
                "Chờ Làm": "🔴", "Đang Làm": "🟡", "Hoàn Thành": "🟢",
            }

            # KPI cards: 2 cột để hiển thị đẹp trên mobile
            kpi_items = [("📋 TỔNG TASK", len(df))] + [
                (f"{_ICON_KPI.get(tt, '⚪')} {tt.upper()}", len(df[df["Trạng Thái"] == tt]))
                for tt in ds_tt_sorted
            ]
            for row_start in range(0, len(kpi_items), 2):
                chunk = kpi_items[row_start:row_start + 2]
                cols_kpi = st.columns(2)
                for col_kpi, (label, val) in zip(cols_kpi, chunk):
                    col_kpi.metric(label, val)

            st.divider()

            # ── Bộ lọc ──
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                all_tt = df["Trạng Thái"].dropna().unique().tolist()
                loc_trang_thai = st.multiselect(
                    "Lọc theo trạng thái",
                    options=all_tt,
                    default=[],
                    placeholder="Hiển thị tất cả...",
                    key="adm_loc_tt",
                )
            with col_f2:
                danh_sach_nv = df["Nhân Viên"].dropna().unique().tolist()
                loc_nhan_vien = st.multiselect("Lọc theo nhân viên", options=danh_sach_nv, key="adm_loc_nv")
            with col_f3:
                danh_sach_ct = df["Công Ty"].dropna().unique().tolist() if "Công Ty" in df.columns else []
                loc_cong_ty  = st.multiselect("🏢 Lọc theo Công Ty", options=danh_sach_ct, key="adm_loc_ct")

            df_hien_thi = df.copy()
            if loc_trang_thai:  # rỗng = hiển thị tất cả
                df_hien_thi = df_hien_thi[df_hien_thi["Trạng Thái"].isin(loc_trang_thai)]
            if loc_nhan_vien:
                df_hien_thi = df_hien_thi[df_hien_thi["Nhân Viên"].isin(loc_nhan_vien)]
            if loc_cong_ty:
                df_hien_thi = df_hien_thi[df_hien_thi["Công Ty"].isin(loc_cong_ty)]

            def render_bang_dep(df_in: pd.DataFrame):
                mau_trang_thai = {
                    "Chờ Làm":                     ("🔴", "#fee2e2", "#dc2626", "#fef2f2"),
                    "Đang Làm":                    ("🟡", "#fef9c3", "#d97706", "#fffbeb"),
                    "Hoàn Thành":                  ("🟢", "#dcfce7", "#16a34a", "#f0fdf4"),
                    "Đang Kiểm Tra":               ("🔵", "#dbeafe", "#1d4ed8", "#eff6ff"),
                    "Đã Phê Duyệt":               ("🟢", "#dcfce7", "#15803d", "#f0fdf4"),
                    "Đã Báo Giá":                 ("🟠", "#fef3c7", "#b45309", "#fffbeb"),
                    "Có Đơn":                      ("🟣", "#ede9fe", "#7c3aed", "#f5f3ff"),
                    "Chờ Giao":                    ("🟡", "#fef9c3", "#a16207", "#fefce8"),
                    "Đã Hoàn Thành - Giao Máy":   ("✅", "#bbf7d0", "#166534", "#f0fdf4"),
                    "Đã Xuất Hóa Đơn":            ("⬜", "#f3f4f6", "#374151", "#f9fafb"),
                    "Bảo Hành - Trả Lại":         ("🔴", "#fee2e2", "#b91c1c", "#fef2f2"),
                }
                cols_hien_thi = ["ID", "Công Ty", "Công Số", "Năm",
                                 "Tên Công Việc", "Nhân Viên", "Trạng Thái",
                                 "Ngày Tạo", "Hạn Hoàn Thành"]
                cols_co  = [c for c in cols_hien_thi if c in df_in.columns]
                df_show  = df_in[cols_co]
                header_html = "".join(f"<th>{c}</th>" for c in cols_co)
                rows_html = ""
                for _, row in df_show.iterrows():
                    cells = ""
                    for col in cols_co:
                        val = str(row[col]) if pd.notna(row[col]) else ""
                        if col == "Trạng Thái":
                            icon, bg, color, _ = mau_trang_thai.get(val, ("⚪", "#f3f4f6", "#6b7280", "#f9fafb"))
                            cells += (
                                f'<td><span style="background:{bg};color:{color};'
                                f'padding:4px 12px;border-radius:20px;font-weight:700;'
                                f'font-size:0.82rem;white-space:nowrap;'
                                f'border:1.5px solid {color}40;">'
                                f'{icon} {val}</span></td>'
                            )
                        elif col == "ID":
                            cells += (
                                f'<td><span style="background:#ede9fe;color:#7c3aed;'
                                f'padding:3px 10px;border-radius:8px;font-weight:700;'
                                f'font-size:0.85rem;">#{val}</span></td>'
                            )
                        elif col == "Công Ty":
                            cells += f'<td><strong style="color:#1e1b4b;">{val}</strong></td>'
                        elif col == "Hạn Hoàn Thành":
                            cells += f'<td><span style="color:#dc2626;font-weight:600;">⏰ {val}</span></td>'
                        else:
                            cells += f"<td>{val}</td>"
                    rows_html += f"<tr>{cells}</tr>"

                html = f"""
                <style>
                .custom-table-wrap{{overflow-x:auto;border-radius:16px;
                    box-shadow:0 4px 24px rgba(102,126,234,0.13);margin-top:0.5rem;}}
                .custom-table{{width:100%;border-collapse:collapse;
                    font-family:'Be Vietnam Pro',sans-serif;font-size:0.88rem;
                    background:white;border-radius:16px;overflow:hidden;}}
                .custom-table thead tr{{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);}}
                .custom-table thead th{{color:white;font-weight:700;padding:14px 16px;
                    text-align:left;white-space:nowrap;border:none;font-size:0.85rem;
                    text-transform:uppercase;}}
                .custom-table tbody tr{{border-bottom:1px solid #f0f0f5;}}
                .custom-table tbody tr:nth-child(even){{background:#f8f7ff;}}
                .custom-table tbody tr:hover{{background:#ede9fe!important;}}
                .custom-table tbody td{{padding:12px 16px;color:#374151;
                    vertical-align:middle;white-space:nowrap;}}
                </style>
                <div class="custom-table-wrap">
                <table class="custom-table">
                <thead><tr>{header_html}</tr></thead>
                <tbody>{rows_html}</tbody>
                </table></div>"""
                st.markdown(html, unsafe_allow_html=True)

            render_bang_dep(df_hien_thi)

    # ========================================================
    # Tab 5: Bảng Quản Lý (Kanban board toàn bộ task)
    # ========================================================
    with tab_board:
        st.subheader("🗂️ Bảng Quản Lý Công Việc")
        col_adm_ref, col_adm_search = st.columns([1, 4])
        with col_adm_ref:
            if st.button("🔄 Làm mới", key="adm_board_refresh"):
                lay_danh_sach_cong_viec.clear()
                st.rerun()
        with col_adm_search:
            adm_q = st.text_input(
                "🔍",
                placeholder="Tìm kiếm theo tên công việc...",
                key="adm_board_search",
                label_visibility="collapsed",
            )

        with st.spinner("Đang tải..."):
            df_board = lay_danh_sach_cong_viec()

        if adm_q.strip():
            df_board = df_board[
                df_board["Tên Công Việc"].fillna("").str.lower().str.contains(adm_q.strip().lower())
            ]

        col_f1, col_f2 = st.columns(2)
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            ds_nv_f = sorted(df_board["Nhân Viên"].dropna().unique().tolist())
            loc_nv_b = st.multiselect("👤 Lọc nhân viên", ds_nv_f, key="adm_board_nv", placeholder="Tất cả")
            if loc_nv_b:
                df_board = df_board[df_board["Nhân Viên"].isin(loc_nv_b)]
        with col_f2:
            ds_ct_f = sorted(df_board["Công Ty"].dropna().unique().tolist())
            loc_ct_b = st.multiselect("🏢 Lọc công ty", ds_ct_f, key="adm_board_ct", placeholder="Tất cả")
            if loc_ct_b:
                df_board = df_board[df_board["Công Ty"].isin(loc_ct_b)]
        with col_f3:
            ds_nam_f = sorted(
                [str(y) for y in df_board["Năm"].dropna().unique() if str(y).strip() != ""],
                reverse=True,
            ) if "Năm" in df_board.columns else []
            loc_nam_b = st.selectbox(
                "📅 Lọc năm",
                options=["Tất cả"] + ds_nam_f,
                key="adm_board_nam",
            ) if ds_nam_f else "Tất cả"
            if loc_nam_b != "Tất cả":
                df_board = df_board[df_board["Năm"].astype(str) == loc_nam_b]

        ds_tt_board = lay_ten_cac_trang_thai() or ["Chờ Làm", "Đang Làm", "Hoàn Thành"]

        # ── KANBAN BOARD ──────────────────────────────────────────
        _render_kanban_board(df_board, ds_tt_board, board_key="adm_kb")

    # ========================================================
    # Tab 6: Quản Lý Công Việc Con
    # ========================================================
    with tab_cvc:
        st.subheader("📋 Quản Lý Công Việc Con")

        col_ref_cvc, _ = st.columns([1, 4])
        with col_ref_cvc:
            if st.button("🔄 Làm mới", key="adm_cvc_refresh"):
                lay_danh_sach_cong_viec.clear()
                st.rerun()

        with st.spinner("Đang tải dữ liệu..."):
            df_all_cvc = lay_danh_sach_cong_viec()

        if df_all_cvc.empty:
            st.info("ℹ️ Chưa có công việc nào.")
        else:
            # Flatten tất cả công việc con ra từng dòng
            today = datetime.today().date()
            rows_cvc = []
            stt = 0
            for _, task_row in df_all_cvc.iterrows():
                raw = task_row.get("Công Việc Con", "") or "[]"
                try:
                    ds_cv = json.loads(raw) if raw else []
                except Exception:
                    ds_cv = []
                if not isinstance(ds_cv, list) or not ds_cv:
                    continue

                han_str  = str(task_row.get("Hạn Hoàn Thành", "") or "")
                han_date = None
                try:
                    if han_str:
                        han_date = datetime.strptime(han_str[:10], "%Y-%m-%d").date()
                except Exception:
                    pass

                for cv in ds_cv:
                    if not isinstance(cv, dict):
                        continue
                    done = bool(cv.get("done", False))
                    if not done:
                        continue  # Chỉ hiển thị công việc con đã hoàn thành
                    stt += 1
                    ten_cv   = cv.get("ten", cv.get("Tên", ""))
                    nv       = cv.get("nhan_vien", cv.get("Nhân Viên", cv.get("nguoi", ""))) or ""
                    ngay_ht  = cv.get("ngay_hoan_thanh", "")

                    # Tính Tình Trạng (deadline-based)
                    if done and ngay_ht:
                        try:
                            ht_date = datetime.strptime(ngay_ht[:10], "%Y-%m-%d").date()
                            if han_date:
                                if ht_date < han_date:
                                    tinh_trang_td = "Trước hạn"
                                elif ht_date == han_date:
                                    tinh_trang_td = "Đúng hạn"
                                else:
                                    tinh_trang_td = "Quá hạn"
                            else:
                                tinh_trang_td = "Hoàn thành"
                        except Exception:
                            tinh_trang_td = "Hoàn thành"
                    elif done:
                        tinh_trang_td = "Hoàn thành"
                    elif han_date and today > han_date:
                        tinh_trang_td = "Quá hạn"
                    elif han_date and today == han_date:
                        tinh_trang_td = "Đúng hạn"
                    else:
                        tinh_trang_td = "Chưa xong"

                    # Ngày hoàn thành dạng date object để lọc
                    ngay_ht_date = None
                    ngay_ht_hien = ""
                    if done and ngay_ht:
                        try:
                            ngay_ht_date = datetime.strptime(ngay_ht[:10], "%Y-%m-%d").date()
                            ngay_ht_hien = ngay_ht_date.strftime("%d/%m/%Y")
                        except Exception:
                            ngay_ht_hien = "✅ (chưa rõ ngày)"
                    elif done:
                        ngay_ht_hien = "✅ (chưa rõ ngày)"

                    rows_cvc.append({
                        "STT":             stt,
                        "Tên Công Ty":     task_row.get("Công Ty", ""),
                        "Tên Công Việc":   task_row.get("Tên Công Việc", ""),
                        "Công Suất":       task_row.get("Công Suất", ""),
                        "Mã Số":           task_row.get("Mã Số", ""),
                        "Công Việc Con":   ten_cv,
                        "Nhân Viên":       nv,
                        "Ngày Hoàn Thành": ngay_ht_hien,
                        "_ngay_ht_raw":    ngay_ht_date,  # dùng để lọc, ẩn khi hiển thị
                        "Trạng Thái":      task_row.get("Trạng Thái", ""),
                        "Loại Máy":        task_row.get("Loại Máy", ""),
                        "Tình Trạng":      tinh_trang_td,
                    })

            if not rows_cvc:
                st.info("ℹ️ Chưa có công việc con nào.")
            else:
                df_cvc = pd.DataFrame(rows_cvc)

                # ── Bộ lọc hàng 1: nhân viên / công ty / tình trạng ──
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    ds_nv_cvc = sorted(df_cvc["Nhân Viên"].dropna().unique().tolist())
                    loc_nv_cvc = st.multiselect("👤 Lọc nhân viên", ds_nv_cvc, key="cvc_loc_nv", placeholder="Tất cả")
                with col_f2:
                    ds_ct_cvc = sorted(df_cvc["Tên Công Ty"].dropna().unique().tolist())
                    loc_ct_cvc = st.multiselect("🏢 Lọc công ty", ds_ct_cvc, key="cvc_loc_ct", placeholder="Tất cả")
                with col_f3:
                    ds_tt_cvc = sorted(df_cvc["Tình Trạng"].dropna().unique().tolist())
                    loc_tt_cvc = st.multiselect("📊 Lọc tình trạng", ds_tt_cvc, key="cvc_loc_tt", placeholder="Tất cả")

                # ── Bộ lọc hàng 2: khoảng ngày hoàn thành ──
                col_d1, col_d2, _ = st.columns(3)
                with col_d1:
                    tu_ngay = st.date_input(
                        "📅 Từ ngày (Ngày Hoàn Thành)",
                        value=None,
                        format="DD/MM/YYYY",
                        key="cvc_tu_ngay",
                    )
                with col_d2:
                    den_ngay = st.date_input(
                        "📅 Đến ngày",
                        value=None,
                        format="DD/MM/YYYY",
                        key="cvc_den_ngay",
                    )

                df_show_cvc = df_cvc.copy()
                if loc_nv_cvc:
                    df_show_cvc = df_show_cvc[df_show_cvc["Nhân Viên"].isin(loc_nv_cvc)]
                if loc_ct_cvc:
                    df_show_cvc = df_show_cvc[df_show_cvc["Tên Công Ty"].isin(loc_ct_cvc)]
                if loc_tt_cvc:
                    df_show_cvc = df_show_cvc[df_show_cvc["Tình Trạng"].isin(loc_tt_cvc)]
                if tu_ngay:
                    df_show_cvc = df_show_cvc[df_show_cvc["_ngay_ht_raw"].apply(
                        lambda d: d is not None and d >= tu_ngay)]
                if den_ngay:
                    df_show_cvc = df_show_cvc[df_show_cvc["_ngay_ht_raw"].apply(
                        lambda d: d is not None and d <= den_ngay)]

                # ── KPI nhanh ──
                total = len(df_show_cvc)
                done_count  = len(df_show_cvc[df_show_cvc["Ngày Hoàn Thành"] != ""])
                qua_han     = len(df_show_cvc[df_show_cvc["Tình Trạng"] == "Quá hạn"])
                truoc_han   = len(df_show_cvc[df_show_cvc["Tình Trạng"] == "Trước hạn"])
                kpi_cols = st.columns(4)
                kpi_cols[0].metric("📋 Tổng việc con", total)
                kpi_cols[1].metric("✅ Hoàn thành", done_count)
                kpi_cols[2].metric("🔴 Quá hạn", qua_han)
                kpi_cols[3].metric("🟢 Trước hạn", truoc_han)

                st.divider()

                # ── Bảng HTML đẹp ──
                _mau_tinh_trang = {
                    "Trước hạn":  ("#dcfce7", "#16a34a"),
                    "Đúng hạn":   ("#fef9c3", "#d97706"),
                    "Quá hạn":    ("#fee2e2", "#dc2626"),
                    "Hoàn thành": ("#dbeafe", "#1d4ed8"),
                    "Chưa xong":  ("#f3f4f6", "#6b7280"),
                }
                cols_show = ["STT", "Tên Công Ty", "Tên Công Việc", "Công Suất", "Mã Số",
                             "Công Việc Con", "Nhân Viên", "Ngày Hoàn Thành", "Trạng Thái",
                             "Loại Máy", "Tình Trạng"]
                header_html = "".join(f"<th>{c}</th>" for c in cols_show)
                rows_html = ""
                for _, r in df_show_cvc.iterrows():
                    cells = ""
                    for c in cols_show:
                        val = str(r.get(c, "") or "")
                        if c == "Tình Trạng":
                            bg, fg = _mau_tinh_trang.get(val, ("#f3f4f6", "#6b7280"))
                            cells += (
                                f'<td><span style="background:{bg};color:{fg};padding:3px 10px;'
                                f'border-radius:20px;font-weight:700;font-size:0.82rem;'
                                f'border:1.5px solid {fg}40;white-space:nowrap;">{val}</span></td>'
                            )
                        elif c == "STT":
                            cells += f'<td style="color:#7c3aed;font-weight:700;">{val}</td>'
                        elif c == "Công Việc Con":
                            cells += f'<td><strong>{val}</strong></td>'
                        elif c == "Tên Công Ty":
                            cells += f'<td style="color:#1e1b4b;font-weight:600;">{val}</td>'
                        else:
                            cells += f"<td>{val}</td>"
                    rows_html += f"<tr>{cells}</tr>"

                html_cvc = f"""
                <style>
                .cvc-table-wrap{{overflow-x:auto;border-radius:16px;
                    box-shadow:0 4px 24px rgba(102,126,234,0.13);margin-top:0.5rem;}}
                .cvc-table{{width:100%;border-collapse:collapse;
                    font-family:'Be Vietnam Pro',sans-serif;font-size:0.86rem;
                    background:white;border-radius:16px;overflow:hidden;}}
                .cvc-table thead tr{{background:linear-gradient(135deg,#f59e0b 0%,#d97706 100%);}}
                .cvc-table thead th{{color:white;font-weight:700;padding:12px 14px;
                    text-align:left;white-space:nowrap;border:none;font-size:0.82rem;
                    text-transform:uppercase;}}
                .cvc-table tbody tr{{border-bottom:1px solid #f0f0f5;}}
                .cvc-table tbody tr:nth-child(even){{background:#fffbeb;}}
                .cvc-table tbody tr:hover{{background:#fef3c7!important;}}
                .cvc-table tbody td{{padding:10px 14px;color:#374151;
                    vertical-align:middle;white-space:nowrap;}}
                </style>
                <div class="cvc-table-wrap">
                <table class="cvc-table">
                <thead><tr>{header_html}</tr></thead>
                <tbody>{rows_html}</tbody>
                </table></div>"""
                st.markdown(html_cvc, unsafe_allow_html=True)
                st.caption(f"Hiển thị {len(df_show_cvc)} / {total} công việc con")

                # ── Xuất Excel ──
                import io
                cols_excel = ["STT", "Tên Công Ty", "Tên Công Việc", "Công Suất", "Mã Số",
                              "Công Việc Con", "Nhân Viên", "Ngày Hoàn Thành", "Trạng Thái",
                              "Loại Máy", "Tình Trạng"]
                df_excel = df_show_cvc[cols_excel].copy()
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    df_excel.to_excel(writer, index=False, sheet_name="CongViecCon")
                    ws = writer.sheets["CongViecCon"]
                    # Định dạng header
                    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
                    header_fill = PatternFill("solid", fgColor="F59E0B")
                    thin = Side(style="thin", color="DDDDDD")
                    border = Border(left=thin, right=thin, top=thin, bottom=thin)
                    for cell in ws[1]:
                        cell.font      = Font(bold=True, color="FFFFFF", size=11)
                        cell.fill      = header_fill
                        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                        cell.border    = border
                    # Tô màu cột Tình Trạng
                    _mau_excel = {
                        "Trước hạn": "DCFCE7", "Đúng hạn": "FEF9C3",
                        "Quá hạn":   "FEE2E2", "Hoàn thành": "DBEAFE",
                        "Chưa xong": "F3F4F6",
                    }
                    col_tt_idx = cols_excel.index("Tình Trạng") + 1
                    for row_idx, row_cells in enumerate(ws.iter_rows(min_row=2), start=2):
                        for cell in row_cells:
                            cell.border    = border
                            cell.alignment = Alignment(vertical="center")
                        tt_val = ws.cell(row=row_idx, column=col_tt_idx).value or ""
                        if tt_val in _mau_excel:
                            ws.cell(row=row_idx, column=col_tt_idx).fill = PatternFill("solid", fgColor=_mau_excel[tt_val])
                    # Tự động độ rộng cột
                    for col in ws.columns:
                        max_len = max((len(str(c.value or "")) for c in col), default=8)
                        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)
                    ws.row_dimensions[1].height = 30
                buf.seek(0)
                ten_file = f"cong_viec_con_{datetime.now().strftime('%d%m%Y_%H%M')}.xlsx"
                st.download_button(
                    label="📥 Xuất Excel",
                    data=buf,
                    file_name=ten_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=False,
                )

    # ========================================================
    # Tab 7: Theo Dõi Tiến Độ Máy
    # ========================================================
    with tab_tdtdm:
        st.subheader("🔩 Theo Dõi Tiến Độ Máy")

        col_ref_tdm, _ = st.columns([1, 4])
        with col_ref_tdm:
            if st.button("🔄 Làm mới", key="adm_tdm_refresh"):
                lay_danh_sach_cong_viec.clear()
                st.rerun()

        with st.spinner("Đang tải dữ liệu..."):
            df_tdm_all = lay_danh_sach_cong_viec()

        if df_tdm_all.empty:
            st.info("ℹ️ Chưa có công việc nào.")
        else:
            today_tdm = datetime.today().date()
            rows_tdm  = []

            for stt_tdm, (_, r) in enumerate(df_tdm_all.iterrows(), start=1):
                han_str_tdm  = str(r.get("Hạn Hoàn Thành", "") or "")
                ngay_kt_str  = str(r.get("Ngày Kết Thúc", "") or "")
                han_date_tdm = None
                ngay_kt_date = None
                try:
                    if han_str_tdm:
                        han_date_tdm = datetime.strptime(han_str_tdm[:10], "%Y-%m-%d").date()
                except Exception:
                    pass
                try:
                    if ngay_kt_str:
                        ngay_kt_date = datetime.strptime(ngay_kt_str[:10], "%Y-%m-%d").date()
                except Exception:
                    pass

                # Tính Tình Trạng
                if ngay_kt_date and han_date_tdm:
                    if ngay_kt_date < han_date_tdm:
                        tinh_trang_tdm = "Trước hạn"
                    elif ngay_kt_date == han_date_tdm:
                        tinh_trang_tdm = "Đúng hạn"
                    else:
                        tinh_trang_tdm = "Quá hạn"
                elif ngay_kt_date:
                    tinh_trang_tdm = "Hoàn thành"
                elif han_date_tdm and today_tdm > han_date_tdm:
                    tinh_trang_tdm = "Quá hạn"
                elif han_date_tdm and today_tdm == han_date_tdm:
                    tinh_trang_tdm = "Đúng hạn"
                else:
                    tinh_trang_tdm = "Chưa xong"

                # Định dạng ngày hiển thị
                ngay_nhan_hien  = ""
                ngay_giao_hien  = ""
                han_hien        = ""
                try:
                    ngay_tao_str = str(r.get("Ngày Tạo", "") or "")
                    if ngay_tao_str:
                        ngay_nhan_hien = datetime.strptime(ngay_tao_str[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
                except Exception:
                    ngay_nhan_hien = str(r.get("Ngày Tạo", "") or "")
                try:
                    if han_date_tdm:
                        han_hien = han_date_tdm.strftime("%d/%m/%Y")
                except Exception:
                    han_hien = han_str_tdm
                try:
                    if ngay_kt_date:
                        ngay_giao_hien = ngay_kt_date.strftime("%d/%m/%Y")
                except Exception:
                    ngay_giao_hien = ngay_kt_str

                rows_tdm.append({
                    "STT":              stt_tdm,
                    "Tên Công Ty":      r.get("Công Ty", ""),
                    "Tên Công Việc":    r.get("Tên Công Việc", ""),
                    "Công Suất":        r.get("Công Suất", ""),
                    "Mã Số Máy":        r.get("Mã Số", ""),
                    "Số PO Nội Bộ":     r.get("Số PO Nội Bộ", ""),
                    "Số PO KH/HĐ":      r.get("Số PO KH/HĐ", ""),
                    "Số Báo Giá":       r.get("Số Báo Giá", ""),
                    "Trạng Thái":       r.get("Trạng Thái", ""),
                    "Ngày Nhận Máy":    ngay_nhan_hien,
                    "Hạn Hoàn Thành":   han_hien,
                    "Ngày Giao Máy":    ngay_giao_hien,
                    "_han_raw":         han_date_tdm,
                    "_giao_raw":        ngay_kt_date,
                    "Loại Máy":         r.get("Loại Máy", ""),
                    "Tình Trạng":       tinh_trang_tdm,
                })

            if not rows_tdm:
                st.info("ℹ️ Chưa có dữ liệu.")
            else:
                df_tdm = pd.DataFrame(rows_tdm)

                # ── Bộ lọc hàng 1 ──
                col_tf1, col_tf2, col_tf3 = st.columns(3)
                with col_tf1:
                    ds_nv_tdm = sorted(df_tdm["Tên Công Ty"].dropna().unique().tolist())
                    loc_ct_tdm = st.multiselect("🏢 Lọc công ty", ds_nv_tdm, key="tdm_loc_ct", placeholder="Tất cả")
                with col_tf2:
                    ds_tt_tdm = sorted(df_tdm["Tình Trạng"].dropna().unique().tolist())
                    loc_tt_tdm = st.multiselect("📊 Lọc tình trạng", ds_tt_tdm, key="tdm_loc_tt", placeholder="Tất cả")
                with col_tf3:
                    ds_lm_tdm = sorted(df_tdm["Loại Máy"].dropna().unique().tolist())
                    ds_lm_tdm = [x for x in ds_lm_tdm if x.strip()]
                    loc_lm_tdm = st.multiselect("🔧 Lọc loại máy", ds_lm_tdm, key="tdm_loc_lm", placeholder="Tất cả")

                # ── Bộ lọc hàng 2: khoảng ngày nhận / giao ──
                col_td1, col_td2, col_td3, col_td4 = st.columns(4)
                with col_td1:
                    tu_ngay_nhan = st.date_input("📅 Nhận máy từ", value=None, format="DD/MM/YYYY", key="tdm_tu_nhan")
                with col_td2:
                    den_ngay_nhan = st.date_input("📅 Nhận máy đến", value=None, format="DD/MM/YYYY", key="tdm_den_nhan")
                with col_td3:
                    tu_ngay_giao = st.date_input("📅 Giao máy từ", value=None, format="DD/MM/YYYY", key="tdm_tu_giao")
                with col_td4:
                    den_ngay_giao = st.date_input("📅 Giao máy đến", value=None, format="DD/MM/YYYY", key="tdm_den_giao")

                df_show_tdm = df_tdm.copy()
                if loc_ct_tdm:
                    df_show_tdm = df_show_tdm[df_show_tdm["Tên Công Ty"].isin(loc_ct_tdm)]
                if loc_tt_tdm:
                    df_show_tdm = df_show_tdm[df_show_tdm["Tình Trạng"].isin(loc_tt_tdm)]
                if loc_lm_tdm:
                    df_show_tdm = df_show_tdm[df_show_tdm["Loại Máy"].isin(loc_lm_tdm)]
                if tu_ngay_nhan:
                    df_show_tdm = df_show_tdm[df_show_tdm["Ngày Nhận Máy"].apply(
                        lambda v: _parse_date_display(v) is not None and _parse_date_display(v) >= tu_ngay_nhan)]
                if den_ngay_nhan:
                    df_show_tdm = df_show_tdm[df_show_tdm["Ngày Nhận Máy"].apply(
                        lambda v: _parse_date_display(v) is not None and _parse_date_display(v) <= den_ngay_nhan)]
                if tu_ngay_giao:
                    df_show_tdm = df_show_tdm[df_show_tdm["_giao_raw"].apply(
                        lambda d: d is not None and d >= tu_ngay_giao)]
                if den_ngay_giao:
                    df_show_tdm = df_show_tdm[df_show_tdm["_giao_raw"].apply(
                        lambda d: d is not None and d <= den_ngay_giao)]

                # ── KPI nhanh ──
                total_tdm   = len(df_show_tdm)
                da_giao     = len(df_show_tdm[df_show_tdm["Ngày Giao Máy"] != ""])
                qua_han_tdm = len(df_show_tdm[df_show_tdm["Tình Trạng"] == "Quá hạn"])
                truoc_han_tdm = len(df_show_tdm[df_show_tdm["Tình Trạng"] == "Trước hạn"])
                kpi_c = st.columns(4)
                kpi_c[0].metric("🔩 Tổng máy", total_tdm)
                kpi_c[1].metric("✅ Đã giao", da_giao)
                kpi_c[2].metric("🔴 Quá hạn", qua_han_tdm)
                kpi_c[3].metric("🟢 Trước hạn", truoc_han_tdm)

                st.divider()

                # ── Bảng HTML đẹp ──
                _mau_tt_tdm = {
                    "Trước hạn":  ("#dcfce7", "#16a34a"),
                    "Đúng hạn":   ("#fef9c3", "#d97706"),
                    "Quá hạn":    ("#fee2e2", "#dc2626"),
                    "Hoàn thành": ("#dbeafe", "#1d4ed8"),
                    "Chưa xong":  ("#f3f4f6", "#6b7280"),
                }
                _mau_trang_thai_tdm = {
                    "Chờ Làm": ("#fee2e2", "#dc2626"), "Đang Làm": ("#fef9c3", "#d97706"),
                    "Hoàn Thành": ("#dcfce7", "#16a34a"), "Đang Kiểm Tra": ("#dbeafe", "#1d4ed8"),
                    "Đã Phê Duyệt": ("#dcfce7", "#15803d"), "Đã Báo Giá": ("#fef3c7", "#b45309"),
                    "Có Đơn": ("#ede9fe", "#7c3aed"), "Chờ Giao": ("#fef9c3", "#a16207"),
                    "Đã Hoàn Thành - Giao Máy": ("#bbf7d0", "#166534"),
                    "Đã Xuất Hóa Đơn": ("#f3f4f6", "#374151"),
                    "Bảo Hành - Trả Lại": ("#fee2e2", "#b91c1c"),
                }
                cols_show_tdm = ["STT", "Tên Công Ty", "Tên Công Việc", "Công Suất", "Mã Số Máy",
                                 "Số PO Nội Bộ", "Số PO KH/HĐ", "Số Báo Giá", "Trạng Thái",
                                 "Ngày Nhận Máy", "Hạn Hoàn Thành", "Ngày Giao Máy",
                                 "Loại Máy", "Tình Trạng"]
                header_html_tdm = "".join(f"<th>{c}</th>" for c in cols_show_tdm)
                rows_html_tdm = ""
                for _, row_t in df_show_tdm.iterrows():
                    cells = ""
                    for c in cols_show_tdm:
                        val = str(row_t.get(c, "") or "")
                        if c == "Tình Trạng":
                            bg, fg = _mau_tt_tdm.get(val, ("#f3f4f6", "#6b7280"))
                            cells += (
                                f'<td><span style="background:{bg};color:{fg};padding:3px 10px;'
                                f'border-radius:20px;font-weight:700;font-size:0.82rem;'
                                f'border:1.5px solid {fg}40;white-space:nowrap;">{val}</span></td>'
                            )
                        elif c == "Trạng Thái":
                            bg2, fg2 = _mau_trang_thai_tdm.get(val, ("#f3f4f6", "#6b7280"))
                            cells += (
                                f'<td><span style="background:{bg2};color:{fg2};padding:3px 10px;'
                                f'border-radius:20px;font-weight:600;font-size:0.82rem;'
                                f'white-space:nowrap;">{val}</span></td>'
                            )
                        elif c == "STT":
                            cells += f'<td style="color:#7c3aed;font-weight:700;">{val}</td>'
                        elif c == "Tên Công Ty":
                            cells += f'<td style="color:#1e1b4b;font-weight:600;">{val}</td>'
                        elif c == "Hạn Hoàn Thành":
                            cells += f'<td style="color:#dc2626;font-weight:600;">⏰ {val}</td>'
                        else:
                            cells += f"<td>{val}</td>"
                    rows_html_tdm += f"<tr>{cells}</tr>"

                html_tdm = f"""
                <style>
                .tdm-table-wrap{{overflow-x:auto;border-radius:16px;
                    box-shadow:0 4px 24px rgba(102,126,234,0.13);margin-top:0.5rem;}}
                .tdm-table{{width:100%;border-collapse:collapse;
                    font-family:'Be Vietnam Pro',sans-serif;font-size:0.86rem;
                    background:white;border-radius:16px;overflow:hidden;}}
                .tdm-table thead tr{{background:linear-gradient(135deg,#3b82f6 0%,#1d4ed8 100%);}}
                .tdm-table thead th{{color:white;font-weight:700;padding:12px 14px;
                    text-align:left;white-space:nowrap;border:none;font-size:0.82rem;
                    text-transform:uppercase;}}
                .tdm-table tbody tr{{border-bottom:1px solid #f0f0f5;}}
                .tdm-table tbody tr:nth-child(even){{background:#eff6ff;}}
                .tdm-table tbody tr:hover{{background:#dbeafe!important;}}
                .tdm-table tbody td{{padding:10px 14px;color:#374151;
                    vertical-align:middle;white-space:nowrap;}}
                </style>
                <div class="tdm-table-wrap">
                <table class="tdm-table">
                <thead><tr>{header_html_tdm}</tr></thead>
                <tbody>{rows_html_tdm}</tbody>
                </table></div>"""
                st.markdown(html_tdm, unsafe_allow_html=True)
                st.caption(f"Hiển thị {len(df_show_tdm)} / {total_tdm} máy")

                # ── Xuất Excel ──
                import io
                cols_excel_tdm = cols_show_tdm
                df_excel_tdm = df_show_tdm[cols_excel_tdm].copy()
                buf_tdm = io.BytesIO()
                with pd.ExcelWriter(buf_tdm, engine="openpyxl") as writer_tdm:
                    df_excel_tdm.to_excel(writer_tdm, index=False, sheet_name="TheoDoiTienDoMay")
                    ws_tdm = writer_tdm.sheets["TheoDoiTienDoMay"]
                    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
                    hdr_fill_tdm = PatternFill("solid", fgColor="3B82F6")
                    thin2 = Side(style="thin", color="DDDDDD")
                    brd2  = Border(left=thin2, right=thin2, top=thin2, bottom=thin2)
                    for cell in ws_tdm[1]:
                        cell.font      = Font(bold=True, color="FFFFFF", size=11)
                        cell.fill      = hdr_fill_tdm
                        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                        cell.border    = brd2
                    _mau_excel_tdm = {
                        "Trước hạn": "DCFCE7", "Đúng hạn": "FEF9C3",
                        "Quá hạn":   "FEE2E2", "Hoàn thành": "DBEAFE",
                        "Chưa xong": "F3F4F6",
                    }
                    col_tt_idx_tdm = cols_excel_tdm.index("Tình Trạng") + 1
                    for row_idx, row_cells in enumerate(ws_tdm.iter_rows(min_row=2), start=2):
                        for cell in row_cells:
                            cell.border    = brd2
                            cell.alignment = Alignment(vertical="center")
                        tt_val = ws_tdm.cell(row=row_idx, column=col_tt_idx_tdm).value or ""
                        if tt_val in _mau_excel_tdm:
                            ws_tdm.cell(row=row_idx, column=col_tt_idx_tdm).fill = PatternFill("solid", fgColor=_mau_excel_tdm[tt_val])
                    for col in ws_tdm.columns:
                        max_len = max((len(str(c.value or "")) for c in col), default=8)
                        ws_tdm.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)
                    ws_tdm.row_dimensions[1].height = 30
                buf_tdm.seek(0)
                ten_file_tdm = f"theo_doi_tien_do_may_{datetime.now().strftime('%d%m%Y_%H%M')}.xlsx"
                st.download_button(
                    label="📥 Xuất Excel",
                    data=buf_tdm,
                    file_name=ten_file_tdm,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="tdm_xuat_excel",
                    use_container_width=False,
                )


def giao_dien_nhan_vien():
    """
    Giao diện dành cho nhân viên:
    - Nhân viên đã đăng nhập thấy công việc của chính mình (không cần chọn tên).
    - Admin khi vào chế độ NV có thể chọn bất kỳ nhân viên để xem.
    """
    st.header("👤 Trang Nhân Viên")

    vai_tro_hien_tai = st.session_state.get("vai_tro", "nhan_vien")
    ho_ten_hien_tai  = st.session_state.get("ho_ten", "")

    # Admin xem từ góc nhân viên → cho phép chọn
    if vai_tro_hien_tai == "admin":
        ten_nhan_vien = st.selectbox(
            "Chọn nhân viên để xem:",
            options=["-- Chọn nhân viên --"] + lay_danh_sach_nhan_vien()
        )
        if ten_nhan_vien == "-- Chọn nhân viên --":
            st.info("👆 Chọn nhân viên để xem công việc của họ.")
            return
    else:
        # Nhân viên đã đăng nhập → dùng tên từ session
        ten_nhan_vien = ho_ten_hien_tai
        st.markdown(f"##### Xin chào, **{ten_nhan_vien}** 👋")

    # Chuẩn hóa tên (trim khoảng trắng) để so sánh chính xác
    ten_nhan_vien = ten_nhan_vien.strip()

    # Mỗi lần tải trang luôn xóa cache để lấy dữ liệu mới nhất từ Google Sheets
    if "_last_nv_load" not in st.session_state or st.session_state["_last_nv_load"] != ten_nhan_vien:
        lay_danh_sach_cong_viec.clear()
        st.session_state["_last_nv_load"] = ten_nhan_vien

    # ---- Tabs ----
    tab_cong_viec, tab_phe_duyet, tab_tao_task = st.tabs([
        "🗂️ Bảng Quản Lý Công Việc",
        "✅ Việc Cần Phê Duyệt",
        "➕ Tạo Công Việc Mới"
    ])

    # ========================================================
    # Tab 1: Công việc của tôi
    # ========================================================
    with tab_cong_viec:
        # ── Toolbar ────────────────────────────────────────────
        col_btn, col_sq = st.columns([1, 4])
        with col_btn:
            if st.button("🔄 Làm mới", key="nv_refresh_board"):
                lay_danh_sach_cong_viec.clear()
                st.session_state.pop("_last_nv_load", None)
                st.rerun()
        with col_sq:
            q_search = st.text_input(
                "🔍",
                placeholder="Tìm kiếm tên công việc...",
                key="nv_search_q",
                label_visibility="collapsed",
            )

        with st.spinner("Đang tải công việc..."):
            df = lay_danh_sach_cong_viec()

        df["_nv_norm"] = df["Nhân Viên"].fillna("").str.strip().str.lower()
        df_cua_toi = df[df["_nv_norm"] == ten_nhan_vien.lower()].copy()

        if q_search.strip():
            df_cua_toi = df_cua_toi[
                df_cua_toi["Tên Công Việc"].fillna("").str.lower().str.contains(q_search.strip().lower())
            ]

        # Bộ lọc — mỗi cái 1 hàng full width
        ds_nam_nv = sorted(
            [str(y) for y in df_cua_toi["Năm"].dropna().unique() if str(y).strip() != ""],
            reverse=True,
        ) if "Năm" in df_cua_toi.columns else []
        loc_nam_nv = st.selectbox(
            "📅 Lọc theo năm",
            options=["Tất cả"] + ds_nam_nv,
            key="nv_loc_nam",
        ) if ds_nam_nv else "Tất cả"
        if loc_nam_nv != "Tất cả":
            df_cua_toi = df_cua_toi[df_cua_toi["Năm"].astype(str) == loc_nam_nv]

        ds_ct_nv = df_cua_toi["Công Ty"].dropna().unique().tolist() if "Công Ty" in df_cua_toi.columns else []
        if ds_ct_nv:
            loc_ct_nv = st.multiselect("🏢 Lọc công ty", ds_ct_nv, key="nv_loc_ct", placeholder="Tất cả")
            if loc_ct_nv:
                df_cua_toi = df_cua_toi[df_cua_toi["Công Ty"].isin(loc_ct_nv)]

        ds_tt = lay_ten_cac_trang_thai() or ["Chờ Làm", "Đang Làm", "Hoàn Thành"]

        if df_cua_toi.empty:
            st.success("🎉 Bạn hiện chưa có công việc nào được giao!")
        else:
            # ── KANBAN BOARD ────────────────────────────────────
            _render_kanban_board(df_cua_toi, ds_tt, board_key="nv_kb")

    # ========================================================
    # Tab 2: Việc Cần Phê Duyệt
    # ========================================================
    with tab_phe_duyet:
        col_btn_pd, _ = st.columns([1, 4])
        with col_btn_pd:
            if st.button("🔄 Làm mới", key="nv_refresh_pd"):
                lay_danh_sach_cong_viec.clear()
                st.rerun()

        with st.spinner("Đang tải..."):
            df_pd_all = lay_danh_sach_cong_viec()

        # Lọc: Người Phê Duyệt == ten_nhan_vien VÀ trạng thái "Đang Kiểm Tra"
        _col_pd = "Người Phê Duyệt"
        if _col_pd not in df_pd_all.columns:
            df_pd_all[_col_pd] = ""
        df_pd = df_pd_all[
            (df_pd_all[_col_pd].fillna("").str.strip().str.lower() == ten_nhan_vien.lower()) &
            (df_pd_all["Trạng Thái"].fillna("") == "Đang Kiểm Tra")
        ].copy()

        ds_tt_pd = lay_ten_cac_trang_thai() or _DS_TRANG_THAI_MAC_DINH

        if df_pd.empty:
            st.success("✅ Không có công việc nào cần bạn phê duyệt!")
        else:
            st.info(f"**{len(df_pd)}** công việc đang chờ bạn phê duyệt.")
            for _, h in df_pd.iterrows():
                task_id   = h.get("ID", "")
                ten_cv    = str(h.get("Tên Công Việc", "") or "")
                cong_ty   = str(h.get("Công Ty", "") or "")
                nhan_vien = str(h.get("Nhân Viên", "") or "")
                ngay_tao  = str(h.get("Ngày Tạo", ""))[:10]
                deadline  = str(h.get("Ngày Kết Thúc", "") or "")[:10]

                today_d = datetime.now().date()
                is_over = False
                try:
                    if deadline:
                        is_over = datetime.strptime(deadline, "%Y-%m-%d").date() < today_d
                except Exception:
                    pass

                border_color = "#ef4444" if is_over else "#3b82f6"
                card_html = f"""
                <div style='border:1.5px solid {border_color};border-radius:10px;
                     padding:12px 16px;margin-bottom:10px;background:#f8faff;'>
                  <div style='font-weight:700;font-size:1rem;color:#1e3a8a;margin-bottom:4px;'>
                    #{task_id} · {ten_cv}
                  </div>
                  <div style='font-size:0.85rem;color:#475569;'>
                    🏢 {cong_ty}&nbsp;&nbsp;|&nbsp;&nbsp;👤 {nhan_vien}&nbsp;&nbsp;|&nbsp;&nbsp;
                    📅 Tạo: {ngay_tao}&nbsp;&nbsp;|&nbsp;&nbsp;
                    ⏰ Hạn: <span style='color:{"#ef4444" if is_over else "#16a34a"};font-weight:600;'>{deadline or "—"}</span>
                  </div>
                </div>"""
                st.markdown(card_html, unsafe_allow_html=True)
                if st.button("📂 Xem & Phê Duyệt", key=f"pd_open_{task_id}", use_container_width=False):
                    _task_dialog(h.to_dict(), ds_tt_pd)

    # ========================================================
    # Tab 3: Tạo Công Việc Mới (nhân viên tự nhập)
    # ========================================================
    with tab_tao_task:
        st.subheader("➕ Tạo Công Việc Mới")
        # Hiển thị success message từ lần tạo task trước
        if st.session_state.get("_nv_task_success"):
            st.success(st.session_state.pop("_nv_task_success"))
            st.balloons()
        st.info(f"Công việc sẽ được giao cho: **{ten_nhan_vien}** *(tự động)*")

        ds_cong_ty_nv = lay_ten_cac_cong_ty()
        if not ds_cong_ty_nv:
            st.warning("⚠️ Chưa có công ty nào trong hệ thống. Vui lòng liên hệ Admin để thêm công ty trước.")
        else:
            # Prefix cho session state (mỗi nhân viên dùng key riêng)
            _nv_prefix = f"nv_{ten_nhan_vien.replace(' ', '_')}"
            _cl_key    = f"{_nv_prefix}_checklist"
            _cv_key    = f"{_nv_prefix}_cong_viec_con"

            ds_nv_nv       = lay_danh_sach_nhan_vien()
            ds_trang_thai_nv = lay_ten_cac_trang_thai() or ["Chờ Làm", "Đang Làm", "Hoàn Thành"]

            # ── Hàng đầu: Công Ty ──
            nv_cong_ty = st.selectbox("🏢 Công Ty *", options=ds_cong_ty_nv, key=f"{_nv_prefix}_ct")
            # ── Hàng tiếp theo: Người Phê Duyệt ──
            nv_phe_duyet = st.selectbox(
                "✅ Người Phê Duyệt",
                options=["-- Không chọn --"] + ds_nv_nv,
                key=f"{_nv_prefix}_pd"
            )

            col_tt2, col_nam2 = st.columns(2)
            with col_tt2:
                nv_trang_thai = st.selectbox("📋 Trạng thái", options=ds_trang_thai_nv, key=f"{_nv_prefix}_tt")
            with col_nam2:
                nv_nam = st.text_input("📅 Năm", value=str(datetime.now().year), key=f"{_nv_prefix}_nam")

            # Nhân viên giao = chính mình, chỉ cần chọn deadline
            st.markdown(f"**👤 Nhân viên thực hiện:** `{ten_nhan_vien}` *(tự động)*")
            nv_deadline = st.date_input("📅 Hạn Hoàn Thành", key=f"{_nv_prefix}_dl")

            col_lm_nv, col_tt_nv = st.columns(2)
            with col_lm_nv:
                ds_loai_may_nv = lay_ten_cac_loai_may()
                nv_loai_may = st.selectbox(
                    "🔧 Loại Máy",
                    options=["-- Không chọn --"] + ds_loai_may_nv,
                    key=f"{_nv_prefix}_loai_may",
                )
            with col_tt_nv:
                ds_tinh_trang_nv = lay_ten_cac_tinh_trang()
                nv_tinh_trang = st.selectbox(
                    "🛠️ Tình Trạng",
                    options=["-- Không chọn --"] + ds_tinh_trang_nv,
                    key=f"{_nv_prefix}_tinh_trang",
                )

            col_cs_nv, col_sc_nv = st.columns(2)
            with col_cs_nv:
                nv_cong_suat = st.text_input("⚡ Công Suất", placeholder="VD: 5.5kW", key=f"{_nv_prefix}_cong_suat")
            with col_sc_nv:
                nv_so_cuc = st.text_input("🔩 Số Cực", placeholder="VD: 4P", key=f"{_nv_prefix}_so_cuc")

            col_ms_nv, col_po_nv = st.columns(2)
            with col_ms_nv:
                nv_ma_so = st.text_input("🏷️ Mã Số", placeholder="VD: ABC-001", key=f"{_nv_prefix}_ma_so")
            with col_po_nv:
                nv_so_po_noi_bo = st.text_input("📄 Số PO Nội Bộ", placeholder="VD: PO-2024-001", key=f"{_nv_prefix}_so_po_noi_bo")

            col_kh_nv, col_bg_nv = st.columns(2)
            with col_kh_nv:
                nv_so_po_kh = st.text_input("📋 Số PO KH/HĐ", placeholder="VD: KH-2024-001", key=f"{_nv_prefix}_so_po_kh")
            with col_bg_nv:
                nv_so_bao_gia = st.text_input("💰 Số Báo Giá", placeholder="VD: BG-2024-001", key=f"{_nv_prefix}_so_bao_gia")

            nv_ten_task = st.text_input("📌 Tên Công Việc *", placeholder="Mô tả ngắn công việc cần làm", key=f"{_nv_prefix}_ten")
            nv_mo_ta    = st.text_area("📝 Mô Tả Chi Tiết", placeholder="Mô tả chi tiết về công việc...", key=f"{_nv_prefix}_mo_ta")

            st.divider()
            _fragment_checklist(_nv_prefix, show_done=False, default_items=_MAC_DINH_CHECKLIST)

            st.divider()
            _fragment_cong_viec_con(_nv_prefix, ds_nv_nv, show_done=False)

            st.divider()

            if st.button("✅ Tạo Task", use_container_width=True, type="primary", key=f"{_nv_prefix}_submit"):
                if not nv_ten_task.strip():
                    st.error("❌ Vui lòng nhập Tên Công Việc!")
                else:
                    phe_duyet_nv = nv_phe_duyet if nv_phe_duyet != "-- Không chọn --" else ""
                    with st.spinner("Đang lưu task mới..."):
                        them_cong_viec(
                            ten_task        = nv_ten_task.strip(),
                            mo_ta           = nv_mo_ta.strip(),
                            nguoi_duoc_giao = ten_nhan_vien,
                            deadline        = str(nv_deadline),
                            cong_ty         = nv_cong_ty,
                            cong_so         = "",
                            nam             = nv_nam.strip(),
                            trang_thai      = nv_trang_thai,
                            nguoi_phe_duyet = phe_duyet_nv,
                            checklist       = list(st.session_state[_cl_key]),
                            cong_viec_con   = list(st.session_state[_cv_key]),
                            cong_doan       = "",
                            loai_may        = nv_loai_may if nv_loai_may != "-- Không chọn --" else "",
                            tinh_trang      = nv_tinh_trang if nv_tinh_trang != "-- Không chọn --" else "",
                            cong_suat       = nv_cong_suat.strip(),
                            so_cuc          = nv_so_cuc.strip(),
                            ma_so           = nv_ma_so.strip(),
                            so_po_noi_bo    = nv_so_po_noi_bo.strip(),
                            so_po_kh        = nv_so_po_kh.strip(),
                            so_bao_gia      = nv_so_bao_gia.strip(),
                        )
                    st.session_state[_cl_key] = []
                    st.session_state[_cv_key] = []
                    # Xoá form fields
                    for _k in [f"{_nv_prefix}_ten", f"{_nv_prefix}_mo_ta"]:
                        st.session_state.pop(_k, None)
                    st.session_state["_nv_task_success"] = (
                        f"🎉 Đã tạo task **{nv_ten_task}** thành công! "
                        f"Chuyển sang tab **Công Việc Của Tôi** để xem."
                    )
                    lay_danh_sach_cong_viec.clear()
                    st.session_state.pop("_last_nv_load", None)
                    st.rerun()


# ============================================================
# GIAO DIỆN ĐĂNG NHẬP / ĐĂNG KÝ
# ============================================================
def giao_dien_dang_nhap():
    """
    Trang đăng nhập và đăng ký.
    Lưu thông tin người dùng vào session_state sau khi xác thực thành công.
    """
    # CSS riêng cho trang auth
    st.markdown("""
    <style>
    .auth-container {
        max-width: 460px;
        margin: 2rem auto;
        background: white;
        border-radius: 16px;
        padding: 2.2rem 2rem 2rem;
        box-shadow: 0 4px 24px rgba(0,0,0,0.09);
    }
    .auth-title {
        text-align: center;
        font-size: 1.6rem;
        font-weight: 700;
        color: #2d3a5e;
        margin-bottom: 0.3rem;
    }
    .auth-sub {
        text-align: center;
        color: #7b8aa0;
        font-size: 0.9rem;
        margin-bottom: 1.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="auth-title">📋 Quản Lý Công Việc</div>
        <div class="auth-sub">Đăng nhập để tiếp tục</div>
    """, unsafe_allow_html=True)

    tab_dn, tab_dk, tab_dmk = st.tabs(["🔑  Đăng Nhập", "📝  Đăng Ký", "🔒  Đổi Mật Khẩu"])

    # ─────────────────────────── ĐĂNG NHẬP ───────────────────────────
    with tab_dn:
        with st.form("form_dang_nhap", clear_on_submit=False):
            username_dn = st.text_input("Username", placeholder="Nhập username của bạn")
            matkhau_dn  = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu")
            btn_dn      = st.form_submit_button("Đăng Nhập", use_container_width=True,
                                                 type="primary")
        if btn_dn:
            if not username_dn or not matkhau_dn:
                st.error("Vui lòng nhập đầy đủ username và mật khẩu.")
            else:
                with st.spinner("Đang xác thực..."):
                    user = kiem_tra_dang_nhap(username_dn, matkhau_dn)
                if user:
                    st.session_state["dang_nhap"]     = True
                    st.session_state["user_id"]        = user["id"]
                    st.session_state["username"]       = user["username"]
                    st.session_state["ho_ten"]         = user["ho_ten"]
                    st.session_state["vai_tro"]        = user["vai_tro"]
                    st.session_state.pop("manual_logout", None)
                    token = str(uuid.uuid4())
                    _session_store()[token] = {
                        "user_id":  str(user["id"]),
                        "username": user["username"],
                        "ho_ten":   user["ho_ten"],
                        "vai_tro":  user["vai_tro"],
                    }
                    st.session_state["session_token"] = token
                    st.query_params["s"] = token
                    st.success(f"Chào mừng, **{user['ho_ten']}**! 🎉")
                    st.rerun()
                else:
                    st.error("❌ Username hoặc mật khẩu không đúng.")

    # ─────────────────────────── ĐĂNG KÝ ────────────────────────────
    with tab_dk:
        with st.form("form_dang_ky", clear_on_submit=True):
            st.markdown("##### Thông Tin Tài Khoản")
            col_u, col_p = st.columns(2)
            with col_u:
                username_dk = st.text_input("Username *", placeholder="Tối thiểu 3 ký tự")
            with col_p:
                matkhau_dk  = st.text_input("Mật khẩu *", type="password",
                                             placeholder="Tối thiểu 6 ký tự")
            xn_matkhau = st.text_input("Xác nhận mật khẩu *", type="password",
                                        placeholder="Nhập lại mật khẩu")
            st.markdown("##### Thông Tin Cá Nhân")
            ho_ten_dk   = st.text_input("Họ và Tên *", placeholder="Vd: Nguyễn Văn A")
            ngay_sinh_dk = st.date_input(
                "Ngày, Tháng, Năm Sinh *",
                value=None,
                min_value=datetime(1950, 1, 1).date(),
                max_value=datetime.today().date(),
                format="DD/MM/YYYY",
            )
            btn_dk = st.form_submit_button("Tạo Tài Khoản", use_container_width=True,
                                            type="primary")

        if btn_dk:
            if matkhau_dk != xn_matkhau:
                st.error("❌ Mật khẩu xác nhận không khớp.")
            else:
                ngay_sinh_str = str(ngay_sinh_dk) if ngay_sinh_dk else ""
                with st.spinner("Đang tạo tài khoản..."):
                    ok, msg = dang_ky_tai_khoan(
                        username=username_dk,
                        mat_khau=matkhau_dk,
                        ho_ten=ho_ten_dk,
                        ngay_sinh=ngay_sinh_str,
                        vai_tro="nhan_vien",
                    )
                if ok:
                    st.success(
                        f"✅ Tài khoản **{username_dk}** đã được tạo thành công! "
                        "Vui lòng chuyển sang tab **Đăng Nhập** để tiếp tục."
                    )
                else:
                    st.error(f"❌ {msg}")

    # ─────────────────────────── ĐỔI MẬT KHẨU ───────────────────────────
    with tab_dmk:
        with st.form("form_doi_mat_khau", clear_on_submit=True):
            st.markdown("##### Đổi Mật Khẩu")
            username_dmk   = st.text_input("Username", placeholder="Nhập username của bạn")
            mk_hien_tai    = st.text_input("Mật khẩu hiện tại", type="password",
                                           placeholder="Nhập mật khẩu hiện tại")
            mk_moi         = st.text_input("Mật khẩu mới", type="password",
                                           placeholder="Tối thiểu 6 ký tự")
            xn_mk_moi      = st.text_input("Xác nhận mật khẩu mới", type="password",
                                           placeholder="Nhập lại mật khẩu mới")
            btn_dmk = st.form_submit_button("Đổi Mật Khẩu", use_container_width=True,
                                            type="primary")

        if btn_dmk:
            if not username_dmk or not mk_hien_tai or not mk_moi or not xn_mk_moi:
                st.error("❌ Vui lòng điền đầy đủ thông tin.")
            elif mk_moi != xn_mk_moi:
                st.error("❌ Mật khẩu mới xác nhận không khớp.")
            elif mk_moi == mk_hien_tai:
                st.error("❌ Mật khẩu mới phải khác mật khẩu hiện tại.")
            else:
                with st.spinner("Đang cập nhật mật khẩu..."):
                    ok, msg = doi_mat_khau(username_dmk, mk_hien_tai, mk_moi)
                if ok:
                    st.success("✅ Đổi mật khẩu thành công! Vui lòng đăng nhập lại.")
                else:
                    st.error(f"❌ {msg}")


# ============================================================
# HÀM CHÍNH
# ============================================================
def inject_css():
    st.markdown("""
    <style>
    /* ===== IMPORT GOOGLE FONT ===== */
    @import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;500;600;700&display=swap');

    /* ===== TOÀN CỤC ===== */
    html, body, [class*="css"] {
        font-family: 'Be Vietnam Pro', sans-serif;
    }
    .stApp {
        background: linear-gradient(135deg, #f0f4ff 0%, #faf5ff 50%, #f0fdf4 100%);
    }

    /* ===== TIÊU ĐỀ CHÍNH ===== */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 0.65rem 1.4rem;
        border-radius: 14px;
        margin-bottom: 1.2rem;
        box-shadow: 0 3px 14px rgba(102,126,234,0.25);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
    }
    .main-header h1 {
        color: white !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
        letter-spacing: 0.2px;
        white-space: nowrap;
    }
    .main-header-right {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        flex-shrink: 0;
    }
    .main-header-user {
        color: rgba(255,255,255,0.9);
        font-size: 0.82rem;
        white-space: nowrap;
    }
    .main-header p {
        color: rgba(255,255,255,0.85) !important;
        margin: 0 !important;
        font-size: 0.8rem !important;
    }

    /* ===== ẨN SIDEBAR HOÀN TOÀN ===== */
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] {
        display: none !important;
    }

    /* Logout button bên trong header HTML */
    .header-logout-btn {
        background: rgba(255,255,255,0.15);
        color: white;
        border: 1.5px solid rgba(255,255,255,0.45);
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.82rem;
        padding: 0.32rem 0.85rem;
        cursor: pointer;
        white-space: nowrap;
        flex-shrink: 0;
        transition: all 0.2s ease;
        font-family: inherit;
    }
    .header-logout-btn:hover {
        background: rgba(239,68,68,0.35);
        border-color: rgba(239,68,68,0.7);
    }

    /* ===== NÚT ĐĂNG XUẤT (st.button) ===== */
    .logout-btn-wrap {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        height: 100%;
        padding-top: 0.35rem;
    }
    .logout-btn-wrap .stButton > button {
        background: rgba(239,68,68,0.12) !important;
        color: #ef4444 !important;
        border: 1.5px solid rgba(239,68,68,0.4) !important;
        border-radius: 8px !important;
        font-size: 1.1rem !important;
        padding: 0.3rem 0.7rem !important;
        width: 100% !important;
        transition: all 0.2s ease !important;
    }
    .logout-btn-wrap .stButton > button:hover {
        background: rgba(239,68,68,0.3) !important;
        border-color: rgba(239,68,68,0.75) !important;
    }

    /* ===== TOPBAR ACTIONS (bell + logout cột phải) ===== */
    .topbar-actions {
        display: flex;
        flex-direction: column;
        gap: 6px;
        align-items: stretch;
        justify-content: center;
        height: 100%;
        padding-top: 0.3rem;
    }
    .topbar-actions .stButton > button {
        border-radius: 8px !important;
        font-size: 1rem !important;
        padding: 0.3rem 0.4rem !important;
        width: 100% !important;
        white-space: nowrap !important;
        min-width: 0 !important;
        transition: all 0.2s ease !important;
    }
    /* Nút chuông */
    .topbar-actions .stButton:first-child > button {
        background: rgba(99,102,241,0.1) !important;
        color: #4f46e5 !important;
        border: 1.5px solid rgba(99,102,241,0.35) !important;
    }
    .topbar-actions .stButton:first-child > button:hover {
        background: rgba(99,102,241,0.22) !important;
    }
    /* Nút đăng xuất */
    .topbar-actions .stButton:last-child > button {
        background: rgba(239,68,68,0.1) !important;
        color: #ef4444 !important;
        border: 1.5px solid rgba(239,68,68,0.35) !important;
    }
    .topbar-actions .stButton:last-child > button:hover {
        background: rgba(239,68,68,0.25) !important;
    }

    /* Padding nội dung chính bình thường */
    .main .block-container {
        padding-bottom: 2rem !important;
    }

    /* Ẩn radio Streamlit gốc */
    div[data-testid="stRadio"] {
        display: none !important;
    }

    /* ===== TABS ===== */
    .stTabs [data-baseweb="tab-list"] {
        background: white;
        border-radius: 14px;
        padding: 6px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        color: #6b7280 !important;
        padding: 0.5rem 1.2rem !important;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea, #764ba2) !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(102,126,234,0.4) !important;
    }

    /* ===== METRIC CARDS ===== */
    [data-testid="stMetric"] {
        background: white;
        border-radius: 16px;
        padding: 1.2rem 1.5rem !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.07);
        border-left: 5px solid #667eea;
        transition: transform 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(102,126,234,0.2);
    }
    [data-testid="stMetricLabel"] {
        font-weight: 600 !important;
        color: #6b7280 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #1e1b4b !important;
    }

    /* ===== BUTTONS ===== */
    .stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 0.5rem 1.2rem !important;
        border: none !important;
        transition: all 0.25s ease !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(102,126,234,0.35) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(102,126,234,0.5) !important;
        opacity: 0.95 !important;
    }
    .stButton > button:active {
        transform: translateY(0px) !important;
    }

    /* ===== DOWNLOAD BUTTON ===== */
    .stDownloadButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        background: linear-gradient(135deg, #10b981, #059669) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(16,185,129,0.35) !important;
        transition: all 0.25s ease !important;
    }
    .stDownloadButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(16,185,129,0.5) !important;
    }

    /* ===== FORM & INPUT ===== */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {
        border-radius: 10px !important;
        border: 2px solid #e5e7eb !important;
        background: white !important;
        transition: border-color 0.2s ease;
        font-family: 'Be Vietnam Pro', sans-serif !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102,126,234,0.15) !important;
    }

    /* ===== FORM SUBMIT BUTTON ===== */
    [data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        padding: 0.65rem !important;
        box-shadow: 0 4px 15px rgba(102,126,234,0.4) !important;
        transition: all 0.25s ease !important;
    }
    [data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 22px rgba(102,126,234,0.55) !important;
    }

    /* ===== EXPANDER (TASK CARDS) ===== */
    [data-testid="stExpander"] {
        background: white !important;
        border-radius: 16px !important;
        border: 1.5px solid #e5e7eb !important;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06) !important;
        margin-bottom: 0.8rem !important;
        overflow: hidden !important;
        transition: box-shadow 0.2s ease !important;
    }
    [data-testid="stExpander"]:hover {
        box-shadow: 0 6px 20px rgba(102,126,234,0.15) !important;
        border-color: #667eea !important;
    }
    [data-testid="stExpander"] summary {
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 1rem 1.2rem !important;
        background: linear-gradient(90deg, #f8f7ff, #f3f4f6) !important;
        color: #1e1b4b !important;
    }

    /* ===== DATAFRAME ===== */
    [data-testid="stDataFrame"] {
        border-radius: 14px !important;
        overflow: hidden !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.07) !important;
        border: none !important;
    }

    /* ===== ALERT / INFO / SUCCESS / WARNING ===== */
    [data-testid="stAlert"] {
        border-radius: 12px !important;
        border: none !important;
        font-weight: 500 !important;
    }

    /* ===== SUBHEADER ===== */
    h2, h3 {
        color: #1e1b4b !important;
        font-weight: 700 !important;
    }

    /* ===== DIVIDER ===== */
    hr {
        border-color: #e5e7eb !important;
        margin: 1.2rem 0 !important;
    }

    /* ===== SPINNER ===== */
    .stSpinner > div {
        border-top-color: #667eea !important;
    }

    /* ===== FILE UPLOADER ===== */
    [data-testid="stFileUploader"] {
        border-radius: 12px !important;
        border: 2px dashed #667eea !important;
        background: #f8f7ff !important;
        padding: 0.5rem !important;
    }

    /* ===== MOBILE RESPONSIVE ===== */
    @media (max-width: 768px) {

        /* Main content full width, padding bottom cho bottom nav */
        .main .block-container {
            padding: 0.3rem 0.8rem 90px 0.8rem !important;
            max-width: 100% !important;
            margin-left: 0 !important;
            margin-top: 0 !important;
        }
        section[data-testid="stMain"] > div:first-child {
            padding-top: 0 !important;
        }

        /* --- Header nhỏ lại & stack dọc --- */
        .main-header {
            padding: 0.5rem 0.8rem !important;
            border-radius: 10px !important;
            flex-direction: column !important;
            align-items: flex-start !important;
            gap: 0.2rem !important;
        }
        .main-header h1 {
            font-size: 0.88rem !important;
            white-space: normal !important;
        }
        .main-header-user {
            font-size: 0.8rem !important;
            white-space: normal !important;
            word-break: break-word !important;
        }
        .main-header p {
            font-size: 0.75rem !important;
        }

        /* --- Form container full width --- */
        [data-testid="stForm"] {
            width: 100% !important;
            padding: 0 !important;
        }

        /* --- Metric cards full width --- */
        [data-testid="stMetric"] {
            padding: 0.9rem 1rem !important;
            margin-bottom: 0.5rem !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.6rem !important;
        }

        /* --- Tabs: nhỏ hơn, scroll ngang --- */
        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
            padding: 4px !important;
            gap: 2px !important;
            -webkit-overflow-scrolling: touch;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 0.78rem !important;
            padding: 0.4rem 0.7rem !important;
            white-space: nowrap !important;
            flex-shrink: 0 !important;
        }

        /* --- Buttons: touch target lớn hơn --- */
        .stButton > button {
            font-size: 1rem !important;
            padding: 0.75rem 1rem !important;
            width: 100% !important;
            min-height: 48px !important;
        }
        [data-testid="stFormSubmitButton"] > button {
            min-height: 52px !important;
            font-size: 1rem !important;
        }
        .stDownloadButton > button {
            min-height: 48px !important;
            font-size: 1rem !important;
            width: 100% !important;
        }

        /* --- Input fields: lớn hơn cho mobile --- */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            font-size: 1rem !important;
            padding: 0.6rem 0.8rem !important;
            min-height: 44px !important;
        }
        .stSelectbox > div > div {
            min-height: 44px !important;
            height: auto !important;
        }
        [data-testid="stSelectbox"] [data-baseweb="select"] > div {
            height: auto !important;
            min-height: 44px !important;
        }
        [data-testid="stSelectbox"] div[class*="singleValue"],
        [data-testid="stSelectbox"] div[class*="SingleValue"],
        [data-testid="stSelectbox"] div[class*="single-value"] {
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            font-size: 0.72rem !important;
            max-width: calc(100% - 28px) !important;
            direction: rtl !important;
            text-align: left !important;
        }

        /* --- Expander: readable trên mobile --- */
        [data-testid="stExpander"] summary {
            font-size: 0.85rem !important;
            padding: 0.8rem 1rem !important;
            line-height: 1.4 !important;
        }

        /* --- File uploader: dễ chạm hơn --- */
        [data-testid="stFileUploader"] {
            padding: 1rem !important;
        }
        [data-testid="stFileUploader"] label {
            font-size: 0.9rem !important;
        }

        /* --- Ảnh full width --- */
        [data-testid="stImage"] img {
            width: 100% !important;
            height: auto !important;
            border-radius: 10px !important;
        }

        /* --- Dataframe: scroll ngang --- */
        [data-testid="stDataFrame"] {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch;
        }

        /* --- Text size --- */
        p, li, label, .stMarkdown {
            font-size: 0.92rem !important;
        }
        h2 { font-size: 1.15rem !important; }
        h3 { font-size: 1rem !important; }

        /* --- Radio buttons: dễ chạm hơn --- */
        [data-testid="stRadio"] label {
            padding: 0.5rem 0 !important;
            font-size: 1rem !important;
        }
        [data-testid="stRadio"] > div {
            gap: 0.4rem !important;
        }

        /* --- Date input --- */
        input[type="date"] {
            min-height: 44px !important;
            font-size: 1rem !important;
        }

        /* --- Divider margin nhỏ hơn --- */
        hr {
            margin: 0.7rem 0 !important;
        }

        /* --- Alert --- */
        [data-testid="stAlert"] {
            font-size: 0.88rem !important;
            padding: 0.7rem 0.9rem !important;
        }

        /* --- Kanban cards: cuộn ngang thay vì xếp chồng --- */
        /* Chỉ áp dụng cho row có 3+ cột (kanban 4 cards), không ảnh hưởng filter 2 cột */
        [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(3)) {
            flex-wrap: nowrap !important;
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch !important;
            gap: 10px !important;
            padding-bottom: 10px !important;
            scroll-snap-type: x mandatory !important;
        }
        [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(3))
            > [data-testid="stColumn"] {
            min-width: 230px !important;
            flex: 0 0 230px !important;
            scroll-snap-align: start !important;
        }
        /* Ẩn scrollbar nhưng vẫn scroll được */
        [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(3))::-webkit-scrollbar {
            height: 4px !important;
        }
        [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(3))::-webkit-scrollbar-thumb {
            background: #c4b5fd !important;
            border-radius: 4px !important;
        }
    }

    /* ===== TABLET (768–1024px) ===== */
    @media (min-width: 769px) and (max-width: 1024px) {
        .main .block-container {
            padding: 1rem 1.5rem !important;
        }
        .main-header h1 {
            font-size: 1rem !important;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 0.85rem !important;
            padding: 0.45rem 0.9rem !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# DIALOG THÔNG BÁO
# ============================================================
@st.dialog("🔔 Thông Báo", width="large")
def dialog_thong_bao(ho_ten: str):
    """Dialog hiển thị danh sách thông báo của user."""
    # Dọn thông báo cũ hơn 2 tuần (chạy 1 lần mỗi session)
    if not st.session_state.get("_da_xoa_tb_cu", False):
        xoa_thong_bao_cu()
        st.session_state["_da_xoa_tb_cu"] = True
    c_title, c_mark = st.columns([5, 2])
    with c_title:
        so_chua = dem_chua_doc(ho_ten)
        if so_chua > 0:
            st.markdown(f"**{so_chua} thông báo chưa đọc**")
    with c_mark:
        if st.button("✅ Đánh dấu tất cả đã đọc",
                     key="dlg_mark_all_read",
                     use_container_width=True):
            danh_dau_da_doc_tat_ca(ho_ten)
            st.rerun()

    st.divider()

    df_tb = lay_thong_bao_nguoi_dung(ho_ten)
    if df_tb.empty:
        st.info("🔔 Bạn chưa có thông báo nào.")
        return

    # CSS: style nút "Xem Chi Tiết" nhỏ như text link
    st.markdown("""<style>
    [data-testid="stDialog"] .tb-xem-btn button {
        background: none !important;
        border: none !important;
        box-shadow: none !important;
        color: #6366f1 !important;
        font-size: 0.82rem !important;
        padding: 0 0 8px 58px !important;
        min-height: unset !important;
        height: auto !important;
        text-decoration: underline !important;
        cursor: pointer !important;
        justify-content: flex-start !important;
    }
    [data-testid="stDialog"] .tb-xem-btn button:hover {
        color: #4338ca !important;
        background: none !important;
    }
    [data-testid="stDialog"] .tb-xem-btn {
        margin-top: -4px !important;
        margin-bottom: 6px !important;
    }
    </style>""", unsafe_allow_html=True)

    for _, tb_row in df_tb.head(50).iterrows():
        _da_doc   = str(tb_row.get("Da_Doc", "0")) == "1"
        _noi_dung = str(tb_row.get("Noi_Dung", ""))
        _tgian    = str(tb_row.get("Thoi_Gian", ""))
        _loai     = str(tb_row.get("Loai", ""))
        _task_id  = str(tb_row.get("Task_ID", ""))

        # Icon + màu avatar theo loại
        _icon_map = {
            "task_moi":     ("📋", "#6366f1"),
            "trang_thai":   ("🔄", "#0ea5e9"),
            "cong_viec_con":("🔧", "#f59e0b"),
        }
        _icon, _col_av = _icon_map.get(_loai, ("🔔", "#6b7280"))

        # Thời gian tương đối
        try:
            _dt = datetime.strptime(_tgian[:19], "%Y-%m-%d %H:%M:%S")
            _delta = datetime.now() - _dt
            if _delta.seconds < 60:              _tg_text = "Vừa xong"
            elif _delta.seconds < 3600:          _tg_text = f"{_delta.seconds // 60} phút trước"
            elif _delta.days == 0:               _tg_text = f"{_delta.seconds // 3600} giờ trước"
            elif _delta.days == 1:               _tg_text = "Hôm qua"
            else:                                _tg_text = _dt.strftime("%d/%m/%Y")
        except Exception:
            _tg_text = _tgian

        _bg      = "#eff6ff" if not _da_doc else "#f9fafb"
        _border  = "2px solid #bfdbfe" if not _da_doc else "1px solid #e5e7eb"
        _dot_html = "<span style='display:inline-block;width:8px;height:8px;border-radius:50%;background:#3b82f6;margin-left:6px;vertical-align:middle'></span>" if not _da_doc else ""
        _has_task = _task_id and _task_id != '0'
        _mk = f"tbmk{tb_row.name}"
        _cursor = "cursor:pointer;" if _has_task else ""

        # Card HTML gốc
        st.markdown(f"""
        <div style="display:flex;gap:12px;align-items:flex-start;
                    background:{_bg};border:{_border};
                    border-radius:12px;padding:12px 14px;margin-bottom:0;">
            <div style="flex-shrink:0;width:42px;height:42px;border-radius:50%;
                        background:{_col_av};display:flex;align-items:center;
                        justify-content:center;font-size:1.25rem">{_icon}</div>
            <div style="flex:1;min-width:0">
                <div style="font-size:0.93rem;color:#1e293b;line-height:1.45">{_noi_dung}{_dot_html}</div>
                <div style="font-size:0.78rem;color:#94a3b8;margin-top:4px">{_tg_text}
                    {f"&nbsp;&middot;&nbsp;Task #{_task_id}" if _has_task else ""}
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

        # Nút "Xem Chi Tiết" nhỏ styled như text link
        if _has_task:
            st.markdown('<div class="tb-xem-btn">', unsafe_allow_html=True)
            if st.button("📂 Xem Chi Tiết", key=f"tb_card_{tb_row.name}"):
                st.session_state["_open_task_id_from_tb"] = _task_id
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)


def main():
    """Hàm chính: khởi động và điều hướng ứng dụng."""
    inject_css()

    # ── Khôi phục session từ query param nếu chưa đăng nhập ──────────────
    if not st.session_state.get("dang_nhap"):
        if st.session_state.get("manual_logout"):
            giao_dien_dang_nhap()
            return

        token = st.query_params.get("s")
        sess  = _session_store().get(token) if token else None

        if sess:
            uid            = sess["user_id"]
            ho_ten_sess    = sess["ho_ten"]
            vai_tro_sess   = sess["vai_tro"]
            try:
                df_users = lay_danh_sach_users()
                if not df_users.empty:
                    user_row = df_users[df_users["ID"].astype(str) == str(uid)]
                    if not user_row.empty:
                        ho_ten_sess  = user_row.iloc[0]["HoTen"]
                        vai_tro_sess = user_row.iloc[0]["VaiTro"]
            except Exception:
                pass
            st.session_state["dang_nhap"]      = True
            st.session_state["user_id"]        = uid
            st.session_state["username"]       = sess["username"]
            st.session_state["ho_ten"]         = ho_ten_sess
            st.session_state["vai_tro"]        = vai_tro_sess
            st.session_state["session_token"]  = token
            st.rerun()
        else:
            giao_dien_dang_nhap()
            return

    vai_tro   = st.session_state.get("vai_tro", "nhan_vien")
    ho_ten    = st.session_state.get("ho_ten", "")

    # ── Toast thông báo mới (tự động hiện ở góc màn hình) ─────────────────
    try:
        df_tb_all = lay_thong_bao_nguoi_dung(ho_ten)
        if not df_tb_all.empty:
            # Lấy ID lớn nhất hiện tại làm mốc
            _ids_hien_tai = pd.to_numeric(df_tb_all["ID"], errors="coerce").dropna()
            _max_id_hien_tai = int(_ids_hien_tai.max()) if not _ids_hien_tai.empty else 0

            _key_seen = f"_tb_seen_max_id_{ho_ten}"
            _last_seen_id = st.session_state.get(_key_seen, None)

            if _last_seen_id is None:
                # Lần đầu đăng nhập → ghi nhận mốc, không toast
                st.session_state[_key_seen] = _max_id_hien_tai
            elif _max_id_hien_tai > _last_seen_id:
                # Có thông báo mới → toast từng cái (tối đa 3)
                _moi = df_tb_all[
                    pd.to_numeric(df_tb_all["ID"], errors="coerce") > _last_seen_id
                ].head(3)
                _loai_icon = {
                    "task_moi":      "📋",
                    "trang_thai":    "🔄",
                    "cong_viec_con": "🔧",
                }
                for _, _r in _moi.iterrows():
                    _icon = _loai_icon.get(str(_r.get("Loai", "")), "🔔")
                    _nd   = str(_r.get("Noi_Dung", ""))
                    # Rút gọn nội dung ≤ 80 ký tự
                    _nd_short = (_nd[:77] + "…") if len(_nd) > 80 else _nd
                    st.toast(f"{_icon} {_nd_short}", icon="🔔")
                st.session_state[_key_seen] = _max_id_hien_tai
    except Exception:
        pass

    # ── Header + nút đăng xuất ──────────────────────────────────────────────
    role_badge   = "🛡️ Admin" if vai_tro == "admin" else "👤"
    so_chua_doc  = dem_chua_doc(ho_ten)
    _bell_label  = f"🔔 {so_chua_doc}" if so_chua_doc > 0 else "🔔"

    col_hdr, col_actions = st.columns([5, 1])
    with col_hdr:
        st.markdown(f"""
            <div class="main-header">
                <h1>📋 Quản Lý Công Việc</h1>
                <div class="main-header-user">{role_badge} &nbsp;<b>{ho_ten}</b></div>
            </div>
        """, unsafe_allow_html=True)
    with col_actions:
        st.markdown('<div class="topbar-actions">', unsafe_allow_html=True)
        if st.button(_bell_label, key="btn_bell", use_container_width=True,
                     help="Thông báo của bạn"):
            dialog_thong_bao(ho_ten)
        if st.button("🚪 Đăng Xuất", key="topbar_logout", use_container_width=True,
                     help="Đăng xuất"):
            token = st.session_state.get("session_token")
            if token:
                _session_store().pop(token, None)
            for k in ["dang_nhap", "user_id", "username", "ho_ten", "vai_tro", "session_token"]:
                st.session_state.pop(k, None)
            st.query_params.clear()
            st.session_state["manual_logout"] = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Mở task dialog từ thông báo (sau rerun) ───────────────────────────
    if st.session_state.get("_open_task_id_from_tb"):
        _tid_tb = st.session_state.pop("_open_task_id_from_tb")
        st.session_state.pop("_open_task_id_from_tb_user", None)
        try:
            _df_all  = lay_danh_sach_cong_viec()
            _ds_tt   = lay_ten_cac_trang_thai()
            _matched = _df_all[_df_all["ID"].astype(str) == str(_tid_tb)]
            if not _matched.empty:
                _task_dialog(_matched.iloc[0].to_dict(), _ds_tt)
        except Exception:
            st.warning(f"Không tìm thấy Task #{_tid_tb}")

    # ── Điều hướng giao diện ───────────────────────────────────────────────
    if vai_tro == "admin":
        giao_dien_admin()
    else:
        giao_dien_nhan_vien()


# ============================================================
# ĐIỂM CHẠY CHƯƠNG TRÌNH
# ============================================================
if __name__ == "__main__":
    main()
