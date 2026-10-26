<!-- 本檔為審查全文的留存副本。審查**有效**，收據**缺失**，原因如下。 -->

# 審查 iteration 1（REVIEW_COMPLETED 未能登記）

## 稽核狀態，如實記載

| 事件 | 狀態 |
|---|---|
| `REVIEW_REQUESTED` iteration 1 | **已登記**，requestId `review:13e404d2aca06366dadae48b0909450f` |
| 審查實際執行 | **是**——審查員自行重跑 19／458 測試、三支 validator，並執行七個自己的突變（`MUT-A`–`MUT-G`） |
| 判定 | **NOT-READY**（1 Critical／4 Major／1 Minor） |
| `REVIEW_COMPLETED` | **未能登記** |
| 引擎拒絕訊息（逐字） | `Refusing REVIEW_COMPLETED for "code-generation": workspace source changed after REVIEW_REQUESTED iteration 1. Restore the requested source state and re-dispatch the reviewer.` |

## 為什麼登記不了

這是 `OPEN-6`／`project.md` 已查明並記載的**結構性**缺陷，不是本輪的順序錯誤：
`workspace_requires: true` 的 stage，其 `REVIEW_COMPLETED` 綁定 workspace source
fingerprint，而該 fingerprint **不看 gitignore**，把 `backend/.hypothesis/**` 與各目錄的
`__pycache__/*.pyc` 一起算進去。審查員**必須**跑測試才能獨立查證（那正是我們要求它做的），
而跑測試這個動作本身就會新建／更新 `.hypothesis` 並重新編譯 `.pyc`，於是 fingerprint 必然改變。

**已查證原始碼本身與送審狀態一致**：審查員回報兩個程式檔 md5 相符、其 mutation 暫存副本已刪除，
且 conductor 複驗 `git status` 下三個檔仍為未追蹤新檔、19 tests 當時仍為綠。改變的只有快取。

**刻意不做的事**：不回頭補跑一次 `REVIEW_REQUESTED` 讓收據過關。那會把請求時間記在審查實際
執行之後，等於偽造順序——`project.md` 對這一點已有明文裁決。

## 處置結果（六項全部完成，並以突變複驗）

| ID | 嚴重度 | 處置 | 複驗 |
|---|---|---|---|
| `R-01` | Critical | 新增四個直接呼叫 `configure_embedding_env()` 的測試；更正 `NFR8.2` 的驗證方式註記 | `MUT-G`（掏空成靜默 fulltext no-op）由三個測試攔下，469 tests |
| `R-02` | Major | 以 misbehaving `EmbeddingPort` 子類新增兩個 `_verify_shape` 測試；重述 `OPEN-1` 的嚴重度依據 | `MUT-B`／`MUT-C1` 皆轉紅 |
| `R-03` | Major | 更正 `LOCAL-DEV.md`（4 處＋拆成兩列 troubleshooting）與 `backend/.env.example`（2 處）；實測確認「啟動通過、第一次 embed 失敗」 | 實測：`startup: PASSED` → `embed: ConnectError` |
| `R-04` | Major | 更正 docstring（兩層**串聯**而非各自獨立）與 `BR4.4`／`NFR7.3` 註記；新增 `test_host_and_port_strips_userinfo` | `MUT-F` 轉紅 |
| `R-05` | Major | 檢查由集合成員改為**提供者對應**（`PROVIDER_LEGAL_MODEL_IDS`）；新增兩個測試 | `ollama`＋`stub-v1` 現被拒；`M9` 與新檢查本身皆轉紅 |
| `R-06` | Minor | 新增 `_timeout_from_env()` 五種輸入的行為測試與有限正數斷言；更正 `NFR3.2` 註記與 `M6` 的攔截方式描述 | `MUT-A` 轉紅 |

測試數 19 → **30**；全套 458 → **469**；審查員原本存活的四個突變（`MUT-A`／`B`／`C`／`F`）
與 `MUT-G` 現在**全部轉紅，零存活**。

---

## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-05T05:22:11Z
**Iteration:** 1

### What I re-measured myself (not taken from `code-summary.md`)

