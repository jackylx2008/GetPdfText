"""pdf_ocr_extractor

将 PDF 每页转换为图像并使用 Tesseract OCR 识别文本，
将每页的识别结果以文本文件保存到输出目录。

主要函数：
- load_config: 从 YAML 配置文件读取设置
- pdf_to_images: 将 PDF 转换为 PIL 图像列表
- ocr_images: 对每张图像执行 OCR，返回每页文本
- save_text: 将每页文本保存为单独的 .txt 文件
- process_pdf: 对单个 PDF 执行完整流程
- main: 遍历目录并处理所有 PDF 文件

用法:
    python pdf_ocr_extractor.py --config ./config.yaml
"""

import os
import logging
import argparse
import yaml
from pdf2image import convert_from_path
import pytesseract
from logging_config import setup_logger  # 引入日志配置模块

# 设置日志记录
logger = setup_logger(
    log_level=logging.DEBUG,
    log_file="./logs/pdf_ocr_extractor.log",
)


# 从配置文件中读取设置
def load_config(config_path="./config.yaml"):
    """从 YAML 配置文件加载配置并返回字典。

    Args:
        config_path (str): 配置文件路径，默认为 "./config.yaml"。

    Returns:
        dict: 配置字典，通常包含 'pdf_directory',
            'output_directory', 'ocr_language', 'dpi' 等键。

    Raises:
        FileNotFoundError: 如果配置文件不存在。
        yaml.YAMLError: 如果 YAML 解析失败。
    """
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg


# 设置Tesseract的路径，如果你没有配置系统路径，可以设置Tesseract的安装路径
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # 请根据你的Tesseract安装路径修改
)


# 将PDF转换为图像
def pdf_to_images(pdf_path, dpi):
    """将 PDF 文件转换为图像列表（每页一张）。

    Args:
        pdf_path (str): PDF 文件路径。
        dpi (int): 转换图像的分辨率。

    Returns:
        list: 每页对应的 PIL Image 列表。

    Raises:
        Exception: 转换过程中发生的异常会被向上抛出。
    """
    try:
        logger.info("开始将PDF文件 %s 转换为图像...", pdf_path)
        images = convert_from_path(pdf_path, dpi=dpi)  # 将PDF转换为每页一张图片
        logger.info("PDF文件 %s 成功转换为 %d 张图像。", pdf_path, len(images))
        return images
    except Exception as e:
        logger.exception("转换PDF为图像时发生错误: %s", e)
        raise


# 使用Tesseract进行OCR识别
def ocr_images(images, ocr_language):
    """对图像列表执行 OCR，返回每页文本。

    Args:
        images (list): 要识别的 PIL Image 列表。
        ocr_language (str): tesseract 使用的语言代码，如 'chi_sim' 或 'eng'。

    Returns:
        list: 每页识别出的文本字符串列表。

    Raises:
        Exception: OCR 过程中发生的异常会向上抛出。
    """
    text_per_page = []
    try:
        logger.info("开始对每一页进行OCR识别...")
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(
                image, lang=ocr_language
            )  # 使用配置的OCR语言
            text_per_page.append(text)
            logger.info("第 %d 页OCR识别完成。", i + 1)
        return text_per_page
    except Exception as e:
        logger.exception("OCR识别过程中发生错误: %s", e)
        raise


# 保存每一页识别的文本
def save_text(text_per_page, output_dir):
    """将每页文本保存到输出目录，每页一个文件。

    Args:
        text_per_page (list): 每页的识别文本列表。
        output_dir (str): 输出目录路径。

    Raises:
        Exception: 保存文件时发生的异常会向上抛出。
    """
    try:
        logger.info("将OCR识别的文本保存到目录: %s", output_dir)
        os.makedirs(output_dir, exist_ok=True)
        for i, text in enumerate(text_per_page):
            file_path = os.path.join(output_dir, f"page_{i + 1}.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)
        logger.info("文本保存完成。")
    except Exception as e:
        logger.exception("保存OCR文本时发生错误: %s", e)
        raise


# 处理PDF文件并进行OCR识别
def process_pdf(pdf_path, output_dir, dpi, ocr_language):
    """处理单个 PDF：转换图像、执行 OCR 并保存文本。

    Args:
        pdf_path (str): PDF 文件路径。
        output_dir (str): 文本输出目录。
        dpi (int): 图像转换分辨率。
        ocr_language (str): OCR 语言代码。
    """
    logger.info("开始处理PDF文件: %s", pdf_path)
    images = pdf_to_images(pdf_path, dpi)
    text_per_page = ocr_images(images, ocr_language)
    save_text(text_per_page, output_dir)
    logger.info("PDF文件处理完成，识别的文本已保存到 %s。", output_dir)


# 主函数，遍历目录下所有PDF文件
def main(cfg):
    """主函数：遍历目录并处理所有 PDF 文件。

    Args:
        config (dict): 配置字典，必须包含 'pdf_directory',
            'output_directory', 'ocr_language' 和 'dpi'。
    """
    pdf_directory = cfg["pdf_directory"]
    output_directory = cfg["output_directory"]
    ocr_language = cfg["ocr_language"]
    dpi = cfg["dpi"]

    logger.info("开始处理目录 %s 中的所有PDF文件...", pdf_directory)

    # 遍历目录下的所有PDF文件
    for file_name in os.listdir(pdf_directory):
        if file_name.lower().endswith(".pdf"):
            pdf_path = os.path.join(pdf_directory, file_name)
            process_pdf(pdf_path, output_directory, dpi, ocr_language)


# 命令行解析
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF OCR Extractor")
    parser.add_argument(
        "--config", type=str, default="./config.yaml", help="配置文件路径"
    )
    args = parser.parse_args()

    # 加载配置文件
    config = load_config(args.config)
    main(config)
