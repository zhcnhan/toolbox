"""文档格式转换。

支持的转换路径:
    PDF  → DOCX  (pdf2docx)
    PDF  → TXT   (PyPDF2)
    DOCX → PDF   (LibreOffice 或 reportlab 回退)
    DOCX → TXT   (python-docx)
    DOCX → HTML  (python-docx)
    DOC  → DOCX  (LibreOffice)
    TXT  → PDF   (reportlab)
    TXT  → DOCX  (python-docx)
    TXT  → MD    (直接复制)
    TXT  → HTML  (简单包装)
    MD   → PDF   (markdown + weasyprint)
    MD   → HTML  (markdown)
    HTML → PDF   (weasyprint)
    HTML → TXT   (beautifulsoup4)
    EPUB → TXT   (ebooklib + beautifulsoup4)
    RTF  → TXT   (stripper)
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from typing import Callable

logger = logging.getLogger(__name__)


def _find_executable(*names: str) -> str | None:
    """在 PATH 和常见 Windows 安装路径中查找可执行文件。"""
    for name in names:
        path = shutil.which(name)
        if path:
            return path

    # Windows 常见安装路径
    win_paths = {
        "soffice": [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ],
        "libreoffice": [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ],
    }

    for name in names:
        for p in win_paths.get(name, []):
            if os.path.exists(p):
                return p

    return None


def convert_document(
    input_path: str,
    output_path: str,
    src_fmt: str,
    dst_fmt: str,
    progress_callback: Callable[[float], None] | None = None,
) -> None:
    """文档格式转换入口。"""
    key = (src_fmt, dst_fmt)

    handlers: dict[tuple[str, str], Callable] = {
        ("pdf", "docx"): _pdf_to_docx,
        ("pdf", "txt"): _pdf_to_txt,
        ("pdf", "png"): _pdf_to_image,
        ("pdf", "jpg"): _pdf_to_image,
        ("docx", "pdf"): _docx_to_pdf,
        ("docx", "txt"): _docx_to_txt,
        ("docx", "html"): _docx_to_html,
        ("doc", "docx"): _doc_to_docx,
        ("txt", "pdf"): _txt_to_pdf,
        ("txt", "docx"): _txt_to_docx,
        ("txt", "md"): _txt_to_md,
        ("txt", "html"): _txt_to_html,
        ("md", "pdf"): _md_to_pdf,
        ("md", "html"): _md_to_html,
        ("html", "pdf"): _html_to_pdf,
        ("html", "txt"): _html_to_txt,
        ("epub", "txt"): _epub_to_txt,
        ("rtf", "txt"): _rtf_to_txt,
    }

    handler = handlers.get(key)
    if handler is None:
        raise ValueError(f"不支持的文档转换: {src_fmt} -> {dst_fmt}")

    handler(input_path, output_path)
    if progress_callback:
        progress_callback(1.0)


# ============================================================================
#  PDF → DOCX
# ============================================================================
def _pdf_to_docx(input_path: str, output_path: str) -> None:
    from pdf2docx import Converter
    cv = Converter(input_path)
    cv.convert(output_path)
    cv.close()
    logger.info("PDF -> DOCX: %s", output_path)


# ============================================================================
#  PDF → TXT
# ============================================================================
def _pdf_to_txt(input_path: str, output_path: str) -> None:
    from PyPDF2 import PdfReader
    reader = PdfReader(input_path)
    lines: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            lines.append(text)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(lines))
    logger.info("PDF -> TXT: %s", output_path)


# ============================================================================
#  PDF → 图片
# ============================================================================
def _pdf_to_image(input_path: str, output_path: str) -> None:
    from PyPDF2 import PdfReader
    from PIL import Image, ImageDraw, ImageFont

    reader = PdfReader(input_path)
    images: list[Image.Image] = []

    for page in reader.pages:
        text = page.extract_text() or ""
        img = Image.new("RGB", (800, 1100), "white")
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except Exception:
            font = ImageFont.load_default()

        y = 50
        for line in text.split("\n"):
            if y > 1050:
                break
            draw.text((50, y), line, fill="black", font=font)
            y += 20
        images.append(img)

    if len(images) == 1:
        images[0].save(output_path)
    else:
        images[0].save(output_path, save_all=True, append_images=images[1:])
    logger.info("PDF -> Image: %s", output_path)


# ============================================================================
#  DOCX → PDF
# ============================================================================
def _docx_to_pdf(input_path: str, output_path: str) -> None:
    """DOCX → PDF：优先尝试 LibreOffice headless，否则用 reportlab。"""
    if _try_libreoffice(input_path, output_path, "pdf"):
        return

    from docx import Document
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    doc = Document(input_path)
    pdf_doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story: list = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            story.append(Spacer(1, 12))
            continue
        try:
            story.append(Paragraph(text, styles["Normal"]))
        except Exception:
            safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(safe, styles["Normal"]))

    pdf_doc.build(story)
    logger.info("DOCX -> PDF (reportlab): %s", output_path)


# ============================================================================
#  DOCX → TXT
# ============================================================================
def _docx_to_txt(input_path: str, output_path: str) -> None:
    from docx import Document
    doc = Document(input_path)
    lines: list[str] = []
    for para in doc.paragraphs:
        lines.append(para.text)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info("DOCX -> TXT: %s", output_path)


# ============================================================================
#  DOCX → HTML
# ============================================================================
def _docx_to_html(input_path: str, output_path: str) -> None:
    from docx import Document
    doc = Document(input_path)
    parts: list[str] = ["<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>"]
    for para in doc.paragraphs:
        text = para.text
        style = para.style.name if para.style else "Normal"
        tag = "h1" if "Heading 1" in style else ("h2" if "Heading 2" in style else "p")
        safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        parts.append(f"<{tag}>{safe}</{tag}>")
    parts.append("</body></html>")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    logger.info("DOCX -> HTML: %s", output_path)


# ============================================================================
#  DOC → DOCX
# ============================================================================
def _doc_to_docx(input_path: str, output_path: str) -> None:
    """DOC → DOCX：通过 LibreOffice 转换。"""
    if _try_libreoffice(input_path, output_path, "docx"):
        return
    raise RuntimeError("DOC -> DOCX 需要安装 LibreOffice (soffice)。")


# ============================================================================
#  TXT → PDF
# ============================================================================
def _txt_to_pdf(input_path: str, output_path: str) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    with open(input_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    pdf_doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story: list = []

    for line in content.split("\n"):
        if not line.strip():
            story.append(Spacer(1, 12))
        else:
            safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(safe, styles["Normal"]))

    pdf_doc.build(story)
    logger.info("TXT -> PDF: %s", output_path)


# ============================================================================
#  TXT → DOCX
# ============================================================================
def _txt_to_docx(input_path: str, output_path: str) -> None:
    from docx import Document
    from docx.shared import Pt

    with open(input_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    doc = Document()
    style = doc.styles["Normal"]
    style.font.size = Pt(11)

    for line in content.split("\n"):
        if not line.strip():
            doc.add_paragraph("")
        else:
            doc.add_paragraph(line)

    doc.save(output_path)
    logger.info("TXT -> DOCX: %s", output_path)


# ============================================================================
#  TXT → MD (直接复制内容)
# ============================================================================
def _txt_to_md(input_path: str, output_path: str) -> None:
    import shutil as su
    su.copy2(input_path, output_path)
    logger.info("TXT -> MD: %s", output_path)


# ============================================================================
#  TXT → HTML (简单包装)
# ============================================================================
def _txt_to_html(input_path: str, output_path: str) -> None:
    with open(input_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # 转义 HTML 特殊字符
    safe = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # 换行转 <br>
    html_body = safe.replace("\n", "<br>\n")

    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>Converted Text</title></head>
<body>
<pre style="white-space: pre-wrap; word-wrap: break-word;">{safe}</pre>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    logger.info("TXT -> HTML: %s", output_path)


# ============================================================================
#  MD → PDF
# ============================================================================
def _md_to_pdf(input_path: str, output_path: str) -> None:
    try:
        import markdown
        from weasyprint import HTML

        with open(input_path, "r", encoding="utf-8") as f:
            md_text = f.read()

        html_body = markdown.markdown(md_text, extensions=["extra", "codehilite", "tables"])
        html_doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; color: #333; }}
code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 4px; }}
pre {{ background: #f4f4f4; padding: 16px; border-radius: 8px; overflow-x: auto; }}
h1, h2, h3 {{ color: #1a1a1a; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px; }}
th {{ background: #f5f5f5; }}
</style></head><body>{html_body}</body></html>"""

        HTML(string=html_doc).write_pdf(output_path)
        logger.info("MD -> PDF (weasyprint): %s", output_path)
    except ImportError as e:
        raise RuntimeError(f"MD -> PDF 需要安装 markdown 和 weasyprint: {e}")