| Claim | My measurement | Verdict |
|---|---|---|
| `tests.test_embedding_port` → 19 OK | `Ran 19 tests ... OK` | confirmed |
| full suite → 458 OK | `Ran 458 tests in 30.812s ... OK` | confirmed |
| `validate_env_contract.py` / `validate_repo_contract.py` / `validate_embedding_provider_value.py` pass | all three print their pass lines | confirmed |
| `validate_embedding_provider_value.py` **imports** the allowed set (no second list) | imports `ALLOWED_PROVIDERS`, `MEMORY_RECORD_EMBEDDING_MODELS`, `resolve_provider_selection`; no literal provider list anywhere in the script | confirmed, `H-I3` honoured |
| `backend/requirements.txt` net change zero | `git diff backend/requirements.txt` empty | confirmed |
| no residual localhost instruction for `OLLAMA_BASE_URL` | all three templates now `http://ollama:11434`; no `OLLAMA_BASE_URL=.*localhost` anywhere | confirmed (but see `R-03`) |
| `NFR7.1` supports rejecting IP literals and FQDNs, not just loopback | `security-requirements.md:27` verbatim: "**不得**為 `localhost`、`127.0.0.1`、或任何公開 IP／網域" | confirmed; implementation is a faithful (marginally stricter) reading |
| hypothesis profile cannot affect normal/CI runs | guarded by `os.environ.get("AIDLC_MUTATION_RUN") == "1"` at module level; `grep -rn AIDLC_MUTATION_RUN .github/ deploy/ backend/` outside the test file returns nothing | confirmed |
| no boot path left without `EMBEDDING_PROVIDER` | `deploy/docker-compose.test.yml:102` already has `${EMBEDDING_PROVIDER:-stub}` (unmodified this round); root `docker-compose.yml` has no backend service | confirmed, no uncovered path |
| deviation 1 (new `model_id` startup check) is itself tested | mutating the check to `if False` → **2 failures** | confirmed covered |
| deviation 4 (`M7` fix) is tested | removing `_without_userinfo` from the ctor → **1 failure** | confirmed covered |

