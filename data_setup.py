"""
data_setup.py - creates the harmless dummy data and safe folder helpers.

company_data/  : sample business files that the monitor watches. Never attacked.
sandbox_data/  : a COPY of company_data. The simulator only ever touches this copy.
"""
import hashlib
import os
import shutil

import config

# Minimal placeholder PDF (just enough bytes to look like a PDF; it is dummy data).
_DUMMY_PDF = (b"%PDF-1.1\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
              b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
              b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 100]>>endobj\n"
              b"trailer<</Root 1 0 R>>\n%%EOF\n")

CORE_FILES = {
    "financial_report.txt": "Quarterly Financial Report (DUMMY DATA)\nRevenue: 1,000,000\nExpenses: 650,000\nProfit: 350,000\n",
    "employee_data.csv": "id,name,department\n1,Asha Rao,Finance\n2,Ravi Kumar,Engineering\n3,Meera Nair,HR\n",
    "customer_report.txt": "Customer Report (DUMMY DATA)\nActive customers: 1,240\nSatisfaction: 92%\n",
}


def ensure_sample_data():
    """Create company_data with 24 harmless files (only if they do not exist yet)."""
    os.makedirs(config.COMPANY_DIR, exist_ok=True)

    def write_text(name, text):
        path = os.path.join(config.COMPANY_DIR, name)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)

    for name, text in CORE_FILES.items():
        write_text(name, text)

    pdf_path = os.path.join(config.COMPANY_DIR, "project_report.pdf")
    if not os.path.exists(pdf_path):
        with open(pdf_path, "wb") as f:
            f.write(_DUMMY_PDF)

    # 20 extra files so a "burst" of activity is easy to see.
    for i in range(1, 9):
        write_text(f"invoice_{i:02d}.txt", f"Invoice #{i:02d} (DUMMY DATA)\nAmount: {i * 1500}\n")
    for i in range(1, 7):
        write_text(f"meeting_notes_{i:02d}.md", f"# Meeting {i:02d} (DUMMY DATA)\n- Discuss roadmap\n")
    for i in range(1, 7):
        write_text(f"export_{i:02d}.csv", f"id,value\n1,{i}\n2,{i * 2}\n")


def is_inside(path, root):
    """True only if `path` is really inside `root` (blocks ../ tricks and symlinks)."""
    try:
        p, r = os.path.realpath(path), os.path.realpath(root)
        return os.path.commonpath([p, r]) == r
    except ValueError:
        return False


def list_files(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)))


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def reset_sandbox(source=None):
    """Delete sandbox_data and refill it with a copy of `source` (default: company_data).
    Safety: we refuse to delete anything that is not the sandbox folder."""
    source = source or config.COMPANY_DIR
    sandbox = os.path.realpath(config.SANDBOX_DIR)
    if os.path.basename(sandbox) != "sandbox_data" or not is_inside(sandbox, config.BASE_DIR):
        raise RuntimeError("Refusing to reset: sandbox path looks unsafe.")
    if os.path.isdir(sandbox):
        shutil.rmtree(sandbox)
    shutil.copytree(source, sandbox)
