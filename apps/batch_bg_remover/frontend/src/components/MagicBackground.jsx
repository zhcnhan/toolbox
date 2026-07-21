import { motion } from 'framer-motion';

// 浮动手办组件（透明背景立牌）
function FloatingFigure({ src, alt, className, delay = 0, duration = 8, glow = 'pink' }) {
  const glowColor = glow === 'pink'
    ? 'drop-shadow-[0_0_30px_rgba(255,143,171,0.5)] drop-shadow-[0_0_60px_rgba(192,132,252,0.3)]'
    : 'drop-shadow-[0_0_30px_rgba(192,132,252,0.5)] drop-shadow-[0_0_60px_rgba(103,232,249,0.3)]';

  return (
    <motion.div
      className={`pointer-events-none absolute select-none ${className}`}
      style={{ filter: glowColor }}
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{
        opacity: 1,
        scale: 1,
        y: [0, -20, 0],
        rotate: [-2, 2, -2],
      }}
      transition={{
        opacity: { duration: 1.2, delay },
        scale: { duration: 1.2, delay },
        y: { duration, repeat: Infinity, ease: 'easeInOut', delay },
        rotate: { duration: duration * 1.3, repeat: Infinity, ease: 'easeInOut', delay },
      }}
    >
      <img src={src} alt={alt} className="w-full h-full object-contain" />
    </motion.div>
  );
}

// 魔法星点（散落在页面上的小亮点）
function MagicSparkle({ top, left, size = 12, delay = 0, color = '#ffd700' }) {
  return (
    <motion.div
      className="absolute pointer-events-none"
      style={{ top, left, fontSize: size, color }}
      initial={{ opacity: 0, scale: 0 }}
      animate={{
        opacity: [0.2, 1, 0.2],
        scale: [0.6, 1.2, 0.6],
        rotate: [0, 180, 360],
      }}
      transition={{
        duration: 3,
        repeat: Infinity,
        ease: 'easeInOut',
        delay,
      }}
    >
      ✦
    </motion.div>
  );
}

// 旋转魔法阵（顶部装饰）
function MagicCircle() {
  return (
    <div className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 w-[800px] h-[800px] opacity-20">
      <motion.div
        className="absolute inset-0 rounded-full border-2 border-pink-300/40"
        style={{ borderTopColor: 'rgba(192, 132, 252, 0.6)', borderRightColor: 'rgba(103, 232, 249, 0.4)' }}
        animate={{ rotate: 360 }}
        transition={{ duration: 30, repeat: Infinity, ease: 'linear' }}
      />
      <motion.div
        className="absolute inset-12 rounded-full border border-purple-300/30"
        style={{ borderBottomColor: 'rgba(255, 143, 171, 0.5)' }}
        animate={{ rotate: -360 }}
        transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
      />
      <motion.div
        className="absolute inset-24 rounded-full border border-cyan-300/20"
        style={{ borderLeftColor: 'rgba(192, 132, 252, 0.4)' }}
        animate={{ rotate: 360 }}
        transition={{ duration: 15, repeat: Infinity, ease: 'linear' }}
      />
    </div>
  );
}

// 主背景组件
export default function MagicBackground() {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
      <MagicCircle />

      {/* 三个手办漂浮 - 大屏显示，小屏隐藏 */}
      <div className="hidden lg:block">
        <FloatingFigure
          src="/anni/figure1.png"
          alt="安妮的手办"
          className="w-48 h-96 left-[3%] top-[15%]"
          delay={0.2}
          duration={7}
          glow="purple"
        />
        <FloatingFigure
          src="/anni/figure2.png"
          alt="安妮的手办"
          className="w-56 h-96 right-[4%] top-[20%]"
          delay={0.6}
          duration={9}
          glow="pink"
        />
        <FloatingFigure
          src="/anni/figure3.png"
          alt="安妮的手办"
          className="w-40 h-80 left-[7%] bottom-[8%]"
          delay={1.0}
          duration={8}
          glow="cyan"
        />
      </div>

      {/* 魔法星点 */}
      <MagicSparkle top="8%" left="20%" size={16} delay={0} color="#ff8fab" />
      <MagicSparkle top="15%" left="75%" size={20} delay={0.5} color="#c084fc" />
      <MagicSparkle top="30%" left="50%" size={14} delay={1.0} color="#67e8f9" />
      <MagicSparkle top="50%" left="15%" size={18} delay={1.5} color="#ff8fab" />
      <MagicSparkle top="65%" left="85%" size={16} delay={2.0} color="#c084fc" />
      <MagicSparkle top="80%" left="35%" size={20} delay={2.5} color="#ffd700" />
      <MagicSparkle top="40%" left="90%" size={14} delay={0.8} color="#67e8f9" />
      <MagicSparkle top="90%" left="70%" size={16} delay={1.2} color="#ff8fab" />
    </div>
  );
}

// 妮妮的头像组件 - 用于页面顶部
export function AnnieAvatar({ size = 64 }) {
  return (
    <div className="relative inline-block" style={{ width: size, height: size }}>
      {/* 旋转魔法环 */}
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{
          background: 'conic-gradient(from 0deg, #ff8fab, #c084fc, #67e8f9, #ff8fab)',
          padding: 2,
        }}
        animate={{ rotate: 360 }}
        transition={{ duration: 6, repeat: Infinity, ease: 'linear' }}
      >
        <div className="w-full h-full rounded-full bg-bg" />
      </motion.div>
      {/* 头像本身 */}
      <img
        src="/anni/anni.png"
        alt="妮妮"
        className="absolute inset-1 rounded-full object-cover w-[calc(100%-8px)] h-[calc(100%-8px)]"
        style={{
          boxShadow: '0 0 20px rgba(255, 143, 171, 0.5), 0 0 40px rgba(192, 132, 252, 0.3)',
        }}
      />
      {/* 闪烁星点 */}
      <motion.div
        className="absolute -top-1 -right-1 text-base"
        animate={{
          opacity: [0.3, 1, 0.3],
          scale: [0.8, 1.2, 0.8],
          rotate: [0, 180, 360],
        }}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
      >
        ✨
      </motion.div>
    </div>
  );
}
