import streamlit as st
import fitz
import io

st.set_page_config(page_title="Kienan PDF Trimmer", page_icon="✂️")

st.title("✂️ Kienan Awidat PDF Trimmer")

st.markdown(
    """
    <div style="font-family: 'David', 'David Libre', serif; font-size: 30px; text-align: center;">
        מוצר זה פותח על ידי <b><u>כינאן עוידאת</u></b>, לשימושכם באהבה.
    </div>
    """,
    unsafe_allow_html=True
)
st.write("---")

padding_mm = st.sidebar.slider("Extra Margin (mm)", 0.0, 20.0, 1.0, 0.5)

uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if uploaded_file:
    try:
        src = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        dst = fitz.open()

        for pno, page in enumerate(src):
            page_rect = page.rect
            bbox = None

            # 1. חיפוש טקסט ממשי
            text_dict = page.get_text("dict")
            for block in text_dict["blocks"]:
                if "lines" in block:  # מוודא שיש תוכן טקסטואלי
                    rect = fitz.Rect(block["bbox"])
                    bbox = rect if bbox is None else bbox | rect

            # 2. חיפוש גרפיקה (צורות, קווים ומילויים)
            for d in page.get_drawings():
                rect = fitz.Rect(d["rect"])
                
                # התעלמות מאובייקטים שמתפרסים על פני כל הדף (כנראה רקע)
                if rect.width > page_rect.width * 0.95 and rect.height > page_rect.height * 0.95:
                    continue
                
                bbox = rect if bbox is None else bbox | rect

            # 3. חיפוש תמונות
            for img in page.get_image_info():
                rect = fitz.Rect(img["bbox"])
                bbox = rect if bbox is None else bbox | rect

            # אם לא נמצא תוכן בכלל, שומרים על הדף המקורי או מדלגים
            if not bbox:
                dst.insert_pdf(src, from_page=pno, to_page=pno)
                continue

            # הוספת השוליים שהמשתמש בחר
            pad = padding_mm * 2.83465  # המרה מ-mm לנקודות PDF
            bbox = fitz.Rect(
                bbox.x0 - pad,
                bbox.y0 - pad,
                bbox.x1 + pad,
                bbox.y1 + pad
            )

            # וודוא שהתיבה לא חורגת מגבולות הדף המקורי
            bbox = bbox & page_rect

            if bbox.width <= 0 or bbox.height <= 0:
                continue

            # יצירת הדף החדש בגודל המצומצם
            new_page = dst.new_page(
                width=bbox.width,
                height=bbox.height
            )

            # העתקת התוכן מהמקור אל הדף החדש תוך חיתוך (clip)
            new_page.show_pdf_page(
                fitz.Rect(0, 0, bbox.width, bbox.height),
                src,
                pno,
                clip=bbox
            )

        buffer = io.BytesIO()
        dst.save(buffer)
        buffer.seek(0)

        st.success("השוליים הלבנים הוסרו בהצלחה!")

        st.download_button(
            "Download Clean PDF",
            buffer,
            file_name="trimmed_pdf_fixed.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    except Exception as e:
        st.exception(e)
