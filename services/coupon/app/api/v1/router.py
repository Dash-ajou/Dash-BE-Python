from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Optional

from fastapi import APIRouter

# 메인 라우터 생성 (prefix 없음)
router = APIRouter(tags=["Coupon"])


def _load_module(module_path: Path) -> Optional[ModuleType]:
    """모듈 파일을 동적으로 로드합니다."""
    spec = spec_from_file_location(module_path.stem.replace(".", "_"), module_path)
    if spec is None or spec.loader is None:
        return None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# v1 디렉토리에서 모든 *.router.py 파일을 자동으로 로드하여 포함
v1_dir = Path(__file__).resolve().parent

for router_file in v1_dir.glob("*.router.py"):
    # 현재 파일은 제외
    if router_file.name == Path(__file__).name:
        continue

    module = _load_module(router_file)
    if module is None:
        continue

    # 모듈에서 router 객체를 가져와서 포함
    sub_router = getattr(module, "router", None)
    if isinstance(sub_router, APIRouter):
        router.include_router(sub_router)

