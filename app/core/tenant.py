from fastapi import Header, HTTPException

def get_current_tenant(x_tenant_id: str = Header(...)):
    """
    Cette fonction regarde l'en-tête de la requête pour trouver
    l'identifiant de l'entreprise (tenant).
    Si personne ne l'a envoyé, on refuse la requête.
    """
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID manquant")
    return x_tenant_id