from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import httpx
import os
import time

# Khởi tạo ứng dụng FastAPI
app = FastAPI()

# Mount thư mục templates làm static để phục vụ CSS, JS
app.mount("/static", StaticFiles(directory="templates"), name="static")

# Chỉ định thư mục chứa file HTML
templates = Jinja2Templates(directory="templates")

# GitHub username
GITHUB_USERNAME = "Tram-anh99"

# Cache cho GitHub API (giảm số lần gọi API)
_repos_cache = {"data": None, "timestamp": 0}
CACHE_TTL = 300  # Cache 5 phút


# Hàm lấy danh sách repo từ GitHub API (có cache)
async def fetch_github_repos():
    """Lấy danh sách repo từ GitHub API, chỉ lấy repo không phải fork. Cache 5 phút."""
    now = time.time()
    # Nếu cache còn hạn thì trả về luôn
    if _repos_cache["data"] is not None and (now - _repos_cache["timestamp"]) < CACHE_TTL:
        return _repos_cache["data"]

    url = f"https://api.github.com/users/{GITHUB_USERNAME}/repos?per_page=100&sort=updated"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                url,
                headers={"Accept": "application/vnd.github.v3+json"}
            )
            if response.status_code == 200:
                repos = response.json()
                result = []
                for repo in repos:
                    if not repo.get("fork", False):
                        # Tự động phát hiện demo URL
                        homepage = repo.get("homepage", "") or ""
                        has_pages = repo.get("has_pages", False)
                        repo_name = repo.get("name", "")

                        # Ưu tiên homepage, nếu không có thì kiểm tra GitHub Pages
                        demo_url = ""
                        if homepage:
                            demo_url = homepage
                        elif has_pages:
                            demo_url = f"https://{GITHUB_USERNAME}.github.io/{repo_name}/"

                        result.append({
                            "name": repo_name,
                            "full_name": repo.get("full_name", ""),
                            "description": repo.get("description", "") or "Không có mô tả",
                            "html_url": repo.get("html_url", "#"),
                            "language": repo.get("language", "") or "N/A",
                            "topics": repo.get("topics", []),
                            "updated_at": repo.get("updated_at", ""),
                            "homepage": homepage,
                            "demo_url": demo_url,
                        })
                result.sort(key=lambda x: x["updated_at"], reverse=True)
                # Lưu vào cache
                _repos_cache["data"] = result
                _repos_cache["timestamp"] = now
                return result
    except Exception as e:
        print(f"Lỗi khi lấy repos từ GitHub: {e}")
    # Nếu lỗi mà có cache cũ thì dùng cache cũ
    return _repos_cache["data"] or []


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
    cursor.execute("SELECT title, content, date FROM posts ORDER BY id DESC")
    posts = cursor.fetchall()
    conn.close()

    # 2. Lấy danh sách repo từ GitHub
    repos = await fetch_github_repos()

    # 3. Gửi file HTML kèm theo dữ liệu bài viết và repo
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"posts_data": posts, "repos_data": repos}
    )
