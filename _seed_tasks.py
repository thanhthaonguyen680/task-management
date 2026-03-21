"""Khôi phục danh sách công việc vào sheet Tasks theo dữ liệu database."""
import json, toml, gspread
from google.oauth2.service_account import Credentials

# ── Kết nối Google Sheets ─────────────────────────────────────
s = toml.load(".streamlit/secrets.toml")
creds = Credentials.from_service_account_info(
    s["gcp_service_account"],
    scopes=["https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"]
)
wb = gspread.authorize(creds).open("QuanLyCongViec")

try:
    ws = wb.worksheet("Tasks")
except Exception:
    ws = wb.add_worksheet("Tasks", 1000, 25)

# ── Header ────────────────────────────────────────────────────
HEADERS = [
    "ID", "Công Ty", "Công Số", "Năm", "Tên Công Việc", "Mô Tả",
    "Nhân Viên", "Trạng Thái", "Ngày Tạo", "Hạn Hoàn Thành",
    "Link Ảnh", "Người Phê Duyệt", "Checklist", "Công Việc Con", "Công Đoạn",
    "Loại Máy", "Tình Trạng",
    "Công Suất", "Số Cực", "Mã Số", "Số PO Nội Bộ", "Số PO KH/HĐ", "Số Báo Giá",
    "Ngày Kết Thúc", "Ảnh Đo Lường",
]

# Kiểm tra sheet hiện tại
existing_ids = ws.col_values(1)[1:]  # bỏ header
existing_ids_set = {str(x).strip() for x in existing_ids if str(x).strip().isdigit()}

# ── Danh sách công việc cần khôi phục ────────────────────────
# Format: (id, cong_ty, cong_so, nam, ten_cv, mo_ta, nhan_vien, trang_thai,
#          ngay_tao, han_ht, link_anh, nguoi_pd, checklist_json, cv_con_json,
#          cong_doan, loai_may, tinh_trang, cong_suat, so_cuc, ma_so,
#          so_po_noi_bo, so_po_kh, so_bao_gia, ngay_kt, anh_do_luong)
TASKS = [
    (
        1,
        "CÔNG TY TNHH DAE MYUNG CHEMICAL (VIỆT NAM) - SƠN",
        "", "2026",
        "AS - motor (120w) số 260600",
        "", "trantuananh", "Đang Kiểm Tra",
        "2026-03-20 09:30:50", "2026-03-20",
        "", "Trần Tuấn Anh",
        json.dumps([{"text": "Quản lý tiếp nhận", "done": False}], ensure_ascii=False),
        json.dumps([{"ten": "Nhận máy", "nhan_vien": "", "done": False}], ensure_ascii=False),
        "", "Động cơ AC 3 Pha", "Sửa chữa",
        "120w", "", "260600",
        "", "", "", "", "{}",
    ),
    (
        2,
        "CÔNG TY TNHH KỸ THUẬT KIM NGÂN PHÁT",
        "", "2026",
        "KNP - bơm 0.4kw 4p số 260599",
        "", "", "Đang Kiểm Tra",
        "2026-03-21 01:00:38", "2026-03-21",
        "", "",
        json.dumps([], ensure_ascii=False),
        json.dumps([{"ten": "Nhận máy", "nhan_vien": "", "done": False}], ensure_ascii=False),
        "", "Động cơ AC 3 Pha", "Sửa chữa",
        "0.4kw", "4p", "260599",
        "", "", "", "", "{}",
    ),
    (
        3,
        "CÔNG TY TNHH KỸ THUẬT KIM NGÂN PHÁT",
        "", "2026",
        "KPN - bơm chìm (không có tem) số 260589",
        "", "", "Đang Kiểm Tra",
        "2026-03-21 01:00:39", "2026-03-21",
        "", "",
        json.dumps([], ensure_ascii=False),
        json.dumps([{"ten": "Nhận máy", "nhan_vien": "", "done": False}], ensure_ascii=False),
        "", "Động cơ AC 3 Pha", "Sửa chữa",
        "", "", "260589",
        "", "", "", "", "{}",
    ),
    (
        4,
        "CÔNG TY TNHH KỸ THUẬT KIM NGÂN PHÁT",
        "", "2026",
        "KNP - bơm khuấy 2.2kw số 260597",
        "", "", "Đang Kiểm Tra",
        "2026-03-21 01:29:53", "2026-03-21",
        "", "",
        json.dumps([], ensure_ascii=False),
        json.dumps([{"ten": "Nhận máy", "nhan_vien": "", "done": False}], ensure_ascii=False),
        "", "Động cơ AC 3 Pha", "Sửa chữa",
        "2.2kw", "", "260597",
        "", "", "", "", "{}",
    ),
    (
        5,
        "CÔNG TY CỔ PHẦN GIÀY ĐỒNG TIẾN - LONG AN",
        "", "2026",
        "Báo trì động cơ M149 - M150 số 260596",
        "", "", "Đang Kiểm Tra",
        "2026-03-21 01:57:24", "2026-03-21",
        "", "",
        json.dumps([], ensure_ascii=False),
        json.dumps([{"ten": "Nhận máy", "nhan_vien": "", "done": False}], ensure_ascii=False),
        "", "Động cơ AC 3 Pha", "Sửa chữa",
        "", "", "260596",
        "", "", "", "", "{}",
    ),
    (
        6,
        "CÔNG TY TNHH KỸ THUẬT PACIFIC VIEW",
        "", "2026",
        "ZQ - motor 5.5kw 4p số 260601",
        "", "trantuananh", "Đã Phê Duyệt",
        "2026-03-21 02:14:00", "2026-03-21",
        "", "Trần Tuấn Anh",
        json.dumps([], ensure_ascii=False),
        json.dumps([{"ten": "Nhận máy", "nhan_vien": "", "done": False}], ensure_ascii=False),
        "", "Động cơ AC 3 Pha", "Sửa chữa",
        "5.5kw", "4p", "260601",
        "", "", "", "", "{}",
    ),
    (
        7,
        "CÔNG TY TNHH KỸ THUẬT PACIFIC VIEW",
        "", "2026",
        "ZQ - motor 5.5kw 4p số 260602",
        "", "trantuananh", "Đang Kiểm Tra",
        "2026-03-21 02:17:01", "2026-03-21",
        "", "Trần Tuấn Anh",
        json.dumps([], ensure_ascii=False),
        json.dumps([{"ten": "Nhận máy", "nhan_vien": "", "done": False}], ensure_ascii=False),
        "", "Động cơ AC 3 Pha", "Sửa chữa",
        "5.5kw", "4p", "260602",
        "", "", "", "", "{}",
    ),
]

# ── Đảm bảo header đúng ───────────────────────────────────────
header_row = ws.row_values(1)
if header_row != HEADERS:
    ws.update(range_name="A1", values=[HEADERS])
    print("✅ Đã cập nhật header row")

# ── Chèn từng task (bỏ qua nếu ID đã tồn tại) ────────────────
added = 0
skipped = 0
for task in TASKS:
    task_id = str(task[0])
    if task_id in existing_ids_set:
        print(f"  SKIP  ID={task_id} — {task[4]} (đã tồn tại)")
        skipped += 1
        continue

    next_row = len(ws.col_values(1)) + 1
    ws.update(range_name=f"A{next_row}:Y{next_row}", values=[list(task)])
    existing_ids_set.add(task_id)
    print(f"  ADDED ID={task_id} — {task[4]}")
    added += 1

print(f"\nHoàn thành: {added} thêm mới, {skipped} bỏ qua (đã có).")
