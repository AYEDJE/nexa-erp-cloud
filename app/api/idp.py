from io import BytesIO
from pathlib import Path

from docx import Document
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pypdf import PdfReader

from app.core.tenant import get_current_tenant_id
from app.services.ocr_service import extract_document_data_from_text

router = APIRouter(prefix="/idp", tags=["Traitement documentaire"])


MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx", ".png", ".jpg", ".jpeg"}


def extract_text(filename: str, content: bytes) -> str:
    extension = Path(filename).suffix.lower()

    if extension == ".txt":
        return content.decode("utf-8", errors="replace")

    if extension == ".docx":
        document = Document(BytesIO(content))
        paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
        table_text = [
            " | ".join(cell.text.strip() for cell in row.cells)
            for table in document.tables
            for row in table.rows
        ]
        return "\n".join(paragraphs + table_text)

    if extension == ".pdf":
        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if extension in {".png", ".jpg", ".jpeg"}:
        try:
            from PIL import Image
            import pytesseract
        except ImportError as exc:
            raise HTTPException(
                status_code=501,
                detail="Installez Pillow et pytesseract pour traiter les images."
            ) from exc

        image = Image.open(BytesIO(content))
        return pytesseract.image_to_string(image, lang="fra+eng+ara")

    raise HTTPException(status_code=415, detail="Format de fichier non accepté.")


@router.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_current_tenant_id),
):
    filename = file.filename or ""
    if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Format de fichier non accepté.")

    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux.")

    raw_text = extract_text(filename, content)
    if not raw_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Aucun texte extrait. Le PDF est peut-être un scan sans OCR."
        )

    result = extract_document_data_from_text(raw_text)
    return {
        "tenant_id": tenant_id,
        "filename": filename,
        "review_required": True,
        "extracted_data": result,
    }