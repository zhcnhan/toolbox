import { addLog } from '../logStore'

const BASE = '/api'

async function request(path, options = {}) {
  const url = `${BASE}${path}`
  const method = options.method || 'GET'
  addLog('info', 'api', `\u2192 ${method} ${path}`)
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      const msg = err.detail || res.statusText || `HTTP ${res.status}`
      addLog('error', 'api', `\u2717 ${method} ${path} \u2192 ${res.status} ${msg}`)
      throw new Error(msg)
    }
    const data = await res.json()
    addLog('success', 'api', `\u2713 ${method} ${path} \u2192 ${res.status}`)
    return data
  } catch (err) {
    if (!err.message?.includes('\u2717')) {
      addLog('error', 'api', `\u2717 ${method} ${path} \u2192 ${err.message}`)
    }
    throw err
  }
}

export const api = {
  /** 健康检查 */
  health: () => request('/health'),

  /** 获取所有格式信息 */
  getFormats: () => request('/formats'),

  /** 获取某类别格式 */
  getCategoryFormats: (category) => request(`/formats/${category}`),

  /** 上传文件 */
  uploadFiles: async (files) => {
    addLog('info', 'api', `\u2192 POST /upload (${files.length} 个文件)`)
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    try {
      const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        const msg = err.detail || `HTTP ${res.status}`
        addLog('error', 'api', `\u2717 POST /upload \u2192 ${res.status} ${msg}`)
        throw new Error(msg)
      }
      const data = await res.json()
      addLog('success', 'api', `\u2713 POST /upload \u2192 ${data.files?.length || 0} 个文件已上传`)
      return data
    } catch (err) {
      if (!err.message?.includes('\u2717')) {
        addLog('error', 'api', `\u2717 POST /upload \u2192 ${err.message}`)
      }
      throw err
    }
  },

  /** 启动转换 */
  startConversion: (data) => {
    addLog('info', 'api', `\u2192 POST /convert (${data.source_fmt} \u2192 ${data.target_fmt}, ${data.files?.length || 0} 文件)`)
    return request('/convert', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  /** 查询任务状态 */
  getTask: (taskId) => request(`/task/${taskId}`),

  /** 取消任务 */
  cancelTask: (taskId) =>
    request(`/task/${taskId}`, { method: 'DELETE' }),

  /** 列出所有任务 */
  listTasks: () => request('/tasks'),

  /** 下载单个文件 */
  getDownloadUrl: (taskId, filename) =>
    `${BASE}/download/${taskId}/${encodeURIComponent(filename)}`,

  /** 打包下载 */
  downloadZip: (taskId) => `${BASE}/download-zip/${taskId}`,
}
