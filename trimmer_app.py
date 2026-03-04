import streamlit as st
import fitz  # PyMuPDF
import io
from PIL import Image

# מניעת שגיאת פצצת דקומפרסיה
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

padding_mm = st.sidebar.slider("Extra Margin (mm)", 0.0, 20.0, 5.0, 0.5)
sensitivity = st.sidebar.slider("Sensitivity (For Scanned Content)", 200, 255, 250, 1)

uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if uploaded_file:
    try:
        src = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        dst = fitz.open()

        progress_bar = st.progress(0)
        
        for pno, page in enumerate(src):
            # 1. זיהוי וקטורי - מוצא את כל האובייקטים (טקסט, קווים, צורות)
            # זו השיטה הכי בטוחה שלא חותכת מידע
            v_bbox = page.get_bboxlog() 
            # אם יש לוג של אובייקטים, נחשב את המעטפת שלהם
            if v_bbox:
                # מאחדים את כל התיבות של האובייקטים לתיבה אחת גדולה
                full_v_rect = fitz.Rect()
                for item in v_bbox:
                    full_v_rect.insert_rect(item[1])
            else:
                full_v_rect = page.rect

            # 2. זיהוי פיקסלים (ליתר ביטחון עבור סריקות)
            pix = page.get_pixmap(dpi=100)
            img = Image.open(io.BytesIO(pix.tobytes()))
            gray_img = img.convert("L")
            bw_mask = gray_img.point(lambda x: 0 if x > sensitivity else 255)
            p_bbox = bw_mask.getbbox()
            
            if p_bbox:
                scale_x = page.rect.width / pix.width
                scale_y = page.rect.height / pix.height
                pixel_rect = fitz.Rect(
                    p_bbox[0] * scale_x, p_bbox[1] * scale_y,
                    p_bbox[2] * scale_x, p_bbox[3] * scale_y
                )
                # מאחדים את הזיהוי הוקטורי עם זיהוי הפיקסלים
                final_rect = full_v_rect | pixel_rect
            else:
                final_rect = full_v_rect

            # 3. הוספת שוליים בטוחה
            pad = padding_mm * 2.83465
            final_rect.x0 -= pad
            final_rect.y0 -= pad
            final_rect.x1 += pad
            final_rect.y1 += pad
            
            # וידוא שלא חרגנו מגבולות הדף המקורי
            final_rect = final_rect & page.rect

            # 4. יצירת הדף החתוך (שיטת ה-Copy המדויקת)
            if not final_rect.is_empty:
                new_page = dst.new_page(width=final_rect.width, height=final_rect.height)
                new_page.show_pdf_page(
                    new_page.rect,
                    src,
                    pno,
                    clip=final_rect
                )
            else:
                dst.insert_pdf(src, from_page=pno, to_page=pno)
            
            progress_bar.progress((pno + 1) / len(src))

        buffer = io.BytesIO()
        dst.save(buffer, garbage=4, deflate=True)
        buffer.seek(0)

        st.success("הקובץ מוכן! החיתוך בוצע על בסיס אובייקטים ופיקסלים.")
        st.download_button(
            label="Download Trimmed PDF",
            data=buffer,
            file_name="Trimmed_Safe.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    except Exception as e:
        st.error(f"אירעה שגיאה: {e}")
