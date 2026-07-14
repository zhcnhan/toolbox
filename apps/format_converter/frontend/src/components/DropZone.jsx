import { useCallback, useState } from 'react'
import { motion } from 'framer-motion'

let fileIdCounter = 0

export default function DropZone({ onFilesAdded, disabled }) {
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    if (!disabled) setIsDragging(true)
  }, [disabled])

  const handleDragLeave = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragging(false)
      if (disabled) return

      const droppedFiles = Array.from(e.dataTransfer.files)
      if (droppedFiles.length > 0) {
        const wrapped = droppedFiles.map((f) => ({
          id: ++fileIdCounter,
          file: f,
          originalName: f.name,
          size: f.size,
          tempPath: null,
          fmt: null,
        }))
        onFilesAdded(wrapped)
      }
    },
    [disabled, onFilesAdded]
  )

  const handleClick = useCallback(() => {
    if (disabled) return
    const input = document.createElement('input')
    input.type = 'file'
    input.multiple = true
    input.onchange = (e) => {
      const selected = Array.from(e.target.files)
      if (selected.length > 0) {
        const wrapped = selected.map((f) => ({
          id: ++fileIdCounter,
          file: f,
          originalName: f.name,
          size: f.size,
          tempPath: null,
          fmt: null,
        }))
        onFilesAdded(wrapped)
      }
    }
    input.click()
  }, [disabled, onFilesAdded])

  return (
    <motion.div
      className={`drop-zone p-10 mb-6 text-center ${isDragging ? 'drag-active' : ''} ${
        disabled ? 'opacity-30 cursor-not-allowed' : 'cursor-pointer'
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      whileHover={disabled ? {} : { scale: 1.003 }}
    >
      <div className="flex flex-col items-center gap-3">
        <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-300 ${
          isDragging
            ? 'bg-accent-blue/15 text-accent-blue shadow-lg shadow-accent-blue/10'
            : 'bg-surface-100 text-text-muted'
        }`}>
          <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
        </div>
        <div>
          <p className="text-text-primary font-medium text-base">
            {isDragging ? '松开以添加文件' : '拖放文件到此处'}
          </p>
          <p className="text-text-muted text-sm mt-1">
            或点击此处选择文件（支持批量）
          </p>
        </div>
      </div>
    </motion.div>
  )
}
