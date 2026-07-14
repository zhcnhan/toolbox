import React, { useRef, useState, useMemo, useCallback, useEffect } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Physics, RigidBody, BallCollider, useRapier } from '@react-three/rapier'
import * as THREE from 'three'
import { motion, AnimatePresence } from 'framer-motion'

// ============================================================
// Custom cursor SVGs
// ============================================================
const stickCursorSvg = encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
    <line x1="2" y1="30" x2="30" y2="2" stroke="#8B4513" stroke-width="3" stroke-linecap="round"/>
    <circle cx="30" cy="2" r="4" fill="#CD853F"/>
  </svg>`)
const handCursorSvg = encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
    <path d="M8 22c0-2 2-4 4-4v-4c0-2 2-4 4-4s4 2 4 4v4c0-2 2-4 4-4s4 2 4 4v2c0 4-4 8-8 8h-4c-4 0-8-4-8-8z"
      fill="#FFDAB9" stroke="#DEB887" stroke-width="1.5"/>
  </svg>`)
const CURSORS = {
  default: 'grab',
  grabbing: `url("data:image/svg+xml,${handCursorSvg}") 16 16, grabbing`,
  stick: `url("data:image/svg+xml,${stickCursorSvg}") 16 16, auto`,
}

const FACES = {
  idle: { color: '#ffffff', blush: 0.25 },
  happy: { color: '#fff8f0', blush: 0.4 },
  ouch: { color: '#ffe4e1', blush: 0.6 },
  dizzy: { color: '#fffacd', blush: 0.5 },
  love: { color: '#fff0f5', blush: 0.7 },
  angry: { color: '#ffcccc', blush: 0.6 },
}

