#!/usr/bin/env python3
"""
pptx_polish.py — PPTX 排版优化工具
Gamma AI 导出 PPTX 后处理：统一字体、提升字号、增强视觉层次、消解重叠

用法:
  python pptx_polish.py input.pptx [--font 微软雅黑] [--min-size 16] [--output output.pptx]

关键设计原则（来自6轮迭代复盘）：
  P1: solidFill 与 noFill 不能共存 → 添加 solidFill 前必须先 remove noFill
  P2: lxml Element 存在性判断必须用 `is not None`，不能用 `if element:`
  P3: sz 单位是 1/100pt（sz=1600 = 16pt），EMU = pt × 12700
  P4: shape 分类靠 name + sz + y位置，不能只靠数值阈值
  P5: 纯文本框（原 noFill）必须保持透明，不加任何填充
  P6: 每次从原始文件重新解包，脚本非幂等
"""

import argparse
import io
import sys
import tempfile
import zipfile

# Windows GBK 兼容：强制 stdout 使用 UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from pathlib import Path
from lxml import etree

# ─── OOXML 命名空间 ──────────────────────────────────────────────────────────
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'

def q(ns_uri, local):
    return f'{{{ns_uri}}}{local}'

def qa(local):   # drawingml
    return q(A, local)

def qp(local):   # presentationml
    return q(P, local)

# ─── 常量 ────────────────────────────────────────────────────────────────────
EMU_PT = 12700           # 1pt = 12700 EMU
SZ_FACTOR = 100          # sz=1600 → 16pt（1/100pt 单位）  P3
SLIDE_H = 6858000        # 标准 16:9 幻灯片高度（EMU）

DEFAULT_FONT    = '微软雅黑'
DEFAULT_MIN_SZ  = 16     # pt
DEFAULT_PAD_PT  = 4      # pt

TITLE_BG    = '1E3A5F'  # 深蓝
TITLE_FG    = 'FFFFFF'  # 白色
WARN_BORDER = 'F0AD4E'  # 黄色（⚠️ 待决策）
DONE_BORDER = '28A745'  # 绿色（✅ 已完成）
CARD_BORDER = '84C5F6'  # 淡蓝（有填充卡片）

LABEL_BG_MAX_H_PT = 30          # 标签底框高度上限；更高的 shape 更可能是卡片/表格
LABEL_TEXT_MAX_CHARS = 24       # 只处理短标签，避免误伤正文文本框
LABEL_BG_PAD_X_PT = 24          # 标签底框左右扩展留白
LABEL_BG_MIN_GAP_PT = 8         # 同一水平带相邻标签的最小间距

# ─── Step 8: 语义色彩映射 ────────────────────────────────────────────────────
# 关键词 → 文字颜色（交通灯体系），可由用户扩展
SEMANTIC_COLORS = {
    'green':  {'color': '28A745', 'keywords': ['完成', '达成', '✅', 'achieved', 'completed']},
    'orange': {'color': 'F0AD4E', 'keywords': ['进行中', '推进', 'on track', '⏳', 'in progress']},
    'red':    {'color': 'C00000', 'keywords': ['风险', '延迟', 'blocked', '⚠️', '❌', 'critical', '告警']},
}

# ─── Step 9: 字号重映射（v2→v3 实测数据）────────────────────────────────────
SIZE_REMAP = {
    # 1650: 1600,  # 16.5→16pt — 回归验证失败：8 处 16.5pt 是刻意保留的，降级为观察
    2150: 2000,  # 21.5→20pt
    2900: 3200,  # 29→32pt
}


# ─── Step 1: 统一字体 ─────────────────────────────────────────────────────────
def fix_fonts(root, font):
    for tag in (qa('rPr'), qa('endParaRPr'), qa('defRPr')):
        for el in root.iter(tag):
            for sub_tag, attr in ((qa('latin'), 'typeface'), (qa('ea'), 'typeface')):
                sub = el.find(sub_tag)
                if sub is None:                          # P2: is not None
                    sub = etree.SubElement(el, sub_tag)
                sub.set(attr, font)


# ─── Step 2: 最小字号 ─────────────────────────────────────────────────────────
def fix_min_sz(root, min_hundredths):
    for tag in (qa('rPr'), qa('endParaRPr'), qa('defRPr')):
        for el in root.iter(tag):
            sz = el.get('sz')
            if sz is not None and int(sz) < min_hundredths:
                el.set('sz', str(min_hundredths))


