import streamlit as st
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="PDF Multi-Trimmer", page_icon="✂️", layout="wide")

st.title("✂️ PDF Multi-Trimmer (גרסת המרה נקייה)")
st.markdown("חיתוך שוליים בשיטת 'העתקה נקייה' למניעת שגיאות במערכות צירים מורכבות.")

padding = st.sidebar.slider("Padding (points)", 0, 100, 20)

uploaded_files = st.file_uploader("גרור לכאן קבצי PDF", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        with st.expander(f"מעבד את: {uploaded_file.name}", expanded=True):
            file_bytes = uploaded_file.read()
            src_doc = fitz.open(stream=file_bytes, filetype="pdf")
            
            # יצירת מסמך חדש לגמרי
            out_doc = fitz.open()
            
            for page in src_doc:
                # מציאת תיבת התוכן
                content_box = page.get_bboxlog()
                if content_box:
                    full_rect = fitz.Rect()
                    for item in content_box:
                        full_rect.include_rect(fitz.Rect(item[1]))
                    
                    # הוספת Padding
                    x0, y0, x1, y1 = full_rect.x0-padding, full_rect.y0-padding, full_rect.x1+padding, full_rect.y1+padding
                    final_rect = fitz.Rect(x0, y0, x1, y1)
                    
                    # יצירת עמוד חדש במסמך הפלט בגודל המדויק של החיתוך
                    new_page = out_doc.new_page(width=final_rect.width, height=final_rect.height)
                    
                    # העתקת התוכן מהעמוד המקורי לעמוד החדש תוך "הזזה" ל-0,0
                    # זה מבטל את כל בעיות ה-MediaBox
                    new_page.show_pdf_page(
                        new_page.rect,      # היכן להציג בעמוד החדש (כל העמוד)
                        src_doc,            # מסמך המקור
                        page.number,        # מספר העמוד
                        clip=final_rect     # מה לחתוך מהמקור
                    )
                else:
                    # אם העמוד ריק, פשוט נעתיק אותו כמו שהוא
                    new_page = out_doc.new_page(width=page.rect.width, height=page.rect.height)
                    new_page.show_pdf_page(new_page.rect, src_doc, page.number)

            # שמירה
            output_buffer = io.BytesIO()
            out_doc.save(output_buffer, garbage=4, deflate=True)
            
            st.success(f"הסתיים: {uploaded_file.name}")
            st.download_button(
                label=f"הורד קובץ: {uploaded_file.name}",
                data=output_buffer.getvalue(),
                file_name=f"trimmed_{uploaded_file.name}",
                mime="application/pdf",
                key=f"dl_{uploaded_file.name}"
            )
