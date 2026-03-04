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

# --- UI ---
extra_margin_mm = st.slider('שוליים נוספים (מ"מ)', min_value=0, max_value=20, value=3)
sensitivity = st.slider("רגישות — סף לבן", min_value=150, max_value=254, value=200)
uploaded_file = st.file_uploader("העלה קובץ PDF", type=["pdf"])

# שמור קובץ ב-session_state כדי שלא יאבד בעת שינוי slider
if uploaded_file is not None:
    st.session_state["pdf_bytes"] = uploaded_file.read()
    st.session_state["pdf_name"] = uploaded_file.name

def mm_to_points(mm):
    return mm * 72.0 / 25.4

def get_content_bbox_pixels(page, white_threshold):
    scale = 150 / 72
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    gray = arr.mean(axis=2)
    mask = gray < white_threshold
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not rows.any() or not cols.any():
        return None
    top    = int(np.argmax(rows))
    bottom = int(len(rows) - np.argmax(rows[::-1]))
    left   = int(np.argmax(cols))
    right  = int(len(cols) - np.argmax(cols[::-1]))
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
    out = io.BytesIO()
    doc.save(out, garbage=4, deflate=True)
    doc.close()
    out.seek(0)
    return out.getvalue(), trimmed

# --- כפתור תמיד מוצג אם יש קובץ ---
st.markdown("---")
if "pdf_bytes" in st.session_state:
    st.success(f"✅ קובץ טעון: {st.session_state.get('pdf_name', 'קובץ PDF')}")
    if st.button("✂️ גזור שוליים", type="primary", use_container_width=True):
        with st.spinner("מעבד... אנא המתן"):
            try:
                output_bytes, trimmed_pages = trim_pdf(
                    st.session_state["pdf_bytes"],
                    extra_margin_mm,
                    sensitivity
                )
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
