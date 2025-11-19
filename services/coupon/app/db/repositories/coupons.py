"""
쿠폰 관련 Repository 구현
"""
import asyncio
from typing import Callable, Protocol, Tuple

from sqlalchemy import text

from services.coupon.app.db.session import session_scope


class CouponRepositoryPort(Protocol):
    """쿠폰 Repository 인터페이스"""
    
    async def find_coupons_by_member_id(
        self,
        member_id: int,
        page: int,
        size: int,
    ) -> Tuple[list[dict], int]:
        """
        회원 ID로 쿠폰 목록을 조회합니다 (페이징 지원).
        
        Args:
            member_id: 회원 ID
            page: 페이지 번호 (1부터 시작)
            size: 페이지 크기
            
        Returns:
            (쿠폰 목록, 전체 개수) 튜플
        """
        ...
    
    async def find_coupon_by_id(
        self,
        coupon_id: int,
    ) -> dict | None:
        """
        쿠폰 ID로 쿠폰 상세 정보를 조회합니다.
        
        Args:
            coupon_id: 쿠폰 ID
            
        Returns:
            쿠폰 상세 정보 딕셔너리 또는 None
        """
        ...
    
    async def validate_coupon_ownership(
        self,
        coupon_ids: list[int],
        member_id: int,
    ) -> tuple[list[int], list[int]]:
        """
        쿠폰 소유권을 검증합니다.
        
        Args:
            coupon_ids: 검증할 쿠폰 ID 목록
            member_id: 회원 ID
            
        Returns:
            (유효한 쿠폰 ID 목록, 유효하지 않은 쿠폰 ID 목록) 튜플
        """
        ...
    
    async def mark_coupons_as_deleted(
        self,
        coupon_ids: list[int],
        member_id: int,
    ) -> list[dict]:
        """
        쿠폰들을 삭제 처리합니다 (register_logs에 deleted_at 기록).
        삭제된 쿠폰 중 사용하지 않은 쿠폰의 상세 정보를 반환합니다.
        
        Args:
            coupon_ids: 삭제할 쿠폰 ID 목록
            member_id: 회원 ID
            
        Returns:
            삭제된 쿠폰 중 사용하지 않은 쿠폰의 상세 정보 목록
        """
        ...
    
    async def find_payment_logs_by_member_id(
        self,
        member_id: int,
        page: int,
        size: int,
    ) -> Tuple[list[dict], int]:
        """
        회원 ID로 결제된 쿠폰의 사용 기록을 조회합니다 (페이징 지원).
        
        Args:
            member_id: 회원 ID
            page: 페이지 번호 (1부터 시작)
            size: 페이지 크기
            
        Returns:
            (사용 로그 목록, 전체 개수) 튜플
        """
        ...
    
    async def find_coupon_by_registration_code(
        self,
        registration_code: str,
    ) -> dict | None:
        """
        등록코드로 쿠폰을 조회합니다.
        
        Args:
            registration_code: 쿠폰 등록 코드
            
        Returns:
            쿠폰 정보 딕셔너리 또는 None
        """
        ...
    
    async def register_coupon(
        self,
        coupon_id: int,
        member_id: int,
        registration_code: str,
        signature_code: str,
    ) -> None:
        """
        쿠폰을 회원에게 등록합니다.
        
        Args:
            coupon_id: 쿠폰 ID
            member_id: 회원 ID
            registration_code: 등록 코드 (검증용)
            signature_code: 서명 이미지 코드
        """
        ...


class _SQLRepositoryBase:
    """SQL Repository 기본 클래스"""
    def __init__(self, session_factory: Callable = session_scope):
        self._session_factory = session_factory

    async def _run_in_thread(self, func: Callable):
        """동기 함수를 비동기로 실행"""
        return await asyncio.to_thread(func)


