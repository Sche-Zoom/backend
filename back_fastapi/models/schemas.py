from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime, time

class Repeat(BaseModel):
    interval: str = Field(..., example="weekly", description="Repeat interval: daily, weekly, or monthly")
    until: Optional[str] = Field(None, example="2024-06-30", description="Repeat until this date in YYYY-MM-DD format or null")
    count: Optional[int] = Field(None, example=10, description="Number of times to repeat or null for infinite")

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

class CreateSchedule(BaseModel):
    title: str = Field(..., example="Meeting with Client", description="Title of the schedule")
    note: Optional[str] = Field(None, example="Discuss project details and deadlines", description="Description of the schedule")
    important: str = Field(..., example="high", description="Important level: very_low, low, medium, high, very_high")
    color: str = Field(..., example="#FF5733", description="Color of the schedule")
    tags: List[str] = Field(..., example=["Client", "Meeting"], description="List of tags for the schedule")
    start_date: datetime = Field(..., example="2024-05-10T10:00:00Z", description="Start date and time in ISO 8601 format")
    end_date: datetime = Field(..., example="2024-05-10T12:00:00Z", description="End date and time in ISO 8601 format")
    repeat: Optional[Repeat] = Field(None, description="Repeat rule for the schedule")
    reminders: Optional[List[int]] = Field(None, example=[180, 2400], description="List of reminder times in minutes before the event")
    reminder_email_noti: Optional[bool] = Field(None, example=True, description="Whether to send email notifications")


class CreateScheduleResponse(BaseModel):
    id: int = Field(..., example=123456, description="Unique ID of the created schedule")
    
    
    
    
    
# 스케줄 날짜 정보 스키마
class ScheduleDate(BaseModel):
    start_date: datetime = Field(..., example="2024-05-15T12:00:00Z", description="Start date and time of the schedule")
    end_date: datetime = Field(..., example="2024-05-15T13:00:00Z", description="End date and time of the schedule")


# 개별 스케줄 조회 응답 아이템 스키마
class ScheduleResponseItem(BaseModel):
    id: int = Field(..., example=24, description="ID of the schedule")
    title: str = Field(..., example="Team Lunch", description="Title of the schedule")
    color: str = Field(..., example="#ffe12e", description="Color code of the schedule")
    dates: List[ScheduleDate] = Field(..., description="List of dates associated with the schedule")

# 스케줄 응답 스키마
class ScheduleResponse(BaseModel):
    schedules: List[ScheduleResponseItem] = Field(..., description="List of schedules matching the criteria")


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


# Tag 응답 스키마
class TotalTagsResponse(BaseModel):
    data: TotalTags = Field(..., description="Data containing all personal and grouped tags")