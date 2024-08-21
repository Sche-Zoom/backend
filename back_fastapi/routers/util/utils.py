from datetime import datetime
from fastapi import HTTPException, status

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
