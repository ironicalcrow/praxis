from pathlib import Path
import fitz
import docx
import easyocr
from app.modules.CV.service import extract_resume_with_grok

_ocr_reader = None

def _get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        _ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _ocr_reader

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
    text= _get_ocr_reader().readtext(file_path,detail=0)
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
    
def text_cleaner(text:str):
    text= text.replace("\x00", " ")
    text= " ".join(text.split())
    return text

async def resume_parser(file_path: str):
    text_extraction= text_extractor(file_path)
    cleaned_text= text_cleaner(text_extraction)
    parsed_resume= await extract_resume_with_grok(cleaned_text)
    
    return parsed_resume
