# Slide Renamer Skill

自动重命名幻灯片图片文件，根据OCR识别的内容生成描述性slug，使文件名与内容相关联。

## 快速开始

### 安装依赖

#### Windows

```powershell
# 1. 下载并安装 Tesseract OCR
# 下载地址: https://github.com/UB-Mannheim/tesseract/wiki
# 安装时勾选 "Chinese Simplified" 语言包

# 2. 常见安装路径（脚本会自动检测）:
#    - D:\Program Files\Tesseract-OCR
#    - C:\Program Files\Tesseract-OCR
#    - C:\Program Files (x86)\Tesseract-OCR

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

### 基本使用

```bash
# 重命名当前目录中的幻灯片
python skills/slide-renamer/rename_slides.py

# 重命名指定目录
python skills/slide-renamer/rename_slides.py /path/to/deck/folder

# 预览模式（不实际重命名）
python skills/slide-renamer/rename_slides.py --dry-run /path/to/deck/folder
```

## 在项目中使用

### 方法1：直接调用skill脚本

```bash
# 从项目根目录
python skills/slide-renamer/rename_slides.py "./deck/example-deck"
```

### 方法2：使用本地包装脚本

如果deck文件夹中有 `rename_slides.py` 包装脚本，可以直接运行：

```bash
cd "./deck/example-deck"
python rename_slides.py
```

### 方法3：批量处理多个deck文件夹

```bash
# 处理所有deck文件夹
for dir in "./deck"/*/; do
    echo "处理: $dir"
    python skills/slide-renamer/rename_slides.py "$dir"
done
```

## 功能特性

- ✅ 支持中英文OCR识别
- ✅ 自动提取标题并生成slug
- ✅ **灵活的文件名格式支持**：自动从各种文件名格式提取编号
- ✅ **统一命名格式**：统一重命名为 `slide-{数字}_{slug}.png` 格式
- ✅ 保留原始幻灯片编号
- ✅ 预览模式（dry-run）
- ✅ 自定义文件匹配模式（默认匹配所有PNG文件）
- ✅ 自动跳过已包含slug的文件
- ✅ **Windows 兼容**：自动检测 Tesseract 安装路径
- ✅ **UTF-8 编码支持**：修复 Windows 控制台中文/特殊字符显示问题

## 文件命名示例

### 支持的输入格式

脚本可以处理多种文件名格式，并统一重命名为标准格式：

**重命名前（各种格式）：**
- `slide-32.png`
- `image-01.png`
- `page-5.png`
- `001.png`

**重命名后（统一格式）：**
- `slide-32_6-topics-develop-documents-and-key-messages.png`
- `slide-01_6-topics-develop-documents-and-key-messages.png`
- `slide-5_key-messages-quantum-security-pqc-qkd.png`
- `slide-001_support-matrix.png`

## 命令行选项

```bash
python rename_slides.py [目录] [选项]

选项:
  --pattern PATTERN    文件匹配模式（默认: *.png，匹配所有PNG文件）
  --dry-run           预览模式，不实际重命名
  -h, --help          显示帮助信息
```

**注意：** 默认模式 `*.png` 会匹配所有PNG文件，脚本会自动从文件名中提取编号。如果只想处理特定格式的文件，可以使用 `--pattern` 参数。

## 故障排除

### OCR识别失败

1. 检查tesseract是否安装：`tesseract --version`
2. 检查中文语言包：`tesseract --list-langs`（应包含chi_sim）
3. 确认图片清晰度足够

### Windows: Tesseract 未找到

脚本会自动检测以下路径：
- `D:\Program Files\Tesseract-OCR\tesseract.exe`
- `C:\Program Files\Tesseract-OCR\tesseract.exe`
- `C:\Program Files (x86)\Tesseract-OCR\tesseract.exe`

如果安装在其他位置，可以：

**方法1**: 添加到系统 PATH 环境变量

**方法2**: 在脚本中添加自定义路径，编辑 `rename_slides.py`：
```python
# 在 tesseract_paths 列表中添加你的安装路径
tesseract_paths = [
    r'D:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'你的自定义路径\tesseract.exe',  # 添加这行
]
```

### Windows: 中文/特殊字符显示乱码

脚本已内置 UTF-8 编码修复，如仍有问题：
```powershell
# 设置控制台编码
chcp 65001
```

### 权限错误

确保对目标目录有写权限。

### Python依赖缺失

```bash
pip install pytesseract Pillow
```

## 相关文档

详细文档请参考 [SKILL.md](SKILL.md)
