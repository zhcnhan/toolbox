import { motion } from 'framer-motion'

export default function Navbar() {
  return (
    <motion.nav
      className="fixed top-0 left-0 right-0 z-50 border-b border-surface-200"
      initial={{ y: -80 }}
      animate={{ y: 0 }}
      transition={{ type: 'spring', stiffness: 100, damping: 20 }}
      style={{ background: 'rgba(13,16,23,0.85)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)' }}
    >
      <div className="max-w-5xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center text-lg font-bold text-white shadow-lg shadow-accent-blue/20">
            F
          </div>
          <span className="font-semibold text-lg tracking-tight text-text-primary">
            Format <span className="gradient-text">Converter</span>
          </span>
        </div>

        <div className="flex items-center gap-2 text-text-muted text-sm">
          <a
            href="/api/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-text-secondary transition-colors px-3 py-1.5 rounded-lg hover:bg-surface-100"
          >
            API Docs
          </a>
          <span className="text-surface-300">|</span>
          <span className="px-2 py-1 rounded-md bg-surface-100 text-xs font-mono text-text-secondary">
            v2.0
          </span>
        </div>
      </div>
    </motion.nav>
  )
}
