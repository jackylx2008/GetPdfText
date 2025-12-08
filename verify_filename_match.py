"""
验证 PDF 文件名是否包含 OCR 识别出的特定内容。

此脚本遍历指定目录下的 PDF 文件，进行 OCR 识别，
使用配置文件中的正则表达式提取内容，并检查提取的内容是否包含在文件名中。
如果不匹配，则记录到日志中。
"""

import os
import argparse
import yaml
import logging
from logging_config import setup_logger
from pdf_ocr_extractor import PdfOcrExtractor


def load_config(config_path="./config.yaml"):
    """从 YAML 配置文件加载配置并返回字典。"""
    with open(config_path, "r", encoding="utf-8") as f:
        conf = yaml.safe_load(f)
    return conf


def main():
    parser = argparse.ArgumentParser(description="Verify PDF Filename Match")
    parser.add_argument(
        "--config", type=str, default="./config.yaml", help="配置文件路径"
    )
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"无法加载配置文件: {e}")
        return

    # 初始化 logger
    # 使用单独的日志文件
    log_file = "./logs/verify_filename.log"
    logger = setup_logger(
        log_level=logging.DEBUG,
        log_file=log_file,
    )

    # 初始化提取器
    extractor = PdfOcrExtractor(config, logger)

    pdf_directory = config.get("pdf_directory")
    filename_regex = config.get("filename_regex")

    if not pdf_directory:
        logger.error("配置文件中未指定 pdf_directory")
        return

    if not filename_regex:
        logger.error("配置文件中未指定 filename_regex")
        return

    if not os.path.exists(pdf_directory):
        logger.error("PDF 目录不存在: %s", pdf_directory)
        return

    logger.info("开始验证目录 %s 中的 PDF 文件...", pdf_directory)
    logger.info("使用的正则表达式: %s", filename_regex)

    count = 0
    mismatch_count = 0

    for file_name in os.listdir(pdf_directory):
        if file_name.lower().endswith(".pdf"):
            pdf_path = os.path.join(pdf_directory, file_name)
            try:
                # 提取正则匹配内容，从第2页开始
                matches = extractor.extract_regex_matches(
                    pdf_path, filename_regex, start_page=2
                )

                if matches:
                    logger.info(
                        "测试提示：文件 %s 在第2页(及以后)匹配到正则内容: %s",
                        file_name,
                        matches,
                    )

                if not matches:
                    logger.warning("文件 %s 中未找到符合正则的内容", file_name)
                    continue

                # 检查匹配内容是否在文件名中
                # 只要有一个匹配项在文件名中，就算通过？
                # 或者所有匹配项都必须在文件名中？
                # 通常假设只要提取到的编号在文件名里就行

                is_match = False
                matched_str = ""

                for m in matches:
                    if m in file_name:
                        is_match = True
                        matched_str = m
                        break

                if is_match:
                    logger.info(
                        "验证通过: 文件名 '%s' 包含 '%s'", file_name, matched_str
                    )
                else:
                    logger.warning(
                        "验证失败: 文件名 '%s' 不包含任何提取的内容 %s",
                        file_name,
                        matches,
                    )
                    mismatch_count += 1

                count += 1

            except Exception as e:
                logger.error("处理文件 %s 时出错: %s", file_name, e)

    logger.info("验证完成。共处理 %d 个文件，发现 %d 个不匹配。", count, mismatch_count)


if __name__ == "__main__":
    main()
