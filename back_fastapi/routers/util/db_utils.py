from fastapi import HTTPException, status
from db.db_conn import get_db_connection, close_db_connection

# def get_user_id_by_nickname(nickname: str) -> int:
#     """
#     닉네임으로 사용자 ID를 가져오는 함수
#     :param nickname: 사용자 닉네임
#     :return: 사용자 ID (정수형)
#     """
#     conn = get_db_connection()
#     cur = conn.cursor()
#     try:
#         cur.execute("SELECT uid FROM users WHERE nickname = %s", (nickname,))
#         user_row = cur.fetchone()
#         if not user_row:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="User not found."
#             )
#         return user_row[0]
#     except Exception as e:
#         print(f"Error retrieving user ID: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to retrieve user ID."
#         )
#     finally:
#         cur.close()
#         close_db_connection(conn)
