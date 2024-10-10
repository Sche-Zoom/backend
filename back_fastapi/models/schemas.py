from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime, time

# 허용된 색상 목록
ALLOWED_COLORS = ['blue', 'green', 'yellow', 'purple', 'orange', 'mint', 'lavender', 'beige', 'coral']


# Reminder 관련 스키마
class Reminder(BaseModel):
    days_before: int = Field(..., example=1, description="Number of days before the event to remind")
    reminder_time: time = Field(..., example="10:00:00", description="Time of the day for the reminder")
    email: bool = Field(..., example=True, description="Whether to send an email reminder")

    @field_validator('reminder_time', mode='before')
    def parse_time(cls, value):
        if isinstance(value, str):
            return datetime.strptime(value, '%H:%M:%S').time()
        return value
# Tag 기본 정보 스키마
class Tag(BaseModel):
    id: int = Field(..., example=1, description="Unique ID of the tag")
    name: str = Field(..., example="Meeting", description="Name of the tag")

# 그룹 내 Tag 정보를 포함한 그룹 스키마
class Group(BaseModel):
    id: int = Field(..., example=24, description="Unique ID of the group")
    name: str = Field(..., example="Development Team", description="Name of the group")
    tags: List[Tag] = Field(..., description="List of tags associated with the group")

# 모든 Tag와 그룹 내 Tag 목록을 포함한 스키마
class TotalTags(BaseModel):
    per_tags: List[Tag] = Field(..., description="List of personal tags")
    groups: List[Group] = Field(..., description="List of groups with associated tags")


# 스케줄 생성시 필요한 스키마
class CreateSchedule(BaseModel):
    title: str = Field(..., example="Meeting with Client", description="Title of the schedule")
    note: Optional[str] = Field(None, example="Discuss project details and deadlines", description="Description of the schedule")
    important: str = Field(..., example="high", description="Important level: very_low, low, medium, high, very_high")
    color: str = Field(..., example="blue", description="Color keyword for the schedule")
    tags: List[str] = Field(..., example=["Client", "Meeting"], description="List of tags for the schedule")
    start_date: datetime = Field(..., example="2024-05-10T10:00:00", description="Start date and time in ISO 8601 format")
    end_date: datetime = Field(..., example="2024-05-10T12:00:00", description="End date and time in ISO 8601 format")
    is_repeat: Optional[bool] = Field(default=False, example = True, description="Defines if the schedule is repeating")
    repeat_frequency: Optional[str] = Field(None, example="daily", description="Frequency of recurrence: daily, weekly, monthly, yearly")
    repeat_interval: Optional[int] = Field(None, example=1, description="Interval between recurrences")
    repeat_end_date: Optional[datetime] = Field(None, example="2024-12-31T23:59:59", description="End date for recurrence in ISO 8601 format")
    repeat_count: Optional[int] = Field(None, example=10, description="Number of occurrences")

    reminders: Optional[List[int]] = Field(None, example=[180, 2400], description="List of reminder times in minutes before the event")
    reminder_email_noti: Optional[bool] = Field(None, example=True, description="Whether to send email notifications")
    
    @field_validator('color')
    def validate_color(cls, value):
        if value not in ALLOWED_COLORS:
            raise ValueError(f"Invalid color: {value}. Allowed colors are {ALLOWED_COLORS}.")
        return value


# 스케줄 생성 뒤  sid를 보내기 위한 responese
class CreateScheduleResponse(BaseModel):
    id: int = Field(..., example=123456, description="Unique ID of the created schedule")
    
    
    
class UpdateSchedule(BaseModel):
    title: Optional[str] = Field(None, example="비마트 퇴사하고싶다", description="Title of the schedule")
    note: Optional[str] = Field(None, example="돈많은 백수 하고 싶어요", description="Description of the schedule")
    important: Optional[str] = Field(None, example="high", description="Important level: very_low, low, medium, high, very_high")
    color: Optional[str] = Field(None, example="orange", description="Color keyword for the schedule")
    tags: Optional[List[str]] = Field(None, example=["퇴사", "월급"], description="List of tags for the schedule")
    start_date: Optional[datetime] = Field(None, example="2024-05-20T10:00:00", description="Start date and time in ISO 8601 format")
    end_date: Optional[datetime] = Field(None, example="2024-05-220T12:00:00", description="End date and time in ISO 8601 format")
    is_repeat: Optional[bool] = Field(default=False, example = True, description="Defines if the schedule is repeating")
    repeat_frequency: Optional[str] = Field(None, example="daily", description="Frequency of recurrence: daily, weekly, monthly, yearly")
    repeat_interval: Optional[int] = Field(None, example=1, description="Interval between recurrences")
    repeat_end_date: Optional[datetime] = Field(None, example="2024-12-31T23:59:59", description="End date for recurrence in ISO 8601 format")
    repeat_count: Optional[int] = Field(None, example=10, description="Number of occurrences")

    reminders: Optional[List[int]] = Field(None, example=[180, 2400], description="List of reminder times in minutes before the event")
    reminder_email_noti: Optional[bool] = Field(None, example=True, description="Whether to send email notifications")
    
    @field_validator('color')
    def validate_color(cls, value):
        if value not in ALLOWED_COLORS:
            raise ValueError(f"Invalid color: {value}. Allowed colors are {ALLOWED_COLORS}.")
        return value

class UpdateRepeatSchedule(UpdateSchedule):
    modify_type: str = Field(None, example="only", description="Type of modification: only, after_all, all")

    
# 스케줄 날짜 정보 스키마
class ScheduleDate(BaseModel):
    start_date: datetime = Field(..., example="2024-05-15T12:00:00", description="Start date and time of the schedule")
    end_date: datetime = Field(..., example="2024-05-15T13:00:00", description="End date and time of the schedule")


# 개별 스케줄 조회 응답 아이템 스키마
class ScheduleResponseItem(BaseModel):
    id: int = Field(..., example=24, description="ID of the schedule")
    title: str = Field(..., example="Team Lunch", description="Title of the schedule")
    color: str = Field(..., example="orange", description="Color code of the schedule")
    dates: List[ScheduleDate] = Field(..., description="List of dates associated with the schedule")

# 스케줄 응답 스키마
class ScheduleResponse(BaseModel):
    schedules: List[ScheduleResponseItem] = Field(..., description="List of schedules matching the criteria")


