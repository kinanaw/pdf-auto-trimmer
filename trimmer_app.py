import streamlit as st
import fitz  # PyMuPDF
from PIL import Image, ImageOps
import io
import tempfile
import os

# Fix decompression bomb error
Image.MAX_IMAGE_PIXELS = None

st.set_page_config(page_title="✂️ Kienan PDF Trimmer", layout="centered")

st.title("✂️ Kienan PDF Trimmer")
st.markdown("❤️ מוצר זה פותח על ידי כינאן עוידאת, לשימושכם באהבה.")

st.markdown("---")

# UI Controls
uploaded_file = st.file_uploader("העלה קובץ PDF", type=["pdf"])
extra_margin_mm = st.slider("שוליים נוספים (מ\"מ)", min_value=0, max_value=20, value=3)
sensitivity = st.slider("רגישות (0=הכל לבן, 255=הכל שחור)", min_value=0, max_value=255, value=240)


def mm_to_points(mm):
    """Convert millimeters to PDF points (1 inch = 72 points, 1 inch = 25.4 mm)."""
    return mm * 72.0 / 25.4


def get_content_bbox_hybrid(page, sensitivity_threshold):
    """
    Hybrid detection: combines bboxlog (vectors/text), image_info, and pixel analysis.
    Returns a fitz.Rect with the bounding box of all content, in page coordinates.
    """
    page_rect = page.rect  # Full page rect (MediaBox)
    content_rect = None

    # --- Method 1: Vector paths, text, drawings via get_bboxlog ---
    try:
        bboxlog = page.get_bboxlog()
        for item in bboxlog:
            # item is (type, rect) where rect is a fitz.Rect
            if len(item) >= 2:
                bbox = fitz.Rect(item[1])
                if bbox.is_valid and not bbox.is_empty:
                    if content_rect is None:
                        content_rect = bbox
                    else:
                        content_rect.include_rect(bbox)
    except Exception as e:
        st.warning(f"get_bboxlog אזהרה: {e}")

    # --- Method 2: Embedded images via get_image_info ---
    try:
        image_infos = page.get_image_info(hashes=False, xrefs=False)
        for img_info in image_infos:
            bbox = fitz.Rect(img_info.get("bbox", (0, 0, 0, 0)))
            if bbox.is_valid and not bbox.is_empty:
                if content_rect is None:
                    content_rect = bbox
                else:
                    content_rect.include_rect(bbox)
    except Exception as e:
        st.warning(f"get_image_info אזהרה: {e}")

    # --- Method 3: Pixel-level analysis (visual fallback) ---
    try:
        # Render page at 150 DPI for speed (scale from 72 dpi base)
        scale = 150 / 72
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes)).convert("L")  # Grayscale

        # Find bounding box of non-white pixels
        # Pixels darker than sensitivity_threshold are "inked"
        img_inverted = img.point(lambda p: 255 if p < sensitivity_threshold else 0)
        bbox_pixel = img_inverted.getbbox()

        if bbox_pixel:
            # bbox_pixel is in pixels at 150 DPI, convert to page points
            x0 = bbox_pixel[0] / scale + page_rect.x0
            y0 = bbox_pixel[1] / scale + page_rect.y0
            x1 = bbox_pixel[2] / scale + page_rect.x0
            y1 = bbox_pixel[3] / scale + page_rect.y0
            pixel_rect = fitz.Rect(x0, y0, x1, y1)

            if content_rect is None:
                content_rect = pixel_rect
            else:
                content_rect.include_rect(pixel_rect)
    except Exception as e:
        st.warning(f"pixel analysis אזהרה: {e}")

    return content_rect


def trim_pdf(input_bytes, extra_margin_mm, sensitivity):
    """
    Main trimming function.
    Uses hybrid detection and set_cropbox to trim each page.
    """
    extra_margin_pts = mm_to_points(extra_margin_mm)

    # Load the PDF from bytes
    doc = fitz.open(stream=input_bytes, filetype="pdf")

    trimmed_pages = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        media_box = page.mediabox  # The true physical page size

        # Get the hybrid content bounding box
        content_rect = get_content_bbox_hybrid(page, sensitivity)

        if content_rect is None or content_rect.is_empty:
            st.info(f"עמוד {page_num + 1}: לא נמצא תוכן, הדף נשמר ללא שינוי.")
            continue

        # Add extra margin around the content
        final_rect = fitz.Rect(
            content_rect.x0 - extra_margin_pts,
            content_rect.y0 - extra_margin_pts,
            content_rect.x1 + extra_margin_pts,
            content_rect.y1 + extra_margin_pts,
        )

        # Clamp final_rect within MediaBox to avoid "CropBox not in MediaBox" errors
        final_rect.x0 = max(final_rect.x0, media_box.x0)
        final_rect.y0 = max(final_rect.y0, media_box.y0)
        final_rect.x1 = min(final_rect.x1, media_box.x1)
        final_rect.y1 = min(final_rect.y1, media_box.y1)

        # Validate the rect is still meaningful
        if final_rect.width < 1 or final_rect.height < 1:
            st.warning(f"עמוד {page_num + 1}: תיבת הגזירה קטנה מדי, הדף נשמר ללא שינוי.")
            continue

        # Apply CropBox directly on the original page (preserves all layers/metadata)
        page.set_cropbox(final_rect)
        trimmed_pages += 1

    # Save to bytes
    output_buffer = io.BytesIO()
    doc.save(output_buffer, garbage=4, deflate=True)
    doc.close()
    output_buffer.seek(0)
    return output_buffer.getvalue(), trimmed_pages


# --- Main App Logic ---
if uploaded_file is not None:
    st.markdown("---")
    if st.button("✂️ גזור שוליים", type="primary", use_container_width=True):
        with st.spinner("מעבד את הקובץ... אנא המתן"):
            try:
                input_bytes = uploaded_file.read()
                output_bytes, trimmed_pages = trim_pdf(input_bytes, extra_margin_mm, sensitivity)

                st.success(f"✅ הצלחה! עובדו {trimmed_pages} עמודים.")
                st.download_button(
                    label="⬇️ הורד Trimmed_Final.pdf",
                    data=output_bytes,
                    file_name="Trimmed_Final.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"❌ שגיאה בעיבוד הקובץ: {e}")
                st.exception(e)
else:
    st.info("📂 אנא העלה קובץ PDF כדי להתחיל.")
