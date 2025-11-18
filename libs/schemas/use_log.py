from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from libs.schemas.coupon import Coupon


class UseLog(BaseModel):
    """
    쿠폰 사용 이력 엔티티.
    """

    useLogId: int = Field(..., description="사용 로그 식별자")
    couponId: int = Field(..., description="연결된 쿠폰 ID")
    coupon: Coupon | None = Field(None, description="연결된 쿠폰 정보")
    usedAt: datetime | None = Field(None, description="사용 일시")

    class Config:
        from_attributes = True

