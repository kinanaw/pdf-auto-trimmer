import streamlit as st
import fitz
from PIL import Image
import io
import numpy as np

Image.MAX_IMAGE_PIXELS = None

st.set_page_config(page_title="✂️ Kienan PDF Trimmer", layout="centered")
st.title("✂️ Kienan PDF Trimmer")
st.markdown("❤️ מוצר זה פותח על ידי כינאן עוידאת, לשימושכם באהבה.")
st.markdown("---")

uploaded_file = st.file_uploader("העלה קובץ PDF", type=["pdf"])
extra_margin_mm = st.slider('שוליים נוספים (מ"מ)', min_value=0, max_value=20, value=3)
sensitivity = st.slider("רגישות — סף לבן", min_value=150, max_value=254, value=200)


def mm_to_points(mm):
    return mm * 72.0 / 25.4


def get_content_bbox_pixels(page, white_threshold):
    """Render page to pixels and find bounding box of non-white content."""
    scale = 150 / 72
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

    # Convert to grayscale
    if pix.n == 3:
        gray = arr.mean(axis=2)
    else:
        gray = arr[:, :, 0].astype(float)

    mask = gray < white_threshold
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)

    if not rows.any() or not cols.any():
        return None

    top    = int(np.argmax(rows))
    bottom = int(len(rows) - np.argmax(rows[::-1]))
    left   = int(np.argmax(cols))
    right  = int(len(cols) - np.argmax(cols[::-1]))

    # IMPORTANT: use mediabox origin, not page.rect
    mb = page.mediabox
    return fitz.Rect(
        mb.x0 + left   / scale,
        mb.y0 + top    / scale,
        mb.x0 + right  / scale,
        mb.y0 + bottom / scale,
    )


def trim_pdf(input_bytes, extra_margin_mm, sensitivity):
    extra_pts = mm_to_points(extra_margin_mm)
    trimmed = 0
    fallback = 0

    doc = fitz.open(stream=input_bytes, filetype="pdf")
    num_pages = doc.page_count

    for i in range(num_pages):
        page = doc[i]
        mb = fitz.Rect(page.mediabox)

        content_rect = get_content_bbox_pixels(page, sensitivity)

        if content_rect is None or content_rect.is_empty:
            fallback += 1
            continue

        # Add margin and clamp within mediabox
        crop = fitz.Rect(
            max(content_rect.x0 - extra_pts, mb.x0),
            max(content_rect.y0 - extra_pts, mb.y0),
            min(content_rect.x1 + extra_pts, mb.x1),
            min(content_rect.y1 + extra_pts, mb.y1),
        )

        if crop.width > 1 and crop.height > 1:
            page.set_cropbox(crop)
            trimmed += 1

    if fallback > 0:
        st.warning(f"⚠️ {fallback} עמודים לא זוהו — נשמרו ללא גיזום.")

    out = io.Byt
