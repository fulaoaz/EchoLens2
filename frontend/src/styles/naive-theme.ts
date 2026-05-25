/**
 * Naive UI dark theme overrides bound to design tokens (src/styles/tokens.css).
 * Apply via <n-config-provider :theme="darkTheme" :theme-overrides="darkThemeOverrides" />.
 */
import type { GlobalThemeOverrides } from 'naive-ui'

export const darkThemeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#5B8DEF',
    primaryColorHover: '#7AA3F2',
    primaryColorPressed: '#4779D8',
    primaryColorSuppl: '#5B8DEF',
    infoColor: '#5B8DEF',
    successColor: '#00E5A8',
    warningColor: '#FFB454',
    errorColor: '#FF6B6B',
    bodyColor: '#0B1020',
    cardColor: '#1A2142',
    modalColor: '#131932',
    popoverColor: '#1A2142',
    tableHeaderColor: '#131932',
    tableColor: '#1A2142',
    textColorBase: '#E2E8F0',
    textColor1: '#E2E8F0',
    textColor2: '#CBD5E1',
    textColor3: '#94A3B8',
    textColorDisabled: '#64748B',
    placeholderColor: '#94A3B8',
    borderColor: 'rgba(91, 141, 239, 0.2)',
    dividerColor: 'rgba(91, 141, 239, 0.15)',
    hoverColor: 'rgba(91, 141, 239, 0.08)',
    fontFamily:
      "'Inter', '思源黑体', 'Source Han Sans CN', system-ui, -apple-system, 'Segoe UI', sans-serif",
    fontFamilyMono: "'JetBrains Mono', ui-monospace, Menlo, monospace",
    borderRadius: '10px',
    borderRadiusSmall: '6px',
  },
  Card: {
    color: '#1A2142',
    colorEmbedded: '#131932',
    borderColor: 'rgba(91, 141, 239, 0.2)',
    titleTextColor: '#E2E8F0',
    textColor: '#CBD5E1',
    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.4)',
    borderRadius: '16px',
  },
  Button: {
    textColorPrimary: '#FFFFFFFF',
    borderRadiusMedium: '8px',
    fontWeight: '500',
  },
  Tabs: {
    tabTextColorActiveLine: '#5B8DEF',
    tabTextColorHoverLine: '#7AA3F2',
    barColor: '#5B8DEF',
    tabFontWeightActive: '600',
  },
  DataTable: {
    thColor: '#131932',
    tdColor: '#1A2142',
    thTextColor: '#CBD5E1',
    tdTextColor: '#E2E8F0',
    borderColor: 'rgba(91, 141, 239, 0.15)',
    borderRadius: '10px',
  },
  Tag: {
    borderRadius: '999px',
    fontWeightStrong: '500',
  },
  Progress: {
    railColor: 'rgba(91, 141, 239, 0.15)',
    fillColor: '#5B8DEF',
    fillColorSuccess: '#00E5A8',
    fillColorWarning: '#FFB454',
    fillColorError: '#FF6B6B',
    textColorCircle: '#E2E8F0',
  },
  Layout: {
    color: '#0B1020',
    siderColor: '#131932',
    headerColor: '#131932',
    footerColor: '#131932',
    headerBorderColor: 'rgba(91, 141, 239, 0.15)',
    siderBorderColor: 'rgba(91, 141, 239, 0.15)',
  },
  Menu: {
    color: '#131932',
    itemColorActive: 'rgba(91, 141, 239, 0.18)',
    itemTextColorActive: '#5B8DEF',
    itemTextColorActiveHover: '#7AA3F2',
    arrowColorActive: '#5B8DEF',
  },
  Statistic: {
    valueFontFamily: "'JetBrains Mono', ui-monospace, Menlo, monospace",
    valueFontSize: '28px',
  },
  Empty: {
    iconColor: '#64748B',
    textColor: '#94A3B8',
  },
}

export default darkThemeOverrides
