# -*- coding: utf-8 -*-
"""
高中英语试卷结构化解析器
========================
基于上游项目 bhanuxbisht/ai-assignment-checker (MIT) 的 pypdf 文本提取流程
优化构建：把提取出的试卷纯文本解析为结构化题目，供网页配置、在线作答与
逐题批改使用。

识别能力：
  * 大题标题（阅读理解 / 完形填空 / 语法填空 / 短文改错 / 书面表达 / 听力 / 第一节…）
  * 选择题：题号 + 选项 A–D（含完形填空“题号 + 同行多选项”格式）
  * 语法填空：短文 + 编号空格 (1)…(10) 或 1.____ 形式
  * 书面表达：作文题面（含词数要求）
  * 短文改错：映射为逐处填写答案的 blank 类型

解析结果只是“草稿”：网页配置页允许教师逐题确认/修订答案、分值、解析。
"""

import re
import unicodedata


# ---------------------------------------------------------------- 常量

# 大题标题规则：题型关键词（用于在“第X部分”行内定位题型，或识别独立短标题）
TYPE_KEYWORDS = [
    ('reading', '阅读理解', '阅读理解'),
    ('cloze', '完形填空', '完形填空'),
    ('blank', '语法填空', '语法填空'),
    ('proofread', '短文改错', '短文改错'),
    ('writing', '书面表达|写作', '书面表达'),
    ('listening', '听力', '听力'),
]
TYPE_RE = [(stype, re.compile(pat)) for stype, pat, _ in TYPE_KEYWORDS]
TYPE_NAME = {stype: name for stype, _, name in TYPE_KEYWORDS}

# “第X部分 / 第X节 / Part I / Section A” 标题行
HEADING_RE = re.compile(r'第[一二三四五六七八九十]+\s*[部节]|Part\s*[IVX]+|Section\s*[A-Z]?', re.I)

NUM_RE = re.compile(r'^(\d{1,3})[.、．。)）]\s*(.*)$')
OPT_RE = re.compile(r'^([A-H])[.、．)）]\s*(.*)$')
# 同一行内多个选项（完形填空常见格式：21. A. xx B. xx C. xx D. xx）
INLINE_OPT_RE = re.compile(r'([A-D])[.、．)）]\s*([^A-D]*?)(?=[A-D][.、．)）]|\s*$)')
BLANK_PAREN_RE = re.compile(r'[（(](\d{1,2})[)）]')
BLANK_UNDER_RE = re.compile(r'(\d{1,2})[.、．)）]?\s*_{2,}')

DEFAULT_SCORES = {
    'reading': 2.0,
    'cloze': 2.0,
    'blank': 1.5,
    'proofread': 1.0,
    'writing': 25.0,
    'listening': 2.0,
}

# 阅读理解常见考点（供配置页快速选择）
KNOWLEDGE_POINTS = [
    '细节理解', '推理判断', '主旨大意', '词义猜测', '观点态度',
    '完形语境', '词汇辨析', '语法知识', '固定搭配', '逻辑衔接',
]


# ---------------------------------------------------------------- 工具

def normalize_text(text):
    """全角转半角、统一换行、压缩空白，保证后续正则可靠。"""
    if not text:
        return ''
    text = text.replace('\u3000', ' ')
    # 全角 -> 半角
    text = unicodedata.normalize('NFKC', text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # 压缩 3+ 个连续空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def tokenize_words(text):
    """提取英文单词（含缩写），返回小写列表。"""
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text.lower())


# ---------------------------------------------------------------- 块解析

def _match_section_title(line):
    """若该行是大题标题，返回 (type, name)；否则 None。

    识别策略（避免把“阅读下面短文，从每题…”等说明行误判为标题）：
      1. 含“第X部分/节”的行：在行内定位题型关键词，命中即创建对应大题；
      2. 不含“部分/节”的独立短行（<=12 字符）：按题型关键词识别。
    """
    stripped = line.strip()
    if len(stripped) > 60:
        return None
    if HEADING_RE.search(stripped):
        for stype, rule in TYPE_RE:
            if rule.search(stripped):
                return (stype, TYPE_NAME[stype])
        return ('_heading', stripped)
    if len(stripped) <= 12:
        for stype, rule in TYPE_RE:
            if rule.search(stripped):
                return (stype, TYPE_NAME[stype])
    return None


