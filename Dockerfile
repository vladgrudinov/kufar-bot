FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

COPY requirements.txt .
RUN pip install --no-cache-dir requests beautifulsoup4 python-dotenv

COPY . .

EXPOSE 8080

CMD ["python", "main_cloud.py"]
