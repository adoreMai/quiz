#!/usr/bin/env python3
"""
超星学习通题库清洗脚本
功能：解析题库txt → 修复乱码 → 统一格式 → 输出 JSON/CSV/TXT
作者：巩颛硕
"""

import re
import json
import csv
from collections import Counter, defaultdict

INPUT = "共同体概论题库汇总.txt"

with open(INPUT, "r", encoding="utf-8") as f:
    raw_text = f.read()

lines = raw_text.split("\n")

# ============================================================
# 1. 解析
# ============================================================

CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}
NUM_CN = {v: k for k, v in CN_NUM.items()}
NUM_CN.update({
    7: "七", 8: "八", 9: "九", 10: "十", 11: "十一", 12: "十二",
    13: "十三", 14: "十四", 15: "十五", 16: "十六"
})

QTYPE_RE = re.compile(r"^###\s*([一二三四五六]+)\.\s*(\S+)（共(\d+)题）$")
QIDX_RE = re.compile(r"^\*(\d+)\*$")
QTAG_RE = re.compile(r"^【(单选题|多选题|判断题|简答题|论述题|填空题)】")
ANSWER_RE = re.compile(r"^正确答案：$")
MY_ANSWER_RE = re.compile(r"^我的答案：$")
# 多行选项标记: "- A、" 或 "- *A、*" 或 "*A、*" 等
OPTION_LINE_RE = re.compile(r"^-?\s*\*?([A-Z])\*?[、，]?\*?\s*$")
# 紧凑选项: *A、*[text](url) 或 *A*[text](url) 或 *A、[text](url) 等
OPTION_COMPACT_RE = re.compile(r"\*?([A-Z])\*?[、，]?\*?\s*\[([^\]]*)\]\(javascript:void\(0\);?\)")
# 检测行内是否包含紧凑选项
HAS_COMPACT_RE = re.compile(r"\*[A-Z]")
SCORE_RE = re.compile(r"^\*\*[\d.]+分\*\*$")
META_RE = re.compile(r"^(题量|第\d+次作答|已完成|章节测验|重做|\[重做)[：: \t]")
AI_RE = re.compile(r"\[[*\s]*AI讲解[*\s]*\]\(javascript:;\)")
TOP_SECTION_RE = re.compile(r"^### (.+)$")

def cn_to_int(s):
    """中文数字→阿拉伯数字，如 十二→12, 二十→20, 一百二十→120"""
    total = 0
    unit = 1
    # 处理十位及以上
    if "十" in s:
        parts = s.split("十")
        if parts[0]:  # 如 "十二" → parts=["", "二"] → parts[0]为空
            total += cn_to_int(parts[0]) * 10
        else:
            total += 10
        if len(parts) > 1 and parts[1]:
            total += CN_NUM.get(parts[1], 0)
        return total
    # 简单数字
    result = 0
    for ch in s:
        if ch in CN_NUM:
            result = result * 10 + CN_NUM[ch]
        elif ch == "零":
            pass
    return result

def extract_chapter_num(title):
    # 匹配 "第X章" 或 "新X章" (可能没有"第")
    m = re.search(r"(?:第|新)\s*([\d一二三四五六七八九十]+)\s*章", title)
    if m:
        s = m.group(1)
        if s.isdigit():
            return int(s)
        return cn_to_int(s)
    return None

def is_top_header(line):
    if not TOP_SECTION_RE.match(line):
        return False
    if QTYPE_RE.match(line):
        return False
    return True

# 解析状态
all_chapters = []
current_chapter = None
current_section = None
current_qtype = "未知"
current_question = None
current_options = []
current_answer_lines = []
current_mode = None  # "question" | "option" | "answer"
pending_label = None
option_text_buf = []

def flush():
    global current_question, current_options, current_answer_lines
    global current_mode, pending_label, option_text_buf

    if current_question is None:
        return

    # 保存最后一个选项
    if pending_label:
        text = "".join(option_text_buf).strip()
        current_options.append({"label": pending_label, "text": text})
        pending_label = None
        option_text_buf = []

    answer = "\n".join(current_answer_lines).strip()
    if answer in ("章节测验", "已完成", ""):
        answer = ""

    qtext = current_question.strip()
    current_section["questions"].append({
        "type": current_qtype,
        "content": qtext,
        "options": current_options,
        "answer": answer,
    })

    current_question = None
    current_options = []
    current_answer_lines = []
    current_mode = None
    pending_label = None
    option_text_buf = []

