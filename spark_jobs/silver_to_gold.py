import os
import argparse
import sys
from pyspark.sql import SparkSession
# Import thêm 'col' để nhân 2 cột với nhau
from pyspark.sql.functions import col, avg, count, desc, split, lit, sum as _sum, current_date

# --- 1. SETUP ĐƯỜNG DẪN & ENV ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(parent_dir, '.env'))

# --- LOGIC CHỌN HOST/PORT THÔNG MINH ---
if os.path.exists('/.dockerenv'):
    print("🐳 Phát hiện môi trường: DOCKER CONTAINER")
    DB_HOST = "db"
    DB_PORT = "5432"
else:
    print("💻 Phát hiện môi trường: LOCAL HOST (Windows/Mac)")
    DB_HOST = "localhost"
    DB_PORT = "5434"

DB_NAME = os.getenv("DB_NAME", "tiki_db")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "admin123")
jdbc_url = f"jdbc:postgresql://{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- 2. NHẬN THAM SỐ NGÀY ---
parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, type=str, help="Ngày cần báo cáo (YYYY-MM-DD)")
args = parser.parse_args()
process_date = args.date
year, month, day = process_date.split("-")

# --- 3. KHỞI TẠO SPARK (FIX LỖI TIMEZONE Ở ĐÂY) ---
print("⚙️ Đang cấu hình Spark với Timezone=UTC để khớp với Postgres...")
spark = SparkSession.builder \
    .appName(f"Silver to Gold - {process_date}") \
    .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.11.1026,org.postgresql:postgresql:42.2.18") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.access.key", os.environ.get("AWS_ACCESS_KEY_ID")) \
    .config("spark.hadoop.fs.s3a.secret.key", os.environ.get("AWS_SECRET_ACCESS_KEY")) \
    .config("spark.hadoop.fs.s3a.endpoint", "s3.ap-southeast-1.amazonaws.com") \
    .config("spark.driver.extraJavaOptions", "-Duser.timezone=UTC") \
    .config("spark.executor.extraJavaOptions", "-Duser.timezone=UTC") \
    .config("spark.sql.session.timeZone", "UTC") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# --- 4. XỬ LÝ DỮ LIỆU ---
BUCKET_NAME = os.environ.get("AWS_BUCKET_NAME", "tiki-crawler-raw-data-thien2026")
input_path = f"s3a://{BUCKET_NAME}/silver/tiki_products/year={year}/month={month}/day={day}"

try:
    print(f"📖 Đọc dữ liệu Silver từ: {input_path}")
    df = spark.read.parquet(input_path)

    # --- TÍNH TOÁN (ĐÃ SỬA CÔNG THỨC) ---
    report_df = df.groupBy("brand_name").agg(
        count("product_id").alias("total_products"), 
        
        # 🔥 QUAN TRỌNG: Doanh thu = Tổng (Giá x Số lượng bán)
        # Nếu quantity_sold = 0 thì Doanh thu sẽ = 0 (Đúng thực tế)
        _sum(col("price") * col("quantity_sold")).alias("total_revenue"),
        
        # Tổng số lượng bán
        _sum("quantity_sold").alias("total_sold")
    ).orderBy(desc("total_revenue"))

    # Thêm ngày báo cáo
    report_df = report_df.withColumn("report_date", current_date())

    print("👇 TOP 5 THƯƠNG HIỆU DOANH THU CAO NHẤT:")
    report_df.show(5)

    # --- LƯU XUỐNG S3 & DB ---
    output_path = f"s3a://{BUCKET_NAME}/gold/brand_report/year={year}/month={month}/day={day}"
    print(f"🥇 Lưu file Parquet xuống S3: {output_path}")
    report_df.write.mode("overwrite").parquet(output_path)

    print(f"🔌 Đang đẩy dữ liệu vào Postgres ({jdbc_url})...")
    
    db_properties = {
        "user": DB_USER,
        "password": DB_PASS,
        "driver": "org.postgresql.Driver"
    }
    
    report_df.write.jdbc(
        url=jdbc_url, 
        table="brand_report_gold", 
        mode="append", 
        properties=db_properties
    )
    print("✅ ĐÃ GHI XONG VÀO DB! (SUCCESS)")

except Exception as e:
    print(f"❌ Lỗi: {e}")
    raise e

finally:
    spark.stop()