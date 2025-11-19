from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Optional

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["Authentication"])
users_router = APIRouter(tags=["Users"])
groups_router = APIRouter(tags=["Groups"])


def _load_module(module_path: Path) -> Optional[ModuleType]:
    spec = spec_from_file_location(module_path.stem.replace(".", "_"), module_path)
    if spec is None or spec.loader is None:
        return None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v1_dir = Path(__file__).resolve().parent

for router_file in v1_dir.glob("*.router.py"):
    if router_file.name == Path(__file__).name:
        continue

    module = _load_module(router_file)
    if module is None:
        continue

    sub_router = getattr(module, "router", None)
    if isinstance(sub_router, APIRouter):
        # users.router.py와 groups.router.py는 별도로 처리
        if router_file.name == "users.router.py":
            users_router.include_router(sub_router)
        elif router_file.name == "groups.router.py":
            # groups.router.py는 별도 router에 포함
            groups_router.include_router(sub_router)
        else:
            router.include_router(sub_router)
