import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion } from 'framer-motion';

/**
 * DropZone.jsx — 拖放/点击上传区域
 *
 * 可爱风格：大图标 + 引导文案 + 拖放动画
 */

const ACCEPTED = {
  'image/png': ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/webp': ['.webp'],
  'image/bmp': ['.bmp'],
  'image/tiff': ['.tiff', '.tif'],
};

export default function DropZone({ onFilesDrop, disabled }) {
  const [isDragging, setIsDragging] = useState(false);

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      onFilesDrop(acceptedFiles);
    }
  }, [onFilesDrop]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    disabled,
    onDragEnter: () => setIsDragging(true),
    onDragLeave: () => setIsDragging(false),
    onDropAccepted: () => setIsDragging(false),
    onDropRejected: () => setIsDragging(false),
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      {...getRootProps()}
      className={`
        glass p-8 md:p-12 text-center cursor-pointer transition-all duration-300
        ${isDragActive || isDragging ? 'dropzone-active scale-[1.01]' : 'hover:border-white/15'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
      `}
    >
      <input {...getInputProps()} />

      <motion.div
        animate={isDragActive ? { scale: 1.1, y: -5 } : { scale: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        className="text-5xl md:text-6xl mb-4"
      >
        {isDragActive ? '🎉' : '📁'}
      </motion.div>

      <h3 className="text-lg md:text-xl font-bold mb-2">
        {isDragActive ? '松手即可上传！' : '拖放图片到这里'}
      </h3>
      <p className="text-white/40 text-sm">
        或点击选择文件 · 支持 PNG / JPG / WebP / BMP / TIFF
      </p>
      <p className="text-white/25 text-xs mt-2">
        🐾 可以一次选很多张哦~
      </p>
    </motion.div>
  );
}
