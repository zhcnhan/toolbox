import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'

export default function LogPanel({ logs }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  if (!logs || logs.length === 0) return null

  return (
    <motion.div
      className="glass p-5 mb-6"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
        <svg className="w-4 h-4 text-accent-purple" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
        </svg>
        转换日志
      </h3>
      <div className="bg-surface-0 rounded-xl p-4 max-h-48 overflow-y-auto border border-surface-200">
        {logs.map((line, i) => {
          let cls = ''
          if (line.includes('\u2713') || line.includes('完成')) cls = 'success'
          else if (line.includes('\u2717') || line.includes('失败')) cls = 'error'
          else if (line.includes('转换中')) cls = 'info'
          return (
            <div key={i} className={`log-line ${cls}`}>
              {line}
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>
    </motion.div>
  )
}
