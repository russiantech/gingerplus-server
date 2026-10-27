import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select

from app.api.deps import DB, CurrentUser, require_permissions
from app.core.exceptions import Conflict, Forbidden, NotFound
from app.core.permissions import DEFAULT_ROLES
from app.core.security import hash_password
from app.enums import Permission as P, UserType
from app.models import Role, User
from app.schemas.auth import RoleOut, UserOut
from app.schemas.common import Message, Page
from app.schemas.user import AdminUserCreate, AdminUserUpdate, RoleCreate, RoleUpdate
from app.utils.pagination import PageParams, page_of, paginate
from app.utils.text import normalize_email, normalize_phone
from datetime import datetime, timezone

router = APIRouter(prefix="/admin", tags=["admin:users"])
users_perm = Depends(require_permissions(P.USERS_MANAGE))
roles_perm = Depends(require_permissions(P.ROLES_MANAGE))


@router.get("/permissions", dependencies=[users_perm])
async def permissions():
    return [{"key": p.value, "group": p.value.split(":")[0]} for p in P]


@router.get("/roles", response_model=list[RoleOut], dependencies=[users_perm])
async def list_roles(db: DB):
    return (await db.execute(select(Role).order_by(Role.name))).scalars().all()


@router.post("/roles", response_model=RoleOut, status_code=201, dependencies=[roles_perm])
async def create_role(data: RoleCreate, db: DB):
    if (await db.execute(select(Role.id).where(Role.key == data.key))).first():
        raise Conflict("Role key already exists.")
    valid = {p.value for p in P}
    role = Role(**{**data.model_dump(), "permissions": [p for p in data.permissions if p in valid]})
    db.add(role)
    await db.flush()
    return role


@router.patch("/roles/{role_id}", response_model=RoleOut, dependencies=[roles_perm])
async def update_role(role_id: uuid.UUID, data: RoleUpdate, db: DB):
    role = await db.get(Role, role_id)
    if not role:
        raise NotFound("Role not found.")
    if role.key == "super_admin":
        raise Forbidden("The Super Admin role cannot be modified.")
    valid = {p.value for p in P}
    patch = data.model_dump(exclude_unset=True)
    if "permissions" in patch:
        patch["permissions"] = [p for p in patch["permissions"] if p in valid]
    for k, v in patch.items():
        setattr(role, k, v)
    return role


@router.delete("/roles/{role_id}", response_model=Message, dependencies=[roles_perm])
async def delete_role(role_id: uuid.UUID, db: DB):
    role = await db.get(Role, role_id)
    if not role:
        raise NotFound("Role not found.")
    if role.is_system:
        raise Forbidden("System roles cannot be deleted.")
    if (await db.execute(select(User.id).where(User.role_id == role.id).limit(1))).first():
        raise Conflict("Reassign users with this role first.")
    await db.delete(role)
    return Message(detail="Role deleted")


@router.get("/users", response_model=Page[UserOut], dependencies=[users_perm])
async def list_users(db: DB, params: PageParams = Depends(), q: str | None = None, user_type: UserType | None = None):
    stmt = select(User).where(User.user_type != UserType.CUSTOMER)
    if user_type:
        stmt = stmt.where(User.user_type == user_type)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(User.email.ilike(like), User.first_name.ilike(like), User.last_name.ilike(like)))
    rows, total, pages = await paginate(db, stmt.order_by(User.created_at.desc()), params, unique=True)
    return page_of(rows, total, pages, params)


async def _role(db, key: str) -> Role:
    r = (await db.execute(select(Role).where(Role.key == key))).scalar_one_or_none()
    if not r:
        raise NotFound(f"Role '{key}' not found.")
    return r


@router.post("/users", response_model=UserOut, status_code=201, dependencies=[users_perm])
async def create_user(data: AdminUserCreate, db: DB, actor: CurrentUser):
    email = normalize_email(data.email)
    if (await db.execute(select(User.id).where(User.email == email))).first():
        raise Conflict("Email already registered.", code="email_taken")
    role = await _role(db, data.role_key)
    if role.key == "super_admin" and actor.role_key != "super_admin":
        raise Forbidden("Only a Super Admin can create another Super Admin.")
    user = User(email=email, password_hash=hash_password(data.password), first_name=data.first_name, last_name=data.last_name,
                phone=normalize_phone(data.phone), user_type=data.user_type, role_id=role.id, email_verified_at=datetime.now(timezone.utc))
    db.add(user)
    await db.flush()
    await db.refresh(user, ["role"])
    return user


@router.patch("/users/{user_id}", response_model=UserOut, dependencies=[users_perm])
async def update_user(user_id: uuid.UUID, data: AdminUserUpdate, db: DB, actor: CurrentUser):
    user = await db.get(User, user_id)
    if not user:
        raise NotFound("User not found.")
    if user.id == actor.id and data.is_active is False:
        raise Forbidden("You cannot deactivate your own account.")
    if user.role_key == "super_admin" and actor.role_key != "super_admin":
        raise Forbidden("Only a Super Admin can modify a Super Admin.")
    for k in ("first_name", "last_name", "phone", "is_active", "user_type", "notes", "linked_store_id"):
        if k in data.model_fields_set:
            setattr(user, k, getattr(data, k))
    if data.role_key:
        role = await _role(db, data.role_key)
        if role.key == "super_admin" and actor.role_key != "super_admin":
            raise Forbidden("Only a Super Admin can grant Super Admin.")
        user.role_id = role.id
    if data.password:
        user.password_hash = hash_password(data.password)
    await db.flush()
    await db.refresh(user, ["role"])
    return user
