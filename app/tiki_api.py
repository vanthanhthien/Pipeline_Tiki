import requests
import time
import config

def get_products_by_page(page):
    """Gọi API danh sách (Listing)"""
    print(f"--> Đang cào trang {page}...")
    url = config.BASE_URL.format(page=page)
    try:
        response = requests.get(url, headers=config.HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('data', [])
        else:
            print(f"❌ API Lỗi trang {page}: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ API Lỗi kết nối trang {page}: {e}")
        return []

def get_product_detail(product_id):
    """
    [MỚI] Gọi API chi tiết (Detail) để lấy all_time_quantity_sold
    """
    url = f"https://tiki.vn/api/v2/products/{product_id}"
    try:
        # Timeout quan trọng để tránh treo tool nếu mạng lag
        response = requests.get(url, headers=config.HEADERS, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            print(f"⚠️ Quá tải (429)! Nghỉ 5s...")
            time.sleep(5)
            return None
        else:
            return None
    except Exception as e:
        print(f"❌ Lỗi lấy chi tiết ID {product_id}: {e}")
        return None