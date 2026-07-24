---
schema_version: 2
---
# add-health-endpoint

## 狀態
draft

## 類型
新功能

## 為什麼做
Operators need a dependency-free endpoint to determine whether the sample API process is responsive.

## 要改什麼
- Add a `GET /health` response with HTTP 200 and a JSON status value.
- Preserve the existing JSON 404 response for unknown paths.

## 影響範圍
- `app.py`
- `tests/test_app.py`
