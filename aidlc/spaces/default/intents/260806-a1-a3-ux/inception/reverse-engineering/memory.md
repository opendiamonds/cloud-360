# Reverse Engineering — memory

## Interpretations
- 2026-08-06T01:50:00Z — User intent = A1/A3 UX bugfix on Workspace (draw.io collab, chat, sidebar IA) + prompt-injection guard for Design Agent; not a greenfield rebuild.
- 2026-08-06T01:50:00Z — 「金耀」視為「金鑰」typo（credentials / API keys）。
- 2026-08-06T01:50:00Z — Sidebar IA：依 user story 大類（A、J…）；A1／A3 為大類 A 下第二層；既有 A、J 先改，未來功能比照。

## Deviations
- （none yet）

## Tradeoffs
- 2026-08-06T01:50:00Z — Full-repo RE vs A1-focused scan: still produce all 9 codekb artifacts (stage contract) but weight scanning toward `frontend/` Workspace/Sidebar/draw.io and `backend` agent prompt path.

## Open questions
- 2026-08-06T01:50:00Z — Draw.io「退出」預期行為：離開全螢幕／卸下載體／navigate away？待 requirements 澄清。
- 2026-08-06T01:50:00Z — 線不重疊 icon：用 draw.io 層級／waypoint／edgeStyle，或自訂 router？

## Interpretations
- 2026-08-06T02:00:00Z — Draw.io「退出」= 未儲存確認後離開編輯／返回瀏覽。
- 2026-08-06T02:00:00Z — 線不蓋 icon：以 `diagram_builder` 加 exit/entry／waypoint 為主。
- 2026-08-06T02:00:00Z — Prompt guard：進 agent 前預檢＋system prompt；固定拒答文案。

## Open questions
- 2026-08-06T02:00:00Z — 「返回瀏覽」具體 UI：僅還原 fullscreen／留在 Workspace？Requirements 再收斂。
