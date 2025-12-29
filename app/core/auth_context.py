from fastapi import Request, HTTPException

def get_current_token(request: Request) -> str:
    # cookie (WEB)
    token = request.cookies.get("access_token")

    # Authorization header (MOBİL)
    if not token:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.split(" ")[1]

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return token
