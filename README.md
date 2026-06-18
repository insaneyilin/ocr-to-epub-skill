# OCR to EPUB

[English version](README_EN.md)

将 OCR 扫描文本恢复为结构完整的 EPUB 电子书——一个供 Claude Code / Codex 使用的 AI 技能。AI 助手负责提取章节、清理 OCR 噪声，最后用 `build_epub.py` 打包。全程零外部依赖，仅使用 Python 标准库。

## 目录结构

```
ocr-to-epub-skill/
├── README.md              ← 中文说明（本文件）
├── README_EN.md           ← English version
└── ocr-to-epub/           ← 技能主体
    ├── SKILL.md           ← AI 运行时读取的工作流说明
    ├── build_epub.py      ← 零依赖 EPUB 打包脚本
    └── README.md          ← 技能级文档
```

## 工作方式

1. **你提供**一本书的 OCR 扫描文本（原始文本或 Markdown）和目录信息（骨架文件、扫描的目录页、或口头描述的章节结构均可）。
2. **AI 助手**读取目录，定位各章节在 OCR 文本中的起止位置，逐章提取为干净的 Markdown 文件，同时修复常见 OCR 噪声（乱码、断行、断词）。
3. **`build_epub.py`** 将章节文件打包为合法 EPUB（`.epub`），包含元数据、目录和 CSS 样式——全部由 Python 标准库完成。

## 安装到 Claude Code

在项目的 `.claude/settings.json` 中添加：

```json
{
  "skills": {
    "ocr-to-epub": {
      "path": "ocr-to-epub-skill/ocr-to-epub",
      "description": "从 OCR 扫描文本和目录信息恢复 EPUB 电子书。"
    }
  }
}
```

也可以注册到全局 `~/.claude/settings.json`（此时 `"path"` 需使用绝对路径）。

注册后，每当你要求将 OCR 文本转换为电子书，Claude Code 会自动加载 `SKILL.md`。

### 作为一次性提示词

也可以将 `SKILL.md` 的内容复制粘贴到任意支持长上下文的 AI 助手的提示词中。技能的主体是工作流描述，真正需要执行的工具只有 `build_epub.py` 一个脚本。

## 安装到 Codex（OpenAI）

1. 将 `ocr-to-epub/` 目录放到你的 Codex 项目中。
2. 在 Codex 会话中，让 agent 读取 `SKILL.md` 作为工作流参考：

   ```
   读取 ocr-to-epub/SKILL.md 并按其中描述的工作流执行。
   这是我的 OCR 文本：[粘贴或文件路径]
   这是目录信息：[粘贴或文件路径]
   ```

3. 章节提取完成后，运行：

   ```bash
   python3 ocr-to-epub/build_epub.py book.json chapters/ output.epub
   ```

## 独立使用 build_epub.py

`build_epub.py` 完全独立于 AI 助手，可直接在命令行使用：

```bash
python3 build_epub.py book.json [chapters_dir] [output.epub]
```

`book.json` 格式：

```json
{
  "meta": {
    "title": "书名",
    "creator": "作者",
    "publisher": "出版社",
    "date": "2024-01",
    "language": "zh-CN"
  },
  "chapters": [
    {"id": "ch01", "title": "第一章 标题", "file": "01-第一章.md"},
    {"id": "ch02", "title": "第二章 标题", "file": "02-第二章.md"}
  ]
}
```

每章字段说明：

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | 是 | EPUB spine 中的唯一标识符，如 `ch01` |
| `title` | 是 | 章节标题 |
| `file` | 是 | `chapters_dir` 下的源 Markdown 文件名 |
| `lines` | 否 | `[起始行, 结束行]`，行号从 1 开始，`null` 表示读至文件末尾。不填则读整个文件 |

## 依赖

- Python 3.6+
- **零外部依赖**——仅使用标准库：`zipfile`, `re`, `html`, `json`, `uuid`, `sys`, `os`

## 实际案例

本仓库自身即是一个完整示例：`raw.md`（OCR 扫描全文）、`skeleton.md`（目录骨架）、`chapters/`（提取的章节文件）、`book.json`（配置）和生成的 `.epub` 文件均包含在内，可直接参考。
