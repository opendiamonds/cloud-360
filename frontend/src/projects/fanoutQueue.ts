/**
 * fanoutQueue.ts — `U23` 的扇出佇列（`BR88.3`、`PPN-01`–`PPN-04`）
 *
 * **契約（請勿改語意）**
 *
 * 清單頁對 P 個專案各取一次系統清單、詳情頁對 S 個系統各取一次需求欄位與變更紀錄。
 * 這些請求經同一個佇列發出：**同時最多 `FANOUT_CONCURRENCY` 個在途**，完成一個補一個，
 * **依入列順序（FIFO）**發出，**不截斷總數**。
 *
 * - 順序由呼叫端的入列順序決定（專案／系統 id 遞增；詳情頁先全部需求欄位、再全部
 *   變更紀錄，functional-design `R-04`），本模組不排序、不重排。
 * - **不截斷**：截斷會讓總覽的未填總和變成部分和、讓最近變更漏列——兩者都是把部分
 *   資料呈現成完整資料（`BR88.3`）。
 * - `cancel()` 之後尚未發出的工作**永不發出**，其 Promise 以 `FanoutCancelled` 拒絕；
 *   已在途的請求不中止（既有抓取函式沒有 `AbortSignal`），其結果由呼叫端的 `cancelled`
 *   旗標丟棄（`PPN-04`）。
 *
 * **4 是經驗值**，作用是限制「單一使用者一次進頁」的突發，**不是**連線池的保護機制
 * （`performance-design.md` §三；後端為單一進程、SQLAlchemy 預設池共 15 條，約 3 位
 * 使用者同時進入系統數多的專案即可耗盡——上限 4 或 8 都改變不了這件事）。
 *
 * 本檔**沒有任何主控台輸出**（`PPN-18`；本檔的主控台呼叫 grep 必須為 0）：取消是正常流程，不是錯誤。
 * 不持有任何 React state、沒有 React 依賴。
 */

/** 每頁同時在途的扇出請求上限（`PPN-01`）。**唯一的定義處。** */
export const FANOUT_CONCURRENCY = 4;

/** 佇列被取消時，尚未發出之工作的拒絕原因。呼叫端一律忽略它。 */
export class FanoutCancelled extends Error {
  constructor() {
    super('fanout cancelled');
    this.name = 'FanoutCancelled';
  }
}

export interface FanoutQueue {
  /** 入列一個工作；在途數低於上限時立即發出，否則排隊（FIFO）。 */
  enqueue<T>(task: () => Promise<T>): Promise<T>;
  /** 取消：尚未發出者不再發出（其 Promise 以 `FanoutCancelled` 拒絕）。 */
  cancel(): void;
}

interface Pending {
  start: () => void;
  abort: () => void;
}

export function createFanoutQueue(limit: number = FANOUT_CONCURRENCY): FanoutQueue {
  let inFlight = 0;
  let cancelled = false;
  const waiting: Pending[] = [];

  const pump = (): void => {
    while (!cancelled && inFlight < limit && waiting.length > 0) {
      const next = waiting.shift();
      if (!next) return;
      inFlight += 1;
      next.start();
    }
  };

  return {
    enqueue<T>(task: () => Promise<T>): Promise<T> {
      if (cancelled) return Promise.reject(new FanoutCancelled());
      return new Promise<T>((resolve, reject) => {
        waiting.push({
          start: () => {
            let result: Promise<T>;
            try {
              result = task();
            } catch (err) {
              result = Promise.reject(err);
            }
            result.then(resolve, reject).finally(() => {
              inFlight -= 1;
              pump();
            });
          },
          abort: () => reject(new FanoutCancelled()),
        });
        pump();
      });
    },
    cancel(): void {
      cancelled = true;
      const dropped = waiting.splice(0, waiting.length);
      for (const item of dropped) item.abort();
    },
  };
}
