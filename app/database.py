import psycopg2
import time
import config

def connect_db():
    print("⏳ DB: Đang kết nối...")
    while True:
        try:
            conn = psycopg2.connect(
                host=config.DB_HOST,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASS
            )
            print("✅ DB: Kết nối thành công!")
            return conn
        except Exception as e:
            print(f"⚠️ DB: Đang chờ... Lỗi: {e}")
            time.sleep(3)

def create_table(curr):
    # XÓA BẢNG CŨ ĐỂ CẬP NHẬT CỘT MỚI (Làm mới dữ liệu)
    curr.execute("DROP TABLE IF EXISTS tiki_products CASCADE;")
    
    query = """
    CREATE TABLE IF NOT EXISTS tiki_products (
        id SERIAL PRIMARY KEY,
        product_id BIGINT UNIQUE,
        sku TEXT,
        name TEXT,
        price BIGINT,
        original_price BIGINT,
        discount_rate INT,
        rating_average REAL,
        review_count INT,
        inventory_status TEXT,
        all_time_quantity_sold BIGINT, -- CỘT QUAN TRỌNG NHẤT
        brand_name TEXT,
        category_id INT,
        thumbnail_url TEXT,
        product_url TEXT,
        crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    curr.execute(query)

def upsert_product(curr, item):
    """Lưu 14 trường thông tin"""
    sql = """
    INSERT INTO tiki_products (
        product_id, sku, name, price, original_price, discount_rate, 
        rating_average, review_count, inventory_status, all_time_quantity_sold, 
        brand_name, category_id, thumbnail_url, product_url
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (product_id) DO UPDATE SET 
        price = EXCLUDED.price, 
        all_time_quantity_sold = EXCLUDED.all_time_quantity_sold,
        crawled_at = CURRENT_TIMESTAMP;
    """
    
    # Map dữ liệu từ dict vào SQL (Thứ tự phải khớp với VALUES ở trên)
    curr.execute(sql, (
        item.get('id'),
        item.get('sku'),
        item.get('name'),
        item.get('price'),
        item.get('original_price', 0),
        item.get('discount_rate', 0),
        item.get('rating_average', 0),
        item.get('review_count', 0),
        item.get('inventory_status', 'unknown'),
        item.get('all_time_quantity_sold', 0), # Số lượng bán
        item.get('brand_name', 'No Brand'),
        item.get('category_id'),
        item.get('thumbnail_url'),
        item.get('product_url')
    ))