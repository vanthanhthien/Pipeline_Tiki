import time
import psycopg2
import os
import json # <--- [MỚI] Dùng để lưu metrics dạng JSON
from datetime import datetime

class JobMonitor:
    def __init__(self, job_name, run_date):
        self.job_name = job_name
        self.run_date = run_date
        self.start_time = None
        
        # --- CẤU HÌNH KẾT NỐI DB ---
        self.db_config_docker = {
            "dbname": os.environ.get("DB_NAME", "tiki_db"),
            "user": os.environ.get("DB_USER", "admin"),
            "password": os.environ.get("DB_PASS", "admin123"),
            "host": "db",
            "port": "5432"
        }
        
        self.db_config_local = {
            "dbname": "tiki_db",
            "user": "admin",
            "password": "admin123",
            "host": "localhost",
            "port": "5434"
        }

        self.check_and_create_table()

    def get_connection(self):
        try:
            return psycopg2.connect(**self.db_config_docker)
        except psycopg2.OperationalError:
            try:
                print("⚠️ Đang chuyển sang Localhost:5434...")
                return psycopg2.connect(**self.db_config_local)
            except Exception as e:
                print(f"❌ Lỗi kết nối DB: {e}")
                return None

    def check_and_create_table(self):
        # [NÂNG CẤP] Thêm cột quality_metrics kiểu TEXT để lưu JSON
        query = """
        CREATE TABLE IF NOT EXISTS pipeline_logs (
            log_id SERIAL PRIMARY KEY,
            job_name VARCHAR(50),
            run_date DATE,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            duration_seconds FLOAT,
            records_processed INT,
            status VARCHAR(20),
            error_message TEXT,
            quality_metrics TEXT  -- <--- Cột mới chứa chỉ số sức khỏe (JSON)
        );
        """
        conn = self.get_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute(query)
                conn.commit()
                cur.close()
                conn.close()
            except Exception as e:
                print(f"⚠️ Lỗi tạo bảng: {e}")

    def start(self):
        self.start_time = time.time()
        print(f"⏱️ [MONITOR] Bắt đầu job: {self.job_name}")

    # [NÂNG CẤP] Thêm tham số `metrics` (dictionary)
    def stop(self, records_count=0, status="SUCCESS", error_msg=None, metrics=None):
        if not self.start_time: return

        end_time_ts = time.time()
        duration = round(end_time_ts - self.start_time, 2)
        start_dt = datetime.fromtimestamp(self.start_time)
        end_dt = datetime.fromtimestamp(end_time_ts)
        
        # Chuyển metrics từ Dict sang JSON String
        metrics_json = json.dumps(metrics) if metrics else None

        conn = self.get_connection()
        if conn:
            try:
                cur = conn.cursor()
                query = """
                    INSERT INTO pipeline_logs 
                    (job_name, run_date, start_time, end_time, duration_seconds, 
                     records_processed, status, error_message, quality_metrics)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cur.execute(query, (
                    self.job_name, self.run_date, start_dt, end_dt, 
                    duration, records_count, status, error_msg, metrics_json
                ))
                conn.commit()
                cur.close()
                conn.close()
                print(f"✅ [LOG SAVED] Status: {status} | Metrics: {metrics_json}")
            except Exception as e:
                print(f"❌ Lỗi ghi log: {e}")