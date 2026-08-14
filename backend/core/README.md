# 🧩 Core Component Documentation (`backend/core/`)

โฟลเดอร์ **`core/`** ทำหน้าที่เป็นศูนย์รวมโมดูลโครงสร้างพื้นฐานกลาง (Shared Infrastructure & Core Utilities) ที่ทุกฟีเจอร์ในระบบนำไปใช้ร่วมกัน เพื่อหลีกเลี่ยงการเขียนโค้ดซ้ำซ้อน (DRY Principle)

---

## 🛠️ รายละเอียดไฟล์ประกอบในโมดูล `core/`

### 1. `config.py` — การจัดการค่าคอนฟิกของแอปพลิเคชัน
* **เทคโนโลยีที่ใช้**: `pydantic-settings`
* **หน้าที่**:
  - อ่านค่าตัวแปรสภาพแวดล้อม (Environment Variables) จากไฟล์ `.env` ที่ root หรือโฟลเดอร์ backend
  - กำหนดค่าเริ่มต้นและตรวจสอบประเภทข้อมูล (Data Validation) ของการตั้งค่าต่างๆ เช่น `database_url`, `minio_endpoint`, `redis_url`, `jwt_secret_key`
  - ทำหน้าที่เป็น Singleton Instance (`settings`) ที่นำไปเรียกใช้ได้ทันทีทั่วทั้งแอปพลิเคชัน

### 2. `database.py` — บริการเชื่อมต่อฐานข้อมูล PostgreSQL
* **เทคโนโลยีที่ใช้**: `sqlalchemy` (ORM)
* **หน้าที่**:
  - สร้าง SQLAlchemy Engine ร่วมกับ `pool_pre_ping=True` เพื่อความเสถียรของการเชื่อมต่อ
  - นิยาม `SessionLocal` สำหรับทำ Database Transaction
  - ประกาศ `Base` Class สำหรับนำไปสืบทอดเป็น ORM Models
  - ให้บริการ **FastAPI Dependency Injection**: `get_db()` เพื่อสร้าง Session ต่อ 1 HTTP Request และสั่งปิด Connection อัตโนมัติในบล็อก `finally`

### 3. `minio_client.py` — ตัวเชื่อมต่อและจัดการไฟล์ใน MinIO Object Storage
* **เทคโนโลยีที่ใช้**: `minio` (MinIO Python SDK)
* **หน้าที่**:
  - ให้บริการฟังก์ชัน `get_minio_client()` เพื่อรับวัตถุ Client สำหรับโต้ตอบกับ MinIO S3 API
  - ฟังก์ชัน `ensure_bucket(bucket_name)`: ตรวจสอบและสร้าง Bucket อัตโนมัติหากยังไม่มีในระบบ
  - ฟังก์ชัน `upload_file()` & `download_file()`: อัปโหลดและดาวน์โหลดไฟล์ไบนารี
  - ฟังก์ชัน `get_presigned_url(bucket, object, expires)`: สร้างลิงก์ดาวน์โหลดไฟล์แบบกำหนดวันหมดอายุชั่วคราว
  - ฟังก์ชัน `list_objects()` & `delete_object()`: บริหารจัดการไฟล์ใน Bucket

### 4. `logger.py` — ระบบบันทึก Log การทำงาน
* **หน้าที่**:
  - กำหนดรูปแบบของ Log (Log Formatter) เพื่อการติดตามสถานะการทำงาน (Debugging & Auditing)
  - รองรับการบันทึกทั้งบน Terminal Console และบันทึกลงไฟล์ใน `storage/logs/`

### 5. `worker_settings.py` — การตั้งค่าสำหรับ ARQ Background Worker
* **เทคโนโลยีที่ใช้**: `arq` & `redis`
* **หน้าที่**:
  - อ่านคอนฟิกการเชื่อมต่อ Redis จาก `settings.redis_url`
  - กำหนดรายชื่อฟังก์ชันงานประมวลผลเบื้องหลัง (Background Worker Functions) เช่น `simple_work`
  - ใช้เป็นเป้าหมายอ้างอิงเมื่อรันคำสั่ง:
    ```bash
    uv run arq worker_settings.WorkerSettings
    ```
