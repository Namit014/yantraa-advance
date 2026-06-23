import os
import boto3
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(_project_root, ".env"), override=True)

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")

KNOWLEDGEBASE_DIR = os.path.join(_project_root, "knowledgebase")

def sync_from_s3():
    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME]):
        print("Error: AWS credentials and S3_BUCKET_NAME must be set in .env")
        return

    print(f"Connecting to S3 bucket: {S3_BUCKET_NAME} in region {AWS_REGION}...")
    
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

    try:
        # Create knowledgebase directory if it doesn't exist
        os.makedirs(KNOWLEDGEBASE_DIR, exist_ok=True)

        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=S3_BUCKET_NAME)

        download_count = 0
        
        for page in pages:
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                key = obj['Key']
                
                # Skip if it's just a directory marker in S3
                if key.endswith('/'):
                    continue

                local_file_path = os.path.join(KNOWLEDGEBASE_DIR, key)
                local_file_dir = os.path.dirname(local_file_path)
                
                # Ensure the local subdirectory exists
                os.makedirs(local_file_dir, exist_ok=True)
                
                s3_size = obj['Size']
                if os.path.exists(local_file_path) and os.path.getsize(local_file_path) == s3_size:
                    print(f"Skipping {key} (already up to date)...")
                    continue
                
                print(f"Downloading {key}...")
                s3_client.download_file(S3_BUCKET_NAME, key, local_file_path)
                download_count += 1

                
        print(f"\nSuccessfully downloaded {download_count} files to {KNOWLEDGEBASE_DIR}/")

    except Exception as e:
        print(f"Error syncing from S3: {e}")

if __name__ == "__main__":
    sync_from_s3()
