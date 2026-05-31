from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from backend.api.deps import get_db
from backend.core.dependencies import get_current_user, get_current_admin
from backend.models.user import User
from backend.models.department import Department
from backend.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse

router = APIRouter()


@router.get("/", response_model=List[DepartmentResponse])
def list_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """获取部门列表"""
    departments = db.query(Department).offset(skip).limit(limit).all()
    return departments


@router.get("/{department_id}", response_model=DepartmentResponse)
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个部门"""
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")
    return department


@router.post("/", response_model=DepartmentResponse)
def create_department(
    department_in: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """创建部门（仅管理员）"""
    # 检查部门名称是否已存在
    existing = db.query(Department).filter(Department.name == department_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="部门名称已存在")

    department = Department(**department_in.model_dump())
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


@router.put("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    department_in: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """更新部门（仅管理员）"""
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")

    # 如果更新名称，检查是否与其他部门重复
    if department_in.name and department_in.name != department.name:
        existing = db.query(Department).filter(Department.name == department_in.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="部门名称已存在")

    update_data = department_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(department, field, value)

    db.commit()
    db.refresh(department)
    return department


@router.delete("/{department_id}")
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """删除部门（仅管理员）"""
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")

    db.delete(department)
    db.commit()
    return {"message": "部门已删除"}
