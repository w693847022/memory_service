"""使用指南构建模块."""

from .guidelines_data import TRANSLATIONS


def _build_guidelines(lang: str) -> dict:
    """根据语言构建指南.

    Args:
        lang: 语言代码 (zh/en)

    Returns:
        指南字典
    """
    t = TRANSLATIONS[lang]
    return {
        "version": "1.1",
        "last_updated": "2026-03-22",
        "language": lang,
        "guidelines": {
            "project_naming": {
                "title": t["project_naming_title"],
                "priority": "highest",
                "workflow": t["project_naming_workflow"],
                "examples": t["project_naming_examples"],
            },
            "groups": {
                "title": t["groups_title"],
                "description": t["groups_description"],
                "groups_list": t["groups_list"],
            },
            "tag_standards": {
                "title": t["tag_standards_title"],
                "standard_tags": t["standard_tags"],
                "tag_limits": {
                    "max_per_item": 5,
                    "recommendation": t["tag_limits_recommendation"],
                },
            },
            "memory_workflow": {
                "title": t["workflow_title"],
                "description": t["workflow_description"],
                "query_flow": t["query_flow"],
                "query_tips": t["query_tips"],
                "recording_guide": {
                    "when": t["recording_guide_when"],
                    "tag_registration": t["recording_guide_tag_registration"],
                    "content": t["recording_guide_content"],
                    "tags": t["recording_guide_tags"],
                },
                "cleanup": t["cleanup"],
            },
            "best_practices": t["best_practices"],
        },
    }


def _build_chinese_guidelines() -> dict:
    """构建中文使用指南."""
    return _build_guidelines("zh")


def _build_english_guidelines() -> dict:
    """Build English usage guidelines."""
    return _build_guidelines("en")


def _build_guidelines_content(lang: str) -> dict:
    """根据语言构建指南内容.

    Args:
        lang: 语言选择 (zh/en)

    Returns:
        指南内容字典
    """
    return _build_guidelines("en" if lang.lower() == "en" else "zh")
