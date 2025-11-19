"""
공통 인증 모듈
모든 MSA에서 사용할 수 있는 JWT 토큰 검증 로직을 제공합니다.
"""
import os
from typing import Tuple

import jwt


class AuthError(Exception):
    """인증 관련 에러"""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
        print(f"AuthError: {code} {message}")


def get_jwt_config() -> Tuple[str, str]:
    """
    환경 변수에서 JWT 설정을 읽어옵니다.
    
    Returns:
        (secret_key, algorithm) 튜플
        
    Raises:
        AuthError: JWT 설정이 없는 경우
    """
    secret_key = os.getenv("JWT_SECRET_KEY")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    
    if not secret_key:
        # 개발 환경에서는 기본값 사용 (프로덕션에서는 반드시 설정 필요)
        secret_key = os.getenv("AUTH_JWT_SECRET_KEY") or os.getenv("COUPON_JWT_SECRET_KEY")
        if not secret_key:
            # 최후의 수단: 개발용 기본값 (프로덕션에서는 절대 사용하지 말 것)
            secret_key = "change-me-in-production"
    
    return (secret_key, algorithm)


def verify_access_token(access_token: str, secret_key: str | None = None, algorithm: str | None = None) -> Tuple[str, int]:
    """
    Access token을 JWT 방식으로 검증하고 subject_type과 subject_id를 반환합니다.
    DB 조회 없이 토큰 자체에서 정보를 추출합니다.
    
    Args:
        access_token: 검증할 access token (JWT)
        secret_key: JWT 서명에 사용할 시크릿 키 (None이면 환경 변수에서 읽음)
        algorithm: JWT 알고리즘 (None이면 환경 변수에서 읽거나 기본값 HS256 사용)
        
    Returns:
        (subject_type, subject_id) 튜플
        
    Raises:
        AuthError: 토큰이 유효하지 않은 경우
    """
    if not secret_key or not algorithm:
        secret_key, algorithm = get_jwt_config()
    
    try:
        # JWT 디코딩 및 검증
        payload = jwt.decode(
            access_token,
            secret_key,
            algorithms=[algorithm]
        )
        
        # 토큰에서 사용자 정보 추출
        subject_type = payload.get("sub_type")
        subject_id = payload.get("sub_id")
        
        if not subject_type or not subject_id:
            raise AuthError("ERR-IVD-PARAM", "access token에 필수 정보가 없습니다.")
        
        return (subject_type, int(subject_id))
    except jwt.ExpiredSignatureError:
        raise AuthError("ERR-IVD-PARAM", "access token이 만료되었습니다.")
    except jwt.InvalidTokenError as e:
        raise AuthError("ERR-IVD-PARAM", "access token이 유효하지 않습니다.") from e


def verify_access_token_from_env(access_token: str) -> Tuple[str, int]:
    """
    환경 변수에서 JWT 설정을 읽어서 Access token을 검증합니다.
    
    Args:
        access_token: 검증할 access token (JWT)
        
    Returns:
        (subject_type, subject_id) 튜플
        
    Raises:
        AuthError: 토큰이 유효하지 않은 경우
    """
    secret_key, algorithm = get_jwt_config()
    return verify_access_token(access_token, secret_key, algorithm)

