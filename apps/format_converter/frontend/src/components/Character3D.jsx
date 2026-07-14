import { useRef, useState, useMemo, useEffect, Suspense } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Float, Text, MeshDistortMaterial, useGLTF } from '@react-three/drei'
import { motion, AnimatePresence } from 'framer-motion'
import * as THREE from 'three'

// ============================================================
// 皮肤配置接口 — 预留自定义皮肤替换
// ============================================================
/**
 * @typedef {Object} SkinConfig
 * @property {string} id          - 皮肤唯一标识
 * @property {string} name        - 皮肤名称
 * @property {string} head        - 头部颜色
 * @property {string} body        - 身体颜色
 * @property {string} limbs       - 四肢颜色
 * @property {string} eyes        - 眼睛颜色
 * @property {string} accent      - 装饰色
 * @property {string} emissive    - 发光色（眼睛/装饰）
 */

/** 默认皮肤：赛博蓝 */
const DEFAULT_SKIN = {
  id: 'cyber-blue',
  name: '赛博蓝',
  head: '#6366f1',
  body: '#4f46e5',
  limbs: '#4338ca',
  eyes: '#ffffff',
  accent: '#06b6d4',
  emissive: '#6366f1',
}

/** 皮肤注册表 — 在此添加新皮肤 */
export const SKIN_REGISTRY = {
  'cyber-blue': DEFAULT_SKIN,
  'neon-pink': {
    id: 'neon-pink',
    name: '霓虹粉',
    head: '#ec4899',
    body: '#db2777',
    limbs: '#be185d',
    eyes: '#ffffff',
    accent: '#f472b6',
    emissive: '#ec4899',
  },
  'forest-green': {
    id: 'forest-green',
    name: '森林绿',
    head: '#10b981',
    body: '#059669',
    limbs: '#047857',
    eyes: '#ffffff',
    accent: '#34d399',
    emissive: '#10b981',
  },
  'sunset-orange': {
    id: 'sunset-orange',
    name: '日落橙',
    head: '#f97316',
    body: '#ea580c',
    limbs: '#c2410c',
    eyes: '#ffffff',
    accent: '#fb923c',
    emissive: '#f97316',
  },
  'ghost-white': {
    id: 'ghost-white',
    name: '幽灵白',
    head: '#e2e8f0',
    body: '#cbd5e1',
    limbs: '#94a3b8',
    eyes: '#0f172a',
    accent: '#64748b',
    emissive: '#e2e8f0',
  },
  'golden': {
    id: 'golden',
    name: '璀璨金',
    head: '#fbbf24',
    body: '#f59e0b',
    limbs: '#d97706',
    eyes: '#ffffff',
    accent: '#fcd34d',
    emissive: '#fbbf24',
  },
}

