from datetime import datetime, timedelta
from fastapi import HTTPException, status
import psycopg2
from db.db_conn import get_db_connection, close_db_connection
from typing import List, Tuple,Optional, Set
import dateutil.relativedelta
import pytz  # 시간대 처리를 위한 모듈

import logging

# Set up logging
# 로깅 수준을 INFO로 설정하여 DEBUG 메시지를 숨김
logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.DEBUG)


logger = logging.getLogger(__name__)
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
        
        
        
def generate_recurring_events(
    start_date: datetime, 
    frequency: str, 
    interval: int, 
    until: Optional[datetime], 
    count: Optional[int], 
    requested_start: datetime, 
    requested_end: datetime, 
    exceptions: Optional[Set[datetime]] = None  # 예외 일정 추가
) -> List[datetime]:
    occurrences = []
    current_date = start_date
    occurrences_count = 0

    # 예외 일정이 없을 경우 빈 집합으로 초기화
    if exceptions is None:
        exceptions = set()

    # 로그: 함수 시작 로그와 입력 데이터 기록
    logger.info(f"Starting generate_recurring_events with start_date={start_date}, frequency={frequency}, "
                f"interval={interval}, until={until}, count={count}, requested_start={requested_start}, "
                f"requested_end={requested_end}, exceptions={exceptions}")

    # Ensure all datetime objects are timezone-aware
    if current_date.tzinfo is None:
        current_date = pytz.utc.localize(current_date)
    if until is not None and until.tzinfo is None:
        until = pytz.utc.localize(until)
    if requested_start.tzinfo is None:
        requested_start = pytz.utc.localize(requested_start)
    if requested_end.tzinfo is None:
        requested_end = pytz.utc.localize(requested_end)

    try:
        # 종료일 또는 무한 반복일 경우, until이 없으면 요청 종료일로 대체
        until = until if until else requested_end
        logger.debug(f"Computed until={until} for the recurring events")

        while current_date <= until and (count is None or occurrences_count < count):
            # 요청된 기간 안에 있는 반복 일정만 추가하고, 예외 일정은 제외
            if current_date >= requested_start and current_date <= requested_end:
                if current_date in exceptions:
                    logger.debug(f"Skipping exception date: {current_date}")
                else:
                    logger.debug(f"Adding occurrence: {current_date}")
                    occurrences.append(current_date)

            # 다음 반복 발생일 계산 (주기와 간격에 따라)
            if frequency == 'daily':
                current_date += timedelta(days=interval)
            elif frequency == 'weekly':
                current_date += timedelta(weeks=interval)
            elif frequency == 'monthly':
                current_date += dateutil.relativedelta.relativedelta(months=interval)
            elif frequency == 'yearly':
                current_date += dateutil.relativedelta.relativedelta(years=interval)
            else:
                logger.error(f"Invalid frequency: {frequency}")
                raise ValueError(f"Invalid frequency: {frequency}")

            occurrences_count += 1
            logger.debug(f"Next occurrence calculated: {current_date}")

    except Exception as e:
        logger.error(f"Error occurred while generating recurring events: {e}")
        raise

    # 로그: 발생한 모든 일정을 로그에 기록
    logger.info(f"Generated {len(occurrences)} occurrences, with exceptions excluded: {exceptions}")

    return occurrences