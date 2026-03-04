import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import numpy as np
from typing import Tuple, Optional
# Disable PIL decompression bomb check
Image.MAX_IMAGE_PIXELS = None
class PDFTrimmer:
    def __init__(self):
        self.doc = None
        self.extra_margin_mm = 5.0
        self.sensitivity = 250
        
    def mm_to_points(self, mm: float) -> float:
        """Convert millimeters to PDF points (1mm = 2.83465 points)"""
        return mm * 2.83465
    
    def get_hybrid_bbox(self, page: fitz.Page) -> Optional[fitz.Rect]:
        """
        Calculate bounding box using hybrid detection:
        1. Vector paths and text from get_bboxlog()
        2. Images from get_image_info()
        3. Visual pixel analysis as fallback
        """
        # Initialize with empty rect
        union_rect = fitz.Rect()
        found_content = False
        
        # Method 1: Get vector paths, text, and drawings
        try:
            bbox_log = page.get_bboxlog()
            for item in bbox_log:
                if item.get("rect"):
                    rect = fitz.Rect(item["rect"])
                    if not rect.is_empty and rect.is_valid:
                        if not found_content:
                            union_rect = rect
                            found_content = True
                        else:
                            union_rect.include_rect(rect)
        except Exception as e:
            st.warning(f"⚠️ Vector detection warning: {str(e)}")
        
        # Method 2: Get image boundaries
        try:
            image_list = page.get_image_info()
            for img in image_list:
                if "bbox" in img:
                    rect = fitz.Rect(img["bbox"])
                    if not rect.is_empty and rect.is_valid:
                        if not found_content:
                            union_rect = rect
                            found_content = True
                        else:
                            union_rect.include_rect(rect)
        except Exception as e:
            st.warning(f"⚠️ Image detection warning: {str(e)}")
        
        # Method 3: Pixel-based detection as fallback
        try:
            # Get pixmap with higher resolution for better detection
            mat = fitz.Matrix(2.0, 2.0)  # 2x scaling for precision
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Convert to PIL Image
            img_data = pix.pil_tobytes(format="PNG")
            img = Image.open(io.BytesIO(img_data))
            
            # Convert to grayscale numpy array
            img_gray = img.convert('L')
            img_array = np.array(img_gray)
            
            # Find non-white pixels based on sensitivity
            non_white = img_array < self.sensitivity
            
            if np.any(non_white):
                # Find bounding box of non-white pixels
                rows = np.any(non_white, axis=1)
                cols = np.any(non_white, axis=0)
                
                if np.any(rows) and np.any(cols):
                    ymin, ymax = np.where(rows)[0][[0, -1]]
                    xmin, xmax = np.where(cols)[0][[0, -1]]
                    
                    # Convert pixel coordinates back to PDF coordinates
                    # Account for the 2x scaling
                    pixel_rect = fitz.Rect(
                        xmin / 2.0,
                        ymin / 2.0,
                        (xmax + 1) / 2.0,
                        (ymax + 1) / 2.0
                    )
                    
                    # Transform to page coordinates
                    page_rect = page.rect
                    scale_x = page_rect.width / (pix.width / 2.0)
                    scale_y = page_rect.height / (pix.height / 2.0)
                    
                    pixel_rect.x0 = page_rect.x0 + pixel_rect.x0 * scale_x
                    pixel_rect.y0 = page_rect.y0 + pixel_rect.y0 * scale_y
                    pixel_rect.x1 = page_rect.x0 + pixel_rect.x1 * scale_x
                    pixel_rect.y1 = page_rect.y0 + pixel_rect.y1 * scale_y
                    
                    if not found_content:
                        union_rect = pixel_rect
                        found_content = True
                    else:
                        union_rect.include_rect(pixel_rect)
                        
        except Exception as e:
            st.warning(f"⚠️ Pixel detection warning: {str(e)}")
        
        if not found_content:
            return None
            
        return union_rect
    
    def trim_pdf(self, pdf_bytes: bytes, extra_margin_mm: float, sensitivity: int) -> Tuple[bool, Optional[bytes], str]:
        """
        Trim white margins from PDF using set_cropbox method
        """
        self.extra_margin_mm = extra_margin_mm
        self.sensitivity = sensitivity
        
        try:
            # Open PDF document
            self.doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            if self.doc.page_count == 0:
                return False, None, "❌ PDF is empty"
            
            # Process each page
            trimmed_pages = 0
            for page_num in range(self.doc.page_count):
                page = self.doc[page_num]
                
                # Get hybrid bounding box
                content_rect = self.get_hybrid_bbox(page)
                
                if content_rect is None:
                    st.info(f"ℹ️ Page {page_num + 1}: No content detected, keeping original")
                    continue
                
                # Add extra margin
                margin_points = self.mm_to_points(extra_margin_mm)
                content_rect.x0 -= margin_points
                content_rect.y0 -= margin_points
                content_rect.x1 += margin_points
                content_rect.y1 += margin_points
                
                # Get MediaBox for clamping
                media_box = page.mediabox
                
                # Clamp the crop box within MediaBox to avoid errors
                final_rect = fitz.Rect(
                    max(content_rect.x0, media_box.x0),
                    max(content_rect.y0, media_box.y0),
                    min(content_rect.x1, media_box.x1),
                    min(content_rect.y1, media_box.y1)
                )
                
                # Ensure the rect is valid
                if final_rect.is_valid and not final_rect.is_empty:
                    # Set the CropBox directly on the original page
                    page.set_cropbox(final_rect)
                    trimmed_pages += 1
                    
                    # Debug info
                    st.success(f"✅ Page {page_num + 1}: Trimmed successfully")
                else:
                    st.warning(f"⚠️ Page {page_num + 1}: Invalid crop area, keeping original")
            
            if trimmed_pages == 0:
                return False, None, "⚠️ No pages were trimmed (no content detected)"
            
            # Save the modified document
            output_buffer = io.BytesIO()
            self.doc.save(output_buffer)
            self.doc.close()
            
            return True, output_buffer.getvalue(), f"✅ Successfully trimmed {trimmed_pages}/{self.doc.page_count} pages"
            
        except Exception as e:
            if self.doc:
                self.doc.close()
            return False, None, f"❌ Error: {str(e)}"
