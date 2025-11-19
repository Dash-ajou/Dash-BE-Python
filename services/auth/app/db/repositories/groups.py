import asyncio
import uuid
from typing import Callable

from sqlalchemy import text

from libs.schemas.group import Group
from services.auth.app.db.session import SessionLocal


class _SQLRepositoryBase:
    def __init__(self, session_factory: Callable[[], SessionLocal] = SessionLocal):
        self._session_factory = session_factory

    async def _run_in_thread(self, func):
        return await asyncio.to_thread(func)


class SQLAlchemyGroupRepository(_SQLRepositoryBase):
    async def search_groups(
        self,
        keyword: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[Group], int]:
        """
        그룹 목록을 검색합니다.
        
        Args:
            keyword: 검색 키워드 (group_name에 대해 LIKE 검색)
            limit: 페이지 크기
            offset: 오프셋
            
        Returns:
            (그룹 목록, 전체 개수) 튜플
        """
        def _search():
            with self._session_factory() as session:
                # WHERE 조건 구성
                where_clause = ""
                params = {}
                
                if keyword:
                    where_clause = "WHERE group_name LIKE :keyword"
                    params["keyword"] = f"%{keyword}%"
                
                # 전체 개수 조회
                count_query = text(f"SELECT COUNT(*) as count FROM `groups` {where_clause}")
                count_result = session.execute(count_query, params).mappings().first()
                total = count_result["count"] if count_result else 0
                
                # 데이터 조회
                data_query = text(
                    f"""
                    SELECT 
                        group_id,
                        group_name,
                        depart_count
                    FROM `groups`
                    {where_clause}
                    ORDER BY group_id
                    LIMIT :limit OFFSET :offset
                    """
                )
                params.update({"limit": limit, "offset": offset})
                rows = session.execute(data_query, params).mappings().all()
                
                groups = [
                    Group(
                        groupId=str(row["group_id"]),
                        groupName=row["group_name"],
                        departCount=row["depart_count"],
                    )
                    for row in rows
                ]
                
                return (groups, total)
        
        return await self._run_in_thread(_search)

    async def group_name_exists(self, group_name: str) -> bool:
        """그룹 이름이 이미 존재하는지 확인합니다."""
        def _check():
            with self._session_factory() as session:
                row = (
                    session.execute(
                        text(
                            """
                            SELECT COUNT(*) as count
                            FROM `groups`
                            WHERE group_name = :group_name
                            LIMIT 1
                            """
                        ),
                        {"group_name": group_name},
                    )
                    .mappings()
                    .first()
                )
                return row["count"] > 0 if row else False

        return await self._run_in_thread(_check)

    async def create_group(self, group_name: str) -> str:
        """
        새로운 그룹을 생성합니다.
        
        Args:
            group_name: 그룹 명칭
            
        Returns:
            생성된 그룹 ID
            
        Raises:
            ValueError: 동일한 이름의 그룹이 이미 존재하는 경우
        """
        def _create():
            with self._session_factory() as session:
                # 중복 체크
                existing = (
                    session.execute(
                        text(
                            """
                            SELECT COUNT(*) as count
                            FROM `groups`
                            WHERE group_name = :group_name
                            LIMIT 1
                            """
                        ),
                        {"group_name": group_name},
                    )
                    .mappings()
                    .first()
                )
                if existing and existing["count"] > 0:
                    raise ValueError("동일한 이름의 그룹이 이미 존재합니다.")

                # group_id 생성 (UUID 사용)
                group_id = str(uuid.uuid4())

                # 그룹 생성
                session.execute(
                    text(
                        """
                        INSERT INTO `groups` (group_id, group_name, depart_count)
                        VALUES (:group_id, :group_name, :depart_count)
                        """
                    ),
                    {
                        "group_id": group_id,
                        "group_name": group_name,
                        "depart_count": 0,  # 초기값은 0
                    },
                )
                session.commit()
                return group_id

        return await self._run_in_thread(_create)

