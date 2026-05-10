import json
import re
from anthropic import Anthropic
from src.rules.models import RuleSet
from src.rules.assembler import assemble_prompt_context

AI_FLAG_WORDS = [
    "首先", "其次", "最后", "综上所述", "总而言之", "值得注意的是",
    "本项目", "该楼盘", "不仅如此", "更重要的是", "为您", "为广大客户",
    "极致", "非凡", "卓越", "因此", "由此可见",
]


class Copywriter:
    def __init__(self, ruleset: RuleSet, api_key: str = None, model: str = None):
        self.rs = ruleset
        self.client = Anthropic(api_key=api_key) if api_key else None
        self.model = model or "claude-sonnet-4-6"

    def build_prompts(self, persona_name: str, content_type: str, topic: str = None) -> tuple[str, str]:
        ctx = assemble_prompt_context(self.rs, persona_name, content_type)
        system_prompt = ctx["system_prompt"]
        user_prompt = ctx["persona_context"]
        if topic:
            user_prompt += f"\n\n选题方向：{topic}"
        user_prompt += f"\n\n请生成一篇{content_type}类型的小红书笔记。输出JSON格式：{{\"title\": \"...\", \"body\": \"...\", \"hashtags\": [\"...\"]}}"
        return system_prompt, user_prompt

    def generate(self, system_prompt: str, user_prompt: str, max_retries: int = 1) -> dict:
        for attempt in range(max_retries + 1):
            result = self._call_api(system_prompt, user_prompt)
            if self.passes_anti_ai_check(result.get("body", "")):
                return result
        return result

    def _call_api(self, system_prompt: str, user_prompt: str) -> dict:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text
        return self._parse_json_response(text)

    def _parse_json_response(self, text: str) -> dict:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"title": "", "body": text, "hashtags": []}

    def passes_anti_ai_check(self, text: str) -> bool:
        for word in AI_FLAG_WORDS:
            if word in text:
                return False
        return True
