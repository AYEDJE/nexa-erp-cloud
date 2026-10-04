from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import UserORM, UserCreate, UserResponse, Token, UserType

from app.core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(
    prefix="/auth",
    tags=["Authentification & Sécurité"]
)

# 1. ROUTE D'INSCRIPTION (/auth/register)

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Inscrit un nouvel utilisateur rattaché à son entreprise (tenant_id)
    et à son profil d'acteur (SuperAdmin, Admin, Staff, External).
    """
    # Vérifier si l'utilisateur existe déjà
    existing_user = db.query(UserORM).filter(UserORM.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec cet e-mail existe déjà."
        )

    # Hachage sécurisé du mot de passe
    hashed_pwd = get_password_hash(user_in.password)

    # Création de l'entité utilisateur
    new_user = UserORM(
        tenant_id=user_in.tenant_id,
        email=user_in.email,
        hashed_password=hashed_pwd,
        user_type=user_in.user_type
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

# 2. ROUTE DE CONNEXION (/auth/login)

@router.post("/login", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Vérifie les identifiants et délivre un jeton JWT contenant 
    l'email, le tenant_id et le user_type de l'utilisateur.
    """
    # Recherche de l'utilisateur par e-mail
    user = db.query(UserORM).filter(UserORM.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Compte utilisateur inactif."
        )

    # Construction de la charge utile (payload) du jeton JWT
    jwt_payload = {
        "sub": user.email,
        "tenant_id": user.tenant_id,
        "user_type": user.user_type,
        "user_id": user.id
    }

    # Génération du jeton signé
    access_token = create_access_token(data={"sub": user.email})

    return {"access_token": access_token, "token_type": "bearer"}