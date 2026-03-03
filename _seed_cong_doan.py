"""Script: xóa dữ liệu cũ CongDoan, thêm 8 công đoạn chuẩn, thêm cột O Tasks."""
import toml
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

secrets = toml.load(".streamlit/secrets.toml")
creds = Credentials.from_service_account_info(
    secrets["gcp_service_account"],
    scopes=[
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ],
)
client = gspread.authorize(creds)
wb = client.open("QuanLyCongViec")

# ── 1. Xóa cũ + thêm 8 công đoạn chuẩn ──────────────────────────────────────
ws_cd = wb.worksheet("CongDoan")
ws_cd.clear()

CONG_DOAN_CHUAN = [
    "Nhận máy", "Lên đơn", "Tháo máy", "Đục máy",
    "Quấn dây", "Vô dây", "Đai đầu", "Lắp máy",
]
today = datetime.now().strftime("%Y-%m-%d")

# Batch write toàn bộ header + data trong 1 lần gọi duy nhất
all_rows = [["ID", "Tên Công Đoạn", "Ngày Tạo"]] + \
           [[idx, ten, today] for idx, ten in enumerate(CONG_DOAN_CHUAN, start=1)]
ws_cd.update(range_name="A1", values=all_rows)

print(f"OK CongDoan: da xoa cu va them {len(CONG_DOAN_CHUAN)} cong doan chuan")
print("  =>", CONG_DOAN_CHUAN)

# ── 2. Thêm header "Công Đoạn" cột O vào Tasks ───────────────────────────────
ws_tasks = wb.worksheet("Tasks")
row1 = ws_tasks.row_values(1)
print(f"\nTasks row1 hien tai ({len(row1)} cot): {row1}")

if "Công Đoạn" not in row1:
    ws_tasks.update_cell(1, 15, "Công Đoạn")
    print("OK Tasks: da them cot O1 = 'Cong Doan'")
else:
    print("OK Tasks: cot 'Cong Doan' da ton tai tai vi tri", row1.index("Công Đoạn") + 1)

print("\nHoan tat!")
