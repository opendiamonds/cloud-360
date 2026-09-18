# CI Pipeline — 釐清問題

> Stage: ci-pipeline（Construction 3.7）· condition: 「Execute when CI pipeline needs creation or significant modification. Skip if CI already exists and is adequate.」
>
> **適用性判定：Execute。** CI **已存在**（四道 job：`repo-contract`／`frontend`／`backend`／`docker-build`），但本 intent 對它做了**實質修改** —— 新增三個步驟，其中兩個是全新的產出物漂移攔截機制。skip 子句的「adequate」對本 intent 不成立：既有四道 job 對「後端改回應形狀而前端型別沒跟上」這條路徑**結構上無感**（`tsc -b` 檢查的是用法對型別檔，不是型別檔對規格檔）。
>
> **本站無新問題**：三個步驟的內容、落點與理由皆已由 application-design 的 C-8／AD-9 定案，並在 U5 的 NFR 文件與 code-summary 中展開。本站只做配置落地與品質閘門的記載。依 `project.md` 的既有 correction（上游已定案的事項不重問），不新增問題。
