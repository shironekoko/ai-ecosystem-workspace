# 🤖 Trainer Worker — Token Classification Training Service

โฟลเดอร์นี้คือ **Trainer Worker** ซึ่งเป็น Docker Container แยกต่างหาก รับผิดชอบการเทรน ML Model ในพื้นหลัง (Background) โดยใช้ GPU และทำงานผ่าน ARQ Task Queue ที่รับงานมาจาก FastAPI

---

## โครงสร้างไฟล์

```
trainer/
├── Dockerfile                      ← GPU-enabled Container (pytorch/pytorch base image)
├── requirements.txt                ← Python dependencies (transformers, datasets, minio, arq)
├── worker.py                       ← ARQ Worker Entry Point (WorkerSettings)
└── tasks/
    ├── __init__.py
    ├── minio_utils.py              ← Upload/Download Dataset & Model ระหว่าง Container และ MinIO
    └── train_token_classifier.py   ← Training Logic หลัก (Token Classification)
```

---

## สิ่งที่ Trainer Worker ทำ (Flow ครบ)

```
1. รอรับ Job จาก Redis Queue (ผ่าน ARQ)
2. เมื่อถึงเวลาที่กำหนด (Scheduled Time) → เริ่มทำงาน
3. โหลด Dataset (Parquet) จาก MinIO bucket: datasets/
4. Load Tokenizer + Model จาก HuggingFace (distilbert-base-uncased)
5. Tokenize + Align Labels กับ Subwords (ตาม HuggingFace Chapter 7)
6. เทรนด้วย HuggingFace Trainer API (รองรับ GPU)
7. บันทึก Training Log → MinIO bucket: training-logs/{job_id}/
8. บันทึก Model → MinIO bucket: models/{job_id}/
```

---

## Token Classification (Token ตาม HuggingFace Chapter 7)

อ้างอิง: https://huggingface.co/learn/llm-course/en/chapter7/2

- **Task**: Named Entity Recognition (NER)
- **Dataset**: `conll2003` — มี Label 9 ประเภท (O, B-PER, I-PER, B-ORG, I-ORG, B-LOC, I-LOC, B-MISC, I-MISC)
- **Model**: `distilbert-base-uncased` (Pre-trained → Fine-tune)
- **ความท้าทาย**: BERT Tokenizer แบ่งคำเป็น Subwords → ต้อง Align Labels ให้ตรง

```python
# ตัวอย่าง Subword Alignment
คำ:      ["Washington"]     → Label: B-LOC
Subword: ["Wash", "##ington"] → Labels: [B-LOC, -100]
#                                              ↑         ↑
#                                         Label จริง   ไม่นำมา Train
```

---

## MinIO Buckets ที่ใช้

| Bucket | เนื้อหา | ตัวอย่าง Object |
| :--- | :--- | :--- |
| `datasets` | Dataset Parquet files | `conll2003/train.parquet` |
| `models` | Trained Model files | `{job_id}/config.json`, `{job_id}/model.safetensors` |
| `training-logs` | Training Log JSON | `{job_id}/training_log.json` |

---

## Dockerfile — GPU Container

```dockerfile
FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime
```

- Base Image มี **CUDA 12.1 + cuDNN 8 + PyTorch 2.3** ติดตั้งมาให้
- **ไม่ต้องติดตั้ง NVIDIA Driver ใน Container** — ใช้ Driver ของ Host เครื่องโดยตรง
- ต้องติดตั้ง [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) บน Host ก่อน

---

## compose.yml — GPU Flag

```yaml
trainer-worker:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia   # ใช้ NVIDIA GPU
            count: 1
            capabilities: [gpu]
```

---

## คำสั่งรัน

```bash
# รัน Worker ผ่าน Docker Compose (แนะนำ)
docker compose up -d trainer-worker

# รัน Worker โดยตรง (สำหรับ Development)
python worker.py

# ดู Log ของ Worker
docker compose logs -f trainer-worker
```
