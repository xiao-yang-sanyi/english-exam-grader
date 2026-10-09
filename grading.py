# -*- coding: utf-8 -*-
"""
批改引擎
========
* 客观题（单选/完形）：与标准答案精确比对（大小写/空白容错）。
* 语法填空/短文改错：逐空比对，支持“多个可接受答案”（用 / 或 | 分隔）。
* 书面表达：优先 AI 精批（配置了 OpenAI 兼容 API 时），
  否则使用内置离线启发式评分（词数、结构、语言、扣题四维度），
  并在结果中明确标注评分引擎。

内置词表为高中常用词（约 700 词），用于离线拼写启发式检查。
"""

import re

from exam_parser import tokenize_words

# ---------------------------------------------------------------- 内置词表（高中常用词）

COMMON_WORDS = set("""
a about above across act after again against age ago air all almost along already also always
am among an and animal another answer any anything apple area arm around arrive art as ask at
away baby back bad bag ball bank base be beautiful because become bed been before begin behind
believe below best better between big bike bird bit black blue boat body book born both box boy
break bring brother build building bus business but buy by call came can cannot car care carry
case cat catch cause center century certain chance change child china chinese choice choose city
class clean clear close club cold collect college color come common community company computer
continue control cook cool country course cover create cross cry culture cup cut dance dark data
daughter day dead deal dear decide decision deep degree develop die different difficult dinner
direction discover discuss do doctor dog door down draw dream drink drive drop during each early
earth east easy eat education effect effort egg eight either else end energy enjoy enough enter
environment even evening event ever every everyone everything example exercise expect experience
explain eye face fact fall family famous far farm fast father favorite fear feel few field fight
fill film final find fine finger finish fire first fish five floor flower fly follow food foot
for force foreign forget form four free friend from front fruit full fun future game garden gas
general get girl give glad glass go goal god gold good government great green ground group grow
guess hair half hand happen happy hard have he head health hear heart heat heavy help her here
high him himself his history hit hold home hope hospital hot hotel hour house how however huge
human hundred hurry husband i ice idea if important improve in include increase indeed
information interest international internet into introduce invent invest island it its itself
job join joy just keep key kid kill kind king know knowledge land language large last late
laugh law lay lead learn least leave left leg less lesson let letter level library lie life
light like line list listen little live local long look lose lot love low machine main make
man manage many map mark market marry matter may maybe me mean meat meet meeting member memory
mention message middle might mind minute miss model modern moment money month more morning most
mother mountain mouth move movie much music must my name national natural near necessary need
never new news next nice night nine no north not note nothing notice now number of off offer
office often old on once one only open operation opportunity option or order other our out
outside over own page paint paper parent park part party pass past pay peace people per perhaps
person phone photo pick picture piece place plan plant play player please point police poor
popular position possible post power practice prepare present president price probably problem
produce product program project protect proud provide public pull push put question quick
quiet quite race radio rain raise reach read ready real really reason receive recent record red
reduce relationship remember report research rest result return rich ride right rise river road
rock role room rule run sad safe same save say school science sea season seat second see seem
sell send sense sentence serious serve service set seven several share she ship shop short
should show side sign since sing single sister sit six size skill sky sleep small smart smile
so social society some someone something sometimes son song soon sorry sound south space speak
special spend sport spring stand star start state station stay step still stop store story
street strong student study subject success such suddenly suggest summer sun support sure
system table take talk task teach teacher team technology tell ten term test than thank that
the their them themselves then there these they thing think third this those though thought
three through time to today together too top total town trade traditional train travel tree
trip trouble true try turn two type under understand unit until up upon us use usually value
very view village visit voice wait walk wall want war warm watch water way we wear week well
west what when where whether which while white who whole why wide wife will win wind window
winter wish with within without woman wonder word work worker world worry would write writer
wrong year yes yet you young your yourself
about able accept accepted achieve achieved advice afraid ago agree agreed allow allowed already
although always amazing angry answer answered anyone anything anywhere apologize appear apply
arrange arrived art ask asked attend attended autumn basketball beautiful became become before
begin began begun believe besides between birthday book books boring bought brave breakfast
bright bring brought build built busy buy bought calm campus careful carefully careless canteen
celebrate certain certainly change changed chemistry choose chose chosen cinema city class
classmate classmates classroom clean clever climb close closed club clubs collect colorful
comfortable common company compare complete completed computer confident consider continue
correct correctly could country courage course cover covered create created culture cup dance
dance danced dangerous decide decided decision deep delicious describe described desk develop
developed dictionary die died different difficult dinner dirty discover discussed dish dishes
dream dreamed dress drink drank driven during each early easily east education effort either
elder else encourage encouraged end enjoy enjoyed enough enter entered environment especially
english chinese maths math physics chemistry
evening event ever every everyone everything exam exams example excellent except excited
exciting exercise expect expensive experience explain explained face fact factory fail failed
famous fantastic farm farmer fast faster fastest father favorite fear feel fell felt festival
few field fight finally find finish finished first fish floor flower fly follow food football
football foreign forest forget forgot form forward found four free freedom fresh friend
friendly friends friendship from front fruit fruits full fun funny future game garden gate
geography gift girl give given glad glass go goal gold good grade graduated grammar grass
great greatly green ground group grow grew grown guess guest guide habit hair half hall hand
happen happened happily happiness happy hard hardly healthy hear heard heart heavy hello help
helped helpful her here hero high hill history hit hobby hold holiday home homework honest
hope hoped hospital hot hotel hour however huge human hungry hurry hurt idea if ill imagine
important improve improved include increase indeed information inside instead interest
interested interesting international introduce introduced invent invite invited island job
join joined joke journey joy jump just keep kept key kick kid kill kind kindly kitchen know
knowledge lake land language large last late later laugh law lazy lead leader learn learned
least leave left lend lent less lesson lessons let letter letters level library lie life
light like liked likely line list listen listened little live lively living local lonely long
look lose lost lot loudly love lovely low luck luckily lucky lunch machine main make major
manage many map mark market marry match math maths matter may meal mean meat meet meeting
member members memory mention message method middle mind minute miss mistake modern moment
money month moon more morning most mother mountain mouse mouth move moved much museum music
must name narrow national natural nature near nearly necessary need neighbor never new news
newspaper next nice night nobody noise noon north nose note notebook nothing notice noticed
now nowadays number nurse obey ocean of off offer offered office often oil once only open
opened opinion opportunity order organize organized other otherwise ought our ours out
outside over own owner page paint pair palace paper pardon parent park part particularly
partner party pass passed past path patient patiently pay peace pen pencil people perfect
perform perhaps person pet phone photo photograph physics piano pick picnic picture piece
pilot pioneer place plan planned plane plant plate play played player playground pleasant
please pleased pleasure pocket poem point police polite poor popular population possible
possibly post postcard pot potato potatoes practice practiced practise praise prefer
prepared present president press pretty price probably problem produce production program
progress promise promised pronounce pronunciation proper protect protected proud provide
provided public pull punish pupil push quarter question queue quick quickly quiet quietly
quite race radio railway rain raise rapid rather reach read ready real realize realized
really reason receive received recent recently recite recognize record red refuse refused
regard regret relation remember remembered repair repeat replied report reporter research
respect rest restaurant result return returned review rice rich ride right ring rise river
road robot rocket roll roof room rose round row rule ruler run rush sad sadly safe safety
sail salad sale salt same sand sandwich satisfy save saved say scene school science
scientist scold screen sea search season seat second secret see seem seen seldom sell send
sense sentence serious serve set settle several shake shall shallow shape share shared sharp
she sheep shelf shine ship shirt shoe shop shopping short should shoulder shout show shower
shut shy sick side sight sign silent silly silver similar simple simply since sing singer
single sir sister sit situation size skill skirt sky sleep slow slowly small smart smell
smile smoke smooth snow so soap soccer social society sock sofa soft soldier solve some
somebody someone something sometimes son song soon sorry sort soul sound soup south space
speak speaker special speech speed spell spend spent spirit spoon sport sports spring square
stand star start started state station stay stayed steal step still stomach stone stop store
storm story straight strange street strict strike strong strongly student students study
studied subject succeed success successful such suddenly sugar suggest suggested suitable
summer sun sunny supper supply suppose sure surface surprise surprised sweet swim swimming
table take taken talk talked tall tape task taste taught teach teacher team tear telephone
television tell temperature ten tennis term terrible test text than thank thanks that theater
theatre then there therefore these thick thin thing think third thirsty though thought
thousand through throw ticket tidy tie tiger tight till time tired to today together toilet
tomato tomorrow tonight too tool tooth top topic total touch tour tourist toward tower town
toy track traffic train trained training translate travel traveled treasure treat tree trip
trouble trousers truck true truly trust truth try turn twice type ugly umbrella uncle under
underground understand understood uniform unit university unless until unusual up upon us
useful usual usually vacation valuable value various vegetable very victory video village
visit visited visitor voice volleyball wait waiter wake walk wall want war warm warn wash
waste watch water wave way weak wear weather website weekday weekend weekends weigh welcome
well west wet what whatever wheel when whenever where wherever whether which while whisper
white who whoever whole whom whose wide wife will willing win window windy wine wing winner
winter wise wish with without witness wolf woman wonder wonderful wood word work worked
worker world worry worse worst worth would wound write written wrong yard year yellow
yesterday yet you young your yours youth zero zoo
""".split())

