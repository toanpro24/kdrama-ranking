import os

import firebase_admin
from firebase_admin import auth, credentials
from fastapi import Header, HTTPException

# Initialize Firebase Admin SDK from environment variables
_project_id = os.getenv("FIREBASE_PROJECT_ID", "")
_client_email = os.getenv("FIREBASE_CLIENT_EMAIL", "")
_private_key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n")

if _project_id and _client_email and _private_key:
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": _project_id,
        "client_email": _client_email,
        "private_key": _private_key,
    })
    firebase_admin.initialize_app(cred)
else:
    print("WARNING: Firebase credentials not configured — auth will be disabled")


def get_current_user(authorization: str = Header(default="")) -> dict | None:
    """FastAPI dependency: extracts and verifies Firebase ID token.

    Returns dict with uid, email, name, picture — or None if no token (guest mode).
    """
    if not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    if not firebase_admin._apps:
        return None
    try:
        decoded = auth.verify_id_token(token)
        return {
            "uid": decoded["uid"],
            "email": decoded.get("email", ""),
            "name": decoded.get("name", ""),
            "picture": decoded.get("picture", ""),
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_user(authorization: str = Header(default="")) -> dict:
    """FastAPI dependency: same as get_current_user but rejects guests."""
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
