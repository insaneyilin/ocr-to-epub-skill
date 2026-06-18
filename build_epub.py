#!/usr/bin/env python3
"""Build an EPUB file from chapter markdown files.

Usage:
    python3 build_epub.py [chapters_dir] [output_path]

Defaults:
    chapters_dir = ./chapters
    output_path  = ./output.epub

Configuration:
    Edit the BOOK_META dict and CHAPTERS list below to match your book.
"""

import zipfile, os, re, html, uuid, sys

# ── Book metadata ────────────────────────────────────────────
BOOK_META = {
    "title": "跨主体性",
    "creator": "赵汀阳",
    "publisher": "生活·读书·新知三联书店",
    "date": "2023-09",
    "language": "zh-CN",
}

# ── Chapter list ─────────────────────────────────────────────
# Each entry: (file_id, chapter_title, source_filename, start_line, end_line)
# start_line and end_line are 1-based line numbers into the source file.
# Use None for start_line to read the whole file, None for end_line to read to EOF.
CHAPTERS = [
    ("ch00a", "鸣谢",           "00-鸣谢与前言.md", 1, 7),
    ("ch00b", "前言：如何定义跨主体性？", "00-鸣谢与前言.md", 10, None),
    ("ch01",  "第一章 跨文化聚点研究",    "01-跨文化聚点研究.md"),
    ("ch02",  "第二章 关于跨文化和跨主体性的一个讨论", "02-关于跨文化和跨主体性的一个讨论.md"),
    ("ch03",  "第三章 中国哲学的身份疑案", "03-中国哲学的身份疑案.md"),
    ("ch04",  "第四章 时间和历史的概念",   "04-时间和历史的概念.md"),
    ("ch05",  "第五章 柏林论辩",           "05-柏林论辩.md"),
    ("ch06",  "第六章 全球正义如何可能",   "06-全球正义如何可能.md"),
    ("ch07",  "第七章 人工智能的反存在论", "07-人工智能的反存在论.md"),
    ("ch08",  "第八章 人工智能的自我意识何以可能？", "08-人工智能的自我意识何以可能.md"),
    ("ch09",  '第九章 最坏可能世界与"安全声明"',      "09-最坏可能世界与安全声明.md"),
    ("ch10",  "第十章 假如元宇宙成为一个存在论事件",  "10-假如元宇宙成为一个存在论事件.md"),
    ("ch11",  "第十一章 GPT提出的新问题",             "11-GPT提出的新问题.md"),
    ("ch12",  "第十二章 替人工智能着想",              "12-替人工智能着想.md"),
]

# ── CSS ──────────────────────────────────────────────────────
EPUB_CSS = (
    'body { font-family: "Songti SC", "STSong", serif; line-height: 1.8; margin: 1em 2em; }\n'
    'h1 { font-size: 1.5em; margin: 1.5em 0 0.8em 0; text-align: center; }\n'
    'h2 { font-size: 1.25em; margin: 1.2em 0 0.5em 0; }\n'
    'h3 { font-size: 1.1em; margin: 1em 0 0.3em 0; }\n'
    'h4 { font-size: 1.05em; }\n'
    'p { text-indent: 2em; margin: 0.5em 0; }\n'
    'hr { margin: 2em 0; border: none; border-top: 1px solid #ccc; }\n'
)

# ── Markdown → HTML converter ────────────────────────────────

def md2html(text: str) -> str:
    """Convert a small subset of Markdown to HTML for EPUB body."""

    # Headings
    text = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.+)$',  r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$',   r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$',    r'<h1>\1</h1>', text, flags=re.MULTILINE)

    # Horizontal rules
    text = re.sub(r'^---$', '<hr/>', text, flags=re.MULTILINE)

    # Bold / italic
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)

    # Paragraphs – split on blank lines, wrap non-tag blocks in <p>
    paragraphs = []
    for block in text.split('\n\n'):
        block = block.strip()
        if not block:
            continue
        if block.startswith('<h') or block.startswith('<hr'):
            paragraphs.append(block)
        else:
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            if lines:
                parts = []
                buf = []
                for line in lines:
                    if line.startswith('<h') or line.startswith('<hr'):
                        if buf:
                            parts.append('<p>' + '<br/>\n'.join(buf) + '</p>')
                            buf = []
                        parts.append(line)
                    else:
                        buf.append(line)
                if buf:
                    parts.append('<p>' + '<br/>\n'.join(buf) + '</p>')
                paragraphs.extend(parts)

    return '\n'.join(paragraphs)


# ── EPUB builder ──────────────────────────────────────────────

