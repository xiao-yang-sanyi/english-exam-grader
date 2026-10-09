# -*- coding: utf-8 -*-
"""
批改版试卷 PDF 导出（reportlab）
===============================
生成一份可直接打印/归档的批改报告：
封面信息（学生、总分、日期）+ 各题型得分 + 逐题批改（对错、正答、解析）
+ 书面表达（学生作文、分项得分、点评、参考范文）。

中文使用 reportlab 内置 Adobe CID 字体 STSong-Light，无需额外字体文件。
"""

import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

try:
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    CJK = 'STSong-Light'
except Exception:
    CJK = 'Helvetica'

GREEN = colors.HexColor('#1a7f37')
GREEN_HEX = '#1a7f37'
RED = colors.HexColor('#c62828')
RED_HEX = '#c62828'
BLUE = colors.HexColor('#1565c0')
GRAY = colors.HexColor('#616161')
LIGHT = colors.HexColor('#f5f5f5')


def _styles():
    return {
        'title': ParagraphStyle('t', fontName=CJK, fontSize=18, leading=24,
                                alignment=TA_CENTER, spaceAfter=2 * mm),
        'subtitle': ParagraphStyle('st', fontName=CJK, fontSize=10.5, leading=15,
                                   alignment=TA_CENTER, textColor=GRAY, spaceAfter=4 * mm),
        'h2': ParagraphStyle('h2', fontName=CJK, fontSize=13, leading=18,
                             spaceBefore=6 * mm, spaceAfter=2 * mm, textColor=BLUE),
        'body': ParagraphStyle('b', fontName=CJK, fontSize=10, leading=15),
        'small': ParagraphStyle('s', fontName=CJK, fontSize=8.5, leading=12, textColor=GRAY),
        'item': ParagraphStyle('i', fontName=CJK, fontSize=9.5, leading=14),
        'essay': ParagraphStyle('e', fontName=CJK, fontSize=9.5, leading=15),
    }


def build_report_pdf(result, paper, out_path):
    s = _styles()
    doc = SimpleDocTemplate(out_path, pagesize=A4,
                            leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm,
                            title='高中英语试卷批改报告')
    story = []

    title = paper.get('meta', {}).get('title') or '高中英语试卷批改报告'
    story.append(Paragraph(title, s['title']))
    story.append(Paragraph(
        '学生：%s　　总分：%s / %s 分（%.1f%%）　　批改时间：%s'
        % (result.get('student') or '未署名',
           _fmt(result.get('total', 0)), _fmt(result.get('full', 0)),
           result.get('percent', 0),
           datetime.now().strftime('%Y-%m-%d %H:%M')),
        s['subtitle']))
    story.append(HRFlowable(width='100%', thickness=0.8, color=BLUE))

    # ---- 各题型得分表 ----
    rows = [['题型', '得分', '满分', '得分率']]
    for sec in result['sections']:
        rate = ('%.0f%%' % (sec['score'] / sec['full'] * 100)) if sec['full'] else '—'
        rows.append([sec['name'] or sec['type'], _fmt(sec['score']), _fmt(sec['full']), rate])
    tbl = Table(rows, colWidths=[70 * mm, 30 * mm, 30 * mm, 30 * mm])
    tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), CJK),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#bdbdbd')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(tbl)

    # ---- 逐题批改 ----
    for sec in result['sections']:
        if sec['type'] == 'writing':
            continue
        story.append(Paragraph('%s（%s / %s 分）' % (
            sec['name'] or '题目', _fmt(sec['score']), _fmt(sec['full'])), s['h2']))
        if sec['type'] in ('blank', 'proofread') and paper:
            ps = next((x for x in paper['sections'] if x['id'] == sec['id']), None)
            if ps and ps.get('passage'):
                story.append(Paragraph('<b>短文：</b>' + _esc(ps['passage'][:600]), s['small']))
        for it in sec['items']:
            mark = '✔ 正确' if it['correct'] else '✘ 错误'
            color = GREEN_HEX if it['correct'] else RED_HEX
            lines = []
            if it['kind'] == 'choice':
                head = '<font color="%s"><b>%d. %s</b></font>　学生选 %s，正确答案 %s（%s / %s 分）' % (
                    color, it['num'], mark,
                    it['student'] or '未作答', it['answer'] or '未设置',
                    _fmt(it['score']), _fmt(it['full']))
            else:
                head = '<font color="%s"><b>第 %d 空　%s</b></font>　学生填 “%s”，参考答案 “%s”（%s / %s 分）' % (
                    color, it['n'], mark,
                    _esc(it['student'] or '未作答'), _esc(it['answer'] or '未设置'),
                    _fmt(it['score']), _fmt(it['full']))
            lines.append(head)
            if it.get('stem'):
                lines.append('<b>题干：</b>' + _esc(it['stem'][:180]))
            if it.get('knowledge'):
                lines.append('<b>考点：</b>%s' % _esc(it['knowledge']))
            if it.get('explain'):
                lines.append('<b>解析：</b>' + _esc(it['explain']))
            story.append(Paragraph('<br/>'.join(lines), s['item']))
            story.append(Spacer(1, 1.6 * mm))

    # ---- 书面表达 ----
    for sec in result['sections']:
        if sec['type'] != 'writing':
            continue
        w = sec['writing']
        r = w['result']
        story.append(Paragraph('%s（%s / %s 分）' % (
            sec['name'] or '书面表达', _fmt(sec['score']), _fmt(sec['full'])), s['h2']))
        story.append(Paragraph('<b>题目：</b>' + _esc(w['prompt'][:300]), s['item']))
        if r.get('breakdown'):
            bd = '　'.join('%s %s 分' % (k, _fmt(v)) for k, v in r['breakdown'].items())
            story.append(Paragraph('<b>分项得分：</b>%s　（词数 %s，评分引擎：%s）' % (
                bd, r.get('word_count', '—'),
                'AI 精批' if r.get('engine') == 'ai' else '离线估算'), s['item']))
        story.append(Paragraph('<b>学生作文：</b>', s['item']))
        story.append(Paragraph(_esc(w['essay'] or '（未作答）'), s['essay']))
        story.append(Paragraph('<b>教师点评：</b>' + _esc(r.get('comment', '')), s['item']))
        if r.get('suggestions'):
            story.append(Paragraph('<b>改进建议：</b>' +
                                   _esc('；'.join(r['suggestions'])), s['item']))
        if w.get('reference') or r.get('revised'):
            story.append(Paragraph('<b>参考范文：</b>', s['item']))
            story.append(Paragraph(_esc(w['reference'] or r.get('revised') or ''),
                                   s['essay']))

    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width='100%', thickness=0.6, color=GRAY))
    story.append(Paragraph(
        '本报告由“高中英语试卷批改网”自动生成 · 基于开源项目 ai-assignment-checker (MIT) 优化构建',
        s['small']))
    doc.build(story)
    return out_path


def _fmt(x):
    try:
        v = float(x)
        return ('%d' % v) if v == int(v) else ('%.1f' % v)
    except (TypeError, ValueError):
        return str(x)


def _esc(text):
    import html
    return html.escape(str(text or '')).replace('\n', '<br/>')
