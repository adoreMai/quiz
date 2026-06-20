"""
大学语文各课测试题 提取脚本
"""
import sys, io, os, re, json, glob, docx, zipfile

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

INPUT_DIR = r"d:\Data\Desktop\共同体项目\大学语文各课测试题"
OUTPUT_FILE = r"d:\Data\Desktop\共同体项目\quiz\subjects\大学语文.json"

SECTION_MAP = {
    '填空题': ('填空题','blank'), '填空': ('填空题','blank'),
    '单选题': ('单选题','single'), '选择题': ('单选题','single'), '单选': ('单选题','single'),
    '多选题': ('多选题','multi'), '多选': ('多选题','multi'),
    '判断题': ('判断题','judge'), '判断': ('判断题','judge'),
    '简答题': ('简答题','short'), '简答': ('简答题','short'),
    '古文今译': ('古文今译题','translation'), '今译': ('古文今译题','translation'),
    '翻译': ('古文今译题','translation'),
    '论述': ('论述题','essay'),
    '名词解释': ('简答题','short'),
    '明辨': ('判断题','judge'),
    '默写': ('填空题','blank'),
    '作文': ('论述题','essay'),
    '写作': ('论述题','essay'),
}

def extract_paragraphs(filepath):
    # python-docx
    try:
        doc = docx.Document(filepath)
        return [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    except: pass
    # zipfile
    try:
        z = zipfile.ZipFile(filepath)
        xml = z.read('word/document.xml').decode('utf-8')
        raw = re.sub(r'<(?:w:p|w:r)[^>]*>', '\n', xml)
        raw = re.sub(r'<[^>]+>', '', raw)
        return [l.strip() for l in raw.split('\n') if l.strip()]
    except: pass
    # olefile
    try:
        import olefile
        ole = olefile.OleFileIO(filepath)
        wd = ole.openstream('WordDocument').read()
        text = wd.decode('utf-16-le', errors='ignore')
        ole.close()
        chars = []
        for ch in text:
            cp = ord(ch)
            if (0x4e00 <= cp <= 0x9fff) or (0x3000 <= cp <= 0x303f) or \
               (0xff00 <= cp <= 0xffef) or (0x20 <= cp <= 0x7e) or cp in (0x0a, 0x0d):
                chars.append(ch)
        raw = ''.join(chars)
        # Insert breaks at key boundaries
        raw = re.sub(r'(\d+\.)', r'\n\1', raw)
        raw = re.sub(r'([一二三四五六七八九十]、)', r'\n\1', raw)
        raw = re.sub(r'(答案[：:]|正确答案[：:])', r'\n\1', raw)
        raw = re.sub(r'([。）\)])([A-F][\.、])', r'\1\n\2', raw)
        return [l.strip() for l in raw.split('\n') if l.strip()]
    except: return None

def split_inline_opts(text):
    """Split A.xxx B.yyy C.zzz into individual options"""
    # Normalize: ensure space before each option letter
    text = re.sub(r'([B-F])[\.、．]', r'\n\1.', text)
    text = re.sub(r'([A-F])[\.、．]', lambda m: f'\n{m.group(1)}.', text, count=1)
    parts = [p.strip() for p in text.split('\n') if p.strip()]
    opts = []
    for p in parts:
        m = re.match(r'([A-F])[\.、．]\s*(.*)', p)
        if m: opts.append({'label': m.group(1), 'text': m.group(2)})
    return opts

def detect_section(text):
    for key, (tname, mode) in SECTION_MAP.items():
        if key in text:
            return tname, mode
    return None

def parse(paragraphs):
    questions = []
    qtype, mode = '简答题', 'short'
    buffer = []

    def save():
        nonlocal buffer
        if not buffer: return
        # Identify answer line
        ans_text = ''
        ans_idx = -1
        for j, line in enumerate(buffer):
            if line.startswith('答案') or line.startswith('正确答案'):
                ans_text = re.sub(r'^(正确)?答案[：:]\s*', '', line).strip()
                ans_idx = j
                break
            if line.startswith('翻译') and len(line) > 3:
                ans_text = re.sub(r'^翻译[：:]\s*', '', line).strip()
                ans_idx = j
                break
            if line.startswith('答：') or line.startswith('答:'):
                ans_text = re.sub(r'^答[：:]\s*', '', line).strip()
                ans_idx = j
                break

        # If no explicit answer, try inline answer in question text (e.g. "（  C   ）")
        if ans_idx < 0:
            # Check first line (question text) and last line for inline answer
            found = False
            for check_idx in [0, len(buffer)-1]:
                check_line = buffer[check_idx].strip()
                inline_m = re.search(r'[（(]\s*([A-F])\s*[）)]', check_line)
                if inline_m and mode in ('single', 'multi'):
                    ans_text = inline_m.group(1)
                    ans_idx = len(buffer)  # fake: answer is in question, content is everything
                    found = True
                    break
            if not found:
                buffer = []
                return

        # Content = everything before answer (or all if inline answer)
        content_lines = []
        end = ans_idx if ans_idx < len(buffer) else len(buffer)
        for l in buffer[:end]:
            cleaned = re.sub(r'^\d+[\.、]\s*', '', l)
            content_lines.append(cleaned)
        if not content_lines:
            buffer = []
            return

        # Extract options from content lines
        opts = []
        new_content_lines = []
        for cl in content_lines:
            # Try inline split (e.g. "A. xxx    B. yyy    C. zzz    D. www")
            inline = split_inline_opts(cl)
            if mode in ('single', 'multi') and len(inline) >= 2:
                opts.extend(inline)
                continue
            # Single option line
            m = re.match(r'^([A-F])[\.、．]\s*(.*)', cl)
            if m and mode in ('single', 'multi'):
                opts.append({'label': m.group(1), 'text': m.group(2).strip()})
                continue
            # Multi-line continuation of last option
            if opts and mode in ('single', 'multi') and not re.match(r'^\d+[\.、]', cl):
                opts[-1]['text'] += ' ' + cl.strip()
                continue
            new_content_lines.append(cl)

        if opts:
            content_lines = new_content_lines
        if not content_lines:
            content_lines = ['']

        content = ' '.join(content_lines).strip()
        # Remove inline answer from content (e.g. "（  C   ）" or "( C )")
        content = re.sub(r'[（(]\s*[A-F]\s*[）)]', '', content).strip()
        # Clean up double spaces
        content = re.sub(r'\s{2,}', ' ', content)

        # Clean answer
        answer = ans_text.strip()
        if mode == 'single':
            m = re.match(r'([A-F])', answer)
            if m: answer = m.group(1)

        if content:
            questions.append({
                'index': len(questions) + 1,
                'type': qtype,
                'content': content,
                'options': opts,
                'answer': answer
            })
        buffer = []

    for i, line in enumerate(paragraphs):
        # Section header? Must contain both type keyword and question count info
        sec = detect_section(line)
        is_header = sec and (
            re.search(r'[（(].*\d+.*[）)]', line) or
            re.search(r'共\s*\d+\s*[题小]', line)
        )
        if is_header:
            save()
            qtype, mode = sec
            continue

        # Question number boundary (e.g., "1、", "1.", "2、")
        if re.match(r'^\d+[\.、]', line) and buffer:
            save()
            buffer.append(line)
            continue

        # Answer line boundary
        if (line.startswith('答案') or line.startswith('正确答案') or line.startswith('翻译：') or line.startswith('翻译:') or line.startswith('答：') or line.startswith('答:')) and buffer:
            buffer.append(line)
            save()
            continue

        buffer.append(line)

    save()  # last question
    return questions

def process_all():
    files = sorted(glob.glob(os.path.join(INPUT_DIR, "*试题*")))
    chapters = []
    for filepath in files:
        basename = os.path.basename(filepath)
        paragraphs = extract_paragraphs(filepath)
        if not paragraphs:
            print(f"SKIP: {basename}")
            continue
        # Title
        title = basename
        for t in paragraphs[:12]:
            # Clean garbled binary prefixes and CJK punctuation
            t = re.sub(r'^[^一-鿿　-〿＀-￯]*', '', t)
            # Extract Chinese content
            m = re.search(r'[一-鿿]+.*', t)
            if m: t = m.group()
            t = re.sub(r'[《》试题\s（）\(\)]', '', t).strip()
            if t and len(t) < 60 and not re.match(r'^[一二三四五六七八九十]、', t):
                title = t; break
        qs = parse(paragraphs)
        print(f"{basename}: {title} -> {len(qs)} questions")
        if qs:
            chapters.append({'chapter': title, 'sections': [{'type': '试题', 'questions': qs}]})
    return chapters

if __name__ == '__main__':
    chapters = process_all()
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(chapters, f, ensure_ascii=False, indent=2)
    total = sum(len(ch['sections'][0]['questions']) for ch in chapters)
    print(f"\nDone: {len(chapters)} chapters, {total} questions")
