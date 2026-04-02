#!/usr/bin/env python3
import subprocess
import json
import urllib.parse

BASE = "http://localhost:8002"

def curl_post(url, params=None):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    result = subprocess.run(["curl", "-s", "-X", "POST", url], capture_output=True, text=True)
    data = json.loads(result.stdout)
    if isinstance(data, str):
        data = json.loads(data)
    return data

def curl_get(url):
    result = subprocess.run(["curl", "-s", url], capture_output=True, text=True)
    data = json.loads(result.stdout)
    if isinstance(data, str):
        data = json.loads(data)
    return data

def curl_put(url, params=None):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    result = subprocess.run(["curl", "-s", "-X", "PUT", url], capture_output=True, text=True)
    data = json.loads(result.stdout)
    if isinstance(data, str):
        data = json.loads(data)
    return data

def curl_delete(url, params=None):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    result = subprocess.run(["curl", "-s", "-X", "DELETE", url], capture_output=True, text=True)
    data = json.loads(result.stdout)
    if isinstance(data, str):
        data = json.loads(data)
    return data

print("=" * 50)
print("Business API Testing")
print("=" * 50)

# 1. Register project
print("\n1. POST /api/projects")
r = curl_post(f"{BASE}/api/projects", {"name": "py_final", "summary": "PyFinal", "tags": "test,py"})
print("   Success:", r.get("success"), "| PID:", r.get("data", {}).get("project_id", "N/A"))
pid = r["data"]["project_id"]

# 2. Get project
print("\n2. GET /api/projects/{pid}")
r = curl_get(f"{BASE}/api/projects/{pid}")
print("   Success:", r.get("success"))

# 3. Add feature
print("\n3. POST /api/projects/{pid}/items (feature)")
r = curl_post(f"{BASE}/api/projects/{pid}/items", {"group": "features", "summary": "TestF", "content": "Content", "status": "pending", "tags": "t1"})
print("   Success:", r.get("success"), "| IID:", r.get("data", {}).get("item_id", "N/A"))
iid = r["data"]["item_id"]

# 4. List items
print("\n4. GET /api/projects/{pid}/items")
r = curl_get(f"{BASE}/api/projects/{pid}/items?group_name=features")
print("   Success:", r.get("success"), "| Total:", r.get("data", {}).get("total", "N/A"))

# 5. Get single item
print("\n5. GET /api/projects/{pid}/items?item_id={iid}")
r = curl_get(f"{BASE}/api/projects/{pid}/items?group_name=features&item_id={iid}")
print("   Success:", r.get("success"))

# 6. Update item
print("\n6. PUT /api/projects/{pid}/items/{iid}")
r = curl_put(f"{BASE}/api/projects/{pid}/items/{iid}", {"group": "features", "content": "Updated"})
print("   Success:", r.get("success"))

# 7. Manage tags
print("\n7. POST /api/projects/{pid}/items/{iid}/tags")
r = curl_post(f"{BASE}/api/projects/{pid}/items/{iid}/tags", {"group_name": "features", "operation": "add", "tag": "newtag"})
print("   Success:", r.get("success"))

# 8. Register tag
print("\n8. POST /api/tags/register")
r = curl_post(f"{BASE}/api/tags/register", {"project_id": pid, "tag_name": "myTag", "summary": "MyTagSummary"})
print("   Success:", r.get("success"))

# 9. Update tag
print("\n9. PUT /api/tags/update")
r = curl_put(f"{BASE}/api/tags/update", {"project_id": pid, "tag_name": "myTag", "summary": "Updated"})
print("   Success:", r.get("success"))

# 10. Merge tags
print("\n10. POST /api/tags/merge")
r = curl_post(f"{BASE}/api/tags/merge", {"project_id": pid, "old_tag": "t1", "new_tag": "myTag"})
print("   Success:", r.get("success"))

# 11. Get groups
print("\n11. GET /api/projects/{pid}/groups")
r = curl_get(f"{BASE}/api/projects/{pid}/groups")
print("   Success:", r.get("success"))

# 12. Get tags
print("\n12. GET /api/projects/{pid}/tags")
r = curl_get(f"{BASE}/api/projects/{pid}/tags")
print("   Success:", r.get("success"), "| Total:", r.get("data", {}).get("total_tags", "N/A"))

# 13. Delete tag
print("\n13. DELETE /api/tags/delete")
r = curl_delete(f"{BASE}/api/tags/delete", {"project_id": pid, "tag_name": "myTag", "force": "true"})
print("   Success:", r.get("success"))

# 14. Delete item
print("\n14. DELETE /api/projects/{pid}/items/{iid}")
r = curl_delete(f"{BASE}/api/projects/{pid}/items/{iid}", {"group": "features"})
print("   Success:", r.get("success"))

# 15. Archive project
print("\n15. DELETE /api/projects/{pid}")
r = curl_delete(f"{BASE}/api/projects/{pid}", {"mode": "archive"})
print("   Success:", r.get("success"))

# 16. Stats
print("\n16. GET /api/stats")
try:
    r = curl_get(f"{BASE}/api/stats")
    print("   Success:", r.get("success"))
except Exception as e:
    print("   Error:", str(e)[:50])

# 17. Stats summary
print("\n17. GET /api/stats/summary")
r = curl_get(f"{BASE}/api/stats/summary?type=tool")
print("   Success:", r.get("success"), "| Tools:", len(r.get("data", {}).get("tools", [])))

# 18. Stats cleanup
print("\n18. DELETE /api/stats/cleanup")
r = curl_delete(f"{BASE}/api/stats/cleanup", {"retention_days": 30})
print("   Success:", r.get("success"))

# 19. Custom group
print("\n19. POST /api/groups/custom")
r = curl_post(f"{BASE}/api/groups/custom", {"project_id": pid, "group_name": "cust_test"})
print("   Success:", r.get("success"))

print("\n" + "=" * 50)
print("All Business API Tests Complete")
print("=" * 50)