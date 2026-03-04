import streamlit as st
import fitz
import io

st.set_page_config(page_title="PDF Ink Trimmer", page_icon="✂️")

st.title("✂️ True Physical PDF Ink Trimmer")

st.markdown(
    """
    <div style="font-family: 'David', 'David Libre', serif; font-size: 30px; text-align: center; width: 100%; margin-top: 10px; margin-bottom: 20px;">
        מוצר זה פותח על ידי <b><u>כינאן עוידאת</u></b>, לשימושכם באהבה.
    </div>
    """,
    unsafe_allow_html=True
)
st.write("---")

padding_mm = st.sidebar.slider("Extra Margin (mm)", 0.0, 20.0, 2.0, 0.5)

uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if uploaded_file:
    try:
        src_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        new_doc = fitz.open()

        for page_number, page in enumerate(src_doc):

            bbox = None

            for item in page.get_bboxlog():
                rect = fitz.Rect(item[1])
                bbox = rect if bbox is None else bbox | rect

            if not bbox:
                # אם אין תוכן – מעתיקים עמוד רגיל
                new_doc.insert_pdf(src_doc, from_page=page_number, to_page=page_number)
                continue

            pad = padding_mm * 2.83465  # mm → points

            bbox = fitz.Rect(
                bbox.x0 - pad,
                bbox.y0 - pad,
                bbox.x1 + pad,
                bbox.y1 + pad
            )

            bbox = bbox & page.mediabox

            if bbox.width <= 0 or bbox.height <= 0:
                continue

            # יוצרים עמוד חדש בגודל פיזי של ה-Ink בלבד
            new_page = new_doc.new_page(
                width=bbox.width,
                height=bbox.height
            )

            # מציגים רק את אזור ה-bbox
            new_page.show_pdf_page(
                fitz.Rect(0, 0, bbox.width, bbox.height),
                src_doc,
                page_number,
                clip=bbox
            )

        output = io.BytesIO()
        new_doc.save(output)
        output.seek(0)

        st.success("PDF physically resized. No white margins remain.")

        st.download_button(
            "Download Trimmed PDF",
            output,
            file_name="trimmed_physical.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    except Exception as e:
        st.error("Crash detected")
        st.exception(e)
