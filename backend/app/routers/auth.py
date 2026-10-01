from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import create_token, current_user, hash_password, verify_password
from ..database import get_db
from ..models import User
from ..schemas import LoginIn, PasswordChange, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    # Même message que le compte existe ou non : ne pas révéler les emails inscrits
    if user is None or not user.active or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    return TokenOut(access_token=create_token(user), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.post("/password", status_code=204)
def change_password(data: PasswordChange, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return Response(status_code=204)
