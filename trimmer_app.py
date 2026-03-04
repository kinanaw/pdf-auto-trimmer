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

            page_area = page.rect.width * page.rect.height
            bbox = None

            # ---- TEXT ----
            for block in page.get_text("blocks"):
                rect = fitz.Rect(block[:4])
                bbox = rect if bbox is None else bbox | rect

            # ---- STROKE PATHS ONLY ----
            for d in page.get_drawings():

                # מתעלם ממילויים
                if d["fill"] is not None:
                    continue

                rect = fitz.Rect(d["rect"])
                rect_area = rect.width * rect.height

                # מתעלם ממסגרות ענק
                if rect_area > page_area * 0.8:
                    continue

                bbox = rect if bbox is None else bbox | rect

            if not bbox:
                dst.insert_pdf(src, from_page=pno, to_page=pno)
                continue

            pad = padding_mm * 2.83465
            bbox = fitz.Rect(
                bbox.x0 - pad,
                bbox.y0 - pad,
                bbox.x1 + pad,
                bbox.y1 + pad
            )

            bbox = bbox & page.mediabox

            if bbox.width <= 0 or bbox.height <= 0:
                continue

            new_page = dst.new_page(
                width=bbox.width,
                height=bbox.height
            )

            new_page.show_pdf_page(
                fitz.Rect(0, 0, bbox.width, bbox.height),
                src,
                pno,
                clip=bbox
            )

        buffer = io.BytesIO()
        dst.save(buffer)
        buffer.seek(0)

        st.success("White margins removed for pdf files.")

        st.download_button(
            "Download Clean PDF",
            buffer,
            file_name="trimmed_pdf.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    except Exception as e:
        st.exception(e)