CONNECTORS = {
    'however', 'therefore', 'moreover', 'furthermore', 'besides', 'meanwhile',
    'first', 'firstly', 'second', 'secondly', 'third', 'finally', 'in', 'addition',
    'for', 'example', 'instance', 'such', 'as', 'on', 'the', 'other', 'hand',
    'in', 'my', 'opinion', 'personally', 'conclusion', 'summary', 'although',
    'because', 'so', 'but', 'and', 'also', 'whats', 'more', 'lastly',
}

BE_MISMATCH = [
    ('i is', 'I am'), ('i are', 'I am'), ('i were', 'I was'),
    ('he are', 'he is'), ('she are', 'she is'), ('it are', 'it is'),
    ('they is', 'they are'), ('we is', 'we are'), ('you is', 'you are'),
    ('people is', 'people are'), ('he have', 'he has'), ('she have', 'she has'),
]

THIRD_PERSON_BARE = re.compile(
    r'\b(he|she|it)\s+(go|do|have|like|want|play|make|take|get|come|see|know|help|feel|look|give)\b'
)

STOPWORDS = set("""
the a an and or but if when where which who what how why that this these those of in on at
to for with without about by from as is are was were be been being have has had do does did
will would can could should may might must not no yes so very too much many more most some
any all both each every other another such it its they them their his her our your my you
i we he she one two three four five six seven eight nine ten also just only still even
than then there here now new good great well
""".split())