def start_section(stype):
    global current_section, current_qtype
    flush()
    current_section = {"type": stype, "questions": []}
    current_qtype = "未知"
    if current_chapter is not None:
        current_chapter["sections"].append(current_section)

def strip_meta(text):
    text = AI_RE.sub("", text)
    text = re.sub(r"\[([^\]]*)\]\(https?://[^\)]+\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\(javascript:void\(0\);\)", r"\1", text)
    return text.strip()

i = 0
while i < len(lines):
    line = lines[i].rstrip()
    stripped = line.strip()
    i += 1

    if not stripped:
        # 在选项模式下，空行可能分隔选项文本
        continue

    # 跳过元数据和分数字
    if SCORE_RE.match(stripped) or META_RE.match(stripped) or AI_RE.search(stripped):
        continue

    # 题型头
    m = QTYPE_RE.match(stripped)
    if m:
        flush()
        current_qtype = m.group(2)
        continue

    # 顶级区块头
    if is_top_header(stripped):
        flush()
        m = TOP_SECTION_RE.match(stripped)
        title = m.group(1).strip()

        if "测试题" in title or "作业" in title:
            if current_chapter is None:
                current_chapter = {"chapter_num": 0, "chapter_name": "未知章节", "sections": []}
                all_chapters.append(current_chapter)
            start_section(title)
        else:
            ch_num = extract_chapter_num(title)
            current_chapter = {"chapter_num": ch_num or 0, "chapter_name": title, "sections": []}
            all_chapters.append(current_chapter)
            start_section("章节测验")
        continue

    # 题目编号 *N*
    m = QIDX_RE.match(stripped)
    if m:
        flush()
        continue

    # 题型标签 【单选题】等
    m = QTAG_RE.match(stripped)
    if m and current_question is None:
        current_qtype = m.group(1)
        current_mode = "question"
        # 标签后可能紧跟题目正文，不要丢弃
        rest = stripped[m.end():].strip()
        if rest:
            # 检查 rest 中是否包含紧凑选项
            compact_in_rest = OPTION_COMPACT_RE.findall(rest)
            if compact_in_rest:
                # 分离题目和选项
                first_pos = len(rest)
                for label, _ in compact_in_rest:
                    markers = [f"*{label}、*", f"*{label}*、", f"*{label}、",
                              f"*{label}*", f"{label}、", f"*{label}"]
                    for mk in markers:
                        p = rest.find(mk)
                        if p >= 0 and p < first_pos:
                            first_pos = p
                            break
                if first_pos > 0:
                    current_question = rest[:first_pos].strip()
                else:
                    current_question = ""
                # 进入选项模式
                current_mode = "option"
                for label, text in compact_in_rest:
                    current_options.append({"label": label, "text": strip_meta(text)})
            else:
                current_question = rest
        else:
            current_question = ""
        continue

    # 答案 / 我的答案
    if ANSWER_RE.match(stripped):
        current_mode = "answer"
        current_answer_lines = []
        continue
    if MY_ANSWER_RE.match(stripped):
        current_mode = "my_answer"
        continue

    # 按当前模式处理
    if current_mode == "question":
        # 检查是否包含紧凑选项（可能和题目正文在同一行）
        compact = OPTION_COMPACT_RE.findall(stripped)
        opt_line = OPTION_LINE_RE.match(stripped)

        if compact:
            # 找到第一个选项的位置，分离题目和选项
            first_opt_pos = len(stripped)
            for label, text in compact:
                # 尝试各种选项标记格式
                markers = [f"*{label}、*", f"*{label}*、", f"*{label}、",
                          f"*{label}*", f"{label}、", f"*{label}"]
                for m in markers:
                    pos = stripped.find(m)
                    if pos >= 0 and pos < first_opt_pos:
                        first_opt_pos = pos
                        break

            # 题目正文是第一个选项之前的部分
            if first_opt_pos > 0 and first_opt_pos < len(stripped):
                prefix = stripped[:first_opt_pos].strip()
                # 过滤纯标记前缀（如单独的 "-"）
                if prefix and not re.match(r'^-?\s*$', prefix):
                    clean_prefix = strip_meta(prefix)
                    if current_question:
                        current_question += "\n" + clean_prefix
                    else:
                        current_question = clean_prefix

            current_mode = "option"
            for label, text in compact:
                current_options.append({"label": label, "text": strip_meta(text)})
            continue
        elif opt_line:
            current_mode = "option"
            pending_label = opt_line.group(1)
            option_text_buf = []
            continue
        else:
            clean = strip_meta(stripped)
            if current_question:
                current_question += "\n" + clean
            else:
                current_question = clean
            continue

    elif current_mode == "option":
        compact = OPTION_COMPACT_RE.findall(stripped)
        opt_line = OPTION_LINE_RE.match(stripped)

        if opt_line:
            # 保存上一个选项
            if pending_label:
                current_options.append({"label": pending_label, "text": "".join(option_text_buf).strip()})
            pending_label = opt_line.group(1)
            option_text_buf = []
            continue
        elif compact:
            if pending_label:
                current_options.append({"label": pending_label, "text": "".join(option_text_buf).strip()})
                pending_label = None
                option_text_buf = []
            for label, text in compact:
                current_options.append({"label": label, "text": strip_meta(text)})
            continue
        elif ANSWER_RE.match(stripped):
            if pending_label:
                current_options.append({"label": pending_label, "text": "".join(option_text_buf).strip()})
                pending_label = None
                option_text_buf = []
            current_mode = "answer"
            current_answer_lines = []
            continue
        elif MY_ANSWER_RE.match(stripped):
            if pending_label:
                current_options.append({"label": pending_label, "text": "".join(option_text_buf).strip()})
                pending_label = None
                option_text_buf = []
            current_mode = "my_answer"
            continue
        elif QIDX_RE.match(stripped) or is_top_header(stripped):
            flush()
            i -= 1  # 回退一行
            continue
        else:
            option_text_buf.append(strip_meta(stripped))
            continue

    elif current_mode == "my_answer":
        if ANSWER_RE.match(stripped):
            current_mode = "answer"
            current_answer_lines = []
            continue
        elif QIDX_RE.match(stripped) or is_top_header(stripped):
            flush()
            i -= 1
            continue
        elif SCORE_RE.match(stripped) or AI_RE.search(stripped):
            continue
        # 忽略我的答案内容
        continue

    elif current_mode == "answer":
        if MY_ANSWER_RE.match(stripped):
            current_mode = "my_answer"
            continue
        elif QIDX_RE.match(stripped) or is_top_header(stripped) or QTYPE_RE.match(stripped):
            flush()
            i -= 1
            continue
        elif SCORE_RE.match(stripped) or AI_RE.search(stripped):
            continue
        else:
            current_answer_lines.append(strip_meta(stripped))
            continue

