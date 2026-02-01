import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

# --- SETUP ENV ---
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(current_dir))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(current_dir), '.env'))

# --- INIT SPARK ---
spark = SparkSession.builder \
    .appName("Debug Bad Data") \
    .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.11.1026") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.access.key", os.environ.get("AWS_ACCESS_KEY_ID")) \
    .config("spark.hadoop.fs.s3a.secret.key", os.environ.get("AWS_SECRET_ACCESS_KEY")) \
    .config("spark.hadoop.fs.s3a.endpoint", "s3.ap-southeast-1.amazonaws.com") \
    .getOrCreate()

# --- ĐỌC DỮ LIỆU ---
# Lưu ý: Thay đổi ngày cho khớp với ngày bạn vừa chạy bị lỗi (VD: ngày 29 hoặc 31)
bucket = os.environ.get("AWS_BUCKET_NAME", "tiki-crawler-raw-data-thien2026")
# SỬA LẠI NGÀY Ở ĐÂY NẾU CẦN 👇
input_path = f"s3a://{bucket}/bronze/tiki/year=2026/month=01/day=29/*.csv" 

print(f"🔍 Đang điều tra dữ liệu tại: {input_path}")
try:
    df = spark.read.option("header", "true").csv(input_path)

    # Điều kiện tìm dữ liệu RÁC (Giống trong file bronze_to_silver)
    # Lỗi khi: (ID thiếu) HOẶC (Tên thiếu) HOẶC (Giá <= 0 hoặc Null)
    bad_condition = (col("id").isNull()) | (col("name").isNull()) | (col("price").cast("long") <= 0) | (col("price").isNull())

    bad_df = df.filter(bad_condition)
    
    count = bad_df.count()
    print(f"😱 PHÁT HIỆN: {count} dòng dữ liệu rác!")
    
    if count > 0:
        print("👇 Dưới đây là chân dung 'kẻ phá hoại' (Top 20):")
        # In ra các cột quan trọng để xem nó thiếu cái gì
        bad_df.select("sku", "name", "price", "original_price", "product_url").show(20, truncate=False)
    else:
        print("✅ Lạ nhỉ? Không tìm thấy dòng lỗi nào theo điều kiện này.")

except Exception as e:
    print(f"❌ Lỗi đọc file (Có thể do đường dẫn sai): {e}")

spark.stop()

