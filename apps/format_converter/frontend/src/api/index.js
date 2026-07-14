const BASE = '/api'

async function request(path, options = {}) {
  const url = `${BASE}${path}`
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
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
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || `HTTP ${res.status}`)
    }
    return res.json()
  },

  /** 启动转换 */
  startConversion: (data) =>
    request('/convert', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

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
