import { motion } from 'framer-motion';

/**
 * ImageGrid.jsx — 图片结果网格
 *
 * 展示上传的图片及其抠图结果：
 *   - processing: 处理中动画
 *   - done: 显示结果图 + 下载/修正按钮
 *   - error: 显示错误信息 + 重试按钮
 */

export default function ImageGrid({ files, results, onPromptFix, onDelete, getDownloadUrl, getOriginalUrl }) {
  const getResult = (fileId) => results.find(r => r.file_id === fileId);

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {files.map((file, index) => {
        const result = getResult(file.file_id);
        const isProcessing = result?.status === 'processing';
        const isDone = result?.status === 'done';
        const isError = result?.status === 'error';

        return (
          <motion.div
            key={file.file_id}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.05 }}
            className={`glass-light overflow-hidden ${
              isError ? 'border-red-500/30' :
              isDone ? 'border-accent-green/30' :
              ''
            }`}
          >
            {/* 预览图 */}
            <div className="aspect-square bg-black/20 relative overflow-hidden">
              {!isProcessing && (
                <button
                  onClick={() => onDelete(file.file_id)}
                  className="absolute top-2 right-2 z-10 w-7 h-7 rounded-full bg-black/50 hover:bg-red-500/70 text-white/70 hover:text-white flex items-center justify-center text-sm transition-all"
                  title="删除此图片"
                >
                  ✕
                </button>
              )}
              {isDone ? (
                <img
                  src={getDownloadUrl(result.result_id)}
                  alt={file.filename}
                  className="w-full h-full object-contain p-2"
                  style={{ background: 'repeating-conic-gradient(#1a1a2e 0% 25%, #252540 0% 50%) 50% / 20px 20px' }}
                />
              ) : isProcessing ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
                      className="text-3xl mb-2"
                    >
                      ✨
                    </motion.div>
                    <p className="text-white/40 text-xs">抠图中...</p>
                  </div>
                </div>
              ) : isError ? (
                <div className="flex items-center justify-center h-full text-center p-3">
                  <div>
                    <div className="text-3xl mb-2">😿</div>
                    <p className="text-red-400/80 text-xs line-clamp-2">{result.error}</p>
                  </div>
                </div>
              ) : (
                <img
                  src={getOriginalUrl(file.file_id)}
                  alt={file.filename}
                  className="w-full h-full object-contain p-2 opacity-80"
                  loading="lazy"
                />
              )}
            </div>

            {/* 底部操作栏 */}
            <div className="p-3">
              <p className="text-xs text-white/60 truncate mb-2" title={file.filename}>
                {file.filename}
              </p>

              <div className="flex gap-1.5">
                {isDone && (
                  <>
                    <a
                      href={getDownloadUrl(result.result_id)}
                      download={`removed_${file.filename.replace(/\.[^.]+$/, '.png')}`}
                      className="flex-1 text-center text-xs py-1.5 rounded-lg bg-accent-green/15 text-accent-green hover:bg-accent-green/25 transition-colors"
                    >
                      💾 下载
                    </a>
                    <button
                      onClick={() => onPromptFix(file.file_id)}
                      className="flex-1 text-center text-xs py-1.5 rounded-lg bg-accent-purple/15 text-accent-purple hover:bg-accent-purple/25 transition-colors"
                    >
                      ✨ 修正
                    </button>
                  </>
                )}
                {isError && (
                  <button
                    onClick={() => onPromptFix(file.file_id)}
                    className="flex-1 text-center text-xs py-1.5 rounded-lg bg-accent-pink/15 text-accent-pink hover:bg-accent-pink/25 transition-colors"
                  >
                    🔄 提示词重试
                  </button>
                )}
                {isProcessing && (
                  <div className="flex-1">
                    <div className="h-1.5 rounded-full shimmer-bg overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-accent-purple to-accent-pink rounded-full"
                        animate={{ width: ['0%', '80%', '80%', '0%'] }}
                        transition={{ repeat: Infinity, duration: 2 }}
                      />
                    </div>
                  </div>
                )}
                {!result && (
                  <span className="text-white/25 text-xs">待处理</span>
                )}
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
