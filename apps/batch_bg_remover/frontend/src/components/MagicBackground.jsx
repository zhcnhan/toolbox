import { useState, useEffect } from 'react';
import { motion, useMotionValue, useSpring } from 'framer-motion';

// ═══════════════════════════════════════════════
// 赛博AI少女 · 妮妮专属 v2
// 赛博网格 + 霓虹光晕 + 全息粒子 + 鼠标尾迹
// ═══════════════════════════════════════════════

const CYBER_COLORS = ['#00fff7', '#ff00aa', '#a855f7', '#38bdf8', '#ffd700'];

// ── 鼠标尾迹（星形粒子，赛博色系） ──────────
function CursorTrail() {
  const [particles, setParticles] = useState([]);

  useEffect(() => {
    const handleMouse = (e) => {
      const newP = {
        id: Date.now() + Math.random(),
        x: e.clientX,
        y: e.clientY,
        color: CYBER_COLORS[Math.floor(Math.random() * CYBER_COLORS.length)],
        size: Math.random() * 12 + 6,
      };
      setParticles((prev) => [...prev.slice(-30), newP]);
    };
    window.addEventListener('mousemove', handleMouse);
    return () => window.removeEventListener('mousemove', handleMouse);
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none z-50">
      {particles.map((p) => (
        <motion.div
          key={p.id}
          className="absolute"
          style={{ left: p.x - 10, top: p.y - 10, width: p.size, height: p.size }}
          initial={{ opacity: 1, scale: 1 }}
          animate={{ opacity: 0, scale: 0, y: -25, rotate: 180 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        >
          {/* 星形 */}
          <svg viewBox="0 0 24 24" fill={p.color}
            style={{ filter: `drop-shadow(0 0 4px ${p.color}) drop-shadow(0 0 8px ${p.color})` }}
          >
            <path d="M12 2l3 8h9l-7 5 3 8-8-5-8 5 3-8-7-5h9z" />
          </svg>
        </motion.div>
      ))}
    </div>
  );
}

// ── 可拖动手办（霞光万道魔法版） ─────────────────
function FloatingFigure({ src, alt, delay = 0, duration = 8, glowColor = '#00fff7' }) {
  const [dragging, setDragging] = useState(false);
  // 多色彩虹辅助色
  const colors = [glowColor, '#ff00aa', '#a855f7', '#ffd700', '#38bdf8', '#4ade80'];
  // 粒子数组
  const [particles, setParticles] = useState([]);

  const handleDragStart = () => {
    setDragging(true);
    // 生成 15 个爆发粒子
    const newP = Array.from({ length: 15 }, (_, i) => ({
      id: Date.now() + i,
      angle: (i / 15) * 360 + Math.random() * 20,
      dist: 40 + Math.random() * 100,
      size: Math.random() * 8 + 4,
      color: colors[Math.floor(Math.random() * colors.length)],
      delay: Math.random() * 0.15,
    }));
    setParticles(newP);
  };

  const handleDragEnd = () => {
    setDragging(false);
    setParticles([]);
  };

  return (
    <>
      {/* 魔法光环叠加 */}
      <motion.div
        className="select-none relative"
        style={{ width: '100%', height: '100%', cursor: 'grab' }}
        drag
        dragMomentum
        dragElastic={0.5}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        whileDrag={{ scale: 1.25, cursor: 'grabbing' }}
        initial={{ opacity: 0, scale: 0.6 }}
        animate={{ opacity: 0.5, scale: 1 }}
        transition={{ opacity: { duration: 1, delay }, scale: { duration: 1, delay } }}
      >
        {/* 第1层：大光晕 */}
        <motion.div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: `radial-gradient(circle, ${glowColor}44 0%, ${glowColor}22 30%, transparent 65%)`,
            borderRadius: '50%',
          }}
          animate={dragging ? {
            scale: [1, 2.2, 1.8],
            opacity: [0.3, 0.8, 0.4],
          } : { scale: 1, opacity: 0 }}
          transition={{ duration: 0.8, repeat: Infinity, ease: 'easeInOut' }}
        />

        {/* 第2层：旋转彩虹光环 */}
        <motion.div
          className="absolute inset-0 pointer-events-none"
          style={{
            borderRadius: '50%',
            background: `conic-gradient(from 0deg, ${colors.join(', ')})`,
            opacity: 0,
            filter: 'blur(8px)',
          }}
          animate={dragging ? { opacity: 0.6, rotate: 360 } : { opacity: 0, rotate: 0 }}
          transition={dragging ? { rotate: { duration: 1.5, repeat: Infinity, ease: 'linear' }, opacity: { duration: 0.3 } } : { duration: 0.3 }}
        />

        {/* 第3层：旋转反光环 */}
        <motion.div
          className="absolute inset-[-20%] pointer-events-none"
          style={{
            borderRadius: '50%',
            border: `2px solid ${glowColor}`,
            opacity: 0,
            filter: `blur(2px) drop-shadow(0 0 8px ${glowColor})`,
          }}
          animate={dragging ? {
            opacity: [0, 0.8, 0],
            scale: [1, 1.4, 1.8],
            rotate: [-180, 0],
          } : { opacity: 0, scale: 1 }}
          transition={{ duration: 1.2, repeat: Infinity, ease: 'easeOut' }}
        />

        {/* 第4层：小旋转光环 */}
        <motion.div
          className="absolute inset-[-10%] pointer-events-none"
          style={{
            borderRadius: '50%',
            border: `1px dashed ${colors[1]}`,
            opacity: 0,
          }}
          animate={dragging ? { opacity: 0.7, rotate: -360, scale: [1, 1.3, 1] } : { opacity: 0, rotate: 0 }}
          transition={dragging ? { rotate: { duration: 2, repeat: Infinity, ease: 'linear' }, opacity: { duration: 0.3 } } : { duration: 0.3 }}
        />

        {/* 爆发粒子 */}
        {particles.map((p) => (
          <motion.div
            key={p.id}
            className="absolute pointer-events-none"
            style={{
              width: p.size, height: p.size,
              background: p.color,
              borderRadius: '50%',
              top: '50%', left: '50%',
              boxShadow: `0 0 ${p.size * 3}px ${p.color}, 0 0 ${p.size * 6}px ${p.color}66`,
            }}
            initial={{ x: 0, y: 0, opacity: 1, scale: 0 }}
            animate={{
              x: Math.cos(p.angle * Math.PI / 180) * p.dist,
              y: Math.sin(p.angle * Math.PI / 180) * p.dist,
              opacity: [0.8, 0.3, 0],
              scale: [0.5, 1.2, 0],
            }}
            transition={{ duration: 0.8, delay: p.delay, ease: 'easeOut' }}
          />
        ))}

        {/* 本体 */}
        <motion.img
          src={src} alt={alt}
          className="w-full h-full object-contain pointer-events-none relative"
          style={{
            filter: dragging
              ? `brightness(1.4) drop-shadow(0 0 20px ${glowColor}88) drop-shadow(0 0 40px ${glowColor}44)`
              : `drop-shadow(0 0 15px ${glowColor}44)`,
            transition: 'filter 0.3s',
          }}
          animate={{ y: [-6, 6, -6], rotate: [-1, 2, -1] }}
          transition={{
            y: { duration, repeat: Infinity, ease: 'easeInOut', delay },
            rotate: { duration: duration * 1.3, repeat: Infinity, ease: 'easeInOut', delay },
          }}
        />
      </motion.div>
    </>
  );
}

// ── 赛博极光 ─────────────────────────────────
function CyberAurora() {
  return (
    <div className="fixed inset-0 -z-10 pointer-events-none overflow-hidden">
      <motion.div
        className="absolute inset-0"
        style={{
          background: `
            radial-gradient(ellipse at 20% 15%, rgba(0, 255, 247, 0.06) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 10%, rgba(255, 0, 170, 0.05) 0%, transparent 50%),
            radial-gradient(ellipse at 45% 70%, rgba(168, 85, 247, 0.04) 0%, transparent 50%),
            radial-gradient(ellipse at 10% 50%, rgba(255, 215, 0, 0.03) 0%, transparent 40%),
            radial-gradient(ellipse at 90% 60%, rgba(0, 255, 247, 0.04) 0%, transparent 40%)
          `,
        }}
        animate={{ scale: [1, 1.06, 1], rotate: [-0.5, 0.5, -0.5] }}
        transition={{ duration: 16, repeat: Infinity, ease: 'easeInOut' }}
      />
    </div>
  );
}

// ── 霓虹魔法阵 ───────────────────────────────
function NeonCircle() {
  return (
    <div className="pointer-events-none absolute -top-32 left-1/2 -translate-x-1/2 w-[600px] h-[600px] opacity-12">
      <motion.div
        className="absolute inset-0 rounded-full border-2"
        style={{ borderColor: 'rgba(0, 255, 247, 0.25)', borderTopColor: 'rgba(255, 0, 170, 0.5)' }}
        animate={{ rotate: 360 }}
        transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
      />
      <motion.div
        className="absolute inset-6 rounded-full border"
        style={{ borderColor: 'rgba(168, 85, 247, 0.2)', borderBottomColor: 'rgba(0, 255, 247, 0.4)' }}
        animate={{ rotate: -360 }}
        transition={{ duration: 14, repeat: Infinity, ease: 'linear' }}
      />
      <motion.div
        className="absolute inset-16 rounded-full border border-dashed"
        style={{ borderColor: 'rgba(255, 0, 170, 0.15)' }}
        animate={{ rotate: 360 }}
        transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
      />
    </div>
  );
}

// ── 赛博粒子 ─────────────────────────────────
function CyberParticles({ count = 20 }) {
  const particles = Array.from({ length: count }, (_, i) => ({
    id: i,
    top: Math.random() * 100,
    left: Math.random() * 100,
    size: Math.random() * 3 + 1.5,
    color: CYBER_COLORS[Math.floor(Math.random() * CYBER_COLORS.length)],
    delay: Math.random() * 6,
    duration: Math.random() * 8 + 5,
    xDrift: (Math.random() - 0.5) * 40,
  }));

  return (
    <>
      {particles.map((p) => (
        <motion.div
          key={p.id}
          className="absolute rounded-full z-0"
          style={{
            top: `${p.top}%`, left: `${p.left}%`,
            width: p.size, height: p.size,
            background: p.color,
            boxShadow: `0 0 ${p.size * 4}px ${p.color}, 0 0 ${p.size * 8}px ${p.color}44`,
          }}
          animate={{
            y: [0, -40, 0],
            x: [0, p.xDrift, 0],
            opacity: [0.05, 0.5, 0.05],
            scale: [0.3, 1, 0.3],
          }}
          transition={{
            duration: p.duration, repeat: Infinity, ease: 'easeInOut', delay: p.delay,
          }}
        />
      ))}
    </>
  );
}

// ── 数字雨（极简版） ────────────────────────
function DigitalRain() {
  const [drops] = useState(() =>
    Array.from({ length: 5 }, (_, i) => ({
      id: i,
      left: 5 + Math.random() * 90,
      chars: '0101001101001010011'.split(''),
      delay: Math.random() * 8,
      speed: 18 + Math.random() * 12,
    }))
  );

  return (
    <div className="fixed inset-0 -z-8 pointer-events-none overflow-hidden opacity-[0.03]">
      {drops.map((drop) => (
        <motion.div
          key={drop.id}
          className="absolute text-[10px] font-mono leading-tight"
          style={{ left: `${drop.left}%`, color: '#00fff7' }}
          initial={{ top: '-20%' }}
          animate={{ top: '120%' }}
          transition={{ duration: drop.speed, repeat: Infinity, delay: drop.delay, ease: 'linear' }}
        >
          {drop.chars.map((c, j) => (
            <div key={j} style={{ opacity: 1 - j * 0.1 }}>{c}</div>
          ))}
        </motion.div>
      ))}
    </div>
  );
}

// ── 主导出 ────────────────────────────────────
export default function MagicBackground() {
  return (
    <>
      <CyberAurora />
      <DigitalRain />
      {/* 非交互元素（魔法阵、粒子）- 不可点击 */}
      <div className="fixed inset-0 -z-9 overflow-hidden pointer-events-none">
        <NeonCircle />
        <CyberParticles />
      </div>
      {/* 手办 - 可点击可拖动 */}
      <div style={{ position: 'fixed', inset: 0, zIndex: 1, pointerEvents: 'none' }}>
        <div style={{ position: 'absolute', left: '3%', top: '15%', width: 176, height: 320, pointerEvents: 'auto' }}>
          <FloatingFigure src="/anni/figure1.png" alt="手办" glowColor="#00fff7" delay={0.2} duration={7} />
        </div>
        <div style={{ position: 'absolute', right: '4%', top: '22%', width: 208, height: 360, pointerEvents: 'auto' }}>
          <FloatingFigure src="/anni/figure2.png" alt="手办" glowColor="#ff00aa" delay={0.6} duration={9} />
        </div>
        <div style={{ position: 'absolute', left: '7%', bottom: '10%', width: 144, height: 288, pointerEvents: 'auto' }}>
          <FloatingFigure src="/anni/figure3.png" alt="手办" glowColor="#a855f7" delay={1.0} duration={8} />
        </div>
      </div>
      <CursorTrail />
    </>
  );
}

// ── 妮妮头像（赛博光环） ────────────────────
export function AnnieAvatar({ size = 64 }) {
  return (
    <motion.div
      className="relative inline-block cursor-pointer"
      style={{ width: size, height: size }}
      whileHover={{ scale: 1.15 }}
      transition={{ type: 'spring', stiffness: 400, damping: 10 }}
    >
      {/* 霓虹光环 */}
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{
          background: 'conic-gradient(from 0deg, #00fff7, #ff00aa, #a855f7, #00fff7)',
          padding: 2,
        }}
        animate={{ rotate: 360 }}
        transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
      >
        <div className="w-full h-full rounded-full" style={{ background: '#080012' }} />
      </motion.div>

      {/* 呼吸光晕 */}
      <motion.div
        className="absolute -inset-3 rounded-full"
        style={{ background: 'radial-gradient(circle, rgba(0,255,247,0.3) 0%, transparent 70%)' }}
        animate={{ scale: [1, 1.4, 1], opacity: [0.15, 0.4, 0.15] }}
        transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
      />

      <img
        src="/anni/anni.png" alt="妮妮"
        className="absolute inset-1 rounded-full object-cover"
        style={{ width: 'calc(100% - 8px)', height: 'calc(100% - 8px)' }}
      />

      <motion.div className="absolute -top-1 -right-1 text-sm"
        animate={{ opacity: [0.2, 1, 0.2], scale: [0.6, 1.3, 0.6], rotate: [0, 180, 360] }}
        transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
      >✨</motion.div>
    </motion.div>
  );
}
