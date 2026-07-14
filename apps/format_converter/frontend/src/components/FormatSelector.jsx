import { useState, useRef, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'

const SWAP_ICON = (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
  </svg>
)

const CHEVRON = (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 9l6 6 6-6" />
  </svg>
)

function CustomSelect({ value, options, onChange, disabled, disabledValues = [] }) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef(null)

  const handleClickOutside = useCallback((e) => {
    if (containerRef.current && !containerRef.current.contains(e.target)) {
      setOpen(false)
    }
  }, [])

  useEffect(() => {
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [handleClickOutside])

  const selectedLabel = value?.toUpperCase() || '—'

  return (
    <div className="relative w-full" ref={containerRef}>
      <button
        type="button"
        className="dropdown-btn w-full"
        onClick={() => !disabled && setOpen(!open)}
        disabled={disabled}
      >
        <span className="truncate">{selectedLabel}</span>
        <span className={`chevron shrink-0 ${open ? 'open' : ''}`}>{CHEVRON}</span>
      </button>

      {open && (
        <div className="dropdown-menu">
          {options.map((opt) => {
            const isDisabled = disabledValues.includes(opt)
            const isSelected = opt === value
            return (
              <div
                key={opt}
                className={`dropdown-option ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}`}
                onClick={() => {
                  if (!isDisabled) {
                    onChange(opt)
                    setOpen(false)
                  }
                }}
              >
                {opt.toUpperCase()}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default function FormatSelector({
  category,
  sourceFmt,
  targetFmt,
  onSourceChange,
  onTargetChange,
  disabled,
}) {
  if (!category) return null

  const inputFormats = category?.input_formats || []
  const outputFormats = category?.output_formats || []

  return (
    <motion.div
      className="glass p-5 mb-6"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.25 }}
    >
      <div className="flex items-end gap-4">
        {/* Source */}
        <div className="flex-1 min-w-0">
          <label className="block text-xs text-text-muted mb-2 font-semibold uppercase tracking-widest">
            源格式
          </label>
          <CustomSelect
            value={sourceFmt}
            options={inputFormats}
            onChange={onSourceChange}
            disabled={disabled}
          />
        </div>

        {/* Swap */}
        <button
          onClick={() => {
            if (
              outputFormats.includes(sourceFmt) &&
              inputFormats.includes(targetFmt)
            ) {
              onSourceChange(targetFmt)
              onTargetChange(sourceFmt)
            }
          }}
          disabled={disabled}
          className="p-2.5 rounded-lg hover:bg-surface-200 transition-colors disabled:opacity-30 text-text-muted mb-0.5 shrink-0"
          title="交换格式"
        >
          {SWAP_ICON}
        </button>

        {/* Target */}
        <div className="flex-1 min-w-0">
          <label className="block text-xs text-text-muted mb-2 font-semibold uppercase tracking-widest">
            目标格式
          </label>
          <CustomSelect
            value={targetFmt}
            options={outputFormats}
            onChange={onTargetChange}
            disabled={disabled}
            disabledValues={[sourceFmt]}
          />
        </div>
      </div>
    </motion.div>
  )
}
