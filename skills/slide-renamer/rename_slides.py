#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重命名幻灯片图片文件，根据OCR识别的内容生成slug

用法:
    python rename_slides.py [目录路径]

如果不提供目录路径，则使用当前目录。
"""
import argparse
import os
import re
import sys
import io
from pathlib import Path

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def create_slug(text):
    """从文本创建slug"""
    if not text:
        return ""
    # 转换为小写
    text = text.lower()
    # 移除特殊字符，只保留字母、数字、中文和空格
    text = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', text)
    # 将空格替换为连字符
    text = re.sub(r'\s+', '-', text)
    # 移除多余的连字符
    text = re.sub(r'-+', '-', text)
    # 移除首尾连字符
    text = text.strip('-')
    # 限制slug长度（避免文件名过长）
    if len(text) > 100:
        text = text[:100].rstrip('-')
    return text

def extract_text_from_image(image_path):
    """尝试从图片中提取文本"""
    try:
        from PIL import Image
        import pytesseract

        # 设置 Tesseract 路径 (Windows)
        import os
        if os.name == 'nt':  # Windows
            tesseract_paths = [
                r'D:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            ]
            for path in tesseract_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break

        # 读取图片
        img = Image.open(image_path)
        # OCR识别（支持中英文）
        text = pytesseract.image_to_string(img, lang='chi_sim+eng')
        return text.strip()
    except ImportError:
        print(f"错误: 需要安装 pytesseract 和 tesseract-ocr", file=sys.stderr)
        print(f"安装命令: pip install pytesseract && sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim", file=sys.stderr)
        return None
    except Exception as e:
        print(f"OCR识别失败 {image_path}: {e}", file=sys.stderr)
        return None

def get_title_from_text(text):
    """从OCR文本中提取标题"""
    if not text:
        return None
    
    lines = text.split('\n')
    # 查找最可能的标题行（通常是最长或最靠前的非空行）
    titles = []
    for line in lines:
        line = line.strip()
        if line and len(line) > 3:  # 过滤太短的行
            # 移除常见的OCR噪音
            if not re.match(r'^[\d\s\-\.]+$', line):  # 不是纯数字/符号
                titles.append(line)
    
    if titles:
        # 返回第一行较长的文本作为标题
        return titles[0] if len(titles[0]) > 5 else (titles[1] if len(titles) > 1 else titles[0])
    return None

def extract_slide_number(filename):
    """
    从文件名中提取幻灯片编号
    
    支持多种格式：
    - slide-32.png -> 32
    - image-01.png -> 01
    - page-5.png -> 5
    - 001.png -> 001
    - slide_32.png -> 32
    
    Returns:
        (number_str, is_standard_format): 数字字符串和是否为标准slide-格式
    """
    stem = Path(filename).stem
    
    # 标准格式: slide-{数字} 或 slide_{数字}
    match = re.search(r'slide[-_](\d+)', stem, re.IGNORECASE)
    if match:
        return match.group(1), True
    
    # 其他常见格式: {prefix}-{数字} 或 {prefix}_{数字}
    match = re.search(r'[-_](\d+)', stem)
    if match:
        return match.group(1), False
    
    # 纯数字文件名: {数字}.png
    match = re.match(r'^(\d+)$', stem)
    if match:
        return match.group(1), False
    
    # 文件名开头的数字: {数字}-{其他} 或 {数字}_{其他}
    match = re.match(r'^(\d+)', stem)
    if match:
        return match.group(1), False
    
    return None, False

def rename_slide_files(directory, pattern='*.png', dry_run=False):
    """
    重命名目录中的幻灯片文件
    
    Args:
        directory: 目标目录路径
        pattern: 文件匹配模式，默认为 '*.png'（匹配所有PNG文件）
        dry_run: 如果为True，只显示将要执行的操作，不实际重命名
    """
    dir_path = Path(directory).resolve()
    
    if not dir_path.exists():
        print(f"错误: 目录不存在: {dir_path}", file=sys.stderr)
        return False
    
    if not dir_path.is_dir():
        print(f"错误: 不是目录: {dir_path}", file=sys.stderr)
        return False
    
    slide_files = sorted(dir_path.glob(pattern))
    
    if not slide_files:
        print(f"未找到匹配 '{pattern}' 的文件")
        return True
    
    print(f"找到 {len(slide_files)} 个幻灯片文件")
    if dry_run:
        print("(预览模式 - 不会实际重命名文件)\n")
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for slide_file in slide_files:
        print(f"\n处理: {slide_file.name}")
        
        # 检查是否已经包含slug（避免重复处理）
        # 格式: slide-{数字}_{slug}.png 或其他格式的 {prefix}_{slug}.png
        if '_' in slide_file.stem:
            parts = slide_file.stem.split('_', 1)
            if len(parts) == 2:
                # 检查第一部分是否符合 slide-{数字} 格式
                if re.match(r'^slide-\d+$', parts[0], re.IGNORECASE) and len(parts[1]) > 0:
                    print("  已包含slug（标准格式），跳过")
                    skip_count += 1
                    continue
                # 检查是否已经有slug（非标准格式但包含下划线和slug）
                elif len(parts[1]) > 3:  # slug长度大于3，可能是有效的slug
                    # 进一步检查：如果第一部分包含数字，可能是已处理的文件
                    if re.search(r'\d+', parts[0]):
                        print("  已包含slug，跳过")
                        skip_count += 1
                        continue
        
        # 尝试OCR识别
        text = extract_text_from_image(slide_file)
        if text:
            print(f"  识别到的文本（前100字符）: {text[:100]}...")
            title = get_title_from_text(text)
            if title:
                print(f"  提取的标题: {title}")
                slug = create_slug(title)
                if slug:
                    # 从文件名中提取编号
                    slide_num, is_standard = extract_slide_number(slide_file.name)
                    
                    # 构建新文件名：统一为 slide-{数字}_{slug}.png 格式
                    if slide_num:
                        new_name = f"slide-{slide_num}_{slug}{slide_file.suffix}"
                        if is_standard:
                            print(f"  检测到标准格式，保留编号: {slide_num}")
                        else:
                            print(f"  从文件名提取编号: {slide_num}")
                    else:
                        # 如果无法提取编号，使用原文件名前缀
                        base_name = slide_file.stem
                        new_name = f"{base_name}_{slug}{slide_file.suffix}"
                        print(f"  未找到编号，使用原文件名前缀")
                    
                    new_path = dir_path / new_name
                    
                    if new_path.exists() and new_path != slide_file:
                        print(f"  警告: {new_name} 已存在，跳过")
                        skip_count += 1
                        continue
                    
                    if dry_run:
                        print(f"  [预览] 将重命名为: {new_name}")
                    else:
                        print(f"  重命名为: {new_name}")
                        slide_file.rename(new_path)
                    success_count += 1
                    continue
        
        print(f"  无法识别内容，保持原文件名")
        error_count += 1
    
    print(f"\n完成: 成功 {success_count}, 跳过 {skip_count}, 失败 {error_count}")
    return True

def main():
    parser = argparse.ArgumentParser(
        description='重命名幻灯片图片文件，根据OCR识别的内容生成slug',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 重命名当前目录中的幻灯片
  python rename_slides.py
  
  # 重命名指定目录中的幻灯片
  python rename_slides.py /path/to/deck/folder
  
  # 预览模式（不实际重命名）
  python rename_slides.py --dry-run /path/to/deck/folder
  
  # 自定义文件匹配模式（默认已匹配所有PNG文件）
  python rename_slides.py --pattern "slide-*.png" /path/to/folder
        """
    )
    parser.add_argument(
        'directory',
        nargs='?',
        default='.',
        help='目标目录路径（默认为当前目录）'
    )
    parser.add_argument(
        '--pattern',
        default='*.png',
        help='文件匹配模式（默认: *.png，匹配所有PNG文件）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预览模式：只显示将要执行的操作，不实际重命名'
    )
    
    args = parser.parse_args()
    
    success = rename_slide_files(args.directory, args.pattern, args.dry_run)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
