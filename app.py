# -*- coding: utf-8 -*-
"""
高中英语试卷批改网站 —— Flask 主应用
====================================
基于开源项目 bhanuxbisht/ai-assignment-checker (MIT) 优化构建：

保留（上游架构）：
  * Flask + 静态模板 + 原生 JS 前端结构
  * 文件校验（allowed_file）、文件哈希缓存（get_file_hash）、
    进度跟踪（PROGRESS_STORE）与批量处理思路
  * /health 健康检查端点、内存 PDF 文本缓存（PDF_CACHE）

重构（针对高中英语试卷场景）：
  * 移除登录/Gemini/Tesseract/spaCy 硬依赖 —— 开箱即用
  * 新流程：上传试卷 PDF → 结构化解析 → 教师配置答案 → 学生在线作答
    （或上传已作答 PDF）→ 逐题批改 → 分数+解析 → 导出批改版 PDF
  * 可选 AI：OpenAI 兼容 API（作文精批 / 解析生成 / 扫描卷视觉 OCR），
    未配置时全部功能离线可用

运行：
  python app.py [端口，默认 5000]
"""

import base64
import hashlib
import io
import json
import os
import re
import sys
import threading
import time
import uuid
from datetime import datetime

# ---- 依赖准备：vendor/lib 不存在时自动从 vendor/*.whl 解压（仓库只携带 wheel） ----
_BASE = os.path.dirname(os.path.abspath(__file__))
_VENDOR_LIB = os.path.join(_BASE, 'vendor', 'lib')
if not os.path.isdir(os.path.join(_VENDOR_LIB, 'flask')):
    import glob as _glob
    import zipfile as _zipfile
    os.makedirs(_VENDOR_LIB, exist_ok=True)
    _count = 0
    for _whl in _glob.glob(os.path.join(_BASE, 'vendor', '*.whl')):
        with _zipfile.ZipFile(_whl) as _z:
            _z.extractall(_VENDOR_LIB)
        _count += 1
    print('[vendor] 首次运行：已从 %d 个 wheel 解压依赖到 vendor/lib' % _count)

# ---- 把 vendor 依赖加入 sys.path ----
sys.path.insert(0, _VENDOR_LIB)

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from exam_parser import parse_paper, paper_full_score
from grading import grade_paper
from pdf_report import build_report_pdf
from ai_client import AIClient
from pypdf import PdfReader
from PIL import Image

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

UPLOAD_FOLDER = os.path.join(_BASE, 'uploads')
SESSION_FOLDER = os.path.join(_BASE, 'sessions')
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SESSION_FOLDER, exist_ok=True)

PDF_CACHE = {}
CACHE_LOCK = threading.Lock()

ai = AIClient()
if ai.available:
    print('[AI] 已配置：%s / %s' % (ai.base_url, ai.model))
else:
    print('[AI] 未配置 API Key —— 作文使用离线评分引擎；'
          '如需 AI 精批/解析生成/扫描卷 OCR，请编辑 .env 或设置环境变量。')


# ---------------------------------------------------------------- 上游保留：工具函数

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_hash(file_path):
    """文件哈希（用于 PDF 文本缓存）。"""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def extract_text_from_pdf(pdf_path):
    """文本型 PDF 直接提取；扫描型 PDF 尝试提取内嵌图片走 AI 视觉 OCR。

    返回 (text, warning)。warning 非空时前端展示提示。
    """
    file_hash = get_file_hash(pdf_path)
    with CACHE_LOCK:
        if file_hash in PDF_CACHE:
            return PDF_CACHE[file_hash]

    text, pages = '', 0
    try:
        reader = PdfReader(pdf_path)
        pages = len(reader.pages)
        for page in reader.pages:
            try:
                t = page.extract_text()
                if t:
                    text += t + '\n'
            except Exception:
                continue
    except Exception as e:
        return '', '无法读取 PDF：%s' % e

    warning = ''
    if len(text.strip()) < 80:
        # 扫描版：尝试内嵌图片 + 视觉模型
        ocr_text = _ocr_scanned_pdf(pdf_path)
        if ocr_text:
            text = ocr_text
            warning = '该 PDF 为扫描版，已使用 AI 视觉模型识别文字，建议在配置页核对题目。'
        else:
            warning = ('该 PDF 似乎为扫描版（无可复制文字层），且未配置视觉 AI 模型。'
                       '请上传文字版 PDF/TXT，或在 .env 中配置 AI_API_KEY 后重试。')
    elif pages and len(text.strip()) > 0 and len(text.strip()) / max(pages, 1) < 150:
        pass  # 正常短文本试卷

    result = (text, warning)
    with CACHE_LOCK:
        PDF_CACHE[file_hash] = result
    return result


