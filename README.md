# 高中英语试卷批改网 📝

上传高中英语试卷（PDF/TXT/图片）→ 自动解析题目 → 教师配置标准答案 →
学生在线作答（或上传答卷）→ 输出批改版报告：**总分、逐题对错、正确答案、考点解析、
作文点评与参考范文**，并可一键导出批改版 PDF。

> 本项目基于开源项目 **[bhanuxbisht/ai-assignment-checker](https://github.com/bhanuxbisht/ai-assignment-checker)**
> (MIT License) 优化构建：保留其 Flask + 上传批处理 + 缓存 + 报告导出的架构，
> 重构核心流程以适配高中英语试卷场景，并**移除对 Gemini / Tesseract / spaCy 的硬依赖**——
> 开箱即用，无需任何 API Key。

---

## ✨ 功能特性

| 模块 | 说明 |
| --- | --- |
| 📄 试卷解析 | pypdf 提取文字层，正则引擎识别**阅读理解 / 完形填空 / 语法填空 / 短文改错 / 书面表达 / 听力**大题结构与题目 |
| ✏️ 答案配置 | 网页上逐题确认：标准答案（多可接受答案用 `/` 分隔）、分值、考点、解析 |
| ⌨️ 在线作答 | 客观题点选 A–D、语法填空逐空填写、作文文本框（实时词数统计） |
| 📥 答卷提取 | 上传学生已作答 PDF/TXT，自动匹配客观题选项、填空答案与作文文本 |
| 🎯 逐题批改 | 客观题精确比对（大小写/空白容错）；填空支持多答案；作文**四维评分**（结构/语言/内容 + 词数） |
| 🤖 可选 AI | 配置 OpenAI 兼容 API 后：作文 AI 精批、客观题解析批量生成、扫描卷视觉 OCR |
| 📊 批改报告 | 网页报告（总分/题型得分/逐题对错/解析/作文点评）+ **PDF 批改版导出**（中文正常） |
| 🔌 零依赖开箱 | 依赖已预置在 `vendor/lib`，无需 pip install，无 API Key 时全部功能离线可用 |

## 🚀 快速开始

```bash
# 1. 生成演示试卷（可选，用于体验）
python make_demo_paper.py

# 2. 启动网站（默认 http://127.0.0.1:5000）
python app.py

# Windows 用户也可双击 start.bat
```

浏览器打开 **http://127.0.0.1:5000**，按页面四步操作：

1. **上传试卷**：选择 `demo_paper.pdf`（或你自己的文字版试卷 PDF/TXT）
2. **配置答案**：逐题选择标准答案、分值、考点、解析（可点「AI 生成解析」）
3. **学生作答**：在线点选/填写，或上传已作答的答卷文件
4. **批改报告**：查看分数与解析，下载批改版 PDF / 打印

### 演示试卷标准答案

| 题型 | 答案 |
| --- | --- |
| 阅读理解（1–5） | B　C　A　D　B |
| 完形填空（21–25） | C　A　D　B　A |
| 语法填空（1–5） | waiting　to visit　an　slowly　was built |

### 环境要求

- Python 3.9+（Windows/Linux/macOS）
- 无需 pip 安装任何依赖（`vendor/lib` 已内置 Flask 3.1 / reportlab 5.0 全套）
  - 若自行重建依赖：`python gen_vendor.py`（从 PyPI 下载 wheel 并解压到 vendor/lib）

## 🤖 可选 AI 配置（OpenAI 兼容）

复制 `.env.example` 为 `.env` 并填写（支持 OpenAI / DeepSeek / 通义 / 智谱 / Ollama 等任意兼容后端）：

```
AI_API_KEY=sk-xxxx
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
```

配置后自动启用三项增强（未配置时全部自动降级为离线引擎）：

1. **作文精批**：按高考标准评分（0.5 分粒度）+ 分项得分 + 点评 + 建议 + 参考范文
2. **解析生成**：配置页「AI 生成解析」为客观题批量写考点解析
3. **扫描卷 OCR**：视觉模型识别扫描版 PDF 内嵌图片 / 试卷照片

## 🏗️ 项目结构

```
english-exam-grader/
├── app.py               # Flask 主应用（基于上游架构重构）
├── exam_parser.py       # 试卷结构化解析器（题型识别/题号/选项/空格编号）
├── grading.py           # 批改引擎：客观题比对 + 离线作文四维评分
├── ai_client.py         # 可选 AI：OpenAI 兼容 chat/completions（标准库实现）
├── pdf_report.py        # 批改版 PDF 导出（内置 Adobe CID 中文字体）
├── make_demo_paper.py   # 演示试卷生成器（reportlab）
├── gen_vendor.py        # 依赖自举脚本（PyPI 下载 wheel → vendor/lib）
├── templates/index.html # 单页四步界面
├── static/              # style.css / app.js
├── vendor/lib/          # 预置依赖（Flask/reportlab 等，离线可用）
├── uploads/  sessions/  # 运行时上传与会话数据（自动创建）
├── demo_paper.pdf       # 演示试卷（运行 make_demo_paper.py 生成）
└── .env.example         # AI 配置模板
```

## 🧮 离线作文评分维度（无 AI 时）

| 维度 | 分值 | 依据 |
| --- | --- | --- |
| 结构 | 5 分 | 词数达标（默认 100±20）+ 段落划分 |
| 语言 | 10 分 | 拼写启发式（内置 1500+ 高中词表 + 词形还原）、主谓一致/冠词常见错误、句长 |
| 内容 | 10 分 | 题面主题词覆盖 + 衔接词使用 |

评分结果会明确标注「离线估算」，建议教学中配置 AI 获得更精准的评语与范文。

## ⚠️ 常见问题

- **扫描版 PDF 提示无法提取文字**：本机不依赖 Tesseract。请上传文字版 PDF/TXT，
  或在 `.env` 配置视觉 AI 模型后重试（自动提取 PDF 内嵌图片识别）。
- **端口被占用**：`python app.py 5001` 换端口。
- **中文显示**：PDF 导出使用 reportlab 内置 STSong-Light CID 字体，无需安装字体文件。
- **解析不完整**：试卷排版差异大，解析结果为“草稿”，配置页可人工修正；复杂排版建议用文字版 PDF。

## 📄 License

MIT License，上游版权归 [Bhanu Bisht](https://github.com/bhanuxbisht/ai-assignment-checker)，
本项目新增代码版权归本项目作者。详见 [LICENSE](LICENSE)。
