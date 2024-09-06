from datetime import datetime
from fastapi import HTTPException, status
import psycopg2
from db.db_conn import get_db_connection, close_db_connection
from typing import List, Tuple

def parse_iso_date(date_str: str) -> datetime:
    """
    ISO 8601 형식의 날짜 문자열을 datetime 객체로 변환하는 함수
    :param date_str: ISO 8601 형식의 날짜 문자열
    :return: datetime 객체
    """
    try:
        # 'Z'를 UTC 타임존 오프셋으로 변환
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + "+00:00"
        return datetime.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO 8601 format, e.g., '2024-05-10T10:00:00Z'."
        )


def check_color_list(color: str) -> bool:
    """
    명시해놓은 color list에 입력받은 문자열이 있는지 체크 후 True False를 반환하는 함수
    Color list : [ blue, green, yello, purple, orange, mint, lavender, beige, coral ]
    
    Args:
        color (str): - 사용자로부터 입력받아오는 색상
    

    Returns:
        bool: _description_
    """
    color_list = [ 'blue', 'green', 'yello', 'purple', 'orange', 'mint',' lavender', 'beige', 'coral' ]
    
    try :
        if color in color_list :
            return True
        else :
            return False
    except :
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail = "색상을 지정 할 수 없습니다. 명시된 색상을 입력해주세요."
        )


def check_group_tags(uid):
    """
    total_tags에 들어갈 그룹 태그 데이터 추출하는 함수
    1. 로그인 한 유저(uid)가 속한 group에서(TB_community_member) community_schedule_id ( TB_schedule_tag)를 추출해오기
    2. 그룹 태그 id( TB_schedule_tag )를기준으로 tag name(TB_tag) select 
    3. 그룹 별 리스트화하여 return
    """
    return 0



def check_per_tags(uid: int) -> List[Tuple[int, str]]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, title FROM tag WHERE uid = %s AND is_personal = TRUE", (uid,))
        tags = cur.fetchall()
        return tags
    except Exception as e:
        print(f"Error fetching personal tags: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch personal tags."
        )
    finally:
        cur.close()
        close_db_connection(conn)