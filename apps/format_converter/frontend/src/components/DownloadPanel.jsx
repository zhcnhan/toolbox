import { motion } from 'framer-motion'
import { api } from '../api'
import { addLog } from '../logStore'

/** Trigger a file download without opening a new window */
function triggerDownload(url, filename) {
  const a = document.createElement('a')
  a.href = url
  if (filename) a.download = filename
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

export default function DownloadPanel({ task, taskId, onNewTask }) {
  if (!task) return null

  const successResults = (task.results || []).filter((r) => r.success)
  const failedResults = (task.results || []).filter((r) => !r.success)

  const handleDownloadZip = () => {
    addLog('info', 'system', '开始打包下载...')
    triggerDownload(api.downloadZip(taskId))
  }

  const handleDownloadFile = (filename) => {
    triggerDownload(api.getDownloadUrl(taskId, filename), filename)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
    >
      {/* Summary card */}
      <div className="glass p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-text-primary">
            {task.status === 'done' ? '转换完成' : '任务结果'}
          </h3>
          <span className="text-sm text-text-muted">
            {task.completed} 个文件, {task.failed} 个失败
          </span>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-surface-100 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-accent-green">{successResults.length}</div>
            <div className="text-xs text-text-muted mt-1">成功</div>
          </div>
          <div className="bg-surface-100 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-red-400">{failedResults.length}</div>
            <div className="text-xs text-text-muted mt-1">失败</div>
          </div>
          <div className="bg-surface-100 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-text-primary">{task.total || 0}</div>
            <div className="text-xs text-text-muted mt-1">总计</div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3 flex-wrap">
          {successResults.length > 0 && (
            <button
              onClick={handleDownloadZip}
              className="btn-primary flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              打包下载全部结果
            </button>
          )}
          <button
            onClick={onNewTask}
            className="btn-ghost flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            开始新转换
          </button>
        </div>
      </div>

      {/* Result list */}
      {(task.results || []).length > 0 && (
        <div className="glass p-5">
          <h4 className="text-sm font-semibold text-text-primary mb-3">转换结果</h4>
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {task.results.map((r, i) => (
              <div
                key={i}
                className={`result-item ${r.success ? 'success' : 'failed'}`}
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text-primary truncate">{r.original}</p>
                  {r.error && (
                    <p className="text-xs text-red-400 mt-0.5 truncate">{r.error}</p>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {r.success ? (
                    <>
                      <span className="w-2 h-2 rounded-full bg-accent-green" />
                      <button
                        onClick={() => handleDownloadFile(r.output)}
                        className="text-xs text-accent-blue hover:text-accent-purple transition-colors px-2 py-1 rounded-lg hover:bg-surface-100"
                      >
                        下载
                      </button>
                    </>
                  ) : (
                    <span className="w-2 h-2 rounded-full bg-red-500" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  )
}
