import streamlit as st
import fitz  # PyMuPDF
from PIL import Image, ImageChops
import io

st.set_page_config(page_title="Auto PDF Trimmer", page_icon="✂️")

st.title("✂️ Automatic PDF White-Space Trimmer")

st.sidebar.header("Settings")
padding = st.sidebar.slider("Margin Padding (pixels)", 0, 100, 20)
threshold = st.sidebar.slider("Sensitivity", 0, 255, 240)

uploaded_file = st.file_uploader("Drop your PDF here", type="pdf")

if uploaded_file:

    file_bytes = uploaded_file.read()
    doc = fitz.open(stream=file_bytes, filetype="pdf")

    processed_pages = []

    st.info(f"Processing {len(doc)} pages...")
    progress_bar = st.progress(0)

    for i, page in enumerate(doc):

        # Render at true 300 DPI
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Convert to grayscale for cleaner thresholding
        gray = img.convert("L")

        # Create mask: anything darker than threshold is considered content
        mask = gray.point(lambda x: 255 if x < threshold else 0)

        bbox = mask.getbbox()

        if bbox:
            left, upper, right, lower = bbox

            bbox = (
                max(0, left - padding),
                max(0, upper - padding),
                min(img.width, right + padding),
                min(img.height, lower + padding)
            )

            cropped = img.crop(bbox)
        else:
            # אם לא נמצא תוכן – שומר את העמוד כמו שהוא
            cropped = img

        processed_pages.append(cropped)
        progress_bar.progress((i + 1) / len(doc))

    if processed_pages:

        output_buffer = io.BytesIO()

        processed_pages[0].save(
            output_buffer,
            format="PDF",
            save_all=True,
            append_images=processed_pages[1:],
            resolution=300
        )

        output_buffer.seek(0)

        st.success("Done.")

        st.image(processed_pages[0], caption="Preview")

        st.download_button(
            label="Download Trimmed PDF",
            data=output_buffer,
            file_name="trimmed_document.pdf",
            mime="application/pdf",
            use_container_width=True
        )
