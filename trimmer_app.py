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
        מוצר זה פותח על ידי <b><u>כינאן עוידאת</u></b>, לשימושכם באהבה ❤️.
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
        src = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        dst = fitz.open()

        progress_bar = st.progress(0)
        
        for pno, page in enumerate(src):
            # 1. יצירת תמונה לצורך זיהוי תוכן
            pix = page.get_pixmap(dpi=dpi_value)
            img = Image.open(io.BytesIO(pix.tobytes()))
            
            # 2. ניתוח ויזואלי למציאת תוכן (Bounding Box)
            gray_img = img.convert("L")
            bw_mask = gray_img.point(lambda x: 0 if x > sensitivity else 255)
            pixel_bbox = bw_mask.getbbox()

            # אם לא נמצא תוכן (דף לבן), פשוט תעתיק את הדף המקורי ותמשיך
            if not pixel_bbox:
                dst.insert_pdf(src, from_page=pno, to_page=pno)
                continue

            # 3. המרה לקואורדינטות PDF
            scale_x = page.rect.width / pix.width
            scale_y = page.rect.height / pix.height
            
            # יצירת מלבן זיהוי ראשוני
            fitz_bbox = fitz.Rect(
                pixel_bbox[0] * scale_x,
                pixel_bbox[1] * scale_y,
                pixel_bbox[2] * scale_x,
                pixel_bbox[3] * scale_y
            )

            # 4. הוספת שוליים
            pad = padding_mm * 2.83465
            crop_rect = fitz.Rect(
                fitz_bbox.x0 - pad,
                fitz_bbox.y0 - pad,
                fitz_bbox.x1 + pad,
                fitz_bbox.y1 + pad
            )
            
            # וודוא שהחיתוך לא חורג מגבולות הדף ולא הופך ל-None
            final_rect = crop_rect & page.rect

            # 5. יצירת דף חדש והעתקה - בדיקת תקינות המלבן (מניעת AttributeError)
            if final_rect and not final_rect.is_empty and final_rect.width > 1 and final_rect.height > 1:
                new_page = dst.new_page(width=final_rect.width, height=final_rect.height)
                new_page.show_pdf_page(
                    new_page.rect,   
                    src,             
                    pno,             
                    clip=final_rect   
                )
            else:
                # הגנה: אם המלבן לא תקין, תכניס דף מקורי
                dst.insert_pdf(src, from_page=pno, to_page=pno)
            
            progress_bar.progress((pno + 1) / len(src))

        buffer = io.BytesIO()
        dst.save(buffer)
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
