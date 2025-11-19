"""
쿠폰 관련 비즈니스 로직을 처리하는 서비스
"""
from typing import Protocol

from fastapi_pagination import Page

from services.coupon.app.schemas.response import (
    CouponAddResponse,
    CouponDetailResponse,
    CouponListItem,
    IssueCouponsResponse,
    IssueInfo,
    IssueListItem,
    IssueListResponse,
    IssueRequestResponse,
    PartnerInfo,
    PartnerInfoInCoupons,
    PartnerListItem,
    PartnerListResponse,
    PaymentLogCouponInfo,
    PaymentLogItem,
    PaymentQrResponse,
    PaymentTransactionResponse,
    ProductInfoInCoupons,
    ProductInfoInRequest,
    ProductListItem,
    ProductListResponse,
    RejectInfo,
    RegisterInfo,
    RegisterLogInfo,
    UseLogInfo,
    VendorInfo,
    VendorInfoInCoupons,
    PartnerInfoInRequest,
)


class CouponRepositoryPort(Protocol):
    """쿠폰 Repository 인터페이스"""
    
    async def find_coupons_by_member_id(
        self,
        member_id: int,
        page: int,
        size: int,
    ) -> tuple[list[dict], int]:
        """회원 ID로 쿠폰 목록을 조회합니다"""
        ...


