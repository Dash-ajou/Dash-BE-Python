# Request schemas will be added here

from services.coupon.app.schemas.request.CouponAddSchema import CouponAddSchema
from services.coupon.app.schemas.request.CouponDeleteSchema import CouponDeleteSchema
from services.coupon.app.schemas.request.CouponRegisterSchema import CouponRegisterSchema
from services.coupon.app.schemas.request.IssueDeleteSchema import IssueDeleteSchema

__all__ = [
    "CouponAddSchema",
    "CouponDeleteSchema",
    "CouponRegisterSchema",
    "IssueDeleteSchema",
]

