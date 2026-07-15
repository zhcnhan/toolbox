import React, { useState, useEffect, useRef } from 'react'
import { subscribe, clearLogs } from '../logStore'

const LEVEL_COLORS = {
  info: '#93c5fd',
  success: '#86efac',
  error: '#fca5a5',
  warn: '#fcd34d',
}

const SOURCE_TAGS = {
  api: 'API',
  backend: '后端',
  system: '系统',
}

export default function GlobalLogPanel() {
  const [logs, setLogs] = useState([])
  const [collapsed, setCollapsed] = useState(true)
  const scrollRef = useRef(null)

  useEffect(() => subscribe(setLogs), [])

  useEffect(() => {
    if (scrollRef.current && !collapsed) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs, collapsed])

  const errorCount = logs.filter((l) => l.level === 'error').length

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        width: 440,
        maxHeight: collapsed ? 34 : 300,
        background: 'rgba(8, 12, 22, 0.93)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderBottom: 'none',
        borderLeft: 'none',
        borderRadius: '0 12px 0 0',
        zIndex: 9999,
        fontFamily: '"Cascadia Code", "Fira Code", "Consolas", monospace',
        fontSize: '11px',
        transition: 'max-height 0.25s ease',
        display: 'flex',
        flexDirection: 'column',
        pointerEvents: 'auto',
      }}
    >
      {/* Header bar */}
      <div
        onClick={() => setCollapsed(!collapsed)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '7px 12px',
          cursor: 'pointer',
          borderBottom: collapsed ? 'none' : '1px solid rgba(255,255,255,0.06)',
          color: '#94a3b8',
          fontWeight: 600,
          fontSize: '11px',
          userSelect: 'none',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: logs.length > 0 ? '#22c55e' : '#64748b',
              boxShadow: logs.length > 0 ? '0 0 6px #22c55e' : 'none',
            }}
          />
          转换日志监控
          <span style={{ color: '#475569' }}>({logs.length})</span>
          {errorCount > 0 && (
            <span style={{ color: '#fca5a5', marginLeft: 4 }}>
              {errorCount} 错误
            </span>
          )}
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {logs.length > 0 && !collapsed && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                clearLogs()
              }}
              style={{
                background: 'none',
                border: '1px solid rgba(255,255,255,0.1)',
                color: '#64748b',
                cursor: 'pointer',
                fontSize: '10px',
                padding: '1px 6px',
                borderRadius: 4,
              }}
            >
              清空
            </button>
          )}
          <span style={{ color: '#475569' }}>{collapsed ? '▲' : '▼'}</span>
        </span>
      </div>

      {/* Log entries */}
      {!collapsed && (
        <div
          ref={scrollRef}
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '6px 12px 8px',
            maxHeight: 266,
          }}
        >
          {logs.length === 0 ? (
            <div style={{ color: '#475569', padding: '12px 0', textAlign: 'center' }}>
              暂无日志 — 开始转换文件后，后台输出将实时显示在此处
            </div>
          ) : (
            logs.map((log) => (
              <div
                key={log.id}
                style={{
                  display: 'flex',
                  gap: '6px',
                  padding: '1.5px 0',
                  lineHeight: 1.55,
                  wordBreak: 'break-word',
                }}
              >
                <span style={{ color: '#3b4252', flexShrink: 0 }}>
                  {log.timestamp}
                </span>
                <span
                  style={{
                    color: '#475569',
                    flexShrink: 0,
                    width: 36,
                    textAlign: 'center',
                    background: 'rgba(255,255,255,0.03)',
                    borderRadius: 3,
                  }}
                >
                  {SOURCE_TAGS[log.source] || log.source}
                </span>
                <span
                  style={{
                    color: LEVEL_COLORS[log.level] || '#94a3b8',
                    flex: 1,
                  }}
                >
                  {log.message}
                </span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
