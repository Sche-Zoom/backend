from fastapi import APIRouter, Depends, HTTPException, status
from models.schemas import Reminder, Repeat, CreateScheduleResponse, CreateSchedule, ScheduleResponse, TotalTags, Tag
from routers.util.jwt import verify_token
from db.db_conn import get_db_connection, close_db_connection
from .util.auth import extract_user_id_from_token
from .util.utils import parse_iso_date, check_per_tags, check_color_list
from fastapi.security import OAuth2PasswordBearer
import psycopg2
from typing import List, Optional
from datetime import datetime

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/sign/token")



## 2-1. [ 조회 ] 개인스케줄 - 통합
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
    start_date_dt = parse_iso_date(start_date)
    end_date_dt = parse_iso_date(end_date)

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 스케줄 조회 쿼리 작성
        query = """
            SELECT s.id, s.title, s.color, s.start_date, s.end_date
            FROM schedule s
            WHERE s.uid = %s
            AND s.start_date >= %s
            AND s.end_date <= %s
        """
        params = [uid, start_date_dt, end_date_dt]
        print(query, params)
        # 태그 필터링
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

        # 결과를 원하는 형식으로 변환
        schedules = [
            {
                "id": row[0],
                "title": row[1],
                "color": row[2],
                "dates": [
                    {"start_date": row[3].isoformat(), "end_date": row[4].isoformat()}
                ]
            }
            for row in rows
        ]

        return {"schedules": schedules}
    except Exception as e:
        print(f"Error retrieving schedules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve schedules"
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
            
        # 날짜 형식 검증 및 변환
        start_date_dt = parse_iso_date(schedule.start_date)
        end_date_dt = parse_iso_date(schedule.end_date)


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
                start_date_dt,
                end_date_dt,
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
                INSERT INTO recurrence (interval, until, count, schedule_id)
                VALUES (%s, %s, %s, %s)
                """,
                (
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