# ocr-to-epub

The skill files in this directory:

| File | Purpose |
|------|---------|
| `SKILL.md` | Workflow instructions for the AI assistant (Chinese) |
| `SKILL_EN.md` | Same workflow, in English |
| `build_epub.py` | Zero-dependency EPUB packager (reads a `book.json` config) |

## Quick start

```bash
# 1. Prepare chapter Markdown files in a chapters/ directory

# 2. Write a book.json
cat > book.json << 'EOF'
{
  "meta": {
    "title": "My Book",
    "creator": "Author Name",
    "language": "en"
  },
  "chapters": [
    {"id": "ch01", "title": "Chapter 1", "file": "01-chapter1.md"},
    {"id": "ch02", "title": "Chapter 2", "file": "02-chapter2.md"}
  ]
}
EOF

# 3. Build the EPUB
python3 build_epub.py book.json chapters/ mybook.epub
```

## book.json reference

**meta** (required):

| Field | Description |
|-------|-------------|
| `title` | Book title |
| `creator` | Author |
| `publisher` | Publisher (optional) |
| `date` | Publication date (optional) |
| `language` | Language code, defaults to `zh-CN` |

**chapters** list — each entry:

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique EPUB spine identifier (e.g. `ch01`) |
| `title` | Yes | Chapter heading |
| `file` | Yes | Source filename inside the chapters directory |
| `lines` | No | `[start, end]` 1-based line range; `null` end = read to EOF. Omit to read entire file |

## Dependencies

- Python 3.6+
- Standard library only (`zipfile`, `re`, `html`, `json`, `uuid`)
