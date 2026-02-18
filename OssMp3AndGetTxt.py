import os
import sys
import json
import time
import requests
import argparse
from http import HTTPStatus
import datetime

# Ensure we can find config.py in the same directory
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    import config
except ImportError:
    print("Error: config.py not found in the script directory.")
    print("Please create config.py with API_KEY, MODEL, and OSS configurations.")
    sys.exit(1)

try:
    import oss2
except ImportError:
    print("请安装 oss2 库以支持文件上传功能：\npip install oss2")
    oss2 = None

API_KEY = config.API_KEY.strip()
MODEL = getattr(config, 'MODEL', 'qwen3-asr-flash-filetrans')

def get_oss_bucket():
    """Helper to get OSS bucket object"""
    if not oss2:
        return None
    
    access_key_id = getattr(config, 'OSS_ACCESS_KEY_ID', '')
    access_key_secret = getattr(config, 'OSS_ACCESS_KEY_SECRET', '')
    endpoint = getattr(config, 'OSS_ENDPOINT', '')
    bucket_name = getattr(config, 'OSS_BUCKET_NAME', '')

    if "**************" in access_key_id or "your-bucket-name" in bucket_name or not access_key_id:
        print("[配置错误] config.py 中的 OSS 配置未正确填写。")
        print("请填入正确的 OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, OSS_ENDPOINT, OSS_BUCKET_NAME")
        return None

    try:
        auth = oss2.Auth(access_key_id, access_key_secret)
        return oss2.Bucket(auth, endpoint, bucket_name)
    except Exception as e:
        print(f"OSS Connection Error: {e}")
        return None

def upload_to_oss(file_path):
    """
    Uploads a local file to Aliyun OSS.
    Returns: (signed_url, object_key)
    """
    bucket = get_oss_bucket()
    if not bucket:
        return None, None
        
    try:
        # Generate object key (filename in OSS)
        file_name = os.path.basename(file_path)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        object_key = f"mp3_to_txt_temp/{timestamp}_{file_name}"
        
        print(f"正在上传文件到 OSS: {object_key} ...")
        
        def percentage(consumed_bytes, total_bytes):
            if total_bytes:
                rate = int(100 * (float(consumed_bytes) / float(total_bytes)))
                sys.stdout.write(f'\r进度: {rate}%')
                sys.stdout.flush()

        bucket.put_object_from_file(object_key, file_path, progress_callback=percentage)
        print("\n上传完成。")
        
        # Sign URL (valid for 1 hour)
        url = bucket.sign_url('GET', object_key, 3600)
        return url, object_key

    except Exception as e:
        print(f"\nOSS 上传失败: {e}")
        return None, None

def delete_oss_file(object_key):
    """Deletes file from OSS"""
    bucket = get_oss_bucket()
    if not bucket or not object_key:
        return
    
    try:
        print(f"正在清理 OSS 临时文件: {object_key} ...")
        bucket.delete_object(object_key)
        print("清理完成。")
    except Exception as e:
        print(f"清理 OSS 文件失败: {e}")
        print("请手动检查 OSS Bucket 进行清理。")

def submit_task(file_url, api_key):
    url = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable"
    }
    
    payload = {
        "model": MODEL,
        "input": {
            "file_url": file_url
        },
        "parameters": {
            "enable_itn": False
        }
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            return response.json()
        else:
            print(f"提交失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"提交任务出错: {e}")
        return None

def get_task_result(task_id, api_key):
    url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"查询结果失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"查询出错: {e}")
        return None

def save_result(text, original_name, output_dir):
    base_name = os.path.basename(original_name)
    # Handle cases where input was a URL with params or a local path
    base_name = os.path.splitext(base_name.split('?')[0])[0]
    
    output_path = os.path.join(output_dir, f"{base_name}.txt")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"转录文稿已保存至: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="MP3 to TXT using DashScope (Auto OSS Upload & Clean)")
    parser.add_argument("file_source", help="本地文件路径 或 远程 URL")
    args = parser.parse_args()
    
    file_source = args.file_source.strip()
    target_url = None
    uploaded_object_key = None
    
    try:
        # Lobbying logic
        if file_source.startswith("http://") or file_source.startswith("https://") or file_source.startswith("oss://"):
            target_url = file_source
        elif os.path.exists(file_source):
            print(f"检测到本地文件: {file_source}")
            target_url, uploaded_object_key = upload_to_oss(file_source)
            if not target_url:
                return
        else:
            print(f"[错误] 输入既不是有效的 URL 也不是本地文件: {file_source}")
            return

        print(f"Model: {MODEL}")
        
        # Submit Task
        submit_resp = submit_task(target_url, API_KEY)
        if not submit_resp:
            return

        task_id = submit_resp.get("output", {}).get("task_id")
        if not task_id:
            print("错误: 无法获取 task_id")
            print(submit_resp)
            return

        print(f"任务已提交. ID: {task_id}")
        
        # Poll for result
        start_time = time.time()
        while True:
            result_resp = get_task_result(task_id, API_KEY)
            if not result_resp:
                break
                
            output = result_resp.get("output", {})
            status = output.get("task_status")
            
            if status == "SUCCEEDED":
                print("\n任务状态: SUCCEEDED")
                
                transcription_url = output.get("result", {}).get("transcription_url")
                full_text = ""
                
                if transcription_url:
                    print(f"正在下载转录结果...")
                    try:
                        res = requests.get(transcription_url)
                        res.raise_for_status()
                        res_data = res.json()
                        
                        if isinstance(res_data, dict) and "transcripts" in res_data:
                            for item in res_data["transcripts"]:
                                if "sentences" in item:
                                    for sent in item["sentences"]:
                                        start_ms = sent.get("begin_time", 0)
                                        text = sent.get("text", "")
                                        # Format milliseconds to HH:MM:SS
                                        seconds = start_ms / 1000.0
                                        time_str = time.strftime('%H:%M:%S', time.gmtime(seconds))
                                        full_text += f"[{time_str}] {text}\n"
                                elif "text" in item:
                                    full_text += item["text"] + "\n"
                        else:
                            full_text = json.dumps(res_data, ensure_ascii=False, indent=2)
                            
                    except Exception as e:
                        print(f"下载详细结果失败: {e}")
                else:
                    full_text = json.dumps(output, ensure_ascii=False, indent=2)

                print("-" * 40)
                print(full_text[:500] + "..." if len(full_text)>500 else full_text)
                print("-" * 40)
                
                out_dir = os.path.join(current_dir, "output")
                if not os.path.exists(out_dir):
                    os.makedirs(out_dir)
                
                save_result(full_text, file_source, out_dir)
                break
                
            elif status == "FAILED":
                print(f"\n任务失败.")
                print(f"Code: {output.get('code')}")
                print(f"Message: {output.get('message')}")
                break
            
            else:
                elapsed = int(time.time() - start_time)
                sys.stdout.write(f"\r状态: {status}... (已耗时: {elapsed}s)")
                sys.stdout.flush()
                time.sleep(3)
                
    except KeyboardInterrupt:
        print("\n用户中断任务。")
    finally:
        # Always clean up OSS file if we uploaded it
        if uploaded_object_key:
            print("\n正在执行清理...")
            delete_oss_file(uploaded_object_key)

if __name__ == "__main__":
    main()
