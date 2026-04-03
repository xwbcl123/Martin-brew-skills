#!/usr/bin/env python3
"""
pptx_diff.py — PPTX 样式 diff 工具
比较两个 PPTX 文件的样式属性差异（字号、颜色、边框、位置），过滤纯文本变化。
用于 pptx-polish skill 的 Mode B (Learn) 迭代优化流程。

用法:
  python pptx_diff.py before.pptx after.pptx [--ignore-text] [--output report.md]
"""

import argparse
import io
import sys
import tempfile
import zipfile

# Windows GBK 兼容：强制 stdout 使用 UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from collections import defaultdict
from pathlib import Path
from lxml import etree

# ─── OOXML 命名空间 ──────────────────────────────────────────────────────────
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'

def q(ns, local):
    return f'{{{ns}}}{local}'

def qa(local):
    return q(A, local)

def qp(local):
    return q(P, local)

SZ_FACTOR = 100


# ─── 提取 shape 信息 ─────────────────────────────────────────────────────────
def _get_shape_name(sp):
    for el in sp.iter():
        if el.tag.endswith('}cNvPr'):
            return el.get('name', '')
    return ''


def _get_text(sp):
    return ''.join(t.text or '' for t in sp.iter(qa('t')))


def _get_font_sizes(sp):
    """返回 shape 内所有字号（hundredths），去重排序"""
    sizes = set()
    for tag in (qa('rPr'), qa('endParaRPr'), qa('defRPr')):
        for el in sp.iter(tag):
            sz = el.get('sz')
            if sz:
                sizes.add(int(sz))
    return sorted(sizes)


def _get_colors(sp):
    """返回 shape 内所有颜色值（从 solidFill/srgbClr）"""
    colors = set()
    for sf in sp.iter(qa('solidFill')):
        for clr in sf:
            val = clr.get('val')
            if val:
                colors.add(val.upper())
    return sorted(colors)


def _get_borders(sp):
    """返回边框信息 [(width, color), ...]"""
    borders = []
    spPr = sp.find(f'.//{qa("spPr")}')
    if spPr is None:
        return borders
    for ln in spPr.findall(qa('ln')):
        w = ln.get('w', '0')
        color = ''
        for sf in ln.findall(qa('solidFill')):
            for clr in sf:
                color = clr.get('val', '').upper()
        borders.append((w, color))
    return borders


def _get_position(sp):
    """返回 (x, y, cx, cy) in EMU"""
    for xfrm in sp.iter(qa('xfrm')):
        off = xfrm.find(qa('off'))
        ext = xfrm.find(qa('ext'))
        if off is not None and ext is not None:
            return (int(off.get('x', 0)), int(off.get('y', 0)),
                    int(ext.get('cx', 0)), int(ext.get('cy', 0)))
    return None


def _extract_shapes(slide_path):
    """从 slide XML 提取所有 shape 的样式信息"""
    tree = etree.parse(str(slide_path))
    root = tree.getroot()
    shapes = []
    for sp in root.iter(qp('sp')):
        shapes.append({
            'name': _get_shape_name(sp),
            'text': _get_text(sp),
            'sizes': _get_font_sizes(sp),
            'colors': _get_colors(sp),
            'borders': _get_borders(sp),
            'position': _get_position(sp),
        })
    return shapes


# ─── 解包 PPTX ──────────────────────────────────────────────────────────────
def _unpack(pptx_path, tmp_dir):
    with zipfile.ZipFile(pptx_path, 'r') as z:
        z.extractall(tmp_dir)
    slides_dir = Path(tmp_dir) / 'ppt' / 'slides'
    if not slides_dir.exists():
        return []
    return sorted(slides_dir.glob('slide[0-9]*.xml'),
                  key=lambda p: int(p.stem.replace('slide', '')))


# ─── 比较两个 shape 列表 ─────────────────────────────────────────────────────
def _match_shapes(shapes_a, shapes_b):
    """按 shape name 匹配，返回 [(shape_a, shape_b), ...]"""
    by_name_a = {}
    for s in shapes_a:
        key = s['name']
        if key not in by_name_a:
            by_name_a[key] = s
    by_name_b = {}
    for s in shapes_b:
        key = s['name']
        if key not in by_name_b:
            by_name_b[key] = s

    matched = []
    all_names = sorted(set(list(by_name_a.keys()) + list(by_name_b.keys())))
    for name in all_names:
        a = by_name_a.get(name)
        b = by_name_b.get(name)
        matched.append((name, a, b))
    return matched


