import { motion } from 'framer-motion'

const ICON_MAP = {
  document: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  image: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  ),
  audio: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
    </svg>
  ),
  video: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
  ),
  data: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
    </svg>
  ),
}

const ACCENT_MAP = {
  document: 'text-accent-blue',
  image: 'text-accent-purple',
  audio: 'text-accent-cyan',
  video: 'text-accent-pink',
  data: 'text-accent-amber',
}

export default function TabNav({ categories, active, onChange, disabled }) {
  if (!categories) return null

  return (
    <motion.div
      className="flex gap-2 mb-6 overflow-x-auto pb-1"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.2 }}
    >
      {Object.entries(categories).map(([key, cat]) => (
        <button
          key={key}
          onClick={() => !disabled && onChange(key)}
          disabled={disabled}
          className={`tab-item flex items-center gap-2 ${active === key ? 'active' : ''} ${
            disabled ? 'opacity-40 cursor-not-allowed' : ''
          }`}
        >
          <span className={active === key ? ACCENT_MAP[key] || 'text-accent-blue' : 'text-text-muted'}>
            {ICON_MAP[key]}
          </span>
          <span>{cat.label}</span>
          <span className="text-[10px] opacity-40 ml-0.5 tabular-nums">
            {cat.input_formats?.length || 0}
          </span>
        </button>
      ))}
    </motion.div>
  )
}
