/**
 * 单一权威源 — 前端镜像，跟后端 `app/services/reliability_tier.py` 一一对应。
 *
 * 阈值（`STRONG_THRESHOLD = 0.7` / `FAIR_THRESHOLD = 0.4`）和 `(label, slug)`
 * 表（`('强','strong')` / `('一般','fair')` / `('弱','weak')` / `('未知','unknown')`）
 * 必须与后端 **完全相同**：决策看板 chip、报告 markdown 字面、打印/PDF
 * HTML 都靠这一份契约把同一个 reliability 数值翻译成同一个 tier。
 *
 * 双端契约由这两份测试同步锁住——任意一端改阈值，两边同时红：
 *
 * - 前端：`frontend/src/composables/__tests__/useReliabilityTier.spec.ts`
 * - 后端：`backend/tests/test_reliability_tier.py`
 *
 * `naiveType` 是该 tier 在 Naive UI `NTag.type` 上的取值：
 *
 * - 强 → success（emerald）
 * - 一般 → warning（amber）
 * - 弱 → error（red）
 * - 未知 → default（中性灰，与同文件 `riskColor` unknown 行为一致）
 *
 * 这三档颜色与后端 `report_html._PRINT_CSS` 中
 * `metric-reliability-{strong|fair|weak|unknown}` 的颜色映射严格对齐，
 * 看板 chip 与下载 HTML/PDF 的视觉一致。
 */

import { computed, type ComputedRef, type Ref } from 'vue'

// ---------- 阈值（必须与后端硬等）-------------------------------------------

/** reliability ≥ STRONG_THRESHOLD 视为强证据。镜像后端 STRONG_THRESHOLD=0.7。 */
export const STRONG_THRESHOLD = 0.7

/** reliability ≥ FAIR_THRESHOLD 且 < STRONG_THRESHOLD 为一般。镜像后端 0.4。 */
export const FAIR_THRESHOLD = 0.4

// ---------- 类型与不可变 tier 表 ---------------------------------------------

export type ReliabilityLabel = '强' | '一般' | '弱' | '未知'
export type ReliabilitySlug = 'strong' | 'fair' | 'weak' | 'unknown'
export type ReliabilityNaiveType = 'success' | 'warning' | 'error' | 'default'

export interface ReliabilityTier {
  readonly label: ReliabilityLabel
  readonly slug: ReliabilitySlug
  readonly naiveType: ReliabilityNaiveType
}

const TIER_STRONG: ReliabilityTier = Object.freeze({
  label: '强',
  slug: 'strong',
  naiveType: 'success',
})
const TIER_FAIR: ReliabilityTier = Object.freeze({
  label: '一般',
  slug: 'fair',
  naiveType: 'warning',
})
const TIER_WEAK: ReliabilityTier = Object.freeze({
  label: '弱',
  slug: 'weak',
  naiveType: 'error',
})
const TIER_UNKNOWN: ReliabilityTier = Object.freeze({
  label: '未知',
  slug: 'unknown',
  naiveType: 'default',
})

/** 顺序与后端 `TIERS` 一致：strong → fair → weak → unknown。 */
export const TIERS: readonly ReliabilityTier[] = Object.freeze([
  TIER_STRONG,
  TIER_FAIR,
  TIER_WEAK,
  TIER_UNKNOWN,
])

// ---------- 核心函数 ---------------------------------------------------------

/**
 * 把任意 reliability 输入映射成 `ReliabilityTier`。
 *
 * 规则（必须与后端 `reliability_tier.tier_for` 等价）：
 *
 * - `null` / `undefined` → 未知
 * - 字符串：`""` / 仅空白 / 不可解析 → 未知；可解析数字按下面继续
 * - 数字（含 `Number(value)` 解析结果）：
 *   - `f >= STRONG_THRESHOLD` (0.7) → 强
 *   - `f >= FAIR_THRESHOLD` (0.4) → 一般
 *   - 其余（含 `NaN`，与后端一致：`NaN >= x` 始终 false 落入 weak）→ 弱
 *
 * 签名故意取 `unknown`：JSON 反序列化和测试样本里会出现 `string` / `null` /
 * `NaN`，宽签名让契约测试与后端的同一组样本集一一对齐，无需 cast。
 */
export function tierFor(value: unknown): ReliabilityTier {
  if (value === null || value === undefined) return TIER_UNKNOWN

  let f: number
  if (typeof value === 'number') {
    f = value
  } else if (typeof value === 'string') {
    const trimmed = value.trim()
    if (trimmed === '') return TIER_UNKNOWN
    const parsed = Number(trimmed)
    if (Number.isNaN(parsed)) return TIER_UNKNOWN
    f = parsed
  } else if (typeof value === 'boolean') {
    // 后端 float(True)=1.0 / float(False)=0.0；保持等价以避免任何隐性 quirk。
    f = value ? 1 : 0
  } else {
    return TIER_UNKNOWN
  }

  // NaN 与后端一致：所有 `>=` 比较都 false，落 weak（不是 unknown）。
  if (f >= STRONG_THRESHOLD) return TIER_STRONG
  if (f >= FAIR_THRESHOLD) return TIER_FAIR
  return TIER_WEAK
}

/**
 * Vue composable —— 把响应式 reliability ref 映射成响应式 tier。
 *
 * `DecisionBoardPanel` 的 `reliabilityColor` 通过
 * `useReliabilityTier(reliability).value.naiveType` 拿到 NTag 颜色，
 * 不再需要内联 `>=0.7` / `>=0.4` 阈值。
 */
export function useReliabilityTier(
  value: Ref<number | null | undefined>,
): ComputedRef<ReliabilityTier> {
  return computed(() => tierFor(value.value))
}
