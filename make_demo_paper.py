# -*- coding: utf-8 -*-
"""
生成演示试卷 demo_paper.pdf（文字版 PDF，可直接上传体验批改流程）
=================================================================
题型：阅读理解 5 题(2分/题) + 完形填空 5 题(2分/题) + 语法填空 5 空(1.5分/空)
     + 书面表达(25分)，满分 52.5 分。

教师标准答案（供配置页使用）：
  阅读理解：1-5  → B C A D B
  完形填空：21-25 → C A D B A
  语法填空：(1) waiting (2) to visit (3) an (4) slowly (5) was built
"""

import sys
import os

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, 'vendor', 'lib'))

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))

TITLE = ParagraphStyle('t', fontName='STSong-Light', fontSize=17, leading=24, alignment=1, spaceAfter=4)
SUB = ParagraphStyle('sub', fontName='STSong-Light', fontSize=10, leading=14, alignment=1, textColor='#555555', spaceAfter=6)
SEC = ParagraphStyle('sec', fontName='STSong-Light', fontSize=13, leading=18, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle('body', fontName='Helvetica', fontSize=10.5, leading=16)
WPROMPT = ParagraphStyle('wprompt', fontName='STSong-Light', fontSize=10.5, leading=16)
Q = ParagraphStyle('q', fontName='Helvetica', fontSize=10.5, leading=16, spaceBefore=3)
OPT = ParagraphStyle('opt', fontName='Helvetica', fontSize=10.5, leading=15, leftIndent=14)
NOTE = ParagraphStyle('note', fontName='STSong-Light', fontSize=9.5, leading=13, textColor='#444444')

PASSAGE_READING = ("Tom is a sixteen-year-old high school student from a small town. "
                   "Last summer, he decided to do something different instead of staying at home. "
                   "He joined a volunteer program and went to a mountain village to teach English. "
                   "At first, the children were shy and seldom spoke in class. Tom tried many ways to "
                   "encourage them, such as playing word games and singing English songs. Little by "
                   "little, the classroom became lively. One day, a girl named Lily wrote him a note: "
                   "'Thank you for making English fun.' Tom said that was the best reward he had ever "
                   "received. He now plans to study education in college and hopes to go back to the "
                   "village in the future.")

QUESTIONS_READING = [
    ("What did Tom do last summer?",
     ["He stayed at home all summer.", "He taught English in a mountain village.",
      "He traveled to a big city.", "He studied in a summer school."]),
    ("Why were the children quiet at the beginning?",
     ["They disliked Tom.", "They could not speak English at all.",
      "They were shy and afraid to speak.", "They were too busy with farm work."]),
    ("What did Tom do to encourage the children?",
     ["He gave them presents.", "He told them stories.",
      "He played games and sang songs.", "He took them to the city."]),
    ("How did Tom feel when he read Lily's note?",
     ["Proud and rewarded.", "Tired and bored.", "Surprised and angry.", "Worried and sad."]),
    ("What does Tom plan to do in the future?",
     ["Become a singer.", "Study education in college and return to the village.",
      "Find a job in a big city.", "Open a school in his hometown."]),
]

PASSAGE_CLOZE = ("When I was twelve, my family moved to a new city. I felt 21____ because I had no "
                 "friends there. My mother noticed my sadness and 22____ me to join the school "
                 "basketball team. At first I refused, 23____ I was afraid of making mistakes. "
                 "However, my mother kept encouraging me, saying that courage is not the absence of "
                 "fear but the ability to 24____ it. In the end, I joined the team and gradually "
                 "made many good friends. That experience taught me a lesson: we grow 25____ when "
                 "we step out of our comfort zone.")

CLOZE_ITEMS = [
    ("21.", [("A", "excited"), ("B", "relaxed"), ("C", "lonely"), ("D", "calm")]),
    ("22.", [("A", "advised"), ("B", "warned"), ("C", "ordered"), ("D", "forced")]),
    ("23.", [("A", "so"), ("B", "but"), ("C", "or"), ("D", "because")]),
    ("24.", [("A", "accept"), ("B", "enjoy"), ("C", "avoid"), ("D", "face")]),
    ("25.", [("A", "quickly"), ("B", "slowly"), ("C", "hardly"), ("D", "quietly")]),
]

PASSAGE_BLANK = ("Last weekend, my classmates and I spent a day at the City Museum. While "
                 "(1)______ (wait) for the bus, we discussed what we expected to see. Our teacher "
                 "had promised (2)______ (visit) the new science hall with us. As soon as we "
                 "arrived, we were amazed by (3)______ huge model of the solar system. The guide "
                 "explained everything patiently and we listened (4)______ (slow) to take notes. "
                 "We learned that the museum (5)______ (build) in 1998 and has attracted millions "
                 "of visitors since then.")

WRITING_PROMPT = ("假定你是李华，你的英国笔友 Peter 来信询问你的高中生活。请你给他回一封邮件，"
                  "内容包括：1. 学校课程与活动；2. 你最喜欢的科目及原因；3. 询问他的近况。"
                  "注意：1. 词数 100 左右；2. 可以适当增加细节，以使行文连贯；3. 开头和结尾已给出，"
                  "不计入总词数。Dear Peter, ... Yours, Li Hua")


def build(out_path):
    doc = SimpleDocTemplate(out_path, pagesize=A4,
                            leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title='高中英语模拟试卷（一）')
    story = [
        Paragraph('高中英语模拟试卷（一）', TITLE),
        Paragraph('（满分 52.5 分　考试时间 40 分钟）', SUB),
        HRFlowable(width='100%', thickness=1),
    ]

    # 第一部分 阅读理解
    story.append(Paragraph('第一部分　阅读理解（共 5 小题；每小题 2 分，满分 10 分）', SEC))
    story.append(Paragraph('阅读下列短文，从每题所给的 A、B、C 和 D 四个选项中，选出最佳选项。', NOTE))
    story.append(Spacer(1, 3))
    story.append(Paragraph(PASSAGE_READING, BODY))
    for i, (stem, opts) in enumerate(QUESTIONS_READING, start=1):
        story.append(Paragraph('%d. %s' % (i, stem), Q))
        for label, text in zip('ABCD', opts):
            story.append(Paragraph('%s. %s' % (label, text), OPT))

    # 第二部分 完形填空
    story.append(Paragraph('第二部分　完形填空（共 5 小题；每小题 2 分，满分 10 分）', SEC))
    story.append(Paragraph('阅读下面短文，从短文后各题所给的 A、B、C 和 D 四个选项中，选出最佳选项。', NOTE))
    story.append(Spacer(1, 3))
    story.append(Paragraph(PASSAGE_CLOZE, BODY))
    for num, opts in CLOZE_ITEMS:
        line = '%s ' % num + '　'.join('%s. %s' % (label, text) for label, text in opts)
        story.append(Paragraph(line, OPT))

    # 第三部分 语法填空
    story.append(Paragraph('第三部分　语法填空（共 5 小题；每小题 1.5 分，满分 7.5 分）', SEC))
    story.append(Paragraph('阅读下面短文，在空白处填入 1 个适当的单词或括号内单词的正确形式。', NOTE))
    story.append(Spacer(1, 3))
    story.append(Paragraph(PASSAGE_BLANK, BODY))

    # 第四部分 书面表达
    story.append(Paragraph('第四部分　书面表达（满分 25 分）', SEC))
    story.append(Paragraph(WRITING_PROMPT, WPROMPT))

    doc.build(story)
    print('已生成演示试卷：%s' % out_path)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, 'demo_paper.pdf')
    build(out)
