from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# Cấu hình mặc định
default_args = {
    'owner': 'thien_data_engineer',
    'start_date': datetime(2026, 1, 20), # Airflow sẽ bắt đầu chạy từ ngày này
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'tiki_automation_final', # Đổi tên DAG để Airflow refresh lại cấu hình
    default_args=default_args,
    schedule_interval='@daily', # Chạy mỗi ngày 1 lần
    catchup=False, # <--- QUAN TRỌNG: Tự động chạy bù những ngày quá khứ chưa chạy
    max_active_runs=1
    
) as dag:

    # 1. CRAWL DATA (Container Python Crawler)
    task_crawl = BashOperator(
        task_id='1_crawl_raw_data',
        # Crawler chạy, nếu lỗi thì bỏ qua (|| true) để pipeline không bị kẹt, 
        # nhưng thực tế nên để nó fail để biết mà sửa. Ở đây mình để true cho mượt luồng demo.
        bash_command='docker exec my_python_crawler python main.py || true' 
    )

    # 2. BRONZE -> SILVER (Container Spark Master)
    task_clean = BashOperator(
        task_id='2_transform_silver',
        bash_command="""
            docker exec -u 0 spark-master /opt/spark/bin/spark-submit \
            --packages org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.11.1026,org.postgresql:postgresql:42.2.18 \
            /opt/spark/jobs/bronze_to_silver.py --date {{ ds }}
        """
    )

    # 3. SILVER -> GOLD (Container Spark Master)
    # Task mới thêm vào: Tính toán báo cáo và đẩy vào Postgres
    task_report = BashOperator(
        task_id='3_create_report_gold',
        bash_command="""
            docker exec -u 0 spark-master /opt/spark/bin/spark-submit \
            --packages org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.11.1026,org.postgresql:postgresql:42.2.18 \
            /opt/spark/jobs/silver_to_gold.py --date {{ ds }}
        """
    )

    # Thiết lập thứ tự: Crawl xong -> Làm sạch -> Lên báo cáo
    task_crawl >> task_clean >> task_report