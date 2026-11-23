from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.config import get_settings
from app.deps import COOKIE, client_ip, current_user, require_csrf
from app.rate_limit import allow
from app.schemas import AuthResponse, LoginBody
from app.security import password_problem
from app.services.accounts import authenticate, create_session, delete_session

router = APIRouter(prefix="/auth", tags=["auth"])


def _cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=COOKIE,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=max(1, min(settings.session_hours, 24 * 30)) * 3600,
        path="/",
    )


@router.post("/login", response_model=AuthResponse)
def login(body: LoginBody, request: Request, response: Response, _: None = Depends(require_csrf)) -> dict:
    if password_problem(body.password):
        raise HTTPException(status_code=401, detail="No se pudo iniciar sesión. Revisa tus credenciales.")
    if not allow(f"login:{client_ip(request)}"):
        raise HTTPException(status_code=429, detail="Demasiados intentos. Espera unos minutos.")
    status, user = authenticate(body.email, body.password)
    if status == "forbidden":
        raise HTTPException(status_code=403, detail="Esta cuenta no tiene permisos de administración.")
    if user is None:
        raise HTTPException(status_code=401, detail="No se pudo iniciar sesión. Revisa tus credenciales.")
    _cookie(response, create_session(user.id))
    return {"user": user.public()}


@router.post("/logout", status_code=204)
def logout(request: Request, _: None = Depends(require_csrf)) -> Response:
    delete_session(request.cookies.get(COOKIE))
    response = Response(status_code=204)
    response.delete_cookie(COOKIE, path="/", samesite="lax", secure=get_settings().cookie_secure, httponly=True)
    return response


@router.get("/me", response_model=AuthResponse)
def me(request: Request) -> dict:
    user = current_user(request)
    return {"user": None if user is None else user.public()}
