from minio_client import get_minio_client,upload_file


if __name__ == "__main__":
    client = get_minio_client()
    upload_file("images", "klong001.jpg", "C:/Users/Klong/OneDrive/เอกสาร/Code/ai-ecosystem-workspace/4f1c6535-a23a-4719-874f-0b0803c989e6.jpg", client)
    buckets = client.list_buckets()
    print("Buckets in MinIO:", [bucket.name for bucket in buckets])