# ============================================================================
#  MD → HTML
# ============================================================================
def _md_to_html(input_path: str, output_path: str) -> None:
    import markdown

    with open(input_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    html_body = markdown.markdown(md_text, extensions=["extra", "codehilite", "tables"])
    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 860px; margin: 40px auto; padding: 20px; line-height: 1.7; color: #333; }}
code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }}
pre {{ background: #1e1e2e; color: #cdd6f4; padding: 20px; border-radius: 10px; overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
th {{ background: #f5f5f5; }}
</style></head><body>{html_body}</body></html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    logger.info("MD -> HTML: %s", output_path)


# ============================================================================
#  HTML → PDF
# ============================================================================
def _html_to_pdf(input_path: str, output_path: str) -> None:
    from weasyprint import HTML
    HTML(filename=input_path).write_pdf(output_path)
    logger.info("HTML -> PDF: %s", output_path)


# ============================================================================
#  HTML → TXT
# ============================================================================
def _html_to_txt(input_path: str, output_path: str) -> None:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError("HTML -> TXT 需要安装 beautifulsoup4")

    with open(input_path, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    # 移除 script 和 style 标签
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # 清理多余空行
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    logger.info("HTML -> TXT: %s", output_path)


# ============================================================================
#  EPUB → TXT
# ============================================================================
def _epub_to_txt(input_path: str, output_path: str) -> None:
    try:
        from ebooklib import epub
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError("EPUB -> TXT 需要安装 ebooklib 和 beautifulsoup4")

    book = epub.read_epub(input_path)
    lines: list[str] = []
    for item in book.get_items_of_type(9):  # ITEM_DOCUMENT
        soup = BeautifulSoup(item.get_body_content(), "html.parser")
        lines.append(soup.get_text())
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(lines))
    logger.info("EPUB -> TXT: %s", output_path)


# ============================================================================
#  RTF → TXT
# ============================================================================
def _rtf_to_txt(input_path: str, output_path: str) -> None:
    """RTF → TXT：优先用 striprtf，回退到正则。"""
    try:
        from striprtf.striprtf import rtf_to_text
        with open(input_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        text = rtf_to_text(content)
    except ImportError:
        import re
        with open(input_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        text = re.sub(r"[\\{].*?[\\}]", " ", content)
        text = re.sub(r"\s+", " ", text).strip()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    logger.info("RTF -> TXT: %s", output_path)


# ============================================================================
#  LibreOffice headless 回退
# ============================================================================
def _try_libreoffice(input_path: str, output_path: str, target_fmt: str) -> bool:
    """尝试用 LibreOffice headless 模式转换文档。"""
    lo = _find_executable("soffice", "libreoffice")
    if lo is None:
        logger.warning("未找到 LibreOffice (soffice)，无法进行 %s 转换", target_fmt)
        return False

    out_dir = os.path.dirname(output_path) or "."
    try:
        subprocess.run(
            [lo, "--headless", "--convert-to", target_fmt,
             "--outdir", out_dir, input_path],
            capture_output=True, text=True, timeout=120,
        )
        # LibreOffice 会在 out_dir 下以原名 + .target_fmt 输出
        lo_output = os.path.join(out_dir,
            os.path.splitext(os.path.basename(input_path))[0] + "." + target_fmt)
        if os.path.exists(lo_output):
            if lo_output != output_path:
                os.replace(lo_output, output_path)
            logger.info("%s -> %s (LibreOffice)", input_path, target_fmt.upper())
            return True
        return False
    except Exception as exc:
        logger.warning("LibreOffice 转换失败: %s", exc)
        return False
