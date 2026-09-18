#!/usr/bin/env node
/**
 * 型別檔漂移檢查（C-8 的第二道 gate，跑在 CI 的 frontend job）。
 *
 * 為何需要第二道 gate：規格檔的 gate 在 backend job，它只保證「規格檔 == 後端
 * 程式碼」。若開發者重新 dump 了規格卻忘了重產型別檔，型別檔仍宣告舊形狀，而
 * `tsc -b` 檢查的是「用法是否符合型別檔」、不是「型別檔是否符合規格檔」——
 * 那條路徑會靜默通過，前端在執行期拿到未定義值。
 *
 * 本檢查重產型別到暫存檔並與 committed 的比對，不寫入 src/。
 */
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const SPEC = '../openapi.json';
const COMMITTED = 'src/types/api.d.ts';
// 與 package.json 的 gen:types 釘同一個版本。兩處若不一致，這道 gate 會比對到
// 不同產生器的輸出而誤報。
const GENERATOR = 'openapi-typescript@7.13.0';

const workdir = mkdtempSync(join(tmpdir(), 'api-types-'));
const regenerated = join(workdir, 'api.d.ts');

try {
  execFileSync('npx', ['--yes', GENERATOR, SPEC, '-o', regenerated], {
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