def _ocr_scanned_pdf(pdf_path):
    """扫描 PDF：提取每页内嵌图像，用 AI 视觉模型 OCR。"""
    if not ai.available:
        return ''
    try:
        reader = PdfReader(pdf_path)
        parts = []
        for page in reader.pages[:8]:
            for img in page.images[:2]:
                try:
                    data = img.data
                    im = Image.open(io.BytesIO(data))
                    im.thumbnail((1400, 1400))
                    buf = io.BytesIO()
                    im.convert('RGB').save(buf, format='JPEG', quality=80)
                    txt = ai.ocr_image(buf.getvalue())
                    if txt:
                        parts.append(txt)
                    break
                except Exception:
                    continue
        return '\n\n'.join(parts)
    except Exception as e:
        print('[OCR] scanned pdf failed:', repr(e)[:120])
        return ''


def extract_text_from_file(file_path):
    ext = file_path.rsplit('.', 1)[1].lower()
    warning = ''
    if ext == 'pdf':
        text, warning = extract_text_from_pdf(file_path)
        return text, warning
    if ext == 'txt':
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read(), ''
    if ext in ('png', 'jpg', 'jpeg', 'gif'):
        if not ai.available:
            return '', '图片试卷需要配置视觉 AI 模型（.env 中 AI_API_KEY）。'
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            txt = ai.ocr_image(data, 'image/' + ('png' if ext == 'png' else 'jpeg'))
            return txt or '', 'AI 未能从图片中识别出文字。' if not txt else '图片已由 AI 视觉模型识别，请核对题目。'
        except Exception as e:
            return '', '图片处理失败：%s' % e
    return '', '不支持的文件类型。'


# ---------------------------------------------------------------- 会话存取

def sess_dir(sid):
    d = os.path.join(SESSION_FOLDER, sid)
    os.makedirs(d, exist_ok=True)
    return d


def sess_save(sid, name, obj):
    with open(os.path.join(sess_dir(sid), name + '.json'), 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def sess_load(sid, name):
    p = os.path.join(SESSION_FOLDER, sid, name + '.json')
    if not os.path.exists(p):
        return None
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)


# ---------------------------------------------------------------- 路由：页面

@app.route('/')
def index():
    return render_template('index.html')


# ---------------------------------------------------------------- 路由：上传与解析

@app.route('/api/upload', methods=['POST'])
def api_upload():
    """上传试卷 PDF/TXT/图片 → 提取文本 → 结构化解析 → 返回 paper。"""
    f = request.files.get('paper')
    if not f or not f.filename:
        return jsonify({'ok': False, 'error': '请选择试卷文件。'}), 400
    if not allowed_file(f.filename):
        return jsonify({'ok': False, 'error': '仅支持 PDF / TXT / PNG / JPG 文件。'}), 400

    sid = uuid.uuid4().hex[:12]
    filename = secure_filename(f.filename)
    path = os.path.join(sess_dir(sid), filename)
    f.save(path)

    text, warning = extract_text_from_file(path)
    if not text.strip():
        return jsonify({'ok': False, 'error': warning or '未能从文件中提取文字。'}), 400

    paper = parse_paper(text, filename=filename)
    paper['meta']['full'] = paper_full_score(paper)
    paper['meta']['warning'] = warning
    paper['meta']['title'] = _guess_title(text, filename)

    sess_save(sid, 'paper', paper)
    sess_save(sid, 'raw', {'text': text[:100000]})
    return jsonify({'ok': True, 'session_id': sid, 'paper': paper})


def _guess_title(text, filename):
    for line in text.split('\n')[:12]:
        line = line.strip()
        if 4 < len(line) < 50 and ('试卷' in line or '英语' in line or '考试' in line or '模拟' in line):
            return line
    return os.path.splitext(filename)[0] or '高中英语试卷'


# ---------------------------------------------------------------- 路由：教师配置

@app.route('/api/paper/<sid>', methods=['GET'])
def api_paper_get(sid):
    paper = sess_load(sid, 'paper')
    if not paper:
        return jsonify({'ok': False, 'error': '会话不存在或已过期。'}), 404
    return jsonify({'ok': True, 'paper': paper})


