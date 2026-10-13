from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from env_bootstrap import BACKEND_DIR, load_backend_dotenv
import logging
import os
from services.agent_router import router as agent_router
from services.brain_gateway import build_brain_gateway, router as brain_gateway_router
from services.user_router import router as user_router
from services.collab_router import router as collab_router
from services.review_router import router as review_router
from services.lens_router import router as lens_router
from services.hierarchy_router import router as hierarchy_router
from services.membership_router import router as membership_router
from services.memory_router import router as memory_router
from services.requirement_field_router import router as requirement_field_router
from cost.estimate_intake_router import router as estimate_intake_router
from cost.advice_stream_router import router as advice_stream_router
from services.llm_provider import configure_provider_env
from services.embedding_port import configure_embedding_env
from services.session_store import configure_session_env
from services.intent_routing_config import configure_intent_routing_env
from database import init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cloud360.main")

# Load environment variables from backend/.env, never from wherever the process
# happens to have been started. See env_bootstrap for the failure this prevents;
# database.py loads the same file through the same helper, and it runs first
# because main imports it above -- fixing only one of the two changes nothing.
load_backend_dotenv(override=True)

# 準備 OpenRouter 環境（金鑰映射到 ANTHROPIC_AUTH_TOKEN／BASE_URL）；
# 同時讓已退役的 LLM_PROVIDER=cli 在啟動時就記一行 ERROR（RAID R-11）
configure_provider_env()

app = FastAPI(title="Cloud-360 API")

# CORS：前後端分服務時以環境變數注入允許來源（逗號分隔）
# 例：CORS_ORIGINS=https://app.example.com,https://www.example.com
_default_cors = "http://localhost:5173,http://127.0.0.1:5173"
_cors_raw = os.environ.get("CORS_ORIGINS", _default_cors)
CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event to initialize database
@app.on_event("startup")
def on_startup():
    logger.info("後端服務正在啟動...")
    configure_provider_env()
    # U6 embedding-port（D-1／BR1.6）：驗 EMBEDDING_PROVIDER 等四個變數，
    # **失敗即拋**——與上面那行只記日誌刻意不同（ADR-008「不得靜默降級」）。
    # 掛在 startup hook 而非 import 時，是為了讓既有測試（完全不設定 embedding
    # 變數、且以 TestClient(app) 不觸發本 hook）不受影響。
    configure_embedding_env()
    # U10 session-store（BR3.5／NFR8.40）：驗 BRAIN_SESSION_HISTORY_MAX，
    # **失敗即拋**，與上面的 embedding 檢查同形。把缺值讀成「無上限」會讓單一
    # Redis key 無上界成長，而那是無聲的——所以這裡刻意沒有預設值可退。
    # 同樣掛在 startup hook 而非 import 時：既有測試完全不設定本變數，而以
    # TestClient(app) 不觸發本 hook。
    configure_session_env()
    # U11 intent-router（BR3.4／NFR8.60）：驗五個 BRAIN_ROUTER_* 變數。
    # 只有 BRAIN_ROUTER_CONFIDENCE_THRESHOLD **失敗即拋**，其餘四個取預設並
    # 記 WARN／INFO——門檻缺值時反問路徑的判定基準不存在，而那是 FR1.3 這條
    # Must 的觸發條件；其餘四個缺值時系統行為正確，只是沒照設定跑。
    # 同樣掛在 startup hook 而非 import 時：既有測試完全不設定這些變數，
    # 而以 TestClient(app) 不觸發本 hook。
    configure_intent_routing_env()
    # U13 brain-gateway（BR67.11）：在既有設定檢查**之後**、init_db **之前**建立
    # 閘道元件（Redis client、SessionStore、記憶執行器、三個 IntentRouter、
    # WorkOrchestrator、連線登錄），存於 app.state。REDIS_URL／REDIS_USER／
    # REDIS_PASSWORD 缺值或 REDIS_USER=default → **啟動失敗**；Redis 暫時不可達
    # 不阻止啟動（client 延遲連線），在入口頁握手時以 1011 呈現。
    # 同樣掛在 startup hook 而非 import 時：CI 的 import smoke 與 OpenAPI dump
    # 只設 DATABASE_URL／JWT_SECRET，而以 TestClient(app) 不觸發本 hook。
    app.state.brain_gateway = build_brain_gateway(app)
    init_db()


