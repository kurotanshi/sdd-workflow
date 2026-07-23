# abandon-snapshot

## 狀態
approved

## 類型
新功能

## 為什麼做
Malformed tasks must not lock abandonment reads.

## 要改什麼
- Preserve best-effort progress with unreliable counts.

## 影響範圍
- Abandonment preflight consumers.