# ─── Step 2b: 字号重映射 ──────────────────────────────────────────────────────
def fix_size_remap(root):
    """将已知的非标准字号精确映射到标准档位（基于 v2→v3 实测数据）"""
    if not SIZE_REMAP:
        return
    for tag in (qa('rPr'), qa('endParaRPr'), qa('defRPr')):
        for el in root.iter(tag):
            sz = el.get('sz')
            if sz is not None and int(sz) in SIZE_REMAP:   # P2
                el.set('sz', str(SIZE_REMAP[int(sz)]))


# ─── Step 3: 文本框内边距 ─────────────────────────────────────────────────────
def fix_padding(root, pad_emu):
    for bodyPr in root.iter(qa('bodyPr')):
        for attr in ('lIns', 'tIns', 'rIns', 'bIns'):
            if int(bodyPr.get(attr, '0')) == 0:
                bodyPr.set(attr, str(pad_emu))


def _get_shape_name(sp):
    for el in sp.iter():
        if el.tag.endswith('}cNvPr'):
            return el.get('name', '')
    return ''


def _get_shape_text(sp):
    return ''.join(t.text or '' for t in sp.iter(qa('t'))).strip()


def _estimate_text_width_emu(text, font_sz_hundredths):
    """粗略估算单行文本渲染宽度，优先解决短标签底框不足问题。"""
    sz_pt = max(font_sz_hundredths, 1600) / SZ_FACTOR
    total = 0.0
    for ch in text:
        if ch.isspace():
            total += 0.35
        elif ord(ch) < 128:
            if ch.isupper():
                total += 0.72
            elif ch.islower():
                total += 0.58
            elif ch.isdigit():
                total += 0.58
            else:
                total += 0.42
        else:
            # 中文及大部分全角字符按接近 1em 估算
            total += 0.95
    return int(total * sz_pt * EMU_PT)


def _get_shape_rect(sp):
    for xfrm in sp.iter(qa('xfrm')):
        off = xfrm.find(qa('off'))
        ext = xfrm.find(qa('ext'))
        if off is not None and ext is not None:
            return (
                int(off.get('x', 0)),
                int(off.get('y', 0)),
                int(ext.get('cx', 0)),
                int(ext.get('cy', 0)),
                off,
                ext,
            )
    return None


def _is_small_label_text(sp):
    text = _get_shape_text(sp)
    if not text:
        return False
    if len(text) > LABEL_TEXT_MAX_CHARS:
        return False

    rect = _get_shape_rect(sp)
    if rect is None:
        return False
    _, _, _, h, _, _ = rect
    if h > LABEL_BG_MAX_H_PT * EMU_PT:
        return False

    # 标题和标签往往是单段短文本；正文/说明文字通常更长
    return '\n' not in text


def _get_max_font_size(sp):
    max_sz = 1600
    for tag in (qa('rPr'), qa('endParaRPr'), qa('defRPr')):
        for el in sp.iter(tag):
            sz = el.get('sz')
            if sz:
                max_sz = max(max_sz, int(sz))
    return max_sz


def _is_small_empty_bg(sp):
    text = _get_shape_text(sp)
    if text:
        return False

    rect = _get_shape_rect(sp)
    if rect is None:
        return False
    _, _, _, h, _, _ = rect
    if h > LABEL_BG_MAX_H_PT * EMU_PT:
        return False

    return True


