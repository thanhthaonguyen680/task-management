import toml, gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

s = toml.load("/Users/guide/Documents/task-management/.streamlit/secrets.toml")
creds = Credentials.from_service_account_info(
    s["gcp_service_account"],
    scopes=["https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"]
)
wb = gspread.authorize(creds).open("QuanLyCongViec")
today = datetime.now().strftime("%Y-%m-%d")

# ---- LoaiMay: viet lai toan bo bang tieng Viet ----
ws_lm = wb.worksheet("LoaiMay")
ws_lm.clear()
ws_lm.update(
    range_name="A1",
    values=[
        ["ID", "T\u00ean Lo\u1ea1i M\u00e1y", "Ng\u00e0y T\u1ea1o"],
        [1,    "\u0110\u1ed9ng c\u01a1 AC 1Pha", today],
        [2,    "\u0110\u1ed9ng c\u01a1 AC 3Pha", today],
        [3,    "\u0110\u1ed9ng c\u01a1 DC",       today],
        [4,    "M\u00e2m t\u1eeb",                today],
    ]
)
print("LoaiMay row1:", ws_lm.row_values(1))

# ---- TinhTrang: viet lai toan bo bang tieng Viet ----
ws_tt = wb.worksheet("TinhTrang")
ws_tt.clear()
ws_tt.update(
    range_name="A1",
    values=[
        ["ID", "T\u00ean T\u00ecnh Tr\u1ea1ng", "Ng\u00e0y T\u1ea1o"],
        [1,    "B\u1ea3o h\u00e0nh",           today],
        [2,    "Tr\u1ea3 l\u1ea1i",             today],
        [3,    "S\u1eeda ch\u1eefa",            today],
        [4,    "Mua thanh l\u00fd",             today],
        [5,    "B\u00e1n m\u00e1y",             today],
    ]
)
print("TinhTrang row1:", ws_tt.row_values(1))

# ---- Tasks: sua cot P=Loai May, Q=Tinh Trang ----
ws_t = wb.worksheet("Tasks")
ws_t.update_cell(1, 16, "Lo\u1ea1i M\u00e1y")
ws_t.update_cell(1, 17, "T\u00ecnh Tr\u1ea1ng")
print("Tasks cols P,Q:", ws_t.row_values(1)[15:17])

print("Done!")
