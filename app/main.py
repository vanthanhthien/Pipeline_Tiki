import requests
import psycopg2
import time
import os
import json
from datetime import datetime

# --- CẤU HÌNH BẢO MẬT ---
# Lấy trực tiếp từ biến môi trường. 
# Tuyệt đối không để giá trị mặc định (như 'admin123') ở tham số thứ 2.
DB_HOST = os.environ.get('DB_HOST')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASS = os.environ.get('DB_PASS')

# Kiểm tra an toàn: Nếu thiếu biến nào thì dừng ngay lập tức
if not all([DB_HOST, DB_NAME, DB_USER, DB_PASS]):
    print("❌ LỖI BẢO MẬT: Thiếu biến môi trường! Hãy kiểm tra file .env và docker-compose.yml")
    exit(1)

# Cấu hình Tiki API
TIKI_URL = "https://tiki.vn/api/personalish/v1/blocks/listings?limit=40&include=advertisement&aggregations=2&version=home-persionalized&trackity_id=739e5590-7f53-8390-1b77-245c364c6762&category=1789&page=1&urlKey=dien-thoai-may-tinh-bang"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://tiki.vn/'
}

def connect_db():
    print("⏳ DOCKER: Đang kết nối Database...")
    while True:
        try:
            conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
            print("✅ Kết nối Database thành công!")
            return conn
        except Exception as e:
            print(f"⚠️ Đang chờ Database khởi động... Lỗi: {e}")
            time.sleep(3)

def create_table(curr):
    query = """
    CREATE TABLE IF NOT EXISTS tiki_products (
        id SERIAL PRIMARY KEY,
        product_id BIGINT UNIQUE,
        name TEXT,
        price INT,
        discount_rate INT,
        rating_average REAL,
        review_count INT,
        thumbnail_url TEXT,
        product_url TEXT,
        crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    curr.execute(query)
    print("✅ Đã kiểm tra bảng 'tiki_products'.")

def crawl_and_save():
    conn = connect_db()
    curr = conn.cursor()
    create_table(curr)

    print(f"🚀 Bắt đầu cào dữ liệu từ Tiki API...")
    
    try:
        response = requests.get(TIKI_URL, headers=HEADERS)
        
        if response.status_code == 200:
            data = response.json()
            products = data.get('data', [])
            print(f"📦 Đã tìm thấy {len(products)} sản phẩm. Đang lưu vào DB...")

            inserted_count = 0
            for item in products:
                p_id = item.get('id')
                name = item.get('name')
                price = item.get('price')
                discount = item.get('discount_rate', 0)
                rating = item.get('rating_average', 0)
                reviews = item.get('review_count', 0)
                thumb = item.get('thumbnail_url')
                p_url = f"https://tiki.vn/{item.get('url_path')}"

                sql = """
                INSERT INTO tiki_products (product_id, name, price, discount_rate, rating_average, review_count, thumbnail_url, product_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (product_id) 
                DO UPDATE SET price = EXCLUDED.price, crawled_at = CURRENT_TIMESTAMP;
                """
                curr.execute(sql, (p_id, name, price, discount, rating, reviews, thumb, p_url))
                inserted_count += 1
            
            conn.commit()
            print(f"🎉 THÀNH CÔNG! Đã lưu/cập nhật {inserted_count} sản phẩm vào Postgres.")
        else:
            print(f"❌ Lỗi khi gọi API Tiki: {response.status_code}")

    except Exception as e:
        print(f"❌ Có lỗi xảy ra: {e}")
    finally:
        curr.close()
        conn.close()

if __name__ == "__main__":
    crawl_and_save()