@app.route('/api/paper/<sid>', methods=['POST'])
def api_paper_save(sid):
    """保存教师配置：每题答案/分值/解析、作文分值/范文。"""
    paper = sess_load(sid, 'paper')
    if not paper:
        return jsonify({'ok': False, 'error': '会话不存在。'}), 404
    data = request.get_json(force=True, silent=True) or {}

    for s in paper['sections']:
        upd = data.get(s['id']) or {}
        if s['type'] == 'writing':
            s['score'] = _num(upd.get('score'), s.get('score', 25.0))
            s['reference'] = str(upd.get('reference', '')).strip()
            s['word_requirement'] = _num(upd.get('word_requirement'), s.get('word_requirement', 100))
        elif s['type'] in ('blank', 'proofread'):
            for b in s.get('blanks') or []:
                bu = upd.get('blank_%d' % b['n']) or {}
                b['answer'] = str(bu.get('answer', '')).strip()
                b['explain'] = str(bu.get('explain', '')).strip()
                b['score'] = _num(bu.get('score'), b.get('score', 1.5))
        else:
            for q in s.get('questions') or []:
                qu = upd.get(q['id']) or {}
                q['answer'] = str(qu.get('answer', '')).strip().upper()
                q['score'] = _num(qu.get('score'), q.get('score', 2.0))
                q['explain'] = str(qu.get('explain', '')).strip()
                q['knowledge'] = str(qu.get('knowledge', '')).strip()

    paper['meta']['full'] = paper_full_score(paper)
    sess_save(sid, 'paper', paper)
    return jsonify({'ok': True, 'paper': paper, 'full': paper['meta']['full']})


def _num(v, default):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


@app.route('/api/explain/<sid>', methods=['POST'])
def api_explain(sid):
    """用 AI 为已配置答案的客观题批量生成解析。"""
    if not ai.available:
        return jsonify({'ok': False, 'error': '未配置 AI API（.env 中 AI_API_KEY）。'}), 400
    paper = sess_load(sid, 'paper')
    if not paper:
        return jsonify({'ok': False, 'error': '会话不存在。'}), 404
    total_done = 0
    for s in paper['sections']:
        if s['type'] in ('blank', 'proofread', 'writing'):
            continue
        qs = [q for q in s.get('questions') or [] if q.get('answer')]
        if not qs:
            continue
        explains = ai.explain_questions(qs, s.get('type'))
        for q in qs:
            key = str(q.get('num'))
            if key in explains and explains[key]:
                q['explain'] = explains[key]
                total_done += 1
    sess_save(sid, 'paper', paper)
    return jsonify({'ok': True, 'done': total_done, 'paper': paper})


# ---------------------------------------------------------------- 路由：作答与答卷提取

@app.route('/api/answers/<sid>', methods=['POST'])
def api_answers_save(sid):
    """保存学生在线作答并立即批改。"""
    paper = sess_load(sid, 'paper')
    if not paper:
        return jsonify({'ok': False, 'error': '会话不存在。'}), 404
    answers = request.get_json(force=True, silent=True) or {}
    sess_save(sid, 'answers', answers)

    result = grade_paper(paper, answers, ai=ai)
    sess_save(sid, 'result', result)
    return jsonify({'ok': True, 'result': result})


@app.route('/api/answers/<sid>/file', methods=['POST'])
def api_answers_file(sid):
    """上传学生已作答的 PDF/TXT 答卷，自动提取作答并批改。"""
    paper = sess_load(sid, 'paper')
    if not paper:
        return jsonify({'ok': False, 'error': '会话不存在。'}), 404
    f = request.files.get('sheet')
    if not f or not f.filename:
        return jsonify({'ok': False, 'error': '请选择答卷文件。'}), 400
    if not allowed_file(f.filename):
        return jsonify({'ok': False, 'error': '仅支持 PDF / TXT / PNG / JPG 文件。'}), 400

    name = request.form.get('name', '').strip()
    path = os.path.join(sess_dir(sid), 'sheet_' + secure_filename(f.filename))
    f.save(path)
    text, warning = extract_text_from_file(path)
    if not text.strip():
        return jsonify({'ok': False, 'error': warning or '未能从答卷中提取文字。'}), 400

    answers = extract_answers_from_text(text, paper)
    answers['name'] = name or answers.get('name') or ''
    sess_save(sid, 'answers', answers)
    result = grade_paper(paper, answers, ai=ai)
    sess_save(sid, 'result', result)
    return jsonify({'ok': True, 'result': result,
                    'extracted': {'text_len': len(text), 'warning': warning}})


