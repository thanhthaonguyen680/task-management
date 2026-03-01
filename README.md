# 📋 Ứng Dụng Quản Lý Công Việc

Web app xây dựng bằng **Streamlit** (Python), tích hợp **Google Sheets**, **Cloudinary** và xuất **PDF nghiệm thu**.

---

## ✨ Tính Năng

| Tính năng | Mô tả |
|---|---|
| 🔧 **Admin** | Tạo task mới, giao việc cho nhân viên, xem tổng quan |
| 👤 **Nhân viên** | Chọn tên, xem task, cập nhật trạng thái (Todo → Doing → Done) |
| 📸 **Upload ảnh** | Khi Done, upload ảnh nghiệm thu lên Cloudinary, lưu URL vào Google Sheets |
| 📄 **Xuất PDF** | Tạo biên bản nghiệm thu có tiêu đề công ty, thông tin task, ảnh nghiệm thu |

---

## 📁 Cấu Trúc Dự Án

```
QuanLyCongViec/
├── app.py                    # File chính của ứng dụng
├── requirements.txt          # Danh sách thư viện Python
├── .gitignore
└── .streamlit/
    └── secrets.toml          # Cấu hình bí mật (KHÔNG commit lên Git)
```

---

## 🚀 Hướng Dẫn Cài Đặt

### Bước 1: Cài đặt thư viện Python

```bash
pip install -r requirements.txt
```

### Bước 2: Tạo Google Sheets

1. Đăng nhập Google Drive, tạo Spreadsheet tên: **`QuanLyCongViec`**
2. Tạo sheet tên **`Tasks`** với các cột ở hàng đầu tiên:

| A  | B         | C           | D           | E      | F            | G        | H         |
|----|-----------|-------------|-------------|--------|--------------|----------|-----------|
| ID | Task_Name | Description | Assigned_To | Status | Created_Date | Deadline | Image_URL |

### Bước 3: Tạo Google Cloud Service Account

1. Vào [Google Cloud Console](https://console.cloud.google.com)
2. Tạo project mới (hoặc dùng project có sẵn)
3. Bật 2 API:
   - **Google Sheets API**
   - **Google Drive API**
4. Vào **IAM & Admin** → **Service Accounts** → **Create Service Account**
5. Tạo Key → chọn **JSON** → tải file `.json` về
6. **Chia sẻ** file Google Sheets với email service account (`...@...iam.gserviceaccount.com`) quyền **Editor**

### Bước 4: Tạo tài khoản Cloudinary

1. Đăng ký tại [cloudinary.com](https://cloudinary.com) (miễn phí)
2. Vào **Dashboard** → lấy: `Cloud Name`, `API Key`, `API Secret`

### Bước 5: Cấu hình Secrets

Mở file `.streamlit/secrets.toml` và điền đầy đủ thông tin:

```toml
[gcp_service_account]
type            = "service_account"
project_id      = "your-project-id"
private_key_id  = "..."
private_key     = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
client_email    = "your-sa@your-project.iam.gserviceaccount.com"
# ... (copy từ file JSON đã tải)

[cloudinary]
cloud_name = "your-cloud-name"
api_key    = "123456789012345"
api_secret = "your-api-secret"
```

### Bước 6: Chạy ứng dụng

```bash
streamlit run app.py
```

Mở trình duyệt: **http://localhost:8501**

---

## 🔐 Lưu Ý Bảo Mật

- **Không** commit file `.streamlit/secrets.toml` lên GitHub
- Thêm vào `.gitignore`:
  ```
  .streamlit/secrets.toml
  ```
- Khi deploy lên [Streamlit Community Cloud](https://streamlit.io/cloud), nhập secrets vào mục **App Settings → Secrets**

---

## 🌐 Deploy Lên Streamlit Cloud

1. Push code lên GitHub (đảm bảo `secrets.toml` đã được gitignore)
2. Vào [share.streamlit.io](https://share.streamlit.io)
3. Chọn repo → `app.py` → Deploy
4. Vào **Settings → Secrets** → paste nội dung `secrets.toml`

---

## 📦 Thư Viện Sử Dụng

| Thư viện | Mục đích |
|---|---|
| `streamlit` | Giao diện web |
| `gspread` | Kết nối Google Sheets |
| `google-auth` | Xác thực Google Service Account |
| `cloudinary` | Upload & lưu trữ ảnh |
| `fpdf2` | Tạo file PDF |
| `pandas` | Xử lý dữ liệu dạng bảng |
| `requests` | Tải ảnh từ URL về để chèn PDF |
