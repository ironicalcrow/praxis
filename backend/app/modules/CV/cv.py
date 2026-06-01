from pathlib import Path
import fitz
import docx
import easyocr
from app.modules.CV.service import extract_resume_with_grok

ocr_reader= easyocr.Reader(["en"],gpu=False)

def extract_text_from_pdf(file_path:str):
    text= ""
    pdf= fitz.open(file_path)
    for page in pdf:
        text+= page.get_text()

    return text

def extract_text_from_docx(file_path:str):
    doc= docx.Document(file_path)
    return "\n".join([paragraph.text for paragraph in doc.paragraphs])

def extract_text_from_image(file_path:str):
    text= ocr_reader.readtext(file_path,detail=0)
    return "\n".join(text)

def text_extractor(file_path:str):
    extension= Path(file_path).suffix.lower()

    if extension==".pdf":
        return extract_text_from_pdf(file_path)
    
    elif extension == ".docx":
        return extract_text_from_docx(file_path)
    
    elif extension in [".png",".jpg",".jpeg"]:
        return extract_text_from_image(file_path)
    
    else:
        return ValueError("Unsupported CV Format")
    
