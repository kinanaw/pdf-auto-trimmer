import streamlit as st
import fitz  # PyMuPDF
import io
from PIL import Image, ImageFilter

Image.MAX_IMAGE_PIXELS = None

st.set_page_config(page_title="✂️ Kienan PDF Trimmer", layout="centered")
st.title("✂️ Kienan PDF Trimmer")
st.markdown("❤️ מוצר זה פותח על ידי כינאן עוידאת, לשימושכם באהבה.")
st.markdown("---")

padding_mm  = st.sidebar.slider('שוליים נוספים (מ"מ)', 0.0, 20.0, 1.0, 0.5)
sensitivity = st.sidebar.slider("רגישות (נמוך = אגרסיבי)", 200, 255, 245, 1)

uploaded_file = st.file_uploader("📂 העלה קובץ PDF", type="pdf")

if uploaded_file:
    try:
        raw = uploaded_file.read()
        doc = fitz.open(stream=raw, filetype="pdf")
        n = doc.page_count
        progress_bar = st.progress(0)
        trimmed = 0

        for pno in range(n):
            page = doc[pno]
            mb = fitz.Rect(page.mediabox)

            # DPI 72 מהיר — אבל מרחיבים קווים דקים לפני זיהוי
            pix = page.get_pixmap(dpi=72)
            img = Image.open(io.BytesIO(pix.tobytes())).convert("L")

            # הרחבת קווים דקים (dilate) — קווי CAD דקים יהפכו גדולים יותר
            img_dilated = img.filter(ImageFilter.MinFilter(3))

            bw = img_dilated.point(lambda x: 0 if x > sensitivity else 255)
            pixel_bbox = bw.getbbox()

            if not pixel_bbox:
                progress_bar.progress((pno + 1) / n)
                continue

            scale_x = mb.width  / pix.width
            scale_y = mb.height / pix.height

            crop = fitz.Rect(
                mb.x0 + pixel_bbox[0] * scale_x,
                mb.y0 + pixel_bbox[1] * scale_y,
                mb.x0 + pixel_bbox[2] * scale_x,
                mb.y0 + pixel_bbox[3] * scale_y,
            )

            pad = padding_mm * 2.83465
            crop = fitz.Rect(
                crop.x0 - pad,
                crop.y0 - pad,
                crop.x1 + pad,
                crop.y1 + pad,
            )

            crop = crop & mb

            if crop.width > 2 and crop.height > 2:
                page.set_cropbox(crop)
                trimmed += 1

            progress_bar.progress((pno + 1) / n)

        if trimmed == 0:
            st.warning("⚠️ לא זוהה תוכן — נסה להוריד את ערך הרגישות.")
        else:
            buffer = io.BytesIO()
            doc.save(buffer, garbage=4, deflate=True)
            buffer.seek(0)
            st.success(f"✅ הצלחה! עובדו {trimmed} עמודים.")
            st.download_button(
                label="⬇️ הורד Trimmed_Final.pdf",
                data=buffer,
                file_name="Trimmed_Final.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        doc.close()

    except Exception as e:
        st.error(f"❌ אירעה שגיאה: {e}")
        st.exception(e)
