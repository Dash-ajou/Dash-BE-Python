# Request schemas will be added here

from services.coupon.app.schemas.request.CouponAddSchema import CouponAddSchema
from services.coupon.app.schemas.request.CouponDeleteSchema import CouponDeleteSchema
from services.coupon.app.schemas.request.CouponRegisterSchema import CouponRegisterSchema

__all__ = [
    "CouponAddSchema",
    "CouponDeleteSchema",
    "CouponRegisterSchema",
]

