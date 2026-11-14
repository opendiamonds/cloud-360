#!/usr/bin/env node
/**
 * WS 契約型別檔漂移檢查（`U2` / `NFR5.1` 的第二道 gate，跑在 CI 的 frontend job）。
 *
 * 為何需要第二道 gate（`BR4.3`，理由與既有的 `check-api-types.mjs` 同型）：第一道
 * 在 backend job（`python scripts/dump_ws_contract.py --check`），它只保證
 * 「`ws-contract.json` == 後端契約模組」。若開發者重新 dump 了規格卻忘了重產型別檔，
 * 型別檔仍宣告舊形狀，而 `tsc -b` 檢查的是「用法是否符合型別檔」、**不是**
 * 「型別檔是否符合規格檔」——那條路徑會靜默通過，前端在執行期拿到未定義值。
 *
 * 為何 WebSocket 需要自己的一組 gate：FastAPI 不登錄 websocket route，所以既有的
 * `/api/collab/ws/...` 不在 `openapi.json` 的 42 個 path 內。既有兩道型別閘門對
 * WebSocket **結構上完全無效**——不是覆蓋不足，是那條變更路徑上沒有任何斷言存在。
 *
 * 產生器的取得方式與釘版：見 `check-api-types.mjs` 的檔頭（同一支
 * `openapi-typescript`，同一份 `devDependencies` 釘選，同一個 `overrides` 的理由）。
 * 本檔**不持有版本字串**。
 *
 * 本檢查重產型別到暫存檔並與 committed 的比對，不寫入 src/。
 */
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { createRequire } from 'node:module';

const SPEC = '../ws-contract.json';
const COMMITTED = 'src/types/ws-contract.d.ts';

// 本地解析：由套件自己宣告的 bin 欄位推出入口路徑（不能直接 resolve
// 'openapi-typescript/bin/cli.js'，該套件的 exports 有一條 "./*.js" -> "./*.mjs"
// 改寫規則會指到不存在的檔）。找不到即拋錯——fail-closed。
const require = createRequire(import.meta.url);
const generatorPkgJson = require.resolve('openapi-typescript/package.json');
const GENERATOR_BIN = join(
  dirname(generatorPkgJson),
  JSON.parse(readFileSync(generatorPkgJson, 'utf8')).bin['openapi-typescript']
);

/**
 * `BR4.4` — 產生的型別檔必須保留 `sideEffect` 兩個哨兵值的說明註解。
 *
 * 為何這一條非驗不可：TypeScript 會把 `"none" | "unknown" | string` 塌縮為
 * `string`，IDE 完全不提示那兩個字面值。所以它們的語意在消費端**只能**靠型別檔
 * 保留 JSDoc 來傳達。若有人拿掉 Pydantic 欄位的 `description=`，註解會從型別檔
 * 靜默消失，兩個哨兵值的語意隨之流失，而**兩個型別檔仍然逐位元一致**——
 * 純比對的漂移檢查看不到這件事，所以它需要自己一條斷言。
 *
 * 把 `"unknown"` 當成 `"none"` 處理，等於對使用者宣稱「停掉不留半成品」，而
 * `components.md` 逐字說系統不承諾那件事（`BR2.10`）。
 */
function assertSideEffectSentinelDoc(source, origin) {
  const field = /\n[ \t]*sideEffect\??[ \t]*:/.exec(source);
  if (field === null) {
    throw new Error(
      `BR4.4 無法判定：${origin} 找不到 sideEffect 欄位。` +
        '契約的 WorkItem.sideEffect 若被改名或移除，請一併更新本斷言。'
    );
  }

  const before = source.slice(0, field.index);
  const close = before.lastIndexOf('*/');
  const open = close === -1 ? -1 : before.lastIndexOf('/**', close);
  if (open === -1) {
    throw new Error(
      `BR4.4 違反：${origin} 的 sideEffect 欄位上方沒有任何 JSDoc 區塊。` +
        '兩個哨兵值（"none"／"unknown"）的語意在消費端已完全消失。'
    );
  }

  // 註解必須**緊貼**該欄位：中間夾了別的宣告時，那段 JSDoc 屬於別的欄位。
  if (before.slice(close + 2).trim() !== '') {
    throw new Error(
      `BR4.4 違反：${origin} 的 sideEffect 上方最近的 JSDoc 並未緊貼該欄位。`
    );
  }

  const doc = before.slice(open, close + 2);
  if (!doc.includes('@description')) {
    throw new Error(
      `BR4.4 違反：${origin} 的 sideEffect JSDoc 沒有 @description 段——` +
        '通常表示後端 Pydantic 欄位的 description= 被拿掉了。'
    );
  }
  for (const sentinel of ['"none"', '"unknown"']) {
    if (!doc.includes(sentinel)) {
      throw new Error(
        `BR4.4 違反：${origin} 的 sideEffect 說明未提到哨兵值 ${sentinel}。` +
          '請確認 backend/services/brain_ws_contract.py 的 WorkItem.sideEffect ' +
          'description= 仍寫出兩個哨兵值的語意，然後重跑 npm run gen:ws-types。'
      );
    }
  }
}

const workdir = mkdtempSync(join(tmpdir(), 'ws-types-'));
const regenerated = join(workdir, 'ws-contract.d.ts');

try {
  execFileSync(process.execPath, [GENERATOR_BIN, SPEC, '-o', regenerated], {
    stdio: ['ignore', 'ignore', 'inherit'],
  });

  const expected = readFileSync(regenerated, 'utf8');
  const actual = readFileSync(COMMITTED, 'utf8');

  // BR4.4 先驗**重產的**那一份：它才反映規格檔的當前內容。只驗 committed 的
  // 那一份時，「description 被拿掉但型別檔忘了重產」會讓斷言看著舊註解過關。
  //
  // 這裡 catch 只為了把訊息印乾淨（不帶 stack），**不是**吞掉錯誤——立刻 exit 1。
  // 一個把斷言例外吞掉後回報「一致」的檢查腳本，它的綠燈不構成任何證據。
  try {
    assertSideEffectSentinelDoc(expected, `由 ${SPEC} 重產的型別檔`);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  }

  if (expected !== actual) {
    console.error(
      `型別檔已漂移：${COMMITTED} 與 ${SPEC} 不一致。\n` +
        '契約改了但型別檔沒重產。請於 frontend/ 執行\n' +
        '  npm run gen:ws-types\n' +
        '並 commit 產出。'
    );
    process.exit(1);
  }

  console.log('WS 契約型別檔與規格檔一致，且 sideEffect 的哨兵值說明仍在（BR4.4）。');
  process.exit(0);
} finally {
  rmSync(workdir, { recursive: true, force: true });
}
