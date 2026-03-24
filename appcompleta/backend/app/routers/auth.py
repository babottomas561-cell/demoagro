from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import bcrypt
from jose import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.config import settings
from app.models.usuario import Usuario

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    nombre: str
    rol: str
    empresa_id: Optional[int] = None


def verify_password(plain: str, hashed: str) -> bool:
    try:
        if hashed.startswith("$2"):
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


@router.post("/auth/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Usuario).where(Usuario.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.activo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")

    token = create_access_token({"sub": str(user.id), "rol": user.rol})
    return Token(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        nombre=user.nombre,
        rol=user.rol,
        empresa_id=user.empresa_id,
    )
