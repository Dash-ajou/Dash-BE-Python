from functools import lru_cache

from services.coupon.app.core.CouponService import CouponService
from services.coupon.app.db.repositories.coupons import SQLAlchemyCouponRepository


@lru_cache
def get_coupon_repository() -> SQLAlchemyCouponRepository:
    """쿠폰 Repository 의존성"""
    return SQLAlchemyCouponRepository()


@lru_cache
def get_coupon_service() -> CouponService:
    """쿠폰 서비스 의존성"""
    return CouponService(coupon_repository=get_coupon_repository())

