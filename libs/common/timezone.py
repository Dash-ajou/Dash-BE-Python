"""
한국표준시(KST) 관련 유틸리티
모든 서버에서 일관된 시간 처리를 위해 사용합니다.
"""
from datetime import datetime, timedelta, timezone

# 한국표준시 (KST = UTC+9)
KST_TIMEZONE = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    """
    현재 시간을 한국표준시(KST)로 반환합니다.
    
    Returns:
        KST 시간대의 현재 datetime 객체
    """
    return datetime.now(KST_TIMEZONE)


def ensure_kst(dt: datetime | None) -> datetime | None:
    """
    datetime 객체가 KST 시간대를 가지도록 보장합니다.
    시간대가 없으면 KST로 설정하고, 다른 시간대면 KST로 변환합니다.
    
    Args:
        dt: datetime 객체 또는 None
        
    Returns:
        KST 시간대의 datetime 객체 또는 None
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # 시간대가 없으면 KST로 가정
        return dt.replace(tzinfo=KST_TIMEZONE)
    # 다른 시간대면 KST로 변환
    return dt.astimezone(KST_TIMEZONE)