def _diff_slide(shapes_a, shapes_b):
    """比较两个 slide 的 shape 样式差异，返回 diff 列表"""
    diffs = []
    for name, a, b in _match_shapes(shapes_a, shapes_b):
        if a is None:
            diffs.append({'shape': name, 'type': 'shape_added',
                          'detail': f'新增 shape: {b["text"][:40]}'})
            continue
        if b is None:
            diffs.append({'shape': name, 'type': 'shape_removed',
                          'detail': f'删除 shape: {a["text"][:40]}'})
            continue

        text_snippet = a['text'][:30].replace('\n', ' ')

        # 字号差异
        if a['sizes'] != b['sizes']:
            removed = set(a['sizes']) - set(b['sizes'])
            added = set(b['sizes']) - set(a['sizes'])
            parts = []
            if removed:
                parts.append(f'移除 {",".join(f"{s/SZ_FACTOR}pt" for s in sorted(removed))}')
            if added:
                parts.append(f'新增 {",".join(f"{s/SZ_FACTOR}pt" for s in sorted(added))}')
            diffs.append({
                'shape': name, 'type': 'font_size', 'text': text_snippet,
                'before': [f'{s/SZ_FACTOR}pt' for s in a['sizes']],
                'after': [f'{s/SZ_FACTOR}pt' for s in b['sizes']],
                'detail': '; '.join(parts),
            })

        # 颜色差异
        if a['colors'] != b['colors']:
            removed = set(a['colors']) - set(b['colors'])
            added = set(b['colors']) - set(a['colors'])
            parts = []
            if removed:
                parts.append(f'移除 #{",#".join(sorted(removed))}')
            if added:
                parts.append(f'新增 #{",#".join(sorted(added))}')
            diffs.append({
                'shape': name, 'type': 'color', 'text': text_snippet,
                'before': [f'#{c}' for c in a['colors']],
                'after': [f'#{c}' for c in b['colors']],
                'detail': '; '.join(parts),
            })

        # 边框差异
        if a['borders'] != b['borders']:
            diffs.append({
                'shape': name, 'type': 'border', 'text': text_snippet,
                'before': a['borders'], 'after': b['borders'],
                'detail': f'{a["borders"]} → {b["borders"]}',
            })

        # 位置/尺寸差异
        if a['position'] != b['position'] and a['position'] and b['position']:
            ax, ay, acx, acy = a['position']
            bx, by_, bcx, bcy = b['position']
            changes = []
            if ax != bx: changes.append(f'x: {ax}→{bx}')
            if ay != by_: changes.append(f'y: {ay}→{by_}')
            if acx != bcx: changes.append(f'w: {acx}→{bcx}')
            if acy != bcy: changes.append(f'h: {acy}→{bcy}')
            if changes:
                diffs.append({
                    'shape': name, 'type': 'position', 'text': text_snippet,
                    'detail': '; '.join(changes),
                })

    return diffs


