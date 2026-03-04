import streamlit as st
import fitz  # PyMuPDF
import io

# הגדרות דף
st.set_page_config(page_title="PDF Multi-Trimmer", page_icon="✂️", layout="wide")

st.title("✂️ PDF Multi-Trimmer (גרסה יציבה סופית)")
st.markdown("חיתוך שוליים אוטומטי. גרסה זו כוללת תיקון מתמטי למערכות צירים מורכבות ב-PDF.")

# תפריט צד
padding = st.sidebar.slider("Padding (points)", 0, 100, 20)

uploaded_files = st.file_uploader("גרור לכאן קבצי PDF", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        with st.expander(f"מעבד את: {uploaded_file.name}", expanded=True):
            file_bytes = uploaded_file.read()
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            
            for page in doc:
                # 1. קבלת גבולות הדף המדויקים (MediaBox)
                m = page.rect  # זהו ה-MediaBox
                
                # 2. מציאת התוכן
                content_box = page.get_bboxlog()
                if content_box:
                    full_rect = fitz.Rect()
                    for item in content_box:
                        full_rect.include_rect(fitz.Rect(item[1]))
                    
                    # 3. חישוב נקודות החיתוך החדשות עם Padding
                    x0 = full_rect.x0 - padding
                    y0 = full_rect.y0 - padding
                    x1 = full_rect.x1 + padding
                    y1 = full_rect.y1 + padding
                    
                    # 4. התיקון הקריטי: מניעת חריגה מה-MediaBox המקורי
                    # אנחנו "נועלים" את הערכים בתוך הטווח של m
                    x0 = max(m.x0, min(x0, m.x1))
                    y0 = max(m.y0, min(y0, m.y1))
                    x1 = max(m.x0, min(x1, m.x1))
                    y1 = max(m.y0, min(y1, m.y1))
                    
                    # יצירת התיבה הסופית
                    final_rect = fitz.Rect(x0, y0, x1, y1)
                    
                    # וידוא שהתיבה תקינה (רוחב וגובה חיוביים)
                    if not final_rect.is_empty and final_rect.width > 0 and final_rect.height > 0:
                        try:
                            page.set_cropbox(final_rect)
                        except Exception:
                            # אם עדיין יש שגיאה, ננסה להשתמש ב-Intersection של הספריה כגיבוי
                            page.set_cropbox(final_rect & m)

            # שמירה
            output_buffer = io.BytesIO()
            doc.save(output_buffer, garbage=4, deflate=True, clean=True)
            
            st.success(f"הסתיים: {uploaded_file.name}")
            st.download_button(
                label=f"הורד קובץ: {uploaded_file.name}",
                data=output_buffer.getvalue(),
                file_name=f"trimmed_{uploaded_file.name}",
                mime="application/pdf",
                key=f"dl_{uploaded_file.name}"
            )
