import streamlit as st
import fitz  # PyMuPDF
import numpy as np
import io

st.set_page_config(page_title="✂️ Kienan PDF Trimmer", layout="centered")
st.title("✂️ Kienan PDF Trimmer")
st.markdown("❤️ מוצר זה פותח על ידי כינאן עוידאת, לשימושכם באהבה.")
st.markdown("---")

padding_mm = st.sidebar.slider('שוליים נוספים (מ"מ)', 0.0, 20.0, 2.0, 0.5)
percentile = st.sidebar.slider("פילטר outliers (percentile)", 1, 10, 2, 1)

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
            pad = padding_mm * 2.83465

            # STEP 1: קבל את כל אובייקטי הווקטור
            drawings = page.get_drawings()

            xs0, ys0, xs1, ys1 = [], [], [], []

            for d in drawings:
                r = d.get("rect")
                if r is None:
                    continue
                w = r.x1 - r.x0
                h = r.y1 - r.y0
                # STEP 4: סנן אובייקטים זעירים (פחות מ-4 נקודות מרובע)
                if w * h < 4:
                    continue
                xs0.append(r.x0)
                ys0.append(r.y0)
                xs1.append(r.x1)
                ys1.append(r.y1)

            if not xs0:
                # אין ווקטורים — דלג
                progress_bar.progress((pno + 1) / n)
                continue

            # STEP 5: percentile filtering — מסיר outliers של AutoCAD
            p = percentile
            xmin = float(np.percentile(xs0, p))
            ymin = float(np.percentile(ys0, p))
            xmax = float(np.percentile(xs1, 100 - p))
            ymax = float(np.percentile(ys1, 100 - p))

            # STEP 7: הוסף שוליים בטיחות
            xmin -= pad
            ymin -= pad
            xmax += pad
            ymax += pad

            # STEP 8: צור Rect וclamp בתוך mediabox
            crop = fitz.Rect(xmin, ymin, xmax, ymax) & mb

            if crop.width > 2 and crop.height > 2:
                page.set_cropbox(crop)
                trimmed += 1

            progress_bar.progress((pno + 1) / n)

        if trimmed == 0:
            st.warning("⚠️ לא זוהה תוכן — נסה לשנות את ה-percentile.")
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
