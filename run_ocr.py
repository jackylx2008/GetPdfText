"""
运行 PDF OCR 提取器的脚本。

此脚本加载配置，初始化 PdfOcrExtractor 类，并遍历指定目录处理 PDF 文件。
"""

import os
import argparse
import yaml
import logging
import csv
import concurrent.futures
from logging_config import setup_logger
from pdf_ocr_extractor import PdfOcrExtractor


def load_config(config_path="./config.yaml"):
    """从 YAML 配置文件加载配置并返回字典。"""
    with open(config_path, "r", encoding="utf-8") as f:
        conf = yaml.safe_load(f)
    return conf


def process_pdf_wrapper(args):
    """
    并行处理的包装函数。

    :param args: 元组 (pdf_path, config)
    :return: (matches, error_message)
    """
    pdf_path, config = args
    try:
        # 在子进程中初始化提取器
        # 注意：这里不传递主进程的 logger，避免 pickle 问题
        # 提取器会使用默认的 logger，可能会输出到控制台
        extractor = PdfOcrExtractor(config)
        matches = extractor.extract_matches_from_pdf(pdf_path)
        return matches, None
    except Exception as e:
        return None, str(e)


def main():
    parser = argparse.ArgumentParser(description="PDF OCR Extractor Runner")
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
    log_file = config.get("log_file", "./logs/pdf_ocr_extractor.log")
    logger = setup_logger(
        log_level=logging.DEBUG,
        log_file=log_file,
    )

    pdf_directory = config.get("pdf_directory")
    if not pdf_directory:
        logger.error("配置文件中未指定 pdf_directory")
        return

    if not os.path.exists(pdf_directory):
        logger.error("PDF 目录不存在: %s", pdf_directory)
        return

    logger.info("开始处理目录 %s 中的所有PDF文件...", pdf_directory)

    # 收集所有 PDF 文件路径
    pdf_files = [
        os.path.join(pdf_directory, f)
        for f in os.listdir(pdf_directory)
        if f.lower().endswith(".pdf")
    ]

    total_files = len(pdf_files)
    if total_files == 0:
        logger.info("未找到 PDF 文件。")
        return

    logger.info("共找到 %d 个 PDF 文件，准备并行处理...", total_files)

    all_matches = []
    count = 0

    # 使用 ProcessPoolExecutor 进行并行处理
    with concurrent.futures.ProcessPoolExecutor() as executor:
        # 提交任务
        future_to_pdf = {
            executor.submit(process_pdf_wrapper, (pdf_path, config)): pdf_path
            for pdf_path in pdf_files
        }

        for future in concurrent.futures.as_completed(future_to_pdf):
            pdf_path = future_to_pdf[future]
            file_name = os.path.basename(pdf_path)
            try:
                matches, error = future.result()
                if error:
                    logger.error("处理文件 %s 时出错: %s", file_name, error)
                else:
                    if matches:
                        all_matches.extend(matches)
                    count += 1
                    logger.info("已完成 (%d/%d): %s", count, total_files, file_name)
            except Exception as exc:
                logger.error("处理文件 %s 时发生未捕获异常: %s", file_name, exc)

    # 合并所有匹配结果
    if all_matches:
        logger.info("正在合并所有匹配结果...")

        # 确定 CSV 路径
        matches_csv = config.get("matches_csv")
        output_directory = config.get("output_directory", "./output")

        if matches_csv:
            csv_path = matches_csv
        else:
            csv_path = os.path.join(output_directory, "matches.csv")

        dirpath = os.path.dirname(csv_path) or "."
        os.makedirs(dirpath, exist_ok=True)

        file_exists = os.path.exists(csv_path)
        try:
            with open(csv_path, "a", encoding="utf-8", newline="") as csvfile:
                writer = csv.writer(csvfile)
                if not file_exists:
                    writer.writerow(["pdf_path", "page", "text"])
                for pdf_path, page, text in all_matches:
                    writer.writerow([pdf_path, page, text])
            logger.info("已将 %d 条匹配写入 CSV: %s", len(all_matches), csv_path)
        except (OSError, PermissionError, csv.Error) as exc:
            logger.exception("将匹配写入 CSV 时发生错误: %s; 异常: %s", csv_path, exc)

    logger.info("所有任务完成，共处理了 %d 个 PDF 文件。", count)


if __name__ == "__main__":
    main()