# ─── 生成报告 ────────────────────────────────────────────────────────────────
def _generate_report(slide_diffs, n_slides_a, n_slides_b, path_a, path_b):
    lines = []
    lines.append(f'# PPTX Style Diff Report')
    lines.append(f'')
    lines.append(f'- **Before**: `{path_a}`')
    lines.append(f'- **After**: `{path_b}`')
    lines.append(f'- **Slides**: {n_slides_a} → {n_slides_b}')
    lines.append(f'')

    if n_slides_a != n_slides_b:
        lines.append(f'## 结构变化')
        lines.append(f'')
        if n_slides_b > n_slides_a:
            for i in range(n_slides_a + 1, n_slides_b + 1):
                lines.append(f'- Slide {i}: **新增页**（非样式模式）')
        else:
            for i in range(n_slides_b + 1, n_slides_a + 1):
                lines.append(f'- Slide {i}: **删除页**')
        lines.append(f'')

    # 按类型汇总
    all_diffs = []
    for slide_num, diffs in slide_diffs.items():
        for d in diffs:
            d['slide'] = slide_num
            all_diffs.append(d)

    by_type = defaultdict(list)
    for d in all_diffs:
        by_type[d['type']].append(d)

    type_labels = {
        'font_size': '字号变化',
        'color': '颜色变化',
        'border': '边框变化',
        'position': '位置/尺寸变化',
        'shape_added': '新增 Shape',
        'shape_removed': '删除 Shape',
    }

    for typ, label in type_labels.items():
        items = by_type.get(typ, [])
        if not items:
            continue
        lines.append(f'## {label}')
        lines.append(f'')
        lines.append(f'| Slide | Shape | 文本片段 | 变化 |')
        lines.append(f'|-------|-------|---------|------|')
        for d in sorted(items, key=lambda x: x['slide']):
            text = d.get('text', d.get('detail', ''))[:30]
            lines.append(f'| {d["slide"]} | `{d["shape"]}` | {text} | {d["detail"]} |')
        lines.append(f'')

    # 可编码模式建议
    lines.append(f'## 可编码模式建议')
    lines.append(f'')

    # 字号重映射模式
    sz_remaps = defaultdict(int)
    for d in by_type.get('font_size', []):
        before_set = set(d.get('before', []))
        after_set = set(d.get('after', []))
        removed = before_set - after_set
        added = after_set - before_set
        if len(removed) == 1 and len(added) == 1:
            sz_remaps[(removed.pop(), added.pop())] += 1

    if sz_remaps:
        lines.append(f'### 字号重映射')
        for (frm, to), count in sorted(sz_remaps.items()):
            confidence = '高频' if count >= 2 else '高置信单点'
            lines.append(f'- `{frm}` → `{to}` (出现 {count} 次, {confidence})')
        lines.append(f'')

    # 颜色模式
    color_adds = defaultdict(int)
    for d in by_type.get('color', []):
        after = set(d.get('after', [])) - set(d.get('before', []))
        for c in after:
            color_adds[c] += 1

    if color_adds:
        lines.append(f'### 新增颜色')
        for color, count in sorted(color_adds.items(), key=lambda x: -x[1]):
            confidence = '高频' if count >= 2 else '需人工判断'
            lines.append(f'- `{color}` (出现 {count} 次, {confidence})')
        lines.append(f'')

    # 需人工判断
    low_confidence = [d for d in all_diffs
                      if d['type'] in ('shape_added', 'shape_removed', 'position')]
    if low_confidence:
        lines.append(f'## 需人工判断')
        lines.append(f'')
        for d in low_confidence:
            lines.append(f'- Slide {d["slide"]}: {d["detail"]}')
        lines.append(f'')

    if not all_diffs:
        lines.append(f'*无样式差异*')
        lines.append(f'')

    return '\n'.join(lines)


# ─── 主流程 ──────────────────────────────────────────────────────────────────
def run(pptx_a, pptx_b, output_path=None):
    with tempfile.TemporaryDirectory() as tmp_a, \
         tempfile.TemporaryDirectory() as tmp_b:

        slides_a = _unpack(pptx_a, tmp_a)
        slides_b = _unpack(pptx_b, tmp_b)

        n_a, n_b = len(slides_a), len(slides_b)
        n_common = min(n_a, n_b)

        slide_diffs = {}
        for i in range(n_common):
            shapes_a = _extract_shapes(slides_a[i])
            shapes_b = _extract_shapes(slides_b[i])
            diffs = _diff_slide(shapes_a, shapes_b)
            if diffs:
                slide_diffs[i + 1] = diffs

        report = _generate_report(slide_diffs, n_a, n_b, str(pptx_a), str(pptx_b))

        if output_path:
            Path(output_path).write_text(report, encoding='utf-8')
            print(f'📄 报告已保存: {output_path}')
        else:
            print(report)

        changed = len(slide_diffs)
        total_diffs = sum(len(d) for d in slide_diffs.values())
        print(f'\n📊 统计: {changed}/{n_common} slides 有样式差异, 共 {total_diffs} 处变化')

        return report


def main():
    ap = argparse.ArgumentParser(description='PPTX 样式 diff 工具')
    ap.add_argument('before', help='修改前的 PPTX')
    ap.add_argument('after', help='修改后的 PPTX')
    ap.add_argument('--output', '-o', help='输出报告路径（默认打印到终端）')
    ap.add_argument('--ignore-text', action='store_true',
                    help='过滤纯文本变化（默认已过滤，此参数保留用于兼容）')
    args = ap.parse_args()

    for f in (args.before, args.after):
        if not Path(f).exists():
            print(f'❌ 文件不存在: {f}', file=sys.stderr)
            sys.exit(1)

    run(Path(args.before), Path(args.after), args.output)


if __name__ == '__main__':
    main()
