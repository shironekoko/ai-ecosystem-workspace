#!/bin/bash
# ─────────────────────────────────────────────
# PostgreSQL Init Script — สร้าง Database เพิ่มเติม
# ─────────────────────────────────────────────
# Script นี้จะรันอัตโนมัติครั้งเดียวเมื่อ PostgreSQL Container เริ่มต้นครั้งแรก
# (ถ้า Volume มีข้อมูลอยู่แล้ว จะไม่รันซ้ำ)

set -e

echo "🔧 Creating additional databases..."

# สร้าง Database สำหรับ MLflow (Backend Store สำหรับ Experiment Tracking)
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE mlflow_db;
    GRANT ALL PRIVILEGES ON DATABASE mlflow_db TO $POSTGRES_USER;
EOSQL

echo "✅ Database 'mlflow_db' created successfully"
