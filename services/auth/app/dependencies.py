from functools import lru_cache

from services.auth.app.core.JoinService import JoinService
from services.auth.app.core.LoginService import LoginService
from services.auth.app.core.PhoneService import PhoneService
from services.auth.app.db.repositories.accounts import (
    DatabasePhoneAccountLookup,
    SQLAlchemyMemberRepository,
    SQLAlchemyPartnerPinRepository,
    SQLAlchemyPartnerRepository,
)
from services.auth.app.db.repositories.groups import SQLAlchemyGroupRepository
from services.auth.app.db.stores.phone import SQLPhoneAuthTokenStore, SQLPhoneVerificationStore
from services.auth.app.db.stores.refresh_token import SQLRefreshTokenStore

# Coupon repository (optional, for issue mapping)
try:
    from services.coupon.app.db.repositories.coupons import SQLAlchemyCouponRepository
except ImportError:
    SQLAlchemyCouponRepository = None


@lru_cache
def _member_repository() -> SQLAlchemyMemberRepository:
    return SQLAlchemyMemberRepository()


@lru_cache
def _partner_repository() -> SQLAlchemyPartnerRepository:
    return SQLAlchemyPartnerRepository()


@lru_cache
def _partner_pin_repository() -> SQLAlchemyPartnerPinRepository:
    return SQLAlchemyPartnerPinRepository()


@lru_cache
def _phone_verification_store() -> SQLPhoneVerificationStore:
    return SQLPhoneVerificationStore()


@lru_cache
def _phone_auth_store() -> SQLPhoneAuthTokenStore:
    return SQLPhoneAuthTokenStore()


@lru_cache
def _refresh_store() -> SQLRefreshTokenStore:
    return SQLRefreshTokenStore()


@lru_cache
def get_phone_service() -> PhoneService:
    account_lookup = DatabasePhoneAccountLookup(
        member_repository=_member_repository(),
        partner_repository=_partner_repository(),
    )
    return PhoneService(
        account_lookup=account_lookup,
        verification_store=_phone_verification_store(),
        phone_auth_store=_phone_auth_store(),
    )


@lru_cache
def get_login_service() -> LoginService:
    return LoginService(
        member_repository=_member_repository(),
        partner_repository=_partner_repository(),
        partner_pin_repository=_partner_pin_repository(),
        refresh_store=_refresh_store(),
        phone_service=get_phone_service(),
    )


@lru_cache
def _coupon_repository():
    """Coupon repository (optional, for issue mapping)"""
    if SQLAlchemyCouponRepository is None:
        return None
    return SQLAlchemyCouponRepository()


@lru_cache
def get_join_service() -> JoinService:
    return JoinService(
        member_repository=_member_repository(),
        member_create=_member_repository(),  # SQLAlchemyMemberRepository가 MemberCreatePort를 구현
        partner_repository=_partner_repository(),
        partner_create=_partner_repository(),  # SQLAlchemyPartnerRepository가 PartnerCreatePort를 구현
        phone_service=get_phone_service(),
        login_service=get_login_service(),
        issue_mapper=_coupon_repository(),  # Coupon repository for issue mapping
    )


@lru_cache
def get_group_repository() -> SQLAlchemyGroupRepository:
    return SQLAlchemyGroupRepository()

