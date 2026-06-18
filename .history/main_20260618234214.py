from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import os

# Khởi tạo ứng dụng FastAPI
app = FastAPI()

# Mount thư mục templates làm static để phục vụ CSS, JS
app.mount("/static", StaticFiles(directory="templates"), name="static")

# Chỉ định thư mục chứa file HTML
templates = Jinja2Templates(directory="templates")

# Hàm tạo cơ sở dữ liệu (Database)


def init_db():
    # Tạo file blog.db nếu chưa có
    conn = sqlite3.connect("blog.db")
    cursor = conn.cursor()

    # Tạo bảng chứa bài viết (id, tiêu đề, nội dung, ngày tháng)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            date TEXT NOT NULL
        )
    ''')

    # Kiểm tra xem có bài viết nào chưa, nếu chưa thì thêm 1 bài mẫu
    cursor.execute("SELECT COUNT(*) FROM posts")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO posts (title, content, date) VALUES (?, ?, ?)",
                       ("Khởi tạo Blog với FastAPI", "Hôm nay tôi đã dùng Python để kết nối Database!", "31/03/2026"))
        conn.commit()
    conn.close()


# Chạy hàm tạo Database ngay khi mở ứng dụng
init_db()

# Cấu hình đường dẫn trang chủ ("/")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # 1. Kết nối DB để lấy bài viết Blog
    conn = sqlite3.connect("blog.db")
    cursor = conn.cursor()
    # Lấy tiêu đề, nội dung, ngày đăng và sắp xếp bài mới nhất lên đầu
    cursor.execute("SELECT title, content, date FROM posts ORDER BY id DESC")
    posts = cursor.fetchall()  # posts lúc này là một danh sách chứa các bài viết
    conn.close()

    # 2. Gửi file HTML kèm theo dữ liệu bài viết (posts) ra ngoài
    # Gửi file HTML kèm theo dữ liệu bài viết (posts) ra ngoài (Cú pháp phiên bản mới)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"posts_data": posts}
    )
