import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io

# Fix decompression bomb error
Image.MAX_IMAGE_PIXELS = None

st.set_page_config(page_title="✂️ Kienan PDF Trimmer", layout="centered")
st.title("✂️ Kienan PDF Trimmer")
st.markdown("❤️ מוצר זה פותח על ידי כינאן עוידאת, לשימושכם באהבה.")
st.markdown("---")

uploaded_file = st.file_uploader("העלה קובץ PDF", type=["pdf"])
extra_margin_mm = st.slider('שוליים נוספים (מ"מ)', min_value=0, max_value=20, value=3)
sensitivity = st.slider("רגישות (0=הכל לבן, 255=הכל שחור)", min_value=0, max_value=255, value=240)


def mm_to_points(mm):
    return mm * 72.0 / 25.4


def get_content_bbox_hybrid(page, sensitivity_threshold):
    """Hybrid: bboxlog + image_info + pixel fallback."""
    content_rect = None

    # Method 1: Vector paths / text / drawings
    try:
        for item in page.get_bboxlog():
            if len(item) >= 2:
                bbox = fitz.Rect(item[1])
                if bbox.is_valid and not bbox.is_empty:
                    content_rect = bbox if content_rect is None else content_rect.include_rect(bbox)
    except Exception:
        pass

    # Method 2: Embedded images
    try:
        for img_info in page.get_image_info():
            bbox = fitz.Rect(img_info.get("bbox", (0, 0, 0, 0)))
            if bbox.is_valid and not bbox.is_empty:
                content_rect = bbox if content_rect is None else content_rect.include_rect(bbox)
    except Exception:
        pass

    # Method 3: Pixel-level visual fallback
    try:
        scale = 150 / 72
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
        img_bin = img.point(lambda p: 255 if p < sensitivity_threshold else 0)
        bb = img_bin.getbbox()
        if bb:
            pr = page.rect
            pixel_rect = fitz.Rect(
                bb[0] / scale + pr.x0,
                bb[1] / scale + pr.y0,
                bb[2] / scale + pr.x0,
                bb[3] / scale + pr.y0,
            )
            content_rect = pixel_rect if content_rect is None else content_rect.include_rect(pixel_rect)
    except Exception:
        pass

    return content_rect


def trim_pdf(input_bytes, extra_margin_mm, sensitivity):
    extra_pts = mm_to_points(extra_margin_mm)
    trimmed = 0

    # Open fresh — keep doc alive for the full function scope
    doc = fitz.open(stream=input_bytes, filetype="pdf")
    num_pages = doc.page_count  # read BEFORE any loop

    for i in range(num_pages):
        page = doc[i]
        media_box = fitz.Rect(page.mediabox)  # copy to plain Rect
        content_rect = get_content_bbox_hybrid(page, sensitivity)

        if content_rect is None or content_rect.is_empty:
            continue

        final_rect = fitz.Rect(
            content_rect.x0 - extra_pts,
            content_rect.y0 - extra_pts,
            content_rect.x1 + extra_pts,
            content_rect.y1 + extra_pts,
        )

        # Clamp strictly inside MediaBox
        final_rect.x0 = max(final_rect.x0, media_box.x0)
        final_rect.y0 = max(final_rect.y0, media_box.y0)
        final_rect.x1 = min(final_rect.x1, media_box.x1)
        final_rect.y1 = min(final_rect.y1, media_box.y1)

        if final_rect.width < 1 or final_rect.height < 1:
            continue

        page.set_cropbox(final_rect)
        trimmed += 1

    out = io.BytesIO()
    doc.save(out, garbage=4, deflate=True)
    doc.close()  # close ONLY after save
    out.seek(0)
    return out.getvalue(), trimmed


# ── Main ──────────────────────────────────────────────────────────────────────
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
