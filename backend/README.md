# ⚙️ Backend Core Application Documentation

บริการส่วนหลัง (Backend Application) สร้างขึ้นด้วย **FastAPI** บนระบบปฏิบัติการ **Python 3.12+** โดยใช้ **`uv`** เป็นเครื่องมือจัดการ Virtual Environment และ Dependencies เพื่อความรวดเร็วและเป็นระเบียบ

---

## 📁 โครงสร้างโฟลเดอร์หลัก (Directory Structure)

```text
backend/
├── app/
│   └── features/          # โครงสร้างแบบ Feature-Based Slices (Domain Modules)
│       ├── auth/          # ระบบยืนยันตัวตน (Sign-up, Login, JWT Token Rotation)
│       ├── profile/       # ระบบจัดการโปรไฟล์ & อัปโหลดรูปภาพผ่าน MinIO
│       ├── storage/       # API จัดการ MinIO Object Storage (Buckets, Objects, Presigned URL)
│       ├── system/        # API ตรวจสอบความพร้อมของระบบ (System Health Check)
│       ├── tasks/         # API จัดการ Redis Cache & คิวงานประมวลผล ARQ Background Worker
│       └── annotation/    # API เชื่อมต่อแพลตฟอร์ม Label Studio Data Labeling
├── core/                  # ส่วนประกอบร่วมกลางของระบบ (Shared Infrastructure)
│   ├── config.py          # อ่านและตรวจสอบค่า Environment Variables (.env) ผ่าน pydantic-settings
│   ├── database.py        # SQLAlchemy Engine & Session Factory (get_db)
│   ├── minio_client.py    # Wrapper Functions สำหรับสั่งงาน MinIO Object Storage
│   └── logger.py          # ระบบบันทึก Log การทำงานของเซิร์ฟเวอร์
├── sandbox/               # สคริปต์ทดสอบการเชื่อมต่อเฉพาะส่วน (Integration & Unit Tests)
├── storage/
│   ├── artifacts/         # ที่เก็บบันทึกไฟล์ Snapshot (api_snapshot.csv, openapi_snapshot.json)
│   └── logs/              # ที่เก็บไฟล์ Log ย้อนหลัง
├── utils/
│   └── export_api_snapshot.py # สคริปต์สกัด OpenAPI Schema เป็น CSV / JSON Snapshot
├── main.py                # Entrypoint หลักของ FastAPI Application
├── worker_settings.py     # การตั้งค่าสำหรับรัน ARQ Background Worker
└── pyproject.toml         # การระบุ Dependencies ของโปรเจกต์
```

---

## 🛠️ การติดตั้งและคำสั่งสำคัญ (Essential Commands)

### 1. ติดตั้ง Dependencies (Sync Dependencies)
```bash
uv sync
```

### 2. รันเซิร์ฟเวอร์พัฒนา (Run Development Server)
```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. รัน Background Worker (Run ARQ Worker)
```bash
uv run arq worker_settings.WorkerSettings
```

### 4. สกัดและส่งออก API List Snapshot เป็น CSV / JSON (Export API Snapshot)
```bash
uv run python utils/export_api_snapshot.py
```
*(ไฟล์ที่สกัดได้จะถูกนำไปบันทึกไว้ที่ `storage/artifacts/api_snapshot.csv` ในรูปแบบ **UTF-8-SIG** เปิดใน Microsoft Excel ได้ภาษาไทยไม่เพี้ยน)*

---

## 🔗 ลิงก์ไปยังเอกสารกำกับแต่ละส่วน (Sub-directory Readmes)

- 📘 [**`core/README.md`**](core/README.md): รายละเอียดโมดูลโครงสร้างพื้นฐานหลัก (`config`, `database`, `minio_client`)
- 📙 [**`app/features/README.md`**](app/features/README.md): รายละเอียดสถาปัตยกรรมแบบ Feature-Based และ Endpoint ในแต่ละโมดูล
- 📕 [**`sandbox/README.md`**](sandbox/README.md): รายละเอียดสคริปต์สำหรับทดสอบการสื่อสารกับ Docker Services