flush()

print(f"解析完成：{len(all_chapters)} 个章节区块")
for ch in all_chapters:
    for sec in ch["sections"]:
        print(f"  {ch['chapter_name']} → {sec['type']}: {len(sec['questions'])} 题")

# ============================================================
# 2. 建立字符映射表
# ============================================================

def extract_cjk(text):
    result = []
    for ch in text:
        cp = ord(ch)
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0xF900 <= cp <= 0xFAFF:
            result.append(ch)
    return result

def add_mapping(g_text, c_text, char_map):
    g_cjk = extract_cjk(g_text)
    c_cjk = extract_cjk(c_text)
    if abs(len(g_cjk) - len(c_cjk)) <= 30:
        for gi, gc in enumerate(g_cjk):
            if gi < len(c_cjk) and gc != c_cjk[gi]:
                if gc not in char_map:
                    char_map[gc] = Counter()
                char_map[gc][c_cjk[gi]] += 1

print("\n=== 建立字符映射 ===")

char_map = {}
matched = 0

def make_fingerprint(text):
    """Create a fingerprint from non-CJK structure: punctuation, digits, spaces, and segment lengths"""
    fp = []
    cjk_len = 0
    for ch in text:
        cp = ord(ch)
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            cjk_len += 1
        else:
            if cjk_len > 0:
                fp.append(f"{{{cjk_len}}}")
                cjk_len = 0
            if not ch.isspace():
                fp.append(ch)
    if cjk_len > 0:
        fp.append(f"{{{cjk_len}}}")
    return "".join(fp)


