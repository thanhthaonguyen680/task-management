import gspread
import toml
from google.oauth2.service_account import Credentials

secrets = toml.load(".streamlit/secrets.toml")
sa_info = secrets["gcp_service_account"]

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(sa_info, scopes=scope)
gc = gspread.authorize(creds)

sh = gc.open("QuanLyCongViec")
ws = sh.worksheet("Tasks")
row1 = ws.row_values(1)
print("Current headers count:", len(row1))
print("Last cols:", row1[-3:])

new_cols = ["Công Suất", "Số Cực", "Mã Số", "Số PO Nội Bộ", "Số PO KH/HĐ", "Số Báo Giá"]
start_col = len(row1) + 1
for i, col_name in enumerate(new_cols):
    if col_name not in row1:
        ws.update_cell(1, start_col + i, col_name)
        print(f"Added '{col_name}' at col {start_col + i}")
    else:
        print(f"'{col_name}' already exists")

row1_new = ws.row_values(1)
print("Done! Total headers:", len(row1_new))
print("Last 8:", row1_new[-8:])