// ============================================================
// 3D 角色模型（占位形象 — 低多边形小人偶）
// ============================================================
function CharacterModel({ skin = DEFAULT_SKIN, isWaving = false, onClick }) {
  const groupRef = useRef()
  const headRef = useRef()
  const leftArmRef = useRef()
  const rightArmRef = useRef()
  const bodyRef = useRef()

  // Float animation
  useFrame((state) => {
    const t = state.clock.getElapsedTime()

    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(t * 0.5) * 0.15
      groupRef.current.position.y = Math.sin(t * 1.5) * 0.15
    }

    if (headRef.current) {
      headRef.current.rotation.y = Math.sin(t * 0.8) * 0.2
      headRef.current.rotation.x = Math.sin(t * 0.6) * 0.1
    }

    // Arm wave
    if (isWaving && rightArmRef.current) {
      rightArmRef.current.rotation.z = Math.sin(t * 8) * 0.6 - 0.3
      rightArmRef.current.rotation.x = Math.sin(t * 4) * 0.2
    } else if (rightArmRef.current) {
      rightArmRef.current.rotation.z = Math.sin(t * 1.2) * 0.08 - 0.15
    }

    if (leftArmRef.current) {
      leftArmRef.current.rotation.z = Math.sin(t * 1.2 + Math.PI) * 0.08 + 0.15
    }

    if (bodyRef.current) {
      bodyRef.current.rotation.y = Math.sin(t * 0.4) * 0.05
    }
  })

  const bodyColor = new THREE.Color(skin.body)
  const headColor = new THREE.Color(skin.head)
  const limbsColor = new THREE.Color(skin.limbs)
  const accentColor = new THREE.Color(skin.accent)
  const emissiveColor = new THREE.Color(skin.emissive)

  return (
    <group ref={groupRef} onClick={(e) => { e.stopPropagation(); onClick?.() }}>
      {/* Body */}
      <mesh ref={bodyRef} position={[0, 0.3, 0]} castShadow>
        <capsuleGeometry args={[0.3, 0.5, 8, 16]} />
        <meshStandardMaterial color={bodyColor} roughness={0.3} metalness={0.1} />
      </mesh>

      {/* Belly accent ring */}
      <mesh position={[0, 0.45, 0.29]} rotation={[0, 0, 0]}>
        <torusGeometry args={[0.22, 0.03, 8, 16]} />
        <meshStandardMaterial color={accentColor} roughness={0.2} metalness={0.4} emissive={emissiveColor} emissiveIntensity={0.3} />
      </mesh>

      {/* Head */}
      <group ref={headRef} position={[0, 0.95, 0]}>
        <mesh castShadow>
          <sphereGeometry args={[0.28, 32, 32]} />
          <meshStandardMaterial color={headColor} roughness={0.25} metalness={0.1} />
        </mesh>

        {/* Eyes */}
        <mesh position={[-0.1, 0.05, 0.25]} scale={[0.06, 0.08, 0.02]}>
          <sphereGeometry args={[1, 16, 16]} />
          <meshStandardMaterial color={skin.eyes} roughness={0} metalness={0} emissive={skin.eyes} emissiveIntensity={0.8} />
        </mesh>
        <mesh position={[0.1, 0.05, 0.25]} scale={[0.06, 0.08, 0.02]}>
          <sphereGeometry args={[1, 16, 16]} />
          <meshStandardMaterial color={skin.eyes} roughness={0} metalness={0} emissive={skin.eyes} emissiveIntensity={0.8} />
        </mesh>

        {/* Antenna */}
        <mesh position={[0, 0.3, 0]} rotation={[0.2, 0, 0]}>
          <cylinderGeometry args={[0.02, 0.04, 0.15, 8]} />
          <meshStandardMaterial color={accentColor} roughness={0.2} metalness={0.5} />
        </mesh>
        <mesh position={[0, 0.38, -0.02]}>
          <sphereGeometry args={[0.05, 16, 16]} />
          <meshStandardMaterial color={accentColor} roughness={0.1} metalness={0.4} emissive={emissiveColor} emissiveIntensity={0.6} />
        </mesh>
      </group>

      {/* Left Arm */}
      <group ref={leftArmRef} position={[-0.32, 0.55, 0]}>
        <mesh castShadow>
          <capsuleGeometry args={[0.08, 0.35, 8, 16]} />
          <meshStandardMaterial color={limbsColor} roughness={0.3} metalness={0.1} />
        </mesh>
        {/* Hand */}
        <mesh position={[0, -0.25, 0]}>
          <sphereGeometry args={[0.09, 16, 16]} />
          <meshStandardMaterial color={limbsColor} roughness={0.2} metalness={0.1} />
        </mesh>
      </group>

      {/* Right Arm */}
      <group ref={rightArmRef} position={[0.32, 0.55, 0]}>
        <mesh castShadow>
          <capsuleGeometry args={[0.08, 0.35, 8, 16]} />
          <meshStandardMaterial color={limbsColor} roughness={0.3} metalness={0.1} />
        </mesh>
        {/* Hand */}
        <mesh position={[0, -0.25, 0]}>
          <sphereGeometry args={[0.09, 16, 16]} />
          <meshStandardMaterial color={limbsColor} roughness={0.2} metalness={0.1} />
        </mesh>
      </group>

      {/* Legs */}
      <mesh position={[-0.1, -0.25, 0]} castShadow>
        <capsuleGeometry args={[0.08, 0.4, 8, 16]} />
        <meshStandardMaterial color={limbsColor} roughness={0.3} metalness={0.1} />
      </mesh>
      <mesh position={[0.1, -0.25, 0]} castShadow>
        <capsuleGeometry args={[0.08, 0.4, 8, 16]} />
        <meshStandardMaterial color={limbsColor} roughness={0.3} metalness={0.1} />
      </mesh>

      {/* Shadow disc */}
      <mesh position={[0, -0.52, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.35, 32]} />
        <meshBasicMaterial color="#000000" transparent opacity={0.15} />
      </mesh>
    </group>
  )
}

// ============================================================
// 粒子背景
// ============================================================
function Particles() {
  const count = 30
  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 4
      pos[i * 3 + 1] = (Math.random() - 0.5) * 4
      pos[i * 3 + 2] = (Math.random() - 0.5) * 2
    }
    return pos
  }, [count])

  const ref = useRef()

  useFrame(() => {
    if (ref.current) {
      ref.current.rotation.y += 0.002
      ref.current.rotation.x += 0.001
    }
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={count}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial size={0.03} color="#6366f1" transparent opacity={0.4} sizeAttenuation />
    </points>
  )
}

// ============================================================
// 主 3D 场景
// ============================================================
function Scene({ skin, isWaving, onClick }) {
  return (
    <>
      <ambientLight intensity={0.6} />
      <directionalLight position={[5, 5, 5]} intensity={0.8} castShadow />
      <pointLight position={[0, 2, 2]} intensity={0.5} color={skin.emissive} />
      <pointLight position={[-2, 0, -2]} intensity={0.2} color={skin.accent} />
      <Particles />
      <CharacterModel skin={skin} isWaving={isWaving} onClick={onClick} />
    </>
  )
}