class SQLAlchemyCouponRepository(_SQLRepositoryBase):
    """SQLAlchemy를 사용한 쿠폰 Repository 구현"""
    
    async def find_coupons_by_member_id(
        self,
        member_id: int,
        page: int,
        size: int,
    ) -> Tuple[list[dict], int]:
        """
        회원 ID로 쿠폰 목록을 조회합니다 (페이징 지원).
        
        사용한 쿠폰도 포함하여 조회합니다.
        """
        def _query():
            offset = (page - 1) * size
            
            with self._session_factory() as session:
                # 전체 개수 조회 (삭제되지 않은 쿠폰만)
                count_query = text("""
                    SELECT COUNT(*) as total
                    FROM coupons c
                    LEFT JOIN register_logs rl ON c.register_log_id = rl.register_log_id
                    WHERE c.register_id = :member_id
                      AND (rl.deleted_at IS NULL OR rl.register_log_id IS NULL)
                """)
                count_result = session.execute(count_query, {"member_id": member_id}).fetchone()
                total = count_result[0] if count_result else 0
                
                # 쿠폰 목록 조회 (JOIN으로 상품명, 파트너명 포함, 삭제되지 않은 쿠폰만)
                query = text("""
                    SELECT 
                        c.coupon_id,
                        p.product_name,
                        pu.partner_name,
                        CASE WHEN c.use_log_id IS NOT NULL THEN 1 ELSE 0 END as is_used,
                        '' as signature,
                        DATE_FORMAT(c.created_at, '%Y-%m-%d %H:%i:%s') as created_at,
                        DATE_FORMAT(c.expired_at, '%Y-%m-%d %H:%i:%s') as expired_at
                    FROM coupons c
                    INNER JOIN products p ON c.product_id = p.product_id
                    INNER JOIN partner_users pu ON c.partner_id = pu.partner_id
                    LEFT JOIN register_logs rl ON c.register_log_id = rl.register_log_id
                    WHERE c.register_id = :member_id
                      AND (rl.deleted_at IS NULL OR rl.register_log_id IS NULL)
                    ORDER BY c.created_at DESC
                    LIMIT :size OFFSET :offset
                """)
                
                result = session.execute(
                    query,
                    {
                        "member_id": member_id,
                        "size": size,
                        "offset": offset,
                    }
                ).fetchall()
                
                # 결과를 딕셔너리 리스트로 변환
                coupons = []
                for row in result:
                    coupons.append({
                        "coupon_id": row[0],
                        "product_name": row[1],
                        "partner_name": row[2],
                        "is_used": bool(row[3]),
                        "signature": row[4] or "",
                        "created_at": row[5],
                        "expired_at": row[6],
                    })
                
                return (coupons, total)
        
        return await self._run_in_thread(_query)
    
    async def find_coupon_by_id(
        self,
        coupon_id: int,
    ) -> dict | None:
        """쿠폰 ID로 쿠폰 상세 정보를 조회합니다."""
        def _query():
            with self._session_factory() as session:
                # 쿠폰 기본 정보 및 관련 정보 조회 (삭제되지 않은 쿠폰만)
                query = text("""
                    SELECT 
                        c.coupon_id,
                        c.register_id,
                        c.use_log_id,
                        c.register_log_id,
                        p.product_name,
                        pu.partner_id,
                        pu.partner_name,
                        m.member_id,
                        m.member_name,
                        DATE_FORMAT(m.member_birth, '%Y-%m-%d') as member_birth,
                        DATE_FORMAT(c.created_at, '%Y-%m-%d %H:%i:%s') as created_at,
                        DATE_FORMAT(c.expired_at, '%Y-%m-%d %H:%i:%s') as expired_at,
                        DATE_FORMAT(rl.registered_at, '%Y-%m-%d %H:%i:%s') as registered_at,
                        DATE_FORMAT(ul.used_at, '%Y-%m-%d %H:%i:%s') as used_at
                    FROM coupons c
                    INNER JOIN products p ON c.product_id = p.product_id
                    INNER JOIN partner_users pu ON c.partner_id = pu.partner_id
                    LEFT JOIN members m ON c.register_id = m.member_id
                    LEFT JOIN register_logs rl ON c.register_log_id = rl.register_log_id
                    LEFT JOIN use_logs ul ON c.use_log_id = ul.use_log_id
                    WHERE c.coupon_id = :coupon_id
                      AND (rl.deleted_at IS NULL OR rl.register_log_id IS NULL)
                    LIMIT 1
                """)
                
                result = session.execute(query, {"coupon_id": coupon_id}).fetchone()
                
                if result is None:
                    return None
                
                # 파트너 전화번호 조회
                partner_id = result[5]  # partner_id는 인덱스 5
                phone_query = text("""
                    SELECT number
                    FROM phones
                    WHERE contact_account_type = 'PARTNER'
                      AND account_id = :partner_id
                    ORDER BY phone_id
                """)
                phone_results = session.execute(
                    phone_query,
                    {"partner_id": partner_id}
                ).fetchall()
                partner_phones = [row[0] for row in phone_results]
                
                return {
                    "coupon_id": result[0],
                    "register_id": result[1],
                    "use_log_id": result[2],
                    "register_log_id": result[3],
                    "product_name": result[4],
                    "partner_id": result[5],
                    "partner_name": result[6],
                    "partner_phones": partner_phones,
                    "member_id": result[7],
                    "member_name": result[8],
                    "member_birth": result[9],
                    "created_at": result[10],
                    "expired_at": result[11],
                    "registered_at": result[12],
                    "used_at": result[13],
                }
        
        return await self._run_in_thread(_query)
    
    async def validate_coupon_ownership(
        self,
        coupon_ids: list[int],
        member_id: int,
    ) -> tuple[list[int], list[int]]:
        """쿠폰 소유권을 검증합니다."""
        if not coupon_ids:
            return ([], [])
        
        def _validate():
            with self._session_factory() as session:
                query = text("""
                    SELECT coupon_id, register_id
                    FROM coupons c
                    WHERE c.coupon_id IN :coupon_ids
                """)
                result = session.execute(
                    query,
                    {"coupon_ids": tuple(coupon_ids)}
                ).fetchall()
                
                valid_ids = []
                invalid_ids = []
                found_ids = {row[0] for row in result}
                
                for coupon_id in coupon_ids:
                    if coupon_id not in found_ids:
                        invalid_ids.append(coupon_id)
                    else:
                        # 소유권 확인
                        row = next((r for r in result if r[0] == coupon_id), None)
                        if row and row[1] == member_id:
                            valid_ids.append(coupon_id)
                        else:
                            invalid_ids.append(coupon_id)
                
                return (valid_ids, invalid_ids)
        
        return await self._run_in_thread(_validate)
    
    async def mark_coupons_as_deleted(
        self,
        coupon_ids: list[int],
        member_id: int,
    ) -> list[dict]:
        """쿠폰들을 삭제 처리합니다 (register_logs에 deleted_at 기록)."""
        if not coupon_ids:
            return []
        
        def _delete():
            with self._session_factory() as session:
                # 삭제할 쿠폰들의 register_log_id 조회
                query = text("""
                    SELECT 
                        c.coupon_id,
                        c.register_log_id,
                        c.use_log_id,
                        p.product_name,
                        pu.partner_id,
                        pu.partner_name,
                        m.member_id,
                        m.member_name,
                        DATE_FORMAT(m.member_birth, '%Y-%m-%d') as member_birth,
                        DATE_FORMAT(c.created_at, '%Y-%m-%d %H:%i:%s') as created_at,
                        DATE_FORMAT(c.expired_at, '%Y-%m-%d %H:%i:%s') as expired_at,
                        DATE_FORMAT(rl.registered_at, '%Y-%m-%d %H:%i:%s') as registered_at
                    FROM coupons c
                    INNER JOIN products p ON c.product_id = p.product_id
                    INNER JOIN partner_users pu ON c.partner_id = pu.partner_id
                    LEFT JOIN members m ON c.register_id = m.member_id
                    LEFT JOIN register_logs rl ON c.register_log_id = rl.register_log_id
                    WHERE c.coupon_id IN :coupon_ids
                      AND c.register_id = :member_id
                """)
                
                coupons = session.execute(
                    query,
                    {"coupon_ids": tuple(coupon_ids), "member_id": member_id}
                ).fetchall()
                
                if not coupons:
                    return []
                
                # register_logs에 deleted_at 업데이트
                register_log_ids = [row[1] for row in coupons if row[1] is not None]
                if register_log_ids:
                    update_query = text("""
                        UPDATE register_logs
                        SET deleted_at = CURRENT_TIMESTAMP
                        WHERE register_log_id IN :register_log_ids
                          AND deleted_at IS NULL
                    """)
                    session.execute(
                        update_query,
                        {"register_log_ids": tuple(register_log_ids)}
                    )
                
                # 사용하지 않은 쿠폰의 상세 정보 수집
                unused_coupons = []
                for row in coupons:
                    coupon_id = row[0]
                    use_log_id = row[2]
                    
                    # 사용하지 않은 쿠폰만 수집
                    if use_log_id is None:
                        # 파트너 전화번호 조회
                        partner_id = row[4]
                        phone_query = text("""
                            SELECT number
                            FROM phones
                            WHERE contact_account_type = 'PARTNER'
                              AND account_id = :partner_id
                            ORDER BY phone_id
                        """)
                        phone_results = session.execute(
                            phone_query,
                            {"partner_id": partner_id}
                        ).fetchall()
                        partner_phones = [p[0] for p in phone_results]
                        
                        unused_coupons.append({
                            "coupon_id": coupon_id,
                            "register_log_id": row[1],
                            "product_name": row[3],
                            "partner_id": partner_id,
                            "partner_name": row[5],
                            "partner_phones": partner_phones,
                            "member_id": row[6],
                            "member_name": row[7],
                            "member_birth": row[8],
                            "created_at": row[9],
                            "expired_at": row[10],
                            "registered_at": row[11],
                        })
                
                session.commit()
                return unused_coupons
        
        return await self._run_in_thread(_delete)
    
    async def find_payment_logs_by_member_id(
        self,
        member_id: int,
        page: int,
        size: int,
    ) -> Tuple[list[dict], int]:
        """회원 ID로 결제된 쿠폰의 사용 기록을 조회합니다."""
        def _query():
            offset = (page - 1) * size
            
            with self._session_factory() as session:
                # 전체 개수 조회 (사용된 쿠폰만, 삭제되지 않은 쿠폰만)
                count_query = text("""
                    SELECT COUNT(*) as total
                    FROM use_logs ul
                    INNER JOIN coupons c ON ul.coupon_id = c.coupon_id
                    LEFT JOIN register_logs rl ON c.register_log_id = rl.register_log_id
                    WHERE c.register_id = :member_id
                      AND (rl.deleted_at IS NULL OR rl.register_log_id IS NULL)
                """)
                count_result = session.execute(count_query, {"member_id": member_id}).fetchone()
                total = count_result[0] if count_result else 0
                
                # 사용 로그 목록 조회 (JOIN으로 쿠폰 정보 포함)
                query = text("""
                    SELECT 
                        ul.use_log_id,
                        c.coupon_id,
                        p.product_name,
                        pu.partner_name,
                        DATE_FORMAT(c.created_at, '%Y-%m-%d %H:%i:%s') as created_at,
                        DATE_FORMAT(c.expired_at, '%Y-%m-%d %H:%i:%s') as expired_at,
                        DATE_FORMAT(ul.used_at, '%Y-%m-%d %H:%i:%s') as used_at
                    FROM use_logs ul
                    INNER JOIN coupons c ON ul.coupon_id = c.coupon_id
                    INNER JOIN products p ON c.product_id = p.product_id
                    INNER JOIN partner_users pu ON c.partner_id = pu.partner_id
                    LEFT JOIN register_logs rl ON c.register_log_id = rl.register_log_id
                    WHERE c.register_id = :member_id
                      AND (rl.deleted_at IS NULL OR rl.register_log_id IS NULL)
                    ORDER BY ul.used_at DESC
                    LIMIT :size OFFSET :offset
                """)
                
                result = session.execute(
                    query,
                    {
                        "member_id": member_id,
                        "size": size,
                        "offset": offset,
                    }
                ).fetchall()
                
                # 결과를 딕셔너리 리스트로 변환
                logs = []
                for row in result:
                    logs.append({
                        "use_log_id": row[0],
                        "coupon_id": row[1],
                        "product_name": row[2],
                        "partner_name": row[3],
                        "created_at": row[4],
                        "expired_at": row[5],
                        "used_at": row[6],
                    })
                
                return (logs, total)
        
        return await self._run_in_thread(_query)
    
    async def find_coupon_by_registration_code(
        self,
        registration_code: str,
    ) -> dict | None:
        """등록코드로 쿠폰을 조회합니다."""
        def _query():
            with self._session_factory() as session:
                query = text("""
                    SELECT 
                        c.coupon_id,
                        c.register_id,
                        p.product_name,
                        pu.partner_name,
                        DATE_FORMAT(c.created_at, '%Y-%m-%d %H:%i:%s') as created_at,
                        DATE_FORMAT(c.expired_at, '%Y-%m-%d %H:%i:%s') as expired_at
                    FROM coupons c
                    INNER JOIN products p ON c.product_id = p.product_id
                    INNER JOIN partner_users pu ON c.partner_id = pu.partner_id
                    WHERE c.registration_code = :registration_code
                    LIMIT 1
                """)
                
                result = session.execute(
                    query,
                    {"registration_code": registration_code}
                ).fetchone()
                
                if result is None:
                    return None
                
                return {
                    "coupon_id": result[0],
                    "register_id": result[1],
                    "product_name": result[2],
                    "partner_name": result[3],
                    "created_at": result[4],
                    "expired_at": result[5],
                }
        
        return await self._run_in_thread(_query)
    
    async def find_coupon_by_id_for_register(
        self,
        coupon_id: int,
    ) -> dict | None:
        """쿠폰 등록을 위해 쿠폰 ID로 쿠폰을 조회합니다."""
        def _query():
            with self._session_factory() as session:
                query = text("""
                    SELECT 
                        c.coupon_id,
                        c.registration_code,
                        c.register_id
                    FROM coupons c
                    WHERE c.coupon_id = :coupon_id
                    LIMIT 1
                """)
                
                result = session.execute(
                    query,
                    {"coupon_id": coupon_id}
                ).fetchone()
                
                if result is None:
                    return None
                
                return {
                    "coupon_id": result[0],
                    "registration_code": result[1],
                    "register_id": result[2],
                }
        
        return await self._run_in_thread(_query)
    
    async def register_coupon(
        self,
        coupon_id: int,
        member_id: int,
        registration_code: str,
        signature_code: str,
    ) -> None:
        """쿠폰을 회원에게 등록합니다."""
        def _register():
            with self._session_factory() as session:
                from libs.common import now_kst
                
                # register_logs에 등록 로그 생성
                insert_log_query = text("""
                    INSERT INTO register_logs (register_user_id, registered_at, created_at, updated_at)
                    VALUES (:register_user_id, :registered_at, :created_at, :updated_at)
                """)
                now = now_kst()
                result = session.execute(
                    insert_log_query,
                    {
                        "register_user_id": member_id,
                        "registered_at": now,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                register_log_id = result.lastrowid
                
                # coupons 테이블 업데이트 (register_id, register_log_id, signature_code)
                update_query = text("""
                    UPDATE coupons
                    SET register_id = :member_id,
                        register_log_id = :register_log_id,
                        signature_code = :signature_code
                    WHERE coupon_id = :coupon_id
                """)
                session.execute(
                    update_query,
                    {
                        "member_id": member_id,
                        "register_log_id": register_log_id,
                        "signature_code": signature_code,
                        "coupon_id": coupon_id,
                    }
                )
                
                session.commit()
        
        return await self._run_in_thread(_register)
    
    async def find_issues_by_user(
        self,
        subject_type: str,
        subject_id: int,
        status: str | None = None,
        title: str | None = None,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[dict], int]:
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
            (이슈 목록, 전체 개수) 튜플
        """
        def _query():
            with self._session_factory() as session:
                offset = (page - 1) * size
                
                # WHERE 조건 구성
                where_conditions = []
                params = {
                    "offset": offset,
                    "size": size,
                }
                
                # 권한 확인 조건
                if subject_type == "member":
                    # 개인사용자: vendor_id가 member_id와 일치하는 경우
                    where_conditions.append("il.vendor_id = :subject_id")
                    params["subject_id"] = subject_id
                elif subject_type == "partner":
                    # 파트너사용자: partner_id가 일치하는 경우
                    where_conditions.append("il.partner_id = :subject_id")
                    params["subject_id"] = subject_id
                else:
                    # 알 수 없는 타입은 빈 결과 반환
                    return ([], 0)
                
                # status 필터
                if status:
                    where_conditions.append("il.status = :status")
                    params["status"] = status
                
                # title 검색 필터 (LIKE 검색)
                if title:
                    where_conditions.append("il.title LIKE :title")
                    params["title"] = f"%{title}%"
                
                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
                
                # 전체 개수 조회
                count_query = text(f"""
                    SELECT COUNT(*)
                    FROM issue_logs il
                    WHERE {where_clause}
                """)
                count_result = session.execute(count_query, params).fetchone()
                total = count_result[0] if count_result else 0
                
                # 이슈 목록 조회
                query = text(f"""
                    SELECT 
                        il.issue_id,
                        il.title,
                        il.product_kind_count,
                        il.status
                    FROM issue_logs il
                    WHERE {where_clause}
                    ORDER BY il.requested_at DESC
                    LIMIT :size OFFSET :offset
                """)
                
                result = session.execute(query, params).fetchall()
                
                # 결과를 딕셔너리 리스트로 변환
                issues = []
                for row in result:
                    issues.append({
                        "issue_id": row[0],
                        "title": row[1],
                        "product_kind_count": row[2],
                        "status": row[3],
                    })
                
                return (issues, total)
        
        return await self._run_in_thread(_query)
    
    async def delete_issues_by_user(
        self,
        issue_ids: list[int],
        subject_type: str,
        subject_id: int,
    ) -> tuple[list[int], list[int]]:
        """
        사용자에게 권한이 부여된 쿠폰 발행기록을 삭제합니다.
        
        Args:
            issue_ids: 삭제할 이슈 ID 목록
            subject_type: 사용자 타입 ("member" 또는 "partner")
            subject_id: 사용자 ID
            
        Returns:
            (유효한 이슈 ID 목록, 유효하지 않은 이슈 ID 목록) 튜플
            
        Raises:
            ValueError: 권한이 없는 이슈가 포함된 경우
        """
        if not issue_ids:
            return ([], [])
        
        def _delete():
            with self._session_factory() as session:
                from libs.common import now_kst
                
                # 이슈 정보 조회 (권한 확인 및 상태 확인용)
                query = text("""
                    SELECT 
                        il.issue_id,
                        il.vendor_id,
                        il.partner_id,
                        il.status
                    FROM issue_logs il
                    WHERE il.issue_id IN :issue_ids
                """)
                
                issues = session.execute(
                    query,
                    {"issue_ids": tuple(issue_ids)}
                ).fetchall()
                
                if not issues:
                    return ([], issue_ids)
                
                # 권한 확인 및 상태별 처리
                valid_issue_ids = []
                invalid_issue_ids = []
                issues_to_delete_completely = []  # 완전 삭제할 이슈
                issues_to_soft_delete_vendor = []  # 벤더측에서만 삭제할 이슈
                issues_to_soft_delete_partner = []  # 파트너측에서만 삭제할 이슈
                issues_to_reject_and_delete = []  # 거절 처리 후 삭제할 이슈
                
                # 승인 이전 상태 목록
                pending_statuses = ["ISSUE_STATUS/PENDING", "ISSUE_STATUS/PAYMENT_READY"]
                # 승인 이후 상태 목록
                approved_statuses = ["ISSUE_STATUS/ISSUED", "ISSUE_STATUS/SHARED", "ISSUE_STATUS/COMPLETED"]
                
                for issue in issues:
                    issue_id, vendor_id, partner_id, status = issue
                    
                    # 권한 확인
                    has_permission = False
                    if subject_type == "member":
                        # 개인사용자: vendor_id가 member_id와 일치하는 경우
                        has_permission = (vendor_id == subject_id)
                    elif subject_type == "partner":
                        # 파트너사용자: partner_id가 일치하는 경우
                        has_permission = (partner_id == subject_id)
                    
                    if not has_permission:
                        invalid_issue_ids.append(issue_id)
                        continue
                    
                    valid_issue_ids.append(issue_id)
                    
                    # 상태와 요청자에 따라 처리 분기
                    if subject_type == "member":
                        # 벤더가 호출한 경우
                        if status in pending_statuses:
                            # 파트너 승인 이전: 파트너와 벤더측 모두에서 삭제 (=DB에서 삭제)
                            issues_to_delete_completely.append(issue_id)
                        elif status in approved_statuses:
                            # 파트너 승인 이후: 벤더측에서만 삭제
                            issues_to_soft_delete_vendor.append(issue_id)
                    elif subject_type == "partner":
                        # 파트너가 호출한 경우
                        if status in pending_statuses:
                            # 승인 이전: 벤더측에서는 거절로 처리되고 파트너측에서만 삭제
                            issues_to_reject_and_delete.append(issue_id)
                        elif status in approved_statuses:
                            # 승인 이후: 파트너측에서만 삭제
                            issues_to_soft_delete_partner.append(issue_id)
                
                now = now_kst()
                
                # 1. 완전 삭제 (벤더요청, 파트너 승인 이전)
                if issues_to_delete_completely:
                    delete_query = text("""
                        DELETE FROM issue_logs
                        WHERE issue_id IN :issue_ids
                    """)
                    session.execute(
                        delete_query,
                        {"issue_ids": tuple(issues_to_delete_completely)}
                    )
                
                # 2. 벤더측에서만 삭제 (벤더요청, 파트너 승인 이후)
                # vendor_deleted_at 필드가 있다고 가정 (없으면 마이그레이션 필요)
                if issues_to_soft_delete_vendor:
                    # 일단 vendor_deleted_at 필드가 있다고 가정하고 구현
                    # 실제로는 마이그레이션이 필요할 수 있음
                    try:
                        update_query = text("""
                            UPDATE issue_logs
                            SET vendor_deleted_at = :deleted_at
                            WHERE issue_id IN :issue_ids
                        """)
                        session.execute(
                            update_query,
                            {
                                "deleted_at": now,
                                "issue_ids": tuple(issues_to_soft_delete_vendor)
                            }
                        )
                    except Exception:
                        # 필드가 없으면 일단 무시 (나중에 마이그레이션 추가 필요)
                        pass
                
                # 3. 파트너측에서만 삭제 (파트너요청, 승인 이후)
                # partner_deleted_at 필드가 있다고 가정 (없으면 마이그레이션 필요)
                if issues_to_soft_delete_partner:
                    try:
                        update_query = text("""
                            UPDATE issue_logs
                            SET partner_deleted_at = :deleted_at
                            WHERE issue_id IN :issue_ids
                        """)
                        session.execute(
                            update_query,
                            {
                                "deleted_at": now,
                                "issue_ids": tuple(issues_to_soft_delete_partner)
                            }
                        )
                    except Exception:
                        # 필드가 없으면 일단 무시 (나중에 마이그레이션 추가 필요)
                        pass
                
                # 4. 거절 처리 후 삭제 (파트너요청, 승인 이전)
                if issues_to_reject_and_delete:
                    # status를 REJECTED로 변경하고 partner_deleted_at 설정
                    try:
                        update_query = text("""
                            UPDATE issue_logs
                            SET status = 'ISSUE_STATUS/REJECTED',
                                partner_deleted_at = :deleted_at,
                                decided_at = :decided_at
                            WHERE issue_id IN :issue_ids
                        """)
                        session.execute(
                            update_query,
                            {
                                "deleted_at": now,
                                "decided_at": now,
                                "issue_ids": tuple(issues_to_reject_and_delete)
                            }
                        )
                    except Exception:
                        # 필드가 없으면 status만 변경
                        update_query = text("""
                            UPDATE issue_logs
                            SET status = 'ISSUE_STATUS/REJECTED',
                                decided_at = :decided_at
                            WHERE issue_id IN :issue_ids
                        """)
                        session.execute(
                            update_query,
                            {
                                "decided_at": now,
                                "issue_ids": tuple(issues_to_reject_and_delete)
                            }
                        )
                
                session.commit()
                return (valid_issue_ids, invalid_issue_ids)
        
        return await self._run_in_thread(_delete)
    
    async def find_partners_by_keyword(
        self,
        keyword: str | None = None,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[dict], int]:
        """
        파트너 상호명을 기반으로 파트너를 검색합니다.
        
        Args:
            keyword: 검색 키워드 (파트너 상호명, 선택)
            page: 페이지 번호 (1부터 시작)
            size: 페이지 크기
            
        Returns:
            (파트너 목록, 전체 개수) 튜플
        """
        def _query():
            with self._session_factory() as session:
                offset = (page - 1) * size
                
                # WHERE 조건 구성
                where_conditions = ["p.contact_account_type = 'PARTNER'"]
                params = {
                    "offset": offset,
                    "size": size,
                }
                
                # keyword 필터 (파트너 상호명 LIKE 검색)
                if keyword:
                    where_conditions.append("pu.partner_name LIKE :keyword")
                    params["keyword"] = f"%{keyword}%"
                
                where_clause = " AND ".join(where_conditions)
                
                # 전체 개수 조회
                count_query = text(f"""
                    SELECT COUNT(DISTINCT pu.partner_id)
                    FROM partner_users pu
                    INNER JOIN phones p ON p.account_id = pu.partner_id
                    WHERE {where_clause}
                """)
                count_result = session.execute(count_query, params).fetchone()
                total = count_result[0] if count_result else 0
                
                # 파트너 목록 조회 (전화번호 포함)
                # GROUP_CONCAT을 사용하여 여러 전화번호를 하나의 문자열로 합침
                query = text(f"""
                    SELECT 
                        pu.partner_id,
                        pu.partner_name,
                        GROUP_CONCAT(p.number ORDER BY p.number SEPARATOR ', ') as numbers
                    FROM partner_users pu
                    INNER JOIN phones p ON p.account_id = pu.partner_id
                    WHERE {where_clause}
                    GROUP BY pu.partner_id, pu.partner_name
                    ORDER BY pu.partner_name ASC
                    LIMIT :size OFFSET :offset
                """)
                
                result = session.execute(query, params).fetchall()
                
                # 결과를 딕셔너리 리스트로 변환
                partners = []
                for row in result:
                    # 전화번호가 여러 개인 경우 첫 번째 것만 사용하거나, 모두 표시
                    # 요구사항에 따르면 "numbers"는 단수형이지만 여러 개일 수 있으므로
                    # 첫 번째 전화번호만 사용하거나, 쉼표로 구분된 문자열 사용
                    phone_numbers = row[2] if row[2] else ""
                    # 첫 번째 전화번호만 사용 (요구사항에 "numbers"가 단수형이므로)
                    first_phone = phone_numbers.split(',')[0].strip() if phone_numbers else ""
                    
                    partners.append({
                        "partner_id": row[0],
                        "partner_name": row[1],
                        "numbers": first_phone,
                    })
                
                return (partners, total)
        
        return await self._run_in_thread(_query)
    
    async def find_products_by_partner_and_keyword(
        self,
        partner_id: int,
        keyword: str,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[dict], int]:
        """
        특정 파트너에게 등록된 제품 목록을 검색합니다.
        
        Args:
            partner_id: 파트너 ID
            keyword: 검색 키워드 (상품명, 필수)
            page: 페이지 번호 (1부터 시작)
            size: 페이지 크기
            
        Returns:
            (상품 목록, 전체 개수) 튜플
        """
        def _query():
            with self._session_factory() as session:
                offset = (page - 1) * size
                
                # WHERE 조건 구성
                where_conditions = ["p.partner_id = :partner_id"]
                params = {
                    "partner_id": partner_id,
                    "offset": offset,
                    "size": size,
                }
                
                # keyword 필터 (상품명 LIKE 검색)
                if keyword:
                    where_conditions.append("p.product_name LIKE :keyword")
                    params["keyword"] = f"%{keyword}%"
                
                where_clause = " AND ".join(where_conditions)
                
                # 전체 개수 조회
                count_query = text(f"""
                    SELECT COUNT(*)
                    FROM products p
                    WHERE {where_clause}
                """)
                count_result = session.execute(count_query, params).fetchone()
                total = count_result[0] if count_result else 0
                
                # 상품 목록 조회
                query = text(f"""
                    SELECT 
                        p.product_id,
                        p.product_name
                    FROM products p
                    WHERE {where_clause}
                    ORDER BY p.product_name ASC
                    LIMIT :size OFFSET :offset
                """)
                
                result = session.execute(query, params).fetchall()
                
                # 결과를 딕셔너리 리스트로 변환
                products = []
                for row in result:
                    products.append({
                        "product_id": row[0],
                        "product_name": row[1],
                    })
                
                return (products, total)
        
        return await self._run_in_thread(_query)