# ---------------------------------------------------------------- 客观题

def normalize_choice(value):
    """A / a. / （A） -> 'A'"""
    if value is None:
        return ''
    m = re.search(r'([A-H])', str(value).strip().upper())
    return m.group(1) if m else ''


def normalize_blank(value):
    """小写、去首尾空白与标点；"答案 / 备选答案" 拆分为集合。"""
    if value is None:
        return set()
    values = set()
    for part in re.split(r'[/|／]', str(value)):
        part = part.strip().strip('.,;:;，。；：()（）"\' \t')
        if part:
            values.add(part.lower())
    return values


def grade_choice(question, student_answer):
    """返回 (correct, score, full)。"""
    full = float(question.get('score') or 0)
    s = normalize_choice(student_answer)
    a = normalize_choice(question.get('answer'))
    if s and a and s == a:
        return True, full, full
    return False, 0.0, full


def grade_blank(blank, student_answer):
    """语法填空/改错：多个可接受答案任一匹配即对。"""
    full = float(blank.get('score') or 1.5)
    refs = normalize_blank(blank.get('answer'))
    stu = normalize_blank(student_answer)
    if not refs or not stu:
        return False, 0.0, full
    if stu & refs:
        return True, full, full
    return False, 0.0, full


# ---------------------------------------------------------------- 离线作文评分

def extract_keywords(prompt, top=8):
    """从作文题面提取主题关键词（词长>=4 的名词/动词，去停用词）。"""
    words = tokenize_words(prompt)
    freq = {}
    for w in words:
        if len(w) >= 4 and w not in STOPWORDS:
            freq[w] = freq.get(w, 0) + 1
    ranked = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    return [w for w, _ in ranked[:top]]