# 同章节内匹配
for ch in all_chapters:
    garbled = []
    correct = []
    for sec in ch["sections"]:
        target = garbled if sec["type"] == "章节测验" else correct
        for q in sec["questions"]:
            if q["type"] in ("单选题", "多选题", "判断题"):
                target.append(q)

    for qtype in ["单选题", "多选题", "判断题"]:
        g_list = [q for q in garbled if q["type"] == qtype and q["options"]]
        c_list = [q for q in correct if q["type"] == qtype and q["options"]]

        for gq in g_list:
            if not gq["answer"]:
                continue
            # Filter by answer + option count first
            candidates = [cq for cq in c_list
                         if cq["answer"] == gq["answer"]
                         and len(cq["options"]) == len(gq["options"])]

            if not candidates:
                continue

            # Use fingerprint matching
            g_fp = make_fingerprint(gq["content"])
            best_cq = None
            best_score = -1

            for cq in candidates:
                c_fp = make_fingerprint(cq["content"])
                # Score: count matching non-CJK characters in order
                score = 0
                for gc, cc in zip(g_fp, c_fp):
                    if gc == cc:
                        score += 1

                # Also compare option fingerprints
                for go, co in zip(gq["options"], cq["options"]):
                    go_fp = make_fingerprint(go["text"])
                    co_fp = make_fingerprint(co["text"])
                    for gc, cc in zip(go_fp, co_fp):
                        if gc == cc:
                            score += 1

                if score > best_score:
                    best_score = score
                    best_cq = cq

            # Require reasonable fingerprint match
            if best_cq and best_score >= max(3, len(g_fp) * 0.3):
                matched += 1
                add_mapping(gq["content"], best_cq["content"], char_map)
                for go, co in zip(gq["options"], best_cq["options"]):
                    add_mapping(go["text"], co["text"], char_map)

# 全局补充匹配
all_g = []
all_c = []
for ch in all_chapters:
    for sec in ch["sections"]:
        target = all_g if sec["type"] == "章节测验" else all_c
        for q in sec["questions"]:
            if q["type"] in ("单选题", "多选题", "判断题"):
                target.append(q)

for gq in all_g:
    if not gq["answer"] or not gq["options"]:
        continue
    candidates = [cq for cq in all_c
                 if cq["answer"] == gq["answer"]
                 and len(cq["options"]) == len(gq["options"])]

    if not candidates:
        continue

    g_fp = make_fingerprint(gq["content"])
    best_cq = None
    best_score = -1

    for cq in candidates:
        c_fp = make_fingerprint(cq["content"])
        score = 0
        for gc, cc in zip(g_fp, c_fp):
            if gc == cc:
                score += 1
        for go, co in zip(gq["options"], cq["options"]):
            go_fp = make_fingerprint(go["text"])
            co_fp = make_fingerprint(co["text"])
            for gc, cc in zip(go_fp, co_fp):
                if gc == cc:
                    score += 1
        if score > best_score:
            best_score = score
            best_cq = cq

    if best_cq and best_score >= max(3, len(g_fp) * 0.3):
        matched += 1
        add_mapping(gq["content"], best_cq["content"], char_map)
        for go, co in zip(gq["options"], best_cq["options"]):
            add_mapping(go["text"], co["text"], char_map)

print(f"乱码组: {len(all_g)} 题, 正确组: {len(all_c)} 题")
print(f"匹配到 {matched} 对题目")
print(f"发现 {len(char_map)} 个映射候选")

# 构建"可信字符集"：所有出现在测试题(正确组)中的CJK字符
# 同时统计字符在正确组和乱码组中的出现频次
trusted_chars = set()
cjk_in_all_c = Counter()  # 正确组中的CJK字符频次
cjk_in_all_g = Counter()  # 乱码组中的CJK字符频次