def extract_answers_from_text(text, paper):
    """从答卷文本中匹配作答（尽力而为，需教师在结果页核对）。

    * 选择题：找 “21. B” / “21 B” / “21、B” 形式
    * 语法填空：找 “(1) word” 或 “1. word” 形式
    * 书面表达：取 “Dear” 开头段落或全文末尾最长英文段落
    """
    answers = {'name': _guess_student_name(text)}
    flat = text.replace('\r', '\n')

    for s in paper['sections']:
        stype = s.get('type')
        if stype in ('reading', 'cloze', 'listening', 'choice', '_choice'):
            for q in s.get('questions') or []:
                n = q.get('num')
                if n is None:
                    continue
                m = re.search(
                    r'(?<!\d)%d\s*[.、．)）]?\s*([A-H])\b' % n, flat, re.I)
                if m:
                    answers[q['id']] = m.group(1)
        elif stype in ('blank', 'proofread'):
            for b in s.get('blanks') or []:
                n = b['n']
                m = re.search(
                    r'[（(]\s*%d\s*[)）]\s*[:：]?\s*([A-Za-z][A-Za-z\'\-]*)'
                    r'|(?<!\d)%d\s*[.、．)）]\s*([A-Za-z][A-Za-z\'\-]*)' % (n, n),
                    flat)
                if m:
                    answers['b%s-%d' % (s['id'], n)] = m.group(1) or m.group(2)
        elif stype == 'writing':
            essay = _extract_essay(flat)
            if essay:
                answers['w%s' % s['id']] = essay
    return answers


def _guess_student_name(text):
    m = re.search(r'姓\s*名[:：]?\s*([\u4e00-\u9fa5]{2,4}|[A-Za-z][A-Za-z\s]{1,20})', text)
    return (m.group(1) or '').strip() if m else ''


def _extract_essay(flat):
    """优先取 Dear 开头段落；否则取末尾最长英文段落。"""
    m = re.search(r'(Dear[\s\S]{60,1200}?)(?:Yours|Sincerely|$)', flat, re.I)
    if m:
        return m.group(1).strip()[:3000]
    paras = [p.strip() for p in flat.split('\n\n') if p.strip()]
    best = ''
    for p in paras:
        if re.search(r'[a-zA-Z]{4,}', p) and len(p) > len(best):
            best = p
    return best[:3000] if len(best) > 40 else ''


# ---------------------------------------------------------------- 路由：结果与导出

@app.route('/api/result/<sid>', methods=['GET'])
def api_result_get(sid):
    result = sess_load(sid, 'result')
    paper = sess_load(sid, 'paper')
    if not result:
        return jsonify({'ok': False, 'error': '还没有批改结果。'}), 404
    return jsonify({'ok': True, 'result': result,
                    'paper_meta': (paper or {}).get('meta', {})})


@app.route('/api/result/<sid>/pdf', methods=['GET'])
def api_result_pdf(sid):
    result = sess_load(sid, 'result')
    paper = sess_load(sid, 'paper')
    if not result:
        return jsonify({'ok': False, 'error': '还没有批改结果。'}), 404
    out_path = os.path.join(sess_dir(sid), 'graded_report.pdf')
    build_report_pdf(result, paper or {}, out_path)
    student = result.get('student') or '未署名'
    return send_file(out_path, as_attachment=True,
                     download_name='批改报告_%s_%s.pdf' % (student, datetime.now().strftime('%Y%m%d')))


# ---------------------------------------------------------------- 路由：健康检查（上游保留）

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'ai_configured': ai.available,
        'ai_model': ai.model if ai.available else None,
        'pdf_cache_size': len(PDF_CACHE),
        'timestamp': datetime.now().isoformat(),
    })


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print('=' * 60)
    print('  高中英语试卷批改网   http://127.0.0.1:%d' % port)
    print('  基于 ai-assignment-checker (MIT) 优化构建')
    print('  AI 增强：%s' % ('已启用 ' + ai.model if ai.available else '未启用（离线模式）'))
    print('=' * 60)
    app.run(host='127.0.0.1', port=port, debug=False, threaded=True)
