"""
脚本功能：针对 B24 配套酒店独立 PDF 扫描文件进行变更编号的匹配与重命名。
实现逻辑：
1. 加载 YAML 配置文件，获取 PDF 目录、CSV 目录及正则匹配规则。
2. 遍历 output 目录下的 *_ocr_results.csv 文件，提取原文件名。
3. 读取 CSV 中 Matched_Text 列的首行内容，利用正则匹配截取“变更编号”作为新文件名。
4. 在 src 目录下定位对应的 PDF 扫描文件并执行重命名操作。
5. 详细记录处理日志与异常信息。
"""

import os
import argparse
import yaml
import logging
import concurrent.futures
from logging_config import setup_logger
from pdf_ocr_extractor import PdfOcrExtractor


def load_config(config_path="./config_B24.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        conf = yaml.safe_load(f)
    return conf


def process_pdf_wrapper(args):
    """
    并行处理的包装函数。
    """
    pdf_path, config = args
    try:
        extractor = PdfOcrExtractor(config)
        # 修正：extract_matches_from_pdf 现在返回 (matches, error)
        # 我们需要确保 pdf_ocr_extractor.py 也是这样实现的
        result = extractor.extract_matches_from_pdf(pdf_path)

        # 健壮性检查：根据返回值类型进行适配
        if isinstance(result, tuple) and len(result) == 2:
            return result  # 已经是 (matches, error)
        else:
            # 假设只返回了 matches 列表（旧逻辑），则 error 为 None
            return result, None

    except Exception as e:
        return None, str(e)


def main():
    parser = argparse.ArgumentParser(description="PDF OCR Extractor Runner")
    parser.add_argument(
        "--config", type=str, default="./config_B24.yaml", help="配置文件路径"
    )
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"无法加载配置文件: {e}")
        return

    log_file = config.get("log_file", "./logs/pdf_ocr_extractor.log")
    logger = setup_logger(log_level=logging.DEBUG, log_file=log_file)

    pdf_directory = config.get("pdf_directory")
    if not pdf_directory or not os.path.exists(pdf_directory):
        logger.error("PDF 目录不存在或未指定: %s", pdf_directory)
        return

    pdf_files = [
        os.path.join(pdf_directory, f)
        for f in os.listdir(pdf_directory)
        if f.lower().endswith(".pdf")
    ]
    total_files = len(pdf_files)

    if total_files == 0:
        logger.info("未找到 PDF 文件。")
        return

    logger.info("准备处理 %d 个 PDF 文件...", total_files)
    count = 0

    with concurrent.futures.ProcessPoolExecutor() as executor:
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
                    count += 1
                    status = f"找到 {len(matches)} 条匹配" if matches else "未找到匹配"
                    logger.info(
                        "已完成 (%d/%d): %s [%s]", count, total_files, file_name, status
                    )
            except Exception as exc:
                logger.error("处理文件 %s 时发生未捕获异常: %s", file_name, exc)

    logger.info(
        "所有任务完成，共处理了 %d 个 PDF 文件。结果保存在 %s",
        count,
        config.get("output_directory"),
    )


if __name__ == "__main__":
    main()
