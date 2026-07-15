import React, { useState, useEffect, useCallback, useRef, Suspense } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Toaster, toast } from 'react-hot-toast'
import { api } from './api'
import { addLog } from './logStore'
import Navbar from './components/Navbar'
import TabNav from './components/TabNav'
import FormatSelector from './components/FormatSelector'
import DropZone from './components/DropZone'
import FileList from './components/FileList'
import ProgressPanel from './components/ProgressPanel'
import DownloadPanel from './components/DownloadPanel'
import LogPanel from './components/LogPanel'
import GlobalLogPanel from './components/GlobalLogPanel'

const InteractivePet = React.lazy(() => import('./components/InteractivePet'))

// Silent error boundary — catches canvas/3D errors without crashing the page
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }
  static getDerivedStateFromError() {
    return { hasError: true }
  }
  componentDidCatch(error, info) {
    console.error('[InteractivePet ErrorBoundary]', error, info)
  }
  render() {
    if (this.state.hasError) return null
    return this.props.children
  }
}

const PAGE_HOME = 'home'
const PAGE_CONVERT = 'convert'

const CATEGORY_ACCENT = {
  document: '#818cf8',
  image: '#a78bfa',
  audio: '#22d3ee',
  video: '#f472b6',
  data: '#fbbf24',
}

