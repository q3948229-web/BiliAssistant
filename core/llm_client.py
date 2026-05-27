import json
import os
import requests
from utils.logger import get_logger
from utils.config import settings

logger = get_logger("LLMClient")

class LLMClient:
    def __init__(self):
        self.api_key = settings.LLM_API_KEY or settings.DASHSCOPE_API_KEY
        self.base_url = settings.LLM_BASE_URL
        self.model = settings.LLM_MODEL
        # Load presets
        try:
            presets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "presets.json")
            with open(presets_path, "r", encoding="utf-8") as f:
                self.presets = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load presets: {e}")
            self.presets = {}

    def generate_summary(self, content: str, preset_name: str = "meeting_summary", custom_prompt: str = None) -> str:
        url = self.base_url
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Determine prompt strategy
        if custom_prompt and custom_prompt.strip():
            system_prompt = custom_prompt
            user_prompt = f"以下是转录内容：\n\n{content}"  # Default wrapper for custom prompt
        else:
            preset = self.presets.get(preset_name, self.presets.get("meeting_summary"))
            if not preset: # Fallback if presets file is broken
                system_prompt = "You are a helpful assistant."
                user_prompt = content
            else:
                system_prompt = preset["system"]
                user_prompt = preset["user_template"].format(content=content)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
        
        logger.info(f"Generating summary with model: {self.model} | Preset: {preset_name} | Custom: {bool(custom_prompt)}")
        resp = requests.post(url, headers=headers, json=payload)

        if resp.status_code == 200:
            result = resp.json()
            if "choices" in result:
                return result["choices"][0]["message"]["content"]
            logger.error(f"LLM response missing 'choices': {resp.text[:500]}")
            raise Exception(f"LLM Error: response missing 'choices' field")

        logger.error(f"LLM API error {resp.status_code}: {resp.text[:500]}")
        raise Exception(f"LLM Error ({resp.status_code}): {resp.text[:200]}")
