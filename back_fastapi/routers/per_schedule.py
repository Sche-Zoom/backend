from fastapi import APIRouter, Depends, HTTPException, status, Query
from models.schemas import Reminder, CreateScheduleResponse, CreateSchedule, ScheduleDate, ScheduleResponseItem, SidebarScheduleGroup, ScheduleResponse,UpdateSchedule, UpdateRepeatSchedule, TotalTags, Tag, SidebarScheduleResponse
from routers.util.jwt import verify_token
from db.db_conn import get_db_connection, close_db_connection
from .util.auth import extract_user_id_from_token
from .util.utils import parse_iso_date, check_per_tags, check_color_list, generate_recurring_events
from fastapi.security import OAuth2PasswordBearer
import psycopg2
from typing import List, Optional
from datetime import datetime, timedelta
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
# 2-1. [ 조회 ] 개인스케줄 - 통합
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

                    logger.info(f"Schedule {schedule_id} has recurrence with frequency={frequency}, interval={interval}, until={until}, count={count}")

                    # 예외 일정 조회
                    cur.execute("""
                        SELECT start_date FROM recurrence_exception
                        WHERE recurrence_id = (
                            SELECT id FROM recurrence WHERE schedule_id = %s
                        )
                    """, [schedule_id])
                    exception_rows = cur.fetchall()
                    exceptions = {ensure_utc(exception_date[0]) for exception_date in exception_rows}

                    if exceptions:
                        logger.info(f"Schedule {schedule_id} has recurrence exceptions: {exceptions}")

                    # 반복 일정 생성 (예외 일정을 고려)
                    events = generate_recurring_events(
                        start_date=start_date,
                        frequency=frequency,
                        interval=interval,
                        until=until,
                        count=count,
                        requested_start=requested_start,
                        requested_end=requested_end,
                        exceptions=exceptions  # 예외 일정 전달
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
@router.get("/sidebar", response_model=SidebarScheduleResponse)
async def get_sidebar_schedules(
    selected_date: str,
    tag_ids: Optional[List[int]] = Query(None),
    token: str = Depends(oauth2_scheme)
):
    # tag_ids가 전달되지 않으면 None, 여러 개 전달되면 리스트로 처리됨
    if tag_ids is None:
        # tag_ids가 없는 경우 처리
        print("No tag_ids provided")
    else:
        # tag_ids가 있는 경우 처리
        print(f"tag_ids: {tag_ids}")
    try:
        uid = extract_user_id_from_token(token)
    except HTTPException as e:
        logger.error(f"HTTPException occurred: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred."
        )
    
    # selected_date로부터 연도 및 월 추출
    try:
        selected_dt = datetime.strptime(selected_date, "%Y-%m-%dT%H:%M:%S")
        selected_year = selected_dt.year
        selected_month = selected_dt.month
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid selected_date format.")

    # 월의 첫날과 마지막 날 계산
    first_day_of_month = selected_dt.replace(day=1)
    next_month = (first_day_of_month + timedelta(days=32)).replace(day=1)
    last_day_of_month = next_month - timedelta(days=1)

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Schedule 데이터 조회 쿼리
        query = """
            SELECT s.id, s.title, s.start_date, s.end_date, s.color, 
                r.frequency, r.interval, r.until, r.count, 
                array_agg(DISTINCT st.tag_id) as tag_ids, array_agg(DISTINCT t.title) as tag_names
            FROM schedule s
            LEFT JOIN recurrence r ON s.id = r.schedule_id
            LEFT JOIN schedule_tag st ON s.id = st.schedule_id
            LEFT JOIN tag t ON st.tag_id = t.id
            WHERE s.uid = %s
            AND s.start_date >= %s
            AND s.start_date <= %s
            GROUP BY s.id, r.frequency, r.interval, r.until, r.count
        """

        params = [uid, first_day_of_month, last_day_of_month]

        # 태그 필터링 추가
        if tag_ids:
            # print(f'tag = {tag_ids}')
            query += " HAVING %s = ANY(array_agg(st.tag_id))"
            params.append(tag_ids[0])  # 하나의 태그만 비교할 때 (리스트가 아닌 단일 값)

        cur.execute(query, params)
        rows = cur.fetchall()

        # logger.debug(f"fetch rows : {rows}")
        # for row in rows :
        #     print(f'fetch rows = {row}')
        
        schedules_by_date = {}

        for row in rows:
            schedule_id, title, start_date, end_date, color, frequency, interval, until, count, tag_id_list, tag_name_list = row
            is_group = False
            start_date = ensure_utc(start_date)
            end_date = ensure_utc(end_date)
            until = ensure_utc(until) if until else None

            schedule_type = "group" if is_group else "personal"

            # Recurrence 예외 처리
            cur.execute("""
                SELECT exception_date FROM recurrence_exception
                WHERE recurrence_id = (
                    SELECT id FROM recurrence WHERE schedule_id = %s
                )
            """, [schedule_id])
            exception_rows = cur.fetchall()
            exceptions = {ensure_utc(exception_date[0]) for exception_date in exception_rows}

            # Recurrence 처리
            if frequency:
                interval = interval or 1
                until = until or last_day_of_month

                events = generate_recurring_events(
                    start_date=start_date,
                    frequency=frequency,
                    interval=interval,
                    until=until,
                    count=count,
                    requested_start=first_day_of_month,
                    requested_end=last_day_of_month,
                    exceptions=exceptions
                )

                for event in events:
                    event = ensure_utc(event)
                    if event not in schedules_by_date:
                        schedules_by_date[event] = []

                    schedules_by_date[event].append({
                        "id": schedule_id,
                        "title": title,
                        # "start_date": event,
                        "end_date": end_date,
                        "color": color,
                        "type": schedule_type,
                        "tags": [{"id": tag_id, "name": tag_name} for tag_id, tag_name in zip(tag_id_list, tag_name_list) if tag_id is not None and tag_name is not None]
                    })
            else:
                # Non-recurring event 처리
                if start_date not in schedules_by_date:
                    schedules_by_date[start_date] = []

                schedules_by_date[start_date].append({
                    "id": schedule_id,
                    "title": title,
                    # "start_date": start_date,
                    "end_date": end_date,
                    "color": color,
                    "type": schedule_type,
                    "tags": [{"id": tag_id, "name": tag_name} for tag_id, tag_name in zip(tag_id_list, tag_name_list) if tag_id is not None and tag_name is not None]
                })

        # Response로 side_schedules 변환
        side_schedules = [
            SidebarScheduleGroup(
                start_date=start_date,
                schedules=schedules
            )
            for start_date, schedules in sorted(schedules_by_date.items())
        ]

        return SidebarScheduleResponse(side_schedules=side_schedules)

    except Exception as e:
        logger.error(f"Error fetching schedules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sidebar schedules."
        )
    finally:
        cur.close()
        close_db_connection(conn)



##2-9.  total_tags 
@router.get("/total-tags", response_model=TotalTags)
async def total_tags(token: str = Depends(oauth2_scheme)):
    # JWT 토큰 검증 및 사용자 ID 추출
    try:
        print("Extracting user ID from token")  # 로깅 추가
        uid = extract_user_id_from_token(token)
        print(f"User ID extracted: {uid}")  # 로깅 추가
    except HTTPException as e:
        print(f"HTTPException occurred during token extraction: {e.detail}")
        raise e
    except Exception as e:
        print(f"An unexpected error occurred during token extraction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during token validation."
        )
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # 개인 태그 가져오기
        print(f"Fetching personal tags for user ID: {uid}")  # 로깅 추가
        personal_tags = check_per_tags(uid)
        print(f"Personal tags fetched: {personal_tags}")  # 로깅 추가

        # 검증: personal_tags가 올바르게 반환되는지 확인
        if not personal_tags:
            print(f"No personal tags found for user ID: {uid}")  # 로깅 추가
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No personal tags found."
            )

        # per_tags 생성
        print("Formatting personal tags")  # 로깅 추가
        per_tags = [Tag(id=t[0], name=t[1]) for t in personal_tags]
        # print(f"Formatted per_tags: {per_tags}")  # 로깅 추가

        # 그룹 정보는 아직 정의되지 않았으므로 빈 리스트로 반환
        group_list = []
        # print("Group list initialized as empty.")  # 로깅 추가

        # TotalTags 객체 생성
        print("Creating TotalTags object")  # 로깅 추가
        total_tags = TotalTags(per_tags=per_tags, groups=group_list)
        # print(f"TotalTags object created: {total_tags}")  # 로깅 추가
        
        # TotalTags 객체를 직접 반환
        # print("Returning TotalTags object")  # 로깅 추가
        return total_tags

    except Exception as e:
        print(f"Error fetching total tags: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch total tags."
        )
    finally:
        # print("Closing database connection")  # 로깅 추가
        cur.close()
        close_db_connection(conn)

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
        if schedule.is_repeat:
            cur.execute(
                """
                INSERT INTO recurrence (frequency, interval, until, count, schedule_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    schedule.repeat_frequency,
                    schedule.repeat_interval,
                    schedule.repeat_end_date,
                    schedule.repeat_count,
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

## 2-3. [ 조회 ] (detail)개인스케줄 - 일정조회
@router.get("/{sid}", response_model=ScheduleResponse)
async def get_schedule(sid: int, token: str = Depends(oauth2_scheme)):
    try:
        # JWT 토큰 검증 및 사용자 ID 추출
        uid = extract_user_id_from_token(token)
        
        conn = get_db_connection()
        cur = conn.cursor()

        # 개인 스케줄 데이터 조회
        cur.execute(
            """
            SELECT s.title, s.note, s.color, s.start_date, s.end_date, s.important, 
                   r.frequency, r.interval, r.until, r.count, 
                   COALESCE((
                       SELECT array_agg(days_before) 
                       FROM reminder WHERE schedule_id = s.id
                   ), '{}') as reminders, 
                   EXISTS(
                       SELECT 1 FROM reminder WHERE schedule_id = s.id AND email = true
                   ) as reminder_email_noti
            FROM schedule s
            LEFT JOIN recurrence r ON s.id = r.schedule_id
            WHERE s.id = %s AND s.uid = %s
            """,
            (sid, uid)
        )

        schedule = cur.fetchone()

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found"
            )

        # 스케줄 정보 매핑
        title, note, color, start_date, end_date, important, repeat_frequency, repeat_interval, repeat_end_date, repeat_count, reminders, reminder_email_noti = schedule
        print(title, note, color, start_date, end_date, important, repeat_frequency, repeat_interval, repeat_end_date, repeat_count, reminders, reminder_email_noti)
        # 태그 데이터 조회
        cur.execute(
            """
            SELECT t.id, t.title 
            FROM tag t
            JOIN schedule_tag st ON t.id = st.tag_id
            WHERE st.schedule_id = %s
            """,
            (sid,)
        )
        tags = cur.fetchall()
        tag_list = [{"id": tag_id, "name": tag_name} for tag_id, tag_name in tags]
        if repeat_count:
            repeat_end_option = "count"
            repeat_end_date = None
        elif repeat_end_date:
            repeat_end_option = "end_date"
            repeat_count = None
        else:
            repeat_end_option = None
        # 반환할 데이터 구조 작성
        response_data = {
            "title": title,
            "type": "personal",  # 타입은 "personal"로 고정
            "description": note,
            "importance": important,
            "color": color,
            "tags": tag_list,
            "start_date": start_date,
            "end_date": end_date,
            "is_repeat": repeat_frequency is not None,
            "repeat_end_option": repeat_end_option,
            "repeat_frequency": repeat_frequency,
            "repeat_interval": repeat_interval,
            "repeat_end_date": repeat_end_date,
            "repeat_count" : repeat_count,
            "reminder": reminders,
            "reminder_email_noti": reminder_email_noti
        }

        return response_data

    except Exception as e:
        print(f"Error fetching schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch schedule",
        )
    finally:
        cur.close()
        close_db_connection(conn)

## 2-5. [ 수정 ] (detail)개인스케줄 - 일정정보
@router.patch("/{sid}")
async def update_schedule(
    sid: int,
    schedule_update: UpdateSchedule,
    token: str = Depends(oauth2_scheme)
):
    try:
        # JWT 토큰 검증 및 사용자 ID 추출
        uid = extract_user_id_from_token(token)
        
        # DB 연결
        conn = get_db_connection()
        cur = conn.cursor()

        # 기본 일정 정보 수정
        update_fields = []
        update_values = []

        if schedule_update.title:
            update_fields.append("title = %s")
            update_values.append(schedule_update.title)
        
        if schedule_update.note:
            update_fields.append("note = %s")
            update_values.append(schedule_update.note)
        
        if schedule_update.color:
            update_fields.append("color = %s")
            update_values.append(schedule_update.color)
        
        if schedule_update.start_date:
            update_fields.append("start_date = %s")
            update_values.append(schedule_update.start_date)
        
        if schedule_update.end_date:
            update_fields.append("end_date = %s")
            update_values.append(schedule_update.end_date)
        
        if schedule_update.important:
            update_fields.append("important = %s")
            update_values.append(schedule_update.important)

        if update_fields:
            update_query = f"""
                UPDATE schedule 
                SET {", ".join(update_fields)}, updated_at = NOW()
                WHERE id = %s AND uid = %s
            """
            update_values.extend([sid, uid])
            logger.info(f"Executing update query: {update_query} with values: {tuple(update_values)}")
            cur.execute(update_query, tuple(update_values))

        # 태그 수정
        if schedule_update.tags is not None:  # None 체크
            cur.execute("DELETE FROM schedule_tag WHERE schedule_id = %s", (sid,))
            for tag in schedule_update.tags:
                # tag는 이제 문자열이므로, 태그 ID를 직접 추가하는 방식으로 변경 필요
                cur.execute("INSERT INTO schedule_tag (tag_id, schedule_id) VALUES ((SELECT id FROM tags WHERE name = %s), %s)", (tag, sid))
        # 알림 수정
        if schedule_update.reminders:
            logger.info(f"Updating reminders: {schedule_update.reminders}")
            cur.execute("DELETE FROM reminder WHERE schedule_id = %s", (sid,))
            for reminder in schedule_update.reminders:
                logger.info(f"Inserting reminder: {reminder}")
                cur.execute("INSERT INTO reminder (days_before, schedule_id) VALUES (%s, %s)", (reminder, sid))

        # 반복 일정 정보가 있는 경우
        if schedule_update.is_repeat:
            logger.info(f"Updating recurrence: frequency='{schedule_update.repeat_frequency}' interval={schedule_update.repeat_interval} until={schedule_update.repeat_end_date} count={schedule_update.repeat_count}")
            cur.execute(
                """
                INSERT INTO recurrence (frequency, interval, until, count, schedule_id)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (schedule_id) DO UPDATE
                SET frequency = EXCLUDED.frequency, interval = EXCLUDED.interval, until = EXCLUDED.until, count = EXCLUDED.count
                """,
                (
                    schedule_update.repeat_frequency,
                    schedule_update.repeat_interval,
                    schedule_update.repeat_end_date,
                    schedule_update.repeat_count,
                    sid
                )
            )
        conn.commit()
        return {"status": "success", "message": "Schedule updated successfully"}
    
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)  # 에러 로그 기록
        if conn:
            conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update schedule")

    finally:
        if cur:
            cur.close()
        if conn:
            close_db_connection(conn)
        
## 2-6. [ 수정 ] 개인스케줄 -  일정정보삭제
"""
delete
api/per-scehdule/{sid}


request
parameter 
- only 
    - 일반일정 삭제 프로세스 
    - 반복일정에서 단일 스케줄 삭제
- after_all
    - 반복 일정에서 특정 시간 이후 스케줄 삭제.
        이전 일정은 유지
- all
    - 반복 일정 전체 스케줄 삭제

일정 삭제 프로세스

"""

## 2-7. [ 조회 ] 개인스케줄 - 알림



## 2-10. (detail) 개인 반복 스케줄 - 일정정보
@router.patch("/repeat/{sid}")
async def modify_repeat_schedule(
    sid: int,
    schedule_update: UpdateRepeatSchedule,  # UpdateRepeatSchedule 모델 사용
    token: str = Depends(oauth2_scheme)
):
    try:
        # JWT 토큰 검증 및 사용자 ID 추출
        uid = extract_user_id_from_token(token)

        # DB 연결
        conn = get_db_connection()
        cur = conn.cursor()

        # 현재 날짜 가져오기
        current_date = datetime.now()

        # 1. only일 경우
        if schedule_update.modify_type == "only":
            logger.info(f"Modifying recurrence only for schedule ID {sid}")

            # 중복 확인 쿼리: start_date, end_date, recurrence_id로 확인
            cur.execute(
                """
                SELECT COUNT(*) FROM recurrence_exception 
                WHERE start_date = %s AND end_date = %s 
                AND recurrence_id = (SELECT id FROM recurrence WHERE schedule_id = %s)
                """,
                (schedule_update.start_date, schedule_update.end_date, sid)
            )
            exists = cur.fetchone()[0] > 0

            if not exists:
                # 중복되지 않으면 삽입
                cur.execute(
                    """
                    INSERT INTO recurrence_exception (exception_date, start_date, end_date, recurrence_id)
                    VALUES (%s, %s, %s, (SELECT id FROM recurrence WHERE schedule_id = %s))
                    """,
                    (current_date, schedule_update.start_date, schedule_update.end_date, sid)
                )
            else:
                logger.info("Recurrence exception already exists, skipping insertion.")
                return {"status": "success", "message": "Recurrence exception already exists."}


            # 해당 스케줄을 새로운 스케줄로 등록 (create-schedule)
            cur.execute(
                """
                INSERT INTO schedule (title, note, important, color, start_date, end_date, uid)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (schedule_update.title, schedule_update.note, schedule_update.important, 
                schedule_update.color, schedule_update.start_date, schedule_update.end_date, uid)
            )
            new_schedule_id = cur.fetchone()[0]
            logger.info(f"New schedule created with ID {new_schedule_id}")

        # 2. after_all일 경우
        elif schedule_update.modify_type == "after_all":
            logger.info(f"Modifying recurrence after existing for schedule ID {sid}")

            # 반복 테이블의 end_date 수정
            cur.execute(
                """
                UPDATE recurrence 
                SET until = %s 
                WHERE schedule_id = %s
                """,
                (schedule_update.start_date, sid)
            )

            # 수정된 반복 일정을 새로운 스케줄로 등록 (create-schedule)
            cur.execute(
                """
                INSERT INTO schedule (title, note, important, color, start_date, end_date, uid)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (schedule_update.title, schedule_update.note, schedule_update.important, 
                schedule_update.color, schedule_update.start_date, schedule_update.end_date, uid)
            )
            new_schedule_id = cur.fetchone()[0]
            logger.info(f"New schedule created with ID {new_schedule_id}")
            
                # (신) 반복 일정 추가
            if schedule_update.is_repeat:
                cur.execute(
                    """
                    INSERT INTO recurrence (frequency, interval, until, count, schedule_id)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        schedule_update.repeat_frequency,
                        schedule_update.repeat_interval,
                        schedule_update.repeat_end_date,
                        schedule_update.repeat_count,
                        new_schedule_id
                    )
                )
                logger.info(f"New recurrence created for schedule ID {new_schedule_id}")

            # (신) 알림 기능 추가
            if schedule_update.reminders:
                for reminder in schedule_update.reminders:
                    cur.execute(
                        """
                        INSERT INTO reminder (days_before, schedule_id)
                        VALUES (%s, %s)
                        """,
                        (reminder, new_schedule_id)
                    )
                    logger.info(f"Reminder added: {reminder} days before for schedule ID {new_schedule_id}")

            logger.info(f"Schedule modification after_all completed for schedule ID {sid}")

        # 3. all일 경우
        elif schedule_update.modify_type == "all":
            logger.info(f"Modifying all recurrences for schedule ID {sid}")

            # 반복 테이블 수정
            cur.execute(
                """
                UPDATE recurrence
                SET frequency = %s, interval = %s, until = %s, count = %s
                WHERE schedule_id = %s
                """,
                (
                    schedule_update.repeat_frequency,
                    schedule_update.repeat_interval,
                    schedule_update.repeat_end_date,
                    schedule_update.repeat_count,
                    sid
                )
            )

        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid modify_type")

        conn.commit()
        return {"status": "success", "message": "Repeat schedule modified successfully"}

    except Exception as e:
        conn.rollback()
        logger.error(f"Error occurred: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to modify repeat schedule")

    finally:
        cur.close()
        close_db_connection(conn)
