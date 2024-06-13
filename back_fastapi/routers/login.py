from fastapi import APIRouter, HTTPException, Depends, status  # 여기에 status 추가
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from routers.util.db_conn import get_db_connection, close_db_connection
from routers.util.jwt import create_access_token, verify_token, invalidate_token  
from bcrypt import hashpw, checkpw
import bcrypt

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

@router.post("/")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user["username"], "uid": user["uid"]})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    try:
        invalidate_token(token)
        return {"msg": "Successfully logged out"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while logging out"
        )

def authenticate_user(username: str, password: str):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT u.uid, u.email, la.password_hash FROM users u JOIN local_auth la ON u.uid = la.uid WHERE la.personal_id = %s", (username,))
        user = cur.fetchone()
        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            return {"uid": user[0], "username": user[1]}
        else:
            return None
    except Exception as e:
        print(f"Error authenticating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while authenticating the user.",
        ) from e
    finally:
        cur.close()
        close_db_connection(conn)