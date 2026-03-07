import toml, gspread
from google.oauth2.service_account import Credentials

secrets = toml.load(".streamlit/secrets.toml")
creds = Credentials.from_service_account_info(
    secrets["gcp_service_account"],
    scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(creds)
ws = gc.open("QuanLyCongViec").worksheet("Tasks")

# Đọc toàn bộ kể cả hàng trống
all_rows = ws.get("A1:W50")
print(f"Total rows fetched: {len(all_rows)}")
for i, r in enumerate(all_rows):
    col_a = r[0] if r else "(empty)"
    col_e = r[4] if len(r) > 4 else ""
    col_g = r[6] if len(r) > 6 else ""
    print(f"  Row {i+1:3}: ID={str(col_a):6} | Task={str(col_e):30} | NV={col_g}")
