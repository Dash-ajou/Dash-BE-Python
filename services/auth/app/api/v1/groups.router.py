from fastapi import APIRouter, Depends, HTTPException, Response, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_pagination import Page

from services.auth.app.core.LoginService import LoginError, LoginService
from services.auth.app.dependencies import get_login_service, get_group_repository
from services.auth.app.db.repositories.groups import SQLAlchemyGroupRepository
from services.auth.app.schemas.request import GroupCreateSchema
from services.auth.app.schemas.response import GroupItem

router = APIRouter(prefix="/groups", tags=["Groups"])

# Swagger UI에서 Bearer token을 입력할 수 있도록 HTTPBearer 설정
security = HTTPBearer(description="Access Token (Bearer)", auto_error=False)


@router.get("", response_model=Page[GroupItem])
async def get_groups(
    page: int = 1,
    size: int = 10,
    keyword: str | None = None,
    credentials: HTTPAuthorizationCredentials | None = Security(security),
    login_service: LoginService = Depends(get_login_service),
    group_repository: SQLAlchemyGroupRepository = Depends(get_group_repository),
):
    """
    소속목록을 검색합니다.
    
    **Query Parameters:**
    - `page`: 페이지 번호 (기본값: 1)
    - `size`: 페이지 크기 (기본값: 10)
    - `keyword`: 검색 키워드 (그룹명 검색, 선택)
    
    **응답 형식:**
    - `items`: 그룹 목록
    - `total`: 전체 개수
    - `page`: 현재 페이지
    - `size`: 페이지 크기
    - `pages`: 전체 페이지 수
    """
    # Bearer token 검증
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="",
        )
    
    try:
        # Access token 검증 (로그인 상태 확인)
        await login_service.verify_access_token(credentials.credentials)
    except LoginError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="",
        )
    
    # 그룹 목록 조회
    groups, total = await group_repository.search_groups(
        keyword=keyword,
        limit=size,
        offset=(page - 1) * size,
    )
    
    # GroupItem으로 변환 (departCount 제외)
    items = [
        GroupItem(
            groupId=group.groupId,
            groupName=group.groupName,
        )
        for group in groups
    ]
    
    # fastapi-pagination의 Page 형식으로 반환
    return Page(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size if size > 0 else 0,
    )


@router.post("", status_code=status.HTTP_200_OK)
async def create_group(
    payload: GroupCreateSchema,
    credentials: HTTPAuthorizationCredentials | None = Security(security),
    login_service: LoginService = Depends(get_login_service),
    group_repository: SQLAlchemyGroupRepository = Depends(get_group_repository),
):
    """
    새로운 소속을 생성합니다.
    
    **주의사항:**
    - 동일한 이름의 그룹이 이미 존재하면 400 Bad Request를 반환합니다.
    """
    # Bearer token 검증
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="",
        )
    
    try:
        # Access token 검증 (로그인 상태 확인)
        await login_service.verify_access_token(credentials.credentials)
    except LoginError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="",
        )
    
    try:
        # 그룹 생성
        await group_repository.create_group(payload.groupName)
    except ValueError as exc:
        # 동일한 이름의 그룹이 존재하는 경우
        if "동일한 이름" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ERR-DUP-VAULE"},
            ) from exc
        raise
    
    # 성공 시 빈 응답 반환 (HTTP 200 OK)
    return Response(status_code=status.HTTP_200_OK)

