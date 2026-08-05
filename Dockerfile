FROM python:3.10-slim

WORKDIR /app

# Install compilation dependencies for psutil and telethon
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Render ana paneli varsayilan olarak app.py ile calisir. Railway'deki bagimsiz
# servisler SERVICE_ENTRYPOINT ile kendi islem dosyasini secebilir.
CMD ["sh", "-c", "python ${SERVICE_ENTRYPOINT:-app.py}"]
