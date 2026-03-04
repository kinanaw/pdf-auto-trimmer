import streamlit as st
import fitz  # PyMuPDF
from PIL import Image, ImageChops
import io

# Page Config
st.set_page_config(page_title="Auto PDF Trimmer", page_icon="✂️")

st.title("✂️ Automatic PDF White-Space Trimmer")
st.markdown("פותח על ידי כינאן עוידאת לשימושכם באהבה.")

# --- Sidebar Settings ---
st.sidebar.header("Settings")
padding = st.sidebar.slider("Margin Padding (pixels)", 0, 100, 20, help="Adds a little breathing room around the ink.")
threshold = st.sidebar.slider("Sensitivity", 0, 255, 250, help="Lower if it crops too much; higher if it leaves gray noise.")

# --- File Uploader ---
uploaded_file = st.file_uploader("Drop your PDF here", type="pdf")

if uploaded_file:
    # Open PDF from memory
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    processed_pages = []
    
    st.info(f"Processing {len(doc)} pages...")
    progress_bar = st.progress(0)

    for i in range(len(doc)):
        page = doc[i]
        
        # 1. Render page to high-res image (300 DPI approx)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # 2. Find Content Bounding Box
        # We compare the image against a pure white background
        bg = Image.new('RGB', img.size, (255, 255, 255))
        diff = ImageChops.difference(img, bg)
        
        # Use a threshold to ignore "near-white" noise (common in scans)
        diff = diff.point(lambda p: p if p > (255 - threshold) else 0)
        bbox = diff.getbbox()

        if bbox:
            # Add the user-defined padding
            left, upper, right, lower = bbox
            bbox = (
                max(0, left - padding), 
                max(0, upper - padding), 
                min(img.size[0], right + padding), 
                min(img.size[1], lower + padding)
            )
            cropped_img = img.crop(bbox)
            processed_pages.append(cropped_img)
        
        progress_bar.progress((i + 1) / len(doc))

    # --- Results & Download ---
    if processed_pages:
        # Save images back to a single PDF buffer
        output_buffer = io.BytesIO()
        processed_pages[0].save(
            output_buffer, 
            format="PDF", 
            save_all=True, 
            append_images=processed_pages[1:],
            resolution=100.0,
            quality=95
        )
        
        st.success("✨ Done! All pages trimmed individually.")
        
        # Preview first and last page to show the different sizes
        col1, col2 = st.columns(2)
        with col1:
            st.image(processed_pages[0], caption="Page 1 Trimmed")
        with col2:
            st.image(processed_pages[-1], caption=f"Page {len(doc)} Trimmed")

        st.download_button(
            label="Download Trimmed PDF",
            data=output_buffer.getvalue(),
            file_name="trimmed_document.pdf",
            mime="application/pdf",
            use_container_width=True
        )