// ============================================================
// CatModel
// ============================================================
const CatModel = React.forwardRef(function CatModel({ emotion, mouse3D }, ref) {
  const groupRef = useRef()
  const pupilL = useRef()
  const pupilR = useRef()
  const bodyTarget = useRef(new THREE.Vector3(1, 1, 1))
  const squishing = useRef(false)
  const tailRef = useRef()
  const face = FACES[emotion] || FACES.idle
  const bodyColor = useMemo(() => new THREE.Color(face.color), [face.color])

  React.useImperativeHandle(ref, () => ({
    squish(amount) {
      squishing.current = true
      bodyTarget.current.set(1 + amount * 0.7, Math.max(0.25, 1 - amount * 2.5), 1 + amount * 0.7)
      setTimeout(() => { squishing.current = false; bodyTarget.current.set(1, 1, 1) }, 200)
    },
    reset() { squishing.current = false; bodyTarget.current.set(1, 1, 1) },
  }))

  useFrame((state) => {
    const t = state.clock.getElapsedTime()
    if (!squishing.current) { const b = 1 + Math.sin(t * 2.5) * 0.03; bodyTarget.current.set(b, b, b) }
    if (groupRef.current) {
      groupRef.current.scale.lerp(bodyTarget.current, 0.12)
      groupRef.current.rotation.z = Math.sin(t * 1.5) * 0.03
    }
    if (pupilL.current && pupilR.current && mouse3D.current) {
      const mx = Math.max(-0.05, Math.min(0.05, mouse3D.current.x * 0.03))
      const my = Math.max(-0.05, Math.min(0.05, mouse3D.current.y * 0.03))
      pupilL.current.position.set(mx, my, 0.06)
      pupilR.current.position.set(mx, my, 0.06)
    }
    if (tailRef.current) tailRef.current.rotation.z = Math.sin(t * 3) * 0.3
  })

  return (
    <group ref={groupRef}>
      <mesh castShadow scale={[1.05, 1.15, 0.95]}>
        <sphereGeometry args={[0.5, 48, 48]} />
        <meshPhysicalMaterial color={bodyColor} roughness={0.2} metalness={0} clearcoat={0.3} clearcoatRoughness={0.2} />
      </mesh>
      <mesh scale={[0.9, 0.95, 0.85]}><sphereGeometry args={[0.5, 24, 24]} /><meshBasicMaterial color={bodyColor} transparent opacity={0.05} /></mesh>
      <mesh position={[-0.18, 0.35, 0.25]} rotation={[0.2, -0.3, 0]}><sphereGeometry args={[0.22, 24, 24]} /><meshStandardMaterial color="#1a1a1a" roughness={0.8} /></mesh>
      <mesh position={[0.15, 0.33, 0.28]} rotation={[0.1, 0.2, 0]}><sphereGeometry args={[0.2, 24, 24]} /><meshStandardMaterial color="#6B4423" roughness={0.8} /></mesh>
      <mesh position={[-0.28, 0.58, 0]} rotation={[0, 0, 0.3]}><coneGeometry args={[0.12, 0.22, 4]} /><meshStandardMaterial color="#1a1a1a" roughness={0.7} /></mesh>
      <mesh position={[-0.28, 0.58, 0.04]} rotation={[0, 0, 0.3]}><coneGeometry args={[0.07, 0.14, 4]} /><meshStandardMaterial color="#FFB6C1" roughness={0.5} /></mesh>
      <mesh position={[0.28, 0.58, 0]} rotation={[0, 0, -0.3]}><coneGeometry args={[0.12, 0.22, 4]} /><meshStandardMaterial color="#6B4423" roughness={0.7} /></mesh>
      <mesh position={[0.28, 0.58, 0.04]} rotation={[0, 0, -0.3]}><coneGeometry args={[0.07, 0.14, 4]} /><meshStandardMaterial color="#FFB6C1" roughness={0.5} /></mesh>
      <group position={[-0.14, 0.1, 0.44]}>
        <mesh><sphereGeometry args={[0.11, 24, 24]} /><meshStandardMaterial color="#ffffff" roughness={0} /></mesh>
        <mesh ref={pupilL}><sphereGeometry args={[0.055, 16, 16]} /><meshStandardMaterial color="#111827" roughness={0} /></mesh>
        <mesh position={[0.03, 0.04, 0.07]}><sphereGeometry args={[0.025, 8, 8]} /><meshBasicMaterial color="#fff" /></mesh>
      </group>
      <group position={[0.14, 0.1, 0.44]}>
        <mesh><sphereGeometry args={[0.11, 24, 24]} /><meshStandardMaterial color="#ffffff" roughness={0} /></mesh>
        <mesh ref={pupilR}><sphereGeometry args={[0.055, 16, 16]} /><meshStandardMaterial color="#111827" roughness={0} /></mesh>
        <mesh position={[0.03, 0.04, 0.07]}><sphereGeometry args={[0.025, 8, 8]} /><meshBasicMaterial color="#fff" /></mesh>
      </group>
      <mesh position={[-0.26, -0.06, 0.44]}><sphereGeometry args={[0.08, 16, 16]} /><meshBasicMaterial color="#ff8da1" transparent opacity={face.blush} /></mesh>
      <mesh position={[0.26, -0.06, 0.44]}><sphereGeometry args={[0.08, 16, 16]} /><meshBasicMaterial color="#ff8da1" transparent opacity={face.blush} /></mesh>
      <mesh position={[0, -0.06, 0.49]} rotation={[0, 0, Math.PI]}><coneGeometry args={[0.03, 0.04, 3]} /><meshStandardMaterial color="#FF69B4" roughness={0.3} /></mesh>
      <group position={[0, -0.12, 0.47]}>
        <mesh position={[-0.025, 0, 0]} rotation={[0, 0, Math.PI / 4]}><boxGeometry args={[0.025, 0.04, 0.01]} /><meshStandardMaterial color="#333" /></mesh>
        <mesh position={[0.025, 0, 0]} rotation={[0, 0, -Math.PI / 4]}><boxGeometry args={[0.025, 0.04, 0.01]} /><meshStandardMaterial color="#333" /></mesh>
      </group>
      <mesh position={[-0.2, -0.52, 0.15]} rotation={[0.3, 0, 0]}><capsuleGeometry args={[0.06, 0.1, 8, 16]} /><meshStandardMaterial color="#ffffff" roughness={0.3} /></mesh>
      <mesh position={[0.2, -0.52, 0.15]} rotation={[0.3, 0, 0]}><capsuleGeometry args={[0.06, 0.1, 8, 16]} /><meshStandardMaterial color="#ffffff" roughness={0.3} /></mesh>
      <mesh position={[-0.22, -0.52, -0.15]} rotation={[-0.3, 0, 0]}><capsuleGeometry args={[0.06, 0.1, 8, 16]} /><meshStandardMaterial color="#ffffff" roughness={0.3} /></mesh>
      <mesh position={[0.22, -0.52, -0.15]} rotation={[-0.3, 0, 0]}><capsuleGeometry args={[0.06, 0.1, 8, 16]} /><meshStandardMaterial color="#ffffff" roughness={0.3} /></mesh>
      <mesh position={[-0.48, -0.1, 0.05]} rotation={[0, 0, Math.PI / 2.5]}><capsuleGeometry args={[0.05, 0.12, 8, 16]} /><meshStandardMaterial color="#ffffff" roughness={0.3} /></mesh>
      <mesh position={[0.48, -0.1, 0.05]} rotation={[0, 0, -Math.PI / 2.5]}><capsuleGeometry args={[0.05, 0.12, 8, 16]} /><meshStandardMaterial color="#ffffff" roughness={0.3} /></mesh>
      <group ref={tailRef} position={[0, -0.2, -0.4]} rotation={[0.8, 0, 0]}>
        <mesh><capsuleGeometry args={[0.05, 0.25, 8, 16]} /><meshStandardMaterial color="#ffffff" roughness={0.3} /></mesh>
        <mesh position={[0, -0.15, 0]}><sphereGeometry args={[0.06, 16, 16]} /><meshStandardMaterial color="#1a1a1a" roughness={0.7} /></mesh>
      </group>
      <mesh position={[0, -0.62, 0]} rotation={[-Math.PI / 2, 0, 0]}><circleGeometry args={[0.35, 32]} /><meshBasicMaterial color="#000" transparent opacity={0.12} /></mesh>
    </group>
  )
})

