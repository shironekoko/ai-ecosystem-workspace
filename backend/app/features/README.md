# 🏛️ Feature-Based Slice Architecture Documentation (`backend/app/features/`)

ซอร์สโค้ดในส่วนนี้ได้รับการออกแบบตามแนวคิด **Feature-Based Directory Structure (Vertical Slice Architecture)** โดยรวบรวมไฟล์ที่มีความเกี่ยวข้องกันทางธุรกิจ (Domain Logic) ไว้ในโมดูลเดียวกัน แทนที่จะแยกตามเลเยอร์ไฟล์แบบดั้งเดิม

---

## 🌟 ข้อดีของสถาปัตยกรรม Feature-Based

1. **High Cohesion**: โค้ดสำหรับ 1 ระบบงาน (เช่น `router`, `service`, `schemas`, `models`) รวมอยู่ในโฟลเดอร์เดียวกัน ทำให้อ่านและดูแลรักษาง่าย
2. **Low Coupling**: แต่ละ Feature ทำงานเป็นอิสระต่อกัน การแก้ไขฟีเจอร์หนึ่งจะไม่ส่งผลกระทบโดยตรงต่อฟีเจอร์อื่น
3. **Easy Scalability**: หากต้องการเพิ่มระบบใหม่ (เช่น ระบบ Dataset) สามารถสร้างโฟลเดอร์ใหม่ เช่น `app/features/dataset/` แล้วนำไปอิมพอร์ตผูกที่ `main.py` ได้ทันที

---

## 📌 รายละเอียดของแต่ละ Feature Module

### 1. `auth/` — ระบบยืนยันตัวตนและการจัดการสิทธิ์ (Authentication & Security)
* **การทำงาน**:
  - `POST /auth/signup`: ลงทะเบียนสมาชิกใหม่ ตรวจสอบ email/username ซ้ำ และแฮชรหัสผ่านด้วย `bcrypt`
  - `POST /auth/login`: ตรวจสอบรหัสผ่าน ออก **Stateless JWT Token Pair** (Access Token 30 นาที, Refresh Token 7 วัน)
  - `POST /auth/refresh`: ขอ Access Token ชุดใหม่โดยใช้ Refresh Token (Token Rotation)
  - `GET /auth/me`: อ่านข้อมูลบัญชีปัจจุบันผ่าน Dependency `get_current_active_user`

### 2. `profile/` — ระบบจัดการโปรไฟล์และรูปภาพสื่อ (Profile & Media Management)
* **การทำงาน**:
  - `GET /profile/me`: อ่านข้อมูลโปรไฟล์พร้อม Presigned URL ของรูปโปรไฟล์ล่าสุด
  - `PUT /profile/me`: อัปเดตข้อมูล `full_name` และ `bio`
  - `POST /profile/me/avatar`: อัปโหลดไฟล์รูปภาพ (JPEG, PNG, GIF, WebP ไม่เกิน 5MB) ไปยัง **MinIO Storage** และบันทึก object key ลง PostgreSQL
  - `DELETE /profile/me/avatar`: ลบรูปโปรไฟล์ออกจาก MinIO และเคลียร์ข้อมูลในฐานข้อมูล

### 3. `system/` — ระบบตรวจสอบสถานะความพร้อมโครงสร้างพื้นฐาน (System Health Check)
* **การทำงาน**:
  - `GET /system/health`: ทดสอบการเชื่อมต่อแบบ Real-time ไปยัง **PostgreSQL** (`SELECT 1`), **MinIO** (`list_buckets`), **Redis** (`PING`), และ **Label Studio** (`ls.projects.list()`)

### 4. `storage/` — ระบบจัดการวัตถุ MinIO (Object Storage API)
* **การทำงาน**:
  - `GET /storage/buckets`: ดึงรายการ Buckets ทั้งหมดในระบบ
  - `GET /storage/objects`: ดึงรายชื่อและขนาดไฟล์ใน Bucket ที่ระบุ
  - `POST /storage/presigned-url`: สร้าง Presigned URL สำหรับดาวน์โหลดไฟล์แบบกำหนดวันหมดอายุชั่วคราว

### 5. `tasks/` — ระบบจัดเก็บแคชและคิวงานประมวลผลเบื้องหลัง (Redis & ARQ Queue)
* **การทำงาน**:
  - `POST /tasks/cache` & `GET /tasks/cache/{key}`: จัดการอ่านและเขียนข้อมูล Key-Value Cache บน Redis พร้อมตั้งเวลาหมดอายุ (TTL)
  - `POST /tasks/enqueue`: ส่งคำสั่งเข้าคิวงานประมวลผลเบื้องหลัง (ARQ Task Queue)

### 6. `annotation/` — ระบบเชื่อมต่อแพลตฟอร์มติดฉลากข้อมูล (Label Studio Annotation)
* **การทำงาน**:
  - `GET /annotation/projects`: ดึงรายชื่อโครงการติดฉลากข้อมูลทั้งหมดใน Label Studio
  - `GET /annotation/projects/{project_id}/tasks`: ดึงรายการ Tasks ข้อมูลภายในโครงการที่ระบุ

---

## 🛠️ ขั้นตอนการเพิ่ม Feature ใหม่เข้าสู่ระบบ

1. สร้างโฟลเดอร์ใหม่ใต้อุปกรณ์นี้ เช่น `backend/app/features/my_feature/`
2. สร้างไฟล์ภายในโฟลเดอร์ ได้แก่ `router.py`, `service.py`, `schemas.py`, และ `models.py` (ถ้ามี)
3. นิยาม `router = APIRouter(prefix="/my-feature", tags=["My Feature"])` ใน `router.py`
4. ลงทะเบียน Router ใน `main.py`:
   ```python
   from app.features.my_feature.router import router as my_feature_router
   app.include_router(my_feature_router)
   ```
