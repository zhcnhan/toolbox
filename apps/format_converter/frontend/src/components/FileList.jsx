import { motion, AnimatePresence } from 'framer-motion'

function formatSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const FILE_ICON = (
  <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
)

export default function FileList({ files, onRemove, onClear, disabled, results }) {
  if (files.length === 0) return null

  const resultMap = {}
  if (results) {
    results.forEach((r) => {
      resultMap[r.original] = r
    })
  }

  return (
    <motion.div
      className="glass p-5 mb-6"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.35 }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
          <svg className="w-4 h-4 text-accent-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
          </svg>
          文件列表 ({files.length})
        </h3>
        {!disabled && (
          <button
            onClick={onClear}
            className="text-xs text-text-muted hover:text-red-400 transition-colors px-3 py-1.5 rounded-lg hover:bg-surface-100"
          >
            清空全部
          </button>
        )}
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto">
        <AnimatePresence>
          {files.map((f, i) => {
            const result = resultMap[f.originalName || f.file?.name]
            return (
              <motion.div
                key={f.id}
                className={`file-item ${result ? (result.success ? 'border-accent-green/20' : 'border-red-500/20') : ''}`}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ delay: i * 0.03 }}
              >
                <div className="w-8 h-8 rounded-lg bg-surface-100 flex items-center justify-center text-text-muted shrink-0">
                  {FILE_ICON}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text-primary truncate">
                    {f.originalName || f.file?.name || '未知文件'}
                  </p>
                  <p className="text-xs text-text-muted">
                    {formatSize(f.size || f.file?.size)}
                  </p>
                </div>
                {result ? (
                  <span
                    className={`text-xs px-2 py-1 rounded-md font-medium shrink-0 ${
                      result.success
                        ? 'bg-accent-green/10 text-accent-green'
                        : 'bg-red-500/10 text-red-400'
                    }`}
                  >
                    {result.success ? '已完成' : '失败'}
                  </span>
                ) : (
                  !disabled && (
                    <button
                      onClick={() => onRemove(f.id)}
                      className="p-1.5 rounded-lg hover:bg-surface-100 text-text-muted hover:text-red-400 transition-colors shrink-0"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  )
                )}
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}
