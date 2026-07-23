# add-health-endpoint 任務

- [ ] Implement the `/health` response without external dependencies
- [ ] Add regression tests for `/health` and unknown paths
- [ ] Document the final health response contract

## 驗收條件
- 情境：`/health` returns HTTP 200 and `{"status": "ok"}`
- 情境：an unknown path still returns the JSON 404 response
