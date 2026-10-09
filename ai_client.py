# -*- coding: utf-8 -*-
"""
可选 AI 增强客户端（OpenAI 兼容协议）
====================================
不依赖任何第三方 SDK，使用标准库 urllib 调用 OpenAI 兼容的
chat/completions 接口。支持任意兼容后端（OpenAI / DeepSeek / 通义 / 智谱 /
本地 Ollama / vLLM 等），通过项目根目录 .env 或环境变量配置：

    AI_API_KEY=sk-xxxx
    AI_BASE_URL=https://api.openai.com/v1     # 可选，默认 OpenAI
    AI_MODEL=gpt-4o-mini                       # 可选
    AI_TIMEOUT=120                             # 可选

未配置 API Key 时 available=False，所有功能自动降级为离线引擎。
"""

import base64
import json
import os
import re
import urllib.request

ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')


def load_dotenv():
    """极简 .env 加载（不依赖 python-dotenv）。"""
    if not os.path.exists(ENV_FILE):
        return
    try:
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except OSError:
        pass


load_dotenv()


class AIClient:
    def __init__(self):
        self.api_key = os.getenv('AI_API_KEY', '').strip()
        self.base_url = (os.getenv('AI_BASE_URL') or 'https://api.openai.com/v1').rstrip('/')
        self.model = os.getenv('AI_MODEL', '').strip() or 'gpt-4o-mini'
        self.timeout = int(os.getenv('AI_TIMEOUT', '120') or 120)

    @property
    def available(self):
        return bool(self.api_key)

    def chat(self, messages, temperature=0.3, max_tokens=1600, json_mode=False):
        """调用 chat/completions，返回文本；失败返回 None。"""
        if not self.available:
            return None
        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        if json_mode:
            payload['response_format'] = {'type': 'json_object'}
        req = urllib.request.Request(
            self.base_url + '/chat/completions',
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + self.api_key,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            return data['choices'][0]['message']['content']
        except Exception as e:
            print('[AI] chat error:', repr(e)[:160])
            return None

    # ------------------------------------------------ 作文精批

    def grade_writing(self, prompt, essay, full=25.0):
        """AI 作文精批，返回与离线引擎相同结构的 dict；失败返回 None。"""
        system = (
            '你是一位经验丰富的高中英语老师，负责批改高考书面表达。'
            '请用 JSON 输出（不要用 Markdown 代码块）。'
        )
        user = (
            '【作文题目】\n%s\n\n【学生作文】\n%s\n\n'
            '请按高考标准批改，满分 %.1f 分。返回 JSON，字段如下：\n'
            '{"score": 总分(保留0.5粒度), "word_count": 词数(int), '
            '"breakdown": {"结构": 满分5, "语言": 满分10, "内容": 满分10}, '
            '"comment": "总评(中文,80字内)", '
            '"suggestions": ["改进建议", ...2-4条], '
            '"issues": ["主要问题", ...0-5条], '
            '"revised": "参考范文(英语,100词左右)"}'
            % (prompt, essay or '（空）', full)
        )
        text = self.chat(
            [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
            temperature=0.3, max_tokens=2000, json_mode=True,
        )
        if not text:
            return None
        data = json.loads(re.sub(r'^```(json)?|```$', '', text.strip(), flags=re.M))
        data['engine'] = 'ai'
        # 归一化分数与字段
        data['score'] = float(data.get('score', 0))
        data['score'] = max(0.0, min(full, round(data['score'] * 2) / 2))
        data.setdefault('comment', '')
        data.setdefault('suggestions', [])
        data.setdefault('issues', [])
        data.setdefault('revised', '')
        data.setdefault('word_count', len(re.findall(r"[A-Za-z']+", essay)))
        return data

    # ------------------------------------------------ 题目解析生成

    def explain_questions(self, questions, section_type='choice'):
        """为客观题批量生成中文解析。返回 {num: 解析文本}。"""
        lines = []
        for q in questions:
            lines.append(
                '%d. %s\n选项：%s\n答案：%s'
                % (q.get('num'), (q.get('stem') or '')[:160],
                   ' | '.join(q.get('options') or []), q.get('answer'))
            )
        system = (
            '你是高中英语命题教师。为每道题写一段中文解析（考点+解题思路+答案依据），'
            '每题 30-60 字，条理清晰。仅输出 JSON：{"解析": {"题号": "解析文本", ...}}'
        )
        user = '题型：%s\n题目：\n%s' % (section_type, '\n\n'.join(lines))
        text = self.chat(
            [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
            temperature=0.2, max_tokens=3000, json_mode=True,
        )
        if not text:
            return {}
        try:
            data = json.loads(re.sub(r'^```(json)?|```$', '', text.strip(), flags=re.M))
            out = {}
            for k, v in data.get('解析', {}).items():
                try:
                    out[int(k)] = v
                except (TypeError, ValueError):
                    out[str(k)] = v
            return out
        except Exception:
            return {}

    # ------------------------------------------------ 视觉 OCR（扫描卷）

    def ocr_image(self, image_bytes, mime='image/jpeg'):
        """用视觉模型识别图片中的文字；失败返回 None。"""
        b64 = base64.b64encode(image_bytes).decode('ascii')
        messages = [{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': (
                    '请完整识别这张英语试卷图片中的所有文字（包括题目、选项、编号），'
                    '保持原有结构与换行，直接输出文字，不要任何解释。')},
                {'type': 'image_url',
                 'image_url': {'url': 'data:%s;base64,%s' % (mime, b64)}},
            ],
        }]
        text = self.chat(messages, temperature=0.1, max_tokens=4000)
        return text
