import os

from docx_checker import check_docx
from pptx_checker import check_pptx
from pdf_checker import check_pdf
from fixers.pdf_fixer import fix_pdf




def detect_file_type(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    return ext.replace(".", "")



def run_accessibility_check(file_path, fix=False):
    if file_path.lower().endswith(".docx"):
        return check_docx(file_path, apply_fix=fix)

    if file_path.lower().endswith(".pdf"):
        result = check_pdf(file_path)
        if fix:
            fix_pdf(file_path, result["issues"], result["counters"])
        return result
    if file_path.lower().endswith(".pptx"):
        return check_pptx(file_path, apply_fix=fix)


   
    else:
        print("Unsupported file type")
        return None
