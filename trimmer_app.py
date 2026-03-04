
Python
import streamlit as st
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="PDF Inked-Area Trimmer", page_icon="✂️", layout="wide")

st.title("✂️ PDF Inked-Area Trimmer")
st.markdown("פותח על ידי כינאן עוידאת, לשימושכם באהבה.")

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
                # 1. מציאת התיבה של התוכן הנראה (Inked Area)
                # בגרסאות חדשות, page.get_bbox() הוא הכלי הכי חזק למשימה
                rect = page.get_bbox()
                
                # אם הדף לא ריק ויש בו תוכן
                if rect and rect.width > 0 and rect.height > 0:
                    # הוספת Padding בזהירות
                    crop_rect = fitz.Rect(
                        rect.x0 - padding,
                        rect.y0 - padding,
                        rect.x1 + padding,
                        rect.y1 + padding
                    )
                    
                    # 2. יצירת עמוד חדש בגודל התיבה שחישבנו
                    new_page = out_doc.new_page(width=crop_rect.width, height=crop_rect.height)
                    
                    # 3. יצירת מטריצת הזזה (Matrix)
                    # המטריצה מזיזה את התוכן כך שהפינה של ה-Inked Area תהיה ב-(0,0)
                    mat = fitz.Matrix(1, 1).pretranslate(-crop_rect.x0, -crop_rect.y0)
                    
                    # 4. העתקת התוכן לעמוד החדש
                    try:
                        new_page.show_pdf_page(
                            new_page.rect,   # גודל העמוד החדש
                            src_doc,         # מסמך המקור
                            page.number,     # מספר העמוד
                            matrix=mat,      # הזזה ל-(0,0)
                            clip=crop_rect   # חיתוך המקור
                        )
                    except Exception as e:
                        # אם החיתוך נכשל מסיבה כלשהי, ניצור עמוד רגיל כדי לא לתקוע את התהליך
                        st.warning(f"בעיה בעמוד {page.number + 1}: {e}")
                        new_page_err = out_doc.new_page(width=page.rect.width, height=page.rect.height)
                        new_page_err.show_pdf_page(new_page_err.rect, src_doc, page.number)
                else:
                    # אם העמוד ריק לגמרי, פשוט נעתיק אותו כפי שהוא
                    new_page_blank = out_doc.new_page(width=page.rect.width, height=page.rect.height)
                    new_page_blank.show_pdf_page(new_page_blank.rect, src_doc, page.number)

            # שמירה
            output_buffer = io.BytesIO()
            out_doc.save(output_buffer, garbage=4, deflate=True, clean=True)
            
            st.success(f"הסתיים: {uploaded_file.name}")
            st.download_button(
                label=f"הורד קובץ חתוך: {uploaded_file.name}",
                data=output_buffer.getvalue(),
                file_name=f"trimmed_{uploaded_file.name}",
                mime="application/pdf",
                key=f"dl_{uploaded_file.name}"
            )


