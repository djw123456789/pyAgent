from typing import Optional
from sqlmodel import SQLModel, Field, Relationship

class Hero(SQLModel, table=True):
    __tablename__ = "heroes"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=50)
    secret_name: str = Field(min_length=3)
    age: Optional[int] = Field(default=None, ge=0, le=999)
    
    # 新增：外键字段，关联到 users.id
    owner_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)

    power: str = Field(default="unknown")

    # 可选：定义关系（方便 ORM 查询，但非必须）
    # owner: Optional["User"] = Relationship(back_populates="heroes")