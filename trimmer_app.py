import streamlit as st
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="PDF Inked-Area Trimmer", page_icon="✂️", layout="wide")

st.title("✂️ PDF Inked-Area Trimmer")
st.markdown("התמקדות בתוכן בלבד (Inked Area) והסרת כל השטח הלבן המיותר.")

# Sidebar
padding = st.sidebar.slider("Padding (points)", 0, 100, 20)

uploaded_files = st.file_uploader("גרור לכאן קבצי PDF", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        with st.expander(f"מעבד את: {uploaded_file.name}", expanded=True):
            file_bytes = uploaded_file.read()
            src_doc = fitz.open(stream=file_bytes, filetype="pdf")
            out_doc = fitz.open()
            
            for page in src_doc:
                # שיפור הזיהוי: נשתמש בשיטה שמחפשת תוכן נראה בלבד
                # get_bbox() מחזירה את המלבן המינימלי שמכיל את כל ה"דיו" (טקסט, קווים, תמונות)
                try:
                    # בגרסאות חדשות זו השיטה המדויקת ביותר ל-Inked Area
                    content_rect = page.get_bbox() 
                except AttributeError:
                    # גיבוי לגרסאות ישנות יותר - איסוף ידני של התיבה
                    content_rect = page.rect
                    # מחפש את התיבה המקיפה את כל התוכן הנראה
                    visible_box = page.get_bboxlog()
                    if visible_box:
                        full_rect = fitz.Rect()
                        for item in visible_box:
                            full_rect.include_rect(fitz.Rect(item[1]))
                        content_rect = full_rect

                if content_rect and not content_rect.is_empty:
                    # הגדרת התיבה החתוכה עם ה-Padding
                    crop_rect = fitz.Rect(
                        content_rect.x0 - padding,
                        content_rect.y0 - padding,
                        content_rect.x1 + padding,
                        content_rect.y1 + padding
                    )
                    
                    # יצירת עמוד חדש בגודל ה-Inked Area בלבד
                    new_page = out_doc.new_page(width=crop_rect.width, height=crop_rect.height)
                    
                    # מטריצת הזזה כדי שהפינה של הדיו תהיה ב-(0,0) של העמוד החדש
                    mat = fitz.Matrix(1, 1).pretranslate(-crop_rect.x0, -crop_rect.y0)
                    
                    # העתקה כירורגית של התוכן
                    new_page.show_pdf_page(
                        new_page.rect,
                        src_doc,
                        page.number,
                        matrix=mat,
                        clip=crop_rect
                    )
                else:
                    # אם העמוד באמת ריק לגמרי
                    new_page = out_doc.new_page(width=100, height=100) # עמוד קטן ריק

            # שמירה
            output_buffer = io.BytesIO()
            out_doc.save(output_buffer, garbage=4, deflate=True)
            
            st.success(f"הסתיים: {uploaded_file.name}")
            st.download_button(
                label=f"הורד קובץ (Inked Only): {uploaded_file.name}",
                data=output_buffer.getvalue(),
                file_name=f"inked_{uploaded_file.name}",
                mime="application/pdf",
                key=f"dl_{uploaded_file.name}"
            )
