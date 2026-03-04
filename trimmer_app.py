import streamlit as st
import fitz  # PyMuPDF
import io

# 1. הגדרות דף
st.set_page_config(page_title="PDF Multi-Trimmer", page_icon="✂️", layout="wide")

# 2. כותרת וקרדיט
st.title("✂️ PDF Multi-Trimmer")
st.markdown("### מוצר זה פותח על ידי כינאן עוידאת, לשימושכם באהבה.")

# 3. תפריט צד
padding = st.sidebar.slider("Padding (points)", 0, 100, 20)

uploaded_files = st.file_uploader("גרור לכאן קבצי PDF", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        with st.expander(f"מעבד את: {uploaded_file.name}", expanded=True):
            file_bytes = uploaded_file.read()
            src_doc = fitz.open(stream=file_bytes, filetype="pdf")
            out_doc = fitz.open()
            
            for page in src_doc:
                # מציאת התיבה של התוכן הנראה (Inked Area) בצורה חסינה
                # ננסה מספר שיטות לפי סדר עדיפויות של דיוק
                rect = None
                
                # שיטה 1: חיפוש כל פריטי הדיו (Text, Image, Path)
                blocks = page.get_bboxlog()
                if blocks:
                    rect = fitz.Rect()
                    for b in blocks:
                        rect.include_rect(fitz.Rect(b[1]))
                
                # אם נמצא תוכן תקין
                if rect and rect.width > 0 and rect.height > 0:
                    crop_rect = fitz.Rect(
                        rect.x0 - padding,
                        rect.y0 - padding,
                        rect.x1 + padding,
                        rect.y1 + padding
                    )
                    
                    # יצירת עמוד חדש והעתקה
                    new_page = out_doc.new_page(width=crop_rect.width, height=crop_rect.height)
                    mat = fitz.Matrix(1, 1).pretranslate(-crop_rect.x0, -crop_rect.y0)
                    
                    try:
                        new_page.show_pdf_page(
                            new_page.rect,
                            src_doc,
                            page.number,
                            matrix=mat,
                            clip=crop_rect
                        )
                    except Exception:
                        # גיבוי במקרה של שגיאה בחיתוך
                        new_page_err = out_doc.new_page(width=page.rect.width, height=page.rect.height)
                        new_page_err.show_pdf_page(new_page_err.rect, src_doc, page.number)
                else:
                    # עמוד ריק או שלא זוהה תוכן - מעתיקים כפי שהוא
                    new_page_blank = out_doc.new_page(width=page.rect.width, height=page.rect.height)
                    new_page_blank.show_pdf_page(new_page_blank.rect, src_doc, page.number)

            # שמירה
            output_buffer = io.BytesIO()
            out_doc.save(output_buffer, garbage=4, deflate=True, clean=True)
            
            st.success(f"הסתיים העיבוד: {uploaded_file.name}")
            st.download_button(
                label=f"הורד קובץ חתוך: {uploaded_file.name}",
                data=output_buffer.getvalue(),
                file_name=f"trimmed_{uploaded_file.name}",
                mime="application/pdf",
                key=f"dl_{uploaded_file.name}"
            )
