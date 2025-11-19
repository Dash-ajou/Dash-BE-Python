# Request schemas will be added here

from services.coupon.app.schemas.request.CouponAddSchema import CouponAddSchema
from services.coupon.app.schemas.request.CouponDeleteSchema import CouponDeleteSchema
from services.coupon.app.schemas.request.CouponRegisterSchema import CouponRegisterSchema
from services.coupon.app.schemas.request.IssueDeleteSchema import IssueDeleteSchema
from services.coupon.app.schemas.request.IssueDecisionSchema import (
    IssueDecisionSchema,
    ProductDecisionSchema,
)
from services.coupon.app.schemas.request.IssueRequestSchema import (
    IssueRequestSchema,
    PartnerRequestSchema,
    ProductRequestSchema,
)
from services.coupon.app.schemas.request.IssueSelfIssueSchema import (
    IssueSelfIssueSchema,
    ProductSelfIssueSchema,
)
from services.coupon.app.schemas.request.PaymentConfirmSchema import (
    PaymentConfirmSchema,
)
from services.coupon.app.schemas.request.PaymentTransactionSchema import (
    PaymentTransactionSchema,
)
from services.coupon.app.schemas.request.PaymentQrSchema import PaymentQrSchema

__all__ = [
    "CouponAddSchema",
    "CouponDeleteSchema",
    "CouponRegisterSchema",
    "IssueDeleteSchema",
    "IssueDecisionSchema",
    "IssueRequestSchema",
    "IssueSelfIssueSchema",
    "PartnerRequestSchema",
    "PaymentConfirmSchema",
    "PaymentQrSchema",
    "PaymentTransactionSchema",
    "ProductDecisionSchema",
    "ProductRequestSchema",
    "ProductSelfIssueSchema",
]

