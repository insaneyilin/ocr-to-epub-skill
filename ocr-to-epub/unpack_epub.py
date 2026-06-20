#!/usr/bin/env python3
"""Unpack an EPUB file back into chapter Markdown files and book.json.

Usage:
    python3 unpack_epub.py input.epub [output_dir]

    output_dir defaults to ./unpacked.

Output structure:
    output_dir/
    ├── book.json
    └── chapters/
        ├── 01-Chapter-Title.md
        ├── 02-Chapter-Title.md
        └── ...
"""

import json, zipfile, os, re, html, sys, xml.etree.ElementTree as ET

OPF_NS = 'http://www.idpf.org/2007/opf'
DC_NS = 'http://purl.org/dc/elements/1.1/'
NCX_NS = 'http://www.daisy.org/z3986/2005/ncx/'


def xhtml_to_md(body: str) -> str:
    """Convert XHTML body content to Markdown."""
    text = body

    # Fix <br/> inside heading tags: replace with space so title stays on one line
    for level in (4, 3, 2, 1):
        tag = f'h{level}'
        text = re.sub(
            rf'(<{tag}[^>]*>.*?)<br\s*/?>(.*?</{tag}>)',
            r'\1 \2',
            text, flags=re.DOTALL
        )

    # Convert remaining <br/> → newline, <hr/> → ---
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<hr\s*/?>', '\n---\n', text)

    for level in (4, 3, 2, 1):
        tag = f'h{level}'
        prefix = '#' * level
        text = re.sub(
            rf'<{tag}[^>]*>(.+?)</{tag}>',
            lambda m, p=prefix: f'\n{p} {re.sub(r"\s+", " ", m.group(1).strip())}\n',
            text, flags=re.DOTALL
        )

    text = re.sub(r'<strong[^>]*>(.+?)</strong>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<em[^>]*>(.+?)</em>', r'*\1*', text, flags=re.DOTALL)
    text = re.sub(r'<strong[^>]*><em[^>]*>(.+?)</em></strong>', r'***\1***', text, flags=re.DOTALL)

    text = re.sub(r'<p[^>]*>(.*?)</p>',
                  lambda m: '\n' + m.group(1).strip() + '\n',
                  text, flags=re.DOTALL)

    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    # Clean up \r and multiple blank lines
    text = text.replace('\r', '')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip() + '\n'


def parse_opf(opf_xml: str):
    """Extract metadata, spine, and NCX path from content.opf.

    Returns: (meta_dict, spine_list, ncx_path_or_None)
    """
    root = ET.fromstring(opf_xml)

    meta = {}
    for tag, key in [('title', 'title'), ('creator', 'creator'),
                     ('publisher', 'publisher'), ('date', 'date'),
                     ('language', 'language')]:
        el = root.find(f'.//{{{DC_NS}}}{tag}')
        if el is not None and el.text:
            meta[key] = el.text.strip()

    meta.setdefault('language', 'zh-CN')
    meta.setdefault('title', 'Untitled')
    meta.setdefault('creator', 'Unknown')

    manifest = {}
    ncx_href = None
    for item in root.findall(f'.//{{{OPF_NS}}}manifest/{{{OPF_NS}}}item'):
        iid = item.get('id')
        href = item.get('href')
        mtype = item.get('media-type', '')
        props = item.get('properties', '')
        if iid and href:
            manifest[iid] = {'href': href, 'media_type': mtype}
            if mtype == 'application/x-dtbncx+xml':
                ncx_href = href

    spine = []
    for itemref in root.findall(f'.//{{{OPF_NS}}}spine/{{{OPF_NS}}}itemref'):
        iid = itemref.get('idref')
        if iid and iid in manifest:
            entry = dict(manifest[iid])
            entry['id'] = iid
            spine.append(entry)

    return meta, spine, ncx_href


def parse_ncx(ncx_xml: str) -> list:
    """Extract all navPoints from toc.ncx (handles nested navPoints)."""
    try:
        root = ET.fromstring(ncx_xml)
    except ET.ParseError:
        return []

    chapters = []
    for nav in root.findall(f'.//{{{NCX_NS}}}navPoint'):
        label = nav.find(f'{{{NCX_NS}}}navLabel')
        content = nav.find(f'{{{NCX_NS}}}content')
        title = ''
        src = ''
        if label is not None:
            text_el = label.find(f'{{{NCX_NS}}}text')
            if text_el is not None and text_el.text:
                title = text_el.text.strip()
        if content is not None:
            src = content.get('src', '')
        if title:
            chapters.append({'title': title, 'src': src})
    return chapters


def sanitize_filename(title: str) -> str:
    """Turn a chapter title into a safe filename stem."""
    name = title.strip().replace('/', '-').replace('\\', '-')
    name = re.sub(r'[<>:"|?*]', '', name)
    name = name.strip('. ')
    return name or 'untitled'


