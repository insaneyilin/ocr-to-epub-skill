# OCR to EPUB

从 OCR 扫描文本恢复书籍内容并生成 EPUB 电子书的工具包。

## 使用场景

你有一本书的 OCR 扫描结果（`raw.md`）和目录骨架（`skeleton.md`），需要：
1. 按章节提取、清理内容
2. 生成结构完整的 EPUB 电子书

## 工作流程

### 1. 准备输入

- `raw.md` — OCR 扫描全文
- `skeleton.md` — 目录骨架（章节标题、层级结构）

### 2. 提取章节

按 skeleton.md 的目录结构，从 raw.md 中逐章提取内容，写入 `chapters/` 目录。命名规范：`{序号}-{章节标题}.md`。

此步骤中需要清理 OCR 噪声：合并断行、修复字符乱码、修正断词，但保留全部实质论证内容。

### 3. 生成 EPUB

修改 `build_epub.py` 中的 `BOOK_META` 和 `CHAPTERS` 配置，然后运行：

```bash
python3 build_epub.py [chapters_dir] [output.epub]
```

默认从 `../chapters/` 读取章节文件，输出 `../output.epub`。

## 配置 build_epub.py

### 书籍元数据

```python
BOOK_META = {
    "title": "书名",
    "creator": "作者",
    "publisher": "出版社",
    "date": "2023-09",
    "language": "zh-CN",
}
```

### 章节列表

```python
CHAPTERS = [
    # (文件id,  章节标题,   源文件名,   起始行, 结束行)
    ("ch00a", "鸣谢",       "00-鸣谢与前言.md", 1,   7),
    ("ch00b", "前言",       "00-鸣谢与前言.md", 10,  None),  # None = 读到文件末尾
    ("ch01",  "第一章 …",  "01-xxx.md"),                      # 省略行号 = 读整个文件
    ...
]
```

## 依赖

- Python 3.6+，仅使用标准库（`zipfile`, `re`, `html`, `uuid`）
- 零外部依赖

## 已知限制

- Markdown → HTML 转换仅覆盖标题、段落、粗体、斜体、分隔线
- 不支持列表、表格、脚注、图片等复杂格式
- 面对特殊的 OCR 噪声可能需要手动调整正则表达式
