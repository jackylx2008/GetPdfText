# GetPdfText

这是一个用于从 PDF 文件中提取特定文本（如“设计变更通知单”）并导出到 CSV 的 Python 工具集。

## 功能特性

* **PDF OCR 提取**: 将 PDF 转换为图像，使用 Tesseract OCR 识别文本，并提取包含特定标记（默认为“设计变更通知单”）的行。
* **结果导出**: 将匹配结果保存为 CSV 文件，支持单文件结果和合并结果。
* **文件筛选与复制**: 根据文本文件中的关键词列表，从指定目录中查找并复制匹配的 PDF 文件。

## 项目结构

* `pdf_ocr_extractor.py`: 包含核心类 `PdfOcrExtractor`，封装了 PDF 转图、OCR 识别和文本提取逻辑。
* `run_ocr.py`: 主运行脚本，加载配置并调用 `PdfOcrExtractor` 批量处理 PDF 文件。
* `copy_pdf_by_name.py`: 工具脚本，根据 `file.txt` 中的文件名列表，从 `target_directories` 中查找并复制 PDF 文件。
* `logging_config.py`: 日志配置模块。
* `config.yaml`: 项目配置文件。

## 安装依赖

需要安装 Tesseract-OCR 引擎，并配置 Python 依赖：

```bash
pip install -r requirements.txt
```

确保 `config.yaml` 或代码中正确配置了 Tesseract 的路径。

## 使用方法

### 1. OCR 提取文本

修改 `config.yaml` 配置输入输出目录，然后运行：

```bash
python run_ocr.py
```

### 2. 根据名称复制 PDF

在 `config.yaml` 中配置 `target_directories` 和 `file_txt` 路径，然后运行：

```bash
python copy_pdf_by_name.py
```

## 配置说明 (config.yaml)

```yaml
pdf_directory: ./src           # OCR 输入目录
output_directory: ./output     # 结果输出目录
ocr_language: chi_sim          # OCR 语言
marker: "设计变更通知单"        # 需要提取的行包含的关键词
target_directories:            # copy_pdf_by_name.py 搜索的源目录列表
  - ./src/folder1
file_txt: ./output/file.txt    # 包含要查找的文件名关键词的文本文件
```
