# pdf_checker.py

import fitz
import pikepdf
from pikepdf import Dictionary, Array, Name, String


# ==========================================
# SCORING
# ==========================================

def contrast_score(count):
    if count == 0:
        return 100
    if count <= 5:
        return 76
    if count <= 21:
        return 53
    return 5


def score_lookup(issue, count=0):
    issue = issue.lower()

    if issue == "alternative text":
        return 100 if count == 0 else (76 if count == 1 else 53)

    if issue == "decorative image":
        return 100 if count == 0 else (76 if count == 1 else 53)

    if issue == "tables with headers":
        return 100 if count == 0 else 68

    if issue == "color contrast":
        return contrast_score(count)

    if issue == "tagging pdf":
        return 100 if count == 0 else 7

    if issue == "title":
        return 100 if count == 0 else 98

    if issue == "language":
        return 100 if count == 0 else 95

    if issue == "links":
        return 100 if count == 0 else 76

    return 100


def get_ally_band(score):
    if score == 100:
        return "Dark Green"
    if score >= 67:
        return "Light Green"
    if score >= 34:
        return "Yellow"
    return "Red"


# ==========================================
# CONTRAST
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


def detect_contrast(doc):
    issues = 0

    for page in doc:
        blocks = page.get_text("dict")["blocks"]

        for b in blocks:
            if "lines" not in b:
                continue

            for line in b["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()

                    if not text or span["size"] < 6:
                        continue

                    color = int_to_rgb(span["color"])

                    c1 = contrast_ratio(color, (255, 255, 255))
                    c2 = contrast_ratio(color, (0, 0, 0))

                    if max(c1, c2) < 4.5:
                        issues += 1

    return issues


# ==========================================
# IMAGE COUNT
# ==========================================

def count_images(doc):
    total = 0
    for page in doc:
        total += len(page.get_images(full=True))
    return total


# ==========================================
# STRUCTURE WALK
# ==========================================

def walk_struct(elem, counters):
    try:
        if isinstance(elem, Array):
            for c in elem:
                walk_struct(c, counters)
            return

        if not isinstance(elem, Dictionary):
            return

        s      = elem.get("/S")
        s_name = str(s)[1:] if isinstance(s, Name) else None

        if s_name == "Figure":
            counters["figures"] += 1

            alt    = elem.get("/Alt")
            actual = elem.get("/ActualText")

            if isinstance(actual, String) and "decorative" in str(actual).lower():
                counters["decorative"] += 1
            elif not alt or len(str(alt).strip()) < 5:
                counters["missing_alt"] += 1

        if s_name == "Table":
            counters["tables"] += 1

        if s_name == "TH":
            counters["table_headers"] += 1

        k = elem.get("/K")
        if k:
            walk_struct(k, counters)

    except Exception:
        pass


# ==========================================
# LINKS
# ==========================================

def _rect_approx_match(r1, r2, tol=2.0):
    try:
        return (
            abs(r1[0] - r2[0]) < tol
            and abs(r1[1] - r2[1]) < tol
            and abs(r1[2] - r2[2]) < tol
            and abs(r1[3] - r2[3]) < tol
        )
    except Exception:
        return False


def detect_links(doc, pdf=None):
    """
    Count link annotations with neither visible text in their rect nor
    a /Contents accessible-name.  When *pdf* is supplied the /Contents
    check is performed so that post-fix re-checks reflect the improvement.
    """
    issues = 0

    for page_idx, page in enumerate(doc):
        contents_by_rect = {}
        if pdf is not None:
            try:
                pdf_page = pdf.pages[page_idx]
                annots   = pdf_page.get("/Annots")
                if annots:
                    for annot_ref in annots:
                        try:
                            annot = dict(annot_ref)
                            if annot.get("/Subtype") != Name("/Link"):
                                continue
                            raw_rect = annot.get("/Rect")
                            if raw_rect is None:
                                continue
                            key      = tuple(float(v) for v in raw_rect)
                            contents = annot.get("/Contents")
                            if contents:
                                contents_by_rect[key] = str(contents).strip()
                        except Exception:
                            pass
            except Exception:
                pass

        for link in page.get_links():
            rect = link.get("from")
            if not rect:
                continue

            text = page.get_textbox(rect).strip()
            if text:
                continue

            has_contents = False
            r = (rect[0], rect[1], rect[2], rect[3])
            for key, val in contents_by_rect.items():
                if _rect_approx_match(r, key) and val:
                    has_contents = True
                    break

            if not has_contents:
                issues += 1

    return issues


# ==========================================
# MAIN CHECKER
# ==========================================

def check_pdf(path, apply_fix=False):
    """
    Run an accessibility check on a PDF file.

    Parameters
    ----------
    path      : str  – path to the PDF
    apply_fix : bool – when True call the fixer and include fixed_path in result

    Returns a dict with keys: score, band, details, issues, counters, fixed_path
    """
    print(f"Running PDF accessibility check for: {path}")

    pdf = pikepdf.Pdf.open(path)
    doc = fitz.open(path)

    counters = {
        "figures":       0,
        "missing_alt":   0,
        "decorative":    0,
        "tables":        0,
        "table_headers": 0,
    }

    issues = []

    # ----------------------------------
    # TAGGING
    # ----------------------------------
    tagging = 0
    if not pdf.Root.get("/StructTreeRoot"):
        tagging = 1
        issues.append(("PDF not tagged", "Document"))
    else:
        walk_struct(pdf.Root["/StructTreeRoot"], counters)

    # ----------------------------------
    # ALT TEXT
    # ----------------------------------
    missing_alt = counters["missing_alt"]
    if missing_alt:
        issues.append((f"{missing_alt} images missing alt text", "Document"))

    # ----------------------------------
    # CONTRAST
    # ----------------------------------
    contrast = detect_contrast(doc)
    if contrast:
        issues.append((f"{contrast} contrast issues", "Document"))

    # ----------------------------------
    # LINKS  (pass pikepdf object so /Contents is also checked)
    # ----------------------------------
    links = detect_links(doc, pdf=pdf)
    if links:
        issues.append((f"{links} links missing text", "Document"))

    # ----------------------------------
    # TITLE
    # ----------------------------------
    title = 0 if pdf.docinfo.get("/Title") else 1
    if title:
        issues.append(("Missing title", "Document"))

    # ----------------------------------
    # LANGUAGE
    # ----------------------------------
    language = 0 if pdf.Root.get("/Lang") else 1
    if language:
        issues.append(("Missing language", "Document"))

    # ----------------------------------
    # TABLE HEADERS
    # ----------------------------------
    table_issues = max(0, counters["tables"] - counters["table_headers"])
    if table_issues:
        issues.append(("Tables missing headers", "Document"))

    # ----------------------------------
    # SCORING
    # ----------------------------------
    detail_scores = {
        "Alternative Text":    score_lookup("alternative text",   missing_alt),
        "Decorative Images":   score_lookup("decorative image",   counters["decorative"]),
        "Tables With Headers": score_lookup("tables with headers", table_issues),
        "Color Contrast":      score_lookup("color contrast",     contrast),
        "Tagging Pdf":         score_lookup("tagging pdf",        tagging),
        "Title":               score_lookup("title",              title),
        "Language":            score_lookup("language",           language),
        "Links":               score_lookup("links",              links),
    }

    final = min(detail_scores.values())
    band  = get_ally_band(final)

    # ----------------------------------
    # OPTIONAL FIX
    # ----------------------------------
    fixed_path = None
    if apply_fix:
        from fixers.pdf_fixer import fix_pdf
        fixed_path = fix_pdf(path)

    doc.close()
    pdf.close()

    return {
        "score":      final,
        "band":       band,
        "details":    detail_scores,
        "issues":     issues,
        "counters":   counters,
        "fixed_path": fixed_path,
    }
