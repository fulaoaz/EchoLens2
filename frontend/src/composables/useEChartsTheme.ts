/**
 * ECharts 图表主题配置
 */

import { computed } from 'vue'
import type { EChartsOption } from 'echarts'

/**
 * 获取 ECharts 深色主题配置
 */
export function getEChartsDarkTheme(): EChartsOption {
  return {
    backgroundColor: 'transparent',
    textStyle: {
      color: '#ffffffd9',
    },
    title: {
      textStyle: {
        color: '#ffffffd9',
      },
      subtextStyle: {
        color: '#ffffffa6',
      },
    },
    legend: {
      textStyle: {
        color: '#ffffffd9',
      },
    },
    tooltip: {
      backgroundColor: '#2c2c32',
      borderColor: '#ffffff1a',
      textStyle: {
        color: '#ffffffd9',
      },
    },
    grid: {
      borderColor: '#ffffff1a',
    },
    xAxis: {
      axisLine: {
        lineStyle: {
          color: '#ffffff1a',
        },
      },
      axisLabel: {
        color: '#ffffffa6',
      },
      splitLine: {
        lineStyle: {
          color: '#ffffff1a',
        },
      },
    },
    yAxis: {
      axisLine: {
        lineStyle: {
          color: '#ffffff1a',
        },
      },
      axisLabel: {
        color: '#ffffffa6',
      },
      splitLine: {
        lineStyle: {
          color: '#ffffff1a',
        },
      },
    },
  }
}

/**
 * 获取 ECharts 浅色主题配置
 */
export function getEChartsLightTheme(): EChartsOption {
  return {
    backgroundColor: 'transparent',
    textStyle: {
      color: '#18181c',
    },
    title: {
      textStyle: {
        color: '#18181c',
      },
      subtextStyle: {
        color: '#51525c',
      },
    },
    legend: {
      textStyle: {
        color: '#18181c',
      },
    },
    tooltip: {
      backgroundColor: '#ffffff',
      borderColor: '#e5e5e5',
      textStyle: {
        color: '#18181c',
      },
    },
    grid: {
      borderColor: '#e5e5e5',
    },
    xAxis: {
      axisLine: {
        lineStyle: {
          color: '#e5e5e5',
        },
      },
      axisLabel: {
        color: '#51525c',
      },
      splitLine: {
        lineStyle: {
          color: '#e5e5e5',
        },
      },
    },
    yAxis: {
      axisLine: {
        lineStyle: {
          color: '#e5e5e5',
        },
      },
      axisLabel: {
        color: '#51525c',
      },
      splitLine: {
        lineStyle: {
          color: '#e5e5e5',
        },
      },
    },
  }
}

/**
 * 根据深色模式状态获取 ECharts 主题
 */
export function useEChartsTheme(isDark: boolean) {
  return computed(() => {
    return isDark ? getEChartsDarkTheme() : getEChartsLightTheme()
  })
}
