import streamlit as st
import fitz  # PyMuPDF
import io
from PIL import Image, ImageChops

st.set_page_config(page_title="Kienan PDF Trimmer - Final", page_icon="✂️")

st.title("✂️ Kienan PDF Trimmer - Ultra Precision")

st.markdown(
    """
    <div style="font-family: 'David', 'David Libre', serif; font-size: 22px; text-align: center; color: #4A4A4A;">
        גרסת הניקוי היסודית ביותר - מבוססת ניתוח פיקסלים אגרסיבי
    </div>
    """,
    unsafe_allow_html=True
)

padding_mm = st.sidebar.slider("Extra Margin (mm)", 0.0, 20.0, 1.0, 0.5)
# הוספתי אפשרות לשלוט ברגישות הלבן
sensitivity = st.sidebar.slider("Sensitivity (Lower = Aggressive)", 200, 255, 250, 1)

uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if uploaded_file:
    try:
        src = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        dst = fitz.open()

        progress_bar = st.progress(0)
        
        for pno, page in enumerate(src):
            # 1. יצירת תמונה ברזולוציה גבוהה לצורך זיהוי (300 DPI)
            pix = page.get_pixmap(dpi=150)
            img = Image.open(io.BytesIO(pix.tobytes()))
            
            # 2. הפיכה לשחור-לבן וניקוי רעשים
            gray_img = img.convert("L")
            
            # כל פיקסל שהוא מעל ה-Sensitivity הופך לשחור (רקע)
            # כל מה שכהה יותר הופך ללבן (תוכן)
            bw_mask = gray_img.point(lambda x: 0 if x > sensitivity else 255)
            
            # 3. מציאת תיבת הגבול המדויקת של התוכן
            pixel_bbox = bw_mask.getbbox()

            if not pixel_bbox:
                # אם לא נמצא כלום, נשמור על הדף המקורי
                dst.insert_pdf(src, from_page=pno, to_page=pno)
                continue

            # 4. המרה חזרה לקואורדינטות של PDF
            scale_x = page.rect.width / pix.width
            scale_y = page.rect.height / pix.height
            
            bbox = fitz.Rect(
                pixel_bbox[0] * scale_x,
                pixel_bbox[1] * scale_y,
                pixel_bbox[2] * scale_x,
                pixel_bbox[3] * scale_y
            )

            # 5. הוספת שוליים וצמצום לגבולות הדף המקורי
            pad = padding_mm * 2.83465
            bbox = fitz.Rect(bbox.x0 - pad, bbox.y0 - pad, bbox.x1 + pad, bbox.y1 + pad)
            bbox = bbox & page.rect

            # 6. יצירת הדף החדש והעתקת התוכן
            if bbox.width > 5 and bbox.height > 5: # הגנה מפני חיתוך לאפס
                new_page = dst.new_page(width=bbox.width, height=bbox.height)
                new_page.show_pdf_page(
                    fitz.Rect(0, 0, bbox.width, bbox.height),
                    src,
                    pno,
                    clip=bbox
                )
            
            progress_bar.progress((pno + 1) / len(src))

        buffer = io.BytesIO()
        dst.save(buffer)
        buffer.seek(0)

        st.success("הקובץ מוכן! הלבן הוסר לפי ניתוח פיקסלים.")
        st.download_button(
            label="Download Clean PDF",
            data=buffer,
            file_name="ultra_trimmed.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    except Exception as e:
        st.error(f"אירעה שגיאה: {e}")
