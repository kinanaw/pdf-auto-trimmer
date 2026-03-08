import streamlit as st
import fitz  # PyMuPDF
import numpy as np
import io

st.set_page_config(page_title="✂️ Kienan PDF Trimmer", layout="centered")
st.title("✂️ Kienan PDF Trimmer")
st.markdown("❤️ מוצר זה פותח על ידי כינאן עוידאת, לשימושכם באהבה.")
st.markdown("---")

padding_mm = st.sidebar.slider('שוליים נוספים (מ"מ)', 0.0, 20.0, 2.0, 0.5)
sigma      = st.sidebar.slider("חוזק פילטר outliers (sigma)", 1.0, 5.0, 3.0, 0.5)

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

            drawings = page.get_drawings()

            # אסוף מרכזי כל אובייקט
            centers_x, centers_y = [], []
            rects = []

            for d in drawings:
                r = d.get("rect")
                if r is None:
                    continue
                w = r.x1 - r.x0
                h = r.y1 - r.y0
                if w * h < 4:
                    continue
                cx = (r.x0 + r.x1) / 2
                cy = (r.y0 + r.y1) / 2
                centers_x.append(cx)
                centers_y.append(cy)
                rects.append(r)

            if not rects:
                progress_bar.progress((pno + 1) / n)
                continue

            cx_arr = np.array(centers_x)
            cy_arr = np.array(centers_y)

            # סינון outliers לפי סטיית תקן מהמדיאנה
            med_x = np.median(cx_arr)
            med_y = np.median(cy_arr)
            std_x = np.std(cx_arr)
            std_y = np.std(cy_arr)

            # אם std=0 (כל אובייקטים באותו מקום) תן ערך מינימלי
            std_x = max(std_x, 1.0)
            std_y = max(std_y, 1.0)

            filtered = [
                r for r, cx, cy in zip(rects, centers_x, centers_y)
                if abs(cx - med_x) <= sigma * std_x
                and abs(cy - med_y) <= sigma * std_y
            ]

            if not filtered:
                filtered = rects  # fallback — קח הכל

            xmin = min(r.x0 for r in filtered) - pad
            ymin = min(r.y0 for r in filtered) - pad
            xmax = max(r.x1 for r in filtered) + pad
            ymax = max(r.y1 for r in filtered) + pad

            crop = fitz.Rect(xmin, ymin, xmax, ymax) & mb

            if crop.width > 2 and crop.height > 2:
                page.set_cropbox(crop)
                trimmed += 1

            progress_bar.progress((pno + 1) / n)

        if trimmed == 0:
            st.warning("⚠️ לא זוהה תוכן.")
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
