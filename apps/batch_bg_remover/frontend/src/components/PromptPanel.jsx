import { useState, useRef } from 'react';
import { motion } from 'framer-motion';

/**
 * PromptPanel.jsx — 提示词修正面板
 *
 * 用户对某张图不满意时，输入文本提示词重新选取主体
 * 如 "左边的猫"、"红色汽车"、"人物"
 */

export default function PromptPanel({ file, onSubmit, onCancel }) {
  const [prompt, setPrompt] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const inputRef = useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim() || submitting) return;
    setSubmitting(true);
    try {
      await onSubmit(prompt.trim());
    } catch (e) {
      console.error('Prompt remove failed:', e);
    } finally {
      setSubmitting(false);
    }
  };

  // 快捷提示词
  const quickPrompts = ['人物', '猫', '狗', '汽车', '产品', '食物', '左边的', '右边的', '最大的'];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
      onClick={onCancel}
    >
      <motion.div
        initial={{ scale: 0.9, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.9, y: 20 }}
        className="glass p-6 w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 mb-4">
          <span className="text-2xl">✨</span>
          <div>
            <h3 className="font-bold">提示词修正</h3>
            <p className="text-white/40 text-xs truncate">{file?.filename}</p>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <label className="text-sm text-white/60 block mb-2">
            描述你想保留的主体：
          </label>
          <input
            ref={inputRef}
            type="text"
            className="input-field mb-3"
            placeholder='例如："左边的猫"、"红色汽车"、"戴帽子的人"'
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            autoFocus
            disabled={submitting}
          />

          {/* 快捷提示词 */}
          <div className="flex flex-wrap gap-1.5 mb-4">
            {quickPrompts.map((qp) => (
              <button
                key={qp}
                type="button"
                className="px-2.5 py-1 text-xs rounded-full bg-white/5 hover:bg-white/10 text-white/60 hover:text-white/80 transition-colors"
                onClick={() => setPrompt(qp)}
                disabled={submitting}
              >
                {qp}
              </button>
            ))}
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              className="btn-primary flex-1 text-sm"
              disabled={!prompt.trim() || submitting}
            >
              {submitting ? '⏳ 处理中...' : '✂️ 重新抠图'}
            </button>
            <button
              type="button"
              className="btn-secondary text-sm"
              onClick={onCancel}
              disabled={submitting}
            >
              取消
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
}
