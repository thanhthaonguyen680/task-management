"""
Script sửa header cho tất cả các sheet trong Google Sheets.
Chạy một lần để thêm tiêu đề cột còn thiếu.

Usage:
    python _fix_headers.py
"""

import sys
import gspread
from google.oauth2.service_account import Credentials

try:
    import tomllib
    def _load_toml(path):
        with open(path, "rb") as f:
            return tomllib.load(f)
except ImportError:
    try:
        import tomli as tomllib
        def _load_toml(path):
            with open(path, "rb") as f:
                return tomllib.load(f)
    except ImportError:
        import json, re
        def _load_toml(path):
            # Fallback: dùng toml thư viện cũ
            try:
                import toml
                with open(path) as f:
                    return toml.load(f)
            except ImportError:
                raise RuntimeError("Cần cài: pip install toml")

# ── Đọc credentials từ secrets.toml ──────────────────────────────────────────
secrets = _load_toml(".streamlit/secrets.toml")

gcp_info = secrets["gcp_service_account"]
scopes = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds  = Credentials.from_service_account_info(gcp_info, scopes=scopes)
client = gspread.authorize(creds)
wb     = client.open("QuanLyCongViec")

print(f"✅ Kết nối thành công: {wb.title}")
print(f"   Các sheet hiện có: {[ws.title for ws in wb.worksheets()]}\n")

# ── Định nghĩa header cho từng sheet ─────────────────────────────────────────
SHEET_HEADERS = {
    "Tasks": [
        "ID", "Công Ty", "Công Số", "Năm", "Tên Công Việc", "Mô Tả",
        "Nhân Viên", "Trạng Thái", "Ngày Tạo", "Hạn Hoàn Thành",
        "Link Ảnh", "Người Phê Duyệt", "Checklist", "Công Việc Con", "Công Đoạn",
        "Loại Máy", "Tình Trạng",
    ],
    "Users": [
        "ID", "Username", "Password", "HoTen", "NgaySinh",
        "VaiTro", "NgayTao",
    ],
    "Companies": [
        "ID", "Tên Công Ty", "Ngày Tạo",
    ],
    "TrangThai": [
        "ID", "Tên Trạng Thái", "Ngày Tạo",
    ],
    "LoaiMay": [
        "ID", "Tên Loại Máy", "Ngày Tạo",
    ],
    "CongDoan": [
        "ID", "Tên Công Đoạn", "Ngày Tạo",
    ],
    "NguoiCongDoan": [
        "ID", "Họ Tên", "Công Đoạn", "Ngày Tạo",
    ],
    "TinhTrang": [
        "ID", "Tên Tình Trạng", "Ngày Tạo",
    ],
}

# ── Xử lý từng sheet ─────────────────────────────────────────────────────────
for sheet_name, headers in SHEET_HEADERS.items():
    # Tạo sheet nếu chưa có
    try:
        ws = wb.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        print(f"⚠️  Sheet '{sheet_name}' chưa tồn tại — bỏ qua.")
        continue

    # Đọc row 1 hiện tại
    all_vals = ws.get_all_values()
    row1     = all_vals[0] if all_vals else []
    # Lấy phần có nội dung (bỏ ô trống cuối)
    row1_stripped = [c.strip() for c in row1 if c.strip()]

    if row1_stripped == headers[:len(row1_stripped)] and len(row1_stripped) >= len(headers):
        print(f"✅ Sheet '{sheet_name}': header đã đúng, không cần sửa.")
        continue

    # Ghi header vào row 1 (cập nhật từ ô A1)
    ws.update(
        range_name=f"A1:{chr(ord('A') + len(headers) - 1)}1",
        values=[headers],
    )
    print(f"✅ Sheet '{sheet_name}': đã ghi {len(headers)} cột header.")
    print(f"   → {headers}")

print("\n🎉 Hoàn tất! Mở lại Google Sheets để kiểm tra.")
