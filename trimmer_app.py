import streamlit as st
import fitz
import io

st.set_page_config(page_title="PDF Ink Trimmer", page_icon="✂️")

st.title("✂️ True Vector PDF Ink Trimmer")

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
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")

        for page in doc:

            original_media = page.mediabox
            bbox = None

            for item in page.get_bboxlog():
                rect = fitz.Rect(item[1])
                bbox = rect if bbox is None else bbox | rect

            if bbox:

                pad = padding_mm * 2.83465

                bbox = fitz.Rect(
                    bbox.x0 - pad,
                    bbox.y0 - pad,
                    bbox.x1 + pad,
                    bbox.y1 + pad
                )

                # ===== CLIP TO ORIGINAL PAGE =====
                bbox = fitz.Rect(
                    max(original_media.x0, bbox.x0),
                    max(original_media.y0, bbox.y0),
                    min(original_media.x1, bbox.x1),
                    min(original_media.y1, bbox.y1),
                )

                # לוודא bbox תקין
                if bbox.width > 0 and bbox.height > 0:
                    page.set_mediabox(bbox)
                    page.set_cropbox(bbox)

        output = io.BytesIO()
        doc.save(output)
        output.seek(0)

        st.success("All pages trimmed successfully.")

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
