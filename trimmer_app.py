import streamlit as st
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="PDF Ink Trimmer", page_icon="✂️")

st.title("✂️ True Vector PDF Ink Trimmer")

# ===== Credit Section =====
st.markdown(
    """
    <div style="font-family: 'David', 'David Libre', serif; font-size: 30px; text-align: center; width: 100%; margin-top: 10px; margin-bottom: 20px;">
        מוצר זה פותח על ידי <b><u>כינאן עוידאת</u></b>, לשימושכם באהבה.
    </div>
    """, 
    unsafe_allow_html=True
)
st.write("---")
# ===========================

st.write("Removes all white margins by trimming to actual drawn content.")

padding_mm = st.sidebar.slider("Extra Margin (mm)", 0.0, 20.0, 2.0, 0.5)

uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if uploaded_file:
    try:
        file_bytes = uploaded_file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        for page in doc:

            bbox = None

            for item in page.get_bboxlog():
                rect = fitz.Rect(item[1])
                if bbox is None:
                    bbox = rect
                else:
                    bbox |= rect  # union of all objects

            if bbox:
                # convert mm to PDF points
                pad = padding_mm * 2.83465

                bbox.x0 -= pad
                bbox.y0 -= pad
                bbox.x1 += pad
                bbox.y1 += pad

                page.set_cropbox(bbox)
                page.set_mediabox(bbox)

        output = io.BytesIO()
        doc.save(output)
        output.seek(0)

        st.success("All pages trimmed to ink area.")

        st.download_button(
            "Download Trimmed PDF",
            output,
            file_name="trimmed_vector.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    except Exception as e:
        st.error("Crash detected")
        st.exception(e)
