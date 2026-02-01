## 📖 Giới thiệu (Overview)
Dự án xây dựng một quy trình xử lý dữ liệu (Data Pipeline) hoàn chỉnh (End-to-End) theo kiến trúc **Lakehouse** để thu thập, làm sạch và phân tích dữ liệu sản phẩm từ sàn thương mại điện tử **Tiki.vn**.

**Mục tiêu:**
* Tự động hóa quy trình thu thập dữ liệu hàng ngày.
* Xây dựng kho dữ liệu tập trung (Data Warehouse).
* Trực quan hóa biến động giá, doanh thu và chất lượng sản phẩm.

---

## 🏗️ Kiến trúc hệ thống (Architecture)

### Data Flow
1.  **Ingestion:** Python Crawler thu thập dữ liệu từ API -> Lưu Raw CSV vào **S3 (Bronze Layer)**.
2.  **Processing (ETL):** Apache Spark đọc dữ liệu từ S3, làm sạch, xử lý -> Lưu Parquet vào **S3 (Silver Layer)**.
3.  **Aggregation:** Spark tổng hợp dữ liệu (Doanh thu, Top Brand...) -> Lưu vào **PostgreSQL (Gold Layer)**.
4.  **Serving:** Power BI kết nối với PostgreSQL để lên báo cáo.
5.  **Orchestration:** Apache Airflow điều phối toàn bộ pipeline.

---

## 📂 Cấu trúc dự án (Project Structure)

```bash
TIKI-DATA-PIPELINE/
├── app/                    # Source code Crawler
├── dags/                   # Airflow DAGs
├── spark_jobs/             # Các Spark Job (ETL)
│   ├── bronze_to_silver.py
│   └── silver_to_gold.py
├── utils/                  # Các module tiện ích
│   └── job_monitor.py      # Hệ thống giám sát (Monitoring)
├── docker-compose.yml      # Cấu hình hạ tầng (Infra)
├── requirements.txt        # Dependencies
├── .env.example            # Mẫu cấu hình biến môi trường
└── README.md               # Tài liệu dự án
🚀 Hướng dẫn cài đặt (Installation)
1. Yêu cầu (Prerequisites)
Docker & Docker Desktop.

Tài khoản AWS S3 (hoặc MinIO).

Python 3.9+.

2. Thiết lập biến môi trường
Dự án sử dụng biến môi trường để bảo mật thông tin. Hãy đổi tên file .env.example thành .env và điền thông tin của bạn vào:

Bash
# Copy file mẫu
cp .env.example .env
Nội dung file .env cần cấu hình:

Đoạn mã
# AWS Configuration
AWS_ACCESS_KEY_ID=<your_aws_access_key>
AWS_SECRET_ACCESS_KEY=<your_aws_secret_key>
AWS_REGION=ap-southeast-1
AWS_BUCKET_NAME=<your_s3_bucket_name>

# Database Configuration
DB_HOST=my_postgres_db
DB_NAME=tiki_db
DB_USER=<your_db_user>
DB_PASS=<your_db_password>
3. Khởi chạy hệ thống
Mở terminal tại thư mục gốc và chạy lệnh:

Bash
docker-compose up -d
Hệ thống sẽ khởi động các dịch vụ:

Airflow Webserver: localhost:8081 (Tài khoản mặc định: admin/admin)

Spark Master: localhost:8080

PostgreSQL: Port 5434 (mapped from 5432)

🛠️ Vận hành & Monitoring
Chạy Job thủ công (Local Testing)
Để test từng job Spark mà không cần đợi Airflow:

Cài đặt môi trường ảo:

Bash
pip install -r requirements.txt
Chạy Job (Ví dụ xử lý dữ liệu ngày 23/01/2026):

Bash
python spark_jobs/bronze_to_silver.py --date 2026-01-23
Giám sát hệ thống (Observability)
Dự án tích hợp module JobMonitor tự động ghi log vào bảng pipeline_logs trong PostgreSQL. Để kiểm tra hiệu suất pipeline, chạy query:

SQL
SELECT job_name, duration_seconds, status 
FROM pipeline_logs 
ORDER BY run_date DESC;
📊 Dashboard Demo
(Nơi bạn có thể chèn ảnh chụp màn hình Power BI Dashboard của bạn vào đây)

Author: Thien DE