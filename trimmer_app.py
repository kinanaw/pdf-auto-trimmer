import streamlit as st
import fitz  # PyMuPDF
import io
from PIL import Image

# שורת הקסם שפותרת את שגיאת פצצת הדקומפרסיה
Image.MAX_IMAGE_PIXELS = None 

st.set_page_config(page_title="Kienan PDF Trimmer", page_icon="✂️")

st.title("✂️ Kienan PDF Trimmer")

st.markdown(
    """
    <div style="font-family: 'David', 'David Libre', serif; font-size: 26px; text-align: center; color: #4A4A4A;">
        ❤️ מוצר זה פותח על ידי <b><u>כינאן עוידאת</u></b>, לשימושכם באהבה .
    </div>
    """,
    unsafe_allow_html=True
)

padding_mm = st.sidebar.slider("Extra Margin (mm)", 0.0, 20.0, 1.0, 0.5)
dpi_value = st.sidebar.select_slider("Resolution (DPI)", options=[72, 100, 150, 200], value=150)
sensitivity = st.sidebar.slider("Sensitivity (Lower = Aggressive)", 200, 255, 250, 1)

uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if uploaded_file:
    try:
        # פותחים את הקובץ המקורי
        src = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        
        progress_bar = st.progress(0)
        
        for pno, page in enumerate(src):
            # 1. יצירת תמונה לצורך זיהוי תוכן
            pix = page.get_pixmap(dpi=dpi_value)
            img = Image.open(io.BytesIO(pix.tobytes()))
            
            # 2. ניתוח ויזואלי למציאת תוכן
            gray_img = img.convert("L")
            bw_mask = gray_img.point(lambda x: 0 if x > sensitivity else 255)
            pixel_bbox = bw_mask.getbbox()

            if not pixel_bbox:
                continue

            # 3. המרה לקואורדינטות PDF תוך התחשבות ב-MediaBox של הדף
            # שימוש ב-MediaBox מבטיח שאנחנו מתייחסים לממדים האמיתיים של הקובץ
            mb = page.mediabox
            scale_x = mb.width / pix.width
            scale_y = mb.height / pix.height
            
            # חישוב המלבן ביחס לנקודת ההתחלה של הדף
            fitz_bbox = fitz.Rect(
                mb.x0 + (pixel_bbox[0] * scale_x),
                mb.y0 + (pixel_bbox[1] * scale_y),
                mb.x0 + (pixel_bbox[2] * scale_x),
                mb.y0 + (pixel_bbox[3] * scale_y)
            )

            # 4. הוספת שוליים (Padding)
            pad = padding_mm * 2.83465
            fitz_bbox.x0 -= pad
            fitz_bbox.y0 -= pad
            fitz_bbox.x1 += pad
            fitz_bbox.y1 += pad
            
            # 5. תיקון קריטי: Clamping
            # מוודא שה-CropBox החדש מוכל בתוך ה-MediaBox המקורי
            # זה מונע את השגיאה CropBox not in MediaBox
            final_rect = fitz_bbox & mb 
            
            # בדיקה שהמלבן הסופי תקין ולא התכווץ לאפס
            if final_rect and not final_rect.is_empty:
                page.set_cropbox(final_rect)
                # אנחנו לא נוגעים ב-MediaBox כדי לא "לשבור" את המבנה הפנימי
            
            progress_bar.progress((pno + 1) / len(src))

        # שמירה
        buffer = io.BytesIO()
        src.save(buffer, garbage=4, deflate=True)
        buffer.seek(0)

        st.success("הקובץ עובד בהצלחה!")
        st.download_button(
            label="Download Trimmed PDF",
            data=buffer,
            file_name="Trimmed_Final.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    except Exception as e:
        st.error(f"אירעה שגיאה בעיבוד: {e}")
