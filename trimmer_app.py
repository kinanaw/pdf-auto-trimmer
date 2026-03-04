import streamlit as st
import fitz  # PyMuPDF
import io
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

st.set_page_config(page_title="✂️ Kienan PDF Trimmer", layout="centered")
st.title("✂️ Kienan PDF Trimmer")
st.markdown("❤️ מוצר זה פותח על ידי כינאן עוידאת, לשימושכם באהבה.")
st.markdown("---")

padding_mm = st.sidebar.slider("שוליים נוספים (מ\"מ)", 0.0, 20.0, 1.0, 0.5)
dpi_value = st.sidebar.select_slider("רזולוציה (DPI)", options=[72, 100, 150, 200], value=100)
sensitivity = st.sidebar.slider("רגישות (נמוך = אגרסיבי)", 200, 255, 250, 1)

uploaded_file = st.file_uploader("📂 העלה קובץ PDF", type="pdf")

if uploaded_file:
    try:
        src = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        dst = fitz.open()
        progress_bar = st.progress(0)
        n = src.page_count

        for pno in range(n):
            page = src[pno]
            pix = page.get_pixmap(dpi=dpi_value)
            img = Image.open(io.BytesIO(pix.tobytes()))

            gray_img = img.convert("L")
            bw_mask = gray_img.point(lambda x: 0 if x > sensitivity else 255)
            pixel_bbox = bw_mask.getbbox()

            if not pixel_bbox:
                dst.insert_pdf(src, from_page=pno, to_page=pno)
                progress_bar.progress((pno + 1) / n)
                continue

            scale_x = page.rect.width / pix.width
            scale_y = page.rect.height / pix.height

            bbox = fitz.Rect(
                pixel_bbox[0] * scale_x,
                pixel_bbox[1] * scale_y,
                pixel_bbox[2] * scale_x,
                pixel_bbox[3] * scale_y,
            )

            pad = padding_mm * 2.83465
            bbox = fitz.Rect(bbox.x0 - pad, bbox.y0 - pad, bbox.x1 + pad, bbox.y1 + pad)
            bbox = bbox & page.rect

            if bbox.width > 2 and bbox.height > 2:
                new_page = dst.new_page(width=bbox.width, height=bbox.height)
                new_page.show_pdf_page(
                    fitz.Rect(0, 0, bbox.width, bbox.height),
                    src,
                    pno,
                    clip=bbox,
                )

            progress_bar.progress((pno + 1) / n)

        if dst.page_count == 0:
            st.warning("⚠️ לא נמצא תוכן — נסה להוריד את ערך הרגישות.")
        else:
            buffer = io.BytesIO()
            dst.save(buffer, garbage=4, deflate=True)
            buffer.seek(0)
            st.success(f"✅ הקובץ עובד בהצלחה! ({dst.page_count} עמודים)")
            st.download_button(
                label="⬇️ הורד Trimmed_Final.pdf",
                data=buffer,
                file_name="Trimmed_Final.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    except Exception as e:
        st.error(f"❌ אירעה שגיאה: {e}")
        st.exception(e)
