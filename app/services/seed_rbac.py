from sqlalchemy.orm import Session

from app.models.rbac import PermissionORM, RoleORM

MODULES = [
    "crm",
    "ventes",
    "achats",
    "stocks",
    "tresorerie",
    "comptabilite",
    "projets",
    "facturation",
    "logistique",
    "rh",
    "marketing",
    "support",
    "production",
    "documents",
]


def _flags(**kwargs) -> dict:
    data = {
        "can_read": False,
        "can_create": False,
        "can_update": False,
        "can_delete": False,
        "can_validate": False,
        "can_export": False,
    }
    data.update(kwargs)
    return data


def _full() -> dict:
    return _flags(
        can_read=True,
        can_create=True,
        can_update=True,
        can_delete=True,
        can_validate=True,
        can_export=True,
    )


def _operate() -> dict:
    return _flags(can_read=True, can_create=True, can_update=True, can_validate=True, can_export=True)


def _read() -> dict:
    return _flags(can_read=True)


def _modules(flags: dict, names: list[str]) -> list[dict]:
    return [{"module_name": name, **flags} for name in names]


# Les noms reprennent le catalogue déjà utilisé par l'écran Équipe,
# complété par les profils métier du cahier des charges.
DEFAULT_ROLES = [
    {
        "name": "Administrateur d'entreprise",
        "description": "Responsable de l'environnement, de l'équipe, des rôles et des paramètres de l'entreprise",
        "permissions": _modules(_full(), MODULES),
    },
    {
        "name": "Administrateur Adjoint",
        "description": "Administration déléguée de l'entreprise",
        "permissions": _modules(_full(), MODULES),
    },
    {
        "name": "Responsable Commercial",
        "description": "Clients, prospects, devis, commandes, ventes et suivi commercial",
        "permissions": [
            {"module_name": "ventes", **_operate()},
            {"module_name": "crm", **_operate()},
            {"module_name": "facturation", **_operate()},
            {"module_name": "stocks", **_read()},
        ],
    },
    {
        "name": "Responsable des Achats",
        "description": "Fournisseurs, demandes d'achat, commandes et réceptions",
        "permissions": [
            {"module_name": "achats", **_full()},
            {"module_name": "stocks", **_read()},
            {"module_name": "documents", **_read()},
        ],
    },
    {
        "name": "Responsable des Stocks et Magasinier",
        "description": "Produits, entrées, sorties, inventaires, mouvements et livraisons",
        "permissions": [
            {"module_name": "stocks", **_full()},
            {"module_name": "logistique", **_operate()},
        ],
    },
    {
        "name": "Responsable Financier et Comptable",
        "description": "Facturation, paiements, trésorerie et rapports financiers",
        "permissions": [
            {"module_name": "comptabilite", **_full()},
            {"module_name": "tresorerie", **_full()},
            {"module_name": "facturation", **_operate()},
        ],
    },
    {
        "name": "Ressources Humaines",
        "description": "Employés, dossiers, absences, congés et documents RH",
        "permissions": [
            {"module_name": "rh", **_full()},
            {"module_name": "documents", **_operate()},
        ],
    },
    {
        "name": "Marketing",
        "description": "Campagnes, promotions, offres et indicateurs",
        "permissions": [
            {"module_name": "marketing", **_full()},
            {"module_name": "crm", **_read()},
        ],
    },
    {
        "name": "Support / Service Client",
        "description": "Tickets, demandes, réclamations et historique des interventions",
        "permissions": [
            {"module_name": "support", **_full()},
            {"module_name": "crm", **_operate()},
        ],
    },
    {
        "name": "Production",
        "description": "Ordres de production, matières, ressources, quantités et coûts",
        "permissions": [
            {"module_name": "production", **_full()},
            {"module_name": "stocks", **_read()},
        ],
    },
    {
        "name": "Collaborateur Standard",
        "description": "Consultation limitée de l'activité de l'entreprise",
        "permissions": [
            {"module_name": "crm", **_read()},
            {"module_name": "ventes", **_read()},
            {"module_name": "documents", **_read()},
        ],
    },
    {
        "name": "Client Partenaire",
        "description": "Portail externe: consultation des documents commerciaux",
        "permissions": [
            {"module_name": "facturation", **_read()},
            {"module_name": "documents", **_read()},
        ],
    },
    {
        "name": "Fournisseur Agréé",
        "description": "Portail externe: consultation des achats",
        "permissions": [
            {"module_name": "achats", **_read()},
            {"module_name": "documents", **_read()},
        ],
    },
]


def seed_tenant_rbac(db: Session, tenant_id: str = "default") -> RoleORM:
    """Crée les rôles métier manquants. Un rôle déjà présent n'est pas réécrit."""
    commercial_role = None
    for spec in DEFAULT_ROLES:
        role = db.query(RoleORM).filter_by(tenant_id=tenant_id, name=spec["name"]).first()
        if role is None:
            role = RoleORM(
                tenant_id=tenant_id,
                name=spec["name"],
                description=spec["description"],
                is_preconfigured=True,
            )
            db.add(role)
            db.flush()
            db.add_all(
                PermissionORM(role_id=role.id, **permission)
                for permission in spec["permissions"]
            )
        if spec["name"] == "Responsable Commercial":
            commercial_role = role
    db.commit()
    if commercial_role is not None:
        db.refresh(commercial_role)
    return commercial_role