class CouponService:
    """쿠폰 서비스"""
    
    def __init__(self, coupon_repository: CouponRepositoryPort):
        self.coupon_repository = coupon_repository
    
    async def get_coupons_by_member(
        self,
        member_id: int,
        page: int,
        size: int,
    ) -> Page[CouponListItem]:
        """
        회원의 쿠폰 목록을 조회합니다.
        
        Args:
            member_id: 회원 ID
            page: 페이지 번호 (1부터 시작)
            size: 페이지 크기
            
        Returns:
            페이징된 쿠폰 목록
        """
        coupons_data, total = await self.coupon_repository.find_coupons_by_member_id(
            member_id=member_id,
            page=page,
            size=size,
        )
        
        # 딕셔너리를 CouponListItem으로 변환
        items = [
            CouponListItem(
                couponId=item["coupon_id"],
                productName=item["product_name"],
                partnerName=item["partner_name"],
                isUsed=item["is_used"],
                signature=item["signature"],
                createdAt=item["created_at"],
                expiredAt=item["expired_at"],
            )
            for item in coupons_data
        ]
        
        # fastapi-pagination의 Page 객체 생성
        return Page(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size if size > 0 else 0,
        )
    
    async def get_coupon_detail(
        self,
        coupon_id: int,
        member_id: int,
    ) -> CouponDetailResponse:
        """
        쿠폰 상세 정보를 조회합니다.
        
        Args:
            coupon_id: 쿠폰 ID
            member_id: 회원 ID (권한 확인용)
            
        Returns:
            쿠폰 상세 정보
            
        Raises:
            ValueError: 쿠폰이 존재하지 않거나 본인이 등록하지 않은 경우
        """
        coupon_data = await self.coupon_repository.find_coupon_by_id(coupon_id)
        
        if coupon_data is None:
            raise ValueError("ERR-IVD-VALUE")
        
        # 본인이 등록한 쿠폰인지 확인
        if coupon_data["register_id"] != member_id:
            raise ValueError("ERR-NOT-YOURS")
        
        # 파트너 정보
        partner = PartnerInfo(
            partnerId=coupon_data["partner_id"],
            partnerName=coupon_data["partner_name"],
            phones=coupon_data["partner_phones"],
        )
        
        # 등록자 정보
        register = RegisterInfo(
            memberId=coupon_data["member_id"],
            memberName=coupon_data["member_name"],
            memberBirth=coupon_data["member_birth"],
        )
        
        # 등록 로그 정보
        register_log = None
        if coupon_data["register_log_id"]:
            register_log = RegisterLogInfo(
                registerLogId=coupon_data["register_log_id"],
                registeredAt=coupon_data["registered_at"],
            )
        
        # 사용 여부 및 사용 로그 정보
        is_used = coupon_data["use_log_id"] is not None
        use_log = None
        if is_used:
            use_log = UseLogInfo(
                useLogId=coupon_data["use_log_id"],
                usedAt=coupon_data["used_at"],
            )
        
        return CouponDetailResponse(
            id=coupon_data["coupon_id"],
            productName=coupon_data["product_name"],
            partner=partner,
            register_info=register,  # alias="register"로 인해 JSON에서는 "register"로 표시됨
            registerLog=register_log,
            isUsed=is_used,
            useLog=use_log,
            createdAt=coupon_data["created_at"],
            expiredAt=coupon_data["expired_at"],
        )
    
    async def get_coupon_by_registration_code(
        self,
        registration_code: str,
        member_id: int,
    ) -> CouponAddResponse:
        """
        등록코드로 쿠폰 정보를 조회합니다.
        
        Args:
            registration_code: 쿠폰 등록 코드
            member_id: 회원 ID (권한 확인용)
            
        Returns:
            쿠폰 정보
            
        Raises:
            ValueError: 쿠폰이 존재하지 않거나 이미 다른 사람에게 등록된 경우
        """
        # 등록코드로 쿠폰 조회
        coupon_data = await self.coupon_repository.find_coupon_by_registration_code(
            registration_code
        )
        
        if coupon_data is None:
            raise ValueError("ERR-IVD-VALUE")
        
        # 이미 등록된 쿠폰인지 확인 (본인이든 다른 사람이든 등록된 쿠폰은 조회 불가)
        if coupon_data["register_id"] is not None:
            raise ValueError("ERR-NOT-YOURS")
        
        # 쿠폰 정보 반환 (등록하지 않고 조회만)
        return CouponAddResponse(
            couponId=coupon_data["coupon_id"],
            productName=coupon_data["product_name"],
            partnerName=coupon_data["partner_name"],
            createdAt=coupon_data["created_at"],
            expiredAt=coupon_data["expired_at"],
        )
    
    async def register_coupon(
        self,
        coupon_id: int,
        registration_code: str,
        signature_code: str,
        member_id: int,
    ) -> None:
        """
        쿠폰을 회원에게 등록합니다.
        
        Args:
            coupon_id: 쿠폰 ID
            registration_code: 등록 코드 (검증용)
            signature_code: 서명 이미지 코드
            member_id: 회원 ID
            
        Raises:
            ValueError: 쿠폰이 존재하지 않거나, 등록코드가 일치하지 않거나, 이미 다른 사람에게 등록된 경우
        """
        # 쿠폰 ID로 쿠폰 조회
        coupon_data = await self.coupon_repository.find_coupon_by_id_for_register(
            coupon_id
        )
        
        if coupon_data is None:
            raise ValueError("ERR-IVD-VALUE")
        
        # 등록코드 검증
        if coupon_data["registration_code"] != registration_code:
            raise ValueError("ERR-IVD-VALUE")
        
        # 이미 다른 사람이 등록한 쿠폰인지 확인
        if coupon_data["register_id"] is not None:
            if coupon_data["register_id"] != member_id:
                raise ValueError("ERR-NOT-YOURS")
        
        # 쿠폰 등록
        await self.coupon_repository.register_coupon(
            coupon_id=coupon_id,
            member_id=member_id,
            registration_code=registration_code,
            signature_code=signature_code,
        )
    
    async def get_payment_logs_by_member(
        self,
        member_id: int,
        page: int,
        size: int,
    ) -> Page[PaymentLogItem]:
        """
        회원의 결제된 쿠폰 사용 기록을 조회합니다.
        
        Args:
            member_id: 회원 ID
            page: 페이지 번호 (1부터 시작)
            size: 페이지 크기
            
        Returns:
            페이징된 사용 로그 목록
        """
        logs_data, total = await self.coupon_repository.find_payment_logs_by_member_id(
            member_id=member_id,
            page=page,
            size=size,
        )
        
        # PaymentLogItem 리스트 생성
        items = []
        for log_data in logs_data:
            coupon_info = PaymentLogCouponInfo(
                couponId=log_data["coupon_id"],
                productName=log_data["product_name"],
                partnerName=log_data["partner_name"],
                isUsed=True,  # 사용 로그가 있으므로 항상 True
                createdAt=log_data["created_at"],
                expiredAt=log_data["expired_at"],
            )
            
            items.append(
                PaymentLogItem(
                    useLogId=log_data["use_log_id"],
                    coupon=coupon_info,
                    usedAt=log_data["used_at"],
                )
            )
        
        # fastapi-pagination의 Page 객체 생성
        return Page(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size if size > 0 else 0,
        )
    
    async def delete_coupons(
        self,
        coupon_ids: list[int],
        member_id: int,
    ) -> list[CouponDetailResponse]:
        """
        쿠폰들을 삭제 처리합니다.
        
        Args:
            coupon_ids: 삭제할 쿠폰 ID 목록
            member_id: 회원 ID
            
        Returns:
            삭제된 쿠폰 중 사용하지 않은 쿠폰의 상세 정보 목록
            
        Raises:
            ValueError: 쿠폰이 유효하지 않거나 본인이 등록하지 않은 경우
        """
        # 쿠폰 소유권 검증
        valid_ids, invalid_ids = await self.coupon_repository.validate_coupon_ownership(
            coupon_ids=coupon_ids,
            member_id=member_id,
        )
        
        if invalid_ids:
            # 유효하지 않은 쿠폰이 있는 경우
            # 먼저 존재하지 않는 쿠폰인지 확인
            if len(invalid_ids) == len(coupon_ids):
                # 모든 쿠폰이 유효하지 않은 경우
                raise ValueError("ERR-IVD-VALUE")
            else:
                # 일부 쿠폰이 본인이 등록하지 않은 경우
                raise ValueError("ERR-NOT-YOURS")
        
        # 쿠폰 삭제 처리 및 사용하지 않은 쿠폰 정보 반환
        unused_coupons_data = await self.coupon_repository.mark_coupons_as_deleted(
            coupon_ids=valid_ids,
            member_id=member_id,
        )
        
        # 사용하지 않은 쿠폰의 상세 정보를 응답 형식으로 변환
        unused_coupons = []
        for coupon_data in unused_coupons_data:
            partner = PartnerInfo(
                partnerId=coupon_data["partner_id"],
                partnerName=coupon_data["partner_name"],
                phones=coupon_data["partner_phones"],
            )
            
            register = RegisterInfo(
                memberId=coupon_data["member_id"],
                memberName=coupon_data["member_name"],
                memberBirth=coupon_data["member_birth"],
            )
            
            register_log = None
            if coupon_data["register_log_id"]:
                register_log = RegisterLogInfo(
                    registerLogId=coupon_data["register_log_id"],
                    registeredAt=coupon_data["registered_at"],
                )
            
            unused_coupons.append(
                CouponDetailResponse(
                    id=coupon_data["coupon_id"],
                    productName=coupon_data["product_name"],
                    partner=partner,
                    register_info=register,  # alias="register"로 인해 JSON에서는 "register"로 표시됨
                    registerLog=register_log,
                    isUsed=False,
                    useLog=None,
                    createdAt=coupon_data["created_at"],
                    expiredAt=coupon_data["expired_at"],
                )
            )
        
        return unused_coupons
    
    async def get_issues_by_user(
        self,
        subject_type: str,
        subject_id: int,
        status: str | None = None,
        title: str | None = None,
        page: int = 1,
        size: int = 10,
    ) -> IssueListResponse:
        """
        사용자에게 권한이 부여된 쿠폰 발행기록을 조회합니다.
        
        Args:
            subject_type: 사용자 타입 ("member" 또는 "partner")
            subject_id: 사용자 ID
            status: 발행 상태 필터 (선택)
            title: 제목 검색 필터 (선택)
            page: 페이지 번호 (1부터 시작)
            size: 페이지 크기
            
        Returns:
            페이징된 이슈 목록
        """
        issues_data, total = await self.coupon_repository.find_issues_by_user(
            subject_type=subject_type,
            subject_id=subject_id,
            status=status,
            title=title,
            page=page,
            size=size,
        )
        
        # 딕셔너리를 IssueListItem으로 변환
        items = [
            IssueListItem(
                requestId=item["issue_id"],
                title=item["title"],
                productKindCount=item["product_kind_count"],
                status=item["status"],
            )
            for item in issues_data
        ]
        
        # IssueListResponse 생성
        pages = (total + size - 1) // size if size > 0 else 0
        return IssueListResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
    
    async def delete_issues_by_user(
        self,
        issue_ids: list[int],
        subject_type: str,
        subject_id: int,
    ) -> None:
        """
        사용자에게 권한이 부여된 쿠폰 발행기록을 삭제합니다.
        
        Args:
            issue_ids: 삭제할 이슈 ID 목록
            subject_type: 사용자 타입 ("member" 또는 "partner")
            subject_id: 사용자 ID
            
        Raises:
            ValueError: 권한이 없는 이슈가 포함된 경우 ("ERR-NOT-YOURS")
        """
        valid_ids, invalid_ids = await self.coupon_repository.delete_issues_by_user(
            issue_ids=issue_ids,
            subject_type=subject_type,
            subject_id=subject_id,
        )
        
        if invalid_ids:
            # 권한이 없는 이슈가 있는 경우
            raise ValueError("ERR-NOT-YOURS")
    
    async def get_partners_by_keyword(
        self,
        keyword: str | None = None,
        page: int = 1,
        size: int = 10,
    ) -> PartnerListResponse:
        """
        파트너 상호명을 기반으로 파트너를 검색합니다.
        
        Args:
            keyword: 검색 키워드 (파트너 상호명, 선택)
            page: 페이지 번호 (1부터 시작)
            size: 페이지 크기
            
        Returns:
            페이징된 파트너 목록
        """
        partners_data, total = await self.coupon_repository.find_partners_by_keyword(
            keyword=keyword,
            page=page,
            size=size,
        )
        
        # 딕셔너리를 PartnerListItem으로 변환
        items = [
            PartnerListItem(
                partnerId=item["partner_id"],
                partnerName=item["partner_name"],
                numbers=item["numbers"],
            )
            for item in partners_data
        ]
        
        # PartnerListResponse 생성
        pages = (total + size - 1) // size if size > 0 else 0
        return PartnerListResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
    
    async def get_products_by_partner_and_keyword(
        self,
        partner_id: int,
        keyword: str,
        page: int = 1,
        size: int = 10,
    ) -> ProductListResponse:
        """
        특정 파트너에게 등록된 제품 목록을 검색합니다.
        
        Args:
            partner_id: 파트너 ID
            keyword: 검색 키워드 (상품명, 필수)
            page: 페이지 번호 (1부터 시작)
            size: 페이지 크기
            
        Returns:
            페이징된 상품 목록
        """
        products_data, total = await self.coupon_repository.find_products_by_partner_and_keyword(
            partner_id=partner_id,
            keyword=keyword,
            page=page,
            size=size,
        )
        
        # 딕셔너리를 ProductListItem으로 변환
        items = [
            ProductListItem(
                productId=item["product_id"],
                productName=item["product_name"],
            )
            for item in products_data
        ]
        
        # ProductListResponse 생성
        pages = (total + size - 1) // size if size > 0 else 0
        return ProductListResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
    
    async def create_issue_request(
        self,
        vendor_id: int,
        title: str,
        partner: dict,  # {"isNew": bool, "partnerId": int | None, "partnerName": str | None, "partnerPhone": str | None}
        products: list[dict],  # [{"isNew": bool, "productId": int | None, "productName": str | None, "count": int}]
    ) -> None:
        """
        쿠폰 발행 요청을 생성합니다.
        
        Args:
            vendor_id: 요청 벤더 ID (member_id)
            title: 발행 요청 제목
            partner: 파트너 정보
            products: 상품 목록
            
        Raises:
            ValueError: 유효하지 않은 값인 경우 ("ERR-IVD-VALUE")
        """
        # 유효성 검사
        # 1. products가 비어있는 경우
        if not products or len(products) == 0:
            raise ValueError("ERR-IVD-VALUE")
        
        # 2. partner 유효성 검사
        partner_is_new = partner.get("isNew", False)
        if not partner_is_new:
            # 기존 파트너인 경우 partnerId 필수
            if partner.get("partnerId") is None:
                raise ValueError("ERR-IVD-VALUE")
        else:
            # 신규 파트너인 경우 partnerName, partnerPhone 필수
            if not partner.get("partnerName") or not partner.get("partnerPhone"):
                raise ValueError("ERR-IVD-VALUE")
        
        # 3. products 유효성 검사
        products_data = []
        for product in products:
            is_new = product.get("isNew", False)
            count = product.get("count", 0)
            
            if count <= 0:
                raise ValueError("ERR-IVD-VALUE")
            
            if not is_new:
                # 기존 상품인 경우 productId 필수
                if product.get("productId") is None:
                    raise ValueError("ERR-IVD-VALUE")
            else:
                # 신규 상품인 경우 productName 필수
                if not product.get("productName"):
                    raise ValueError("ERR-IVD-VALUE")
            
            products_data.append({
                "is_new": is_new,
                "product_id": product.get("productId"),
                "product_name": product.get("productName"),
                "count": count,
            })
        
        # Repository 호출
        await self.coupon_repository.create_issue_request(
            vendor_id=vendor_id,
            title=title,
            partner_is_new=partner_is_new,
            partner_id=partner.get("partnerId"),
            partner_name=partner.get("partnerName"),
            partner_phone=partner.get("partnerPhone"),
            products=products_data,
        )
    
    async def get_issue_request(
        self,
        issue_id: int,
        subject_type: str,
        subject_id: int,
    ) -> IssueRequestResponse:
        """
        발행기록의 발행요청서 정보를 조회합니다.
        
        Args:
            issue_id: 발행기록 ID
            subject_type: 사용자 타입 ("member" 또는 "partner")
            subject_id: 사용자 ID
            
        Returns:
            발행요청서 정보
            
        Raises:
            ValueError: 권한이 없거나 존재하지 않는 발행기록인 경우 ("ERR-IVD-VALUE")
        """
        from libs.common import ensure_kst
        
        issue_data = await self.coupon_repository.find_issue_request_by_id(
            issue_id=issue_id,
            subject_type=subject_type,
            subject_id=subject_id,
        )
        
        if not issue_data:
            raise ValueError("ERR-IVD-VALUE")
        
        # 날짜 포맷팅 (YYYY.MM.DD HH:MM:SS)
        requested_at = ensure_kst(issue_data["requested_at"])
        requested_at_str = requested_at.strftime("%Y.%m.%d %H:%M:%S") if requested_at else ""
        
        # Response 객체 생성
        return IssueRequestResponse(
            issueId=issue_data["issue_id"],
            title=issue_data["title"],
            status=issue_data["status"],
            vendor=VendorInfo(
                memberId=issue_data["vendor"]["member_id"],
                memberName=issue_data["vendor"]["member_name"],
                number=issue_data["vendor"]["number"],
            ),
            partner=PartnerInfoInRequest(
                partnerId=issue_data["partner"]["partner_id"],
                partnerName=issue_data["partner"]["partner_name"],
                number=issue_data["partner"]["number"],
            ),
            products=[
                ProductInfoInRequest(
                    productId=product["product_id"],
                    productName=product["product_name"],
                    count=product["count"],
                )
                for product in issue_data["products"]
            ],
            requestedAt=requested_at_str,
        )
    
    async def get_issue_coupons(
        self,
        issue_id: int,
        subject_type: str,
        subject_id: int,
    ) -> IssueCouponsResponse:
        """
        발행기록의 쿠폰 내역 또는 반려 정보를 조회합니다.
        
        Args:
            issue_id: 발행기록 ID
            subject_type: 사용자 타입 ("member" 또는 "partner")
            subject_id: 사용자 ID
            
        Returns:
            쿠폰 내역 또는 반려 정보
            
        Raises:
            ValueError: 권한이 없거나 존재하지 않는 발행기록인 경우 ("ERR-IVD-VALUE")
            ValueError: 아직 결정되지 않은 발행기록인 경우 ("ERR-NOT-DECIDED")
        """
        from datetime import timedelta
        from libs.common import ensure_kst
        
        issue_data = await self.coupon_repository.find_issue_coupons_by_id(
            issue_id=issue_id,
            subject_type=subject_type,
            subject_id=subject_id,
        )
        
        if not issue_data:
            raise ValueError("ERR-IVD-VALUE")
        
        # 아직 결정되지 않은 경우
        if issue_data.get("status") == "PENDING":
            raise ValueError("ERR-NOT-DECIDED")
        
        # 승인된 경우
        if issue_data.get("status") == "APPROVED":
            requested_at = ensure_kst(issue_data["requested_at"])
            decided_at = ensure_kst(issue_data["decided_at"])
            
            # expiredAt 계산: decidedAt + validDays
            expired_at = None
            if decided_at:
                expired_at = decided_at + timedelta(days=issue_data["valid_days"])
            
            requested_at_str = requested_at.strftime("%Y.%m.%d %H:%M:%S") if requested_at else ""
            decided_at_str = decided_at.strftime("%Y.%m.%d %H:%M:%S") if decided_at else ""
            expired_at_str = expired_at.strftime("%Y.%m.%d %H:%M:%S") if expired_at else ""
            
            return IssueCouponsResponse(
                isApproved=True,
                issueInfo=IssueInfo(
                    requestedIssueCount=issue_data["requested_issue_count"],
                    approvedIssueCount=issue_data["approved_issue_count"],
                    validDays=issue_data["valid_days"],
                    vendor=VendorInfoInCoupons(
                        memberId=issue_data["vendor"]["member_id"],
                        memberName=issue_data["vendor"]["member_name"],
                        number=issue_data["vendor"]["number"],
                    ),
                    partner=PartnerInfoInCoupons(
                        partnerId=issue_data["partner"]["partner_id"],
                        partnerName=issue_data["partner"]["partner_name"],
                        number=issue_data["partner"]["number"],
                    ),
                    products=[
                        ProductInfoInCoupons(
                            productId=product["product_id"],
                            productName=product["product_name"],
                            count=product["count"],
                        )
                        for product in issue_data["products"]
                    ],
                    requestedAt=requested_at_str,
                    decidedAt=decided_at_str,
                    expiredAt=expired_at_str,
                ),
                rejectInfo=None,
            )
        
        # 반려된 경우
        elif issue_data.get("status") == "REJECTED":
            requested_at = ensure_kst(issue_data["requested_at"])
            decided_at = ensure_kst(issue_data["decided_at"])
            
            requested_at_str = requested_at.strftime("%Y.%m.%d %H:%M:%S") if requested_at else ""
            decided_at_str = decided_at.strftime("%Y.%m.%d %H:%M:%S") if decided_at else ""
            
            return IssueCouponsResponse(
                isApproved=False,
                issueInfo=None,
                rejectInfo=RejectInfo(
                    requestedIssueCount=issue_data["requested_issue_count"],
                    reason=issue_data["reason"],
                    requestedAt=requested_at_str,
                    decidedAt=decided_at_str,
                ),
            )
        
        # 알 수 없는 상태
        raise ValueError("ERR-IVD-VALUE")
    
    async def decide_issue(
        self,
        issue_id: int,
        partner_id: int,
        is_approved: bool,
        products: list[dict] | None = None,  # [{"isNew": bool, "productId": int | None, "productName": str | None, "count": int}]
        reason: str | None = None,
    ) -> None:
        """
        발행기록에 대한 파트너의 결정을 처리합니다.
        
        Args:
            issue_id: 발행기록 ID
            partner_id: 파트너 ID
            is_approved: 승인 여부
            products: 승인된 상품 목록 (is_approved가 True인 경우 필수)
            reason: 반려 사유 (is_approved가 False인 경우 필수)
            
        Raises:
            ValueError: 유효하지 않은 값인 경우 ("ERR-IVD-VALUE")
            ValueError: 이미 결정된 발행기록인 경우 ("ERR-ALREADY-DECIDED")
        """
        # 유효성 검사
        if is_approved:
            if not products or len(products) == 0:
                raise ValueError("ERR-IVD-VALUE")
            
            # products 유효성 검사
            products_data = []
            for product in products:
                is_new = product.get("isNew", False)
                count = product.get("count", 0)
                
                if count <= 0:
                    raise ValueError("ERR-IVD-VALUE")
                
                if not is_new:
                    # 기존 상품인 경우 productId 필수
                    if product.get("productId") is None:
                        raise ValueError("ERR-IVD-VALUE")
                else:
                    # 신규 상품인 경우 productName 필수
                    if not product.get("productName"):
                        raise ValueError("ERR-IVD-VALUE")
                
                products_data.append({
                    "is_new": is_new,
                    "product_id": product.get("productId"),
                    "product_name": product.get("productName"),
                    "count": count,
                })
        else:
            if not reason:
                raise ValueError("ERR-IVD-VALUE")
        
        # Repository 호출
        await self.coupon_repository.decide_issue(
            issue_id=issue_id,
            partner_id=partner_id,
            is_approved=is_approved,
            products=products_data if is_approved else None,
            reason=reason if not is_approved else None,
        )
    
    async def create_self_issue(
        self,
        partner_id: int,
        title: str,
        products: list[dict],  # [{"isNew": bool, "productId": int | None, "productName": str | None, "count": int}]
    ) -> None:
        """
        파트너가 직접 쿠폰을 발행합니다.
        
        Args:
            partner_id: 파트너 ID
            title: 발행 제목
            products: 상품 목록
            
        Raises:
            ValueError: 유효하지 않은 값인 경우 ("ERR-IVD-VALUE")
        """
        # 유효성 검사
        # 1. products가 비어있는 경우
        if not products or len(products) == 0:
            raise ValueError("ERR-IVD-VALUE")
        
        # 2. products 유효성 검사
        products_data = []
        for product in products:
            is_new = product.get("isNew", False)
            count = product.get("count", 0)
            
            if count <= 0:
                raise ValueError("ERR-IVD-VALUE")
            
            if not is_new:
                # 기존 상품인 경우 productId 필수
                if product.get("productId") is None:
                    raise ValueError("ERR-IVD-VALUE")
            else:
                # 신규 상품인 경우 productName 필수
                if not product.get("productName"):
                    raise ValueError("ERR-IVD-VALUE")
            
            products_data.append({
                "is_new": is_new,
                "product_id": product.get("productId"),
                "product_name": product.get("productName"),
                "count": count,
            })
        
        # Repository 호출
        await self.coupon_repository.create_self_issue(
            partner_id=partner_id,
            title=title,
            products=products_data,
        )
    
    async def get_payment_transaction(
        self,
        payment_code: str,
    ) -> PaymentTransactionResponse:
        """
        결제코드로 쿠폰 정보를 조회합니다.
        
        Args:
            payment_code: 결제코드 (registration_code)
            
        Returns:
            쿠폰 정보
            
        Raises:
            ValueError: 쿠폰이 존재하지 않는 경우 ("ERR-IVD-VALUE")
            ValueError: 이미 사용한 경우 ("ERR-ALREADY-USED")
        """
        from services.coupon.app.schemas.response import PaymentTransactionResponse
        
        # 결제코드로 쿠폰 조회
        coupon_data = await self.coupon_repository.find_coupon_by_payment_code(
            payment_code
        )
        
        if coupon_data is None:
            raise ValueError("ERR-IVD-VALUE")
        
        # 이미 사용한 경우 확인
        if coupon_data["use_log_id"] is not None:
            raise ValueError("ERR-ALREADY-USED")
        
        # 쿠폰 정보 반환
        return PaymentTransactionResponse(
            couponId=coupon_data["coupon_id"],
            productName=coupon_data["product_name"],
            vendorName=coupon_data["vendor_name"],
            createdAt=coupon_data["created_at"],
            expiredAt=coupon_data["expired_at"],
        )
    
    async def confirm_payment_transaction(
        self,
        payment_code: str,
    ) -> None:
        """
        결제코드로 쿠폰을 결제처리합니다.
        
        Args:
            payment_code: 결제코드 (registration_code)
            
        Raises:
            ValueError: 쿠폰이 존재하지 않는 경우 ("ERR-IVD-VALUE")
            ValueError: 이미 사용한 경우 ("ERR-ALREADY-USED")
        """
        await self.coupon_repository.confirm_payment_transaction(
            payment_code=payment_code,
        )
    
    async def create_payment_qr(
        self,
        coupon_id: int,
        member_id: int,
    ) -> PaymentQrResponse:
        """
        결제 QR 코드를 생성합니다.
        
        Args:
            coupon_id: 쿠폰 ID
            member_id: 회원 ID (소유권 확인용)
            
        Returns:
            결제 QR 코드 정보
            
        Raises:
            ValueError: 쿠폰이 존재하지 않거나 소유하지 않은 경우 ("ERR-IVD-VALUE")
            ValueError: 이미 사용한 경우 ("ERR-IVD-VALUE")
            ValueError: 쿠폰이 만료된 경우 ("ERR-IVD-VALUE")
        """
        from datetime import timedelta
        import httpx
        from services.coupon.app.schemas.response import PaymentQrResponse
        from services.coupon.app.db.connection import settings
        from libs.common import now_kst
        
        # 1. 쿠폰 정보 조회 (소유권 확인 포함)
        coupon_data = await self.coupon_repository.find_coupon_by_id_for_payment_qr(
            coupon_id=coupon_id,
            member_id=member_id,
        )
        
        if coupon_data is None:
            # 쿠폰이 존재하지 않거나 소유하지 않은 경우
            # 먼저 쿠폰이 존재하는지 확인
            coupon_exists = await self.coupon_repository.find_coupon_by_id(coupon_id)
            if coupon_exists is None:
                raise ValueError("ERR-IVD-VALUE")
            else:
                # 쿠폰은 존재하지만 소유하지 않은 경우
                raise ValueError("ERR-NOT-YOURS")
        
        # 2. 쿠폰 유효성 검사
        # - 이미 사용한 경우
        if coupon_data["use_log_id"] is not None:
            raise ValueError("ERR-IVD-VALUE")
        
        # - 만료된 경우
        now = now_kst()
        expired_at_str = coupon_data["expired_at"]
        from datetime import datetime
        from libs.common import KST_TIMEZONE
        expired_at = datetime.strptime(expired_at_str, "%Y-%m-%d %H:%M:%S")
        # timezone-naive를 timezone-aware로 변환 (KST로 가정)
        expired_at = expired_at.replace(tzinfo=KST_TIMEZONE)
        if expired_at < now:
            raise ValueError("ERR-IVD-VALUE")
        
        # 3. 기존 활성 QR 코드 만료 처리
        await self.coupon_repository.expire_payment_qr_by_coupon_id(coupon_id)
        
        # 4. 결제코드 생성 (UUID)
        import uuid
        payment_code = str(uuid.uuid4())
        
        # 5. 새로운 QR 코드 만료 시간 설정 (1분 후)
        qr_expired_at = now + timedelta(minutes=1)
        
        # 6. 결제 QR 코드 DB에 저장
        await self.coupon_repository.create_payment_qr(
            coupon_id=coupon_id,
            payment_code=payment_code,
            expired_at=qr_expired_at,
        )
        
        # 7. Media 서버로 QR 코드 이미지 생성 요청
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{settings.MEDIA_SERVICE_URL}/generate/qrcode",
                    json={
                        "data": payment_code,
                        "file_name": f"payment_qr_{coupon_id}.png",
                    },
                )
                response.raise_for_status()
                qr_data = response.json()
                file_id = qr_data["fileId"]
        except Exception as e:
            # Media 서버 요청 실패 시 예외 발생
            raise ValueError(f"QR 코드 생성 실패: {str(e)}")
        
        # 8. 응답 생성
        code_img_url = f"{settings.MEDIA_SERVICE_URL}/media/{file_id}"
        
        return PaymentQrResponse(
            codeImg=code_img_url,
            expiredAt=qr_expired_at.strftime("%Y-%m-%d %H:%M:%S"),
        )

