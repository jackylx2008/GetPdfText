"""Logging configuration helper.

This module provides a small helper `setup_logger` that configures a
root logger with a console handler and a file handler. It is intended for
simple scripts and small projects that need consistent logging output.

Usage:
    from logging_config import setup_logger
    logger = setup_logger(log_level=logging.INFO, log_file='./logs/app.log')
    logger.info('Started')

The `setup_logger` function returns the configured root logger object.
"""

import logging
import os
import sys

# 动态添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def setup_logger(log_level=logging.DEBUG, log_file="./logs/app.log"):
    """
    设置日志记录器。

    :param log_level: 日志级别，默认为 DEBUG。
    :param log_file: 日志文件路径，默认为 ./logs/app.log。
    :return: 配置好的日志记录器。
    """
    # 创建日志文件夹
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # 配置日志格式
    log_format = "%(asctime)s - %(levelname)s - %(module)s - %(message)s"

    # 设置日志级别
    log = logging.getLogger()
    log.setLevel(log_level)

    # 避免重复添加处理器
    if not log.handlers:
        # 控制台日志处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format))

        # 文件日志处理器
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))

        # 添加处理器
        log.addHandler(console_handler)
        log.addHandler(file_handler)

    return log


# 单独运行时的测试代码
if __name__ == "__main__":
    # 示例日志文件路径（常量风格）
    LOG_FILE_PATH = "./logs/test_logger.log"

    # 初始化日志记录器
    logger = setup_logger(log_level=logging.INFO, log_file=LOG_FILE_PATH)

    # 测试日志输出
    logger.debug("This is a DEBUG message.")
    logger.info("This is an INFO message.")
    logger.warning("This is a WARNING message.")
    logger.error("This is an ERROR message.")
    logger.critical("This is a CRITICAL message.")
