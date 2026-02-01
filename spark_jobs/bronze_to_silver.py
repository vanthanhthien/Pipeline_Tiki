import os
import argparse
import sys
from dotenv import load_dotenv

# --- SETUP ĐƯỜNG DẪN MONITOR TRONG DOCKER ---
# Trong docker-compose, ta mount ./utils vào /opt/spark/utils
sys.path.append("/opt/spark")

# Setup đường dẫn import module nội bộ
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
load_dotenv(os.path.join(parent_dir, '.env'))

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, avg, count, when
from pyspark.sql.types import StructType, StructField, LongType, StringType, DoubleType, IntegerType

# Import JobMonitor (Cần đảm bảo file utils/job_monitor.py đã tồn tại)
try:
    from utils.job_monitor import JobMonitor
except ImportError:
    print("⚠️ Không tìm thấy module utils.job_monitor. Chạy chế độ không log DB.")
    JobMonitor = None # Fallback nếu chạy local không đúng cấu trúc

# --- CẤU HÌNH ---
MAX_ERROR_RATE = 0.2 

# 1. PARSE ARGUMENTS
parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, type=str)
args = parser.parse_args()
process_date = args.date
year, month, day = process_date.split("-")

# 2. START MONITOR
monitor = None
if JobMonitor:
    monitor = JobMonitor(job_name="2_transform_silver", run_date=process_date)
    monitor.start()

# 3. INIT SPARK
print(f"⚙️ Khởi động Spark xử lý ngày: {process_date}")
spark = SparkSession.builder \
    .appName(f"Bronze to Silver - {process_date}") \
    .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.11.1026,org.postgresql:postgresql:42.2.18") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.access.key", os.environ.get("AWS_ACCESS_KEY_ID")) \
    .config("spark.hadoop.fs.s3a.secret.key", os.environ.get("AWS_SECRET_ACCESS_KEY")) \
    .config("spark.hadoop.fs.s3a.endpoint", "s3.ap-southeast-1.amazonaws.com") \
    .getOrCreate()
spark.sparkContext.setLogLevel("WARN")

# 4. SCHEMA DEFINITION (Phải chuẩn từng cột)
bronze_schema = StructType([
    StructField("id", LongType(), True),
    StructField("sku", StringType(), True),
    StructField("name", StringType(), True),
    StructField("price", LongType(), True),
    StructField("original_price", LongType(), True),
    StructField("discount_rate", IntegerType(), True),
    StructField("rating_average", DoubleType(), True),
    StructField("review_count", IntegerType(), True),
    StructField("inventory_status", StringType(), True),
    StructField("all_time_quantity_sold", LongType(), True), # Cột quan trọng
    StructField("thumbnail_url", StringType(), True),
    StructField("product_url", StringType(), True),
    StructField("brand_name", StringType(), True),
    StructField("category_id", LongType(), True)
])

BUCKET_NAME = os.environ.get("AWS_BUCKET_NAME", "tiki-crawler-raw-data-thien2026")
input_path = f"s3a://{BUCKET_NAME}/bronze/tiki/year={year}/month={month}/day={day}/*.csv"
output_path = f"s3a://{BUCKET_NAME}/silver/tiki_products/"

try:
    print(f"🚀 [STEP 1] Đọc dữ liệu Raw: {input_path}")
    df_raw = spark.read.option("header", "true").schema(bronze_schema).csv(input_path)
    
    # Cache để tối ưu hiệu năng tính toán
    df_raw.cache()
    
    total_raw_rows = df_raw.count()
    print(f"📊 Tổng số dòng Raw: {total_raw_rows}")

    if total_raw_rows == 0:
        raise ValueError("❌ Không có dữ liệu đầu vào (File rỗng)!")

    # --- DATA QUALITY CHECK ---
    print("🔍 [STEP 2] Kiểm tra chất lượng dữ liệu...")
    clean_condition = (col("id").isNotNull()) & (col("name").isNotNull()) & (col("price") > 0)
    
    df_clean = df_raw.filter(clean_condition)
    valid_rows = df_clean.count()
    error_rows = total_raw_rows - valid_rows
    error_rate = error_rows / total_raw_rows if total_raw_rows > 0 else 0

    metrics = {
        "total_input": total_raw_rows,
        "valid_output": valid_rows,
        "error_rows": error_rows,
        "error_rate": round(error_rate, 4)
    }
    
    print(f"📉 Tỷ lệ lỗi: {error_rate * 100:.2f}% (Ngưỡng: {MAX_ERROR_RATE * 100}%)")

    if error_rate > MAX_ERROR_RATE:
        error_msg = f"⛔ CHẶN JOB: Tỷ lệ lỗi quá cao ({error_rate:.2%})"
        if monitor:
            monitor.stop(records_count=valid_rows, status="FAILED", error_msg=error_msg, metrics=metrics)
        raise ValueError(error_msg)

    # --- TRANSFORMATION ---
    print("✅ [STEP 3] Chuẩn hóa dữ liệu...")
    df_final = df_clean.select(
        col("id").alias("product_id"),
        col("name"),
        col("price"),
        col("original_price"),
        col("discount_rate"),
        col("rating_average"),
        col("review_count"),
        col("all_time_quantity_sold").alias("quantity_sold"),
        col("thumbnail_url"),
        col("brand_name"),
        lit(process_date).alias("crawled_at")
    ).na.fill({"quantity_sold": 0})

    final_path = f"{output_path}/year={year}/month={month}/day={day}"
    print(f"💾 [STEP 4] Lưu Parquet: {final_path}")
    df_final.write.mode("overwrite").parquet(final_path)

    # --- SUCCESS LOG ---
    if monitor:
        monitor.stop(records_count=valid_rows, status="SUCCESS", metrics=metrics)
    print("🎉 BRONZE TO SILVER SUCCESS!")

except Exception as e:
    print(f"❌ ERROR: {e}")
    if monitor:
        monitor.stop(status="FAILED", error_msg=str(e))
    raise e

finally:
    spark.stop()