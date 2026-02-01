import time
import os
import sys
from datetime import datetime
import database
import tiki_api
import storage

# --- CẤU HÌNH ĐƯỜNG DẪN IMPORT UTILS ---
# Vì trong Docker ta mount ./utils vào /app/utils, nên Python sẽ tìm thấy ngay
try:
    from utils.job_monitor import JobMonitor
except ImportError:
    # Fallback phòng trường hợp chạy local máy tính cá nhân
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from utils.job_monitor import JobMonitor

def run():
    # 1. KHỞI TẠO MONITOR & DB
    # Job Name trùng với Task ID trong Airflow để dễ khớp
    job_name = "1_crawl_raw_data"
    run_date = datetime.now().strftime('%Y-%m-%d')
    
    monitor = JobMonitor(job_name=job_name, run_date=run_date)
    monitor.start()

    conn = database.connect_db()
    curr = conn.cursor()
    
    # Tạo bảng nếu chưa có (Lưu ý: Upsert sẽ không làm mất dữ liệu cũ)
    database.create_table(curr)

    all_products = []
    START_PAGE = 1
    END_PAGE = 20  # Config số trang cần cào
    
    total_items_processed = 0

    print(f"🚀 [JOB: {job_name}] BẮT ĐẦU CÀO TỪ TRANG {START_PAGE} ĐẾN {END_PAGE}...")

    try:
        for page in range(START_PAGE, END_PAGE + 1):
            page_start_time = time.time()
            
            # --- BƯỚC A: LẤY DANH SÁCH ID ---
            list_products = tiki_api.get_products_by_page(page)
            if not list_products:
                print(f"⚠️ Trang {page}: Không có dữ liệu hoặc bị chặn.")
                break
            
            print(f"--> Trang {page}: Tìm thấy {len(list_products)} sản phẩm. Đang lấy chi tiết...")

            # --- BƯỚC B: LẤY CHI TIẾT (DEEP CRAWL) ---
            items_in_page = 0
            for item in list_products:
                pid = item.get('id')
                if not pid: continue

                full_info = tiki_api.get_product_detail(pid)
                
                if full_info:
                    # Logic xử lý số lượng bán
                    qty_sold = 0
                    if 'all_time_quantity_sold' in full_info:
                         qty_sold = full_info.get('all_time_quantity_sold', 0)
                    elif 'quantity_sold' in full_info and isinstance(full_info['quantity_sold'], dict):
                         qty_sold = full_info['quantity_sold'].get('value', 0)

                    # Chuẩn hóa object
                    clean_item = {
                        "id": full_info.get("id"),
                        "sku": full_info.get("sku"),
                        "name": full_info.get("name"),
                        "price": full_info.get("price"),
                        "original_price": full_info.get("original_price", 0),
                        "discount_rate": full_info.get("discount_rate", 0),
                        "rating_average": full_info.get("rating_average", 0),
                        "review_count": full_info.get("review_count", 0),
                        "inventory_status": full_info.get("inventory_status", "unknown"),
                        "all_time_quantity_sold": qty_sold, 
                        "thumbnail_url": full_info.get("thumbnail_url", ""),
                        "product_url": full_info.get("short_url", ""), 
                        "brand_name": full_info.get("brand", {}).get("name", "No Brand"),
                        "category_id": full_info.get("categories", {}).get("id")
                    }
                    
                    if not clean_item['name'] or not clean_item['price']: continue

                    all_products.append(clean_item)
                    
                    # Upsert Database
                    try:
                        database.upsert_product(curr, clean_item) 
                    except TypeError:
                        database.upsert_product(curr, clean_item)

                    items_in_page += 1
                
                # Nghỉ ngắn tránh chặn IP
                time.sleep(0.5)

            conn.commit()
            total_items_processed += items_in_page
            
            page_duration = time.time() - page_start_time
            print(f"   ✅ Xong trang {page}. Lấy được {items_in_page} món. Mất {page_duration:.2f}s")
            time.sleep(2)

        # 3. LƯU S3
        if all_products:
            timestamp = datetime.now().strftime('%H%M%S')
            filename = f"tiki_raw_{timestamp}.csv"
            
            storage.save_to_csv(all_products, filename)
            
            now = datetime.now()
            s3_path = f"bronze/tiki/year={now.year}/month={now.month:02d}/day={now.day:02d}/{filename}"
            storage.upload_to_s3(filename, s3_path)
            os.remove(filename)
            print("📦 Đã upload dữ liệu lên S3 Bronze.")
            
            # --- GHI LOG THÀNH CÔNG VÀO DB ---
            # Ghi lại tổng kết: Số trang, số sản phẩm
            metrics = {
                "pages_crawled": END_PAGE - START_PAGE + 1,
                "s3_path": s3_path
            }
            monitor.stop(records_count=total_items_processed, status="SUCCESS", metrics=metrics)
            print(f"🏁 JOB COMPLETED. Tổng sản phẩm: {total_items_processed}")
            
        else:
            print("⚠️ Không thu thập được dữ liệu nào.")
            monitor.stop(status="WARNING", error_msg="No products found")

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        # --- GHI LOG THẤT BẠI VÀO DB ---
        monitor.stop(status="FAILED", error_msg=str(e))
        raise e # Raise lỗi để Airflow biết mà báo đỏ

    finally:
        curr.close()
        conn.close()

if __name__ == "__main__":
    run()