def build_epub(chapters_dir: str, output_path: str):
    chapter_htmls = []
    toc_items = []
    uid = uuid.uuid4().hex

    for i, entry in enumerate(CHAPTERS):
        cid = entry[0]
        title = entry[1]
        filename = entry[2]
        start = entry[3] if len(entry) > 3 else None
        end = entry[4] if len(entry) > 4 else None

        path = os.path.join(chapters_dir, filename)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        if start is not None:
            lines = content.split('\n')
            selected = '\n'.join(lines[start - 1:end]) if end else '\n'.join(lines[start - 1:])
        else:
            selected = content

        # Remove the first H1 (chapter title) – we insert our own
        selected = re.sub(r'^# .+\n', '', selected, count=1)
        # Remove part-divider H1s
        selected = re.sub(r'^# 第[一二三]部分.+\n+', '', selected, flags=re.MULTILINE)
        selected = selected.lstrip('\n')

        body = md2html(selected)

        chap_id = f'chapter_{i}'
        page = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh-CN">\n'
            '<head>\n'
            '  <meta charset="UTF-8"/>\n'
            f'  <title>{html.escape(title)}</title>\n'
            '  <link rel="stylesheet" type="text/css" href="../styles/stylesheet1.css"/>\n'
            '</head>\n'
            '<body>\n'
            f'  <h1>{html.escape(title)}</h1>\n'
            f'{body}\n'
            '</body>\n'
            '</html>'
        )
        chapter_htmls.append((cid, page))
        toc_items.append((cid, title, chap_id))

    # ── Write ZIP ──────────────────────────────────────────
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as z:
        # mimetype (uncompressed, first entry)
        z.writestr('mimetype', 'application/epub+zip', zipfile.ZIP_STORED)

        # container.xml
        z.writestr('META-INF/container.xml', (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">\n'
            '  <rootfiles>\n'
            '    <rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/>\n'
            '  </rootfiles>\n'
            '</container>'
        ))

        # Stylesheet
        z.writestr('EPUB/styles/stylesheet1.css', EPUB_CSS)

        # Chapter XHTML
        for cid, page in chapter_htmls:
            z.writestr(f'EPUB/text/{cid}.xhtml', page.encode('utf-8'))

        # NCX
        ncx_nav = ''
        for n, (cid, title, chap_id) in enumerate(toc_items, 1):
            ncx_nav += (
                f'    <navPoint id="{chap_id}" playOrder="{n}">\n'
                f'      <navLabel><text>{html.escape(title)}</text></navLabel>\n'
                f'      <content src="text/{cid}.xhtml"/>\n'
                f'    </navPoint>\n'
            )

        ncx = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" '
            '"http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">\n'
            '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
            '  <head>\n'
            f'    <meta name="dtb:uid" content="{uid}"/>\n'
            '    <meta name="dtb:depth" content="1"/>\n'
            '    <meta name="dtb:totalPageCount" content="0"/>\n'
            '    <meta name="dtb:maxPageNumber" content="0"/>\n'
            '  </head>\n'
            f'  <docTitle><text>{html.escape(BOOK_META["title"])}</text></docTitle>\n'
            f'  <docAuthor><text>{html.escape(BOOK_META["creator"])}</text></docAuthor>\n'
            '  <navMap>\n'
            f'{ncx_nav}'
            '  </navMap>\n'
            '</ncx>'
        )
        z.writestr('EPUB/toc.ncx', ncx.encode('utf-8'))

        # Nav XHTML
        nav_links = ''
        for cid, title, _chap_id in toc_items:
            nav_links += f'      <li><a href="text/{cid}.xhtml">{html.escape(title)}</a></li>\n'

        nav = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh-CN">\n'
            '<head><title>目录</title></head>\n'
            '<body>\n'
            '  <nav epub:type="toc">\n'
            '    <h1>目录</h1>\n'
            '    <ol>\n'
            f'{nav_links}'
            '    </ol>\n'
            '  </nav>\n'
            '</body>\n'
            '</html>'
        )
        z.writestr('EPUB/nav.xhtml', nav.encode('utf-8'))

        # content.opf
        manifest = (
            '    <item id="css" href="styles/stylesheet1.css" media-type="text/css"/>\n'
            '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>\n'
            '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>\n'
        )
        spine = ''
        for i, (_cid, _title, __chap_id) in enumerate(toc_items):
            mid = f'item_{i}'
            manifest += f'    <item id="{mid}" href="text/{_cid}.xhtml" media-type="application/xhtml+xml"/>\n'
            spine += f'    <itemref idref="{mid}"/>\n'

        opf = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="book-id" version="3.0">\n'
            '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
            f'    <dc:title>{html.escape(BOOK_META["title"])}</dc:title>\n'
            f'    <dc:creator>{html.escape(BOOK_META["creator"])}</dc:creator>\n'
            f'    <dc:language>{BOOK_META["language"]}</dc:language>\n'
            f'    <dc:publisher>{html.escape(BOOK_META["publisher"])}</dc:publisher>\n'
            f'    <dc:date>{BOOK_META["date"]}</dc:date>\n'
            f'    <dc:identifier id="book-id">urn:uuid:{uid}</dc:identifier>\n'
            f'    <meta property="dcterms:modified">{BOOK_META["date"]}T00:00:00Z</meta>\n'
            '  </metadata>\n'
            '  <manifest>\n'
            f'{manifest}'
            '  </manifest>\n'
            '  <spine toc="ncx">\n'
            f'{spine}'
            '  </spine>\n'
            '</package>'
        )
        z.writestr('EPUB/content.opf', opf.encode('utf-8'))

    size_kb = os.path.getsize(output_path) / 1024
    print(f'EPUB created: {output_path} ({size_kb:.0f} KB, {len(chapter_htmls)} chapters)')


if __name__ == '__main__':
    chapters_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'chapters')
    output_path  = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'output.epub')
    build_epub(chapters_dir, output_path)
