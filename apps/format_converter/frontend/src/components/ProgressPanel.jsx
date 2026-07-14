import { motion } from 'framer-motion'

export default function ProgressPanel({ task, onCancel }) {
  if (!task) return null

  const percent = Math.round((task.overall_progress || 0) * 100)
  const isRunning = task.status === 'running'

  return (
    <motion.div
      className="glass p-6 mb-6"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {isRunning && (
            <div className="w-6 h-6 border-2 border-accent-blue/30 border-t-accent-blue rounded-full animate-spin" />
          )}
          <div>
            <h3 className="text-sm font-semibold text-text-primary">
              {isRunning ? '转换中...' : task.status === 'done' ? '转换完成' : '任务已取消'}
            </h3>
            <p className="text-xs text-text-muted mt-0.5">
              {task.completed} / {task.total} 个文件
              {task.failed > 0 && (
                <span className="text-red-400 ml-2">{task.failed} 个失败</span>
              )}
            </p>
          </div>
        </div>

        {isRunning && (
          <button
            onClick={onCancel}
            className="btn-ghost text-sm text-red-400 hover:text-red-300"
          >
            取消
          </button>
        )}
      </div>

      {/* Progress bar */}
      <div className="relative h-2.5 bg-surface-100 rounded-full overflow-hidden">
        <motion.div
          className="absolute inset-y-0 left-0 progress-gradient rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${percent}%` }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
        />
        <div
          className="absolute inset-y-0 left-0 rounded-full blur-sm opacity-40 progress-gradient"
          style={{ width: `${percent}%` }}
        />
      </div>

      <div className="flex justify-between mt-2">
        <span className="text-xs text-text-muted">
          {task.current_file && (
            <span className="truncate block max-w-xs">{task.current_file}</span>
          )}
        </span>
        <span className="text-sm font-semibold gradient-text">{percent}%</span>
      </div>
    </motion.div>
  )
}
