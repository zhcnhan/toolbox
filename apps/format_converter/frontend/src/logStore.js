// Global log store — pub/sub pattern, no React context needed
const logs = []
const listeners = new Set()
const MAX_LOGS = 300

export function addLog(level, source, message) {
  const entry = {
    id: Date.now() + Math.random(),
    timestamp: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    level,     // 'info' | 'success' | 'error' | 'warn'
    source,    // 'api' | 'backend' | 'system'
    message: String(message),
  }
  logs.push(entry)
  if (logs.length > MAX_LOGS) logs.shift()
  listeners.forEach((fn) => fn([...logs]))
}

export function subscribe(fn) {
  listeners.add(fn)
  fn([...logs])
  return () => listeners.delete(fn)
}

export function clearLogs() {
  logs.length = 0
  listeners.forEach((fn) => fn([]))
}
