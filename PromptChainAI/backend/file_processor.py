import os
import json
import zipfile
import tempfile
import pandas as pd
import docx2txt
import pdfplumber
import pytesseract
from PIL import Image
from faster_whisper import WhisperModel
from bs4 import BeautifulSoup  # ✅ Added for .html parsing

# ✅ Prevent Pandas DtypeWarning for mixed columns
pd.options.mode.chained_assignment = None
import warnings
warnings.simplefilter(action='ignore', category=pd.errors.DtypeWarning)

# Load Whisper model only once
whisper_model = WhisperModel("base", device="cpu")

def extract_text_from_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()

    try:
        if ext == ".zip":
            return extract_from_zip(filepath)

        elif ext == ".txt":
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()

        elif ext == ".json":
            with open(filepath, "r", encoding="utf-8") as f:
                return json.dumps(json.load(f), indent=2)

        elif ext == ".csv":
            df = pd.read_csv(filepath, low_memory=False)
            return df.to_string(index=False)

        elif ext in [".xls", ".xlsx"]:
            excel_file = pd.ExcelFile(filepath)
            text = ""
            for sheet in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet)
                text += f"📄 Sheet: {sheet}\n{df.to_string(index=False)}\n\n"
            return text.strip()

        elif ext == ".docx":
            return docx2txt.process(filepath)

        elif ext == ".pdf":
            text = ""
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text if text.strip() else "(No extractable text found in PDF. It might be scanned or image-based.)"

        elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
            try:
                image = Image.open(filepath)
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                return pytesseract.image_to_string(image)
            except Exception as e:
                return f"(OCR failed: {str(e)})"

        elif ext in [".mp3", ".wav", ".m4a", ".ogg", ".webm"]:
            try:
                segments, _ = whisper_model.transcribe(filepath)
                return " ".join([seg.text for seg in segments])
            except Exception as e:
                return f"(Audio transcription failed: {str(e)})"

        elif ext in [".html", ".htm"]:
            with open(filepath, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")
                return soup.get_text(separator="\n")

        elif ext == ".wiki":
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()

        else:
            return f"(Unsupported file type: {ext})"

    except Exception as e:
        return f"(Failed to extract {os.path.basename(filepath)}: {str(e)})"

def extract_from_zip(zip_path):
    extracted_texts = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            with tempfile.TemporaryDirectory() as tmpdir:
                z.extractall(tmpdir)
                for name in z.namelist():
                    full_path = os.path.join(tmpdir, name)
                    if os.path.isdir(full_path):
                        continue
                    try:
                        text = extract_text_from_file(full_path)
                        extracted_texts.append(f"📄 {name}:\n{text.strip()}")
                    except Exception as e:
                        extracted_texts.append(f"❌ Failed to extract {name}: {str(e)}")
        return "\n\n".join(extracted_texts)
    except Exception as e:
        return f"(Failed to extract ZIP: {str(e)})"
