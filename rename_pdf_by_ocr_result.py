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
import re
import csv
import yaml
import logging
import argparse
from pathlib import Path
from logging_config import setup_logger


def load_config(config_path):
    """加载 YAML 配置文件"""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def rename_pdfs(config_path):
    """
    根据 OCR 结果 CSV 文件重命名 PDF。
    """
    config = load_config(config_path)

    # 从配置中读取路径和参数
    pdf_dir = Path(config.get("pdf_directory", "./src"))
    output_dir = Path(config.get("output_directory", "./output"))
    log_file = config.get("log_file", "./logs/rename_process.log")
    patterns = config.get("content_regex", [])

    # 初始化日志记录器
    logger = setup_logger(log_level=logging.INFO, log_file=log_file)
    logger.info("=" * 50)
    logger.info(f"开始执行 PDF 重命名任务，配置文件: {config_path}")
    logger.info(f"PDF 目录: {pdf_dir}")
    logger.info(f"CSV 目录: {output_dir}")

    if not output_dir.exists():
        logger.error(f"输出目录不存在: {output_dir}")
        return

    # 遍历输出目录下的 CSV 文件
    csv_files = list(output_dir.glob("*_ocr_results.csv"))
    if not csv_files:
        logger.warning(f"在 {output_dir} 下未找到匹配 *_ocr_results.csv 的文件。")
        return

    logger.info(f"找到 {len(csv_files)} 个 OCR 结果文件。")

    success_count = 0
    fail_count = 0
    skip_count = 0

    for csv_path in csv_files:
        try:
            # 获取原文件名 (old_pdf_name)
            old_pdf_name = csv_path.name.replace("_ocr_results.csv", "")
            old_pdf_file = pdf_dir / f"{old_pdf_name}.pdf"

            if not old_pdf_file.exists():
                logger.warning(f"未找到对应的 PDF 文件: {old_pdf_file}，跳过处理。")
                skip_count += 1
                continue

            # 读取 CSV 获取匹配内容
            new_pdf_name = None
            matched_text = ""

            # 使用 utf-8-sig 处理可能存在的 BOM
            with open(csv_path, mode="r", encoding="utf-8-sig") as csvfile:
                reader = csv.DictReader(csvfile)
                first_row = next(reader, None)

                if first_row and "Matched_Text" in first_row:
                    matched_text = first_row["Matched_Text"].strip()

                    # 按照配置文件中的正则表达式进行匹配
                    if isinstance(patterns, str):
                        patterns = [patterns]

                    for pattern in patterns:
                        match = re.search(pattern, matched_text)
                        if match:
                            # 提取匹配的内容作为新文件名
                            new_pdf_name = match.group(0)
                            break

            if new_pdf_name:
                # 清洗文件名，移除非法字符
                new_pdf_name = re.sub(r'[\\/*?:"<>|]', "_", new_pdf_name)
                new_pdf_file = pdf_dir / f"{new_pdf_name}.pdf"

                # 如果目标文件名已存在且不是当前处理的文件（避免大小写或相同命名的冲突）
                if (
                    new_pdf_file.exists()
                    and new_pdf_file.resolve() != old_pdf_file.resolve()
                ):
                    logger.error(
                        f"目标文件名已存在: {new_pdf_file}，无法重命名 {old_pdf_name}"
                    )
                    fail_count += 1
                else:
                    os.rename(old_pdf_file, new_pdf_file)
                    logger.info(f"成功重命名: {old_pdf_name}.pdf -> {new_pdf_name}.pdf")
                    success_count += 1
            else:
                logger.warning(
                    f"文件 {csv_path.name} 的内容中未找到符合正则表达式的匹配项。原内容: {matched_text}"
                )
                skip_count += 1

        except Exception as e:
            logger.error(
                f"处理文件 {csv_path.name} 时发生异常: {str(e)}", exc_info=True
            )
            fail_count += 1

    logger.info(
        f"任务完成! 成功: {success_count}, 失败: {fail_count}, 跳过: {skip_count}"
    )
    logger.info("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="根据 OCR 结果重命名 PDF 文件")
    parser.add_argument(
        "--config", type=str, default="config_B24.yaml", help="配置文件路径 (YAML格式)"
    )
    args = parser.parse_args()

    # 确保配置文件绝对路径
    config_path = os.path.abspath(args.config)

    if not os.path.exists(config_path):
        print(f"配置文件未找到: {config_path}")
    else:
        rename_pdfs(config_path)
