FROM node:22-alpine AS froxy-ui

WORKDIR /app/miniapp_froxy/frontend
COPY miniapp_froxy/frontend/package.json miniapp_froxy/frontend/package-lock.json ./
RUN npm ci
COPY miniapp_froxy/frontend/ ./
RUN npm run build

FROM python:3.10-slim

WORKDIR /app

RUN apt-get update -o Acquire::Retries=3 && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* || true

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=froxy-ui /app/miniapp_froxy/dist /app/miniapp_froxy/dist

EXPOSE 5000

CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 --timeout 120 --graceful-timeout 30 app:app"]