def grade_writing_offline(prompt, essay, full=25.0, word_requirement=100):
    """离线启发式作文评分（满分默认 25，可配置）。

    维度：
      结构（含词数） 5 分
      语言 10 分（拼写/基础语法启发式检查）
      内容与扣题 10 分（主题词覆盖 + 衔接词使用）
    仅供无 AI API 时使用，结果会标注“离线估算”。
    """
    words = tokenize_words(essay)
    n = len(words)
    if n == 0:
        return {
            'score': 0.0, 'engine': 'offline', 'word_count': 0,
            'breakdown': {'结构': 0.0, '语言': 0.0, '内容': 0.0},
            'comment': '未检测到作答内容。',
            'suggestions': ['请提交完整的英语作文。'],
            'issues': [],
        }

    issues = []

    # ---- 结构（5 分）：词数 4 分 + 段落 1 分 ----
    low, high = max(30, word_requirement - 20), word_requirement + 60
    if n >= low and n <= high:
        word_score = 4.0
    elif n >= low - 20:
        word_score = 3.0
        issues.append('词数略低于要求（%d 词）' % n)
    elif n > high:
        word_score = 3.0
        issues.append('词数超出要求（%d 词），注意控制篇幅' % n)
    elif n >= 20:
        word_score = 1.5
        issues.append('词数明显不足（%d 词），建议扩写至 %d 词左右' % (n, word_requirement))
    else:
        word_score = 0.5
        issues.append('词数严重不足（%d 词）' % n)
    paragraphs = len([p for p in re.split(r'\n+', essay.strip()) if p.strip()])
    para_score = 1.0 if paragraphs >= 2 else 0.5
    structure = round(min(5.0, word_score + para_score), 1)

    # ---- 语言（10 分）----
    lang = 10.0
    low_words = [w for w in words if len(w) >= 4]
    misspelled = 0
    proper = set()

    def base_candidates(w):
        """词形还原候选：剥常见后缀，并处理去 e / 双写 / y→ies
        （include→including、run→running、story→stories）。"""
        if w.endswith('ies') and len(w) > 4:
            yield w[:-3] + 'y'                          # stories -> story
        for suf in ('ingly', 'ation', 'ment', 'ness', 'ful', 'less', 'ing', 'ed', 'es',
                    's', 'ly', 'er', 'est', 'tion'):
            if w.endswith(suf) and len(w) > len(suf) + 1:
                b = w[:-len(suf)]
                yield b
                if suf in ('ing', 'ed', 'es'):
                    yield b + 'e'                       # including -> include
                    if len(b) > 1 and b[-1] == b[-2]:
                        yield b[:-1]                    # running -> run

    for i, w in enumerate(low_words):
        if w in COMMON_WORDS or w in CONNECTORS:
            continue
        # 首字母大写的原形词视为专有名词/标题词（不扣分）
        raw = words[i]
        if raw and raw[0].isupper() and raw.lower() not in COMMON_WORDS:
            proper.add(raw.lower())
            continue
        if w in proper:
            continue
        if any(b in COMMON_WORDS or b in CONNECTORS for b in base_candidates(w)):
            continue
        misspelled += 1
    spell_penalty = min(4.0, misspelled * 0.4)
    if misspelled:
        lang -= spell_penalty
        issues.append('发现 %d 处疑似拼写错误' % misspelled)

    # 基础语法启发式
    lower = ' '.join(words)
    grammar_hits = []
    for bad, good in BE_MISMATCH:
        if re.search(r'\b' + bad.replace(' ', r'\s+') + r'\b', lower):
            grammar_hits.append('“%s” 应为 “%s”' % (bad, good))
    for m in THIRD_PERSON_BARE.finditer(lower):
        if m.group(2) != 'have':
            grammar_hits.append('“%s %s” 疑漏第三人称单数' % (m.group(1), m.group(2)))
    if re.search(r'\ba\s+[aeiou]', lower) and not re.search(r'\ba\s+(hour|honest)', lower):
        grammar_hits.append('元音前应使用 “an”')
    unique_grammar = list(dict.fromkeys(grammar_hits))[:6]
    grammar_penalty = min(2.0, len(unique_grammar) * 0.4)
    lang -= grammar_penalty
    issues.extend(unique_grammar)

    # 句式：句子数量与平均句长
    sentences = [s for s in re.split(r'[.!?]+', essay) if len(s.split()) >= 3]
    if len(sentences) >= 3:
        avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
        if avg_len > 28:
            lang -= 0.5
            issues.append('句子平均过长（%.0f 词），建议拆分长句' % avg_len)
    lang = round(max(0.0, min(10.0, lang)), 1)

    # ---- 内容与扣题（10 分）----
    keywords = extract_keywords(prompt)
    essay_words = set(words)
    covered = [k for k in keywords if k in essay_words]
    coverage = len(covered) / len(keywords) if keywords else 0.5
    content = 3.0 + coverage * 5.0
    connector_hits = sum(1 for w in words if w in CONNECTORS)
    if connector_hits >= 3:
        content += 2.0
    elif connector_hits >= 1:
        content += 1.0
    else:
        issues.append('缺少衔接词（however/first/therefore 等），行文连贯性不足')
    content = round(min(10.0, content), 1)

    total = round(min(full, structure + lang + content) * 2) / 2  # 0.5 分粒度

    comments = []
    if total >= full * 0.85:
        comments.append('整体完成度高，语言流畅、要点齐全。')
    elif total >= full * 0.6:
        comments.append('基本完成任务，语言与内容达标，仍有提升空间。')
    else:
        comments.append('离要求还有差距，建议对照问题逐条改进。')
    if issues:
        comments.append('主要问题：' + '；'.join(issues[:5]) + '。')

    suggestions = []
    if n < word_requirement - 20:
        suggestions.append('扩展内容至 %d 词左右，补充细节与理由支撑观点。' % word_requirement)
    if misspelled:
        suggestions.append('重点订正拼写错误的单词，并养成写后自查的习惯。')
    if unique_grammar:
        suggestions.append('复习主谓一致与冠词用法：' + '；'.join(unique_grammar[:3]) + '。')
    if connector_hits < 3:
        suggestions.append('多使用 however、therefore、besides、firstly 等衔接词提升连贯性。')
    if len(sentences) and sum(len(s.split()) for s in sentences) / len(sentences) > 28:
        suggestions.append('长句拆短，避免结构混乱。')
    if not suggestions:
        suggestions.append('保持现状，可尝试更高级的句式与词汇（非谓语、定语从句等）。')

    return {
        'score': total,
        'engine': 'offline',
        'word_count': n,
        'breakdown': {'结构': structure, '语言': lang, '内容': content},
        'comment': ''.join(comments),
        'suggestions': suggestions,
        'issues': issues[:8],
    }


