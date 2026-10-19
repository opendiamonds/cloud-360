import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

// ADR-0019 §5 — subprotocol 的消費端強制（三條選擇器）。抽成檔內常數，app 區塊與 tests 區塊
// 都展開它：flat config 對同一條規則以後者取代前者，tests 區塊若只列新選擇器，tests 目錄會失去
// 這三條（U14 security-design §六之六）。規則只有一份。
const WS_SUBPROTOCOL_RESTRICTIONS = [
  {
    // 陣列形式：`new WebSocket(url, [...])`。用**後代**而非直接子選擇器，
    // 這樣 `['bearer' + '.' + token]` 也會被抓到，而不只是最表面的
    // `` [`bearer.${token}`] ``。由常數相加組出的字串沒有任何字面量節點，
    // 所以正確寫法通得過。
    selector:
      "NewExpression[callee.name='WebSocket'] > ArrayExpression :matches(Literal, TemplateLiteral)",
    message:
      'subprotocol 必須由 ws-contract.d.ts 的 WsSubprotocol 取值，不得寫死字串（ADR-0019 §5／NFR5.4）。',
  },
  {
    // 單一字串形式：`new WebSocket(url, 'bearer.x')`。WebSocket 的第二引數
    // 可以是字串或字串陣列，只擋陣列會留下一條等價的繞道。
    selector: "NewExpression[callee.name='WebSocket'][arguments.1.type='Literal']",
    message:
      'subprotocol 必須由 ws-contract.d.ts 的 WsSubprotocol 取值，不得寫死字串（ADR-0019 §5／NFR5.4）。',
  },
  {
    selector: "NewExpression[callee.name='WebSocket'][arguments.1.type='TemplateLiteral']",
    message:
      'subprotocol 必須由 ws-contract.d.ts 的 WsSubprotocol 取值，不得寫死字串（ADR-0019 §5／NFR5.4）。',
  },
]

// U14（EPN-19；functional-design R-04）：e2e spec 不得手寫伺服器訊框——同一個物件同時有 type 與
// payload 鍵即擋（只看 type 會誤擋 member-pages.spec.ts 的 { loc, msg, type: 'enum' }）。訊框一律由
// src/brain/testing/wsFrames.ts 的型別化建構器產生（受 tsc -b 檢查）。
const HAND_WRITTEN_FRAME_RESTRICTIONS = [
  {
    selector:
      "ObjectExpression:has(> Property[key.name='type']):has(> Property[key.name='payload'])",
    message:
      'e2e 不得手寫 WS 訊框；請呼叫 src/brain/testing/wsFrames.ts 的建構器（BR98.4／EPN-19）。',
  },
  {
    selector:
      "ObjectExpression:has(> Property[key.value='type']):has(> Property[key.value='payload'])",
    message:
      'e2e 不得手寫 WS 訊框；請呼叫 src/brain/testing/wsFrames.ts 的建構器（BR98.4／EPN-19）。',
  },
]

