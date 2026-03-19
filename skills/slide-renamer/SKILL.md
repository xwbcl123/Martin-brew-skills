---
name: slide-renamer
description: Automatically rename slide image files (PNG, JPG, etc.) by adding descriptive slugs based on OCR-recognized content. Use when working with presentation slides, deck folders, or when you need to rename slide images with content-based filenames. Supports Chinese and English OCR recognition.
allowed-tools: Read, Write, Run, Glob
aspg:
  origin:
    vendor: claude
    imported_at: 2026-03-06
---

# Slide Renamer Skill

自动重命名幻灯片图片文件，根据OCR识别的内容生成描述性slug，使文件名与内容相关联。

## When to Use

- 处理演示文稿的幻灯片图片文件
- 需要为幻灯片文件添加描述性文件名
- 批量重命名deck文件夹中的幻灯片
- 需要根据幻灯片内容自动生成slug

## 功能特性

- ✅ 支持中英文OCR识别
- ✅ 自动从图片内容提取标题并生成slug
- ✅ **灵活的文件名格式支持**：自动从各种文件名格式提取编号
- ✅ **统一命名格式**：统一重命名为 `slide-{数字}_{slug}.png` 格式
- ✅ 保留原始幻灯片编号
- ✅ 支持预览模式（dry-run）
- ✅ 可自定义文件匹配模式（默认匹配所有PNG文件）
- ✅ 自动跳过已包含slug的文件
- ✅ **Windows 兼容**：自动检测常见 Tesseract 安装路径
- ✅ **UTF-8 编码支持**：修复 Windows 控制台中文/特殊字符显示问题

## 前置要求

### 系统依赖

#### Windows

```powershell
# 1. 下载并安装 Tesseract OCR
# 下载地址: https://github.com/UB-Mannheim/tesseract/wiki
# 安装时勾选 "Chinese Simplified" 语言包

# 2. 脚本会自动检测以下常见安装路径:
#    - D:\Program Files\Tesseract-OCR\tesseract.exe
#    - C:\Program Files\Tesseract-OCR\tesseract.exe
#    - C:\Program Files (x86)\Tesseract-OCR\tesseract.exe

# 3. 安装 Python 包
pip install pytesseract Pillow
```

#### Ubuntu/Debian

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim
pip install pytesseract Pillow
```

#### macOS

```bash
brew install tesseract tesseract-lang
pip install pytesseract Pillow
```

## 使用方法

### 基本用法

```bash
# 重命名当前目录中的幻灯片
python skills/slide-renamer/rename_slides.py

# 重命名指定目录中的幻灯片
python skills/slide-renamer/rename_slides.py /path/to/deck/folder
```

### 高级用法

```bash
# 预览模式（不实际重命名）
python skills/slide-renamer/rename_slides.py --dry-run /path/to/deck/folder

# 自定义文件匹配模式
python skills/slide-renamer/rename_slides.py --pattern "*.png" /path/to/folder

# 组合使用
python skills/slide-renamer/rename_slides.py --pattern "slide-*.jpg" --dry-run ./deck/example-deck
```

## 文件命名规则

### 支持的输入格式

脚本可以处理多种文件名格式，并统一重命名为标准格式：

**支持的格式示例：**
- `slide-32.png` → `slide-32_{slug}.png`
- `image-01.png` → `slide-01_{slug}.png`
- `page-5.png` → `slide-5_{slug}.png`
- `001.png` → `slide-001_{slug}.png`
- `slide_32.png` → `slide-32_{slug}.png`
- `presentation-10.png` → `slide-10_{slug}.png`

### 编号提取规则

脚本会按以下优先级从文件名中提取编号：
1. 标准格式：`slide-{数字}` 或 `slide_{数字}`
2. 分隔符格式：`{prefix}-{数字}` 或 `{prefix}_{数字}`
3. 纯数字文件名：`{数字}.png`
4. 文件名开头的数字：`{数字}-{其他}` 或 `{数字}_{其他}`

### 输出格式

所有文件统一重命名为：`slide-{编号}_{内容slug}.png`

**示例：**
- `slide-32.png` → `slide-32_6-topics-develop-documents-and-key-messages.png`
- `image-01.png` → `slide-01_6-topics-develop-documents-and-key-messages.png`
- `page-5.png` → `slide-5_key-messages-quantum-security-pqc-qkd.png`

## 工作流程

1. **扫描文件**: 在指定目录中查找匹配模式的幻灯片文件
2. **OCR识别**: 使用Tesseract OCR识别图片中的文本（支持中英文）
3. **提取标题**: 从识别的文本中提取最可能的标题
4. **生成slug**: 将标题转换为URL友好的slug格式
5. **重命名**: 将slug添加到文件名中，保留原始编号

## 在项目中使用

### 示例：重命名deck文件夹中的幻灯片

```bash
# 在项目deck目录中使用
cd "./deck/example-deck"
python ../../skills/slide-renamer/rename_slides.py .
```

### 批量处理多个deck文件夹

```bash
# 处理所有deck文件夹
for dir in "./deck"/*/; do
    echo "处理: $dir"
    python skills/slide-renamer/rename_slides.py "$dir"
done
```

## 注意事项

1. **已包含slug的文件**: 脚本会自动检测并跳过已经包含slug的文件
2. **文件名长度**: slug长度限制为100字符，避免文件名过长
3. **OCR准确性**: OCR识别结果取决于图片质量和清晰度
4. **中文支持**: 需要安装 `tesseract-ocr-chi-sim` 语言包
5. **文件格式**: 默认处理PNG文件，可通过 `--pattern` 参数自定义

## 故障排除

### OCR识别失败

- 检查是否安装了tesseract-ocr和中文语言包
- 确认图片清晰度足够
- 尝试使用预览模式查看识别结果

### 权限错误

- 确保对目标目录有写权限
- 检查文件是否被其他程序占用

### 依赖缺失

```bash
# 检查tesseract是否安装
tesseract --version

# 检查Python包
python3 -c "import pytesseract; print('OK')"
```

## 集成到Claude工作流

当用户需要重命名幻灯片文件时：

1. 识别用户需求（重命名幻灯片、添加slug等）
2. 检查目标目录是否存在
3. 确认tesseract OCR已安装
4. 先使用 `--dry-run` 预览结果
5. 确认后执行实际重命名

## 相关技能

- `pptx`: 处理PowerPoint演示文稿
- `pdf`: 处理PDF文档（可能包含幻灯片）
