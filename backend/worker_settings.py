import asyncio
from arq.connections import RedisSettings
from core.config import settings

async def simple_work(ctx, job_data: str):
    print("👷 [Worker] เริ่มทำงาน...")
    print(f"📦 ข้อมูลที่ได้รับ (Job Data): {job_data}")
    
    await asyncio.sleep(2)
    
    print("✅ ทำงานเสร็จสมบูรณ์!\n")
    return f"Success: {job_data}"

# 🛠️ แก้ไขบรรทัดนี้: ใช้ from_dsn เพื่ออ่านจาก redis_url แทน
redis_settings = RedisSettings.from_dsn(settings.redis_url)

class WorkerSettings:
    functions = [simple_work]
    redis_settings = redis_settings