from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import User
from app.security import verify_password, hash_password

router = APIRouter()


@router.get("/login")
def login_page(request: Request):
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request}
    )


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.scalar(
        select(User).where(
            User.username == username,
            User.active == True
        )
    )

    ok = False
    legacy = False

    if user:
        ok, legacy = verify_password(password, user.password_hash)

    if not ok:
        return request.app.state.templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "request": request,
                "error": "Invalid username or password."
            },
            status_code=401
        )

    # Upgrade legacy password hash if necessary
    if legacy:
        user.password_hash = hash_password(password)
        db.commit()

    # Store authenticated user information in session
    request.session["user_id"] = user.user_id
    request.session["full_name"] = user.full_name
    request.session["role"] = user.role

    return RedirectResponse("/", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)