def fix_label_bg_widths(root):
    """短标签文字扩宽后，同步扩宽其背后的空白底框 shape。"""
    shapes = list(root.iter(qp('sp')))
    label_pad_x = int(LABEL_BG_PAD_X_PT * EMU_PT)
    min_gap_x = int(LABEL_BG_MIN_GAP_PT * EMU_PT)

    empty_bgs = []
    text_labels = []
    for sp in shapes:
        rect = _get_shape_rect(sp)
        if rect is None:
            continue
        x, y, w, h, off, ext = rect
        item = {
            'sp': sp,
            'name': _get_shape_name(sp),
            'text': _get_shape_text(sp),
            'max_sz': _get_max_font_size(sp),
            'x': x,
            'y': y,
            'w': w,
            'h': h,
            'off': off,
            'ext': ext,
        }
        if _is_small_empty_bg(sp):
            empty_bgs.append(item)
        elif _is_small_label_text(sp):
            text_labels.append(item)

    matched_pairs = []
    for bg in empty_bgs:
        candidates = []
        for label in text_labels:
            # 仅处理明显位于底框内部的短标签；避免误吸附附近正文
            if label['x'] < bg['x'] or label['x'] + label['w'] > bg['x'] + bg['w']:
                continue

            label_center_y = label['y'] + label['h'] / 2
            bg_center_y = bg['y'] + bg['h'] / 2
            if abs(label_center_y - bg_center_y) > max(bg['h'], label['h']) * 0.6:
                continue

            inter_y = max(0, min(bg['y'] + bg['h'], label['y'] + label['h']) - max(bg['y'], label['y']))
            if inter_y <= 0:
                continue

            slack = bg['w'] - label['w']
            candidates.append((slack, label))

        if not candidates:
            continue

        candidates.sort(key=lambda item: item[0])
        _, label = candidates[0]

        estimated_text_w = _estimate_text_width_emu(label['text'], label['max_sz'])
        # 留一档安全系数，优先避免视觉上“刚刚卡边”的情况
        content_w = max(label['w'], int(estimated_text_w * 1.12))
        target_x = label['x'] - label_pad_x
        target_w = content_w + 2 * label_pad_x
        if target_x < 0:
            target_w += target_x
            target_x = 0

        if target_w > bg['w']:
            bg['off'].set('x', str(target_x))
            bg['ext'].set('cx', str(target_w))
            bg['x'] = target_x
            bg['w'] = target_w

        matched_pairs.append((bg, label))

    # 同一水平带内，如果扩大后的标签底框互相挤压，则把右侧 pair 整体右移。
    matched_pairs.sort(key=lambda pair: (pair[0]['y'], pair[0]['x']))
    for i in range(1, len(matched_pairs)):
        prev_bg, _prev_label = matched_pairs[i - 1]
        bg, label = matched_pairs[i]

        prev_center_y = prev_bg['y'] + prev_bg['h'] / 2
        center_y = bg['y'] + bg['h'] / 2
        if abs(prev_center_y - center_y) > max(prev_bg['h'], bg['h']) * 0.8:
            continue

        prev_right = prev_bg['x'] + prev_bg['w']
        needed_left = prev_right + min_gap_x
        if bg['x'] >= needed_left:
            continue

        delta = needed_left - bg['x']
        bg['x'] += delta
        label['x'] += delta
        bg['off'].set('x', str(bg['x']))
        label['off'].set('x', str(label['x']))


# ─── Step 4: 标题 shape 配色 ─────────────────────────────────────────────────
def _get_sp_meta(sp):
    """提取 shape name、y比例、最大字号"""
    name = ''
    for el in sp.iter():
        if el.tag.endswith('}cNvPr'):
            name = el.get('name', '')
            break

    y_emu = 0
    for xfrm in sp.iter(qa('xfrm')):
        off = xfrm.find(qa('off'))
        if off is not None:                              # P2
            y_emu = int(off.get('y', 0))
        break

    max_sz = 0
    for rPr in sp.iter(qa('rPr')):
        sz = rPr.get('sz')
        if sz:
            max_sz = max(max_sz, int(sz))

    return name, y_emu / SLIDE_H, max_sz


def fix_title_bg(root):
    """主标题 shape → 深蓝背景 + 白色文字（P1: 先 remove noFill）"""
    for sp in root.iter(qp('sp')):
        name, y_ratio, max_sz = _get_sp_meta(sp)
        # P4: 多维判断，不能只靠字号/位置
        if not (name == 'Text 0' and max_sz >= 2000 and y_ratio < 0.2):
            continue

        spPr = sp.find(f'.//{qa("spPr")}')
        if spPr is None:                                 # P2
            continue

        # P1: 先移除 noFill，再添加 solidFill
        noFill = spPr.find(qa('noFill'))
        if noFill is not None:
            spPr.remove(noFill)
        for sf in spPr.findall(qa('solidFill')):
            spPr.remove(sf)
        sf = etree.SubElement(spPr, qa('solidFill'))
        etree.SubElement(sf, qa('srgbClr')).set('val', TITLE_BG)

        # 文字变白
        for rPr in sp.iter(qa('rPr')):
            for sf in rPr.findall(qa('solidFill')):
                rPr.remove(sf)
            sf = etree.SubElement(rPr, qa('solidFill'))
            etree.SubElement(sf, qa('srgbClr')).set('val', TITLE_FG)


# ─── Step 5: 边框着色（P5: 纯文本框保持透明）─────────────────────────────────
def _is_pure_textbox(sp):
    """判断是否为原始 noFill 纯文本框（P5）"""
    spPr = sp.find(f'.//{qa("spPr")}')
    if spPr is None:
        return False
    has_no   = spPr.find(qa('noFill'))    is not None   # P2
    has_solid= spPr.find(qa('solidFill')) is not None
    has_grad = spPr.find(qa('gradFill'))  is not None
    return has_no and not has_solid and not has_grad


