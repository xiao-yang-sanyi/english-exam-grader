/* 高中英语试卷批改网 —— 前端交互（原生 JS，基于上游 main.js 重构） */
(function () {
  'use strict';

  const state = { sid: null, paper: null, result: null };

  // ---------------- 通用 ----------------
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  function toast(msg, isErr) {
    const t = $('toast');
    t.textContent = msg;
    t.hidden = false;
    t.className = isErr ? 'error' : '';
    clearTimeout(t._timer);
    t._timer = setTimeout(() => { t.hidden = true; }, 3200);
  }

  async function api(url, opts) {
    const resp = await fetch(url, opts);
    let data = null;
    try { data = await resp.json(); } catch (e) { /* 非 JSON */ }
    if (!resp.ok) throw new Error((data && data.error) || ('请求失败（' + resp.status + '）'));
    return data;
  }

  function go(step) {
    for (let i = 1; i <= 4; i++) {
      $('panel-upload').hidden = i !== 1;
      $('panel-config').hidden = i !== 2;
      $('panel-answer').hidden = i !== 3;
      $('panel-result').hidden = i !== 4;
    }
    document.querySelectorAll('#steps .step').forEach((el) => {
      const n = +el.dataset.step;
      el.classList.toggle('active', n === step);
      el.classList.toggle('done', n < step);
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  const fmt = (x) => {
    const v = Number(x);
    return Number.isInteger(v) ? String(v) : String(Math.round(v * 10) / 10);
  };

  // ---------------- 步骤 1：上传 ----------------
  const dz = $('dropzone'), fileInput = $('file-input');
  dz.addEventListener('click', () => fileInput.click());
  dz.addEventListener('dragover', (e) => { e.preventDefault(); dz.classList.add('over'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('over'));
  dz.addEventListener('drop', (e) => {
    e.preventDefault();
    dz.classList.remove('over');
    if (e.dataTransfer.files.length) uploadPaper(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener('change', () => {
    if (fileInput.files.length) uploadPaper(fileInput.files[0]);
  });

  async function uploadPaper(file) {
    $('upload-status').hidden = false;
    $('upload-status-text').textContent = '正在上传并解析试卷：' + file.name;
    try {
      const fd = new FormData();
      fd.append('paper', file);
      const data = await api('/api/upload', { method: 'POST', body: fd });
      state.sid = data.session_id;
      state.paper = data.paper;
      renderConfig();
      go(2);
    } catch (err) {
      toast(err.message, true);
    } finally {
      $('upload-status').hidden = true;
    }
  }

  // ---------------- 步骤 2：配置 ----------------
  function renderConfig() {
    const wrap = $('config-sections');
    wrap.innerHTML = '';
    const paper = state.paper;
    if (paper.meta && paper.meta.warning) {
      $('config-warning').hidden = false;
      $('config-warning').textContent = '⚠ ' + paper.meta.warning;
    } else {
      $('config-warning').hidden = true;
    }

    for (const s of paper.sections) {
      const card = document.createElement('div');
      card.className = 'sec-card';
      const typeName = { reading: '阅读理解', cloze: '完形填空', blank: '语法填空',
        proofread: '短文改错', writing: '书面表达', listening: '听力', choice: '选择题' }[s.type] || s.type;
      let inner = '<div class="sec-head">' + esc(s.name || typeName) +
        '<span class="badge">' + typeName + '</span>';

      if (s.type === 'writing') {
        inner += '<div style="width:100%"></div></div>';
        inner += '<div class="passage">' + esc(s.prompt) + '</div>';
        inner += '<div class="blanks-grid">' +
          '<div class="blank-item"><label>本题分值<input type="number" step="0.5" min="0" value="' + esc(s.score) + '" data-w="score"></label>' +
          '<label>词数要求<input type="number" step="10" min="30" value="' + esc(s.word_requirement || 100) + '" data-w="wordreq"></label></div>' +
          '<div class="blank-item" style="grid-column:span 2"><label>参考范文（可选，展示在批改报告中）<textarea rows="4" data-w="reference">' + esc(s.reference || '') + '</textarea></label></div>' +
          '</div>';
      } else if (s.type === 'blank' || s.type === 'proofread') {
        inner += '</div>';
        if (s.passage) inner += '<div class="passage">' + esc(s.passage) + '</div>';
        inner += '<div class="blanks-grid">';
        for (const b of (s.blanks || [])) {
          inner += '<div class="blank-item"><b>第 ' + b.n + ' 空</b>' +
            '<label>标准答案（多个可接受答案用 / 分隔）<input type="text" value="' + esc(b.answer || '') + '" data-a="blank_' + b.n + '"></label>' +
            '<label>分值<input type="number" step="0.5" min="0" value="' + esc(b.score != null ? b.score : 1.5) + '" data-a="score_' + b.n + '"></label>' +
            '<label>解析<input type="text" value="' + esc(b.explain || '') + '" placeholder="如：考查固定搭配…" data-a="explain_' + b.n + '"></label></div>';
        }
        inner += '</div>';
      } else {
        inner += '</div>';
        if (s.passage) inner += '<div class="passage">' + esc(s.passage) + '</div>';
        for (const q of (s.questions || [])) {
          inner += '<div class="q-grid"><div class="q-num">' + esc(q.num ?? '') + '</div><div class="q-body">' +
            '<div class="q-stem">' + esc(q.stem || '') + '</div>';
          if (q.options && q.options.length) {
            inner += '<div class="q-opts">' + esc(q.options.join('　')) + '</div>';
          }
          inner += '<div class="q-controls">' +
            '<label>答案<select data-a="' + q.id + '"><option value="">—未设置—</option>' +
            'ABCDEFGH'.split('').map((L) => '<option' + (q.answer === L ? ' selected' : '') + '>' + L + '</option>').join('') +
            '</select></label>' +
            '<label>分值<input type="number" step="0.5" min="0" value="' + esc(q.score != null ? q.score : 2) + '" data-a="score_' + q.id + '"></label>' +
            '<label>考点<select data-a="knowledge_' + q.id + '"><option value="">—</option>' +
            ['细节理解', '推理判断', '主旨大意', '词义猜测', '观点态度', '词汇辨析', '语法知识', '固定搭配', '逻辑衔接']
              .map((k) => '<option' + (q.knowledge === k ? ' selected' : '') + '>' + k + '</option>').join('') +
            '</select></label>' +
            '<label style="grid-column:1/-1">解析<input type="text" value="' + esc(q.explain || '') + '" placeholder="考点与解题思路（可点击右上角 AI 生成）" data-a="explain_' + q.id + '"></label>' +
            '</div></div></div>';
        }
      }
      card.dataset.sid = s.id;
      card.innerHTML = inner;
      wrap.appendChild(card);
    }
  }

  function collectConfig() {
    const data = {};
    for (const s of state.paper.sections) {
      const upd = {};
      const card = document.querySelector('.sec-card[data-sid="' + s.id + '"]');
      if (!card) continue;
      if (s.type === 'writing') {
        upd.score = card.querySelector('[data-w="score"]').value;
        upd.word_requirement = card.querySelector('[data-w="wordreq"]').value;
        upd.reference = card.querySelector('[data-w="reference"]').value;
      } else {
        card.querySelectorAll('[data-a]').forEach((el) => {
          upd[el.dataset.a] = el.value;
        });
      }
      data[s.id] = upd;
    }
    return data;
  }

  $('btn-save-config').addEventListener('click', async () => {
    try {
      const data = await api('/api/paper/' + state.sid, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(collectConfig()),
      });
      state.paper = data.paper;
      toast('配置已保存（试卷满分 ' + fmt(data.full) + ' 分）');
      renderAnswer();
      go(3);
    } catch (err) { toast(err.message, true); }
  });

  $('btn-ai-explain').addEventListener('click', async () => {
    const btn = $('btn-ai-explain');
    btn.disabled = true;
    btn.textContent = '⏳ AI 生成中…';
    try {
      const data = await api('/api/explain/' + state.sid, { method: 'POST' });
      state.paper = data.paper;
      toast('已为 ' + data.done + ' 道题生成解析');
      renderConfig();
    } catch (err) { toast(err.message, true); }
    finally { btn.disabled = false; btn.textContent = '✨ AI 生成解析'; }
  });

  $('btn-back-config').addEventListener('click', () => { renderConfig(); go(2); });

  // ---------------- 步骤 3：作答 ----------------
  function renderAnswer() {
    const wrap = $('answer-sections');
    wrap.innerHTML = '';
    for (const s of state.paper.sections) {
      const card = document.createElement('div');
      card.className = 'ans-sec';
      const typeName = { reading: '阅读理解', cloze: '完形填空', blank: '语法填空',
        proofread: '短文改错', writing: '书面表达', listening: '听力', choice: '选择题' }[s.type] || s.type;
      let inner = '<div class="sec-head">' + esc(s.name || typeName) + '<span class="badge">' + typeName + '</span></div>';

      if (s.type === 'writing') {
        inner += '<div class="q-item"><div class="q-title">📌 ' + esc(s.prompt) + '</div>' +
          '<textarea class="essay-box" data-ans="w' + s.id + '" placeholder="在这里输入英语作文…（' + (s.word_requirement || 100) + ' 词左右）"></textarea>' +
          '<div class="word-count" data-wc="w' + s.id + '">0 词 / 要求约 ' + (s.word_requirement || 100) + ' 词</div></div>';
      } else if (s.type === 'blank' || s.type === 'proofread') {
        if (s.passage) inner += '<div class="passage">' + esc(s.passage) + '</div>';
        inner += '<div class="q-item"><div class="blanks-grid">';
        for (const b of (s.blanks || [])) {
          inner += '<div class="blank-item"><b>第 ' + b.n + ' 空</b> <input type="text" class="blank-input" data-ans="b' + s.id + '-' + b.n + '" placeholder="填写单词"></div>';
        }
        inner += '</div></div>';
      } else {
        for (const q of (s.questions || [])) {
          inner += '<div class="q-item"><div class="q-title">' +
            (q.num != null ? esc(q.num) + '. ' : '') + esc(q.stem || '') + '</div>';
          if (q.options && q.options.length) {
            inner += '<div class="opt-btns">' + q.options.map((o, i) =>
              '<button type="button" class="opt-btn" data-opt="' + q.id + '" data-val="' + String.fromCharCode(65 + i) + '">' + esc(o) + '</button>'
            ).join('') + '</div>';
          } else {
            inner += '<input type="text" data-ans="' + q.id + '" placeholder="填写选项 A/B/C/D" style="max-width:160px">';
          }
          inner += '</div>';
        }
      }
      card.innerHTML = inner;
      wrap.appendChild(card);
    }
    // 事件绑定
    wrap.querySelectorAll('.opt-btn').forEach((b) => {
      b.addEventListener('click', () => {
        const key = b.dataset.opt;
        wrap.querySelectorAll('.opt-btn[data-opt="' + key + '"]').forEach((x) => x.classList.remove('sel'));
        b.classList.add('sel');
      });
    });
    wrap.querySelectorAll('.essay-box').forEach((t) => {
      t.addEventListener('input', () => {
        const wc = t.value.trim() ? t.value.trim().split(/\s+/).length : 0;
        const el = document.querySelector('[data-wc="' + t.dataset.ans + '"]');
        if (el) {
          el.textContent = wc + ' 词';
          el.classList.toggle('bad', wc > 0 && (wc < 60 || wc > 200));
        }
      });
    });
  }

  function collectAnswers() {
    const ans = { name: $('student-name').value.trim() };
    document.querySelectorAll('#answer-sections [data-ans]').forEach((el) => {
      ans[el.dataset.ans] = el.value;
    });
    document.querySelectorAll('#answer-sections .opt-btn.sel').forEach((b) => {
      ans[b.dataset.opt] = b.dataset.val;
    });
    return ans;
  }

  async function submitAnswers() {
    const btn = $('btn-submit');
    btn.disabled = true;
    btn.textContent = '批改中…';
    try {
      const data = await api('/api/answers/' + state.sid, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(collectAnswers()),
      });
      state.result = data.result;
      renderResult();
      go(4);
    } catch (err) { toast(err.message, true); }
    finally { btn.disabled = false; btn.textContent = '提交并批改'; }
  }
  $('btn-submit').addEventListener('click', submitAnswers);

  $('btn-upload-sheet').addEventListener('click', async () => {
    const f = $('sheet-input').files[0];
    if (!f) { toast('请先选择答卷文件', true); return; }
    const btn = $('btn-upload-sheet');
    btn.disabled = true;
    btn.textContent = '提取中…';
    try {
      const fd = new FormData();
      fd.append('sheet', f);
      fd.append('name', $('student-name').value.trim());
      const data = await api('/api/answers/' + state.sid + '/file', { method: 'POST', body: fd });
      state.result = data.result;
      if (data.extracted && data.extracted.warning) toast(data.extracted.warning);
      renderResult();
      go(4);
    } catch (err) { toast(err.message, true); }
    finally { btn.disabled = false; btn.textContent = '提取并批改'; }
  });

  // ---------------- 步骤 4：结果 ----------------
  function renderResult() {
    const r = state.result;
    const wrap = $('result-body');
    wrap.innerHTML = '';

    const hero = document.createElement('div');
    hero.className = 'score-hero';
    hero.innerHTML =
      '<div class="score-big">' + fmt(r.total) + '<small> / ' + fmt(r.full) + ' 分</small></div>' +
      '<div class="score-meta">学生：<b>' + esc(r.student) + '</b><br>得分率：<b>' + fmt(r.percent) + '%</b></div>';
    wrap.appendChild(hero);

    // 题型得分表
    let tbl = '<table class="sect-table"><tr><th>题型</th><th>得分</th><th>满分</th><th>得分率</th></tr>';
    for (const s of r.sections) {
      tbl += '<tr><td>' + esc(s.name) + '</td><td>' + fmt(s.score) + '</td><td>' + fmt(s.full) + '</td><td>' +
        (s.full ? fmt(Math.round(s.score / s.full * 100)) + '%' : '—') + '</td></tr>';
    }
    tbl += '</table>';
    wrap.insertAdjacentHTML('beforeend', tbl);

    for (const s of r.sections) {
      const card = document.createElement('div');
      card.className = 'ans-sec';
      let inner = '<div class="sec-head">' + esc(s.name) +
        '<span class="badge">' + fmt(s.score) + ' / ' + fmt(s.full) + ' 分</span></div>';

      if (s.type === 'writing') {
        const w = s.writing, res = w.result || {};
        inner += '<div class="writing-card">' +
          '<div class="q-title">📌 ' + esc(w.prompt) + '</div>' +
          '<div class="breakdown">' +
          (res.breakdown ? Object.entries(res.breakdown).map(([k, v]) =>
            '<div class="bd">' + esc(k) + '<b>' + fmt(v) + '</b></div>').join('') : '') +
          '</div>' +
          '<div>得分：<b class="' + (s.score >= s.full * 0.6 ? 'r-ans-ok' : 'r-ans-bad') + '">' + fmt(s.score) +
          ' / ' + fmt(s.full) + ' 分</b> · 词数 ' + (res.word_count ?? '—') +
          ' · <span class="engine-tag' + (res.engine === 'ai' ? ' ai' : '') + '">' +
          (res.engine === 'ai' ? 'AI 精批' : '离线评分（配置 AI 更精准）') + '</span></div>' +
          '<div style="margin:10px 0"><b>学生作文：</b></div>' +
          '<div class="essay-view">' + esc(w.essay || '（未作答）') + '</div>' +
          '<div style="margin-top:10px"><b>教师点评：</b>' + esc(res.comment || '') + '</div>';
        if (res.suggestions && res.suggestions.length) {
          inner += '<div style="margin-top:6px"><b>改进建议：</b>' +
            res.suggestions.map(esc).join('；') + '</div>';
        }
        if (w.reference || res.revised) {
          inner += '<div style="margin-top:10px"><b>参考范文：</b></div>' +
            '<div class="essay-view">' + esc(w.reference || res.revised) + '</div>';
        }
        inner += '</div>';
      } else {
        for (const it of s.items) {
          const ok = it.correct;
          inner += '<div class="r-item">' +
            '<div class="r-mark" style="color:' + (ok ? 'var(--ok)' : 'var(--bad)') + '">' + (ok ? '✔' : '✘') + '</div>' +
            '<div class="r-body"><div class="r-line">' +
            (it.kind === 'choice'
              ? '<b>' + esc(it.num) + '. ' + esc(it.stem) + '</b>'
              : '<b>第 ' + esc(it.n) + ' 空</b>') +
            '</div><div class="r-line">' +
            (it.kind === 'choice'
              ? '学生选：<span class="' + (ok ? 'r-ans-ok' : 'r-ans-bad') + '">' + esc(it.student || '未作答') + '</span>　正确答案：<b>' + esc(it.answer || '未设置') + '</b>'
              : '学生填：<span class="' + (ok ? 'r-ans-ok' : 'r-ans-bad') + '">' + esc(it.student || '未作答') + '</span>　参考答案：<b>' + esc(it.answer || '未设置') + '</b>') +
            '　得分：<b>' + fmt(it.score) + ' / ' + fmt(it.full) + '</b>' +
            (it.knowledge ? '<span class="r-knowledge">' + esc(it.knowledge) + '</span>' : '') +
            '</div>' +
            (it.explain ? '<div class="r-explain"><b>解析：</b>' + esc(it.explain) + '</div>' : '') +
            '</div></div>';
        }
      }
      card.innerHTML = inner;
      wrap.appendChild(card);
    }

    $('btn-pdf').href = '/api/result/' + state.sid + '/pdf';
  }

  $('btn-reanswer').addEventListener('click', () => { renderAnswer(); go(3); });

  go(1);
})();
