import hashlib
from datetime import datetime
import base64
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from routers.util.db_conn import get_db_connection
import bcrypt

router = APIRouter()



class UserCreate(BaseModel):
    id : str
    email: str
    nickname: str
    password : str
    
    

class CheckUser(BaseModel):
    check_id : str


@router.post("/")
async def register_user(user: UserCreate):
    """
    새로운 사용자를 등록하는 엔드포인트입니다.
    사용자 정보(이메일, 닉네임, 비밀번호, 프로필)를 받아서 데이터베이스에 저장합니다.
    """
    
    
    # 비밀번호 해싱
    password_hash = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # users 테이블에 사용자 정보 삽입
        cur.execute("INSERT INTO users (email, nickname) VALUES (%s, %s) RETURNING uid", 
                    (user.email, user.nickname))
        
        
        # select uid where email = ' adsf ' 
        uid = cur.fetchone()[0]
        
        # local_auth 테이블에 인증 정보 삽입
        cur.execute("INSERT INTO local_auth (personal_id, password_hash, uid ) VALUES (%s, %s, %s)  ", 
                    (user.id, password_hash, uid))
        
        conn.commit()
        return {"message": "User registered successfully"}
    except Exception as e:
        print(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        cur.close()
        conn.close()
        
        
        
@router.post("/check-username")
async def check_user(check_user: CheckUser):
    """
    사용자 ID의 중복을 확인하는 엔드포인트입니다.
    이미 사용 중인 경우 에러를 반환합니다.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # 데이터베이스에서 해당 사용자 ID가 이미 존재하는지 확인
        cur.execute("SELECT EXISTS (SELECT 1 FROM local_auth WHERE personal_id = %s)", (check_user.check_id,))
        exists = cur.fetchone()[0]
        if exists:
            raise HTTPException(status_code=400, detail="User ID already exists")
        return {"message": "User ID is available"}
    except Exception as e:
        print(f"Error checking user ID: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        cur.close()
        conn.close()