def _add_border(spPr, color, width_emu):
    for ln in spPr.findall(qa('ln')):
        spPr.remove(ln)
    ln = etree.SubElement(spPr, qa('ln'))
    ln.set('w', str(width_emu))
    sf = etree.SubElement(ln, qa('solidFill'))
    etree.SubElement(sf, qa('srgbClr')).set('val', color)


def fix_borders(root):
    for sp in root.iter(qp('sp')):
        text = ''.join(t.text or '' for t in sp.iter(qa('t')))
        spPr = sp.find(f'.//{qa("spPr")}')
        if spPr is None:
            continue

        if _is_pure_textbox(sp):
            # P5: 纯文本框不加填充，只根据内容加边框
            if any(k in text for k in ('⚠️', '待决策', '❓', 'TODO')):
                _add_border(spPr, WARN_BORDER, 25400)   # 2pt
            elif any(k in text for k in ('✅', '已完成', '完成')):
                _add_border(spPr, DONE_BORDER, 19050)   # 1.5pt
        else:
            has_fill = (spPr.find(qa('solidFill')) is not None or
                        spPr.find(qa('gradFill'))  is not None)
            if has_fill:
                _add_border(spPr, CARD_BORDER, 12700)   # 1pt


# ─── Step 5b: 语义色彩映射 ────────────────────────────────────────────────────
def _is_title_shape(sp):
    """判断 shape 是否已被 Step 4 处理为标题（深蓝背景）"""
    name, y_ratio, max_sz = _get_sp_meta(sp)
    return name == 'Text 0' and max_sz >= 2000 and y_ratio < 0.2


def fix_semantic_colors(root):
    """根据文本关键词为文字着色（交通灯体系），跳过标题 shape"""
    for sp in root.iter(qp('sp')):
        if _is_title_shape(sp):
            continue

        # 收集 shape 内全部文本
        full_text = ''.join(t.text or '' for t in sp.iter(qa('t'))).lower()
        if not full_text.strip():
            continue

        # 按优先级匹配：red > orange > green
        matched_color = None
        for priority in ('red', 'orange', 'green'):
            entry = SEMANTIC_COLORS[priority]
            if any(kw.lower() in full_text for kw in entry['keywords']):
                matched_color = entry['color']
                break

        if matched_color is None:
            continue

        # 修改该 shape 内所有 run 的文字颜色
        for rPr in sp.iter(qa('rPr')):
            for sf in rPr.findall(qa('solidFill')):
                rPr.remove(sf)
            sf = etree.SubElement(rPr, qa('solidFill'))
            etree.SubElement(sf, qa('srgbClr')).set('val', matched_color)


# ─── Step 6: shape 高度自适应 ────────────────────────────────────────────────
def _text_needed_height(text, sz_pt, w_emu):
    if not text.strip() or w_emu <= 0:
        return 0
    chars_per_line = max(1, int(w_emu / (sz_pt * EMU_PT * 0.6)))
    lines = sum(max(1, len(p or '') / chars_per_line) for p in text.split('\n'))
    return int(lines * sz_pt * EMU_PT * 1.4) + int(8 * EMU_PT)


def fix_shape_heights(root):
    for sp in root.iter(qp('sp')):
        txBody = sp.find(f'.//{qa("txBody")}')
        if txBody is None:
            continue
        text = ''.join(t.text or '' for t in txBody.iter(qa('t')))
        if not text.strip():
            continue

        max_sz = 1600
        for rPr in txBody.iter(qa('rPr')):
            sz = rPr.get('sz')
            if sz:
                max_sz = max(max_sz, int(sz))
        sz_pt = max_sz / SZ_FACTOR     # P3: sz → pt

        xfrm = None
        for el in sp.iter(qa('xfrm')):
            xfrm = el
            break
        if xfrm is None:               # P2
            continue

        ext = xfrm.find(qa('ext'))
        if ext is None:                # P2
            continue

        w_emu = int(ext.get('cx', 0))
        h_emu = int(ext.get('cy', 0))
        needed = _text_needed_height(text, sz_pt, w_emu)
        if needed > h_emu:
            ext.set('cy', str(needed))


