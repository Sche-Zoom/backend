# database.py
from dotenv import load_dotenv
import os
import psycopg2
from psycopg2 import Error


# load .env
load_dotenv()


DB_ID = os.environ.get('db_id')
DB_PW = os.environ.get('db_pw')
DB_HOST = os.environ.get('db_host')
PORT = os.environ.get('port')
DB_DATABASE = os.environ.get('db_database')


import psycopg2

# PostgreSQL 데이터베이스에 연결
conn = psycopg2.connect(
    host=DB_HOST,
    database=DB_DATABASE,
    user=DB_ID,
    password=DB_PW
)

# 커서 생성
cur = conn.cursor()

# # 쿼리 실행 예시
# cur.execute("SELECT * FROM your_table")
# rows = cur.fetchall()

# # 결과 출력
# for row in rows:
#     print(row)

# 연결 및 커서 닫기
cur.close()
conn.close()