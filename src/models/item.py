"""统一条目模型 - Item."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class ItemRelated:
    """关联字段 - 替代原有的 related_feature, note_id 等"""
    features: List[str] = field(default_factory=list)
    fixes: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    standards: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, List[str]]:
        """转换为字典，仅包含非空字段"""
        result: Dict[str, List[str]] = {}
        if self.features:
            result["features"] = self.features
        if self.fixes:
            result["fixes"] = self.fixes
        if self.notes:
            result["notes"] = self.notes
        if self.standards:
            result["standards"] = self.standards
        return result

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, List[str]]]) -> Optional["ItemRelated"]:
        """从字典创建（兼容旧数据迁移）"""
        if not data:
            return None
        return cls(
            features=data.get("features", []),
            fixes=data.get("fixes", []),
            notes=data.get("notes", []),
            standards=data.get("standards", [])
        )


@dataclass
class Item:
    """统一条目模型

    存储结构：
    - id, summary, content, tags: 必须字段
    - status: 可选，仅 features/fixes
    - severity: 可选，仅 fixes
    - related: 可选，关联其他条目
    - created_at, updated_at: 自动生成的时间戳

    存储时字段为空则不存储该字段。
    """
    id: str
    summary: str
    content: str = ""
    tags: List[str] = field(default_factory=list)

    # 可选字段
    status: Optional[str] = None
    severity: Optional[str] = None
    related: Optional[ItemRelated] = None

    # 时间戳（自动生成，存储时可选）
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，仅包含非空字段（用于存储）"""
        result: Dict[str, Any] = {
            "id": self.id,
            "summary": self.summary,
        }

        if self.content:
            result["content"] = self.content

        if self.tags:
            result["tags"] = self.tags

        if self.status:
            result["status"] = self.status

        if self.severity:
            result["severity"] = self.severity

        if self.related:
            related_dict = self.related.to_dict()
            if related_dict:
                result["related"] = related_dict

        if self.created_at:
            result["created_at"] = self.created_at

        if self.updated_at:
            result["updated_at"] = self.updated_at

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Item":
        """从字典创建"""
        related_data = data.get("related")
        related = ItemRelated.from_dict(related_data) if related_data else None

        return cls(
            id=data["id"],
            summary=data["summary"],
            content=data.get("content", ""),
            tags=data.get("tags", []),
            status=data.get("status"),
            severity=data.get("severity"),
            related=related,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
