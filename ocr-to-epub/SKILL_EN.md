# OCR to EPUB — Recover Ebooks from OCR Text

Recover a structured, readable EPUB ebook from a book's OCR-scanned text and its table of contents.

## Input

Two pieces of information are required:

- **Book body text**: OCR output, typically one large text file (Markdown or plain text) with content arranged in chapter order.
- **Table of contents**: A list of chapter titles and hierarchy. This can be:
  - A skeleton outline file (Markdown list)
  - The book's original TOC page, itself OCR-scanned
  - The user describing the structure verbally

## Workflow

### 1. Understand the structure

Read the TOC information first. Map out the book's full structure:
- Front matter (acknowledgments, preface, etc.)
- Parts / volumes
- Chapter titles and section hierarchy

Scan the OCR body text to confirm completeness and assess OCR noise level (character errors, broken lines, garbled text).

### 2. Extract chapters

Create a `chapters/` directory. Following the TOC structure, locate each chapter's start and end in the OCR text, extract the full body, and write it to an independent file.

Naming convention: `{number}-{chapter-title}.md` (e.g., `01-introduction.md`).

If front matter and a chapter body are contiguous in the OCR scan, split them by line-number ranges from the same source file.

Clean OCR noise during extraction:
- Merge inappropriate line breaks (mid-sentence breaks)
- Repair broken English/pinyin words
- Remove garbled characters and OCR tag artifacts
- **Preserve all substantive argument content** — do not add or remove ideas

### 3. Generate the EPUB

#### Option A: Use build_epub.py (recommended)

Write a `book.json` configuration file, then run:

```bash
python3 build_epub.py book.json [chapters_dir] [output.epub]
```

`book.json` structure:

```json
{
  "meta": {
    "title": "Book Title",
    "creator": "Author Name",
    "publisher": "Publisher",
    "date": "2023-09",
    "language": "en"
  },
  "chapters": [
    {"id": "ch00a", "title": "Acknowledgments", "file": "00-frontmatter.md", "lines": [1, 7]},
    {"id": "ch00b", "title": "Preface",          "file": "00-frontmatter.md", "lines": [10, null]},
    {"id": "ch01",  "title": "Chapter 1 …",      "file": "01-chapter1.md"}
  ]
}
```

- `id` — unique EPUB internal identifier
- `title` — chapter heading
- `file` — source filename inside the chapters directory
- `lines` (optional) — `[start, end]`, 1-based; `null` end means read to EOF. Omit to read the whole file.

#### Option B: Use other tools

You can also use pandoc or similar tools to generate the EPUB, but be aware:
- Avoid `---` horizontal rules (pandoc interprets them as YAML metadata block boundaries, which can merge or drop chapters)
- Ensure each chapter starts with a single H1 heading for correct splitting

### 4. Verify

After generating the EPUB, inspect its internal structure with `unzip -l`:
- Chapter count matches the TOC
- Each chapter is an independent `.xhtml` file
- The TOC (`toc.ncx` or `nav.xhtml`) lists all chapter titles
- Open in a reader (Apple Books, etc.) to confirm readability

## Notes

- `build_epub.py` has **zero external dependencies** — uses only the Python standard library (`zipfile`, `re`, `html`, `json`, `uuid`)
- The Markdown → HTML converter covers headings, paragraphs, bold, italic, and horizontal rules. It does not support lists, tables, images, or other complex formatting.
- If the OCR body is very large (>200 KB), read it in chunks to stay within the AI's context window.
- The core of this skill is the *identify structure → extract chapters → clean noise* workflow. `build_epub.py` only handles the final packaging step.
