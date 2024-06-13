

from datetime import datetime, timedelta, timezone
import jwt
from fastapi import HTTPException, status
from routers.util.db_conn import get_db_connection, close_db_connection

# JWT 설정 상수
SECRET_KEY = "JeonKinSong"  # 실제 시크릿 키로 교체
ALGORITHM = "HS256"  # 사용하고자 하는 알고리즘으로 교체
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 토큰 만료 시간 (분)

def create_access_token(data: dict):
    """
    JWT 액세스 토큰을 생성하는 함수
    :param data: 토큰에 포함할 사용자 데이터 (딕셔너리 형식)
    :return: 생성된 JWT 토큰 (문자열 형식)
    """
    to_encode = data.copy()  # 원본 데이터를 복사
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)  # 만료 시간 설정
    to_encode.update({"exp": expire})  # 만료 시간을 데이터에 추가
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)  # JWT 토큰 생성
    save_token_to_db(encoded_jwt, data["uid"], expire)  # PostgreSQL에 토큰 저장
    return encoded_jwt

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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # JWT 토큰 디코딩 및 페이로드 추출
        if is_token_blacklisted(token):  # 토큰이 블랙리스트에 있는지 확인
            raise credentials_exception
        return payload
    except jwt.exceptions.ExpiredSignatureError:  # 토큰이 만료된 경우
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.exceptions.JWTError:  # 기타 JWT 오류
        raise credentials_exception

def save_token_to_db(token: str, uid: int, expires_at: datetime):
    """
    PostgreSQL 데이터베이스에 토큰을 저장하는 함수
    :param token: 저장할 JWT 토큰 (문자열 형식)
    :param uid: 사용자 ID (정수형)
    :param expires_at: 토큰 만료 시간 (datetime 형식)
    """
    conn = get_db_connection()  # 데이터베이스 연결
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO test_redis_jwt (token, uid, expires_at) VALUES (%s, %s, %s)",
            (token, uid, expires_at)
        )  # 토큰 정보 삽입 쿼리 실행
        conn.commit()  # 트랜잭션 커밋
    except Exception as e:  # 예외 발생 시
        conn.rollback()  # 트랜잭션 롤백
        print(f"Error saving token to db: {e}")
    finally:
        cur.close()  # 커서 닫기
        close_db_connection(conn)  # 연결 풀에 반환

def is_token_blacklisted(token: str):
    """
    토큰이 블랙리스트에 있는지 확인하는 함수
    :param token: 확인할 JWT 토큰 (문자열 형식)
    :return: 블랙리스트에 있으면 True, 아니면 False
    """
    conn = get_db_connection()  # 데이터베이스 연결
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT 1 FROM blacklisted_tokens WHERE token = %s",
            (token,)
        )  # 블랙리스트 테이블에서 토큰 존재 확인 쿼리 실행
        result = cur.fetchone()  # 결과 가져오기
        return result is not None  # 결과가 있으면 블랙리스트에 있음
    finally:
        cur.close()  # 커서 닫기
        close_db_connection(conn)  # 연결 풀에 반환

def invalidate_token(token: str):
    """
    토큰을 블랙리스트에 추가하여 무효화하는 함수
    :param token: 무효화할 JWT 토큰 (문자열 형식)
    
    
    블랙리스트에 JWT가 들어가야 하는 예시
    1. 로그아웃 시
    상황: 사용자가 웹 애플리케이션에서 로그아웃 버튼을 클릭합니다.
    동작: 서버는 해당 사용자의 JWT를 블랙리스트에 추가합니다. 이후 해당 JWT로 인증 요청이 들어오면, 서버는 이를 무효한 토큰으로 간주합니다.
    
    2. 강제 로그아웃 시
    상황: 관리자가 보안 문제를 발견하고 특정 사용자의 세션을 강제로 종료해야 합니다.
    동작: 관리자는 해당 사용자의 JWT를 블랙리스트에 추가합니다. 사용자는 다시 로그인해야 하며, 기존의 JWT는 더 이상 유효하지 않습니다.
    
    3. 토큰 도난 시
    상황: 사용자가 자신의 계정 활동 내역을 확인하고, 의심스러운 로그인 활동을 발견합니다. 이는 JWT가 도난당했을 가능성을 시사합니다.
    동작: 사용자는 관리자에게 보고하고, 관리자는 해당 JWT를 블랙리스트에 추가합니다. 도난된 토큰을 가진 공격자는 더 이상 시스템에 접근할 수 없습니다.
    
    4. 비밀번호 변경 시
    상황: 사용자가 보안을 강화하기 위해 비밀번호를 변경합니다.
    동작: 서버는 비밀번호가 변경된 사용자와 관련된 기존의 모든 JWT를 블랙리스트에 추가합니다. 사용자는 비밀번호 변경 후 새로 로그인해야 하며, 이전의 JWT는 무효화됩니다.
    
    """
    conn = get_db_connection()  # 데이터베이스 연결
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO blacklisted_tokens (token) VALUES (%s)", 
            (token,)
        )  # 토큰을 블랙리스트 테이블에 추가
        conn.commit()  # 트랜잭션 커밋
    except Exception as e:  # 예외 발생 시
        conn.rollback()  # 트랜잭션 롤백
        print(f"Error invalidating token: {e}")
    finally:
        cur.close()  # 커서 닫기
        close_db_connection(conn)  # 연결 풀에 반환