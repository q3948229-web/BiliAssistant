import os
import sys
import datetime
import oss2
from utils.logger import get_logger
from utils.config import settings

logger = get_logger("OSSManager")

class OSSManager:
    def __init__(self):
        try:
            self.auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
            self.bucket = oss2.Bucket(self.auth, settings.OSS_ENDPOINT, settings.OSS_BUCKET_NAME)
        except Exception as e:
            logger.error(f"OSS Init Failed: {e}")
            self.bucket = None

    def upload_file(self, file_path: str) -> tuple[str, str]:
        """Uploads file to OSS, returns (signed_url, object_key)"""
        if not self.bucket:
            raise Exception("OSS Bucket not initialized")

        try:
            file_name = os.path.basename(file_path)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            object_key = f"mp3_to_txt_temp/{timestamp}_{file_name}"
            
            logger.info(f"Uploading to OSS: {object_key}")
            
            def percentage(consumed_bytes, total_bytes):
                if total_bytes:
                    rate = int(100 * (float(consumed_bytes) / float(total_bytes)))
                    # Simple progress log, maybe improve later
                    # sys.stdout.write(f'\rProgress: {rate}%')
                    # sys.stdout.flush()

            self.bucket.put_object_from_file(object_key, file_path, progress_callback=percentage)
            logger.info("Upload complete.")
            
            url = self.bucket.sign_url('GET', object_key, 3600)
            return url, object_key

        except Exception as e:
            logger.error(f"OSS Upload Failed: {e}")
            raise e

    def delete_file(self, object_key: str):
        if not self.bucket or not object_key:
            return
        try:
            logger.info(f"Cleaning up OSS file: {object_key}")
            self.bucket.delete_object(object_key)
        except Exception as e:
            logger.error(f"Failed to delete OSS file: {e}")
