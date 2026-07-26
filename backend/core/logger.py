import logging
import sys
import os
from logging.handlers import RotatingFileHandler

# ตรวจสอบและสร้างโฟลเดอร์ logs หากยังไม่มี
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..','storage', 'logs'))
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    
    # ป้องกันการสร้าง Log ซ้ำซ้อนหากมีการเรียกใช้ฟังก์ชันหลายครั้ง
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)

    # กำหนดรูปแบบ (Format) ของ Log
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. แสดงผลออกทางหน้าจอ (Console)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # 2. บันทึกลงไฟล์ (File) พร้อมจำกัดขนาดไฟล์ไม่เกิน 5MB (เก็บสำรอง 3 ไฟล์)
    file_path = os.path.join(LOG_DIR, "app.log")
    file_handler = RotatingFileHandler(file_path, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    file_handler.setLevel(logging.INFO) # ในไฟล์จะเก็บเฉพาะ INFO ขึ้นไป
    file_handler.setFormatter(formatter)

    # เพิ่ม Handler เข้าไปใน Logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# ทดสอบการทำงานของ Logger
if __name__ == "__main__":
    log = setup_logger("TestLogger")
    log.debug("นี่คือข้อความระดับ DEBUG (แสดงเฉพาะหน้าจอ)")
    log.info("นี่คือข้อความระดับ INFO (บันทึกลงไฟล์ด้วย)")
    log.error("นี่คือข้อความระดับ ERROR (เกิดข้อผิดพลาด!)")