for q in all_c:
    for ch in q["content"]:
        cp = ord(ch)
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            trusted_chars.add(ch)
            cjk_in_all_c[ch] += 1
    for opt in q["options"]:
        for ch in opt["text"]:
            cp = ord(ch)
            if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
                trusted_chars.add(ch)
                cjk_in_all_c[ch] += 1
    for ch in q["answer"]:
        cp = ord(ch)
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            trusted_chars.add(ch)
            cjk_in_all_c[ch] += 1

for q in all_g:
    for ch in q["content"]:
        cp = ord(ch)
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            cjk_in_all_g[ch] += 1
    for opt in q["options"]:
        for ch in opt["text"]:
            cp = ord(ch)
            if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
                cjk_in_all_g[ch] += 1
    for ch in q["answer"]:
        cp = ord(ch)
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            cjk_in_all_g[ch] += 1

print(f"可信字符集: {len(trusted_chars)} 个字符 (来自测试题)")

# 合并映射，并过滤可疑映射
final_map = {}
rejected_trusted = 0
rejected_low_conf = 0
rejected_ratio = 0
for gc, counter in char_map.items():
    if not counter:
        continue
    best_char, best_count = counter.most_common(1)[0]
    if best_count < 2:  # 至少出现2次
        rejected_low_conf += 1
        continue
    gc_cp = ord(gc)
    cc_cp = ord(best_char)
    if cc_cp < 0x4E00:
        continue
    if gc_cp < 0x3000:
        continue
    # 关键过滤1：源字符不能在可信字符集中
    if gc in trusted_chars:
        rejected_trusted += 1
        continue
    # 关键过滤2：乱码字符在乱码组中的频次应远高于正确组（≥5:1）
    g_freq = cjk_in_all_g.get(gc, 0)
    c_freq = cjk_in_all_c.get(gc, 0)
    if c_freq > 0 and g_freq / c_freq < 5:
        rejected_ratio += 1
        continue
    # 要求最高频候选占绝对多数（≥80%）
    total = sum(counter.values())
    if best_count / total < 0.8:
        continue
    final_map[gc] = best_char

print(f"最终映射: {len(final_map)} 个字符 (过滤后)")
print(f"  拒绝: {rejected_low_conf} 低频次, {rejected_trusted} 在可信集中, {rejected_ratio} 频次比不足")

# 验证部分映射
print("\n=== 映射示例 ===")
for gc, cc in list(final_map.items())[:30]:
    print(f"  {gc} (U+{ord(gc):04X}) → {cc} (U+{ord(cc):04X})")

# ============================================================
# 3. 应用映射修复文本
# ============================================================

def fix_text(text, mapping):
    if not mapping:
        return text
    return "".join(mapping.get(ch, ch) for ch in text)

# 只修复乱码来源的章节测验，保护测试题和元数据
for ch in all_chapters:
    for sec in ch["sections"]:
        if sec["type"] != "章节测验":
            continue  # 只修乱码组
        for q in sec["questions"]:
            q["type"] = fix_text(q["type"], final_map)
            q["content"] = fix_text(q["content"], final_map)
            q["answer"] = fix_text(q["answer"], final_map)
            for opt in q["options"]:
                opt["text"] = fix_text(opt["text"], final_map)

# ============================================================
# 4. 统一章节
# ============================================================

TITLE_CN = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六",
            7: "七", 8: "八", 9: "九", 10: "十", 11: "十一", 12: "十二",
            13: "十三", 14: "十四", 15: "十五", 16: "十六"}

chapter_map = {}
for ch in all_chapters:
    ch_num = ch["chapter_num"]
    if ch_num == 0:
        key = f"unknown_{len(chapter_map)}"
        chapter_map[key] = ch
        continue

    cn = TITLE_CN.get(ch_num, str(ch_num))
    norm_name = f"第{cn}章"

    if ch_num not in chapter_map:
        chapter_map[ch_num] = {"chapter_num": ch_num, "chapter_name": norm_name, "sections": []}

    for sec in ch["sections"]:
        raw_type = sec["type"]
        if "测试题" in raw_type or "作业" in raw_type:
            sec["type"] = "测试题"
        else:
            sec["type"] = "章节测验"
        chapter_map[ch_num]["sections"].append(sec)

int_keys = sorted([k for k in chapter_map if isinstance(k, int)])
str_keys = sorted([k for k in chapter_map if isinstance(k, str)])
final_chapters = [chapter_map[k] for k in int_keys + str_keys]