# ---------------------------------------------------------------- 试卷批改主入口

def grade_paper(paper, answers, ai=None):
    """整卷批改。

    paper:   解析后的试卷结构
    answers: {'q<id>': 'A', 'b<s_id>-<n>': 'word', 'w<s_id>': 'essay', 'name': ...}
    ai:      AIClient 实例或 None（离线模式）

    返回 result dict（用于结果页渲染与 PDF 导出）。
    """
    result = {
        'student': answers.get('name') or '未署名',
        'sections': [],
        'total': 0.0,
        'full': 0.0,
    }
    total = full_total = 0.0

    for s in paper['sections']:
        stype = s.get('type')
        sec = {'id': s['id'], 'name': s.get('name') or '', 'type': stype,
               'score': 0.0, 'full': 0.0, 'items': []}

        if stype == 'writing':
            essay = answers.get('w%s' % s['id'], '').strip()
            full = float(s.get('score') or 25.0)
            req = int(s.get('word_requirement') or 100)
            wresult = None
            if ai is not None and ai.available:
                try:
                    wresult = ai.grade_writing(s.get('prompt') or '', essay, full)
                except Exception as e:  # AI 失败自动降级
                    print('[AI writing failed -> offline]', e)
                    wresult = None
            if wresult is None:
                wresult = grade_writing_offline(s.get('prompt') or '', essay, full, req)
            wresult.setdefault('engine', 'ai' if (ai and ai.available and wresult.get('engine') != 'offline') else 'offline')
            sec['writing'] = {
                'prompt': s.get('prompt') or '',
                'essay': essay,
                'reference': s.get('reference') or '',
                'result': wresult,
            }
            sec['score'] = wresult['score']
            sec['full'] = full
            total += wresult['score']
            full_total += full

        elif stype in ('blank', 'proofread'):
            full = float(DEFAULT_SCORE(stype))
            for b in s.get('blanks') or []:
                key = 'b%s-%d' % (s['id'], b['n'])
                ok, got, bfull = grade_blank(b, answers.get(key))
                sec['items'].append({
                    'kind': 'blank', 'n': b['n'],
                    'student': (answers.get(key) or '').strip(),
                    'answer': b.get('answer') or '',
                    'correct': ok, 'score': got, 'full': bfull,
                    'explain': b.get('explain') or '',
                })
                sec['score'] += got
                sec['full'] += bfull
            total += sec['score']
            full_total += sec['full']

        else:  # choice / reading / cloze / listening
            for q in s.get('questions') or []:
                ok, got, qfull = grade_choice(q, answers.get(q['id']))
                sec['items'].append({
                    'kind': 'choice', 'num': q.get('num'),
                    'stem': q.get('stem') or '',
                    'options': q.get('options') or [],
                    'student': normalize_choice(answers.get(q['id'])),
                    'answer': normalize_choice(q.get('answer')),
                    'correct': ok, 'score': got, 'full': qfull,
                    'explain': q.get('explain') or '',
                    'knowledge': q.get('knowledge') or '',
                })
                sec['score'] += got
                sec['full'] += qfull
            total += sec['score']
            full_total += sec['full']

        result['sections'].append(sec)

    result['total'] = round(total, 1)
    result['full'] = round(full_total, 1)
    result['percent'] = round(total / full_total * 100, 1) if full_total else 0.0
    return result


def DEFAULT_SCORE(stype):
    return {'blank': 1.5, 'proofread': 1.0}.get(stype, 2.0)
