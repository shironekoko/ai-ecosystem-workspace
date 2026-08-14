"""
API OpenAPI Snapshot Exporter — สคริปต์สำหรับแปลง openapi.json เป็น CSV และ JSON Snapshot

วิธีใช้งาน:
    uv run python utils/export_api_snapshot.py

ผลลัพธ์ที่ได้:
    1. api_snapshot.csv (ไฟล์ CSV ที่บันทึกรายชื่อ API พร้อม Encoding UTF-8-SIG เปิดใน Microsoft Excel ได้ภาษาไทยไม่ต่าง)
    2. openapi_snapshot.json (ไฟล์ OpenAPI Schema ล่าสุดของระบบ)
"""

import csv
import json
import os
import sys

# บังคับใช้ UTF-8 ในการแสดงผล Terminal ฝั่ง Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# ทำให้ Script อ่านโฟลเดอร์ root ของ backend ได้
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app


def export_openapi_to_csv_and_json():
    print("==================================================")
    print("Beginning Snapshot API List generation from openapi.json")
    print("==================================================")

    # 1. ดึง OpenAPI Schema จาก FastAPI App โดยตรง
    openapi_schema = app.openapi()

    # 2. บันทึกไฟล์ openapi_snapshot.json
    json_output_path = os.path.join(os.path.dirname(__file__), "..", "storage", "artifacts", "openapi_snapshot.json")
    os.makedirs(os.path.dirname(json_output_path), exist_ok=True)

    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, ensure_ascii=False, indent=2)
    print(f"[SUCCESS] Saved OpenAPI JSON Schema to: {os.path.abspath(json_output_path)}")

    # 3. แปลง OpenAPI Paths เป็น รายการ API สำหรับสร้าง CSV
    api_rows = []
    paths = openapi_schema.get("paths", {})

    for path, methods in paths.items():
        for method, details in methods.items():
            if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                continue

            summary = details.get("summary", "")
            description = details.get("description", "").replace("\n", " ").strip()
            tags = ", ".join(details.get("tags", []))

            # อ่าน พารามิเตอร์ (Query / Path Params)
            params = []
            for param in details.get("parameters", []):
                p_name = param.get("name", "")
                p_in = param.get("in", "")
                p_req = "Required" if param.get("required") else "Optional"
                params.append(f"{p_name} ({p_in}, {p_req})")
            param_str = "; ".join(params) if params else "-"

            # อ่าน Request Body
            has_body = "Yes" if "requestBody" in details else "No"

            # อ่าน Responses Status Codes
            responses = list(details.get("responses", {}).keys())
            response_str = ", ".join(responses)

            api_rows.append(
                {
                    "Tag/Group": tags,
                    "Method": method.upper(),
                    "Path Endpoint": path,
                    "Summary": summary,
                    "Description": description,
                    "Parameters": param_str,
                    "Has Request Body": has_body,
                    "Response Codes": response_str,
                }
            )

    # เรียงลำดับตาม Tag และ Path เพื่อความสวยงาม
    api_rows.sort(key=lambda x: (x["Tag/Group"], x["Path Endpoint"], x["Method"]))

    # 4. บันทึกเป็นไฟล์ CSV (UTF-8-SIG สำหรับ Excel)
    csv_output_path = os.path.join(os.path.dirname(__file__), "..", "storage", "artifacts", "api_snapshot.csv")

    headers = [
        "Tag/Group",
        "Method",
        "Path Endpoint",
        "Summary",
        "Description",
        "Parameters",
        "Has Request Body",
        "Response Codes",
    ]

    with open(csv_output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(api_rows)

    print(f"[SUCCESS] Exported CSV Snapshot to: {os.path.abspath(csv_output_path)}")
    print(f"[INFO] Total APIs in system: {len(api_rows)} Endpoints")
    print("==================================================\n")

    # แสดงตัวอย่าง API Snapshot ในทอมินัล
    print(f"{'Method':<8} | {'Path Endpoint':<35} | {'Summary'}")
    print("-" * 80)
    for r in api_rows:
        print(f"{r['Method']:<8} | {r['Path Endpoint']:<35} | {r['Summary']}")
    print("-" * 80)


if __name__ == "__main__":
    export_openapi_to_csv_and_json()
