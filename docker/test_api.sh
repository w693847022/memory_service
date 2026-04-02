#!/bin/bash

echo "=========================================="
echo "Business API Full Testing (Port 8002)"
echo "=========================================="

# 1. GET /api/projects (list projects)
echo -e "\n--- 1. GET /api/projects ---"
curl -s -X GET http://localhost:8002/api/projects

# 2. POST /api/projects (register project) - store project_id
echo -e "\n--- 2. POST /api/projects ---"
PROJECT_RESP=$(curl -s -X POST "http://localhost:8002/api/projects?name=rest_test_project&summary=REST%20API%E6%B5%8B%E8%AF%95%E9%A1%B9%E7%9B%AE&tags=test,rest")
echo "$PROJECT_RESP"
PROJECT_ID=$(echo "$PROJECT_RESP" | grep -o '"project_id":"[^"]*"' | cut -d'"' -f4)
echo "Created project_id: $PROJECT_ID"

# 3. GET /api/projects/{project_id} using UUID
echo -e "\n--- 3. GET /api/projects/{project_id} (using UUID) ---"
curl -s -X GET "http://localhost:8002/api/projects/$PROJECT_ID"

# 4. GET /api/projects/{project_id}/groups
echo -e "\n--- 4. GET /api/projects/{project_id}/groups ---"
curl -s -X GET "http://localhost:8002/api/projects/$PROJECT_ID/groups"

# 5. GET /api/projects/{project_id}/tags
echo -e "\n--- 5. GET /api/projects/{project_id}/tags ---"
curl -s -X GET "http://localhost:8002/api/projects/$PROJECT_ID/tags"

# 6. POST /api/projects/{project_id}/items (add feature with status)
echo -e "\n--- 6. POST /api/projects/{project_id}/items (add feature with status) ---"
ITEM_RESP=$(curl -s -X POST "http://localhost:8002/api/projects/$PROJECT_ID/items?group=features&summary=REST%20API%E6%B7%BB%E5%8A%A0%E7%9A%84%E5%8A%9F%E8%83%BD&content=%E8%BF%99%E6%98%AF%E5%8A%9F%E8%83%BD%E5%86%85%E5%AE%B9&status=pending&tags=test")
echo "$ITEM_RESP"
ITEM_ID=$(echo "$ITEM_RESP" | grep -o '"item_id":"[^"]*"' | cut -d'"' -f4)
echo "Created item_id: $ITEM_ID"

# 7. GET /api/projects/{project_id}/items (list items)
echo -e "\n--- 7. GET /api/projects/{project_id}/items (list features) ---"
curl -s -X GET "http://localhost:8002/api/projects/$PROJECT_ID/items?group_name=features"

# 8. GET /api/projects/{project_id}/items/{item_id}
echo -e "\n--- 8. GET /api/projects/{project_id}/items/{item_id} ---"
curl -s -X GET "http://localhost:8002/api/projects/$PROJECT_ID/items?group_name=features&item_id=$ITEM_ID"

# 9. PUT /api/projects/{project_id}/items/{item_id} (update item)
echo -e "\n--- 9. PUT /api/projects/{project_id}/items/{item_id} (update) ---"
curl -s -X PUT "http://localhost:8002/api/projects/$PROJECT_ID/items/$ITEM_ID?group=features&content=%E6%9B%B4%E6%96%B0%E5%90%8E%E7%9A%84%E5%86%85%E5%AE%B9"

# 10. POST /api/projects/{project_id}/items/{item_id}/tags (manage tags)
echo -e "\n--- 10. POST /api/projects/{project_id}/items/{item_id}/tags (add tag) ---"
curl -s -X POST "http://localhost:8002/api/projects/$PROJECT_ID/items/$ITEM_ID/tags?group_name=features&operation=add&tag=newtag"

# 11. POST /api/tags/register
echo -e "\n--- 11. POST /api/tags/register ---"
curl -s -X POST "http://localhost:8002/api/tags/register?project_id=$PROJECT_ID&tag_name=apptest&summary=REST%20API%E6%B5%8B%E8%AF%95%E6%A0%87%E7%AD%BE&aliases=test,api"

# 12. PUT /api/tags/update
echo -e "\n--- 12. PUT /api/tags/update ---"
curl -s -X PUT "http://localhost:8002/api/tags/update?project_id=$PROJECT_ID&tag_name=apptest&summary=%E6%9B%B4%E6%96%B0%E7%9A%84%E6%A0%87%E7%AD%BE%E6%91%8A%E8%A6%81"

# 13. POST /api/tags/merge
echo -e "\n--- 13. POST /api/tags/merge ---"
curl -s -X POST "http://localhost:8002/api/tags/merge?project_id=$PROJECT_ID&old_tag=test&new_tag=apptest"

# 14. DELETE /api/projects/{project_id}/items/{item_id}
echo -e "\n--- 14. DELETE /api/projects/{project_id}/items/{item_id} ---"
curl -s -X DELETE "http://localhost:8002/api/projects/$PROJECT_ID/items/$ITEM_ID?group=features"

# 15. DELETE /api/tags/delete
echo -e "\n--- 15. DELETE /api/tags/delete ---"
curl -s -X DELETE "http://localhost:8002/api/tags/delete?project_id=$PROJECT_ID&tag_name=apptest&force=false"

# 16. DELETE /api/projects/{project_id} (archive)
echo -e "\n--- 16. DELETE /api/projects/{project_id} (archive) ---"
curl -s -X DELETE "http://localhost:8002/api/projects/$PROJECT_ID?mode=archive"

# 17. GET /api/stats
echo -e "\n--- 17. GET /api/stats ---"
curl -s -X GET http://localhost:8002/api/stats

# 18. GET /api/stats/summary
echo -e "\n--- 18. GET /api/stats/summary ---"
curl -s -X GET "http://localhost:8002/api/stats/summary?type=full"

# 19. DELETE /api/stats/cleanup
echo -e "\n--- 19. DELETE /api/stats/cleanup ---"
curl -s -X DELETE "http://localhost:8002/api/stats/cleanup?retention_days=30"

# 20. POST /api/groups/custom (create custom group)
echo -e "\n--- 20. POST /api/groups/custom ---"
curl -s -X POST "http://localhost:8002/api/groups/custom?project_id=$PROJECT_ID&group_name=custom_test&summary_max_bytes=100"

echo -e "\n=========================================="
echo "Business API Testing Complete"
echo "=========================================="

echo -e "\n=========================================="
echo "MCP API Testing (tools/list)"
echo "=========================================="

# Get MCP tools list
echo -e "\n--- MCP tools/list ---"
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":100}'

# Test MCP project_stats
echo -e "\n--- MCP project_stats ---"
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"project_stats","arguments":{}},"id":101}'

# Test MCP stats_summary
echo -e "\n--- MCP stats_summary ---"
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"stats_summary","arguments":{"type":"full"}},"id":102}'

echo -e "\n=========================================="
echo "All Testing Complete"
echo "=========================================="