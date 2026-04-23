from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from config import OCR, PATHS


@lru_cache(maxsize=1)
def _reader():
    import easyocr
    return easyocr.Reader(OCR["languages"], gpu=False, verbose=False)


def _prepare(path):
    img = Image.open(path).convert("RGB")
    max_dim = OCR["max_image_dim"]
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
    return np.array(img)


def ocr_images(rel_paths):
    if not rel_paths:
        return OCR["no_text_message"]
    reader = _reader()
    lines = []
    seen = set()
    base = Path(PATHS["images"])
    for rel in rel_paths:
        full = base / rel
        try:
            arr = _prepare(full)
            results = reader.readtext(arr, detail=0, paragraph=False)
        except Exception as e:
            print(f"  OCR failed for {rel}: {e}")
            continue
        for text in results:
            cleaned = (text or "").strip()
            if not cleaned or cleaned.lower() in seen:
                continue
            seen.add(cleaned.lower())
            lines.append(cleaned)
    combined = "\n".join(lines).strip()
    if len(combined) < OCR["min_chars_for_valid"]:
        return OCR["no_text_message"]
    return combined