// ============================================================
// StickHit
// ============================================================
function StickHit({ position, onComplete }) {
  const ref = useRef()
  const start = useRef(performance.now())
  useFrame(() => {
    if (!ref.current) return
    const elapsed = (performance.now() - start.current) / 1000
    if (elapsed > 0.35) { onComplete(); return }
    const p = elapsed / 0.35
    if (p < 0.4) { const t = p / 0.4; ref.current.rotation.z = -Math.PI / 3 * (1 - Math.pow(1 - t, 2)); ref.current.position.y = position[1] + 0.5 * (1 - t) }
    else if (p < 0.6) { ref.current.rotation.z = -Math.PI / 3; ref.current.position.y = position[1] }
    else { const t = (p - 0.6) / 0.4; ref.current.rotation.z = -Math.PI / 3 * (1 - t * 0.5); ref.current.position.y = position[1] + 0.3 * t; const s = 1 - t; ref.current.scale.set(s, s, s) }
  })
  return (
    <group ref={ref} position={position}>
      <mesh position={[0, 0.2, 0]}><boxGeometry args={[0.04, 0.5, 0.04]} /><meshStandardMaterial color="#8B4513" /></mesh>
      <mesh position={[0, 0.45, 0]}><sphereGeometry args={[0.06, 8, 8]} /><meshStandardMaterial color="#CD853F" /></mesh>
    </group>
  )
}

// ============================================================
// RigidBodyCapture — finds RigidBody via rigidBodyStates Map
// ============================================================
function RigidBodyCapture({ bridge }) {
  const groupRef = useRef()
  const { rigidBodyStates } = useRapier()
  useFrame(() => {
    if (bridge.rb || !groupRef.current) return
    const parentObj = groupRef.current.parent
    if (!parentObj) return
    for (const [, state] of rigidBodyStates) {
      if (state.object === parentObj) { bridge.rb = state.rigidBody; bridge.getRb = () => state.rigidBody; break }
    }
  })
  return <group ref={groupRef} />
}

// ============================================================
// CameraRig — offsets camera so the cat (at world 0,0.3,0)
// appears in the bottom-right area of the full-screen canvas.
// ============================================================
function CameraRig({ bridge }) {
  const { camera, size } = useThree()
  useEffect(() => {
    const halfH = camera.position.z * Math.tan((camera.fov * Math.PI) / 360)
    const halfW = halfH * (size.width / size.height)
    // Cat at (0, 0.3) should appear ~78% right, ~72% down
    const offsetX = 0 - halfW * 0.56
    const offsetY = 0.3 + halfH * 0.44
    camera.position.set(offsetX, offsetY, camera.position.z)
    camera.lookAt(offsetX, offsetY, 0)
    camera.updateProjectionMatrix()
    bridge.cameraOffset = { x: offsetX, y: offsetY }
  }, [camera, size, bridge])
  return null
}