export default function App() {
  const [formats, setFormats] = useState(null)
  const [activeCategory, setActiveCategory] = useState('document')
  const [page, setPage] = useState(PAGE_HOME)
  const [sourceFmt, setSourceFmt] = useState('')
  const [targetFmt, setTargetFmt] = useState('')
  const [files, setFiles] = useState([])
  const [taskId, setTaskId] = useState(null)
  const [taskStatus, setTaskStatus] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const pollRef = useRef(null)
  const lastLogCount = useRef(0)

  useEffect(() => {
    api.getFormats()
      .then((data) => {
        addLog('success', 'system', `格式列表加载完成 — ${Object.keys(data.categories || {}).length} 个类别`)
        setFormats(data)
      })
      .catch(() => toast.error('无法获取格式列表'))
  }, [])

  useEffect(() => {
    if (formats) {
      const cat = formats.categories[activeCategory]
      if (cat) {
        const inputs = cat.input_formats || []
        const outputs = cat.output_formats || []
        setSourceFmt(inputs[0] || '')
        setTargetFmt(outputs.length > 1 ? outputs[1] : outputs[0] || '')
      }
    }
  }, [activeCategory, formats])

  const startPolling = useCallback((id) => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const status = await api.getTask(id)
        setTaskStatus(status)
        // Emit new backend logs to global log panel
        if (status.logs && status.logs.length > lastLogCount.current) {
          const newLogs = status.logs.slice(lastLogCount.current)
          newLogs.forEach((msg) => addLog('info', 'backend', msg))
          lastLogCount.current = status.logs.length
        }
        if (['done', 'failed', 'cancelled'].includes(status.status)) {
          clearInterval(pollRef.current)
          pollRef.current = null
          if (status.status === 'done') {
            addLog('success', 'backend', `任务完成 — 成功 ${status.total - status.failed}/${status.total}`)
            toast.success(`转换完成！成功 ${status.total - status.failed}/${status.total} 个文件`)
          } else if (status.status === 'failed') {
            addLog('error', 'backend', `任务失败 — ${status.failed}/${status.total} 个文件失败`)
          } else {
            addLog('warn', 'backend', '任务已取消')
          }
        }
      } catch {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }, 600)
  }, [])

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const handleFilesAdded = useCallback((newFiles) => {
    setFiles((prev) => [...prev, ...newFiles])
    setPage(PAGE_CONVERT)
  }, [])

  const handleRemoveFile = useCallback((id) => {
    setFiles((prev) => prev.filter((f) => f.id !== id))
  }, [])

  const handleClearFiles = useCallback(() => {
    setFiles([])
    setPage(PAGE_HOME)
  }, [])

  const handleStartConvert = useCallback(async () => {
    if (files.length === 0) { toast.error('请先添加文件'); return }
    if (!sourceFmt || !targetFmt) { toast.error('请选择源格式和目标格式'); return }
    if (sourceFmt === targetFmt) { toast.error('源格式和目标格式不能相同'); return }

    try {
      lastLogCount.current = 0
      setIsUploading(true)
      addLog('info', 'system', `开始转换 — ${sourceFmt} \u2192 ${targetFmt}, ${files.length} 个文件`)
      const uploadResult = await api.uploadFiles(files.map((f) => f.file))
      const tempPaths = uploadResult.files.map((f) => f.temp_path)
      const originalNames = uploadResult.files.map((f) => f.original_name)

      const result = await api.startConversion({
        files: tempPaths,
        source_fmt: sourceFmt,
        target_fmt: targetFmt,
        original_names: originalNames,
      })

      setIsUploading(false)
      setTaskId(result.task_id)
      startPolling(result.task_id)
    } catch (err) {
      setIsUploading(false)
      toast.error(`启动转换失败: ${err.message}`)
    }
  }, [files, sourceFmt, targetFmt, startPolling])

  const handleCancel = useCallback(async () => {
    if (taskId) {
      await api.cancelTask(taskId)
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
      // Fetch updated status so UI reflects cancelled state immediately
      try {
        const status = await api.getTask(taskId)
        setTaskStatus(status)
        addLog('warn', 'system', '任务已取消')
      } catch { /* ignore */ }
    }
  }, [taskId])

  const handleNewTask = useCallback(() => {
    setFiles([])
    setTaskId(null)
    setTaskStatus(null)
    setPage(PAGE_HOME)
  }, [])

  const isConverting = taskStatus && ['pending', 'running'].includes(taskStatus.status)
  const isDone = taskStatus && ['done', 'failed', 'cancelled'].includes(taskStatus.status)
  const categoryData = formats?.categories?.[activeCategory]

  return (
    <div className="min-h-screen bg-mesh relative">
      <Toaster
        position="top-center"
        toastOptions={{
          style: {
            background: '#161a25',
            color: '#e8ecf2',
            border: '1px solid #23273a',
            borderRadius: '12px',
            fontSize: '14px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
          },
        }}
      />

      <Navbar />

      <main className="max-w-5xl mx-auto px-4 sm:px-6 pt-24 pb-32">
        <AnimatePresence mode="wait">
          <motion.div
            key={page}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            {/* Hero */}
            {page === PAGE_HOME && (
              <div className="text-center mb-12">
                <motion.h1
                  className="text-4xl sm:text-5xl font-bold mb-4 gradient-text"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                >
                  Format Converter
                </motion.h1>
                <motion.p
                  className="text-text-secondary text-lg max-w-2xl mx-auto leading-relaxed"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                >
                  万能格式转换工具 — 支持文档、图片、音频、视频、数据等
                  多种格式之间的快速互转
                </motion.p>
                <motion.div
                  className="mt-8 flex justify-center gap-3 flex-wrap"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  {formats && Object.entries(formats.categories).map(([key, cat]) => (
                    <span
                      key={key}
                      className="px-3 py-1.5 rounded-full text-xs font-medium text-text-secondary"
                      style={{
                        background: `${CATEGORY_ACCENT[key] || '#818cf8'}10`,
                        border: `1px solid ${CATEGORY_ACCENT[key] || '#818cf8'}20`,
                      }}
                    >
                      {cat.icon} {cat.label} {cat.input_formats?.length || 0} 种格式
                    </span>
                  ))}
                </motion.div>
              </div>
            )}

            {/* Tab nav */}
            <TabNav
              categories={formats?.categories}
              active={activeCategory}
              onChange={setActiveCategory}
              disabled={isConverting}
            />

            {/* Format selector */}
            <FormatSelector
              category={categoryData}
              sourceFmt={sourceFmt}
              targetFmt={targetFmt}
              onSourceChange={setSourceFmt}
              onTargetChange={setTargetFmt}
              disabled={isConverting || isDone || isUploading}
            />

            {/* Drop zone */}
            {!isDone && (
              <DropZone
                onFilesAdded={handleFilesAdded}
                disabled={isConverting || isUploading}
              />
            )}

            {/* File list */}
            <FileList
              files={files}
              onRemove={handleRemoveFile}
              onClear={handleClearFiles}
              disabled={isConverting || isUploading}
              results={taskStatus?.results}
            />

            {/* Convert button */}
            {!isDone && files.length > 0 && !isConverting && !isUploading && (
              <motion.div
                className="flex justify-center mt-6"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <button
                  className="btn-primary flex items-center gap-2 text-base px-10 py-3.5 rounded-xl"
                  onClick={handleStartConvert}
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  开始转换 {files.length} 个文件
                </button>
              </motion.div>
            )}

            {/* Upload progress */}
            {isUploading && (
              <motion.div
                className="glass p-6 mb-6"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-6 h-6 border-2 border-accent-blue/30 border-t-accent-blue rounded-full animate-spin" />
                  <div>
                    <h3 className="text-sm font-semibold text-text-primary">上传文件中...</h3>
                    <p className="text-xs text-text-muted mt-0.5">正在上传 {files.length} 个文件到服务器</p>
                  </div>
                </div>
                {/* Indeterminate progress bar */}
                <div className="relative h-2.5 bg-surface-100 rounded-full overflow-hidden">
                  <motion.div
                    className="absolute inset-y-0 progress-gradient rounded-full"
                    style={{ width: '40%' }}
                    animate={{ x: ['-100%', '250%'] }}
                    transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
                  />
                </div>
              </motion.div>
            )}

            {/* Progress */}
            {isConverting && (
              <ProgressPanel
                task={taskStatus}
                onCancel={handleCancel}
              />
            )}

            {/* Logs */}
            {isConverting && taskStatus?.logs?.length > 0 && (
              <LogPanel logs={taskStatus.logs} />
            )}

            {/* Download results */}
            {isDone && (
              <DownloadPanel
                task={taskStatus}
                taskId={taskId}
                onNewTask={handleNewTask}
              />
            )}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Interactive Pet — lazy-loaded physics pet */}
      <Suspense fallback={null}>
        <ErrorBoundary silent>
          <InteractivePet />
        </ErrorBoundary>
      </Suspense>

      {/* Global log panel — monitors all conversion backend output */}
      <GlobalLogPanel />

      {/* Footer */}
      <footer className="text-center py-8 text-text-muted text-sm">
        <p>Format Converter v2.0 — Built with React + FastAPI</p>
      </footer>
    </div>
  )
}
