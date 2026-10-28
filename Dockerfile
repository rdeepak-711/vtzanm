FROM node:22-slim AS web

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY data/ data/
COPY --from=web /app/frontend/dist /app/frontend/dist

EXPOSE 8000
CMD ["uvicorn", "windapp.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
