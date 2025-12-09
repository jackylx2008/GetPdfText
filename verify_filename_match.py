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
import concurrent.futures
import csv
import re
import warnings
from PIL import Image
from logging_config import setup_logger
from pdf_ocr_extractor import PdfOcrExtractor

# 优化并行性能：限制 Tesseract/OpenMP 每个进程只使用一个线程
# 这样可以安全地运行与 CPU 核心数相同数量的并行进程
os.environ["OMP_THREAD_LIMIT"] = "1"

# 将 DecompressionBombWarning 设置为错误，以便捕获
warnings.simplefilter("error", Image.DecompressionBombWarning)


def load_config(config_path="./config.yaml"):
    """从 YAML 配置文件加载配置并返回字典。"""
    with open(config_path, "r", encoding="utf-8") as f:
        conf = yaml.safe_load(f)
    return conf


def verify_pdf_wrapper(args):
    """
    并行验证的包装函数。

    :param args: 元组 (pdf_path, config, filename_regex)
    :return: (matches, error_message)
    """
    pdf_path, config, filename_regex = args
    try:
        # 在子进程中初始化提取器
        extractor = PdfOcrExtractor(config)
        # 提取正则匹配内容，从第2页开始
        matches = extractor.extract_regex_matches(
            pdf_path, filename_regex, start_page=2
        )
        return matches, None
    except Image.DecompressionBombWarning:
        return None, "DecompressionBombWarning"
    except Image.DecompressionBombError:
        return None, "DecompressionBombError"
    except Exception as e:
        return None, str(e)


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
    # 使用单独的日志文件，每次运行清空
    log_file = "./logs/verify_filename_match.log"
    logger = setup_logger(
        log_level=logging.DEBUG,
        log_file=log_file,
        mode="w",
    )

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

    # 准备 unmatches.csv 和 skipped_errors.csv
    output_directory = config.get("output_directory", "./output")
    os.makedirs(output_directory, exist_ok=True)
    unmatch_csv_path = os.path.join(output_directory, "unmatches.csv")
    skipped_csv_path = os.path.join(output_directory, "skipped_errors.csv")

    # 初始化 CSV 文件
    try:
        with open(unmatch_csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["file_name", "filename_match", "ocr_matches"])

        with open(skipped_csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["file_name", "error_type"])
    except Exception as e:
        logger.error("无法创建 CSV 文件: %s", e)
        return

    count = 0
    mismatch_count = 0

    # 显式设置 max_workers 为 CPU 核心数，确保充分利用 32 核
    max_workers = os.cpu_count()
    logger.info("使用 %d 个并行进程进行处理...", max_workers)

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_pdf = {
            executor.submit(
                verify_pdf_wrapper, (pdf_path, config, filename_regex)
            ): pdf_path
            for pdf_path in pdf_files
        }

        for future in concurrent.futures.as_completed(future_to_pdf):
            pdf_path = future_to_pdf[future]
            file_name = os.path.basename(pdf_path)

            try:
                matches, error = future.result()

                if error:
                    if (
                        "DecompressionBombWarning" in error
                        or "DecompressionBombError" in error
                    ):
                        logger.warning(
                            "文件 %s 触发 DecompressionBombWarning/Error，跳过处理。",
                            file_name,
                        )
                        with open(
                            skipped_csv_path, "a", encoding="utf-8", newline=""
                        ) as f:
                            writer = csv.writer(f)
                            # 记录具体的错误类型 (Warning 或 Error)
                            writer.writerow([file_name, error])
                    else:
                        logger.error("处理文件 %s 时出错: %s", file_name, error)
                    continue

                # 如果没有匹配到任何内容，直接跳过，不记录
                if not matches:
                    logger.info("文件 %s 未匹配到任何正则内容，跳过。", file_name)
                    continue

                # 1. 从文件名中提取符合正则的字符串
                filename_match_obj = re.search(filename_regex, file_name)
                filename_match_str = (
                    filename_match_obj.group(0) if filename_match_obj else None
                )

                if not filename_match_str:
                    logger.warning("文件名 %s 不符合正则表达式规则", file_name)
                    # 如果文件名本身都不符合规则，记录为 mismatch
                    with open(unmatch_csv_path, "a", encoding="utf-8", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow(
                            [file_name, "NO_MATCH_IN_FILENAME", str(matches)]
                        )
                    mismatch_count += 1
                    continue

                # 2. 检查 OCR 结果中是否包含该字符串
                is_match = False
                if filename_match_str in matches:
                    is_match = True

                if is_match:
                    logger.info(
                        "验证通过: 文件名匹配 '%s' 在 OCR 结果中找到",
                        filename_match_str,
                    )
                else:
                    logger.warning(
                        "验证失败: 文件名匹配 '%s' 未在 OCR 结果 %s 中找到",
                        filename_match_str,
                        matches,
                    )
                    mismatch_count += 1
                    # 写入 unmatches.csv
                    with open(unmatch_csv_path, "a", encoding="utf-8", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow([file_name, filename_match_str, str(matches)])

                count += 1

            except Exception as exc:
                logger.error("处理文件 %s 时发生未捕获异常: %s", file_name, exc)

    logger.info("验证完成。共处理 %d 个文件，发现 %d 个不匹配。", count, mismatch_count)

    # 对结果文件进行排序
    def sort_csv(file_path):
        if not os.path.exists(file_path):
            return
        try:
            with open(file_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)

            if len(rows) > 1:
                header = rows[0]
                data = rows[1:]
                # 按第一列 (file_name) 排序
                data.sort(key=lambda x: x[0])

                with open(file_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(header)
                    writer.writerows(data)
                logger.info("已对文件进行排序: %s", file_path)
        except Exception as e:
            logger.error("排序文件 %s 时出错: %s", file_path, e)

    sort_csv(unmatch_csv_path)
    sort_csv(skipped_csv_path)


if __name__ == "__main__":
    main()
