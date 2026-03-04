import streamlit as st
import fitz  # PyMuPDF
import io

# הגדרות דף
st.set_page_config(page_title="PDF Multi-Trimmer", page_icon="✂️", layout="wide")

st.title("✂️ PDF Multi-Trimmer (גרסה יציבה)")
st.markdown("חיתוך שוליים חכם שמוודא תמיד שהחיתוך נשאר בתוך גבולות הדף המקורי.")

# תפריט צד
padding = st.sidebar.slider("Padding (points)", 0, 100, 20)

# העלאת קבצים
uploaded_files = st.file_uploader("גרור לכאן קבצי PDF", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        with st.expander(f"מעבד את: {uploaded_file.name}", expanded=True):
            # קריאת הקובץ
            file_bytes = uploaded_file.read()
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            
            for page in doc:
                # 1. מציאת ה-MediaBox (גבולות הדף המקוריים)
                media_box = page.rect
                
                # 2. מציאת תיבת התוכן
                content_box = page.get_bboxlog()
                if content_box:
                    full_rect = fitz.Rect()
                    for item in content_box:
                        full_rect.include_rect(fitz.Rect(item[1]))
                    
                    # 3. הוספת Padding
                    full_rect.x0 -= padding
                    full_rect.y0 -= padding
                    full_rect.x1 += padding
                    full_rect.y1 += padding
                    
                    # 4. התיקון הקריטי: חיתוך (Intersect) עם ה-MediaBox
                    # זה מבטיח שה-CropBox לעולם לא יהיה גדול מהדף
                    safe_rect = full_rect & media_box
                    
                    # בדיקה נוספת שהתיבה לא הפכה לריקה/שגויה
                    if not safe_rect.is_empty:
                        page.set_cropbox(safe_rect)

            # שמירה
            output_buffer = io.BytesIO()
            doc.save(output_buffer, garbage=4, deflate=True, clean=True)
            
            st.success(f"הסתיים: {uploaded_file.name}")
            st.download_button(
                label=f"הורד קובץ: {uploaded_file.name}",
                data=output_buffer.getvalue(),
                file_name=f"trimmed_{uploaded_file.name}",
                mime="application/pdf",
                key=f"dl_{uploaded_file.name}" # מפתח ייחודי
            )