// U16（nfr-requirements N-03、nfr-design D-06）：選單檔案集合的禁令，使「必須紅燈」由 npm run lint 承載。
// no-restricted-syntax 在 flat config 以後者取代前者，故末端區塊必須展開 WS_SUBPROTOCOL_RESTRICTIONS，否則這幾個檔
// 會失去 ADR-0019 §5 的三條。擋無心之失、擋不住刻意繞過（經變數間接取得的儲存／主控台物件、computed 屬性
// `el['innerHTML']`、以不同相對路徑或路徑別名匯入建立函式；security-design §九 S-1）。
const OBJECT_PICKER_FILES = [
  'src/brain/objectPickerData.ts',
  'src/brain/objectPickerModel.ts',
  'src/components/brain/ObjectPicker*.tsx',
]
const OBJECT_PICKER_RESTRICTIONS = [
  { selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']", message: '選單名稱一律以文字節點呈現（OPN-13）。' },
  {
    selector: 'AssignmentExpression > MemberExpression.left[property.name=/^(innerHTML|outerHTML)$/]',
    message: '選單不得指派 innerHTML／outerHTML（OPN-13）。',
  },
  { selector: "NewExpression[callee.name='RegExp']", message: '搜尋以子字串比對，不得把輸入編譯成正規表示式（OPN-14）。' },
  { selector: "CallExpression[callee.name='RegExp']", message: '搜尋以子字串比對，不得把輸入編譯成正規表示式（OPN-14）。' },
  { selector: "NewExpression[callee.name='WebSocket']", message: '選單只經 useBrainSession().setWorkTarget 送出（NFR5.160）。' },
  {
    selector: "MemberExpression[object.name='window'][property.name=/^(localStorage|sessionStorage|indexedDB|caches)$/]",
    message: '選單不得使用瀏覽器儲存（OPN-15）。',
  },
]
const OBJECT_PICKER_CREATE_IMPORT = {
  importNames: ['createProject', 'createSystem'],
  message: '建立一律經 objectCreateAction（BR14.1／OPN-11）。',
}

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
    rules: {
      // ADR-0019 §5 — subprotocol 的消費端強制。
      //
      // `WsSubprotocol` 進契約（ADR-0019 §3）讓 subprotocol 的名稱與分隔字元受兩道
      // 型別閘門保護，但那條保護**只在前端真的由型別取值時成立**。前端寫死
      // `` [`bearer.${token}`] `` 時型別層碰不到它，而失敗是靜默的：後端改格式時
      // **握手全面失敗、四道閘門全綠**。
      //
      // 必須是 `error`：CI 跑 `npm run lint` = `eslint .`，**未加**
      // `--max-warnings 0`，所以 warn 級規則等於沒有閘門。
      //
      // 正確寫法（ADR-0020 C-1 起須同時帶協定名；原現例 DEMO 頁已隨 U13 移除，正式消費端為 U14）：
      //   const PROTOCOL_NAME: Sub['protocolName'] = 'cloud360.brain.v1';
      //   const SUBPROTOCOL_SCHEME: Sub['scheme'] = 'bearer';
      //   const SUBPROTOCOL_SEPARATOR: Sub['separator'] = '.';
      //   new WebSocket(url, [PROTOCOL_NAME, SUBPROTOCOL_SCHEME + SUBPROTOCOL_SEPARATOR + token])
      //
      // 擋不住的（誠實記載，ADR-0019 §5 已接受此殘餘）：先把字串存進變數再傳入。
      // AST 選擇器碰不到跨陳述的資料流，而 TypeScript 的模板字面量型別也無法區分
      // 「由常數組出的 bearer.x」與「手寫的 bearer.x」。它擋掉無心之失，擋不住
      // 刻意繞過——而刻意繞過會在 code review 留下痕跡，無心之失不會。
      'no-restricted-syntax': ['error', ...WS_SUBPROTOCOL_RESTRICTIONS],
    },
  },
  {
    files: ['tests/**/*.ts'],
    rules: {
      'no-restricted-syntax': ['error', ...WS_SUBPROTOCOL_RESTRICTIONS, ...HAND_WRITTEN_FRAME_RESTRICTIONS],
    },
  },
  {
    files: OBJECT_PICKER_FILES,
    rules: {
      'no-console': 'error',
      'no-restricted-globals': [
        'error',
        { name: 'localStorage', message: '選單不得使用瀏覽器儲存（OPN-15）。' },
        { name: 'sessionStorage', message: '選單不得使用瀏覽器儲存（OPN-15）。' },
        { name: 'indexedDB', message: '選單不得使用瀏覽器儲存（OPN-15）。' },
        { name: 'caches', message: '選單不得使用瀏覽器儲存（OPN-15）。' },
      ],
      'no-restricted-imports': [
        'error',
        {
          paths: [
            { name: '../../projects/projectsApi', ...OBJECT_PICKER_CREATE_IMPORT },
            { name: '../projects/projectsApi', ...OBJECT_PICKER_CREATE_IMPORT },
          ],
        },
      ],
      'no-restricted-syntax': ['error', ...WS_SUBPROTOCOL_RESTRICTIONS, ...OBJECT_PICKER_RESTRICTIONS],
    },
  },
])