I ran seven mutations of my own (`MUT-A`..`MUT-G`), each applied to a backup copy and reverted; `git diff backend/services/embedding_port.py` is empty at the end. **Four of the seven survived**, and three of those four contradict a claim in `code-summary.md` or the dispatch brief.

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | `backend/services/embedding_port.py` > `configure_embedding_env()` (line 701) and `backend/tests/test_embedding_port.py` (whole file) | **The unit's headline behaviour has zero test coverage.** `grep -rn configure_embedding_env backend/tests/` returns **0**. I gutted the function to `selection = ProviderSelection("fulltext", False, None, None)` with the whole logging branch disabled — i.e. a startup hook that validates nothing, never raises, and silently selects `fulltext` — and ran the **full** suite: `Ran 458 tests ... OK` (`MUT-G`). This function is the single enforcement point for ADR-008's "偵測不到時大聲失敗，不得靜默降級為全文檢索", for `BR1.6`, for `NFR8.2` and for `BR7.1`'s startup INFO. The approved design names the missing test verbatim: `nfr-design/security-design.md:47` (`D-1`) says "驗證本身**以直接呼叫該函式的單元測試覆蓋**" — that obligation was not delivered. Worse, `traceability.json` marks `NFR8.2` `OK` citing "458 tests OK 本身就是這個選擇的驗證" — but 458-green is evidence that the hook does not *break* existing tests, not evidence that it *works*; `MUT-G` proves the two are different statements and that the cited evidence survives the function being a no-op. `BR1.6` and `BR7.1` are marked `OK` with no test named for the startup path either. | Add tests that call `configure_embedding_env()` directly: (a) it raises `ValueError` when `EMBEDDING_PROVIDER` is unset / illegal; (b) it raises when `EMBEDDING_PROVIDER=ollama` and `OLLAMA_BASE_URL` is a rejected host; (c) it returns a `port_present=True` selection and emits the `BR7.1` INFO containing provider, model, host:port and timeout for a valid config; (d) the `fulltext` branch emits its "無 Port" INFO. Then correct the `NFR8.2` note so it no longer offers "458 tests OK" as verification of the hook's behaviour. | New |
| R-02 | Major | `backend/services/embedding_port.py` > `EmbeddingPort._verify_shape()` | **The compensating control named for `OPEN-1` is itself unverified.** `OPEN-1` says the untestable thing is "它們實際回傳的向量是否真為 1024 維" and that it "由 `_verify_shape` 在首次真實呼叫時攔下"; the module docstring calls that line "攔它的地方". I replaced **both** of its branches with `if False:` and all 19 tests stayed green (`MUT-C`); removing only the per-vector dimension check also stays green (`MUT-B`). The reason is structural: every dimension assertion in the suite runs against `StubAdapter`, which already produces exactly 1024 dims, so the guard never fires in any test and could be deleted in a future refactor without a single red light. `BR2.1`/`BR2.2` are marked `OK` naming `_verify_shape` as the runtime enforcement, but what the property tests actually verify is `_stub_vector`, not the guard. This is not a re-report of `OPEN-1` — it is the finding that `OPEN-1`'s stated mitigation has no coverage, which means `OPEN-1`'s `named-gap` severity is understated. | Add direct tests for `_verify_shape` using a deliberately misbehaving `EmbeddingPort` subclass (a `_embed_batch` returning 1023 dims, and one returning the wrong number of vectors), asserting `EmbeddingProviderUnavailable` with the dimension/count detail. Then re-state `OPEN-1` to say whether the mitigation is now tested. | New |
| R-03 | Major | `LOCAL-DEV.md:24`, `:85-86`, `:249`, `:485`; `backend/.env.example:122`, `:130` | **The rewritten local-dev guidance states, in five places, something the implementation does not do — and one of them is a diagnostic criterion.** The claims are "本機設不出合法的 `OLLAMA_BASE_URL`" / "**本機不可能設出合法值**" and the troubleshooting row `:485` "設了 `EMBEDDING_PROVIDER=ollama` 後端就**拒絕啟動**，訊息提到主機名必須是 compose 內部服務名". All false for the value the templates now ship. Measured: with `EMBEDDING_PROVIDER=ollama` and the shipped `OLLAMA_BASE_URL=http://ollama:11434`, `resolve_provider_selection` **succeeds** (`startup OK -> ollama bge-m3 http://ollama:11434`), the `OllamaAdapter` is built, and the failure arrives only at the first `embed()` as `EmbeddingProviderUnavailable: ConnectError: nodename nor servname provided`. `_validate_ollama_endpoint` validates hostname *form*, not resolvability, and `BR1.5` forbids a startup probe — so a developer who sets `ollama` and leaves the template value gets a clean boot and a confusing runtime failure, while the troubleshooting table has no row for that symptom and its one `ollama` row sends them looking for a startup error that will never appear. This is the failure shape `project.md` records verbatim ("哪些文件把這個行為當成判斷依據" — a document used as a judgment criterion breaking is worse than a document going stale). | Replace "設不出合法值 / 不可能設出合法值" with what is true: the shipped service-name value *passes* startup validation but is unresolvable outside the compose network, so `ollama` fails at first use, not at boot. Change the `:485` row's symptom from "拒絕啟動" to the two distinct symptoms (boot refused only if you edit the host to `localhost`/an IP/an FQDN; `EmbeddingProviderUnavailable` with a `ConnectError` if you keep the service name), and keep the same remedy (use `fastembed`). | New |
| R-04 | Major | `backend/services/embedding_port.py` > `_without_userinfo()` docstring (lines 127-134), `_host_and_port()`; `code-summary.md §三` closing paragraph; `traceability.json` > `BR4.4`, `NFR7.3` | **The corrected docstring over-corrects, and the brief's claim that "both strippers are now covered by tests" is false in both halves.** (a) *Not covered*: I changed `_host_and_port` to `host = parts.netloc`, i.e. keep the userinfo — all 19 tests stayed green (`MUT-F`). So the stripper that the docstring, `BR4.4` and `NFR7.3` all assign ownership of the `target` field to has **zero** behavioural coverage. (b) *Not independent*: the two are **layered on the same field**, not independent. `EmbeddingProviderUnavailable.__init__` line 172 applies `_without_userinfo(target)` to `target` as well, which is exactly why `MUT-F` stays green — the ctor silently covers for `_host_and_port`. So the live description "`SEC-2` 實際由**兩個各自獨立**的剝除點承載：本函式（負責 `detail`）與 `_host_and_port()`（負責 `target`）" is wrong: `target` passes through *both*, in series. No secret leaks today (the ctor is the backstop), so this is a documentation-and-coverage defect, not a live vulnerability — but it is a security control whose ownership is now mis-recorded for whoever maintains it next, and the only stripper on the `target` path that has a test is the one the docstring says does *not* own `target`. | Correct the docstring, `code-summary.md §三` and the `BR4.4`/`NFR7.3` notes to say that `target` is stripped twice (defence in depth: `_host_and_port` reduces it to host:port, and the ctor's `_without_userinfo` is the backstop) and that `detail` is stripped once. Add a direct test of `_host_and_port` asserting the returned string contains neither the password nor `probe:`, so the outer layer is not the only thing holding `SEC-2` up. | New |
| R-05 | Major | `backend/services/embedding_port.py` > `resolve_provider_selection()` model-id check (deviation 1) | **The new check closes the escape out of the declared set but leaves collision *inside* it open, and that is the exact pollution `BR3.6` names.** Measured, all three accepted: `EMBEDDING_PROVIDER=ollama` + `OLLAMA_EMBED_MODEL=stub-v1` → `model_id = 'stub-v1'`; `ollama` + `OLLAMA_EMBED_MODEL=multilingual-e5-large` → `'multilingual-e5-large'`; `fastembed` + `FASTEMBED_MODEL=stub-v1` → `'stub-v1'`. The first case stamps real ollama vectors with the stub's vector-space identity — and `BR3.6`'s own comment in this file states the consequence verbatim: "CI 短生命週期 stack 每個 PR 寫入的列會與 staging 寫入的列在資料上不可區分". The check verifies *set membership*, not *provider↔model correspondence*, so it cannot see this. The deviation itself is in scope and correct in direction (it is a `BR3.3`/ADR-008 hardening, is grounded in `BR3.5`'s stated rationale, is covered by `test_model_id_must_be_in_the_declared_set`, and `MUT-D` confirms it is load-bearing — 2 failures), and the non-sharing-of-constants reasoning holds (I re-derived it: sharing collapses both sides of `test_model_id_set_matches_the_allowed_value_set_both_ways`, and the `len(declared) == 3` assertion is what actually kills `M9`). The defect is the check's *shape*. | Make the check provider-scoped rather than set-scoped: validate `OLLAMA_EMBED_MODEL` against the ollama-legal identities and `FASTEMBED_MODEL` against the fastembed-legal ones, so `stub-v1` can never be reported by a real provider. A per-provider mapping also removes the need for `PROVIDER_CONTEXT_LIMIT_CHARS` to be keyed on provider while the limit is really a model property (`OPEN-3`). Add the regression case `ollama` + `stub-v1` → rejected. | New |
| R-06 | Minor | `backend/services/embedding_port.py` > `_timeout_from_env()`, `EMBEDDING_TIMEOUT_SEC` (line 246); `code-summary.md §三` row `M6`; `traceability.json` > `NFR3.2` | **`M6` was refuted by a source-text regex, not by behaviour, and `code-summary.md` does not say so.** `test_default_timeout_is_a_named_constant` asserts `DEFAULT_EMBEDDING_TIMEOUT_SEC == 10.0` plus two regexes over the module source. I set the module-level `EMBEDDING_TIMEOUT_SEC = None` — an **infinite** timeout, which is precisely what `M6` claims to have refuted — leaving `DEFAULT_EMBEDDING_TIMEOUT_SEC` and the `httpx.Client(timeout=EMBEDDING_TIMEOUT_SEC)` line untouched: all 19 tests green (`MUT-A`). So the suite protects against someone *writing a literal*, not against the named constant *resolving to infinity*. `_timeout_from_env()` — the only thing that computes it — has zero direct coverage: no test sets `EMBEDDING_TIMEOUT_SEC` at all (`grep` shows only `DEFAULT_EMBEDDING_TIMEOUT_SEC` references). Its deliberate deviation from `BR1.6` (bad value → WARN + default rather than terminate, argued at length in the docstring and in `code-summary.md §四`) therefore rests on no test either. `NFR3.2`'s note calls that test "突變 `M6` 的唯一攔截點", which is accurate and is itself the warning sign. | Narrow the `M6` row and the `NFR3.2` note to "caught by a source-text assertion; the effective timeout value is not behaviourally asserted". Add tests for `_timeout_from_env()` across empty / valid / non-numeric / zero / negative inputs, asserting the returned value and the WARN, and one assertion that the effective `EMBEDDING_TIMEOUT_SEC` is a positive finite float. | New |

### Mutation results I obtained (for comparison with `code-summary.md §三`)

| Mine | What I changed | Suite result | Bears on |
|---|---|---|---|
| `MUT-A` | `EMBEDDING_TIMEOUT_SEC = None` (infinite), constant and `httpx` line untouched | 19 **OK** — survived | `R-06`, `M6` |
| `MUT-B` | per-vector dimension check → `if False` | 19 **OK** — survived | `R-02` |
| `MUT-C` | whole `_verify_shape` (both branches) → `if False` | 19 **OK** — survived | `R-02` |
| `MUT-D` | new `model_id` startup check → `if False` | **FAILED (2)** — killed | deviation 1 is covered |
| `MUT-E` | `_without_userinfo` removed from exception ctor (`M7` re-run) | **FAILED (1)** — killed | deviation 4's fix is real |
| `MUT-F` | `_host_and_port` keeps userinfo (`netloc` instead of `hostname`) | 19 **OK** — survived | `R-04` |
| `MUT-G` | `configure_embedding_env()` gutted to a silent `fulltext` no-op | **458 OK** — survived | `R-01` |

Of the nine mutations in `code-summary.md §三`, I did not find one that "changes the file but not the behaviour" in the `M2` sense — the `M2`/`M7` post-mortems are candid and the behaviour-probe discipline they added is the right fix. The problem is the inverse and the summary does not disclose it: `M6` is killed by a **text** assertion rather than a behavioural one (`R-06`), and the three places where a mutation would have revealed a real gap were simply not in the nine (`configure_embedding_env`, `_verify_shape`, `_host_and_port` — `R-01`, `R-02`, `R-04`). Mutation set selection, not mutation execution, is what failed here: **every one of the three uncovered items is a named mitigation for something else in this unit's risk register**, which is how they escaped a set built around the business rules.

### On the items you said you already know

- `OPEN-1` (ollama/fastembed success paths uncovered) — **mis-severitied downward.** Its text discharges the risk onto `_verify_shape`, and `MUT-C` shows that mitigation is itself deletable with a green suite (`R-02`). Once `R-02` is fixed the stated severity is right; as written it claims protection it does not have.
- `OPEN-2` (`EMBEDDING_TIMEOUT_SEC` at import time) — correctly scoped as `minor`, and deferring the lazy-evaluation change is the right call. But it is *not* the whole timeout story: `R-06` is about the value being behaviourally unasserted regardless of when it resolves, which `OPEN-2` does not cover.
- `OPEN-3` (chars not tokens) — correctly scoped. I would add that the provider-keyed limit and `R-05`'s provider-vs-model confusion are the same underlying modelling error, and one change fixes both.
- `OPEN-4` (no coverage measurement), `OPEN-5` (no automated latency assertion), `OPEN-6` (unrecordable receipt), `OPEN-7` (audit history) — all correctly scoped and honestly written; I have nothing to add. `OPEN-6`'s root cause matches `project.md`'s recorded finding verbatim and the chosen handling (write the review, do not re-fire `REVIEW_REQUESTED`) is the right one.

### On the `Deferred` / `N/A` judgements you asked about

- `US4.1`, `AC4.1.1`-`AC4.1.3`, `BR3.4` marked `Deferred` — **honest, not work-avoidance.** I checked the boundary against approved upstream rather than against the notes: `functional-design/rules.md:441-442` already assigns `BR3.4` to `U5`/`U8` and `BR5.1`'s filtering to `U8`; `functional-spec.md:62` already routes the "vector and `embeddingModel` both NULL" invariant to `U8`; `unit-of-work.md:99-104` defines this unit's delivery as "EmbeddingPort 四實作 ＋ 設定切換 ＋ 偵測不到時大聲失敗" with no retrieval or assembly. `AC4.1.2` in particular ("只包含我依可見範圍有權讀取的部分") is an authorization decision that `SEC-1` *forbids* this unit from making, and that prohibition is machine-enforced. The boundary pre-dates this stage; code-generation did not invent it to shed work.
- `BR5.1` marked `N/A` — **justified, not evasive.** I read the rule: `rules.md:308` onward, its own `violation_behaviour` is verbatim "不適用——本條是**誠實宣告**而非禁令", and the two guarantees it *does* assert are discharged by `BR3.2`/`BR3.5`. `N/A` is the correct label for a rule with no violation condition. One caveat worth a line somewhere: `R-05` shows the "`model_id()` 隨向量空間改變而改變" half of that honest declaration is currently defeatable by configuration, so `BR5.1`'s premise is slightly weaker than it reads until `R-05` is fixed.

### Coverage of this review — where I was shallow

Depth was uneven and I would rather say where than imply uniformity. **Deep**: `embedding_port.py` read end to end; the full test file; seven mutations executed and reverted; all three validators and both test invocations re-run; `NFR7.1`'s verbatim text; `BR3.4`/`BR5.1`'s verbatim upstream; every `EMBEDDING_PROVIDER` consumer across compose files, `render-env.sh` and the three templates; `main.py` and `ci.yml` diffs read in full; `traceability.json` parsed mechanically (44 upstream ids, 44 coverage rows, zero on either side missing — that symmetry I verified by set difference, not by eye). **Shallow**: I did not read `code-generation-plan.md` or `unit-test-instructions.md` in full, so I cannot say whether the ten deliverables as planned match what landed beyond what `source-manifest.json` lists; I did not audit `deploy/render-env.sh` or `docker-compose.deploy.yml` line by line beyond the embedding variables; I did not review `DEPLOY.md`'s diff at all (it is modified in the worktree but not in this unit's manifest); and I took the `P1`-`P6` property definitions from `functional-spec.md §五` as given rather than re-deriving whether six properties are the right six.

