# Deep Research Citation Formatter - 快速参考

## 常用命令

```bash
# 检查文件格式和引用统计
python skills/ds-citations/scripts/format_ds_citations.py -c <文件或目录>

# 预览转换（不写入）
python skills/ds-citations/scripts/format_ds_citations.py -n <文件>

# 执行转换
python skills/ds-citations/scripts/format_ds_citations.py <文件或目录>

# 递归处理子目录
python skills/ds-citations/scripts/format_ds_citations.py -r <目录>
```

## 输出符号

| 符号 | 含义 |
|------|------|
| ✓ | 成功处理 |
| ◈ | 已是目标格式 |
| ⊘ | 跳过 |
| ✗ | 错误 |
| ⚠ | 警告 |

## 支持的格式

- **GPT Deep Research**: `[[n]](URL)` → `[^n]`
- **Gemini Deep Research**: ` n。` → `[^n]`

## 详细文档

参见 `skills/ds-citations/SKILL.md`