// ============================================================
// 点击后的反馈动画
// ============================================================
function ClickParticles({ position }) {
  // Simplified: just return null since we can't easily map screen coords to 3D
  return null
}

// ============================================================
// 3D 人偶容器组件（页面右下角）
// ============================================================
export default function Character3D({
  initialSkin = 'cyber-blue',
  onSkinChange,
}) {
  const [mounted, setMounted] = useState(false)
  const [skinId, setSkinId] = useState(initialSkin)
  const [isWaving, setIsWaving] = useState(false)
  const [showSkinPanel, setShowSkinPanel] = useState(false)
  const [speechBubble, setSpeechBubble] = useState(null)

  useEffect(() => {
    // Delay canvas init until after the container div is in the DOM
    const id = requestAnimationFrame(() => setMounted(true))
    return () => cancelAnimationFrame(id)
  }, [])

  const skin = SKIN_REGISTRY[skinId] || DEFAULT_SKIN

  const handleClick = () => {
    setIsWaving(true)
    setTimeout(() => setIsWaving(false), 1500)

    // Random speech
    const messages = [
      '你好！👋',
      '需要帮忙转换文件吗？',
      '点击我可以换皮肤哦~',
      '今天也是元气满满的一天！',
      '呜呼~',
      '✨',
    ]
    const msg = messages[Math.floor(Math.random() * messages.length)]
    setSpeechBubble(msg)
    setTimeout(() => setSpeechBubble(null), 2500)
  }

  const handleSkinSelect = (id) => {
    setSkinId(id)
    onSkinChange?.(SKIN_REGISTRY[id])
  }

  return (
    <>
      {/* 3D Canvas */}
      <div
        className="fixed bottom-4 right-4 z-40"
        style={{ width: 180, height: 200 }}
      >
        {/* Speech bubble */}
        <AnimatePresence>
          {speechBubble && (
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.8 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.8 }}
              className="absolute -top-12 left-1/2 -translate-x-1/2 bg-white/10 backdrop-blur-xl border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white whitespace-nowrap z-10"
            >
              {speechBubble}
            </motion.div>
          )}
        </AnimatePresence>

        {mounted && (
          <Canvas
            camera={{ position: [0, 0.8, 2.5], fov: 40 }}
            gl={{ antialias: true, alpha: true }}
            style={{ background: 'transparent' }}
          >
            <Suspense fallback={null}>
              <Scene skin={skin} isWaving={isWaving} onClick={handleClick} />
            </Suspense>
          </Canvas>
        )}

        {/* Clickable overlay */}
        <div
          className="absolute inset-0 cursor-pointer"
          onClick={handleClick}
          title="点击互动"
        />
      </div>

      {/* Skin panel toggle button */}
      <button
        onClick={() => setShowSkinPanel(!showSkinPanel)}
        className="fixed bottom-6 right-[200px] z-50 w-8 h-8 rounded-full glass flex items-center justify-center text-text-muted hover:text-text-primary transition-all hover:scale-110"
        title="切换皮肤"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
        </svg>
      </button>

      {/* Skin panel */}
      <AnimatePresence>
        {showSkinPanel && (
          <motion.div
            initial={{ opacity: 0, x: 20, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 20, scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            className="fixed bottom-[220px] right-4 z-50 glass-elevated p-4 w-48"
          >
            <h4 className="text-xs font-semibold text-text-primary mb-3 flex items-center gap-2">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
              </svg>
              选择皮肤
            </h4>
            <div className="space-y-1.5">
              {Object.entries(SKIN_REGISTRY).map(([id, s]) => (
                <button
                  key={id}
                  onClick={() => {
                    handleSkinSelect(id)
                    setShowSkinPanel(false)
                  }}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs transition-all ${
                    skinId === id
                      ? 'bg-white/10 text-text-primary border border-white/10'
                      : 'text-text-secondary hover:bg-white/5 hover:text-text-primary'
                  }`}
                >
                  <span
                    className="w-4 h-4 rounded-full shrink-0 border border-white/20"
                    style={{ background: s.head }}
                  />
                  {s.name}
                  {skinId === id && (
                    <svg className="w-3 h-3 ml-auto text-accent-blue" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  )}
                </button>
              ))}
            </div>

            {/* Custom skin info */}
            <div className="mt-3 pt-3 border-t border-white/5">
              <p className="text-[10px] text-text-muted leading-relaxed">
                如需自定义皮肤，请修改 <code className="text-accent-blue bg-white/5 px-1 rounded">SKIN_REGISTRY</code> 中的配置对象。
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mobile: hide skin toggle if screen is small */}
      <style>{`
        @media (max-width: 640px) {
          .skin-toggle-btn { display: none; }
        }
      `}</style>
    </>
  )
}
