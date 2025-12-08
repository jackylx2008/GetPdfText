"""pdf_ocr_extractor

定义 PdfOcrExtractor 类，用于将 PDF 转换为图像并使用 Tesseract OCR 识别文本。
"""

import os
import logging
import csv
import re
from pdf2image import convert_from_path
import pytesseract


# 设置 Tesseract 可执行路径（按需修改）
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
)


class PdfOcrExtractor:
    """PDF OCR 提取器类"""

    def __init__(self, config, logger=None):
        """
        初始化提取器。

        :param config: 配置字典
        :param logger: 日志记录器实例
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

        self.dpi = config.get("dpi", 300)
        self.ocr_language = config.get("ocr_language", "chi_sim")
        self.output_directory = config.get("output_directory", "./output")
        self.matches_csv = config.get("matches_csv")
        self.marker = config.get("marker", "设计变更通知单")
        self.auto_rotate = config.get("auto_rotate", False)  # 是否自动修正图像方向

        # 确保输出目录存在
        os.makedirs(self.output_directory, exist_ok=True)

        # 屏蔽 pytesseract 的 DEBUG 日志（包含临时文件路径等信息）
        logging.getLogger("pytesseract").setLevel(logging.INFO)

    def _pdf_to_images(self, pdf_path, start_page=1):
        """将 PDF 文件转换为 PIL Image 列表（每页一张）。"""
        try:
            self.logger.info(
                "开始将PDF文件 %s 转换为图像(从第%d页开始)...", pdf_path, start_page
            )
            images = convert_from_path(pdf_path, dpi=self.dpi, first_page=start_page)
            self.logger.info("PDF文件 %s 成功转换为 %d 张图像。", pdf_path, len(images))
            return images
        except Exception as exc:
            self.logger.exception("转换PDF为图像时发生错误: %s", exc)
            raise

    def _correct_orientation(self, image):
        """检测并修正图像方向。"""
        try:
            # 使用 Tesseract 的 OSD 模式检测方向
            # psm 0: Orientation and script detection (OSD) only.
            osd = pytesseract.image_to_osd(
                image, config="--psm 0 -c min_characters_to_try=5"
            )

            rotate_angle = 0
            # 解析 OSD 输出，查找 "Rotate: 90" 这样的行
            search = re.search(r"Rotate: (\d+)", osd)
            if search:
                rotate_angle = int(search.group(1))

            if rotate_angle != 0:
                self.logger.info("检测到图像需要旋转 %d 度", rotate_angle)
                # PIL rotate 是逆时针，Rotate: 90 意味着需要顺时针旋转 90 度
                # 所以使用 -rotate_angle
                # expand=True 确保旋转后图像不被裁剪
                image = image.rotate(-rotate_angle, expand=True)

        except pytesseract.TesseractError as e:
            # OSD 检测失败（例如文本太少），忽略错误，使用原图
            self.logger.debug("方向检测失败 (可能是文本太少): %s", e)
        except Exception as e:
            self.logger.warning("图像方向修正时发生未知错误: %s", e)

        return image

    def _ocr_images(self, images):
        """对每页图像执行 OCR，返回每页文本的列表。"""
        text_per_page = []
        try:
            self.logger.info("开始对每一页进行OCR识别...")
            for i, image in enumerate(images):
                # 如果开启了自动旋转，则先修正方向
                if self.auto_rotate:
                    image = self._correct_orientation(image)

                text = pytesseract.image_to_string(image, lang=self.ocr_language)
                text_per_page.append(text)
                self.logger.info("第 %d 页OCR识别完成。", i + 1)
            return text_per_page
        except Exception as exc:
            self.logger.exception("OCR识别过程中发生错误: %s", exc)
            raise

    def _extract_marker_line(self, text_per_page, marker_string, start_page=1):
        """在 OCR 结果中查找包含标记字符串的行并返回匹配列表。

        返回的每项为 (page_number, match_text)
        """
        matches = []
        for i, page_text in enumerate(text_per_page):
            if not page_text:
                continue
            for line in page_text.splitlines():
                if marker_string in line:
                    match_text = line.strip()
                    current_page = start_page + i
                    self.logger.info(
                        "第 %d 页 找到 '%s': %s",
                        current_page,
                        marker_string,
                        match_text,
                    )
                    matches.append((current_page, match_text))
        if not matches:
            self.logger.debug("未找到 '%s'。", marker_string)
        return matches

    def _append_matches_to_csv(self, matches, csv_path=None):
        """将匹配结果追加到 CSV 文件，若文件不存在则写入表头。"""
        # 确定 CSV 路径
        if not csv_path:
            if self.matches_csv:
                csv_path = self.matches_csv
            else:
                csv_path = os.path.join(self.output_directory, "matches.csv")

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
            self.logger.info("已将 %d 条匹配写入 CSV: %s", len(matches), csv_path)
        except (OSError, PermissionError, csv.Error) as exc:
            self.logger.exception(
                "将匹配写入 CSV 时发生错误: %s; 异常: %s", csv_path, exc
            )

    def extract_regex_matches(self, pdf_path, regex_pattern, start_page=1):
        """
        处理单个 PDF：转换图像并执行 OCR，然后使用正则提取匹配项。

        :param pdf_path: PDF 文件路径
        :param regex_pattern: 正则表达式模式字符串
        :param start_page: 起始页码，默认为 1
        :return: 匹配到的字符串列表（去重）
        """
        self.logger.info("开始处理PDF文件 (正则匹配): %s", pdf_path)
        matches = set()

        try:
            images = self._pdf_to_images(pdf_path, start_page=start_page)
            text_per_page = self._ocr_images(images)

            for i, page_text in enumerate(text_per_page):
                if not page_text:
                    continue

                # 在当前页文本中查找所有匹配项
                # 使用 finditer 以便获取完整的匹配字符串（group(0)），无论正则是否有分组
                for match in re.finditer(regex_pattern, page_text):
                    full_match = match.group(0).strip()
                    if full_match:
                        matches.add(full_match)
                        self.logger.info("第 %d 页找到匹配: %s", i + 1, full_match)

            self.logger.info(
                "PDF 文件 %s 处理完成，找到 %d 个唯一匹配。", pdf_path, len(matches)
            )
            return list(matches)

        except Exception as e:
            self.logger.error("处理 PDF %s 失败: %s", pdf_path, e)
            raise

    def extract_matches_from_pdf(self, pdf_path):
        """处理单个 PDF：转换图像并执行 OCR，然后提取匹配并写入 CSV。"""
        self.logger.info("开始处理PDF文件: %s", pdf_path)

        try:
            # 复用 extract_content 的逻辑，但我们需要页码信息来写入 CSV
            # 所以这里手动调用底层方法
            images = self._pdf_to_images(pdf_path, start_page=1)
            text_per_page = self._ocr_images(images)
            # extract_marker_line 返回 (page, text)
            matches_with_page = self._extract_marker_line(
                text_per_page, self.marker, start_page=1
            )

            # 转换为 append_matches_to_csv 需要的格式 (pdf_path, page, text)
            csv_matches = [(pdf_path, page, text) for page, text in matches_with_page]

            if csv_matches:
                # 输出为 pdf文件名+matches.csv
                base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                individual_csv_path = os.path.join(
                    self.output_directory, f"{base_name}_matches.csv"
                )
                self._append_matches_to_csv(csv_matches, individual_csv_path)

            self.logger.info("PDF 文件 %s 处理完成。", pdf_path)
            return csv_matches
        except Exception as e:
            self.logger.error("处理 PDF %s 失败: %s", pdf_path, e)
            raise
