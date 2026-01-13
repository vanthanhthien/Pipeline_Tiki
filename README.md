tiki-data-pipeline/
│
├── .github/                # Cấu hình GitHub Actions (Ops)
│   └── workflows/
│       └── ci-cd.yml       # File quy định các bước tự động
│
├── app/                    # Code Python (Crawler)
│   ├── main.py             # Code cào dữ liệu
│   ├── requirements.txt    # Các thư viện python (pandas, requests...)
│   └── Dockerfile          # Công thức đóng gói Docker
│
├── infra/                  # Code Terraform (Infrastructure)
│   └── main.tf             # File tạo tài nguyên AWS (S3, ECR...)
│
├── .gitignore              # File chặn rác không cho lên Git
└── docker-compose.yml      # Giả lập môi trường chạy thử trên máy (Local Infra)