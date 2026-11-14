#!/usr/bin/env node
/**
 * 型別檔漂移檢查（C-8 的第二道 gate，跑在 CI 的 frontend job）。
 *
 * 為何需要第二道 gate：規格檔的 gate 在 backend job，它只保證「規格檔 == 後端
 * 程式碼」。若開發者重新 dump 了規格卻忘了重產型別檔，型別檔仍宣告舊形狀，而
 * `tsc -b` 檢查的是「用法是否符合型別檔」、不是「型別檔是否符合規格檔」——
 * 那條路徑會靜默通過，前端在執行期拿到未定義值。
 *
 * 產生器的版本從何而來（ADR-0019 §2，原本的註解已作廢）：本檔**不再持有版本
 * 字串**。`openapi-typescript` 已是 `package.json` 的 `devDependencies`（精確釘
 * `7.13.0`），由 `npm ci` 依 `package-lock.json` 的 `integrity` 雜湊安裝，本檔以
 * `node_modules` 內解析出的本地執行檔呼叫它。從前這裡與 `gen:types` 各存一份
 * 版本字串、靠註解提醒同步，而兩份都不是依賴鎖定——實測 `grep -c
 * 'openapi-typescript' package-lock.json` 回 0，即每次 CI 都從 npm registry 取
 * 回未鎖定的第三方程式碼來執行這道 gate。版本字串的物化份數現在是 1
 * （`devDependencies`），升版時必須在同一個 PR 內重產並 commit 兩個型別檔
 * （`api.d.ts` 與 `ws-contract.d.ts`）。
 *
 * 為何 `package.json` 有一條 `overrides`：`openapi-typescript@7.13.0` 宣告
 * `peerDependencies: typescript ^5.x`，而本專案用 `typescript ~6.0.2`，所以把它
 * 放進 `devDependencies` 會讓 `npm install`／`npm ci` 直接 ERESOLVE 失敗。從前
 * 用 `npx --yes` 看不到這個衝突——那正是「未鎖定」的另一面。處置是最小範圍的
 * `overrides`（只改這一個套件看到的 `typescript`，指向根專案的同一版），不是
 * 全域 `legacy-peer-deps`。實測：本地產生器產出的 `api.d.ts` 與 `npx --yes` 時代
 * committed 的版本**逐位元相同**，故 ADR-0019 §2 要求的一次性複驗無差異。
 *
 * 本檢查重產型別到暫存檔並與 committed 的比對，不寫入 src/。
 */
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { createRequire } from 'node:module';

const SPEC = '../openapi.json';
const COMMITTED = 'src/types/api.d.ts';

// 本地解析：由套件**自己宣告的** bin 欄位推出入口路徑，不經 PATH、不經 npx。
// 不直接 require.resolve('openapi-typescript/bin/cli.js')，因為該套件的 exports
// 有一條 "./*.js" -> "./*.mjs" 改寫規則，會把實際存在的 cli.js 解析成不存在的
// cli.mjs。resolve package.json 再讀 bin 是唯一不依賴那張 map 的路徑。
// 找不到即拋錯（fail-closed）——一個「產生器不在」卻回報「型別檔一致」的 gate
// 比沒有 gate 更糟。
const require = createRequire(import.meta.url);
const generatorPkgJson = require.resolve('openapi-typescript/package.json');
const GENERATOR_BIN = join(
  dirname(generatorPkgJson),
  JSON.parse(readFileSync(generatorPkgJson, 'utf8')).bin['openapi-typescript']
);

const workdir = mkdtempSync(join(tmpdir(), 'api-types-'));
const regenerated = join(workdir, 'api.d.ts');

try {
  execFileSync(process.execPath, [GENERATOR_BIN, SPEC, '-o', regenerated], {
    stdio: ['ignore', 'ignore', 'inherit'],
  });

  const expected = readFileSync(regenerated, 'utf8');
  const actual = readFileSync(COMMITTED, 'utf8');

  if (expected === actual) {
    console.log('API 型別檔與規格檔一致。');
    process.exit(0);
  }

  console.error(
    `型別檔已漂移：${COMMITTED} 與 ${SPEC} 不一致。\n` +
      '規格改了但型別檔沒重產。請於 frontend/ 執行\n' +
      '  npm run gen:types\n' +
      '並 commit 產出。'
  );
  process.exit(1);
} finally {
  rmSync(workdir, { recursive: true, force: true });
}
