from sqlalchemy.orm import Session
from app.models.rbac import RoleORM, PermissionORM

MODULES = ["crm", "ventes", "achats", "stocks", "tresorerie", "comptabilite", "projets"]


def seed_tenant_rbac(db: Session, tenant_id: str = "default") -> RoleORM:
    commercial_role = (
        db.query(RoleORM)
        .filter_by(tenant_id=tenant_id, name="Responsable Commercial")
        .first()
    )

    if not commercial_role:
        commercial_role = RoleORM(
            tenant_id=tenant_id,
            name="Responsable Commercial",
            description="Gestion des ventes, du CRM et consultation des stocks",
            is_preconfigured=True,
        )
        db.add(commercial_role)
        db.flush()

        perms = [
            PermissionORM(
                role_id=commercial_role.id,
                module_name="ventes",
                can_read=True,
                can_create=True,
                can_update=True,
                can_export=True,
            ),
            PermissionORM(
                role_id=commercial_role.id,
                module_name="crm",
                can_read=True,
                can_create=True,
                can_update=True,
                can_export=True,
            ),
            PermissionORM(
                role_id=commercial_role.id,
                module_name="stocks",
                can_read=True,
            ),
        ]
        db.add_all(perms)
        db.commit()
        db.refresh(commercial_role)

    return commercial_role