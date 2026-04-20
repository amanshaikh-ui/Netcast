"""Optional OCR on image bytes (e.g. thumbnails). Requires pillow + pytesseract — install separately."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def ocr_image_bytes(data: bytes) -> str:
    try:
        from PIL import Image
        import io
        import pytesseract
    except ImportError:
        return ""
    try:
        img = Image.open(io.BytesIO(data))
        txt = pytesseract.image_to_string(img) or ""
        return " ".join(txt.split())[:2000]
    except Exception as e:
        logger.debug("OCR skipped: %s", e)
        return ""
