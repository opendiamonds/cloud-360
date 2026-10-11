import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

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
      // 正確寫法（現例 `src/pages/BrainPage.tsx`）：
      //   const SUBPROTOCOL_SCHEME: Sub['scheme'] = 'bearer';
      //   const SUBPROTOCOL_SEPARATOR: Sub['separator'] = '.';
      //   new WebSocket(url, [SUBPROTOCOL_SCHEME + SUBPROTOCOL_SEPARATOR + token])
      //
      // 擋不住的（誠實記載，ADR-0019 §5 已接受此殘餘）：先把字串存進變數再傳入。
      // AST 選擇器碰不到跨陳述的資料流，而 TypeScript 的模板字面量型別也無法區分
      // 「由常數組出的 bearer.x」與「手寫的 bearer.x」。它擋掉無心之失，擋不住
      // 刻意繞過——而刻意繞過會在 code review 留下痕跡，無心之失不會。
      'no-restricted-syntax': [
        'error',
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
      ],
    },
  },
])