@app.on_event("shutdown")
async def on_shutdown():
    # U13：只關閉本行程閘道自己的記憶執行器與背景 task（帶入項 22）。
    gateway = getattr(app.state, "brain_gateway", None)
    if gateway is not None:
        gateway.shutdown()

app.include_router(agent_router, prefix="/api/architecture")
app.include_router(review_router, prefix="/api/architecture")
app.include_router(lens_router, prefix="/api/architecture")
app.include_router(user_router, prefix="/api/auth")
app.include_router(collab_router, prefix="/api/collab")
app.include_router(estimate_intake_router, prefix="/api/cost/v1")
app.include_router(advice_stream_router, prefix="/api/cost/v1")
# U7 hierarchy-service：專案 → 系統 → 架構圖 階層的讀／建／刪。
# 授權**不掛在 dependency 上**——K2 判定在 HierarchyFacade 內，與四個同進程
# 呼叫端共用同一個落點（契約 K-07 的 sole_entry）。
app.include_router(hierarchy_router, prefix="/api/hierarchy")
# U19 membership-service：per-project 成員與角色、自動改選的橫幅。
# **兩層串聯**（契約 K-16 的 two_layer_rule／BR1.2）：全域功能權限那一層由既有
# require_story_action("K3", ...) 這個 dependency 承載（與 U7 刻意不同，理由見
# services/membership_router.py 的檔頭），per-project 那一層在 MembershipFacade
# 內——同進程呼叫端（U20／U13）走的只有後者，故 facade 自己也驗一次全域層。
app.include_router(membership_router, prefix="/api/membership")
# U8 memory-service：記憶的讀寫、刪除（留稽核）、可見範圍放寬與稽核查詢。
# 授權**不掛在 dependency 上**，且刻意與上面的 U19 不同：K-08 的路由守衛逐字
# 「/memory 走 ProtectedRoute 但**不包** CapabilityRoute……把關的是擁有者欄位
# 而非角色，故不需新 story id」。故這裡只有 get_current_user，沒有
# require_story_action——兩套授權模型（擁有者 ＋ 可見範圍、以及放寬／稽核查詢
# 的角色判定）全在 MemoryFacade 內（契約 K-08 的 sole_entry）。
# 同進程消費端為 U11 intent-router（經 K-10），故 facade 不得拋 HTTPException。
app.include_router(memory_router, prefix="/api/memory")
# U20 requirement-field-service：系統層需求欄位的讀、寫、清空。
# 授權**不掛在 dependency 上**——K4 的全域層與 per-project 層都在
# RequirementFieldFacade 內（契約 K-17 的 sole_entry；BR41.2），因為 U13 是同進程
# 呼叫端、沒有 dependency 鏈。請求本體在授權之後才由 facade 解析，故本 router 的
# 422 一律晚於授權判定（BR46.4）。
app.include_router(requirement_field_router, prefix="/api/requirements")
# U13 brain-gateway：大腦唯一的 WebSocket 端點 /api/brain/ws（BR61.1）。掛在
# /api/ 之下，nginx 的 location /api/ 才會帶 Upgrade 標頭。認證在 handler 內
# （子協定帶 token、accept 前判定 K1），不掛 dependency——WebSocket 端點不走
# HTTPBearer。單一行程假設見 services/brain_gateway.py 檔頭。
app.include_router(brain_gateway_router, prefix="/api/brain")

@app.get("/")
def read_root():
    return {"message": "Cloud-360 Backend is running"}
