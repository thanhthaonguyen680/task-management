# ============================================================
# app.py - Ứng dụng Quản Lý Công Việc
# Sử dụng: Streamlit + Google Sheets (gspread) + Cloudinary + FPDF
# ============================================================

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import cloudinary
import cloudinary.uploader
from fpdf import FPDF
import pandas as pd
from datetime import datetime
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
    ];
    var CSS_RULES = HIDE.map(function(s){ return s+'{display:none!important;visibility:hidden!important}'; }).join('');

    function injectCSS(doc) {
        try {
            var id = '__st_hide_v2';
            var existing = doc.getElementById(id);
            if (existing) return;
            var s = doc.createElement('style');
            s.id = id;
            s.textContent = CSS_RULES;
            (doc.head || doc.documentElement).appendChild(s);
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
    });

    // MutationObserver để bắt các element được thêm sau
    function observeDoc(doc) {
        try {
            var obs = new MutationObserver(function(mutations) {
                injectCSS(doc);
                hideElements(doc);
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
            });
        }, delay);
    });
    </script>
    """,
    height=1,
)


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


# ============================================================
# CẤU HÌNH CLOUDINARY (lưu trữ ảnh nghiệm thu)
# ============================================================
def cau_hinh_cloudinary():
    """Khởi tạo cấu hình kết nối Cloudinary từ Streamlit Secrets."""
    cloudinary.config(
        cloud_name=st.secrets["cloudinary"]["cloud_name"],
        api_key=st.secrets["cloudinary"]["api_key"],
        api_secret=st.secrets["cloudinary"]["api_secret"]
    )


def tai_anh_len_cloudinary(file_anh) -> str:
    """
    Tải ảnh lên Cloudinary và trả về URL công khai (secure_url).
    
    Args:
        file_anh: File object từ st.file_uploader
    
    Returns:
        str: URL ảnh trên Cloudinary
    """
    cau_hinh_cloudinary()
    ket_qua = cloudinary.uploader.upload(
        file_anh,
        folder="quan_ly_cong_viec",   # Thư mục lưu trên Cloudinary
        resource_type="image"
    )
    return ket_qua["secure_url"]


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
            sheet = bang_tinh.add_worksheet(title="Companies", rows=200, cols=4)
            sheet.append_row(["ID", "Tên Công Ty", "Ngày Tạo"])
        return sheet
    except (ConnectionError, OSError, Exception) as e:
        raise ConnectionError(_xoa_cache_va_thong_bao(e)) from e


@st.cache_data(ttl=60)
def lay_danh_sach_cong_ty() -> pd.DataFrame:
    """Lấy toàn bộ danh sách công ty từ sheet 'Companies'."""
    _COT = ["ID", "Tên Công Ty", "Ngày Tạo"]
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
    headers = [v.strip() for v in allvals[0][:len(_COT)]]
    rows = [r[:len(_COT)] for r in allvals[1:] if any(r[:len(_COT)])]
    df = pd.DataFrame(rows, columns=headers)
    df.rename(columns={"Cong_Ty": "Tên Công Ty", "Created_Date": "Ngày Tạo"}, inplace=True)
    return df


def them_cong_ty(ten_cong_ty: str) -> int:
    """
    Thêm công ty mới vào sheet 'Companies'.

    Args:
        ten_cong_ty: Tên công ty khách hàng

    Returns:
        int: ID vừa tạo
    """
    sheet = lay_sheet_cong_ty()
    id_moi = len(sheet.col_values(1))  # cột A: header + các hàng dữ liệu
    ngay_tao = datetime.now().strftime("%Y-%m-%d")
    sheet.append_row([id_moi, ten_cong_ty, ngay_tao])
    lay_danh_sach_cong_ty.clear()
    lay_ten_cac_cong_ty.clear()
    return id_moi


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


# Danh sách trạng thái mặc định (theo quy trình thực tế)
_DS_TRANG_THAI_MAC_DINH = [
    "Đang Kiểm Tra",
    "Đã Phê Duyệt",
    "Đã Báo Giá",
    "Có Đơn",
    "Chờ Giao",
    "Đã Hoàn Thành - Giao Máy",
    "Đã Xuất Hóa Đơn",
    "Bảo Hành - Trả Lại",
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

@st.cache_data(ttl=60)
def lay_ten_cac_loai_may() -> list:
    df = lay_danh_sach_loai_may()
    return df["Tên Loại Máy"].dropna().tolist() if not df.empty else []


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
    # 14 cột A→N (chỉ lấy đúng số cột này — tránh lỗi duplicate header từ cột trống)
    _HEADERS = [
        "ID", "Công Ty", "Công Số", "Năm", "Tên Công Việc", "Mô Tả",
        "Nhân Viên", "Trạng Thái", "Ngày Tạo", "Hạn Hoàn Thành",
        "Link Ảnh", "Người Phê Duyệt", "Checklist", "Công Việc Con"
    ]
    _N = len(_HEADERS)
    _COT_TRONG = _HEADERS[:11]  # các cột hiển thị chính
    try:
        sheet   = lay_sheet()
        allvals = sheet.get_all_values()
    except (ConnectionError, OSError, Exception):
        return pd.DataFrame(columns=_COT_TRONG)
    if len(allvals) <= 1:
        return pd.DataFrame(columns=_COT_TRONG)
    # Dùng tên cột cố định (không đọc từ row 1) — tránh lỗi duplicate
    rows = [r[:_N] for r in allvals[1:] if any(r[:_N])]
    df = pd.DataFrame(rows, columns=_HEADERS[:len(rows[0])] if rows else _HEADERS)
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
                   checklist: list = None, cong_viec_con: list = None) -> int:
    """
    Thêm một công việc mới vào cuối sheet.

    Cấu trúc hàng:
    A:ID | B:Cong_Ty | C:Cong_So | D:Nam | E:Task_Name | F:Description
    G:Assigned_To | H:Status | I:Created_Date | J:Deadline | K:Image_URL
    L:Nguoi_Phe_Duyet | M:Checklist (JSON) | N:Cong_Viec_Con (JSON)
    """
    sheet = lay_sheet()
    # Đếm số hàng qua cột A (tránh get_all_records duplicate header)
    id_moi   = len(sheet.col_values(1))  # header row + các hàng = ID tiếp theo
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
    ]

    sheet.append_row(hang_moi)
    lay_danh_sach_cong_viec.clear()
    return id_moi


def cap_nhat_trang_thai(task_id: int, trang_thai_moi: str):
    """
    Cập nhật trạng thái (Status) của công việc theo ID.
    
    Args:
        task_id: ID công việc cần cập nhật
        trang_thai_moi: Trạng thái mới ('Chờ Làm', 'Đang Làm', hoặc 'Hoàn Thành')
    """
    sheet = lay_sheet()
    # Tìm ô chứa ID cần tìm (tìm ở cột A)
    o_tim = sheet.find(str(task_id), in_column=1)
    if o_tim:
        # Cột Status là cột H (8): ID|Cong_Ty|Cong_So|Nam|Task_Name|Description|Assigned_To|Status
        sheet.update_cell(o_tim.row, 8, trang_thai_moi)
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
    ds_anh       = doc_danh_sach_anh(str(thong_tin_task.get("Link Ảnh", "")))

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

    W_STT  = 15
    W_DATE = 35
    W_PASS = 38
    W_HM   = W - W_STT - W_DATE - W_PASS

    # Header bảng – nền xanh
    pdf.set_fill_color(*BLUE_CELL)
    pdf.set_font("DejaVu", "B", 8.5)
    HDR_H = 9
    y_hdr = pdf.get_y()
    # Vẽ 4 ô header bằng rect để kiểm soát chính xác
    pdf.rect(M_LEFT,                    y_hdr, W_STT,  HDR_H)
    pdf.rect(M_LEFT + W_STT,            y_hdr, W_HM,   HDR_H)
    pdf.rect(M_LEFT + W_STT + W_HM,     y_hdr, W_DATE, HDR_H)
    pdf.rect(M_LEFT + W_STT + W_HM + W_DATE, y_hdr, W_PASS, HDR_H)
    # Fill màu
    pdf.set_fill_color(*BLUE_CELL)
    pdf.set_xy(M_LEFT, y_hdr)
    pdf.cell(W_STT,  HDR_H, "",                                border=0, fill=True, new_x="END",    new_y="LAST")
    pdf.cell(W_HM,   HDR_H, "",                                border=0, fill=True, new_x="END",    new_y="LAST")
    pdf.cell(W_DATE, HDR_H, "",                                border=0, fill=True, new_x="END",    new_y="LAST")
    pdf.cell(W_PASS, HDR_H, "",                                border=0, fill=True, new_x="LMARGIN", new_y="NEXT")
    # Text header
    pdf.set_xy(M_LEFT, y_hdr + 0.5)
    pdf.set_font("DejaVu", "B", 8.5)
    pdf.cell(W_STT, HDR_H - 1, "STT", align="C", new_x="END", new_y="LAST")
    pdf.cell(W_HM,  HDR_H - 1, "Repair catalog / Hạng mục sửa chữa", align="C", new_x="END", new_y="LAST")
    pdf.cell(W_DATE,HDR_H - 1, "Date / Ngày", align="C", new_x="END", new_y="LAST")
    # "Passed / Thông qua" — 2 dòng nhỏ
    x_pass = M_LEFT + W_STT + W_HM + W_DATE
    pdf.set_xy(x_pass, y_hdr + 0.5)
    pdf.set_font("DejaVu", "B", 8)
    pdf.cell(W_PASS, 4.5, "Passed /", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(x_pass, y_hdr + 4.5)
    pdf.cell(W_PASS, 4.5, "Thông qua", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(M_LEFT, y_hdr + HDR_H)

    # 12 dòng hạng mục
    pdf.set_fill_color(*WHITE)
    pdf.set_font("DejaVu", "", 8.5)
    ROW_H2 = 7
    for i in range(1, 13):
        noi_dung = hang_muc[i - 1] if (i - 1) < len(hang_muc) else ""
        y_r = pdf.get_y()
        # Vẽ khung bằng rect
        pdf.rect(M_LEFT,                         y_r, W_STT,  ROW_H2)
        pdf.rect(M_LEFT + W_STT,                 y_r, W_HM,   ROW_H2)
        pdf.rect(M_LEFT + W_STT + W_HM,          y_r, W_DATE, ROW_H2)
        pdf.rect(M_LEFT + W_STT + W_HM + W_DATE, y_r, W_PASS, ROW_H2)
        # Text
        pdf.set_xy(M_LEFT, y_r + 0.5)
        pdf.cell(W_STT,  ROW_H2 - 1, f"{i} -",  align="C", new_x="END",    new_y="LAST")
        pdf.cell(W_HM,   ROW_H2 - 1, noi_dung,  align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(M_LEFT, y_r + ROW_H2)

    # ── Footer box trang 1 (absolute, sát đáy trang) ─────────
    y_footer = 267
    BOX_H1 = 8
    BOX_H2 = 8
    pdf.set_xy(M_LEFT, y_footer)
    W1 = 16   # logo placeholder
    W2 = int((W - W1) / 3)
    W3 = W - W1 - W2 - W2

    # Hàng 1: logo + Quotation | Engine number | Order number
    pdf.set_font("DejaVu", "B", 8)
    pdf.cell(W1, BOX_H1, "NT", border=1, align="C", new_x="END", new_y="LAST")
    pdf.set_font("DejaVu", "", 7.5)
    pdf.cell(W2, BOX_H1, "Quotation / Báo giá :", border=1, new_x="END", new_y="LAST")
    pdf.cell(W2, BOX_H1, "Engine number / Số máy :", border=1, new_x="END", new_y="LAST")
    pdf.cell(W3, BOX_H1, f"Order number / Số đơn hàng : {cong_so}", border=1, new_x="LMARGIN", new_y="NEXT")

    # Hàng 2: logo span + Management doc | Edition date | Page
    y2 = y_footer + BOX_H1
    pdf.rect(M_LEFT,              y2, W1, BOX_H2)
    pdf.rect(M_LEFT + W1,         y2, W2, BOX_H2)
    pdf.rect(M_LEFT + W1 + W2,    y2, W2, BOX_H2)
    pdf.rect(M_LEFT + W1 + W2*2,  y2, W3, BOX_H2)
    pdf.set_font("DejaVu", "", 7)
    # Management doc — 2 dòng
    pdf.set_xy(M_LEFT + W1,      y2 + 0.5);  pdf.cell(W2, 4, "Management document / Tài liệu quản lý :", align="C")
    pdf.set_xy(M_LEFT + W1,      y2 + 4);    pdf.cell(W2, 4, "QT-NT-029-1A", align="C")
    # Edition date
    pdf.set_xy(M_LEFT + W1 + W2, y2 + 1.5);  pdf.cell(W2, 5, "Edition date / Ngày xuất bản :", align="C")
    # Page — 2 dòng
    pdf.set_xy(M_LEFT + W1 + W2*2, y2 + 0.5); pdf.cell(W3, 4, "Page / Trang:", align="C")
    pdf.set_xy(M_LEFT + W1 + W2*2, y2 + 4);   pdf.cell(W3, 4, "1/11", align="C")

    # ========================================================= #
    #  TRANG 2: bảng điện trở + ảnh trong ô                    #
    # ========================================================= #
    pdf.add_page()

    # ── Header doc trang 2 ────────────────────────────────────
    pdf.set_xy(M_LEFT, M_TOP)
    pdf.set_font("DejaVu", "", 7.5)
    pdf.cell(W1, BOX_H1, "NT", border=1, align="C",
             new_x="END", new_y="LAST")
    pdf.cell(W2, BOX_H1, "Quotation / Báo giá :", border=1, new_x="END", new_y="LAST")
    pdf.cell(W2, BOX_H1, "Engine number / Số máy :", border=1, new_x="END", new_y="LAST")
    pdf.cell(W3, BOX_H1, f"Order number / Số đơn hàng : {cong_so}", border=1, new_x="LMARGIN", new_y="NEXT")

    y2p = M_TOP + BOX_H1
    pdf.rect(M_LEFT,              y2p, W1, BOX_H2)
    pdf.rect(M_LEFT + W1,         y2p, W2, BOX_H2)
    pdf.rect(M_LEFT + W1 + W2,    y2p, W2, BOX_H2)
    pdf.rect(M_LEFT + W1 + W2*2,  y2p, W3, BOX_H2)
    pdf.set_font("DejaVu", "", 7)
    pdf.set_xy(M_LEFT + W1,       y2p + 0.5); pdf.cell(W2, 4, "Management document / Tài liệu quản lý :", align="C")
    pdf.set_xy(M_LEFT + W1,       y2p + 4);   pdf.cell(W2, 4, "QT-NT-029-1A", align="C")
    pdf.set_xy(M_LEFT + W1 + W2,  y2p + 1.5); pdf.cell(W2, 5, "Edition date / Ngày xuất bản :", align="C")
    pdf.set_xy(M_LEFT + W1+W2*2,  y2p + 0.5); pdf.cell(W3, 4, "Page / Trang:", align="C")
    pdf.set_xy(M_LEFT + W1+W2*2,  y2p + 4);   pdf.cell(W3, 4, "1/11", align="C")
    pdf.set_xy(M_LEFT, M_TOP + BOX_H1 + BOX_H2 + 4)

    # ── Hàm vẽ 1 bảng điện trở có ô ảnh ─────────────────────
    COL_W  = W / 3          # chiều rộng mỗi cột (3 cột đều nhau)
    IMG_H  = 55             # chiều cao ô ảnh (mm)
    HDR_H  = 8              # chiều cao dòng tiêu đề
    LBL_H  = 8              # chiều cao dòng nhãn pha

    def _bang_co_anh(ten_en: str, ten_vi: str, nhan_pha: list, danh_sach_anh_bang: list):
        """
        Vẽ bảng 3 cột có:
          - Dòng 1: tiêu đề full width (nền xanh đậm, chữ trắng)
          - Dòng 2: 3 nhãn pha (nền xanh nhạt)
          - Dòng 3: 3 ô ảnh (hoặc trống nếu không có ảnh)
        """
        y_start = pdf.get_y()

        # -- Dòng tiêu đề --
        pdf.set_fill_color(*BLUE_HDR)
        pdf.set_text_color(*WHITE)
        pdf.set_font("DejaVu", "B", 9.5)
        pdf.cell(W, HDR_H, f"{ten_en} / {ten_vi}",
                 border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*BLACK)

        # -- Dòng nhãn pha --
        pdf.set_fill_color(*BLUE_CELL)
        pdf.set_font("DejaVu", "B", 9)
        for idx_p, nhan in enumerate(nhan_pha):
            nx = "LMARGIN" if idx_p == 2 else "END"
            ny = "NEXT"    if idx_p == 2 else "LAST"
            pdf.cell(COL_W, LBL_H, nhan, border=1, align="C",
                     fill=True, new_x=nx, new_y=ny)

        # -- Dòng ô ảnh --
        y_img = pdf.get_y()
        for idx_a in range(3):
            x_img = M_LEFT + idx_a * COL_W
            # Vẽ khung ô
            pdf.rect(x_img, y_img, COL_W, IMG_H)
            # Chèn ảnh nếu có
            if idx_a < len(danh_sach_anh_bang) and danh_sach_anh_bang[idx_a]:
                duong_dan = danh_sach_anh_bang[idx_a]
                try:
                    # Fit ảnh vào ô, giữ tỉ lệ, padding 1mm
                    pad = 1
                    pdf.image(duong_dan, x=x_img + pad, y=y_img + pad,
                              w=COL_W - 2*pad, h=IMG_H - 2*pad)
                except Exception:
                    pass

        pdf.set_xy(M_LEFT, y_img + IMG_H)
        pdf.ln(3)

    # ── Tải trước tất cả ảnh về temp files ───────────────────
    temp_files = []
    for url in ds_anh:
        temp_files.append(_tai_anh_tam(url))

    # Padding danh sách để đủ 9 slot (3 bảng × 3 cột)
    while len(temp_files) < 9:
        temp_files.append(None)

    # ── Vẽ 3 bảng ────────────────────────────────────────────
    _bang_co_anh(
        "Stator 1 coil resistance", "Điện trở cuộn dây Stator 1",
        ["U1 – V1", "U1 – W1", "V1 –  W1"],
        temp_files[0:3]
    )
    _bang_co_anh(
        "Stator 2 coil resistance", "Điện trở cuộn dây Stator 2",
        ["U2 – V2", "U2 – W2", "V2 –  W2"],
        temp_files[3:6]
    )
    _bang_co_anh(
        "Rotor coil resistance", "Điện trở cuộn dây Rotor",
        ["K – L", "K – M", "L –  M"],
        temp_files[6:9]
    )

    # ── Dọn temp files ────────────────────────────────────────
    for p in temp_files:
        if p and os.path.exists(p):
            try:
                os.unlink(p)
            except Exception:
                pass

    # ── Xuất PDF ─────────────────────────────────────────────
    return bytes(pdf.output())


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
        padding: 10px 14px;
        margin-bottom: 8px;
        display: flex;
        align-items: flex-start;
        gap: 12px;
    }
    .cv-con-card.done {
        background: #f0fdf4;
        border-color: #bbf7d0;
        opacity: 0.75;
    }
    .cv-con-title {
        font-weight: 700;
        font-size: 0.95rem;
        color: #1e1b4b;
        margin-bottom: 3px;
    }
    .cv-con-title.done-text {
        text-decoration: line-through;
        color: #6b7280;
    }
    .cv-con-meta {
        font-size: 0.8rem;
        color: #6b7280;
        display: flex;
        gap: 14px;
        flex-wrap: wrap;
    }
    .cv-con-meta span { display:inline-flex; align-items:center; gap:3px; }
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

    # ── Hàng trên: thông tin chính + chọn trạng thái ─────────
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown(
            f"🏢 **Công ty:** `{hang.get('Công Ty', '')}` &nbsp;&nbsp; "
            f"📄 **Công số:** `{hang.get('Công Số', '')}` &nbsp;&nbsp; "
            f"📅 **Năm:** `{hang.get('Năm', '')}`"
        )
        if hang.get("Người Phê Duyệt"):
            st.markdown(f"✅ **Người phê duyệt:** `{hang.get('Người Phê Duyệt', '')}`")
        st.markdown(f"📅 **Hạn hoàn thành:** `{hang.get('Hạn Hoàn Thành', '')}`")
        st.markdown(f"🕐 **Ngày tạo:** `{hang.get('Ngày Tạo', '')}`")
        if hang.get("Mô Tả"):
            with st.expander("📝 Xem mô tả chi tiết"):
                st.write(hang.get("Mô Tả", ""))

    with col_right:
        # Badge màu trạng thái hiện tại
        st.markdown(
            f'<div style="margin-bottom:8px">'
            f'<span class="badge-trang-thai" style="color:{tt_color};background:{tt_bg};border-color:{tt_color}40;">'
            f'{tt_hien_thi}</span></div>',
            unsafe_allow_html=True,
        )
        # Selectbox đổi trạng thái
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

    st.divider()

    # ── Checklist ─────────────────────────────────────────────
    raw_cl = hang.get("Checklist", "") or "[]"
    try:
        _cl_parsed = json.loads(raw_cl) if raw_cl else []
    except Exception:
        _cl_parsed = []

    # Dùng session_state làm nguồn thực tế (để fragment rerun không mất item mới thêm)
    _cl_key = f"cl_editable_{task_id}"
    if _cl_key not in st.session_state:
        st.session_state[_cl_key] = _cl_parsed
    checklist = st.session_state[_cl_key]

    so_xong = sum(1 for item in checklist if isinstance(item, dict) and item.get("done"))
    pct     = int(so_xong / len(checklist) * 100) if checklist else 0
    st.markdown(
        f"""**☑️ Checklist** &nbsp;<span style='color:#6b7280;font-size:0.82rem;'>{so_xong}/{len(checklist)} mục</span>
        <div style='background:#e5e7eb;border-radius:99px;height:6px;margin:4px 0 10px 0;'>
        <div style='background:#7c3aed;width:{pct}%;height:6px;border-radius:99px;transition:width .3s'></div>
        </div>""",
        unsafe_allow_html=True,
    )

    # Inline add
    _cl_add_cnt = st.session_state.get(f"cl_add_cnt_{task_id}", 0)
    col_cl_inp, col_cl_btn = st.columns([5, 1])
    with col_cl_inp:
        cl_moi = st.text_input(
            "Thêm mục", placeholder="Nhập mục checklist rồi bấm ➕...",
            key=f"cl_inp_{task_id}_{_cl_add_cnt}", label_visibility="collapsed",
        )
    with col_cl_btn:
        if st.button("➕", key=f"cl_add_{task_id}", use_container_width=True):
            if cl_moi.strip():
                checklist.append({"text": cl_moi.strip(), "done": False})
                st.session_state[_cl_key] = checklist
                st.session_state[f"cl_add_cnt_{task_id}"] = _cl_add_cnt + 1
                cap_nhat_checklist(task_id, checklist)

    da_thay_doi = False
    _cl_xoa = None
    for i, item in enumerate(checklist):
        if isinstance(item, str):
            item = {"text": item, "done": False}
            checklist[i] = item
        hien_tai = bool(item.get("done", False))
        col_ck, col_tx, col_del = st.columns([0.5, 8, 0.7])
        with col_ck:
            moi = st.checkbox(
                "", value=hien_tai,
                key=f"cl_{task_id}_{i}",
                label_visibility="collapsed",
            )
        with col_tx:
            label_style = "text-decoration:line-through;color:#9ca3af;" if hien_tai else ""
            st.markdown(
                f'<p style="margin:6px 0 0 0;{label_style}">{item.get("text", f"Mục {i+1}")}</p>',
                unsafe_allow_html=True,
            )
        with col_del:
            if st.button("🗑️", key=f"cl_del_{task_id}_{i}", use_container_width=True, help="Xóa mục này"):
                _cl_xoa = i
        if moi != hien_tai:
            checklist[i]["done"] = moi
            da_thay_doi = True
    if _cl_xoa is not None:
        checklist.pop(_cl_xoa)
        st.session_state[_cl_key] = checklist
        cap_nhat_checklist(task_id, checklist)
    elif da_thay_doi:
        st.session_state[_cl_key] = checklist
        cap_nhat_checklist(task_id, checklist)
    st.divider()

    # ── Công việc con ─────────────────────────────────────────
    raw_cv = hang.get("Công Việc Con", "") or "[]"
    try:
        _cv_parsed = json.loads(raw_cv) if raw_cv else []
    except Exception:
        _cv_parsed = []

    _cv_key = f"cv_editable_{task_id}"
    if _cv_key not in st.session_state:
        st.session_state[_cv_key] = _cv_parsed
    ds_cv_con = st.session_state[_cv_key]

    st.markdown("**📋 Công Việc Con**")

    # Inline add row
    _ds_nv_cv = lay_danh_sach_nhan_vien()
    _cv_add_cnt = st.session_state.get(f"cv_add_cnt_{task_id}", 0)
    col_cv1, col_cv2, col_cv3, col_cv4 = st.columns([3, 2, 2, 1])
    with col_cv1:
        cv_ten_moi = st.text_input(
            "Tên việc", placeholder="Ví dụ: Tháo máy",
            key=f"cv_inp_ten_{task_id}_{_cv_add_cnt}", label_visibility="collapsed",
        )
    with col_cv2:
        cv_nv_moi = st.selectbox(
            "Nhân viên", options=["-- Chọn --"] + _ds_nv_cv,
            key=f"cv_inp_nv_{task_id}_{_cv_add_cnt}", label_visibility="collapsed",
        )
    with col_cv3:
        cv_dl_moi = st.date_input(
            "Deadline", key=f"cv_inp_dl_{task_id}_{_cv_add_cnt}", label_visibility="collapsed",
        )
    with col_cv4:
        if st.button("➕", key=f"cv_add_{task_id}", use_container_width=True):
            if cv_ten_moi.strip():
                nv_luu = cv_nv_moi if cv_nv_moi != "-- Chọn --" else ""
                ds_cv_con.append({
                    "ten": cv_ten_moi.strip(),
                    "nhan_vien": nv_luu,
                    "deadline": str(cv_dl_moi),
                    "done": False,
                })
                st.session_state[_cv_key] = ds_cv_con
                st.session_state[f"cv_add_cnt_{task_id}"] = _cv_add_cnt + 1
                _sh = lay_sheet()
                _o  = _sh.find(str(task_id), in_column=1)
                if _o:
                    _sh.update_cell(_o.row, 14, json.dumps(ds_cv_con, ensure_ascii=False))
                    lay_danh_sach_cong_viec.clear()

    cv_changed = False
    _cv_xoa = None
    for j, cv in enumerate(ds_cv_con):
        if not isinstance(cv, dict):
            continue
        ten_cv  = cv.get("ten",       cv.get("Tên",       f"Việc {j+1}"))
        nv_cv   = cv.get("nhan_vien", cv.get("Nhân Viên", ""))
        dl_cv   = cv.get("deadline",  cv.get("Deadline",  ""))
        done_cv = bool(cv.get("done", False))

        card_cls  = "cv-con-card done" if done_cv else "cv-con-card"
        title_cls = "cv-con-title done-text" if done_cv else "cv-con-title"
        meta_parts = []
        if nv_cv:
            meta_parts.append(f'<span>👤 {nv_cv}</span>')
        if dl_cv:
            meta_parts.append(f'<span>📅 {dl_cv}</span>')
        if done_cv:
            meta_parts.append('<span style="color:#16a34a;font-weight:700;">✅ Đã xong</span>')
        meta_html = "".join(meta_parts)

        col_card, col_chk, col_del = st.columns([8, 0.8, 0.8])
        with col_card:
            st.markdown(
                f'<div class="{card_cls}">'
                f'<div style="flex:1">'
                f'<div class="{title_cls}">{j+1}. {ten_cv}</div>'
                f'<div class="cv-con-meta">{meta_html}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        with col_chk:
            da_xong = st.checkbox(
                "Xong", value=done_cv,
                key=f"cv_{task_id}_{j}",
                label_visibility="collapsed",
            )
            if da_xong != done_cv:
                ds_cv_con[j]["done"] = da_xong
                cv_changed = True
        with col_del:
            if st.button("🗑️", key=f"cv_del_{task_id}_{j}", use_container_width=True, help="Xóa công việc này"):
                _cv_xoa = j

    if _cv_xoa is not None:
        ds_cv_con.pop(_cv_xoa)
        st.session_state[_cv_key] = ds_cv_con
        _sh = lay_sheet()
        _o  = _sh.find(str(task_id), in_column=1)
        if _o:
            _sh.update_cell(_o.row, 14, json.dumps(ds_cv_con, ensure_ascii=False))
            lay_danh_sach_cong_viec.clear()
    elif cv_changed:
        st.session_state[_cv_key] = ds_cv_con
        _sh = lay_sheet()
        _o  = _sh.find(str(task_id), in_column=1)
        if _o:
            _sh.update_cell(_o.row, 14, json.dumps(ds_cv_con, ensure_ascii=False))
            lay_danh_sach_cong_viec.clear()
    st.divider()

    # ── Upload ảnh + xuất PDF ─────────────────────────────────
    ds_anh_hien_co = st.session_state[_anh_key]

    st.markdown("**📸 Ảnh Nghiệm Thu**")
    if ds_anh_hien_co:
        st.caption(f"{len(ds_anh_hien_co)} ảnh đã upload")
        cols_anh = st.columns(min(len(ds_anh_hien_co), 3))
        for idx_a, url_a in enumerate(ds_anh_hien_co):
            with cols_anh[idx_a % 3]:
                st.image(url_a, caption=f"Ảnh {idx_a + 1}", use_container_width=True)
                if st.button(f"🗑️ Xoá", key=f"xoa_anh_{task_id}_{idx_a}", use_container_width=True):
                    with st.spinner("Đang xoá..."):
                        xoa_url_anh(task_id, url_a)
                    st.session_state[_anh_key] = [u for u in ds_anh_hien_co if u != url_a]
    else:
        st.caption("Chưa có ảnh nghiệm thu.")

    with st.form(key=f"form_upload_{task_id}"):
        anh_upload = st.file_uploader(
            "Thêm ảnh (JPG, PNG)",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
        if st.form_submit_button("📤 Upload ảnh"):
            if not anh_upload:
                st.warning("⚠️ Chọn ít nhất một file ảnh!")
            else:
                with st.spinner(f"Đang upload {len(anh_upload)} ảnh..."):
                    new_urls = []
                    for f in anh_upload:
                        url = tai_anh_len_cloudinary(f)
                        cap_nhat_url_anh(task_id, url)
                        new_urls.append(url)
                st.session_state[_anh_key] = list(ds_anh_hien_co) + new_urls
                st.success(f"✅ Đã upload {len(anh_upload)} ảnh!")

    # PDF
    tt_pdf = st.session_state.get(f"tt_select_{task_id}", trang_thai)
    if tt_pdf == "Đã Hoàn Thành - Giao Máy" or "Hoàn Thành" in tt_pdf:
        st.divider()
        if st.button("📄 Tạo Biên Bản PDF", key=f"pdf_{task_id}", use_container_width=True):
            with st.spinner("Đang tạo PDF..."):
                df_moi = lay_danh_sach_cong_viec()
                rows = df_moi[df_moi["ID"].astype(str) == str(task_id)]
                if not rows.empty:
                    du_lieu_pdf = tao_pdf_nghiem_thu(rows.iloc[0].to_dict())
                    st.download_button(
                        "💾 Tải Xuống PDF",
                        data=du_lieu_pdf,
                        file_name=f"BBNT_task_{task_id}.pdf",
                        mime="application/pdf",
                        key=f"dl_pdf_{task_id}",
                        use_container_width=True,
                    )


# ============================================================
# FRAGMENT: CHECKLIST & CÔNG VIỆC CON (rerun cục bộ, không reload toàn trang)
# ============================================================
@st.fragment
def _fragment_checklist(key_prefix: str):
    """
    Fragment quản lý checklist. st.rerun() bên trong chỉ rerun fragment này,
    không kéo theo tất cả Google Sheets calls ở ngoài.
    """
    cl_key = f"{key_prefix}_checklist"
    if cl_key not in st.session_state:
        st.session_state[cl_key] = []

    st.markdown("**☑️ Checklist**")
    col_inp, col_btn = st.columns([4, 1])
    with col_inp:
        moi = st.text_input(
            "Thêm mục checklist",
            placeholder="Ví dụ: Quấn dây, Thay bạc đạn...",
            key=f"{key_prefix}_cl_inp",
            label_visibility="collapsed",
        )
    with col_btn:
        if st.button("➕ Thêm", key=f"{key_prefix}_cl_add", use_container_width=True):
            if moi.strip():
                st.session_state[cl_key].append({"text": moi.strip(), "done": False})
                st.rerun()   # chỉ rerun fragment

    for i, item in enumerate(st.session_state[cl_key]):
        col_ck, col_tx, col_del = st.columns([0.5, 5.5, 1])
        with col_ck:
            done = st.checkbox(
                "", value=item["done"],
                key=f"{key_prefix}_ck_{i}",
                label_visibility="collapsed",
            )
            if done != item["done"]:
                st.session_state[cl_key][i]["done"] = done
                st.rerun()
        with col_tx:
            txt = f"~~{item['text']}~~" if done else item["text"]
            st.markdown(f"{i + 1}. {txt}")
        with col_del:
            if st.button("🗑️", key=f"{key_prefix}_cl_del_{i}", use_container_width=True):
                st.session_state[cl_key].pop(i)
                st.rerun()


@st.fragment
def _fragment_cong_viec_con(key_prefix: str, ds_nhan_vien: list):
    """
    Fragment quản lý công việc con. st.rerun() chỉ rerun fragment này.
    """
    cv_key = f"{key_prefix}_cong_viec_con"
    if cv_key not in st.session_state:
        st.session_state[cv_key] = []

    st.markdown("**📋 Công Việc Con**")
    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
    with col1:
        cv_ten = st.text_input(
            "Tên việc", placeholder="Ví dụ: Tháo máy",
            key=f"{key_prefix}_cv_ten", label_visibility="collapsed",
        )
    with col2:
        cv_nv = st.selectbox(
            "Nhân viên", options=["-- Chọn --"] + ds_nhan_vien,
            key=f"{key_prefix}_cv_nv", label_visibility="collapsed",
        )
    with col3:
        cv_dl = st.date_input("Deadline", key=f"{key_prefix}_cv_dl", label_visibility="collapsed")
    with col4:
        if st.button("➕", key=f"{key_prefix}_cv_add", use_container_width=True):
            if cv_ten.strip():
                st.session_state[cv_key].append({
                    "ten":      cv_ten.strip(),
                    "nguoi":    cv_nv if cv_nv != "-- Chọn --" else "",
                    "deadline": str(cv_dl),
                    "done":     False,
                })
                st.rerun()   # chỉ rerun fragment

    for i, cv in enumerate(st.session_state[cv_key]):
        col_a, col_b, col_c, col_d, col_e = st.columns([0.5, 3, 2, 2, 1])
        with col_a:
            done_cv = st.checkbox(
                "", value=cv["done"],
                key=f"{key_prefix}_cvcv_{i}",
                label_visibility="collapsed",
            )
            if done_cv != cv["done"]:
                st.session_state[cv_key][i]["done"] = done_cv
                st.rerun()
        with col_b:
            label_cv = f"~~{cv['ten']}~~" if done_cv else cv["ten"]
            st.markdown(f"{i + 1}. {label_cv}")
        with col_c:
            st.markdown(f"👤 {cv['nguoi'] or '—'}")
        with col_d:
            st.markdown(f"📅 {cv['deadline']}")
        with col_e:
            if st.button("🗑️", key=f"{key_prefix}_cv_del_{i}", use_container_width=True):
                st.session_state[cv_key].pop(i)
                st.rerun()


# ============================================================
# GIAO DIỆN ADMIN
# ============================================================
def giao_dien_admin():
    """Giao diện quản lý dành cho Admin — 4 tab ngang: Cài Đặt / Nhân Viên / Tạo Task / Tổng Quan."""
    st.header("🔧 Bảng Điều Khiển Admin")

    tab_cai_dat, tab_nhan_vien, tab_tao_task, tab_tong_quan = st.tabs(
        ["⚙️  Cài Đặt", "👥  Nhân Viên", "➕  Tạo Công Việc Mới", "📊  Tổng Quan"]
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
                st.dataframe(df, use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════
    # TAB 1 — CÀI ĐẶT
    # ══════════════════════════════════════════════
    with tab_cai_dat:
        _section_don_gian(
            "🏢 Quản Lý Công Ty", "cong_ty",
            lay_danh_sach_cong_ty, them_cong_ty, "Tên Công Ty",
            placeholder="Ví dụ: Công Ty TNHH ABC",
            mo_ta_them="Tên Công Ty *", expanded=True,
        )
        _section_don_gian(
            "🔧 Loại Máy", "loai_may",
            lay_danh_sach_loai_may, them_loai_may, "Tên Loại Máy",
            placeholder="Ví dụ: Động Cơ Điện, Máy Bơm...",
            mo_ta_them="Tên Loại Máy *",
        )
        _section_don_gian(
            "📋 Trạng Thái Công Việc", "trang_thai",
            lay_danh_sach_trang_thai_custom, them_trang_thai_custom, "Tên Trạng Thái",
            placeholder="Ví dụ: Chờ Làm, Đang Làm, Hoàn Thành...",
            mo_ta_them="Tên Trạng Thái *",
        )
        _section_don_gian(
            "⚙️ Công Đoạn", "cong_doan",
            lay_danh_sach_cong_doan, them_cong_doan, "Tên Công Đoạn",
            placeholder="Ví dụ: Kiểm Tra Đầu Vào, Tháo Rã, Quấn Dây...",
            mo_ta_them="Tên Công Đoạn *",
        )
        with st.expander("👷 Người Thực Hiện Công Đoạn"):
            ds_cong_doan_hien = lay_ten_cac_cong_doan()
            if not ds_cong_doan_hien:
                st.warning("⚠️ Chưa có Công Đoạn nào. Hãy thêm ở mục **⚙️ Công Đoạn** trước!")
            else:
                with st.form("form_nguoi_cong_doan", clear_on_submit=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        ho_ten_ncd = st.text_input("Họ Tên *", placeholder="Ví dụ: Nguyễn Văn An")
                    with col_b:
                        cong_doan_chon = st.selectbox("Công Đoạn *", options=ds_cong_doan_hien)
                    gui_ncd = st.form_submit_button("➕ Thêm Người Thực Hiện", use_container_width=True)
                    if gui_ncd:
                        if not ho_ten_ncd.strip():
                            st.error("⛔ Vui lòng nhập họ tên!")
                        else:
                            with st.spinner("Đang lưu..."):
                                id_ncd = them_nguoi_cong_doan(ho_ten_ncd.strip(), cong_doan_chon)
                            st.success(f"✅ Đã thêm #{id_ncd}: **{ho_ten_ncd}** — Công đoạn: **{cong_doan_chon}**!")
                st.divider()
                df_ncd = lay_danh_sach_nguoi_cong_doan()
                if df_ncd.empty:
                    st.info("ℹ️ Chưa có người thực hiện nào.")
                else:
                    st.markdown(f"**Tổng cộng: {len(df_ncd)} người**")
                    st.dataframe(df_ncd, use_container_width=True, hide_index=True)

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
                border-radius: 12px;
                padding: 14px 18px;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
                gap: 16px;
            }
            .nv-avatar {
                width: 42px; height: 42px;
                border-radius: 50%;
                background: linear-gradient(135deg, #7c3aed, #a78bfa);
                display: flex; align-items: center; justify-content: center;
                font-size: 1.2rem; color: white; font-weight: 700;
                flex-shrink: 0;
            }
            .nv-info { flex: 1; }
            .nv-name { font-weight: 700; font-size: 0.97rem; color: #1e1b4b; }
            .nv-meta { font-size: 0.8rem; color: #6b7280; margin-top: 2px; }
            .nv-badge {
                background: #ede9fe; color: #7c3aed;
                border-radius: 99px; padding: 3px 10px;
                font-size: 0.75rem; font-weight: 600; white-space: nowrap;
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

            # Chọn nhân viên để xem chi tiết
            ds_ten_nv = df_nv_users["HoTen"].tolist()
            sel_nv = st.selectbox(
                "🔍 Chọn nhân viên để xem task:",
                options=["-- Chọn --"] + ds_ten_nv,
                key="adm_sel_nv",
            )

            # ── Danh sách card nhân viên ───────────────────────────────
            for _, u in df_nv_users.iterrows():
                ho_ten  = u["HoTen"]
                uname   = u["Username"]
                ns      = u["NgaySinh"]
                ngay_tao = u.get("NgayTao", "")[:10]
                avatar_char = (ho_ten[0] if ho_ten else "?").upper()
                tc, ts = _dem_task_cua(ho_ten)
                badge_txt = f"📋 {tc} công việc &nbsp;|&nbsp; 🔹 {ts} việc con"
                is_selected = (sel_nv == ho_ten)
                border_style = "border: 2px solid #7c3aed;" if is_selected else ""

                st.markdown(f"""
                <div class="nv-summary-card" style="{border_style}">
                    <div class="nv-avatar">{avatar_char}</div>
                    <div class="nv-info">
                        <div class="nv-name">{ho_ten}</div>
                        <div class="nv-meta">@{uname} &nbsp;·&nbsp; 🎂 {ns or '—'} &nbsp;·&nbsp; 📅 Tham gia {ngay_tao}</div>
                    </div>
                    <div class="nv-badge">{badge_txt}</div>
                </div>
                """, unsafe_allow_html=True)

            # ── Chi tiết task khi chọn nhân viên ──────────────────────
            if sel_nv != "-- Chọn --":
                st.markdown(f"---\n#### 📋 Công việc của **{sel_nv}**")

                # Task chính
                df_task_chinh = df_all_tasks[df_all_tasks["Nhân Viên"] == sel_nv].copy() if not df_all_tasks.empty else pd.DataFrame()

                # Subtask (trong công việc con của các task khác)
                ds_subtask_rows = []
                if not df_all_tasks.empty:
                    for _, row in df_all_tasks.iterrows():
                        try:
                            ds_cv = json.loads(row.get("Công Việc Con", "") or "[]")
                        except Exception:
                            ds_cv = []
                        for cv in ds_cv:
                            if isinstance(cv, dict):
                                nv_cv = cv.get("nhan_vien", cv.get("Nhân Viên", ""))
                                if nv_cv == sel_nv:
                                    ds_subtask_rows.append({
                                        "ID Task Cha": row.get("ID", ""),
                                        "Tên Task Cha": row.get("Tên Công Việc", ""),
                                        "Công Ty": row.get("Công Ty", ""),
                                        "Tên Việc Con": cv.get("ten", cv.get("Tên", "—")),
                                        "Deadline": cv.get("deadline", cv.get("Deadline", "—")),
                                        "Trạng Thái": "✅ Xong" if cv.get("done") else "⏳ Chưa xong",
                                    })

                # ── Tab chính / subtask ─────────────────────────────
                tab_tc, tab_st = st.tabs([
                    f"📌 Công Việc Chính ({len(df_task_chinh)})",
                    f"🔹 Việc Con ({len(ds_subtask_rows)})",
                ])

                _ICON_TT = {
                    "Đang Kiểm Tra": "🔵", "Đã Phê Duyệt": "🟢",
                    "Đã Báo Giá": "🟠", "Có Đơn": "🟣", "Chờ Giao": "🟡",
                    "Đã Hoàn Thành - Giao Máy": "✅", "Đã Xuất Hóa Đơn": "⬜",
                    "Bảo Hành - Trả Lại": "🔴",
                    "Chờ Làm": "🔴", "Đang Làm": "🟡", "Hoàn Thành": "🟢",
                }

                with tab_tc:
                    if df_task_chinh.empty:
                        st.info("Nhân viên này chưa được giao task chính nào.")
                    else:
                        for _, t in df_task_chinh.iterrows():
                            tt = t.get("Trạng Thái", "")
                            icon_tt = _ICON_TT.get(tt, "⚪")
                            with st.expander(
                                f"{icon_tt} **#{t.get('ID','')}** — {t.get('Tên Công Việc','—')}  |  {t.get('Công Ty','')}",
                                expanded=False,
                            ):
                                col_a, col_b, col_c = st.columns(3)
                                col_a.markdown(f"**Công Số:** `{t.get('Công Số','—')}`")
                                col_b.markdown(f"**Hạn:** `{t.get('Hạn Hoàn Thành','—')}`")
                                col_c.markdown(f"**Trạng Thái:** {icon_tt} {tt}")
                                if t.get("Mô Tả"):
                                    st.markdown(f"📝 {t.get('Mô Tả','')}")
                                # Checklist mini
                                try:
                                    cl = json.loads(t.get("Checklist","") or "[]")
                                except Exception:
                                    cl = []
                                if cl:
                                    xong = sum(1 for c in cl if isinstance(c,dict) and c.get("done"))
                                    st.markdown(f"☑️ Checklist: **{xong}/{len(cl)}** mục hoàn thành")

                with tab_st:
                    if not ds_subtask_rows:
                        st.info("Nhân viên này chưa được giao công việc con nào.")
                    else:
                        df_st = pd.DataFrame(ds_subtask_rows)
                        st.dataframe(df_st, use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════
    # TAB 3 — TẠO TASK MỚI
    # ══════════════════════════════════════════════
    with tab_tao_task:
        ds_cong_ty = lay_ten_cac_cong_ty()
        if not ds_cong_ty:
            st.warning("⚠️ Chưa có công ty nào! Hãy thêm ở tab **⚙️ Cài Đặt** trước.")

        _ADM_PREFIX = "adm"
        ds_nhan_vien = lay_danh_sach_nhan_vien()
        ds_trang_thai = lay_ten_cac_trang_thai() or ["Chờ Làm", "Đang Làm", "Hoàn Thành"]

        col_ct, col_pd = st.columns([3, 2])
        with col_ct:
            adm_cong_ty = st.selectbox(
                "🏢 Công Ty Khách Hàng *",
                options=ds_cong_ty if ds_cong_ty else ["(Chưa có công ty)"],
                key="adm_cong_ty",
            )
        with col_pd:
            adm_phe_duyet = st.selectbox(
                "✅ Người Phê Duyệt",
                options=["-- Không chọn --"] + ds_nhan_vien,
                key="adm_phe_duyet",
            )

        col_cs, col_nam = st.columns(2)
        with col_cs:
            adm_cong_so = st.text_input("Công Số *", placeholder="Ví dụ: CS-2026-001", key="adm_cong_so")
        with col_nam:
            adm_nam = st.text_input("Năm *", value=str(datetime.now().year), key="adm_nam")

        col_nv, col_dl = st.columns(2)
        with col_nv:
            adm_nguoi_giao = st.selectbox("👤 Giao cho nhân viên *", options=ds_nhan_vien, key="adm_nguoi_giao")
        with col_dl:
            adm_deadline = st.date_input("📅 Hạn hoàn thành", key="adm_deadline")

        adm_ten_task   = st.text_input("📌 Tên công việc *", placeholder="Ví dụ: Sửa chữa động cơ bơm", key="adm_ten_task")
        adm_mo_ta      = st.text_area("📝 Mô tả chi tiết", placeholder="Nhập mô tả, yêu cầu kỹ thuật...", key="adm_mo_ta")
        adm_trang_thai = st.selectbox("📋 Trạng thái", options=ds_trang_thai, key="adm_trang_thai")

        st.divider()
        _fragment_checklist(_ADM_PREFIX)
        st.divider()
        _fragment_cong_viec_con(_ADM_PREFIX, ds_nhan_vien)
        st.divider()

        if st.button("✅ Tạo Task", use_container_width=True, type="primary", key="adm_submit_task"):
            if not adm_ten_task.strip():
                st.error("⛔ Vui lòng nhập tên công việc!")
            elif not ds_cong_ty:
                st.error("⛔ Vui lòng thêm ít nhất một công ty trước!")
            elif not adm_cong_so.strip():
                st.error("⛔ Vui lòng nhập Công Số!")
            else:
                phe_duyet_luu = adm_phe_duyet if adm_phe_duyet != "-- Không chọn --" else ""
                with st.spinner("Đang lưu lên Google Sheets..."):
                    id_moi = them_cong_viec(
                        adm_ten_task.strip(), adm_mo_ta.strip(), adm_nguoi_giao,
                        adm_deadline.strftime("%Y-%m-%d"),
                        cong_ty=adm_cong_ty, cong_so=adm_cong_so.strip(),
                        nam=adm_nam.strip(), trang_thai=adm_trang_thai,
                        nguoi_phe_duyet=phe_duyet_luu,
                        checklist=list(st.session_state.get(f"{_ADM_PREFIX}_checklist", [])),
                        cong_viec_con=list(st.session_state.get(f"{_ADM_PREFIX}_cong_viec_con", [])),
                    )
                st.session_state[f"{_ADM_PREFIX}_checklist"] = []
                st.session_state[f"{_ADM_PREFIX}_cong_viec_con"] = []
                st.success(
                    f"✅ Đã tạo task #{id_moi} — **{adm_cong_ty}** | "
                    f"CS: **{adm_cong_so}** | Giao: **{adm_nguoi_giao}**!"
                )
                st.balloons()
                st.rerun()

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

            # Hàng 1: Tổng + các KPI
            kpi_items = [("📋 TỔNG TASK", len(df))] + [
                (f"{_ICON_KPI.get(tt, '⚪')} {tt.upper()}", len(df[df["Trạng Thái"] == tt]))
                for tt in ds_tt_sorted
            ]
            # Chia thành các nhóm 4 cột
            for row_start in range(0, len(kpi_items), 4):
                chunk = kpi_items[row_start:row_start + 4]
                cols_kpi = st.columns(len(chunk))
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
                    default=all_tt,
                    key="adm_loc_tt",
                )
            with col_f2:
                danh_sach_nv = df["Nhân Viên"].dropna().unique().tolist()
                loc_nhan_vien = st.multiselect("Lọc theo nhân viên", options=danh_sach_nv, key="adm_loc_nv")
            with col_f3:
                danh_sach_ct = df["Công Ty"].dropna().unique().tolist() if "Công Ty" in df.columns else []
                loc_cong_ty  = st.multiselect("🏢 Lọc theo Công Ty", options=danh_sach_ct, key="adm_loc_ct")

            df_hien_thi = df.copy()
            if loc_trang_thai:
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


# ============================================================
# GIAO DIỆN NHÂN VIÊN
# ============================================================
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

    # Khi nhân viên vừa chọn tên → xóa cache để lấy dữ liệu mới nhất từ Google Sheets
    _nv_key = f"_nv_loaded_{ten_nhan_vien}"
    if not st.session_state.get(_nv_key):
        lay_danh_sach_cong_viec.clear()
        st.session_state[_nv_key] = True

    # ---- Tabs ----
    tab_cong_viec, tab_tao_task = st.tabs([
        "📋 Công Việc Của Tôi",
        "➕ Tạo Công Việc Mới"
    ])

    # ========================================================
    # Tab 1: Công việc của tôi
    # ========================================================
    with tab_cong_viec:
        st.subheader(f"Công việc của: **{ten_nhan_vien}**")

        col_btn, col_loc = st.columns([1, 3])
        with col_btn:
            if st.button("🔄 Làm mới"):
                lay_danh_sach_cong_viec.clear()
                st.rerun()

        # Tải danh sách công việc
        with st.spinner("Đang tải công việc..."):
            df = lay_danh_sach_cong_viec()

        # Lọc công việc thuộc nhân viên này
        df_cua_toi = df[df["Nhân Viên"] == ten_nhan_vien].copy()

        if df_cua_toi.empty:
            st.success("🎉 Bạn hiện chưa có công việc nào được giao!")
        else:
            # Bộ lọc theo Công Ty cho nhân viên
            ds_cong_ty_cua_toi = df_cua_toi["Công Ty"].dropna().unique().tolist() if "Công Ty" in df_cua_toi.columns else []
            with col_loc:
                if ds_cong_ty_cua_toi:
                    loc_cong_ty = st.multiselect(
                        "🏢 Lọc theo Công Ty",
                        options=ds_cong_ty_cua_toi,
                        placeholder="Hiển thị tất cả..."
                    )
                    if loc_cong_ty:
                        df_cua_toi = df_cua_toi[df_cua_toi["Công Ty"].isin(loc_cong_ty)]

        # Lấy danh sách trạng thái (custom từ admin, hoặc mặc định)
        ds_tt = lay_ten_cac_trang_thai() or ["Chờ Làm", "Đang Làm", "Hoàn Thành"]

        # Hiển thị từng task dưới dạng expander
        for _, hang in df_cua_toi.iterrows():
            task_id    = hang["ID"]
            trang_thai = hang.get("Trạng Thái", "Chờ Làm")
            _ICON_TT = {
                "Đang Kiểm Tra": "🔵", "Đã Phê Duyệt": "🟢", "Đã Báo Giá": "🟠",
                "Có Đơn": "🟣", "Chờ Giao": "🟡",
                "Đã Hoàn Thành - Giao Máy": "✅",
                "Đã Xuất Hóa Đơn": "⬜", "Bảo Hành - Trả Lại": "🔴",
                "Chờ Làm": "🔴", "Đang Làm": "🟡", "Hoàn Thành": "🟢",
            }
            icon_tt    = _ICON_TT.get(trang_thai, "⚪")
            ten_cv     = hang.get("Tên Công Việc", "")
            cong_ty    = hang.get("Công Ty", "")

            with st.expander(
                f"{icon_tt} [{cong_ty}]  Task #{task_id}: {ten_cv}  —  {trang_thai}",
                expanded=(trang_thai in ["Chờ Làm", "Đang Làm"])
            ):
                _fragment_chi_tiet_task(hang.to_dict(), ds_tt)

    # ========================================================
    # Tab 2: Tạo Công Việc Mới (nhân viên tự nhập)
    # ========================================================
    with tab_tao_task:
        st.subheader("➕ Tạo Công Việc Mới")
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

            # ── Hàng đầu: Công Ty (trái) + Người Phê Duyệt (phải) ──
            col_ct2, col_pd2 = st.columns([3, 2])
            with col_ct2:
                nv_cong_ty = st.selectbox("🏢 Công Ty *", options=ds_cong_ty_nv, key=f"{_nv_prefix}_ct")
            with col_pd2:
                nv_phe_duyet = st.selectbox(
                    "✅ Người Phê Duyệt",
                    options=["-- Không chọn --"] + ds_nv_nv,
                    key=f"{_nv_prefix}_pd"
                )

            col_cs2, col_nam2 = st.columns(2)
            with col_cs2:
                nv_cong_so = st.text_input("📋 Công Số", placeholder="Ví dụ: CS-001", key=f"{_nv_prefix}_cs")
            with col_nam2:
                nv_nam = st.text_input("📅 Năm", value=str(datetime.now().year), key=f"{_nv_prefix}_nam")

            # Nhân viên giao = chính mình, chỉ cần chọn deadline
            st.markdown(f"**👤 Nhân viên thực hiện:** `{ten_nhan_vien}` *(tự động)*")
            nv_deadline = st.date_input("📅 Hạn Hoàn Thành", key=f"{_nv_prefix}_dl")

            nv_ten_task = st.text_input("📌 Tên Công Việc *", placeholder="Mô tả ngắn công việc cần làm", key=f"{_nv_prefix}_ten")
            nv_mo_ta    = st.text_area("📝 Mô Tả Chi Tiết", placeholder="Mô tả chi tiết về công việc...", key=f"{_nv_prefix}_mo_ta")

            nv_trang_thai = st.selectbox("📋 Trạng thái", options=ds_trang_thai_nv, key=f"{_nv_prefix}_tt")

            st.divider()
            _fragment_checklist(_nv_prefix)

            st.divider()
            _fragment_cong_viec_con(_nv_prefix, ds_nv_nv)

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
                            cong_so         = nv_cong_so.strip(),
                            nam             = nv_nam.strip(),
                            trang_thai      = nv_trang_thai,
                            nguoi_phe_duyet = phe_duyet_nv,
                            checklist       = list(st.session_state[_cl_key]),
                            cong_viec_con   = list(st.session_state[_cv_key]),
                        )
                    st.session_state[_cl_key] = []
                    st.session_state[_cv_key] = []
                    st.success(f"🎉 Đã tạo task **{nv_ten_task}** thành công! Chuyển sang tab **Công Việc Của Tôi** để xem.")
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

    tab_dn, tab_dk = st.tabs(["🔑  Đăng Nhập", "📝  Đăng Ký"])

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

        with st.expander("ℹ️ Thông tin về tài khoản"):
            st.info(
                "- Tài khoản mới sẽ có vai trò **Nhân Viên**.\n"
                "- Quản trị viên được cấp quyền **Admin** bởi hệ thống.\n"
                "- Tài khoản mặc định admin: **admin / admin123** (đổi mật khẩu sau khi đăng nhập)."
            )


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

    /* ===== ẨN SIDEBAR BUTTON & SIDEBAR HOÀN TOÀN ===== */
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] {
        display: none !important;
    }
    .main .block-container {
        padding-bottom: 80px !important; /* chỗ cho bottom nav */
    }

    /* ===== BOTTOM NAV BAR ===== */
    .bottom-nav {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        background: #ffffff;
        border-top: 1px solid #e5e7eb;
        box-shadow: 0 -4px 20px rgba(0,0,0,0.10);
        display: flex;
        height: 64px;
        align-items: stretch;
    }
    .nav-item {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 3px;
        cursor: pointer;
        border: none;
        background: transparent;
        color: #9ca3af;
        font-size: 0.68rem;
        font-family: 'Be Vietnam Pro', sans-serif;
        font-weight: 600;
        letter-spacing: 0.3px;
        transition: color 0.2s ease;
        text-decoration: none;
        padding: 8px 0;
    }
    .nav-item .nav-icon {
        font-size: 1.45rem;
        line-height: 1;
    }
    .nav-item.active {
        color: #667eea;
    }
    .nav-item.active .nav-icon {
        filter: drop-shadow(0 2px 6px rgba(102,126,234,0.45));
    }

    /* indicator gạch chân */
    .nav-item.active::before {
        content: '';
        position: absolute;
        top: 0;
        width: 40px;
        height: 3px;
        background: linear-gradient(90deg,#667eea,#764ba2);
        border-radius: 0 0 4px 4px;
    }
    .nav-item { position: relative; }

    /* Ẩn radio Streamlit gốc (dùng để giữ state), chỉ dùng bottom nav HTML */
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
            padding: 0.8rem 0.8rem 90px 0.8rem !important;
            max-width: 100% !important;
            margin-left: 0 !important;
        }

        /* --- Header nhỏ lại --- */
        .main-header {
            padding: 0.55rem 0.9rem !important;
            border-radius: 10px !important;
        }
        .main-header h1 {
            font-size: 0.92rem !important;
        }
        .main-header p {
            font-size: 0.75rem !important;
        }

        /* --- Columns tự stack dọc --- */
        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: 0 !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
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
            font-size: 1rem !important;
            min-height: 44px !important;
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


def main():
    """Hàm chính: khởi động và điều hướng ứng dụng."""
    inject_css()

    # ── Xử lý query param chuyển vai trò (chỉ dùng cho admin) ──────────────
    qp = st.query_params
    if "role" in qp:
        role_val = qp["role"]
        if role_val in ("admin", "nhan_vien") and st.session_state.get("vai_tro") == "admin":
            st.session_state["vai_tro"] = role_val
        st.query_params.clear()
        st.rerun()

    # ── Kiểm tra đăng nhập ─────────────────────────────────────────────────
    if not st.session_state.get("dang_nhap"):
        giao_dien_dang_nhap()
        return

    vai_tro   = st.session_state.get("vai_tro", "nhan_vien")
    ho_ten    = st.session_state.get("ho_ten", "")

    # ── Header compact (topbar) ────────────────────────────────────────────
    role_badge = "🛡️ Admin" if vai_tro == "admin" else "👤"
    st.markdown(f"""
        <div class="main-header">
            <h1>📋 Quản Lý Công Việc</h1>
            <div class="main-header-user">{role_badge} &nbsp;<b>{ho_ten}</b></div>
        </div>
    """, unsafe_allow_html=True)
    # Nút đăng xuất — căn phải, có chữ rõ ràng
    col_gap, col_logout = st.columns([7, 2])
    with col_logout:
        if st.button("🚪 Đăng Xuất", use_container_width=True, type="secondary"):
            for key in ["dang_nhap", "user_id", "username", "ho_ten", "vai_tro"]:
                st.session_state.pop(key, None)
            st.rerun()

    # ── Bottom nav (chỉ admin mới thấy để chuyển qua lại view) ────────────
    if vai_tro == "admin":
        view = st.session_state.get("vai_tro", "admin")
        is_admin = "active" if view == "admin" else ""
        is_nv    = "active" if view == "nhan_vien" else ""
        st.markdown(f"""
            <div class="bottom-nav">
                <a class="nav-item {is_nv}" href="?role=nhan_vien">
                    <span class="nav-icon">👤</span>
                    <span>Nhân Viên</span>
                </a>
                <a class="nav-item {is_admin}" href="?role=admin">
                    <span class="nav-icon">⚙️</span>
                    <span>Admin</span>
                </a>
            </div>
        """, unsafe_allow_html=True)

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