// ============================================================
// PhysicsScene — pure physics + rendering
// ============================================================
const PhysicsScene = React.forwardRef(function PhysicsScene({ emotion, bridge }, forwardedRef) {
  const petMesh = useRef()
  const mouseWorld = useRef(new THREE.Vector3())
  const [stickHit, setStickHit] = useState(null)
  const { camera } = useThree()
  const isDragging = useRef(false)
  const throwingAt = useRef(0)

  useEffect(() => {
    if (!bridge) return
    bridge.camera = camera
    bridge.squishPet = (a) => petMesh.current?.squish?.(a)
    bridge.resetPet = () => petMesh.current?.reset?.()
    bridge.setMouseWorld = (v) => mouseWorld.current.copy(v)
    bridge.setDragging = (v) => { isDragging.current = v }
    bridge.setThrowingAt = (v) => { throwingAt.current = v }
    bridge.triggerStickHit = () => {
      const cp = bridge.rb?.translation?.()
      setStickHit({ x: (cp?.x ?? 0) + (Math.random() - 0.5) * 0.2, y: (cp?.y ?? 0) + 0.35, id: Date.now() })
    }
    bridge.screenToWorld = (clientX, clientY) => {
      try {
        const cam = bridge.camera
        const canvas = bridge.canvas
        if (!cam || !canvas) return null
        const rect = canvas.getBoundingClientRect()
        if (!rect || rect.width === 0) return null
        const x = ((clientX - rect.left) / rect.width) * 2 - 1
        const y = -((clientY - rect.top) / rect.height) * 2 + 1
        const vec = new THREE.Vector3(x, y, 0.5)
        vec.unproject(cam)
        const dir = vec.sub(cam.position).normalize()
        if (dir.z === 0) return null
        const t = -cam.position.z / dir.z
        return new THREE.Vector3(cam.position.x + dir.x * t, cam.position.y + dir.y * t, 0)
      } catch { return null }
    }
    // World → screen pixel coords (for HTML overlays)
    bridge.worldToScreen = (wx, wy, wz) => {
      try {
        const cam = bridge.camera
        const canvas = bridge.canvas
        if (!cam || !canvas) return null
        const v = new THREE.Vector3(wx, wy, wz)
        v.project(cam)
        const rect = canvas.getBoundingClientRect()
        return { x: (v.x * 0.5 + 0.5) * rect.width + rect.left, y: (-v.y * 0.5 + 0.5) * rect.height + rect.top }
      } catch { return null }
    }
  }, [bridge, camera])

  // Auto-return spring
  useFrame(() => {
    if (!bridge.rb) return
    const pos = bridge.rb.translation()
    const vel = bridge.rb.linvel()
    const dist = Math.hypot(pos.x, pos.y - 0.3)
    const inCooldown = (performance.now() - throwingAt.current) < 2500
    if (!isDragging.current && !inCooldown && dist > 0.05) {
      const k = 0.04, c = 0.04
      bridge.rb.applyImpulse({ x: -pos.x * k - vel.x * c, y: -(pos.y - 0.3) * k - vel.y * c, z: 0 }, true)
      if (dist < 0.08 && Math.abs(vel.x) < 0.3 && Math.abs(vel.y) < 0.3) {
        bridge.rb.setTranslation({ x: 0, y: 0.3, z: 0 }, true)
        bridge.rb.setLinvel({ x: 0, y: 0, z: 0 }, true)
      }
    }
  })

  return (
    <group ref={forwardedRef}>
      <CameraRig bridge={bridge} />
      <ambientLight intensity={0.6} />
      <directionalLight position={[4, 5, 3]} intensity={0.7} castShadow />
      <pointLight position={[0, 1.5, 2]} intensity={0.5} color="#818cf8" />
      <pointLight position={[-2, -1, -1]} intensity={0.15} color="#a78bfa" />
      <RigidBody colliders={false} linearDamping={0.15} angularDamping={0.5} gravityScale={0.3} position={[0, 0.3, 0]}>
        <BallCollider args={[0.48]} />
        <CatModel ref={petMesh} emotion={emotion} mouse3D={mouseWorld} />
        <RigidBodyCapture bridge={bridge} />
      </RigidBody>
      {stickHit && <StickHit key={stickHit.id} position={[stickHit.x, stickHit.y + 0.5, 0.3]} onComplete={() => setStickHit(null)} />}
    </group>
  )
})

