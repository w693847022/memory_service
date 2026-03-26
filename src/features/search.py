"""搜索功能模块."""

from typing import Optional

import requests


def search_github(query: str, language: Optional[str] = None, max_results: int = 5):
    """搜索 GitHub 仓库."""
    try:
        search_query = query
        if language:
            search_query += f" language:{language}"

        url = "https://api.github.com/search/repositories"
        params = {
            "q": search_query,
            "sort": "stars",
            "order": "desc",
            "per_page": max_results
        }
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Project-Memory-Server/1.0.0"
        }

        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("items", []):
            results.append({
                "name": item.get("name", ""),
                "full_name": item.get("full_name", ""),
                "description": item.get("description", "No description"),
                "url": item.get("html_url", ""),
                "stars": item.get("stargazers_count", 0),
                "language": item.get("language", "Unknown"),
                "topics": item.get("topics", [])
            })

        return {"success": True, "results": results}

    except requests.exceptions.Timeout:
        return {"success": False, "error": "GitHub API timeout"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"GitHub API error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


def search_stackoverflow(query: str, language: Optional[str] = None, max_results: int = 5):
    """搜索 Stack Overflow 问答."""
    try:
        url = "https://api.stackexchange.com/2.3/search/advanced"
        params = {
            "order": "desc",
            "sort": "relevance",
            "q": query,
            "pagesize": max_results,
            "site": "stackoverflow",
            "filter": "withbody"
        }

        if language:
            tag = language.lower().replace(" ", "-")
            params["tagged"] = tag

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("items", []):
            body = item.get("body_markdown", "")
            preview = body[:200] + "..." if len(body) > 200 else body

            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "score": item.get("score", 0),
                "answers": item.get("answer_count", 0),
                "is_answered": item.get("is_answered", False),
                "tags": item.get("tags", []),
                "preview": preview
            })

        return {"success": True, "results": results}

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Stack Overflow API timeout"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Stack Overflow API error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}
