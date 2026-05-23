FROM python:3.9-slim

WORKDIR /app

COPY recommendation-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY recommendation-service/ .
COPY image/recommended_image/ /app/images/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
