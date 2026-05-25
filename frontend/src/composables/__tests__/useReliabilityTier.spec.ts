/**
 * Reliability tier 阈值契约 — 前端这一半。
 *
 * 后端那一半在：`backend/tests/test_reliability_tier.py`。
 *
 * 两份测试用 **完全相同** 的边界样本集，确保对同一个 reliability 输入，
 * 前端 composable（`@/composables/useReliabilityTier`）和后端 shared
 * 模块（`app.services.reliability_tier`）输出同一个 `(label, slug)` 对。
 *
 * 任何一端改 `STRONG_THRESHOLD = 0.7` / `FAIR_THRESHOLD = 0.4` / `tierFor` 规则，
 * 两端测试必然同时红。这正是看板 chip 颜色与打印/PDF
 * `metric-reliability-{strong|fair|weak|unknown}` 视觉对齐的最后一道防线。
 */

import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import {
  STRONG_THRESHOLD,
  FAIR_THRESHOLD,
  TIERS,
  tierFor,
  useReliabilityTier,
  type ReliabilityLabel,
  type ReliabilityNaiveType,
  type ReliabilitySlug,
} from '../useReliabilityTier'

// ---------- 边界样本集（与后端 `_SAMPLES` 一一对齐）-------------------------

interface Sample {
  readonly value: unknown
  readonly label: ReliabilityLabel
  readonly slug: ReliabilitySlug
  readonly naiveType: ReliabilityNaiveType
}

const SAMPLES: readonly Sample[] = [
  // weak: 严格小于 FAIR_THRESHOLD (0.4)
  { value: 0.0, label: '弱', slug: 'weak', naiveType: 'error' },
  { value: 0.1, label: '弱', slug: 'weak', naiveType: 'error' },
  { value: 0.39, label: '弱', slug: 'weak', naiveType: 'error' },
  { value: 0.3999999, label: '弱', slug: 'weak', naiveType: 'error' },
  // fair: [FAIR_THRESHOLD, STRONG_THRESHOLD)
  { value: 0.4, label: '一般', slug: 'fair', naiveType: 'warning' },
  { value: 0.5, label: '一般', slug: 'fair', naiveType: 'warning' },
  { value: 0.69, label: '一般', slug: 'fair', naiveType: 'warning' },
  { value: 0.6999999, label: '一般', slug: 'fair', naiveType: 'warning' },
  // strong: ≥ STRONG_THRESHOLD (0.7)
  { value: 0.7, label: '强', slug: 'strong', naiveType: 'success' },
  { value: 0.85, label: '强', slug: 'strong', naiveType: 'success' },
  { value: 1.0, label: '强', slug: 'strong', naiveType: 'success' },
  // 整数 0 / 1（JSON snapshot 可能上来就是整数）
  { value: 0, label: '弱', slug: 'weak', naiveType: 'error' },
  { value: 1, label: '强', slug: 'strong', naiveType: 'success' },
  // 未知：null / undefined / 空字符串 / 不可解析字符串
  { value: null, label: '未知', slug: 'unknown', naiveType: 'default' },
  { value: undefined, label: '未知', slug: 'unknown', naiveType: 'default' },
  { value: '', label: '未知', slug: 'unknown', naiveType: 'default' },
  { value: '   ', label: '未知', slug: 'unknown', naiveType: 'default' },
  { value: 'abc', label: '未知', slug: 'unknown', naiveType: 'default' },
  // NaN：与后端一致 — `NaN >= x` 永远 false，落入 weak（不是 unknown）
  { value: Number.NaN, label: '弱', slug: 'weak', naiveType: 'error' },
]

// ---------- 阈值常量保钉 ----------------------------------------------------

describe('reliability tier · 阈值常量保钉', () => {
  it('STRONG_THRESHOLD === 0.7（与后端 reliability_tier.py 严格对齐）', () => {
    expect(STRONG_THRESHOLD).toBe(0.7)
  })

  it('FAIR_THRESHOLD === 0.4（与后端 reliability_tier.py 严格对齐）', () => {
    expect(FAIR_THRESHOLD).toBe(0.4)
  })

  it('STRONG_THRESHOLD > FAIR_THRESHOLD（保留隐式排序不变量）', () => {
    expect(STRONG_THRESHOLD).toBeGreaterThan(FAIR_THRESHOLD)
  })
})

// ---------- 边界样本表驱动 ---------------------------------------------------

describe('tierFor · 边界值映射到固定的 (label, slug, naiveType)', () => {
  for (const { value, label, slug, naiveType } of SAMPLES) {
    const desc = `${String(value)} → (${label}, ${slug}, ${naiveType})`
    it(desc, () => {
      const tier = tierFor(value)
      expect(tier.label).toBe(label)
      expect(tier.slug).toBe(slug)
      expect(tier.naiveType).toBe(naiveType)
    })
  }
})

// ---------- composable 包装 --------------------------------------------------

describe('useReliabilityTier · 响应式 ref → 响应式 tier', () => {
  it('对每个边界样本，composable 与裸 tierFor 输出完全一致', () => {
    for (const { value } of SAMPLES) {
      // composable 签名只接 number | null | undefined；string/boolean 等
      // 走 tierFor 直接路径，已在上一组测试覆盖。
      if (value === null || value === undefined || typeof value === 'number') {
        const r = ref<number | null | undefined>(value as number | null | undefined)
        const tier = useReliabilityTier(r)
        expect(tier.value).toEqual(tierFor(value))
      }
    }
  })

  it('ref 变化时 tier 自动重算（响应式契约）', () => {
    const r = ref<number | null | undefined>(0.85)
    const tier = useReliabilityTier(r)
    expect(tier.value.slug).toBe('strong')
    r.value = 0.5
    expect(tier.value.slug).toBe('fair')
    r.value = 0.1
    expect(tier.value.slug).toBe('weak')
    r.value = null
    expect(tier.value.slug).toBe('unknown')
    r.value = 0.7
    expect(tier.value.slug).toBe('strong')
    r.value = 0.6999999
    expect(tier.value.slug).toBe('fair')
    r.value = 0.4
    expect(tier.value.slug).toBe('fair')
    r.value = 0.3999999
    expect(tier.value.slug).toBe('weak')
  })
})

// ---------- (label, slug) 唯一性 --------------------------------------------

describe('TIERS · 四个 tier 唯一稳定且 slug 全 ASCII', () => {
  it('四档 (label, slug) 互不重复，与后端 TIERS 顺序一致', () => {
    const labels = TIERS.map((t) => t.label)
    const slugs = TIERS.map((t) => t.slug)
    expect(new Set(labels).size).toBe(4)
    expect(new Set(slugs).size).toBe(4)
    // 顺序：strong → fair → weak → unknown，与后端 TIERS 一致
    expect(slugs).toEqual(['strong', 'fair', 'weak', 'unknown'])
  })

  it('slug 必须是纯 ASCII 字母（CSS 选择器 metric-reliability-{slug} 安全）', () => {
    for (const { slug } of TIERS) {
      // 仅小写字母 + 长度 >0
      expect(slug).toMatch(/^[a-z]+$/)
    }
  })

  it('每个 (label, slug) 都被边界样本集真实覆盖至少一次', () => {
    const produced = new Set<string>()
    for (const { value } of SAMPLES) {
      const t = tierFor(value)
      produced.add(`${t.label}|${t.slug}`)
    }
    for (const { label, slug } of TIERS) {
      expect(produced).toContain(`${label}|${slug}`)
    }
  })
})