print(f"\n统一后：{len(final_chapters)} 个章节")

# ============================================================
# 5. 标记题目来源
# ============================================================

print("\n=== 标记题目来源 ===")

def build_q_fp(q):
    """Build fingerprint for question dedup: non-CJK structure + options + answer"""
    parts = [make_fingerprint(q["content"])]
    for o in q["options"]:
        parts.append(o["label"])
        parts.append(make_fingerprint(o["text"]))
    parts.append(q.get("answer", ""))
    return "|".join(parts)

ceyan_fps = {}
ceshi_fps = {}

for ch in final_chapters:
    for sec in ch["sections"]:
        target = ceyan_fps if sec["type"] == "章节测验" else ceshi_fps
        for q in sec["questions"]:
            fp = build_q_fp(q)
            target[fp] = target.get(fp, 0) + 1

ceyan_fp_list = list(ceyan_fps.keys())
ceshi_fp_list = list(ceshi_fps.keys())

print(f"章节测验唯一指纹: {len(ceyan_fp_list)}, 测试题唯一指纹: {len(ceshi_fp_list)}")

def fuzzy_match(query_fp, target_list, threshold=0.5):
    """Return True if query_fp has a fuzzy match in target_list"""
    if not query_fp:
        return False
    query_len = len(query_fp)
    for tfp in target_list:
        if abs(len(tfp) - query_len) > max(20, query_len * 0.3):
            continue
        score = sum(1 for c1, c2 in zip(query_fp, tfp) if c1 == c2)
        if score >= max(5, query_len * threshold):
            return True
    return False

dual_ceyan = 0
dual_ceshi = 0
ceshi_only = 0
ceyan_only = 0

for ch in final_chapters:
    for sec in ch["sections"]:
        for q in sec["questions"]:
            fp = build_q_fp(q)
            if sec["type"] == "章节测验":
                if fp in ceshi_fps or fuzzy_match(fp, ceshi_fp_list):
                    q["content"] = "** " + q["content"]
                    dual_ceyan += 1
                else:
                    ceyan_only += 1
            else:  # 测试题
                if fp in ceyan_fps or fuzzy_match(fp, ceyan_fp_list):
                    q["content"] = "** " + q["content"]
                    dual_ceshi += 1
                else:
                    q["content"] = "* " + q["content"]
                    ceshi_only += 1

print(f"章节测验: {ceyan_only} 题仅测验(无标记), {dual_ceyan} 题双源(**标记)")
print(f"测试题: {ceshi_only} 题仅测试(*标记), {dual_ceshi} 题双源(**标记)")

# ============================================================
# 6. 输出
# ============================================================

BASE = "题库"

# --- JSON ---
json_out = []
for ch in final_chapters:
    secs = []
    for sec in ch["sections"]:
        qs = []
        for idx, q in enumerate(sec["questions"], 1):
            qs.append({
                "index": idx,
                "type": q["type"],
                "content": q["content"],
                "options": q["options"],
                "answer": q["answer"],
            })
        secs.append({"type": sec["type"], "questions": qs})
    json_out.append({"chapter": ch["chapter_name"], "sections": secs})

with open(BASE + ".json", "w", encoding="utf-8") as f:
    json.dump(json_out, f, ensure_ascii=False, indent=2)
print(f"JSON → {BASE}.json")

# --- CSV ---
with open(BASE + ".csv", "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    headers = ["章节", "分组", "题型", "题号", "题目",
               "选项A", "选项B", "选项C", "选项D", "选项E", "选项F", "答案"]
    writer.writerow(headers)
    for ch in final_chapters:
        for sec in ch["sections"]:
            for q in sec["questions"]:
                row = [ch["chapter_name"], sec["type"], q["type"],
                       q.get("index", ""), q["content"]]
                for label in "ABCDEF":
                    txt = ""
                    for opt in q["options"]:
                        if opt["label"] == label:
                            txt = opt["text"]
                            break
                    row.append(txt)
                row.append(q["answer"])
                writer.writerow(row)
print(f"CSV → {BASE}.csv")

