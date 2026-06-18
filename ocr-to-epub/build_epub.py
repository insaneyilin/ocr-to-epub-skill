#!/usr/bin/env python3
"""Build an EPUB file from chapter markdown files.

Usage:
    python3 build_epub.py book.json [chapters_dir] [output.epub]

    book.json is a JSON file with book metadata and chapter list (see below).
    chapters_dir defaults to ./chapters, output to ./output.epub.

Example book.json:
{
  "meta": {
    "title": "Book Title",
    "creator": "Author Name",
    "publisher": "Publisher",
    "date": "2023-09",
    "language": "en"
  },
  "chapters": [
    {"id": "ch00", "title": "Preface", "file": "00-preface.md", "lines": [1, 7]},
    {"id": "ch01", "title": "Chapter 1", "file": "01-chapter1.md"}
  ]
}

Each chapter entry:
  - id:    short file-id used in the EPUB spine (required)
  - title: chapter heading (required)
  - file:  source markdown filename inside chapters_dir (required)
  - lines: optional [start, end] 1-based line range; omit to read the whole file.
           End can be null to read from start to EOF.
"""

import json, zipfile, os, re, html, uuid, sys


EPUB_CSS = (
    'body { font-family: "Songti SC", "STSong", serif; line-height: 1.8; margin: 1em 2em; }\n'
    'h1 { font-size: 1.5em; margin: 1.5em 0 0.8em 0; text-align: center; }\n'
    'h2 { font-size: 1.25em; margin: 1.2em 0 0.5em 0; }\n'
    'h3 { font-size: 1.1em; margin: 1em 0 0.3em 0; }\n'
    'h4 { font-size: 1.05em; }\n'
    'p { text-indent: 2em; margin: 0.5em 0; }\n'
    'hr { margin: 2em 0; border: none; border-top: 1px solid #ccc; }\n'
)


def md2html(text: str) -> str:
    """Convert a small subset of Markdown to HTML for EPUB body."""
    text = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.+)$',  r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$',   r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$',    r'<h1>\1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r'^---$', '<hr/>', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)

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
                parts, buf = [], []
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


def build_epub(book_cfg: dict, chapters_dir: str, output_path: str):
    meta = book_cfg['meta']
    chapters = book_cfg['chapters']
    uid = uuid.uuid4().hex

    chapter_htmls = []
    toc_items = []

    for i, ch in enumerate(chapters):
        cid = ch['id']
        title = ch['title']
        path = os.path.join(chapters_dir, ch['file'])
        line_range = ch.get('lines')

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        if line_range:
            lines = content.split('\n')
            start, end = line_range[0], line_range[1]
            selected = '\n'.join(lines[start - 1:end]) if end else '\n'.join(lines[start - 1:])
        else:
            selected = content

        selected = re.sub(r'^# .+\n', '', selected, count=1)
        selected = selected.lstrip('\n')
        body = md2html(selected)

        chap_id = f'chapter_{i}'
        page = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh-CN">\n'
            '<head>\n  <meta charset="UTF-8"/>\n'
            f'  <title>{html.escape(title)}</title>\n'
            '  <link rel="stylesheet" type="text/css" href="../styles/stylesheet1.css"/>\n'
            '</head>\n<body>\n'
            f'  <h1>{html.escape(title)}</h1>\n{body}\n'
            '</body>\n</html>'
        )
        chapter_htmls.append((cid, page))
        toc_items.append((cid, title, chap_id))

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype', 'application/epub+zip', zipfile.ZIP_STORED)

        z.writestr('META-INF/container.xml', (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">\n'
            '  <rootfiles>\n'
            '    <rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/>\n'
            '  </rootfiles>\n'
            '</container>'))

        z.writestr('EPUB/styles/stylesheet1.css', EPUB_CSS)

        for cid, page in chapter_htmls:
            z.writestr(f'EPUB/text/{cid}.xhtml', page.encode('utf-8'))

        ncx_nav = ''
        for n, (cid, title, chap_id) in enumerate(toc_items, 1):
            ncx_nav += (
                f'    <navPoint id="{chap_id}" playOrder="{n}">\n'
                f'      <navLabel><text>{html.escape(title)}</text></navLabel>\n'
                f'      <content src="text/{cid}.xhtml"/>\n'
                f'    </navPoint>\n')

        ncx = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" '
            '"http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">\n'
            '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
            f'  <head>\n    <meta name="dtb:uid" content="{uid}"/>\n'
            '    <meta name="dtb:depth" content="1"/>\n'
            '    <meta name="dtb:totalPageCount" content="0"/>\n'
            '    <meta name="dtb:maxPageNumber" content="0"/>\n  </head>\n'
            f'  <docTitle><text>{html.escape(meta["title"])}</text></docTitle>\n'
            f'  <docAuthor><text>{html.escape(meta["creator"])}</text></docAuthor>\n'
            f'  <navMap>\n{ncx_nav}  </navMap>\n</ncx>')
        z.writestr('EPUB/toc.ncx', ncx.encode('utf-8'))

        nav_links = ''
        for cid, title, _ in toc_items:
            nav_links += f'      <li><a href="text/{cid}.xhtml">{html.escape(title)}</a></li>\n'

        nav = (
            '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh-CN">\n'
            '<head><title>目录</title></head>\n<body>\n  <nav epub:type="toc">\n'
            '    <h1>目录</h1>\n    <ol>\n'
            f'{nav_links}    </ol>\n  </nav>\n</body>\n</html>')
        z.writestr('EPUB/nav.xhtml', nav.encode('utf-8'))

        manifest = (
            '    <item id="css" href="styles/stylesheet1.css" media-type="text/css"/>\n'
            '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>\n'
            '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>\n')
        spine = ''
        for i, (_cid, _title, __) in enumerate(toc_items):
            mid = f'item_{i}'
            manifest += f'    <item id="{mid}" href="text/{_cid}.xhtml" media-type="application/xhtml+xml"/>\n'
            spine += f'    <itemref idref="{mid}"/>\n'

        opf = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="book-id" version="3.0">\n'
            '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
            f'    <dc:title>{html.escape(meta["title"])}</dc:title>\n'
            f'    <dc:creator>{html.escape(meta["creator"])}</dc:creator>\n'
            f'    <dc:language>{meta.get("language", "zh-CN")}</dc:language>\n'
            f'    <dc:publisher>{html.escape(meta.get("publisher", ""))}</dc:publisher>\n'
            f'    <dc:date>{meta.get("date", "")}</dc:date>\n'
            f'    <dc:identifier id="book-id">urn:uuid:{uid}</dc:identifier>\n'
            f'    <meta property="dcterms:modified">{meta.get("date", "2023")}T00:00:00Z</meta>\n'
            '  </metadata>\n'
            f'  <manifest>\n{manifest}  </manifest>\n'
            f'  <spine toc="ncx">\n{spine}  </spine>\n</package>')
        z.writestr('EPUB/content.opf', opf.encode('utf-8'))

    size_kb = os.path.getsize(output_path) / 1024
    print(f'EPUB created: {output_path} ({size_kb:.0f} KB, {len(chapter_htmls)} chapters)')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        book_cfg = json.load(f)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    chapters_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(script_dir, '..', 'chapters')
    output_path = sys.argv[3] if len(sys.argv) > 3 else os.path.join(script_dir, '..', 'output.epub')
    build_epub(book_cfg, chapters_dir, output_path)
