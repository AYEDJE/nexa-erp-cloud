# NexaERP

NexaERP is a multi-tenant ERP platform with a FastAPI backend and a web frontend. Existing modules cover invoices, products, purchases, stock, treasury, security and document assistance.

## Run locally

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive API documentation is at `/docs`. Serve `frontend/` from a local web server to use the dashboard and its authenticated API integration.

## AI assistant

The dashboard assistant reuses the authenticated `POST /ai/query` endpoint for text questions. Where supported, browser speech recognition transcribes French, English or Arabic speech locally in the browser; answers can be read aloud with the browser speech synthesis API. Voice recognition and speech output are browser-dependent, and microphone access requires HTTPS or localhost. The microphone audio is not uploaded by this interface. The initial voice command set is intentionally limited to opening allowlisted ERP pages; it does not create, modify or approve ERP records.

## Document extraction

`POST /ocr/extract` currently accepts text already extracted from a document. In addition to existing invoice-oriented fields, the extraction service now retains additional labeled values and simple pipe/tab-delimited tables, detects a basic document category and language, and flags results for human review. This endpoint is not itself an OCR engine and does not yet accept PDF/image/Word uploads. Extracted values must be checked before they are entered into business records.

Run tests with:

```bash
pytest
```

## Next development increments

The voice and document-extraction work is an initial foundation, not the complete feature brief. File-based multilingual OCR/IDP with traceable source positions and validation workflow, a reusable calculation engine, Room Live collaboration, administrator-managed floating buttons, notifications and broader mobile/desktop integration remain follow-up work. Sensitive business actions should require server-side authorization and explicit confirmation.

## Security and configuration

Use secure environment-specific secrets and database configuration. Do not commit credentials or production data. Configure HTTPS, CORS, backups and access policies before production deployment.

## License

No license file is currently defined in the repository; reuse and redistribution terms should be confirmed with the project owner.