def split_sections(lines):
    """按大题标题把行切成 [(type, name, block_lines)]。标题行本身不进块。"""
    sections = []
    current = None
    buffer = []

    def flush():
        nonlocal current, buffer
        if buffer:
            if current:
                sections.append((current[0], current[1], buffer))
            else:
                # 卷首内容（标题/考生信息等）也保留，避免丢题
                sections.append(('_unknown', '卷首内容', buffer))
        buffer = []

    for line in lines:
        m = _match_section_title(line)
        if m:
            if m[0] == '_heading':
                buffer.append(line)   # 纯结构行（如“第Ⅰ卷”），并入后续块
                continue
            flush()
            current = m
        else:
            buffer.append(line)

    flush()
    # 完全没有标题：全文作为一个块
    if not sections:
        sections = [('_unknown', '试卷内容', lines)]
    return sections


def _is_option_line(line):
    return bool(OPT_RE.match(line.strip()))


def _count_inline_options(line):
    """同一行内独立选项数量（用于完形填空同行选项检测）。"""
    return len(INLINE_OPT_RE.findall(line))


def parse_choice_block(lines, stype, sname):
    """解析选择题块（reading/cloze/listening）。

    支持两种格式：
      1) 题号行 + 独立选项行（A. xxx / B. xxx）
      2) 题号行 + 同行选项（21. A. xxx B. xxx C. xxx D. xxx）——完形填空
    """
    questions = []
    passage_lines = []
    pending = None        # (num, stem_lines)
    opt_buffer = None     # (num, stem_lines, options)

    def finish_opt():
        nonlocal opt_buffer
        if opt_buffer:
            num, stem_lines, options = opt_buffer
            # 题干为空时（同行选项紧接题号），题干取自 stem_lines 剩余
            stem = ' '.join(s.strip() for s in stem_lines if s.strip()).strip()
            if options:
                questions.append({
                    'id': 'q%d' % len(questions),
                    'num': num,
                    'stem': stem,
                    'options': options,
                    'answer': '',
                    'score': DEFAULT_SCORES.get(stype, 2.0),
                    'explain': '',
                    'knowledge': '',
                })
            opt_buffer = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        m = NUM_RE.match(line)
        if m:
            finish_opt()
            pending = (int(m.group(1)), [m.group(2)])
            # 题号行内可能直接跟同行选项（完形填空）
            rest = m.group(2)
            inline = INLINE_OPT_RE.findall(rest)
            if len(inline) >= 3:
                options = [l + '. ' + t.strip() for l, t in inline]
                questions.append({
                    'id': 'q%d' % len(questions),
                    'num': int(m.group(1)),
                    'stem': '',
                    'options': options,
                    'answer': '',
                    'score': DEFAULT_SCORES.get(stype, 2.0),
                    'explain': '',
                    'knowledge': '',
                })
                pending = None
            continue

        m = OPT_RE.match(line)
        if m:
            # 同行多选项：视为完形格式，从 pending 取题号
            inline = INLINE_OPT_RE.findall(line)
            if len(inline) >= 3 and pending:
                options = [l + '. ' + t.strip() for l, t in inline]
                questions.append({
                    'id': 'q%d' % len(questions),
                    'num': pending[0],
                    'stem': ' '.join(s.strip() for s in pending[1] if s.strip()).strip(),
                    'options': options,
                    'answer': '',
                    'score': DEFAULT_SCORES.get(stype, 2.0),
                    'explain': '',
                    'knowledge': '',
                })
                pending = None
                continue
            # 独立选项行
            if pending:
                opt_buffer = (pending[0], pending[1], [m.group(1) + '. ' + m.group(2).strip()])
                pending = None
            elif opt_buffer:
                opt_buffer[2].append(m.group(1) + '. ' + m.group(2).strip())
            else:
                passage_lines.append(raw)
            continue

        # 普通行：选项尚未开始时属于题干/短文
        if opt_buffer:
            finish_opt()
            passage_lines.append(raw)
        elif pending:
            pending[1].append(line)
        else:
            passage_lines.append(raw)

    finish_opt()

    passage = '\n'.join(passage_lines).strip()
    return {
        'type': stype,
        'name': sname,
        'passage': passage,
        'questions': questions,
    }


