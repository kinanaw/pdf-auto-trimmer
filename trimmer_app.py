import streamlit as st
import fitz  # PyMuPDF
import io

# הגדרות דף
st.set_page_config(page_title="PDF Multi-Trimmer", page_icon="✂️", layout="wide")

st.title("✂️ PDF Multi-Trimmer")
st.markdown("חיתוך שוליים אוטומטי למספר קבצים במקביל. הפעם עם הגנה מפני חריגה מגבולות הדף.")

# תפריט צד
padding = st.sidebar.slider("Padding (points)", 0, 100, 20)

# העלאת קבצים מרובים
uploaded_files = st.file_uploader("גרור לכאן קבצי PDF", type="pdf", accept_multiple_files=True)

if uploaded_files:
    st.write(f"הועלו {len(uploaded_files)} קבצים:")
    
    for uploaded_file in uploaded_files:
        with st.expander(f"מעבד את: {uploaded_file.name}", expanded=True):
            file_bytes = uploaded_file.read()
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            
            for page in doc:
                # מציאת תיבת התוכן
                item_list = page.get_bboxlog()
                if item_list:
                    full_content_box = fitz.Rect()
                    for item in item_list:
                        item_rect = fitz.Rect(item[1])
                        full_content_box.include_rect(item_rect)
                    
                    # הוספת המרווח
                    full_content_box.x0 -= padding
                    full_content_box.y0 -= padding
                    full_content_box.x1 += padding
                    full_content_box.y1 += padding
                    
                    # --- התיקון החשוב ---
                    # אנחנו מוודאים שהתיבה החדשה לא גדולה מהדף המקורי (MediaBox)
                    media_box = page.rect
                    # הפונקציה & מחזירה רק את השטח המשותף לשתי התיבות
                    safe_crop_box = full_content_box & media_box
                    
                    # הגדרת החיתוך בבטחה
                    page.set_cropbox(safe_crop_box)

            # שמירה
            output_buffer = io.BytesIO()
            doc.save(output_buffer, garbage=4, deflate=True, clean=True)
            
            st.success(f"הסתיים העיבוד של {uploaded_file.name}")
            st.download_button(
                label=f"הורד קובץ חתוך: {uploaded_file.name}",
                data=output_buffer.getvalue(),
                file_name=f"trimmed_{uploaded_file.name}",
                mime="application/pdf",
                key=uploaded_file.name
            )
