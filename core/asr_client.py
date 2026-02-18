import json
import time
import requests
from utils.logger import get_logger
from utils.config import settings
from utils.helpers import format_milliseconds

logger = get_logger("ASRClient")

class ASRClient:
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.model = settings.DASHSCOPE_MODEL

    def submit_task(self, file_url: str):
        url = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"
        }
        
        payload = {
            "model": self.model,
            "input": {"file_url": file_url},
            "parameters": {"enable_itn": False}
        }
        
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code == 200:
            return resp.json().get("output", {}).get("task_id")
        else:
            logger.error(f"ASR Submit Failed: {resp.text}")
            raise Exception(f"ASR Task Submission Failed: {resp.status_code}")

    def poll_result(self, task_id: str):
        url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        start_time = time.time()
        while True:
            try:
                resp = requests.get(url, headers=headers)
                if resp.status_code != 200:
                    logger.warning(f"Poll check failed: {resp.status_code}")
                    time.sleep(3)
                    continue

                data = resp.json()
                status = data.get("output", {}).get("task_status")
                
                if status == "SUCCEEDED":
                    return self._process_success(data)
                elif status == "FAILED":
                    error = data.get("output", {})
                    raise Exception(f"Task Failed: {error.get('code')} - {error.get('message')}")
                else:
                    elapsed = int(time.time() - start_time)
                    if elapsed % 10 == 0:
                        logger.info(f"Task Status: {status} (Elapsed: {elapsed}s)")
                    time.sleep(3)
            except Exception as e:
                raise e

    def _process_success(self, data):
        transcription_url = data.get("output", {}).get("result", {}).get("transcription_url")
        if not transcription_url:
            return json.dumps(data, ensure_ascii=False)
        
        res = requests.get(transcription_url)
        res_data = res.json()
        
        full_text = ""
        if isinstance(res_data, dict) and "transcripts" in res_data:
            for item in res_data["transcripts"]:
                if "sentences" in item:
                    for sent in item["sentences"]:
                        start_ms = sent.get("begin_time", 0)
                        text = sent.get("text", "")
                        time_str = format_milliseconds(start_ms)
                        full_text += f"[{time_str}] {text}\n"
                elif "text" in item:
                    full_text += item["text"] + "\n"
        
        return full_text
