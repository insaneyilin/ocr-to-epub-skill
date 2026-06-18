# OCR to EPUB

A Claude Code / Codex skill that recovers a structured EPUB ebook from OCR-scanned text and a table of contents. The AI assistant extracts chapters, cleans OCR noise, and packages the result — no external dependencies beyond Python's standard library.

## What's included

```
ocr-to-epub-skill/
├── README.md              ← Chinese version (default)
├── README_EN.md           ← English version (this file)
└── ocr-to-epub/           ← the skill itself
    ├── SKILL.md           ← instructions the AI reads at runtime
    ├── build_epub.py      ← zero-dependency EPUB packager
    └── README.md          ← skill-level docs
```

## How it works

1. **You provide** an OCR dump of a book (raw text or Markdown) and a table of contents (skeleton outline, scanned TOC page, or just describe the chapter structure).
2. **The AI** reads the skeleton, finds chapter boundaries in the OCR text, extracts each chapter into a clean Markdown file under `chapters/`, and repairs common OCR artifacts (garbled characters, broken lines, split words).
3. **`build_epub.py`** packs those chapter files into a valid EPUB (`.epub`) with proper metadata, table of contents, and CSS styling — powered entirely by Python's standard library.

## Install to Claude Code

Add the skill to your project's `.claude/settings.json`:

```json
{
  "skills": {
    "ocr-to-epub": {
      "path": "ocr-to-epub-skill/ocr-to-epub",
      "description": "Recover a structured EPUB ebook from OCR-scanned text and a table of contents."
    }
  }
}
```

Or register it globally in `~/.claude/settings.json` (use an absolute path for `"path"`).

Once registered, Claude Code loads `SKILL.md` automatically whenever you ask to convert OCR text into an ebook.

### As a one-shot prompt

You can also copy the contents of `SKILL.md` into your prompt for any AI assistant that supports long context. The skill is mostly a workflow description — the only executable tool is `build_epub.py`.

## Install to Codex (OpenAI)

1. Place the `ocr-to-epub/` directory inside your Codex project.
2. In your Codex session, instruct the agent to read `SKILL.md` as its workflow reference:

   ```
   Read ocr-to-epub/SKILL.md and follow the workflow described there.
   Here is my OCR text: [paste or file path]
   Here is the table of contents: [paste or file path]
   ```

3. When the chapters are ready, run:

   ```bash
   python3 ocr-to-epub/build_epub.py book.json chapters/ output.epub
   ```

## Using build_epub.py standalone

`build_epub.py` is completely independent of any AI assistant — use it directly from the command line:

```bash
python3 build_epub.py book.json [chapters_dir] [output.epub]
```

Where `book.json` looks like:

```json
{
  "meta": {
    "title": "My Book",
    "creator": "Author Name",
    "publisher": "Publisher Name",
    "date": "2024-01",
    "language": "en"
  },
  "chapters": [
    {"id": "ch01", "title": "Chapter 1 Title", "file": "01-chapter1.md"},
    {"id": "ch02", "title": "Chapter 2 Title", "file": "02-chapter2.md"}
  ]
}
```

Each chapter entry:

| Field   | Required | Description |
|---------|----------|-------------|
| `id`    | Yes      | Unique EPUB spine identifier (e.g. `ch01`) |
| `title` | Yes      | Chapter heading |
| `file`  | Yes      | Source Markdown file inside `chapters_dir` |
| `lines` | No       | `[start, end]` 1-based line range; `null` end = read to EOF. Omit to read entire file |

## Dependencies

- Python 3.6+
- **Zero external packages** — uses only `zipfile`, `re`, `html`, `json`, `uuid`, `sys`, `os` from the standard library.

## End-to-end example

You just hand the OCR text and table of contents to the AI assistant — the rest is fully automated:

1. The AI extracts each chapter, cleans OCR noise, and writes `chapters/`
2. The AI generates `book.json` to define chapter order
3. The AI runs `python3 build_epub.py book.json chapters/ output.epub`
4. A structured EPUB is produced, ready for Apple Books or any EPUB reader