# --- TXT ---
with open(BASE + ".txt", "w", encoding="utf-8-sig") as f:
    for ch in final_chapters:
        f.write(f"{'='*60}\n  {ch['chapter_name']}\n{'='*60}\n\n")
        for sec in ch["sections"]:
            f.write(f"  【{sec['type']}】\n\n")
            groups = defaultdict(list)
            for q in sec["questions"]:
                groups[q["type"]].append(q)
            order = ["单选题", "多选题", "判断题", "简答题", "论述题", "填空题"]
            type_prefix = {"单选题": "一", "多选题": "二", "判断题": "三",
                           "简答题": "四", "论述题": "五", "填空题": "六"}
            cn_labels = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
            # Output known types in order first
            idx = 0
            for qt in order:
                if qt not in groups:
                    continue
                prefix = type_prefix.get(qt, cn_labels[idx] if idx < len(cn_labels) else str(idx+1))
                f.write(f"    {prefix}、{qt}\n\n")
                for j, q in enumerate(groups[qt], 1):
                    f.write(f"      {j}. {q['content']}\n")
                    for opt in q["options"]:
                        f.write(f"         {opt['label']}. {opt['text']}\n")
                    if q["answer"]:
                        f.write(f"         [答案] {q['answer']}\n")
                    f.write("\n")
                idx += 1
            # Output remaining unknown types (e.g. garbled type names)
            for qt in sorted(groups.keys()):
                if qt in order:
                    continue
                prefix = cn_labels[idx] if idx < len(cn_labels) else str(idx+1)
                f.write(f"    {prefix}、{qt}\n\n")
                for j, q in enumerate(groups[qt], 1):
                    f.write(f"      {j}. {q['content']}\n")
                    for opt in q["options"]:
                        f.write(f"         {opt['label']}. {opt['text']}\n")
                    if q["answer"]:
                        f.write(f"         [答案] {q['answer']}\n")
                    f.write("\n")
                idx += 1
print(f"TXT → {BASE}.txt")

# --- MD (Markdown for Typora) ---
with open(BASE + ".md", "w", encoding="utf-8-sig") as f:
    for ch in final_chapters:
        f.write(f"# {ch['chapter_name']}\n\n")
        for sec in ch["sections"]:
            f.write(f"## {sec['type']}\n\n")
            groups = defaultdict(list)
            for q in sec["questions"]:
                groups[q["type"]].append(q)
            order = ["单选题", "多选题", "判断题", "简答题", "论述题", "填空题"]
            type_prefix = {"单选题": "一", "多选题": "二", "判断题": "三",
                           "简答题": "四", "论述题": "五", "填空题": "六"}
            cn_labels = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
            idx = 0
            for qt in order:
                if qt not in groups:
                    continue
                prefix = type_prefix.get(qt, cn_labels[idx] if idx < len(cn_labels) else str(idx+1))
                f.write(f"### {prefix}、{qt}\n\n")
                for j, q in enumerate(groups[qt], 1):
                    f.write(f"{j}. {q['content']}\n\n")
                    for opt in q["options"]:
                        f.write(f"   - {opt['label']}. {opt['text']}\n")
                    if q["answer"]:
                        f.write(f"   - **答案：{q['answer']}**\n")
                    f.write("\n")
                idx += 1
            # Output remaining unknown types
            for qt in sorted(groups.keys()):
                if qt in order:
                    continue
                prefix = cn_labels[idx] if idx < len(cn_labels) else str(idx+1)
                f.write(f"### {prefix}、{qt}\n\n")
                for j, q in enumerate(groups[qt], 1):
                    f.write(f"{j}. {q['content']}\n\n")
                    for opt in q["options"]:
                        f.write(f"   - {opt['label']}. {opt['text']}\n")
                    if q["answer"]:
                        f.write(f"   - **答案：{q['answer']}**\n")
                    f.write("\n")
                idx += 1
print(f"MD → {BASE}.md")

# ============================================================
# 7. 统计
# ============================================================
total = sum(1 for ch in final_chapters for sec in ch["sections"] for _ in sec["questions"])
with_ans = sum(1 for ch in final_chapters for sec in ch["sections"] for q in sec["questions"] if q["answer"])
print(f"\n总计: {len(final_chapters)} 章, {total} 题, 有答案: {with_ans} 题, 无答案: {total - with_ans} 题")
print("完成！")