# ─── Step 7: 重叠消解 ────────────────────────────────────────────────────────
def fix_overlaps(root, gap_emu=38100):  # 3pt
    items = []
    for sp in root.iter(qp('sp')):
        for xfrm in sp.iter(qa('xfrm')):
            off = xfrm.find(qa('off'))
            ext = xfrm.find(qa('ext'))
            if off is not None and ext is not None:   # P2
                items.append({
                    'y': int(off.get('y', 0)), 'x': int(off.get('x', 0)),
                    'w': int(ext.get('cx', 0)), 'h': int(ext.get('cy', 0)),
                    'off': off,
                })
            break

    items.sort(key=lambda s: s['y'])

    for i in range(1, len(items)):
        a = items[i]
        for j in range(i):
            b = items[j]
            # 水平方向有重叠
            if a['x'] < b['x'] + b['w'] and a['x'] + a['w'] > b['x']:
                bottom_b = b['y'] + b['h']
                if a['y'] < bottom_b:
                    new_y = bottom_b + gap_emu
                    a['off'].set('y', str(new_y))
                    a['y'] = new_y


# ─── 主流程 ───────────────────────────────────────────────────────────────────
def process_slide(slide_path: Path, font, min_hundredths, pad_emu):
    tree = etree.parse(str(slide_path))
    root = tree.getroot()

    fix_fonts(root, font)
    fix_min_sz(root, min_hundredths)
    fix_size_remap(root)           # Step 2b: 字号重映射（在 min_sz 之后）
    fix_padding(root, pad_emu)
    fix_label_bg_widths(root)      # Step 3b: 短标签底框跟随文字扩宽
    fix_title_bg(root)             # ← 必须在 fix_borders 之前（P1 先处理标题，避免误判）
    fix_borders(root)
    # fix_semantic_colors(root)    # Step 5b: 暂停——匹配逻辑太激进，误染叙述性文本
    # fix_shape_heights(root)     # Step 6: 暂停——高度估算对中文严重偏大，
    #                             # 导致 shape 膨胀 + 级联下推，布局大幅混乱
    # fix_overlaps(root)          # Step 7: 暂停——无法区分背景卡片和文本框，
    #                             # 与 Step 6 级联后所有内容被推到页面底部

    tree.write(str(slide_path), xml_declaration=True,
               encoding='UTF-8', standalone=True)


def run(pptx_in: Path, pptx_out: Path, font, min_sz_pt, pad_pt):
    """P6: 每次从原始文件重新解包，保持干净起始状态"""
    min_h = int(min_sz_pt * SZ_FACTOR)
    pad   = int(pad_pt * EMU_PT)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # 解包
        with zipfile.ZipFile(pptx_in, 'r') as z:
            z.extractall(tmp)

        # 处理所有 slide XML
        slides_dir = tmp / 'ppt' / 'slides'
        if slides_dir.exists():
            for slide_xml in sorted(slides_dir.glob('slide[0-9]*.xml')):
                process_slide(slide_xml, font, min_h, pad)
                print(f'  ✓ {slide_xml.name}')

        # 重新打包（不覆盖原文件）
        with zipfile.ZipFile(pptx_out, 'w', zipfile.ZIP_DEFLATED) as zout:
            for f in tmp.rglob('*'):
                if f.is_file():
                    zout.write(f, f.relative_to(tmp))

    print(f'\n✅ 输出：{pptx_out}')


def main():
    ap = argparse.ArgumentParser(
        description='PPTX 排版优化 — 统一字体/提升字号/增强视觉层次/消解重叠')
    ap.add_argument('pptx', help='输入 PPTX 文件')
    ap.add_argument('--font',     default=DEFAULT_FONT,
                    help=f'目标字体（默认：{DEFAULT_FONT}）')
    ap.add_argument('--min-size', type=float, default=DEFAULT_MIN_SZ,
                    help=f'最小字号 pt（默认：{DEFAULT_MIN_SZ}）')
    ap.add_argument('--padding',  type=float, default=DEFAULT_PAD_PT,
                    help=f'文本框内边距 pt（默认：{DEFAULT_PAD_PT}）')
    ap.add_argument('--output',   help='输出路径（默认：原名 + _v2.pptx）')
    args = ap.parse_args()

    pptx_in = Path(args.pptx)
    if not pptx_in.exists():
        print(f'❌ 文件不存在：{pptx_in}', file=sys.stderr)
        sys.exit(1)

    pptx_out = Path(args.output) if args.output else \
               pptx_in.with_name(pptx_in.stem + '_v2' + pptx_in.suffix)

    print(f'📂 输入：{pptx_in}')
    print(f'🔤 字体：{args.font}  最小字号：{args.min_size}pt  内边距：{args.padding}pt')
    run(pptx_in, pptx_out, args.font, args.min_size, args.padding)


if __name__ == '__main__':
    main()
