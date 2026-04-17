# fixers/pdf_fixer.py

import io
import os
import tempfile
from collections import defaultdict

import fitz
import pikepdf
from pikepdf import Name, String, Dictionary, Array
from PIL import Image, ImageStat

from transformers import BlipProcessor, BlipForConditionalGeneration

HF_TOKEN = os.environ.get("HF_TOKEN", None)

BLIP_MODEL_NAME = "Salesforce/blip-image-captioning-base"

blip_processor = BlipProcessor.from_pretrained(BLIP_MODEL_NAME)
blip_model     = BlipForConditionalGeneration.from_pretrained(
    BLIP_MODEL_NAME,
    token=HF_TOKEN,
)


# ==========================================
# COLOUR UTILITIES  (mirrored from checker)
# ==========================================

def int_to_rgb(color_int):
    return (
        (color_int >> 16) & 255,
        (color_int >> 8) & 255,
        color_int & 255,
    )


def luminance(r, g, b):
    def f(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast_ratio(c1, c2):
    L1 = luminance(*c1)
    L2 = luminance(*c2)
    return (max(L1, L2) + 0.05) / (min(L1, L2) + 0.05)


# ==========================================
# IMAGE UTILITIES
# ==========================================

def extract_image_bytes(doc, xref):
    try:
        pix = fitz.Pixmap(doc, xref)
        if pix.n >= 5:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        return pix.tobytes("png")
    except Exception:
        return None


def generate_alt_text(image_bytes):
    try:
        img     = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        inputs  = blip_processor(images=img, return_tensors="pt")
        out     = blip_model.generate(**inputs)
        caption = blip_processor.decode(out[0], skip_special_tokens=True)

        if not caption or len(caption.strip()) < 5:
            return "Image requires manual description."

        return caption
    except Exception:
        return "Image requires manual description."


def is_decorative(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = img.size

        # VERY small images only
        if w * h < 24 * 24:
            return True

        gray = img.convert("L")
        stat = ImageStat.Stat(gray)

        # Only near-blank images
        if stat.var[0] < 10:  # was 50 → too aggressive
            return True

        # Only extreme white/black
        if stat.mean[0] > 250 or stat.mean[0] < 5:
            return True

        return False
    except Exception:
        return False

def get_all_images(doc):
    """Return {page_index: [xref, ...]} with duplicates removed per page."""
    page_images = {}
    for i, page in enumerate(doc):
        xrefs = list(dict.fromkeys(img[0] for img in page.get_images(full=True)))
        page_images[i] = xrefs
    return page_images


# ==========================================
# STRUCTURE UTILITIES
# ==========================================

def create_structure_if_missing(pdf):
    if "/StructTreeRoot" in pdf.Root:
        return pdf.Root["/StructTreeRoot"]

    struct = pdf.make_indirect(Dictionary({
        "/Type": Name("/StructTreeRoot"),
        "/K":    Array([]),
    }))
    pdf.Root["/StructTreeRoot"] = struct
    pdf.Root["/MarkInfo"]       = Dictionary({"/Marked": True})
    return struct


def _append_to_struct(struct, elem):
    if "/K" not in struct:
        struct["/K"] = Array()
    struct["/K"].append(elem)


def create_figure_tag(pdf, struct, page_obj, alt_text):
    """Create an informative Figure element with the given alt text."""
    page_ref = page_obj.obj if hasattr(page_obj, "obj") else page_obj
    fig = pdf.make_indirect(Dictionary({
        "/Type": Name("/StructElem"),
        "/S":    Name("/Figure"),
        "/Alt":  String(alt_text),
        "/Pg":   page_ref,
    }))
    _append_to_struct(struct, fig)


def create_decorative_figure_tag(pdf, struct, page_obj):
    """
    Create a Figure element for a decorative image.

    The checker identifies decorative figures by checking whether
    /ActualText contains "decorative".  Setting /ActualText = "decorative"
    here (rather than /Alt = "") means the checker correctly counts this as
    decorative rather than as a missing-alt-text violation.
    """
    page_ref = page_obj.obj if hasattr(page_obj, "obj") else page_obj
    fig = pdf.make_indirect(Dictionary({
        "/Type":       Name("/StructElem"),
        "/S":          Name("/Figure"),
        "/Alt":        String(""),
        "/ActualText": String("decorative"),
        "/Pg":         page_ref,
    }))
    _append_to_struct(struct, fig)


# ==========================================
# FIX 1 – ALT TEXT
# ==========================================

def _build_obj_to_page(pdf):
    """
    Return a dict mapping PDF object number → zero-based page index.

    The broken original code used  pg.objgen[0] - 1  which treated the PDF
    object number as a page index.  Object numbers are assigned in order of
    creation, not in page order, so this produces a completely wrong value
    for every page after the first.

    The correct approach is to iterate pdf.pages once, record each page's
    object number, then look up Figure elements' /Pg references against that
    mapping.
    """
    obj_to_page = {}
    for i, page in enumerate(pdf.pages):
        try:
            obj_to_page[page.objgen[0]] = i
        except Exception:
            pass
    return obj_to_page


def _collect_figures_needing_alt(struct, obj_to_page):
    """
    Walk the StructTree and return two lists:

    figures_by_page  – dict {page_index: [elem, ...]}
                       Figures whose page we could resolve via /Pg.

    orphan_figures   – [elem, ...]
                       Figures with no /Pg or an unresolvable /Pg reference.
                       These are paired with whatever images remain after
                       page-matched figures are processed.

    Figures that already have adequate alt text (len >= 5) or are already
    marked decorative via /ActualText are skipped.
    """
    figures_by_page = defaultdict(list)
    orphan_figures  = []

    def walk(elem):
        try:
            if isinstance(elem, Array):
                for c in elem:
                    walk(c)
                return

            if not isinstance(elem, Dictionary):
                return

            s      = elem.get("/S")
            s_name = str(s)[1:] if isinstance(s, Name) else None

            if s_name == "Figure":
                alt    = elem.get("/Alt")
                actual = elem.get("/ActualText")

                # Already decorative — nothing to do
                if isinstance(actual, String) and "decorative" in str(actual).lower():
                    pass

                # Already has adequate alt text — nothing to do
                elif alt and len(str(alt).strip()) >= 5:
                    pass

                else:
                    # Needs alt text — try to resolve the page
                    page_index = None
                    pg = elem.get("/Pg")
                    if pg is not None:
                        try:
                            page_index = obj_to_page.get(pg.objgen[0])
                        except Exception:
                            pass

                    if page_index is not None:
                        figures_by_page[page_index].append(elem)
                    else:
                        orphan_figures.append(elem)

            k = elem.get("/K")
            if k:
                walk(k)

        except Exception:
            pass

    walk(struct)
    return figures_by_page, orphan_figures


def _caption_for_image(doc, xref):
    img_bytes = extract_image_bytes(doc, xref)
    if not img_bytes:
        return "Image requires manual description.", False

    # Generate caption FIRST
    caption = generate_alt_text(img_bytes)

    # Only mark decorative if:
    # - caption is weak AND
    # - strong decorative signal
    if is_decorative(img_bytes) and (
        not caption or "manual" in caption.lower()
    ):
        return "", True

    return caption, False


def _apply_alt_to_elem(elem, caption, decorative):
    existing_alt = elem.get("/Alt")
    existing_actual = elem.get("/ActualText")

    # If already marked decorative → leave it
    if isinstance(existing_actual, String) and "decorative" in str(existing_actual).lower():
        return

    # If already has good alt text → DO NOT overwrite
    if existing_alt and len(str(existing_alt).strip()) >= 5:
        return

    # Only mark decorative if VERY confident
    if decorative and not caption:
        elem["/ActualText"] = String("decorative")
        elem["/Alt"] = String("")
    else:
        elem["/Alt"] = String(caption if caption else "Image requires manual description.")

def fix_alt_text(pdf, doc, struct, page_images):
    """
    Two-phase alt-text fixer.

    Phase 1 – Fix existing Figure elements in the StructTree
    ---------------------------------------------------------
    For each Figure element that is missing alt text we look up its page via
    /Pg → obj_to_page and then pair it with the next unused image xref on
    that page.  This is an ordered pairing: the first Figure on a page gets
    the first image, the second Figure gets the second image, etc.  It is a
    heuristic but matches the typical document order.

    Figures whose page cannot be resolved (no /Pg, or object number not in
    the page list) are collected as "orphans" and processed in Phase 1b using
    whatever image xrefs are still unused after the page-matched pass.

    Phase 2 – Tag genuinely untagged images
    ----------------------------------------
    Any image xref that was not consumed in Phase 1 has no StructTree entry
    at all.  We create a new Figure element for each, using BLIP to generate
    a caption.

    Returns the set of all image xrefs that were processed (used_images).
    """
    obj_to_page = _build_obj_to_page(pdf)

    figures_by_page, orphan_figures = _collect_figures_needing_alt(
        struct, obj_to_page
    )

    used_images: set = set()

    # ── Phase 1a: page-matched Figures ───────────────────────────────────
    for page_idx, figures in figures_by_page.items():
        # Build an ordered list of unused xrefs for this page
        available = [x for x in page_images.get(page_idx, [])
                     if x not in used_images]

        for i, fig_elem in enumerate(figures):
            if i < len(available):
                xref = available[i]
                caption, decorative = _caption_for_image(doc, xref)
                _apply_alt_to_elem(fig_elem, caption, decorative)
                used_images.add(xref)
            else:
                # More Figures on this page than images — use placeholder
                fig_elem["/Alt"] = String("Image requires manual description.")

    # ── Phase 1b: orphan Figures (no page info) ──────────────────────────
    if orphan_figures:
        remaining = [
            (pi, x)
            for pi, xrefs in page_images.items()
            for x in xrefs
            if x not in used_images
        ]

        for i, fig_elem in enumerate(orphan_figures):
            if i < len(remaining):
                _, xref       = remaining[i]
                caption, decorative = _caption_for_image(doc, xref)
                _apply_alt_to_elem(fig_elem, caption, decorative)
                used_images.add(xref)
            else:
                fig_elem["/Alt"] = String("Image requires manual description.")

    # ── Phase 2: genuinely untagged images ───────────────────────────────
    untagged = [
        (pi, x)
        for pi, xrefs in page_images.items()
        for x in xrefs
        if x not in used_images
    ]

    if untagged:
        print(f"  Tagging {len(untagged)} untagged image(s)...")
        for page_idx, xref in untagged:
            page_obj          = pdf.pages[page_idx]
            caption, decorative = _caption_for_image(doc, xref)
            if decorative:
                create_decorative_figure_tag(pdf, struct, page_obj)
            else:
                create_figure_tag(pdf, struct, page_obj, caption)
            used_images.add(xref)
    else:
        print("  All images matched to existing StructTree Figure elements.")

    return used_images


# ==========================================
# FIX 2 – TABLE HEADERS
# ==========================================

def fix_table_headers(pdf):
    """
    Walk the PDF StructTree.  For each Table element that has no TH
    descendants, convert the first TR's cells from TD → TH and add
    /Scope = /Column so the header relationship is explicit.

    Returns the number of tables fixed.
    """
    if "/StructTreeRoot" not in pdf.Root:
        return 0

    fixed = 0

    def has_th(elem):
        try:
            if isinstance(elem, Array):
                return any(has_th(c) for c in elem)
            if not isinstance(elem, Dictionary):
                return False
            s = elem.get("/S")
            if isinstance(s, Name) and str(s) == "/TH":
                return True
            k = elem.get("/K")
            return has_th(k) if k else False
        except Exception:
            return False

    def get_children(elem):
        k = elem.get("/K")
        if k is None:
            return []
        if isinstance(k, Array):
            return list(k)
        if isinstance(k, Dictionary):
            return [k]
        return []

    def promote_first_row(table_elem):
        for child in get_children(table_elem):
            if not isinstance(child, Dictionary):
                continue
            s = child.get("/S")
            if not (isinstance(s, Name) and str(s) == "/TR"):
                continue
            for cell in get_children(child):
                if not isinstance(cell, Dictionary):
                    continue
                cs = cell.get("/S")
                if isinstance(cs, Name) and str(cs) in ("/TD", "/TH"):
                    cell["/S"]     = Name("/TH")
                    cell["/Scope"] = Name("/Column")
            return True
        return False

    def walk(elem):
        nonlocal fixed
        try:
            if isinstance(elem, Array):
                for c in elem:
                    walk(c)
                return
            if not isinstance(elem, Dictionary):
                return

            s      = elem.get("/S")
            s_name = str(s)[1:] if isinstance(s, Name) else None

            if s_name == "Table" and not has_th(elem):
                if promote_first_row(elem):
                    fixed += 1

            k = elem.get("/K")
            if k:
                walk(k)
        except Exception:
            pass

    walk(pdf.Root["/StructTreeRoot"])
    return fixed


# ==========================================
# FIX 3 – LINK ACCESSIBLE NAMES
# ==========================================

def fix_link_accessible_names(pdf, doc):
    """
    Find Link annotations with neither visible text in their rectangle nor
    an existing /Contents entry, then populate /Contents with the link's URI
    or a page-destination reference so assistive technology has an accessible
    name.

    Returns the number of annotations updated.
    """
    fixed = 0

    for page_idx, page in enumerate(doc):
        try:
            pdf_page = pdf.pages[page_idx]
            annots   = pdf_page.get("/Annots")
            if not annots:
                continue
        except Exception:
            continue

        fitz_links = {
            (round(lk["from"][0]), round(lk["from"][1]),
             round(lk["from"][2]), round(lk["from"][3])): lk
            for lk in page.get_links()
            if lk.get("from")
        }

        for annot_ref in annots:
            try:
                annot = annot_ref

                if annot.get("/Subtype") != Name("/Link"):
                    continue

                existing = annot.get("/Contents")
                if existing and str(existing).strip():
                    continue

                raw_rect = annot.get("/Rect")
                if raw_rect is None:
                    continue

                fitz_rect    = fitz.Rect(float(raw_rect[0]), float(raw_rect[1]),
                                         float(raw_rect[2]), float(raw_rect[3]))
                visible_text = page.get_textbox(fitz_rect).strip()
                if visible_text:
                    continue

                accessible_name = _derive_link_name(annot, fitz_links, fitz_rect)
                if accessible_name:
                    annot["/Contents"] = String(accessible_name)
                    fixed += 1

            except Exception:
                pass

    return fixed


def _derive_link_name(annot, fitz_links, fitz_rect):
    action = annot.get("/A")
    if isinstance(action, Dictionary):
        uri = action.get("/URI")
        if uri:
            return str(uri)
        named = action.get("/N")
        if named:
            return str(named).lstrip("/")

    dest = annot.get("/Dest")
    if dest is not None:
        if isinstance(dest, Array) and len(dest) > 0:
            try:
                return f"Link to page {dest[0].objgen[0]}"
            except Exception:
                return "Internal link"
        return "Internal link"

    key = (round(fitz_rect.x0), round(fitz_rect.y0),
           round(fitz_rect.x1), round(fitz_rect.y1))
    lk = fitz_links.get(key)
    if lk:
        uri = lk.get("uri", "")
        if uri:
            return uri
        pg = lk.get("page")
        if pg is not None:
            return f"Link to page {pg + 1}"

    return "Link"


# ==========================================
# FIX 4 – COLOUR CONTRAST
# ==========================================

def fix_contrast(fitz_path):
    """
    Open *fitz_path*, find every low-contrast text span, redact the old
    rendering (white-fill), then reinsert the text in black.

    Why redact + reinsert rather than patching the content stream?
    Directly editing colour operators in a compressed binary content stream
    requires a full PDF content-stream parser.  PyMuPDF's redaction API
    safely removes the old rendered glyph, and insert_textbox places a new
    fully-accessible text span at the same position in black.

    The corrected file is written back to the same path via a temp file +
    os.replace so we never write to an open file handle.

    Returns the number of spans fixed.
    """
    doc   = fitz.open(fitz_path)
    fixed = 0

    for page in doc:
        blocks       = page.get_text("dict")["blocks"]
        spans_to_fix = []

        for b in blocks:
            if "lines" not in b:
                continue
            for line in b["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text or span["size"] < 6:
                        continue

                    color   = int_to_rgb(span["color"])
                    c_white = contrast_ratio(color, (255, 255, 255))
                    c_black = contrast_ratio(color, (0, 0, 0))

                    if max(c_white, c_black) < 4.5:
                        spans_to_fix.append(span)

        if not spans_to_fix:
            continue

        for span in spans_to_fix:
            page.add_redact_annot(fitz.Rect(span["bbox"]), fill=(1, 1, 1))

        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

        for span in spans_to_fix:
            try:
                page.insert_textbox(
                    fitz.Rect(span["bbox"]),
                    span["text"],
                    fontsize=span["size"],
                    color=(0, 0, 0),
                    align=fitz.TEXT_ALIGN_LEFT,
                )
                fixed += 1
            except Exception:
                pass

    if fixed > 0:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(tmp_fd)
        try:
            doc.save(
                tmp_path,
                incremental=False,
                encryption=fitz.PDF_ENCRYPT_NONE,
                garbage=4,
                deflate=True,
            )
            doc.close()
            os.replace(tmp_path, fitz_path)
        except Exception:
            doc.close()
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    else:
        doc.close()

    return fixed


# ==========================================
# MAIN FIXER
# ==========================================

def fix_pdf(path):
    """
    Apply all accessibility fixes to *path* and save as <base>_fixed.pdf.

    Fixes applied (in order)
    -------------------------
    1.  Title / Language metadata
    2.  Tagging  (StructTree created if absent)
    3.  Alt text  – existing Figure elements fixed via BLIP captioning;
                    genuinely untagged images get new Figure entries
    4.  Table headers  (TD → TH promotion on first row)
    5.  Link accessible names  (/Contents on image/shape links)
    6.  Colour contrast  (fitz redact + black reinsert, second pass)

    Returns the path of the saved fixed file.
    """
    print(f"Fixing PDF: {path}")

    base, ext  = os.path.splitext(path)
    fixed_path = path if base.endswith("_fixed") else f"{base}_fixed{ext}"

    # ── Open both libraries on the original file ──────────────────────────
    pdf = pikepdf.Pdf.open(path)
    doc = fitz.open(path)

    # ── 1. Metadata ───────────────────────────────────────────────────────
    if not pdf.docinfo.get("/Title"):
        pdf.docinfo.update({"/Title": String("Accessible Document")})

    if not pdf.Root.get("/Lang"):
        pdf.Root["/Lang"] = String("en-US")

    # ── 2. StructTree ─────────────────────────────────────────────────────
    struct = create_structure_if_missing(pdf)

    # ── 3. Alt text ───────────────────────────────────────────────────────
    page_images = get_all_images(doc)
    fix_alt_text(pdf, doc, struct, page_images)

    # ── 4. Table headers ──────────────────────────────────────────────────
    tables_fixed = fix_table_headers(pdf)
    if tables_fixed:
        print(f"  Table headers fixed: {tables_fixed} table(s)")

    # ── 5. Link accessible names ──────────────────────────────────────────
    links_fixed = fix_link_accessible_names(pdf, doc)
    if links_fixed:
        print(f"  Link accessible names added: {links_fixed} annotation(s)")

    # ── Save structural fixes ─────────────────────────────────────────────
    doc.close()
    pdf.save(fixed_path)
    pdf.close()
    print(f"Saved fixed PDF (structural): {fixed_path}")

    # ── 6. Colour contrast (second fitz pass on saved file) ───────────────
    contrast_fixed = fix_contrast(fixed_path)
    if contrast_fixed:
        print(f"  Contrast spans fixed: {contrast_fixed}")

    print(f"Saved fixed PDF (final): {fixed_path}")
    return fixed_path
