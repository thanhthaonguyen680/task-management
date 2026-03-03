import toml, gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

s = toml.load(".streamlit/secrets.toml")
creds = Credentials.from_service_account_info(
    s["gcp_service_account"],
    scopes=["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
)
wb = gspread.authorize(creds).open("QuanLyCongViec")
today = datetime.now().strftime("%Y-%m-%d")

# 1. Seed LoaiMay
try:
    ws_lm = wb.worksheet("LoaiMay")
except Exception:
    ws_lm = wb.add_worksheet("LoaiMay", 100, 3)
ws_lm.clear()
loai_may_data = [
    ["ID", "Ten Loai May", "Ngay Tao"],
    [1, "Dong co AC 1Pha", today],
    [2, "Dong co AC 3Pha", today],
    [3, "Dong co DC", today],
    [4, "Mam tu", today],
]
ws_lm.update(range_name="A1", values=loai_may_data)
print("OK LoaiMay: seeded 4 items")

# 2. Seed TinhTrang (new sheet)
try:
    ws_tt = wb.worksheet("TinhTrang")
except Exception:
    ws_tt = wb.add_worksheet("TinhTrang", 100, 3)
ws_tt.clear()
tinh_trang_data = [
    ["ID", "Ten Tinh Trang", "Ngay Tao"],
    [1, "Bao hanh", today],
    [2, "Tra lai", today],
    [3, "Sua chua", today],
    [4, "Mua thanh ly", today],
    [5, "Ban may", today],
]
ws_tt.update(range_name="A1", values=tinh_trang_data)
print("OK TinhTrang: seeded 5 items")

# 3. Add columns P=Loai May, Q=Tinh Trang to Tasks header row
ws_tasks = wb.worksheet("Tasks")
r1 = ws_tasks.row_values(1)
print("Tasks current cols:", len(r1))
if "Loai May" not in r1:
    ws_tasks.update_cell(1, 16, "Loai May")
    print("Added col P = Loai May")
if "Tinh Trang" not in r1:
    ws_tasks.update_cell(1, 17, "Tinh Trang")
    print("Added col Q = Tinh Trang")

print("Done!")
