# worker_settings.py
import asyncio
from arq import Worker

# ฟังก์ชันที่จะรับข้อมูล (Job data) มาแสดงผล
async def simple_work(ctx, job_data):
    print(f"📦 [Job ID: {ctx['job_id']}] กำลังประมวลผลข้อมูล: {job_data}")
    await asyncio.sleep(2) 
    print(f"✅ งานเสร็จสมบูรณ์!")
    return f"Success: {job_data}"

# การตั้งค่าสำหรับ ARQ Worker
class WorkerSettings:
    functions = [simple_work]