# pptx_checker.py

import os
from pptx import Presentation

from fixers.pptx_fixer import (
    process_slides,
    fix_language,
    AllyScores,
)


def run_pptx_accessibility_check(file_path, fix=False):
    """
    Run an accessibility check (and optionally fix) a .pptx file.

    Returns a dict with keys:
        score      – int  (0-100)
        band       – str  ("Dark Green" | "Light Green" | "Yellow" | "Red")
        details    – dict of per-category scores
        issues     – list of (description, location) tuples
        fixed_path – str path of saved fixed file, or None if fix=False
    """
    print(f"Running PPTX accessibility check for: {file_path}")

    prs    = Presentation(file_path)
    issues = []

    # -------- LANGUAGE --------
    lang             = prs.core_properties.language
    language_missing = 0 if lang else 1
    if language_missing:
        issues.append(("Presentation language not set", "Presentation"))

    # -------- SLIDE PROCESSING --------
    # process_slides returns a 6-tuple (added total_text_runs)
    (
        missing_alt,
        decorative,
        contrast,
        total_text_runs,
        table_violations,
        slide_issues,
    ) = process_slides(prs, apply_fix=fix)
    issues.extend(slide_issues)

    # -------- APPLY REMAINING FIXES & SAVE --------
    fixed_path = None
    if fix:
        fix_language(prs, issues)

        base, ext = os.path.splitext(file_path)
        # Avoid appending _fixed twice if the file is already a fixed copy
        fixed_path = file_path if base.endswith("_fixed") else f"{base}_fixed{ext}"

        prs.save(fixed_path)
        print(f"Fixed file saved: {fixed_path}")

    # -------- SCORING --------
    scores = AllyScores.compute(
        missing_alt      = missing_alt,
        decorative       = decorative,
        language_missing = language_missing,
        headings_missing = 0,               # PPTX has no semantic heading elements
        tables_missing   = table_violations,
        contrast         = contrast,
        total_text_runs  = total_text_runs,
        lists            = 0,
        links            = 0,
    )

    # Strip the aggregate keys so 'details' contains only per-category scores
    details = {k: v for k, v in scores.items() if k not in ("final", "band")}

    return {
        "score":      scores["final"],
        "band":       scores["band"],
        "details":    details,
        "issues":     issues,
        "fixed_path": fixed_path,
    }
