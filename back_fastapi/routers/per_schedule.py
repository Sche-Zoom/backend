from fastapi import APIRouter, Depends, HTTPException, status
from models.schemas import Reminder, Repeat, CreateScheduleResponse, CreateSchedule, ScheduleDate, ScheduleResponseItem, ScheduleResponse, TotalTags, Tag
from routers.util.jwt import verify_token
from db.db_conn import get_db_connection, close_db_connection
from .util.auth import extract_user_id_from_token
from .util.utils import parse_iso_date, check_per_tags, check_color_list, generate_recurring_events
from fastapi.security import OAuth2PasswordBearer
import psycopg2
from typing import List, Optional
from datetime import datetime
import logging
import pytz



# Set up logging

# 로깅 수준을 INFO로 설정하여 DEBUG 메시지를 숨김
logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.DEBUG)


logger = logging.getLogger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/sign/token")


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return pytz.utc.localize(dt)
    return dt

@router.get("/list", response_model=ScheduleResponse)
async def list_schedules(
    start_date: str,
    end_date: str,
    tag_ids: Optional[List[int]] = None,
    token: str = Depends(oauth2_scheme)
):
    # JWT 토큰 검증 및 사용자 ID 추출
    try:
        uid = extract_user_id_from_token(token)
    except HTTPException as e:
        print(f"HTTPException occurred: {e.detail}")
        raise e
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred."
        )
    
    # 날짜 형식 검증 및 변환
    start_date_dt = datetime.fromisoformat(start_date).astimezone(pytz.utc)
    end_date_dt = datetime.fromisoformat(end_date).astimezone(pytz.utc)
    
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 기본 일정 및 반복 일정 조회
        query = """
            SELECT s.id, s.title, s.start_date, s.end_date, s.color, r.frequency, r.interval, r.until, r.count
            FROM schedule s
            LEFT JOIN recurrence r ON s.id = r.schedule_id
            WHERE s.uid = %s
            AND (s.start_date <= %s AND (s.end_date IS NULL OR s.end_date >= %s))
        """
        params = [uid, end_date_dt, start_date_dt]

        if tag_ids:
            query += """
                AND EXISTS (
                    SELECT 1
                    FROM schedule_tag st
                    WHERE st.schedule_id = s.id
                    AND st.tag_id = ANY(%s)
                )
            """
            params.append(tag_ids)

        cur.execute(query, params)
        rows = cur.fetchall()

        schedules = []

        for row in rows:
            try:
                schedule_id, title, start_date, end_date, color, frequency, interval, until, count = row
                # DB에서 읽어온 데이터 처리
                start_date = ensure_utc(start_date)
                end_date = ensure_utc(end_date)
                until = ensure_utc(until) if until else None
                requested_start = ensure_utc(start_date_dt)
                requested_end = ensure_utc(end_date_dt)

                logger.debug(f"Processing schedule_id={schedule_id}, frequency={frequency}, interval={interval}, until={until}, count={count}")

                # 반복 일정이 있는 경우, 해당 기간 동안 발생하는 모든 일정을 계산
                if frequency:
                    interval = interval or 1  # interval이 None일 경우 기본값 1로 설정
                    until = until or end_date_dt  # until이 None이면 요청된 기간의 끝으로 설정
                    count = count  # count는 None일 수 있음

                    events = generate_recurring_events(
                        start_date=start_date,
                        frequency=frequency,
                        interval=interval,
                        until=until,
                        count=count,
                        requested_start=start_date_dt,
                        requested_end=end_date_dt
                    )

                    # 날짜 리스트로 변환
                    dates = [ScheduleDate(start_date=event, end_date=event + (end_date - start_date)) for event in events]

                    schedules.append(ScheduleResponseItem(
                        id=schedule_id,
                        title=title,
                        color=color,
                        dates=dates
                    ))
                    logger.debug(f"Added event: {schedules[-1]}")
                else:
                    # 반복이 아닌 단일 일정 추가
                    schedules.append(ScheduleResponseItem(
                        id=schedule_id,
                        title=title,
                        color=color,
                        dates=[ScheduleDate(start_date=start_date, end_date=end_date)]
                    ))
                    logger.debug(f"Added single schedule: {schedules[-1]}")

            except Exception as e:
                logger.error(f"Error processing row {row}: {e}")
                raise

        return ScheduleResponse(schedules=schedules)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve schedules."
        )
    finally:
        cur.close()
        close_db_connection(conn)
## 2-2. [ 조회 ] (side)개인스케줄 - 통합

## 2-3. [ 조회 ] (detail)개인스케줄 - 일정조회

