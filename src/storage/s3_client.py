import os
import shutil
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class S3MockClient:
    """
    A local storage proxy that emulates an AWS S3 bucket.
    This allows us to test the Background Synchronization architecture 
    without requiring AWS credentials. When ready, replace this class 
    with a boto3 implementation.
    """
    def __init__(self):
        # Emulate the S3 bucket using the Next.js public/cad folder
        # This allows the frontend to serve the files statically (like a CDN)
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.bucket_path = os.path.join(self.root_dir, "frontend", "public", "cad")
        os.makedirs(self.bucket_path, exist_ok=True)
        
        # Knowledgebase path for storing raw backups/metadata
        self.kb_path = os.path.join(self.root_dir, "knowledgebase")
        os.makedirs(self.kb_path, exist_ok=True)

    def upload_to_s3(self, local_file_path: str, destination_key: str = None) -> bool:
        """
        Upload a file to the mocked S3 bucket.
        """
        if not os.path.exists(local_file_path):
            logger.error(f"[S3Mock] File not found: {local_file_path}")
            return False
            
        if not destination_key:
            destination_key = os.path.basename(local_file_path)
            
        destination_path = os.path.join(self.bucket_path, destination_key)
        
        try:
            shutil.copy2(local_file_path, destination_path)
            
            # Also keep a copy in the knowledgebase for embedding processing
            kb_dest = os.path.join(self.kb_path, destination_key)
            shutil.copy2(local_file_path, kb_dest)
            
            logger.info(f"[S3Mock] Successfully uploaded {destination_key} to mock S3.")
            return True
        except Exception as e:
            logger.error(f"[S3Mock] Upload failed for {destination_key}: {e}")
            return False

    def get_presigned_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a pre-signed URL to access the S3 object.
        For the local mock, this just returns the Next.js public static route.
        """
        destination_path = os.path.join(self.bucket_path, s3_key)
        if not os.path.exists(destination_path):
            logger.warning(f"[S3Mock] Key not found in bucket: {s3_key}")
            return None
            
        # Return the CDN/Frontend path
        return f"/cad/{s3_key}"

# Singleton instance
s3_client = S3MockClient()

def upload_to_s3(local_file_path: str, destination_key: str = None) -> bool:
    return s3_client.upload_to_s3(local_file_path, destination_key)

def get_presigned_url(s3_key: str) -> Optional[str]:
    return s3_client.get_presigned_url(s3_key)
