from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.session import LoginRequest, UserOut, SessionOut
from app.services.session import create_session, get_session_user, delete_session

router = APIRouter(prefix="/api/session", tags=["session"])


@router.post("/login", response_model=SessionOut)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Accept any non-empty credentials and return a mock user."""
    if not body.username.strip() or not body.password.strip():
        raise HTTPException(
            status_code=422, detail="Username and password must not be empty."
        )

    user = create_session(db, username=body.username.strip())
    response.set_cookie(
        key="session_id",
        value=user["session_id"],
        httponly=True,
        samesite="lax",
        path="/",
    )

    return SessionOut(user=UserOut(**user))


@router.get("/me", response_model=SessionOut)
def me(request: Request, db: Session = Depends(get_db)):
    """Return the current session user from cookie."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = get_session_user(db, session_id=session_id)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired")

    return SessionOut(user=UserOut(**user))


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """Clear the session cookie."""
    session_id = request.cookies.get("session_id")
    if session_id:
        delete_session(db, session_id=session_id)

    response.delete_cookie(key="session_id", path="/")
    return {"ok": True}
