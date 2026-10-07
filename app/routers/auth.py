from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import Token, UserCreate, UserORM, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentification & Sécurité"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(UserORM).filter(UserORM.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec cet e-mail existe déjà.",
        )

    hashed_pwd = get_password_hash(user_in.password)
    new_user = UserORM(
        tenant_id=user_in.tenant_id,
        email=user_in.email,
        hashed_password=hashed_pwd,
        user_type=user_in.user_type,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
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
            detail="Compte utilisateur inactif.",
        )

    jwt_payload = {
        "sub": user.email,
        "tenant_id": user.tenant_id,
        "user_type": user.user_type,
        "user_id": user.id,
    }
    access_token = create_access_token(data=jwt_payload)
    return {"access_token": access_token, "token_type": "bearer"}
