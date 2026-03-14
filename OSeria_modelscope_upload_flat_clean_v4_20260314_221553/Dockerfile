FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /build

COPY Architect/frontend/package*.json /build/Architect/frontend/
COPY Runtime/frontend/package*.json /build/Runtime/frontend/

WORKDIR /build/Architect/frontend
RUN npm ci

WORKDIR /build/Runtime/frontend
RUN npm ci

WORKDIR /build
COPY Architect/frontend /build/Architect/frontend
COPY Runtime/frontend /build/Runtime/frontend

WORKDIR /build/Architect/frontend
RUN npm run build

WORKDIR /build/Runtime/frontend
RUN npm run build


FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY Architect /app/Architect
COPY Runtime /app/Runtime
COPY app.py /app/app.py
COPY start.py /app/start.py
COPY README.md /app/README.md
COPY .env.example /app/.env.example

COPY --from=frontend-builder /build/Architect/frontend/dist /app/Architect/frontend/dist
COPY --from=frontend-builder /build/Architect/frontend/public /app/Architect/frontend/public
COPY --from=frontend-builder /build/Runtime/frontend/dist /app/Runtime/frontend/dist

ENV OSERIA_PUBLIC_MODE=1

EXPOSE 7860

CMD ["python", "start.py"]
