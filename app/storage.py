import csv
import os

def save_to_csv(products, filename):
    # Định nghĩa đúng 14 cột khớp với Spark Schema trong bronze_to_silver.py
    # Thứ tự cực kỳ quan trọng!
    fieldnames = [
        "id", 
        "sku", 
        "name", 
        "price", 
        "original_price", 
        "discount_rate", 
        "rating_average", 
        "review_count", 
        "inventory_status", 
        "all_time_quantity_sold", 
        "thumbnail_url", 
        "product_url", 
        "brand_name", 
        "category_id"
    ]

    # Mở file để ghi
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        # Ghi dòng tiêu đề (Header)
        writer.writeheader()
        
        # Ghi dữ liệu
        for product in products:
            # Chuẩn hóa dữ liệu trước khi ghi để tránh lỗi thiếu trường
            row = {
                "id": product.get("id"),
                "sku": product.get("sku"),
                "name": product.get("name"),
                "price": product.get("price"),
                "original_price": product.get("original_price", 0),
                "discount_rate": product.get("discount_rate", 0),
                "rating_average": product.get("rating_average", 0),
                "review_count": product.get("review_count", 0),
                "inventory_status": product.get("inventory_status", "unknown"),
                "all_time_quantity_sold": product.get("all_time_quantity_sold", 0),
                "thumbnail_url": product.get("thumbnail_url", ""),
                "product_url": product.get("product_url", ""),
                "brand_name": product.get("brand_name", "No Brand"),
                "category_id": product.get("category_id")
            }
            writer.writerow(row)

    print(f"📄 CSV: Đã lưu {len(products)} sản phẩm vào {filename} với đủ 14 cột.")

# Hàm upload S3 giữ nguyên
def upload_to_s3(local_file, s3_path):
    import boto3
    from botocore.exceptions import NoCredentialsError
    
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION', 'ap-southeast-1')
    )
    bucket_name = os.getenv('AWS_BUCKET_NAME')
    
    try:
        s3.upload_file(local_file, bucket_name, s3_path)
        print(f"🎉 S3: Upload thành công lên {s3_path}!")
    except FileNotFoundError:
        print("❌ Lỗi: Không tìm thấy file để upload.")
    except NoCredentialsError:
        print("❌ Lỗi: Sai thông tin đăng nhập AWS.")