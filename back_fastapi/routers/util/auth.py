import jwt
from fastapi import HTTPException, status

# JWT 설정 상수
SECRET_KEY = "JeonKinSong"  # 실제 시크릿 키로 교체
ALGORITHM = "HS256"

def verify_token(token: str):
    """
    JWT 토큰을 검증하는 함수
    :param token: 검증할 JWT 토큰 (문자열 형식)
    :return: 검증된 토큰의 페이로드 (딕셔너리 형식)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # print(payload)
        return payload
    except jwt.exceptions.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.exceptions.JWTError:
        raise credentials_exception

def extract_user_id_from_token(token: str) -> str:
    """
    JWT 토큰에서 사용자 ID를 추출하는 함수
    :param token: 검증할 JWT 토큰 (문자열 형식)
    :return: 사용자 ID (문자열형)
    """
    payload = verify_token(token)
    user_id = payload.get("uid")
    if not isinstance(user_id, int):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token payload: user ID should be a string."
        )
    return user_id
