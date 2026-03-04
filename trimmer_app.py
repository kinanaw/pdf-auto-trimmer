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
    # Render via the page's own coordinate system (clip=page.rect)
    scale = 150 / 72
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False, clip=page.rect)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    gray = arr.mean(axis=2)  # average RGB → grayscale

    mask = gray < white_threshold
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)

    if not rows.any() or not cols.any():
        return None

    top    = int(np.argmax(rows))
    bottom = int(len(rows) - np.argmax(rows[::-1]))
    left   = int(np.argmax(cols))
    right  = int(len(cols) - np.argmax(cols[::-1]))

    # Convert pixels → page points (page.rect already normalized)
    pr = page.rect
    return fitz.Rect(
        pr.x0 + left   / scale,
        pr.y0 + top    / scale,
        pr.x0 + right  / scale,
        pr.y0 + bottom / scale,
    )


def trim_pdf(input_bytes, extra_margin_mm, sensitivity):
    extra_pts = mm_to_points(extra_margin_mm)

    src = fitz.open(stream=input_bytes, filetype="pdf")
    out_doc = fitz.open()
    trimmed = 0

    for i in range(src.page_count):
        src_page = src[i]
        # Use page.rect (already accounts for rotation/offsets)
        pr = fitz.Rect(src_page.rect)

        content_rect = get_content_bbox_pixels(src_page, sensitivity)

        # Fallback to full page if detection fails
        if content_rect is None or content_rect.is_empty or not content_rect.is_valid:
            content_rect = pr

        # Build crop rect with margin, clamped to page bounds
        crop = fitz.Rect(
            max(content_rect.x0 - extra_pts, pr.x0),
            max(content_rect.y0 - extra_pts, pr.y0),
            min(content_rect.x1 + extra_pts, pr.x1),
            min(content_rect.y1 + extra_pts, pr.y1),
        )

        # Safety check
        w = crop.x1 - crop.x0
        h = crop.y1 - crop.y0
        if w <= 0 or h <= 0:
            crop = pr
            w = crop.x1 - crop.x0
            h = crop.y1 - crop.y0

        # New page sized exactly to cropped content
        new_page = out_doc.new_page(width=w, height=h)

        # Map cropped source area → full new page
        dest = fitz.Rect(0, 0, w, h)
        new_page.show_pdf_page(dest, src, i, clip=crop)
        trimmed += 1

    out = io.BytesIO()
    out_doc.save(out, garbage=4, deflate=True)
    out_doc.close()
    src.close()
    out.seek(0)
    return out.getvalue(), trimmed


if uploaded_file is not None:
    st.markdown("---")
    if st.button("✂️ גזור שוליים", type="primary", use_container_width=True):
        with st.spinner("מעבד... אנא המתן"):
            try:
                raw = uploaded_file.read()
                output_bytes, trimmed_pages = trim_pdf(raw, extra_margin_mm, sensitivity)
                st.success(f"✅ הצלחה! עובדו {trimmed_pages} עמודים.")
                st.download_button(
                    label="⬇️ הורד Trimmed_Final.pdf",
                    data=output_bytes,
                    file_name="Trimmed_Final.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"❌ שגיאה: {e}")
                st.exception(e)
else:
    st.info("📂 אנא העלה קובץ PDF כדי להתחיל.")