def parse_blank_block(lines, stype, sname):
    """解析语法填空/短文改错块：短文 + 编号空格。"""
    passage = '\n'.join(l.strip() for l in lines if l.strip()).strip()
    blanks = []
    seen = set()
    # 括号编号：(1) (2)
    for m in BLANK_PAREN_RE.finditer(passage):
        n = int(m.group(1))
        if n not in seen:
            seen.add(n)
            blanks.append({'n': n, 'answer': ''})
    # 下划线编号：1.____
    if not blanks:
        for m in BLANK_UNDER_RE.finditer(passage):
            n = int(m.group(1))
            if n not in seen:
                seen.add(n)
                blanks.append({'n': n, 'answer': ''})
    blanks.sort(key=lambda b: b['n'])
    return {
        'type': stype,
        'name': sname,
        'passage': passage,
        'blanks': blanks,
    }


def parse_writing_block(lines, sname):
    prompt = '\n'.join(l.strip() for l in lines if l.strip()).strip()
    # 提取词数要求（如“词数 100 左右”）
    m = re.search(r'(\d{2,3})\s*词左右|词数\s*(\d{2,3})', prompt)
    word_requirement = int(m.group(1) or m.group(2)) if m else 100
    return {
        'type': 'writing',
        'name': sname,
        'prompt': prompt,
        'word_requirement': word_requirement,
        'score': DEFAULT_SCORES['writing'],
        'reference': '',
    }


def parse_section(section):
    stype, sname, lines = section
    if stype in ('reading', 'cloze', 'listening'):
        return parse_choice_block(lines, stype, sname)
    if stype in ('blank', 'proofread'):
        return parse_blank_block(lines, stype, sname)
    if stype == 'writing':
        return parse_writing_block(lines, sname)
    # 未知块：尝试按选择题解析
    return parse_choice_block(lines, '_choice', sname)


# ---------------------------------------------------------------- 主入口

def parse_paper(text, filename='', pages=0):
    """把试卷文本解析为结构化 paper dict。"""
    text = normalize_text(text)
    lines = text.split('\n')
    sections = []
    for sec in split_sections(lines):
        parsed = parse_section(sec)
        if parsed['type'] == '_choice' and not parsed['questions']:
            continue
        # 完形/阅读等题型标题未识别时保留原题名
        sections.append(parsed)

    # 完全没有题目的兜底：若文本够长，当作一篇作文题让老师至少能批作文
    if not sections or all(
        (s.get('questions') or s.get('blanks')) is None
        and s.get('type') not in ('writing',)
        for s in sections
    ):
        total_q = sum(len(s.get('questions') or []) + len(s.get('blanks') or []) for s in sections)
        if total_q == 0 and len(text) > 100:
            sections = [{
                'type': 'writing',
                'name': '书面表达（自动兜底）',
                'prompt': text[:2000],
                'word_requirement': 100,
                'score': 25.0,
                'reference': '',
            }]

    # 统一 id
    for i, s in enumerate(sections):
        s['id'] = 's%d' % (i + 1)
        if s.get('type') == '_choice':
            s['type'] = 'choice'
        for j, q in enumerate(s.get('questions') or []):
            q['id'] = '%s-q%d' % (s['id'], j + 1)

    return {
        'meta': {
            'filename': filename,
            'pages': pages,
            'chars': len(text),
        },
        'sections': sections,
    }


def paper_full_score(paper):
    """总分值。"""
    total = 0.0
    for s in paper['sections']:
        if s['type'] == 'writing':
            total += s.get('score', DEFAULT_SCORES['writing']) or 0
        elif s['type'] in ('blank', 'proofread'):
            total += len(s.get('blanks') or []) * DEFAULT_SCORES.get(s['type'], 1.5)
        else:
            total += sum(q.get('score') or 0 for q in s.get('questions') or [])
    return round(total, 1)
