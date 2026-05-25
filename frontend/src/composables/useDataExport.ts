/**
 * 数据导出工具
 */

/**
 * 导出为 JSON
 */
export function exportToJSON(data: unknown, filename: string): void {
  const json = JSON.stringify(data, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  downloadBlob(blob, `${filename}.json`)
}

/**
 * 导出为 CSV
 */
export function exportToCSV(data: Record<string, unknown>[], filename: string): void {
  if (data.length === 0) {
    throw new Error('No data to export')
  }

  // 获取所有列名
  const columns = Object.keys(data[0])

  // 生成 CSV 头部
  const header = columns.map(escapeCSVValue).join(',')

  // 生成 CSV 行
  const rows = data.map((row) => {
    return columns.map((col) => escapeCSVValue(row[col])).join(',')
  })

  // 组合 CSV 内容
  const csv = [header, ...rows].join('\n')

  // 添加 BOM 以支持 Excel 正确显示中文
  const bom = '﻿'
  const blob = new Blob([bom + csv], { type: 'text/csv;charset=utf-8;' })
  downloadBlob(blob, `${filename}.csv`)
}

/**
 * 转义 CSV 值
 */
function escapeCSVValue(value: unknown): string {
  if (value === null || value === undefined) {
    return ''
  }

  const str = String(value)

  // 如果包含逗号、引号或换行符，需要用引号包裹
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    // 引号需要转义为两个引号
    return `"${str.replace(/"/g, '""')}"`
  }

  return str
}

/**
 * 导出为 Markdown 表格
 */
export function exportToMarkdown(data: Record<string, unknown>[], filename: string): void {
  if (data.length === 0) {
    throw new Error('No data to export')
  }

  // 获取所有列名
  const columns = Object.keys(data[0])

  // 生成表头
  const header = `| ${columns.join(' | ')} |`
  const separator = `| ${columns.map(() => '---').join(' | ')} |`

  // 生成表格行
  const rows = data.map((row) => {
    const values = columns.map((col) => String(row[col] ?? ''))
    return `| ${values.join(' | ')} |`
  })

  // 组合 Markdown 内容
  const markdown = [header, separator, ...rows].join('\n')

  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8;' })
  downloadBlob(blob, `${filename}.md`)
}

/**
 * 导出为 HTML 表格
 */
export function exportToHTML(data: Record<string, unknown>[], filename: string): void {
  if (data.length === 0) {
    throw new Error('No data to export')
  }

  // 获取所有列名
  const columns = Object.keys(data[0])

  // 生成表头
  const thead = `
    <thead>
      <tr>
        ${columns.map((col) => `<th>${escapeHTML(col)}</th>`).join('\n        ')}
      </tr>
    </thead>
  `

  // 生成表格行
  const tbody = `
    <tbody>
      ${data
        .map(
          (row) => `
      <tr>
        ${columns.map((col) => `<td>${escapeHTML(String(row[col] ?? ''))}</td>`).join('\n        ')}
      </tr>`,
        )
        .join('\n      ')}
    </tbody>
  `

  // 组合 HTML 内容
  const html = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHTML(filename)}</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      padding: 20px;
      max-width: 1200px;
      margin: 0 auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 20px;
    }
    th, td {
      border: 1px solid #ddd;
      padding: 12px;
      text-align: left;
    }
    th {
      background-color: #f5f5f5;
      font-weight: 600;
    }
    tr:nth-child(even) {
      background-color: #fafafa;
    }
    tr:hover {
      background-color: #f0f0f0;
    }
  </style>
</head>
<body>
  <h1>${escapeHTML(filename)}</h1>
  <table>
    ${thead}
    ${tbody}
  </table>
</body>
</html>
  `

  const blob = new Blob([html], { type: 'text/html;charset=utf-8;' })
  downloadBlob(blob, `${filename}.html`)
}

/**
 * 转义 HTML 特殊字符
 */
function escapeHTML(str: string): string {
  const div = document.createElement('div')
  div.textContent = str
  return div.innerHTML
}

/**
 * 下载 Blob
 */
function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.style.display = 'none'

  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  // 释放 URL 对象
  setTimeout(() => URL.revokeObjectURL(url), 100)
}

/**
 * 数据导出 composable
 */
export function useDataExport() {
  return {
    exportToJSON,
    exportToCSV,
    exportToMarkdown,
    exportToHTML,
  }
}

/**
 * 导出格式选项
 */
export const EXPORT_FORMATS = [
  { value: 'json', label: 'JSON', icon: '📄' },
  { value: 'csv', label: 'CSV', icon: '📊' },
  { value: 'markdown', label: 'Markdown', icon: '📝' },
  { value: 'html', label: 'HTML', icon: '🌐' },
] as const

export type ExportFormat = (typeof EXPORT_FORMATS)[number]['value']
