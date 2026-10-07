from sqlalchemy.orm import Session
from app.models.rbac import RoleORM, PermissionORM

ACTIONS = ["read", "create", "update", "delete", "validate", "export"]
MODULES = ["crm", "ventes", "achats", "stocks", "tresorerie", "comptabilite", "projets"]

def seed_tenant_rbac(db: Session):
    # 1. Génération de la matrice de permissions
    permissions_map = {}
    for mod in MODULES:
        for act in ACTIONS:
            code = f"{mod}:{act}"
            perm = db.query(PermissionORM).filter_by(code=code).first()
            if not perm:
                perm = PermissionORM(code=code, module=mod, action=act)
                db.add(perm)
            permissions_map[code] = perm
    
    db.commit()

    # 2. Rôle Préconfiguré : Responsable Commercial
    commercial_role = db.query(RoleORM).filter_by(name="Responsable Commercial").first()
    if not commercial_role:
        commercial_role = RoleORM(name="Responsable Commercial", is_system=True)
        # Permissions attribuées : Ventes + CRM (Read/Create/Update/Export) + Stock (Read)
        commercial_perms = [
            permissions_map[f"ventes:{a}"] for a in ["read", "create", "update", "export"]
        ] + [
            permissions_map[f"crm:{a}"] for a in ["read", "create", "update", "export"]
        ] + [
            permissions_map["stocks:read"]
        ]
        commercial_role.permissions = commercial_perms
        db.add(commercial_role)

    db.commit()