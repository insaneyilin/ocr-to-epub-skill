# OCR to EPUB 书籍复原技能

## 触发条件

当用户提供 OCR 扫描结果文件（如 `raw.md`）和目录骨架文件（如 `skeleton.md`），并要求：
- 恢复整本书内容，分章节整理
- 生成 EPUB 电子书
- 从 OCR 文本重建书籍结构

## 工作流程

### 阶段 1：分析输入

1. 阅读 `skeleton.md`（目录骨架），理解全书结构：前言、各部分、各章节、小节层级
2. 阅读 `raw.md`（OCR 文本），确认内容完整性和 OCR 质量问题
3. 通过 `wc -l` 确认文件行数，规划分批读取策略（大文件需分块读取）

### 阶段 2：提取章节内容

1. 创建 `chapters/` 目录
2. 按 skeleton.md 的章节结构，从 raw.md 中提取每章完整正文
3. 为每个章节写入独立的 markdown 文件，命名规范：`{序号}-{章节标题}.md`
   - 前言与鸣谢：`00-鸣谢与前言.md`
   - 各章：`01-章节标题.md`, `02-章节标题.md`, ...
4. 清理 OCR 产生的常见问题：
   - 修复断行（不当换行处合并）
   - 修复乱码字符（如 `&lt;sub&gt;` → 删除）
   - 修复英文术语中的空格断裂（如 `fe a s ib ility` → `feasibility`）
   - 保留所有实质性论证内容
   - 清理多余的空格、标点异常

### 阶段 3：生成阅读建议（可选）

如果用户要求，生成 `reading_suggestions.md`，包含：
- 全书内容脉络概括
- 各部分逻辑关系
- 针对不同读者的阅读路径建议

### 阶段 4：构建 EPUB

使用 `build_epub.py` 脚本生成 EPUB 文件。脚本工作方式：

1. 定义章节列表（顺序、标题、源文件）
2. 对每个章节：
   - 读取 markdown 源文件
   - 用正则将 markdown 转为 HTML（标题、段落、粗体、斜体、分隔线）
   - 包裹为完整的 XHTML 页面
3. 生成 EPUB 结构：
   - `mimetype`（无压缩）
   - `META-INF/container.xml`
   - `EPUB/styles/stylesheet1.css`（中文字体、首行缩进）
   - `EPUB/text/{chapter}.xhtml`（各章内容）
   - `EPUB/toc.ncx`（NCX 目录）
   - `EPUB/nav.xhtml`（HTML5 目录）
   - `EPUB/content.opf`（元数据 + manifest + spine）

关键注意事项：
- 使用纯 Python + 标准库（`zipfile`, `re`, `html`, `uuid`），零外部依赖
- 每个 H1 标题作为一个独立章节，避免 pandoc 的章节合并/丢失问题
- mimetype 必须无压缩且为 zip 第一个条目
- CSS 中 `p { text-indent: 2em; }` 保证中文段落格式

## 需要调整的部分

根据每本书的具体情况，使用前需修改 `build_epub.py` 中的：

1. `CHAPTERS` 列表：章节 ID、标题、源文件名
2. 书籍元数据：书名、作者、出版社、出版日期
3. 特殊的章节提取需求（如从单个文件中切分前言的小节）

## 文件清单

```
ocr-to-epub/
├── SKILL.md          # 本文件（Claude 读取的技能说明）
├── build_epub.py     # EPUB 构建脚本（零依赖）
└── README.md         # 人类可读的说明文档
```
