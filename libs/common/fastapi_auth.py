"""
FastAPI에서 사용할 수 있는 인증 Dependency 헬퍼
"""
from typing import Annotated, Tuple

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from libs.common.auth import AuthError, verify_access_token_from_env

# Swagger UI에서 Bearer token을 입력할 수 있도록 HTTPBearer 설정
security = HTTPBearer(description="Access Token (Bearer)", auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> Tuple[str, int]:
    """
    FastAPI Dependency로 사용할 수 있는 인증 검증 함수.
    Bearer token에서 사용자 정보를 추출합니다.
    
    Args:
        credentials: HTTPAuthorizationCredentials (Bearer token)
        
    Returns:
        (subject_type, subject_id) 튜플
        
    Raises:
        HTTPException: 인증 실패 시 HTTP 401 반환
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="",
        )
    
    if not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="",
        )
    
    try:
        subject_type, subject_id = verify_access_token_from_env(credentials.credentials)
        return (subject_type, subject_id)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="",
        ) from e
    except Exception as e:
        # 예상치 못한 에러도 401로 처리
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="",
        ) from e


# Type alias for dependency injection
CurrentUser = Annotated[Tuple[str, int], Depends(get_current_user)]