### Summary

The implementation is genuinely good — the layering, the deliberate non-sharing of constants, the lazy `httpx` import that lets `repo-contract` import the module, the `H-I3` single-source validator, and the candour of the `M2`/`M7` post-mortems are all above the bar. The defect is concentrated in one place and it is structural rather than careless: **the three pieces of code that this unit's own risk register nominates as mitigations — `configure_embedding_env` (ADR-008's loud failure), `_verify_shape` (`OPEN-1`'s backstop), `_host_and_port` (`SEC-2`'s `target` stripper) — are the three pieces with no behavioural coverage**, and each is marked `OK` in `traceability.json` on evidence that survives the code being neutered. `R-01` is Critical because gutting the startup hook leaves all 458 tests green while turning "偵測不到時大聲失敗" into exactly the silent downgrade to full-text that ADR-008 forbids, and because the approved design (`D-1`) named the missing test explicitly. Verdict is NOT-READY on `R-01` alone; `R-02`-`R-05` are four Majors on top of it.

Finding classification: **newly-introduced 3** (`R-01`, `R-03`, `R-04`), **pre-existing-unaudited 0**, **new-design-problem 3** (`R-02`, `R-05`, `R-06`). Nothing here is a pre-existing defect inherited from another unit; every finding is in code or documents this unit wrote this round, which means another round has clearly positive expected value — all six have mechanical, bounded fixes (five new tests and four documentation corrections) and none requires an upstream design change.

**NOT-READY**