def main():
    st.set_page_config(
        page_title="PDF Trimmer",
        page_icon="✂️",
        layout="wide"
    )
    
    # Title and credit
    st.title("✂️ Kienan PDF Trimmer")
    st.markdown("❤️ מוצר זה פותח על ידי כינאן עוידאת, לשימושכם באהבה.")
    
    st.markdown("---")
    
    # Create columns for better layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # File uploader
        uploaded_file = st.file_uploader(
            "📄 Choose a PDF file",
            type=["pdf"],
            help="Upload the PDF file you want to trim"
        )
    
    with col2:
        # Settings
        st.subheader("⚙️ Settings")
        
        extra_margin = st.slider(
            "Extra Margin (mm)",
            min_value=0.0,
            max_value=20.0,
            value=5.0,
            step=0.5,
            help="Additional margin to keep around detected content"
        )
        
        sensitivity = st.slider(
            "Sensitivity (0-255)",
            min_value=0,
            max_value=255,
            value=250,
            step=5,
            help="Lower values = more aggressive trimming (detects lighter grays)"
        )
    
    st.markdown("---")
    
    if uploaded_file is not None:
        # Read PDF bytes
        pdf_bytes = uploaded_file.read()
        
        # Display file info
        st.info(f"📊 File: {uploaded_file.name} | Size: {len(pdf_bytes) / 1024:.1f} KB")
        
        # Process button
        if st.button("🚀 Trim PDF", type="primary", use_container_width=True):
            with st.spinner("🔄 Processing PDF..."):
                # Create trimmer instance
                trimmer = PDFTrimmer()
                
                # Process PDF
                success, output_bytes, message = trimmer.trim_pdf(
                    pdf_bytes, 
                    extra_margin, 
                    sensitivity
                )
                
                # Display result
                if success:
                    st.success(message)
                    
                    # Download button
                    st.download_button(
                        label="📥 Download Trimmed PDF",
                        data=output_bytes,
                        file_name="Trimmed_Final.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                else:
                    st.error(message)
    else:
        # Instructions
        st.info("👆 Please upload a PDF file to begin trimming")
        
        with st.expander("ℹ️ How it works"):
            st.markdown("""
            This tool uses **hybrid detection** to find content:
            
            1. **Vector Analysis**: Detects all paths, text, and drawings
            2. **Image Detection**: Includes embedded images and scans
            3. **Pixel Scanning**: Visual fallback for complex elements
            
            The tool preserves all layers and metadata by using direct CropBox modification.
            """)
if __name__ == "__main__":
    main()