// ============================================================
// LinCanText — "林参" text with spring physics following
// ============================================================
const SPARKLE_KEYFRAMES = `
@keyframes linCanSparkle {
  0%, 100% { text-shadow: 0 0 8px rgba(255,182,193,0.8), 0 0 16px rgba(255,182,193,0.4), 0 0 24px rgba(255,182,193,0.2); }
  25% { text-shadow: 0 0 12px rgba(255,215,0,0.9), 0 0 24px rgba(255,215,0,0.5), 0 0 36px rgba(255,215,0,0.3); }
  50% { text-shadow: 0 0 10px rgba(147,112,219,0.9), 0 0 20px rgba(147,112,219,0.5), 0 0 30px rgba(147,112,219,0.3); }
  75% { text-shadow: 0 0 14px rgba(135,206,250,0.9), 0 0 28px rgba(135,206,250,0.5), 0 0 42px rgba(135,206,250,0.3); }
}
`

function LinCanText({ bridge }) {
  const textRef = useRef(null)
  // Spring state: position + velocity for each char
  const spring = useRef({
    x: 0, y: 0,           // current position (char 1)
    x2: 0, y2: 0,         // current position (char 2)
    vx: 0, vy: 0,         // velocity (char 1)
    vx2: 0, vy2: 0,       // velocity (char 2)
  })

  useEffect(() => {
    // Inject keyframes once
    const styleId = 'lincan-sparkle-style'
    if (!document.getElementById(styleId)) {
      const el = document.createElement('style')
      el.id = styleId
      el.textContent = SPARKLE_KEYFRAMES
      document.head.appendChild(el)
    }
  }, [])

  useEffect(() => {
    let raf
    const loop = () => {
      raf = requestAnimationFrame(loop)
      if (!bridge.rb || !bridge.camera || !bridge.canvas || !bridge.worldToScreen) return
      const pos = bridge.rb.translation()
      const screen = bridge.worldToScreen(pos.x, pos.y + 0.75, 0)
      if (!screen) return

      // Damped spring: tight follow with slight wobble
      const s = spring.current
      const k = 0.38, damp = 0.72

      // Char 1 → cat position
      s.vx = (s.vx + (screen.x - s.x) * k) * damp
      s.vy = (s.vy + (screen.y - s.y) * k) * damp
      s.x += s.vx
      s.y += s.vy

      // Char 2 → trails char1 with slight delay (inertia wobble)
      const target2x = s.x + 30
      const target2y = s.y
      s.vx2 = (s.vx2 + (target2x - s.x2) * k * 0.85) * damp
      s.vy2 = (s.vy2 + (target2y - s.y2) * k * 0.85) * damp
      s.x2 += s.vx2
      s.y2 += s.vy2

      if (textRef.current) {
        textRef.current.style.transform = `translate(${s.x}px, ${s.y}px)`
        const ch2 = textRef.current.querySelector('.lincan-char2')
        if (ch2) ch2.style.transform = `translate(${s.x2 - s.x - 30}px, ${s.y2 - s.y}px)`
      }
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [bridge])

  return (
    <div ref={textRef} style={{
      position: 'fixed', top: 0, left: 0, zIndex: 45, pointerEvents: 'none',
      willChange: 'transform',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
        <span className="lincan-char1" style={{
          fontFamily: '"YouYuan", "幼圆", "Hiragino Maru Gothic ProN", "Mochiy Pop One", "Noto Sans SC", sans-serif',
          fontSize: '28px', fontWeight: 'bold',
          color: '#fff0f5',
          WebkitTextStroke: '1.5px #ff69b4',
          textStroke: '1.5px #ff69b4',
          animation: 'linCanSparkle 2s ease-in-out infinite',
          display: 'inline-block',
          willChange: 'transform, text-shadow',
          letterSpacing: '2px',
        }}>林</span>
        <span className="lincan-char2" style={{
          fontFamily: '"YouYuan", "幼圆", "Hiragino Maru Gothic ProN", "Mochiy Pop One", "Noto Sans SC", sans-serif',
          fontSize: '28px', fontWeight: 'bold',
          color: '#f0f8ff',
          WebkitTextStroke: '1.5px #9370db',
          textStroke: '1.5px #9370db',
          animation: 'linCanSparkle 2s ease-in-out infinite',
          animationDelay: '0.5s',
          display: 'inline-block',
          willChange: 'transform, text-shadow',
          letterSpacing: '2px',
          marginLeft: '2px',
        }}>参</span>
      </div>
    </div>
  )
}

// ============================================================
// InteractivePet — main export
// ============================================================
export default function InteractivePet() {
  const [mounted, setMounted] = useState(false)
  const [speech, setSpeech] = useState(null)
  const [particles, setParticles] = useState([])
  const [emotion, setEmotion] = useState('idle')
  const [catScreenPos, setCatScreenPos] = useState({ x: window.innerWidth - 120, y: window.innerHeight - 80 })
  const pidRef = useRef(0)
  const containerRef = useRef(null)
  const bridge = useRef({}).current

  useEffect(() => {
    const id = requestAnimationFrame(() => setMounted(true))
    return () => cancelAnimationFrame(id)
  }, [])

  const spawnParticle = useCallback((emoji) => {
    const id = ++pidRef.current
    setParticles((p) => [...p.slice(-8), { id, emoji, x: 80 + Math.random() * 80, y: 100 + Math.random() * 60 }])
    setTimeout(() => setParticles((p) => p.filter((i) => i.id !== id)), 1200)
  }, [])

  const doSpeech = useCallback((msg) => {
    setSpeech(msg)
    spawnParticle('💬')
    setTimeout(() => setSpeech(null), 2200)
  }, [spawnParticle])

  const doSpeechRef = useRef(doSpeech); doSpeechRef.current = doSpeech
  const setEmotionRef = useRef(setEmotion); setEmotionRef.current = setEmotion
  const dragState = useRef({ isDragging: false, hasMoved: false, history: [], downX: 0, downY: 0 })

  // Track cat screen position for speech bubble / particles
  useEffect(() => {
    if (!mounted) return
    let raf
    const loop = () => {
      raf = requestAnimationFrame(loop)
      if (bridge.rb && bridge.camera && bridge.canvas) {
        const pos = bridge.rb.translation()
        const screen = bridge.worldToScreen?.(pos.x, pos.y + 0.6, 0)
        if (screen) setCatScreenPos({ x: screen.x, y: screen.y })
      }
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [mounted, bridge])

  // Window-level pointer events
  useEffect(() => {
    if (!mounted) return

    let canvasEl = null
    let retries = 0
    const findCanvas = () => {
      canvasEl = containerRef.current?.querySelector('canvas')
      if (canvasEl) { bridge.canvas = canvasEl; return true }
      if (retries++ < 30) setTimeout(findCanvas, 100)
      return false
    }
    findCanvas()

    const setCursor = (c) => { document.body.style.cursor = c }

    const onDown = (e) => {
      if (!bridge.getRb) return
      const rb = bridge.getRb()
      if (!rb) return
      if (!bridge.screenToWorld) return
      const wp = bridge.screenToWorld(e.clientX, e.clientY)
      if (!wp) return
      const cp = rb.translation()
      if (Math.hypot(wp.x - cp.x, wp.y - cp.y) > 0.8) return

      e.preventDefault()
      const s = dragState.current
      s.isDragging = true; s.hasMoved = false; s.downX = e.clientX; s.downY = e.clientY
      s.history = [{ t: performance.now(), x: wp.x, y: wp.y }]
      bridge.setDragging?.(true)
      bridge.squishPet?.(0.15)
      setCursor(CURSORS.grabbing)
    }

    const onMove = (e) => {
      const s = dragState.current
      if (!s.isDragging) return
      if (!bridge.getRb || !bridge.screenToWorld) return
      const rb = bridge.getRb()
      if (!rb) return
      const wp = bridge.screenToWorld(e.clientX, e.clientY)
      if (!wp) return
      if (Math.abs(e.clientX - s.downX) > 3 || Math.abs(e.clientY - s.downY) > 3) s.hasMoved = true
      rb.setTranslation({ x: wp.x, y: wp.y, z: 0 }, true)
      rb.setLinvel({ x: 0, y: 0, z: 0 }, true)
      bridge.setMouseWorld?.(wp)
      s.history.push({ t: performance.now(), x: wp.x, y: wp.y })
      if (s.history.length > 10) s.history.shift()
    }

    const onUp = () => {
      const s = dragState.current
      if (!s.isDragging) return
      s.isDragging = false
      bridge.setDragging?.(false)
      if (!bridge.getRb) return
      const rb = bridge.getRb()

      if (s.hasMoved && s.history.length >= 2) {
        const last = s.history[s.history.length - 1]
        const first = s.history[0]
        const dt = (last.t - first.t) / 1000
        if (rb && dt > 0.01 && dt < 0.5) {
          rb.applyImpulse({ x: (last.x - first.x) / dt * 0.5, y: (last.y - first.y) / dt * 0.5 + 2.5, z: 0 }, true)
        } else if (rb) {
          rb.applyImpulse({ x: 0, y: 2.5, z: 0 }, true)
        }
        bridge.setThrowingAt?.(performance.now())
        bridge.resetPet?.()
        doSpeechRef.current?.('咻—— 🚀')
      } else if (!s.hasMoved && rb) {
        setCursor(CURSORS.stick)
        bridge.triggerStickHit?.()
        doSpeechRef.current?.('哎呀！')
        setEmotionRef.current?.('ouch')
        setTimeout(() => setCursor(CURSORS.default), 350)
      }
      setCursor(CURSORS.default)
      s.history = []
    }

    window.addEventListener('pointerdown', onDown, { capture: true })
    window.addEventListener('pointermove', onMove, { capture: true })
    window.addEventListener('pointerup', onUp, { capture: true })
    return () => {
      window.removeEventListener('pointerdown', onDown, { capture: true })
      window.removeEventListener('pointermove', onMove, { capture: true })
      window.removeEventListener('pointerup', onUp, { capture: true })
      document.body.style.cursor = ''
    }
  }, [mounted, bridge])

  return (
    <>
      {/* Full-screen transparent canvas overlay */}
      <div ref={containerRef} className="fixed inset-0 z-40" style={{ pointerEvents: 'none' }}>
        {mounted && (
          <Canvas camera={{ position: [0, 0, 12], fov: 35 }} gl={{ antialias: true, alpha: true }}
            style={{ background: 'transparent', width: '100%', height: '100%' }}
            onCreated={({ gl }) => gl.setClearColor(0, 0)}>
            <Physics>
              <PhysicsScene emotion={emotion} bridge={bridge} />
            </Physics>
          </Canvas>
        )}
      </div>

      {/* "林参" text following the cat with spring physics */}
      <LinCanText bridge={bridge} />

      {/* Speech bubble — positioned at cat's screen location */}
      <AnimatePresence>
        {speech && (
          <motion.div
            initial={{ opacity: 0, y: 12, scale: 0.85 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -12, scale: 0.85 }}
            className="fixed bg-black/50 backdrop-blur-xl border border-white/10 rounded-2xl px-3.5 py-2 text-xs text-white whitespace-nowrap z-50 shadow-xl pointer-events-none"
            style={{ left: catScreenPos.x, top: catScreenPos.y - 50, transform: 'translateX(-50%)' }}
          >
            {speech}
            <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-black/50 border-r border-b border-white/10 rotate-45 rounded-br-sm" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating particles — positioned at cat's screen location */}
      {particles.map((p) => (
        <motion.div key={p.id} initial={{ opacity: 1, y: 0, scale: 0.4 }} animate={{ opacity: 0, y: -70, scale: 1.4 }} transition={{ duration: 1, ease: 'easeOut' }}
          className="fixed pointer-events-none text-xl z-50" style={{ left: catScreenPos.x + p.x - 120, top: catScreenPos.y + p.y - 80 }}>
          {p.emoji}
        </motion.div>
      ))}

      {/* Info hint */}
      <div className="fixed bottom-4 right-4 z-50 hidden lg:block">
        <motion.div initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 2 }}
          className="text-[10px] text-white/40 leading-relaxed text-right">
          <div>🐱 点击 = 敲它</div>
          <div>🖱️ 拖拽 = 扔飞它</div>
        </motion.div>
      </div>
    </>
  )
}
