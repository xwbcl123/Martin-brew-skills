# Iteration Loop

## Purpose

这个流程用于把人工 polished 结果反哺回 skill，而不是把个例硬编码成一次性规则。

## Inputs

- `raw.md`: NotebookLM 原始导出
- `formatted.md`: 当前脚本输出
- `polished.md`: 用户人工调整后的版本

## How To Iterate

1. 先运行格式化脚本，生成当前版本输出。
2. 用 `--learn-from polished.md` 生成差异笔记。
3. 只把高频、可泛化的差异升级为规则。
4. 更新以下三类资产之一：
   - `scripts/format_notebooklm_export.py`
   - `reference/formatted_example.md`
   - `SKILL.md`
5. 不要把单篇文档独有的措辞偏好写死进脚本。

## What Counts As A Good Generalized Rule

适合沉淀为规则：

- 同类 heading 总是被导出成裸段落
- 同类 emoji 标签总是应转成一级或二级列表
- 引用样式总是可机械转换为 footnotes
- 某类噪音块总是应移除，例如 `导出时间:`

不适合沉淀为规则：

- 用户只在某一篇里手动加了一句总结
- 某一篇里把一个二级标题改成一级标题只是出于偏好
- 对正文内容做了事实补充或措辞润色

## Suggested Iteration Notes Structure

```markdown
# Iteration Notes

## Source
- raw: ...
- polished: ...

## Repeated deltas
- ...

## Candidate generalized rules
- ...

## Keep manual-only
- ...
```
