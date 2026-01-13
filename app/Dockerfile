From python:3.11-slim

WORKDIR /app
copy requirements.txt .

#update python khi cần
Run pip install --upgrade pip &&\
    pip install --no-cache-dir -r requirements.txt

Copy . .

CMD ["python", "main.py"]