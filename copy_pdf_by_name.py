"""
根据文件名匹配规则复制 PDF 文件。

此脚本读取配置文件中指定的目标目录，查找所有 PDF 文件，
如果文件名包含指定文本文件中的任意字符串，则将其复制到输出目录。
"""

import os
import shutil
import yaml
from logging_config import setup_logger


def load_config(config_path="config.yaml"):
    """加载配置文件"""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_match_strings(file_path):
    """从文本文件中读取匹配字符串列表"""
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def find_and_copy_pdfs(target_dirs, match_strings, output_dir, logger):
    """查找并复制匹配的PDF文件"""
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    copied_files = 0
    # 用于跟踪每个匹配字符串是否找到对应的PDF
    unmatched_strings = set(match_strings)

    for target_dir in target_dirs:
        logger.info("正在处理目录：%s", target_dir)

        # 确保目录存在
        if not os.path.exists(target_dir):
            logger.warning("目录不存在：%s", target_dir)
            continue

        # 遍历目录中的所有PDF文件
        for root, _, files in os.walk(target_dir):
            for file in files:
                if not file.lower().endswith(".pdf"):
                    continue

                # 检查文件名是否包含任意匹配字符串
                for match_str in match_strings:
                    if match_str in file:
                        src_path = os.path.join(root, file)
                        dst_path = os.path.join(output_dir, file)

                        try:
                            # 如果目标文件已存在，添加序号
                            if os.path.exists(dst_path):
                                base, ext = os.path.splitext(file)
                                counter = 1
                                while os.path.exists(dst_path):
                                    new_name = f"{base}_{counter}{ext}"
                                    # Split long line into multiple lines
                                    dst_path = os.path.join(
                                        output_dir,
                                        new_name,
                                    )
                                    counter += 1

                            # 复制文件
                            shutil.copy2(src_path, dst_path)
                            dst_name = os.path.basename(dst_path)
                            logger.info("已复制文件：%s -> %s", file, dst_name)
                            copied_files += 1
                            # 从未匹配集合中移除已匹配的字符串
                            unmatched_strings.discard(match_str)
                        except (OSError, IOError) as e:
                            logger.error("复制文件时出错 %s: %s", file, str(e))

                        break  # 找到匹配后就跳出内层循环

    return copied_files, unmatched_strings


def main():
    # 设置日志记录
    logger = setup_logger(log_file="./logs/copy_pdf_by_name.log")

    try:
        # 加载配置
        config = load_config()

        # 加载匹配字符串
        match_strings = load_match_strings(config["file_txt"])
        logger.info("已加载 %d 个匹配字符串", len(match_strings))

        # 开始处理文件
        copied_count, unmatched = find_and_copy_pdfs(
            config["target_directories"],
            match_strings,
            config["output_directory"],
            logger,
        )

        logger.info("处理完成！共复制了 %d 个文件", copied_count)

        # 显示未匹配的字符串
        if unmatched:
            logger.warning("以下字符串未找到匹配的PDF文件：")
            for s in sorted(unmatched):
                logger.warning("  - %s", s)
        else:
            logger.info("所有字符串都已找到匹配的PDF文件")

    except (OSError, IOError) as e:
        logger.error("文件操作出错: %s", str(e))
        raise
    except yaml.YAMLError as e:
        logger.error("YAML配置文件格式错误: %s", str(e))
        raise
    except Exception as e:
        logger.error("未预期的错误: %s", str(e))
        raise


if __name__ == "__main__":
    main()