def fallback_title(manifest_id: str) -> str:
    """Derive a readable chapter name from a manifest ID like 'x_cover.xhtml'."""
    name = re.sub(r'\.x?html?$', '', manifest_id)
    name = re.sub(r'^x_', '', name)
    name = name.replace('_', ' ').replace('-', ' ')
    return name.strip().title() or 'Untitled'


def unpack_epub(epub_path: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    chapters_dir = os.path.join(output_dir, 'chapters')
    os.makedirs(chapters_dir, exist_ok=True)

    with zipfile.ZipFile(epub_path, 'r') as z:
        # Parse container to find OPF path
        container = z.read('META-INF/container.xml').decode('utf-8')
        c_root = ET.fromstring(container)
        c_ns = 'urn:oasis:names:tc:opendocument:xmlns:container'
        opf_path = c_root.find(f'.//{{{c_ns}}}rootfile').get('full-path')
        opf_dir = os.path.dirname(opf_path)  # e.g. "OEBPS" or "EPUB"

        opf_xml = z.read(opf_path).decode('utf-8')
        meta, spine, ncx_href = parse_opf(opf_xml)

        # Try to parse NCX-based TOC
        toc = []
        ncx_path = None
        if ncx_href:
            ncx_path = os.path.normpath(os.path.join(opf_dir, ncx_href))
        else:
            # Fallback: look for toc.ncx next to OPF
            guess = os.path.join(opf_dir, 'toc.ncx')
            if guess in z.namelist():
                ncx_path = guess

        if ncx_path:
            try:
                toc_xml = z.read(ncx_path).decode('utf-8')
                toc = parse_ncx(toc_xml)
            except (KeyError, ET.ParseError):
                pass

        # Build chapter list from spine, merging TOC titles
        chapters = []
        for i, item in enumerate(spine):
            href = item['href']
            full_path = os.path.normpath(os.path.join(opf_dir, href))
            src_filename = href.split('/')[-1]

            # Find title from TOC by matching src filename
            title = ''
            for t in toc:
                t_filename = t['src'].split('/')[-1] if t['src'] else ''
                if t_filename == src_filename:
                    title = t['title']
                    break
            if not title:
                title = fallback_title(item.get('id', f'ch{i}'))

            chapters.append({
                'id': f'ch{i:02d}',
                'title': title,
                'path': full_path,
            })

        # Extract and convert each chapter
        written = []
        full_md_parts = []
        for i, ch in enumerate(chapters):
            try:
                xhtml = z.read(ch['path']).decode('utf-8')
            except KeyError:
                print(f"Warning: missing file {ch['path']}, skipping")
                continue

            body_match = re.search(r'<body[^>]*>(.*?)</body>', xhtml, re.DOTALL)
            if body_match:
                body = body_match.group(1)
                md_text = xhtml_to_md(body)
            else:
                md_text = ''

            # Skip pages with no real content (cover images, blank pages)
            if not re.search(r'\S', md_text):
                continue

            safe_name = sanitize_filename(ch['title'])
            filename = f'{len(written) + 1:02d}-{safe_name}.md'
            filepath = os.path.join(chapters_dir, filename)

            counter = 1
            while os.path.exists(filepath):
                filename = f'{len(written) + 1:02d}-{safe_name}-{counter}.md'
                filepath = os.path.join(chapters_dir, filename)
                counter += 1

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(md_text)

            ch['file'] = filename
            written.append(ch)
            full_md_parts.append((ch['title'], md_text))
            print(f'  {filename}')

    # Write book.json
    book_json = {
        'meta': meta,
        'chapters': [{'id': ch['id'], 'title': ch['title'], 'file': ch['file']}
                      for ch in written],
    }
    book_json_path = os.path.join(output_dir, 'book.json')
    with open(book_json_path, 'w', encoding='utf-8') as f:
        json.dump(book_json, f, ensure_ascii=False, indent=2)

    # Write a single combined Markdown file for the full book
    full_md = f"# {meta['title']}\n\n"
    full_md += f"作者：{meta['creator']}\n"
    for title, md_text in full_md_parts:
        full_md += f"\n\n# {title}\n\n"
        # Drop leading H1 lines to avoid duplicate heading
        body_text = md_text
        while body_text.startswith('# '):
            body_text = body_text.split('\n', 1)[1].lstrip('\n')
        full_md += body_text
    full_md = full_md.strip() + '\n'

    full_name = sanitize_filename(meta['title']) + '.md'
    full_path = os.path.join(output_dir, full_name)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(full_md)

    full_name = sanitize_filename(meta['title']) + '.md'
    full_path = os.path.join(output_dir, full_name)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(full_md)

    print(f'\nUnpacked {len(written)} chapters to {output_dir}/')
    print(f'  book.json  — metadata + chapter manifest')
    print(f'  chapters/  — {len(written)} Markdown files')
    print(f'  {full_name}  — combined full book')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    epub_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'unpacked')
    unpack_epub(epub_path, output_dir)
