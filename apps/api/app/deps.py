import re

from fastapi import HTTPException, Request

from app.config import get_settings
from app.services.accounts import CurrentUser, user_from_token

COOKIE = "cn_session"
CSRF_HEADER = "x-codigo-naranja"
_IP = re.compile(r"^[A-Za-z0-9:.]{1,64}$")


def client_ip(request: Request) -> str:
    if get_settings().trust_proxy:
        forwarded = request.headers.get("x-real-ip", "").strip()
        if _IP.fullmatch(forwarded):
            return forwarded
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def require_csrf(request: Request) -> None:
    if request.headers.get(CSRF_HEADER) != "1":
        raise HTTPException(status_code=403, detail="Solicitud rechazada.")


def current_user(request: Request) -> CurrentUser | None:
    return user_from_token(request.cookies.get(COOKIE))


def require_admin(request: Request) -> CurrentUser:
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Inicia sesión para continuar.")
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Esta cuenta no tiene permisos de administración.")
    return user
