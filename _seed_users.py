"""Seed danh sách nhân viên vào sheet Users."""
import hashlib, toml, gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ── Kết nối Google Sheets ─────────────────────────────────────
s = toml.load(".streamlit/secrets.toml")
creds = Credentials.from_service_account_info(
    s["gcp_service_account"],
    scopes=["https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"]
)
wb = gspread.authorize(creds).open("QuanLyCongViec")

try:
    ws = wb.worksheet("Users")
except Exception:
    ws = wb.add_worksheet("Users", 500, 7)
    ws.append_row(["ID", "Username", "Password", "HoTen", "NgaySinh", "VaiTro", "NgayTao"])

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def parse_ngay_sinh(s: str) -> str:
    """Chuyển DD/MM/YYYY → YYYY-MM-DD."""
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except Exception:
        return s.strip()

# ── Danh sách nhân viên ───────────────────────────────────────
NHAN_VIEN = [
    ("Trần Tuấn Anh",            "NV01", "trantuananh",        "29/06/2021"),
    ("Bùi Lê Ngọc Linh",         "NV03", "builengoclinh",      "04/08/2023"),
    ("Nguyễn Văn Hữu",           "NV05", "nguyenvanhuu",       "04/06/2021"),
    ("Đặng Bá Hiệp",             "NV08", "dangbahiep",         "04/06/2021"),
    ("Lê Minh Trường",            "NV09", "leminhtruong",       "01/06/2023"),
    ("Phạm Thị Huyền Trâm",      "NV25", "phamthihuyentram",   "15/06/2022"),
    ("Nguyễn Văn Hoàng Sơn",     "NV26", "nguyenvanhoangson",  "15/06/2022"),
    ("Nguyễn Công Quý",          "NV27", "nguyencongquy",      "15/06/2022"),
    ("Lê Văn Minh",              "NV29", "levanminh",          "02/03/2023"),
    ("Phạm Hải Lương",           "NV33", "phamhailuong",       "02/03/2024"),
    ("Nguyễn Anh Minh",          "NV37", "nguyenanhminh",      "01/07/2024"),
    ("Trương Hoài Duy",          "NV39", "truonghoaiduy",      "01/08/2024"),
    ("Trương Thị Ngọc Huyền",    "NV44", "truongthingochuyen", "02/01/2025"),
    ("Nguyễn Bảo Toàn",         "NV45", "nguyenbaotoan",      "01/03/2025"),
    ("Nguyễn Văn Vững",          "NV49", "nguyenvanvung",      "01/03/2025"),
    ("Lê Thị Bảo Ý",             "NV50", "lethibaoy",          "01/03/2025"),
    ("Ly Văn Hiển",              "NV51", "lyvanhien",          "21/09/2005"),
    ("Trần Văn Hùng",            "NV53", "tranvanhung",        "14/06/1976"),
    ("Nguyễn Văn Minh",          "NV54", "nguyenvanminh",      "05/08/2003"),
    ("Võ Thanh Việt",            "NV56", "vothanhviet",        "18/03/1976"),
    ("Nguyễn Tấn Dũng",          "NV57", "nguyentandung",      "01/01/1992"),
    ("Nguyễn Tiến Minh",         "NV58", "nguyentienminh",     "15/03/2008"),
    ("Trần Quỳnh",               "NV59", "tranquynh",          "26/08/1989"),
]

# ── Lấy danh sách username đã có ─────────────────────────────
existing = ws.col_values(2)  # cột Username (1-based = 2)
existing_lower = {u.strip().lower() for u in existing if u.strip()}
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

added = 0
skipped = 0
for ho_ten, username, mat_khau, ngay_sinh in NHAN_VIEN:
    if username.lower() in existing_lower:
        print(f"  SKIP  {username} ({ho_ten}) — đã tồn tại")
        skipped += 1
        continue
    id_moi = len(ws.col_values(1))  # header + rows hiện tại
    ws.append_row([
        id_moi,
        username,
        hash_pw(mat_khau),
        ho_ten,
        parse_ngay_sinh(ngay_sinh),
        "nhan_vien",
        now,
    ])
    existing_lower.add(username.lower())
    print(f"  ADDED #{id_moi}  {username} — {ho_ten}")
    added += 1

print(f"\nHoàn thành: {added} thêm mới, {skipped} bỏ qua (đã có).")
