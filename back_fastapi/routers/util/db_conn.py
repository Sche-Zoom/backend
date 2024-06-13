from dotenv import load_dotenv
import os
import psycopg2
from psycopg2 import pool, OperationalError
from fastapi import HTTPException, status


# Load .env
load_dotenv()

DB_ID = os.environ.get('db_id')
DB_PW = os.environ.get('db_pw')
DB_HOST = os.environ.get('db_host')
PORT = os.environ.get('port')
DB_DATABASE = os.environ.get('db_database')

# PostgreSQL connection pool
connection_pool = pool.SimpleConnectionPool(1, 20,
                                            user=DB_ID,
                                            password=DB_PW,
                                            host=DB_HOST,
                                            port=PORT,
                                            database=DB_DATABASE)


def get_db_connection():
    try:
        conn = connection_pool.getconn()
        return conn
    except psycopg2.pool.PoolError as e:
        # Connection pool exhausted or other operational errors
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The server is busy. Please try again later.",
        ) from e  # psycopg2 예외를 함께 던집니다.

def close_db_connection(conn):
    connection_pool.putconn(conn)
    """
    연결 반환 (close_db_connection):

    작업이 완료되면 close_db_connection 함수를 호출하여 연결을 반환합니다.
    이때 실제로 연결이 닫히지 않고, 연결 풀이 연결을 재사용할 수 있도록 준비 상태로 돌려놓습니다.
    connection_pool.putconn(conn)을 호출하여 연결을 반환합니다.
    """

# 예외 처리 및 연결 반환을 보장하기 위해 context manager 사용
async def handle_database_operation():
    conn = None
    try:
        conn = get_db_connection()
        # Perform database operations using `conn`
        # 예: cursor를 사용하여 쿼리 실행 등

    finally:
        if conn:
            close_db_connection(conn)