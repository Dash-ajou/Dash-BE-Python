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

