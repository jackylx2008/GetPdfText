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
import csv
import yaml
from pdf2image import convert_from_path
import pytesseract
from logging_config import setup_logger


# 从配置文件中读取设置
def load_config(config_path="./config.yaml"):
    """从 YAML 配置文件加载配置并返回字典。
    返回字典中期望包含键：
        - pdf_directory
        - output_directory
        - ocr_language
        - dpi
        - log_file (可选)
        - matches_csv (可选)
    """
    with open(config_path, "r", encoding="utf-8") as f:
        conf = yaml.safe_load(f)
    return conf


# 初始化（将在 main 中根据配置覆盖 log_file）
logger = setup_logger(
    log_level=logging.DEBUG,
    log_file="./logs/pdf_ocr_extractor.log",
)


# 设置 Tesseract 可执行路径（按需修改）
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
)


def pdf_to_images(pdf_path, dpi):
    """将 PDF 文件转换为 PIL Image 列表（每页一张）。"""
    try:
        logger.info("开始将PDF文件 %s 转换为图像...", pdf_path)
        images = convert_from_path(pdf_path, dpi=dpi)
        logger.info("PDF文件 %s 成功转换为 %d 张图像。", pdf_path, len(images))
        return images
    except Exception as exc:
        logger.exception("转换PDF为图像时发生错误: %s", exc)
        raise


def ocr_images(images, ocr_language):
    """对每页图像执行 OCR，返回每页文本的列表。"""
    text_per_page = []
    try:
        logger.info("开始对每一页进行OCR识别...")
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image, lang=ocr_language)
            text_per_page.append(text)
            logger.info("第 %d 页OCR识别完成。", i + 1)
        return text_per_page
    except Exception as exc:
        logger.exception("OCR识别过程中发生错误: %s", exc)
        raise


def extract_design_change(text_per_page, pdf_path):
    """在 OCR 结果中查找包含 '设计变更通知单' 的行并返回匹配列表。

    返回的每项为 (pdf_path, page_number, match_text)
    """
    matches = []
    for i, page_text in enumerate(text_per_page):
        if not page_text:
            continue
        for line in page_text.splitlines():
            if "设计变更通知单" in line:
                match_text = line.strip()
                logger.info(
                    "PDF %s 第 %d 页 找到 '设计变更通知单': %s",
                    pdf_path,
                    i + 1,
                    match_text,
                )
                matches.append((pdf_path, i + 1, match_text))
    if not matches:
        logger.debug("PDF %s 中未找到 '设计变更通知单'。", pdf_path)
    return matches


def append_matches_to_csv(matches, csv_path):
    """将匹配结果追加到 CSV 文件，若文件不存在则写入表头。"""
    dirpath = os.path.dirname(csv_path) or "."
    os.makedirs(dirpath, exist_ok=True)
    file_exists = os.path.exists(csv_path)
    try:
        with open(csv_path, "a", encoding="utf-8", newline="") as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(["pdf_path", "page", "text"])
            for pdf_path, page, text in matches:
                writer.writerow([pdf_path, page, text])
        logger.info("已将 %d 条匹配写入 CSV: %s", len(matches), csv_path)
    except (OSError, PermissionError, csv.Error) as exc:
        logger.exception("将匹配写入 CSV 时发生错误: %s; 异常: %s", csv_path, exc)


def process_pdf(pdf_path, output_dir, dpi, ocr_language, matches_csv=None):
    """处理单个 PDF：转换图像并执行 OCR，然后提取匹配并写入 CSV。

    注意：不会将每页文本保存为单独文本文件。
    """
    logger.info("开始处理PDF文件: %s", pdf_path)
    images = pdf_to_images(pdf_path, dpi)
    text_per_page = ocr_images(images, ocr_language)
    # 计算 CSV 路径：优先使用 matches_csv，否则放到 output_dir/matches.csv
    if matches_csv:
        csv_path = matches_csv
    else:
        csv_path = os.path.join(output_dir, "matches.csv")
    matches = extract_design_change(text_per_page, pdf_path)
    if matches:
        append_matches_to_csv(matches, csv_path)
    logger.info("PDF 文件 %s 处理完成。", pdf_path)


def main(config):
    """主入口：读取配置并遍历目录处理 PDF 文件。"""
    # 根据配置初始化 logger（覆盖默认 log_file）
    log_file = config.get("log_file")
    if log_file:
        # 重新初始化 logger handler（简单做法：覆盖模块级 logger）
        globals()["logger"] = setup_logger(
            log_level=logging.DEBUG,
            log_file=log_file,
        )

    pdf_directory = config["pdf_directory"]
    output_directory = config.get("output_directory", "./output")
    ocr_language = config.get("ocr_language", "chi_sim")
    dpi = config.get("dpi", 300)
    matches_csv = config.get("matches_csv")

    logger.info("开始处理目录 %s 中的所有PDF文件...", pdf_directory)

    for file_name in os.listdir(pdf_directory):
        if file_name.lower().endswith(".pdf"):
            pdf_path = os.path.join(pdf_directory, file_name)
            process_pdf(
                pdf_path,
                output_directory,
                dpi,
                ocr_language,
                matches_csv=matches_csv,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF OCR Extractor")
    parser.add_argument(
        "--config", type=str, default="./config.yaml", help="配置文件路径"
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    main(cfg)
