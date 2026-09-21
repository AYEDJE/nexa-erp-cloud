from fastapi import FastAPI, Depends

from app.core.tenant import get_current_tenant
from app.core.database import Base, engine
from app.api import products

# Crée les tables dans la base 
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ERP Cloud API", version="0.1.0")

app.include_router(products.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/whoami")
def whoami(tenant_id: str = Depends(get_current_tenant)):
    return {"message": f"Vous appartenez à l'entreprise : {tenant_id}"}