## 2-4. [생성] 개인스케줄 - 일정생성
@router.post("/create-schedule", response_model=CreateScheduleResponse)
async def create_schedule(schedule: CreateSchedule, token: str = Depends(oauth2_scheme)):
    try:
        # JWT 토큰 검증 및 사용자 ID 추출
        uid = extract_user_id_from_token(token)
        
        # 색상 체크
        if not check_color_list(schedule.color):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid color. Please provide a valid color."
            )
            
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 일정 테이블에 데이터 삽입
        cur.execute(
            """
            INSERT INTO schedule (title, note, color, start_date, end_date, important, uid, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW()) RETURNING id
            """,
            (
                schedule.title,
                schedule.note,
                schedule.color,
                schedule.start_date,
                schedule.end_date,
                schedule.important,
                uid
            )
        )
        schedule_id = cur.fetchone()[0]

        # 태그 처리
        for tag in schedule.tags:
            cur.execute("SELECT id FROM tag WHERE title = %s", (tag,))
            tag_id = cur.fetchone()
            if not tag_id:
                cur.execute(
                    """
                    INSERT INTO tag (title, is_personal, uid)
                    VALUES (%s, %s, %s) RETURNING id
                    """,
                    (tag, True, uid)
                )
                tag_id = cur.fetchone()[0]
            else:
                tag_id = tag_id[0]

            cur.execute(
                """
                INSERT INTO schedule_tag (tag_id, schedule_id, is_personal)
                VALUES (%s, %s, %s)
                """,
                (tag_id, schedule_id, True)
            )

        # 반복 설정
        if schedule.repeat:
            cur.execute(
                """
                INSERT INTO recurrence (frequency, interval, until, count, schedule_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    schedule.repeat.frequency,
                    schedule.repeat.interval,
                    schedule.repeat.until,
                    schedule.repeat.count,
                    schedule_id
                )
            )

        # 알림 설정
        if schedule.reminders:
            for reminder in schedule.reminders:
                cur.execute(
                    """
                    INSERT INTO reminder (days_before, schedule_id)
                    VALUES (%s, %s)
                    """,
                    (
                        reminder,
                        schedule_id
                    )
                )

        conn.commit()
        return {"id": schedule_id}
    except Exception as e:
        conn.rollback()
        print(f"Error creating schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create schedule",
        )
    finally:
        cur.close()
        close_db_connection(conn)


## 2-5. [ 수정 ] (detail)개인스케줄 - 일정정보
@router.get("/detail/{schedule_id}", response_model=ScheduleResponse)
async def detail_schedule(
    schedule_id: int,
    token: str = Depends(oauth2_scheme)
):
    # JWT 토큰 검증 및 사용자 ID 추출
    try:
        uid = extract_user_id_from_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token."
        )

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 기본 일정 및 반복 규칙 조회
        cur.execute("""
            SELECT s.id, s.title, s.start_date, s.end_date, s.color, r.frequency, r.interval, r.until, r.count
            FROM schedule s
            LEFT JOIN recurrence r ON s.id = r.schedule_id
            WHERE s.id = %s AND s.uid = %s
        """, (schedule_id, uid))
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

        schedule_id, title, start_date, end_date, color, frequency, interval, until, count = row
        
        # 반복 일정이 있으면 반복 규칙에 맞게 계산하여 반환
        if frequency:
            events = generate_recurring_events(
                start_date=start_date,
                frequency=frequency,
                interval=interval,
                until=until,
                count=count,
                requested_start=start_date,
                requested_end=end_date
            )
            return {
                "id": schedule_id,
                "title": title,
                "start_date": events[0],  # 최초 일정 반환
                "end_date": events[0] + (end_date - start_date),
                "color": color
            }
        else:
            return {
                "id": schedule_id,
                "title": title,
                "start_date": start_date,
                "end_date": end_date,
                "color": color
            }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve schedule detail."
        )
    finally:
        cur.close()
        close_db_connection(conn)
## 2-6. [ 수정 ] 개인스케줄 -  일정정보삭제

## 2-7. [ 조회 ] 개인스케줄 - 알림

## 2-8. =진행예정= total_groups 조회

@router.get("/total-tags", response_model=TotalTags)
async def total_tags(
    token: str = Depends(oauth2_scheme)
):
    # JWT 토큰 검증 및 사용자 ID 추출
    try:
        uid = extract_user_id_from_token(token)
    except HTTPException as e:
        print(f"HTTPException occurred: {e.detail}")
        raise e
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred."
        )
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # 개인 태그 가져오기
        personal_tags = check_per_tags(uid)
        per_tags = [Tag(id=t[0], name=t[1]) for t in personal_tags]

        # 그룹 정보는 아직 정의되지 않았으므로 빈 리스트로 반환
        group_list = []

        # TotalTags 객체 생성
        total_tags = TotalTags(per_tags=per_tags, groups=group_list)
        
        # TotalTags 객체를 직접 반환
        return total_tags
    except Exception as e:
        print(f"Error fetching total tags: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch total tags."
        )
    finally:
        cur.close()
        close_db_connection(conn)