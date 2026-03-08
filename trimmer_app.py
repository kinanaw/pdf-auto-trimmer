import io
import zipfile
import streamlit as st
import fitz  # PyMuPDF
from PIL import Image, ImageFilter
from concurrent.futures import ThreadPoolExecutor, as_completed

Image.MAX_IMAGE_PIXELS = None

st.set_page_config(page_title="✂️ Kienan PDF Trimmer", layout="centered")
st.title("✂️ Kienan PDF Trimmer")
st.markdown("❤️ מוצר זה פותח על ידי כינאן עוידאת, לשימושכם באהבה.")
st.markdown("---")

# ─── Sidebar ────────────────────────────────────────────────────────────────
padding_mm  = st.sidebar.slider('שוליים נוספים (מ"מ)', 0.0, 20.0, 2.0, 0.5)
sensitivity = st.sidebar.slider("רגישות פיקסל (נמוך = אגרסיבי)", 180, 254, 240, 1)
method = st.sidebar.radio(
    "שיטת זיהוי תוכן",
    ["Vector (מהיר)", "Pixel (איטי, אמין)", "Vector → Pixel (שילוב)"],
    index=2,
)

# ─── Core logic ─────────────────────────────────────────────────────────────
TARGET_SHORT = 800

def _union(rects):
    valid = [r for r in rects if r and not r.is_empty and r.is_valid]
    if not valid:
        return None
    result = valid[0]
    for r in valid[1:]:
        result |= r
    return result

def detect_vector(page):
    rects = []
    for d in page.get_drawings():
        r = d.get("rect")
        if r:
            rects.append(fitz.Rect(r))
    for b in page.get_text("blocks"):
        r = fitz.Rect(b[:4])
        if not r.is_empty:
            rects.append(r)
    for img_info in page.get_images(full=True):
        try:
            bbox = page.get_image_bbox(img_info)
            if bbox and not fitz.Rect(bbox).is_empty:
                rects.append(fitz.Rect(bbox))
        except Exception:
            pass
    return _union(rects)

def detect_pixel(page, thresh):
    mb = fitz.Rect(page.mediabox)
    shortest = min(mb.width, mb.height)
    scale = TARGET_SHORT / shortest
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes())).convert("L")
    bw = img.filter(ImageFilter.MinFilter(3)).point(lambda x: 0 if x > thresh else 255)
    bb = bw.getbbox()
    if not bb:
        return None
    return fitz.Rect(
        mb.x0 + bb[0] / scale, mb.y0 + bb[1] / scale,
        mb.x0 + bb[2] / scale, mb.y0 + bb[3] / scale,
    )

def process_pdf(raw_bytes, filename, method_key, thresh, pad_pts):
    doc = fitz.open(stream=raw_bytes, filetype="pdf")
    trimmed = 0
    for page in doc:
        mb = fitz.Rect(page.mediabox)
        content = None
        if method_key == "vector":
            content = detect_vector(page)
        elif method_key == "pixel":
            content = detect_pixel(page, thresh)
        else:
            content = detect_vector(page) or detect_pixel(page, thresh)
        if not content:
            continue
        padded = fitz.Rect(
            content.x0 - pad_pts, content.y0 - pad_pts,
            content.x1 + pad_pts, content.y1 + pad_pts,
        ) & mb
        if padded.width > 2 and padded.height > 2:
            page.set_cropbox(padded)
            trimmed += 1
    buf = io.BytesIO()
    doc.save(buf, garbage=4, deflate=True)
    doc.close()
    buf.seek(0)
    return filename, buf.read(), trimmed

# ─── UI ─────────────────────────────────────────────────────────────────────
uploaded_files = st.file_uploader(
    "📂 העלה קבצי PDF (ניתן לבחור מספר קבצים)",
    type="pdf",
    accept_multiple_files=True,
)

if uploaded_files:
    st.write(f"**{len(uploaded_files)} קובץ/קבצים נבחרו**")
    if st.button("🚀 חתוך את כל הקבצים", type="primary", use_container_width=True):

        method_key = "vector" if "Vector (" in method else "pixel" if "Pixel (" in method else "combined"
        pad_pts = padding_mm * 2.83465

        # Read all files upfront (Streamlit uploaders close after first read)
        files_data = [(f.name, f.read()) for f in uploaded_files]

        progress = st.progress(0, text="מעבד קבצים…")
        status_area = st.empty()
        results = {}
        errors = {}

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(process_pdf, raw, name, method_key, sensitivity, pad_pts): name
                for name, raw in files_data
            }
            done = 0
            for future in as_completed(futures):
                name = futures[future]
                done += 1
                progress.progress(done / len(futures), text=f"הושלם: {name}")
                try:
                    fname, out_bytes, trimmed = future.result()
                    results[fname] = (out_bytes, trimmed)
                    status_area.write("\n".join(
                        f"✅ {n} — {t} עמודים גוזמו" for n, (_, t) in results.items()
                    ) + ("\n" + "\n".join(f"❌ {n}: {e}" for n, e in errors.items()) if errors else ""))
                except Exception as e:
                    errors[name] = str(e)

        progress.progress(1.0, text="✅ הכל הושלם!")

        if not results:
            st.error("לא הצליח לעבד אף קובץ.")
        elif len(results) == 1:
            # Single file → direct download
            fname, (out_bytes, _) = next(iter(results.items()))
            st.download_button(
                label=f"⬇️ הורד {fname}",
                data=out_bytes,
                file_name=fname.replace(".pdf", "_cropped.pdf"),
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            # Multiple files → ZIP
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for fname, (out_bytes, _) in results.items():
                    zf.writestr(fname.replace(".pdf", "_cropped.pdf"), out_bytes)
            zip_buf.seek(0)
            total_trimmed = sum(t for _, t in results.values())
            st.success(f"✅ {len(results)} קבצים עובדו — סה\"כ {total_trimmed} עמודים גוזמו.")
            st.download_button(
                label="⬇️ הורד את כל הקבצים כ-ZIP",
                data=zip_buf,
                file_name="Trimmed_PDFs.zip",
                mime="application/zip",
                use_container_width=True,
            )
