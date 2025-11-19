# Request schemas will be added here

from services.coupon.app.schemas.request.CouponAddSchema import CouponAddSchema
from services.coupon.app.schemas.request.CouponDeleteSchema import CouponDeleteSchema
from services.coupon.app.schemas.request.CouponRegisterSchema import CouponRegisterSchema
from services.coupon.app.schemas.request.IssueDeleteSchema import IssueDeleteSchema
from services.coupon.app.schemas.request.IssueRequestSchema import (
    IssueRequestSchema,
    PartnerRequestSchema,
    ProductRequestSchema,
)

__all__ = [
    "CouponAddSchema",
    "CouponDeleteSchema",
    "CouponRegisterSchema",
    "IssueDeleteSchema",
    "IssueRequestSchema",
    "PartnerRequestSchema",
    "ProductRequestSchema",
]

