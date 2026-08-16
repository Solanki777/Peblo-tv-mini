from fastapi import Depends, HTTPException, status

from app.api.auth import get_current_user
from app.models.user import User


def require_editor(current_user: User = Depends(get_current_user)) -> User:
    """Any authenticated user - editor or admin - may do CRUD.

    FIXED: previously nothing in shows/seasons/episodes/artworks depended
    on auth at all, so those endpoints were reachable without a token by
    anyone who could reach the API. This is the dependency the CRUD routers
    now use; it just requires a valid token, since both roles are allowed
    to create/edit/delete content per the brief ("editor (CRUD) vs admin
    (CRUD + publish)"). Named separately from `get_current_user` so the
    intent reads clearly at each route: "this needs an editor" vs "this
    needs an admin".
    """
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Only admins may publish, or see what's blocking a publish."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires an admin role.",
        )
    return current_user