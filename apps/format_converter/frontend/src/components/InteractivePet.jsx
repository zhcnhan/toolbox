import React, { useRef, useState, useMemo, useCallback, useEffect } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { motion, AnimatePresence } from 'framer-motion'

// ============================================================
// Custom cursor SVGs (inline data URLs)
// ============================================================
const stickCursorSvg = encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
    <line x1="2" y1="30" x2="30" y2="2" stroke="#8B4513" stroke-width="3" stroke-linecap="round"/>
    <circle cx="30" cy="2" r="4" fill="#CD853F"/>
  </svg>`,
)

const handCursorSvg = encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
    <path d="M8 22c0-2 2-4 4-4v-4c0-2 2-4 4-4s4 2 4 4v4c0-2 2-4 4-4s4 2 4 4v2c0 4-4 8-8 8h-4c-4 0-8-4-8-8z"
      fill="#FFDAB9" stroke="#DEB887" stroke-width="1.5"/>
  </svg>`,
)

const CURSORS = {
  default: 'grab',
  grabbing: `url("data:image/svg+xml,${handCursorSvg}") 16 16, grabbing`,
  stick: `url("data:image/svg+xml,${stickCursorSvg}") 16 16, auto`,
}

// ── Generate a radial-glow halo texture (off‑screen canvas) ──
const HALO_SIZE = 256
const haloCanvas = document.createElement('canvas')
haloCanvas.width = HALO_SIZE
haloCanvas.height = HALO_SIZE
const hctx = haloCanvas.getContext('2d')
const hgrad = hctx.createRadialGradient(HALO_SIZE / 2, HALO_SIZE / 2, 0, HALO_SIZE / 2, HALO_SIZE / 2, HALO_SIZE / 2)
hgrad.addColorStop(0, 'rgba(255,255,240,1)')
hgrad.addColorStop(0.12, 'rgba(255,240,200,0.95)')
hgrad.addColorStop(0.3, 'rgba(255,210,120,0.7)')
hgrad.addColorStop(0.5, 'rgba(255,180,60,0.25)')
hgrad.addColorStop(0.75, 'rgba(255,220,100,0.06)')
hgrad.addColorStop(1, 'rgba(255,255,255,0)')
hctx.fillStyle = hgrad
hctx.fillRect(0, 0, HALO_SIZE, HALO_SIZE)
const haloTexture = new THREE.CanvasTexture(haloCanvas)

// ── Generate glowing "林" and "参" character textures ──
function createGlowCharTexture(char, color) {
  const s = 128
  const c = document.createElement('canvas')
  c.width = s; c.height = s
  const ctx = c.getContext('2d')
  ctx.font = 'bold 88px "YouYuan", "幼圆", "Noto Sans SC", sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  // Multi-layer glow
  ctx.shadowColor = color
  ctx.shadowBlur = 28; ctx.fillStyle = color; ctx.fillText(char, s / 2, s / 2)
  ctx.shadowBlur = 16; ctx.fillText(char, s / 2, s / 2)
  ctx.shadowBlur = 8;  ctx.fillStyle = '#fff'; ctx.fillText(char, s / 2, s / 2)
  return new THREE.CanvasTexture(c)
}
const linTexture = createGlowCharTexture('林', '#60a5fa')
const canTexture = createGlowCharTexture('参', '#c084fc')

// ============================================================
// CatModel — loads external GLB model with holy backlight
// Uses manual GLTFLoader (no Suspense) so PhysicsScene mounts
// immediately and pointer events are attached right away.
// ============================================================
// Module-level model cache — loads ONCE, shared across all renders
// Starts downloading immediately when the JS chunk is parsed,
// before React even mounts. Subsequent visits use the cached scene.
// ============================================================
let _cachedScene = null
let _loadPromise = null

function _processModel(gltfScene) {
  const cloned = gltfScene.clone()
  cloned.traverse((child) => {
    if (child.isMesh) {
      child.castShadow = true
      child.receiveShadow = true
    }
  })
  const box = new THREE.Box3().setFromObject(cloned)
  const size = new THREE.Vector3()
  box.getSize(size)
  const maxDim = Math.max(size.x, size.y, size.z) || 1
  const targetScale = 0.5 / maxDim

  const estimate = new THREE.Vector3()
  box.getCenter(estimate)
  const v = new THREE.Vector3()
  cloned.updateWorldMatrix(true, true)
  const radius = maxDim * 0.3
  for (let iter = 0; iter < 3; iter++) {
    const c = new THREE.Vector3()
    let n = 0
    cloned.traverse((child) => {
      if (child.isMesh && child.geometry?.attributes?.position) {
        const pos = child.geometry.attributes.position
        const step = Math.max(1, Math.floor(pos.count / 500))
        for (let i = 0; i < pos.count; i += step) {
          v.fromBufferAttribute(pos, i)
          child.localToWorld(v)
          if (v.distanceTo(estimate) < radius) { c.add(v); n++ }
        }
      }
    })
    if (n > 0) estimate.copy(c.divideScalar(n))
  }
  cloned.scale.setScalar(targetScale)
  cloned.position.set(
    -estimate.x * targetScale, -estimate.y * targetScale, -estimate.z * targetScale,
  )
  return cloned
}

function _getOrLoadModel() {
  if (_cachedScene) return Promise.resolve(_cachedScene)
  if (_loadPromise) return _loadPromise
  console.log('[CatModel] Starting model load (singleton)')
  _loadPromise = new Promise((resolve, reject) => {
    const loader = new GLTFLoader()
    loader.load(
      '/cat_model.glb',
      (gltf) => {
        _cachedScene = _processModel(gltf.scene)
        console.log('[CatModel] Model cached (singleton)')
        resolve(_cachedScene)
      },
      (xhr) => {
        if (xhr.total) console.log('[CatModel] loading', `${((xhr.loaded / xhr.total) * 100).toFixed(0)}%`)
      },
      (err) => { _loadPromise = null; console.error('[CatModel] load error', err); reject(err) },
    )
  })
  return _loadPromise
}

// Start preloading immediately — model begins downloading as soon as JS is parsed
_getOrLoadModel()

// ============================================================
// CatModel — loads external GLB model with holy backlight
// Uses module-level singleton cache so model is only fetched once
// ============================================================
const CatModel = React.forwardRef(function CatModel({ emotion, mouse3D }, ref) {
  const groupRef = useRef()
  const haloRef = useRef()
  const bodyTarget = useRef(new THREE.Vector3(1, 1, 1))
  const squishing = useRef(false)
  const [modelScene, setModelScene] = useState(_cachedScene)

  useEffect(() => {
    let cancelled = false
    _getOrLoadModel().then((scene) => { if (!cancelled) setModelScene(scene) })
    return () => { cancelled = true }
  }, [])

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
    // Breathing animation
    if (!squishing.current) { const b = 1 + Math.sin(t * 2.5) * 0.03; bodyTarget.current.set(b, b, b) }
    if (groupRef.current) {
      groupRef.current.scale.lerp(bodyTarget.current, 0.12)
      groupRef.current.rotation.z = Math.sin(t * 1.5) * 0.03
    }
    // Pulsing halo glow
    if (haloRef.current) {
      const pulse = 1 + Math.sin(t * 1.8) * 0.08
      haloRef.current.scale.setScalar(pulse)
      haloRef.current.material.opacity = 0.75 + Math.sin(t * 2.2 + 1) * 0.25
    }
  })

  return (
    <group ref={groupRef}>
      {/* Holy backlight halo — at z=0 to eliminate parallax, renders behind model via renderOrder */}
      <mesh ref={haloRef} position={[0, 0, 0]} renderOrder={-1}>
        <planeGeometry args={[1.0, 1.0]} />
        <meshBasicMaterial
          map={haloTexture}
          transparent
          depthWrite={false}
          depthTest={false}
          blending={THREE.AdditiveBlending}
          opacity={0.7}
        />
      </mesh>
      {/* Second smaller, brighter inner glow ring */}
      <mesh position={[0, 0, 0]} renderOrder={-1}>
        <planeGeometry args={[0.6, 0.6]} />
        <meshBasicMaterial
          map={haloTexture}
          transparent
          depthWrite={false}
          depthTest={false}
          blending={THREE.AdditiveBlending}
          opacity={0.35}
        />
      </mesh>
      {/* The GLB model (renders once loaded) */}
      {modelScene && <primitive object={modelScene} />}
      {/* Ground shadow */}
      <mesh position={[0, -0.35, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.2, 32]} />
        <meshBasicMaterial color="#000" transparent opacity={0.12} />
      </mesh>
    </group>
  )
})

// ============================================================
// SatelliteText — "林" and "参" orbit the cat like satellites
// ============================================================
function SatelliteText() {
  const linRef = useRef()
  const canRef = useRef()

  useFrame((state) => {
    const t = state.clock.getElapsedTime()
    const radius = 0.5
    const speed = 1.3
    // "林" — orbit
    if (linRef.current) {
      const a = t * speed
      linRef.current.position.set(Math.cos(a) * radius, Math.sin(a) * radius * 0.55, Math.sin(a) * 0.35 + 0.1)
      const s = 1 + Math.sin(t * 3) * 0.08
      linRef.current.scale.setScalar(s)
    }
    // "参" — opposite side of orbit
    if (canRef.current) {
      const a = t * speed + Math.PI
      canRef.current.position.set(Math.cos(a) * radius, Math.sin(a) * radius * 0.55, Math.sin(a) * 0.35 + 0.1)
      const s = 1 + Math.sin(t * 3 + 1.5) * 0.08
      canRef.current.scale.setScalar(s)
    }
  })

  return (
    <>
      <mesh ref={linRef} renderOrder={5}>
        <planeGeometry args={[0.2, 0.2]} />
        <meshBasicMaterial map={linTexture} transparent depthWrite={false} depthTest={false} blending={THREE.AdditiveBlending} />
      </mesh>
      <mesh ref={canRef} renderOrder={5}>
        <planeGeometry args={[0.2, 0.2]} />
        <meshBasicMaterial map={canTexture} transparent depthWrite={false} depthTest={false} blending={THREE.AdditiveBlending} />
      </mesh>
    </>
  )
}

// ============================================================
// StickHit — 3D stick swing animation on click
// ============================================================
function StickHit({ position, onComplete }) {
  const ref = useRef()
  const start = useRef(performance.now())

  useFrame(() => {
    if (!ref.current) return
    const elapsed = (performance.now() - start.current) / 1000
    if (elapsed > 0.35) {
      onComplete()
      return
    }
    const p = elapsed / 0.35
    if (p < 0.4) {
      const t = p / 0.4
      const ease = 1 - Math.pow(1 - t, 2)
      ref.current.rotation.z = -Math.PI / 3 * ease
      ref.current.position.y = position[1] + 0.5 * (1 - t)
    } else if (p < 0.6) {
      ref.current.rotation.z = -Math.PI / 3
      ref.current.position.y = position[1]
    } else {
      const t = (p - 0.6) / 0.4
      ref.current.rotation.z = -Math.PI / 3 * (1 - t * 0.5)
      ref.current.position.y = position[1] + 0.3 * t
      const s = 1 - t
      ref.current.scale.set(s, s, s)
    }
  })

  return (
    <group ref={ref} position={position}>
      <group scale={0.55}>
        <mesh position={[0, 0.2, 0]}>
          <boxGeometry args={[0.04, 0.5, 0.04]} />
          <meshStandardMaterial color="#8B4513" />
        </mesh>
        <mesh position={[0, 0.45, 0]}>
          <sphereGeometry args={[0.06, 8, 8]} />
          <meshStandardMaterial color="#CD853F" />
        </mesh>
      </group>
    </group>
  )
}

// ============================================================
// PhysicsScene — custom physics, drag-to-throw, auto-return
//
// Uses NATIVE DOM pointer events on the <canvas> element.
// No Rapier dependency — custom spring + damping physics.
// ============================================================
const PhysicsScene = React.forwardRef((props, _forwardedRef) => {
  const { emotion, onSetEmotion, onSpeech, onDebug } = props

  const petMesh = useRef()
  const catGroupRef = useRef()
  const catPos = useRef(new THREE.Vector3(0, 0.3, 0))
  const catVel = useRef(new THREE.Vector3(0, 0, 0))
  const mouseWorld = useRef(new THREE.Vector3())
  const hitCount = useRef(0)
  const emotionTimer = useRef(null)
  const [stickHit, setStickHit] = useState(null)
  const { camera, size, gl } = useThree()

  // ── drag state (refs — stable across renders) ──
  const isDragging = useRef(false)
  const dragStartPos = useRef(null) // { x, y } — pointerdown 位置，用于判断是否为拖拽
  const dragHistory = useRef([])    // { t, x, y }[]
  const hasMoved = useRef(false)    // 总位移超过阈值才算拖拽（兼容触摸屏噪声）
  const throwingAt = useRef(0)
  // Stable ref to current callbacks so native listeners don't stale
  const onSpeechRef = useRef(onSpeech)
  onSpeechRef.current = onSpeech
  const onSetEmotionRef = useRef(onSetEmotion)
  onSetEmotionRef.current = onSetEmotion

  // ── screen (clientX,clientY) → world (z=0 plane) ──
  const screenToWorld = useCallback((clientX, clientY) => {
    const rect = gl.domElement.getBoundingClientRect()
    const x = ((clientX - rect.left) / rect.width) * 2 - 1
    const y = -((clientY - rect.top) / rect.height) * 2 + 1
    const vec = new THREE.Vector3(x, y, 0.5)
    vec.unproject(camera)
    const dir = vec.sub(camera.position).normalize()
    const t = -camera.position.z / dir.z
    return new THREE.Vector3(
      camera.position.x + dir.x * t,
      camera.position.y + dir.y * t,
      0,
    )
  }, [camera, gl])

  // ════════════════════════════════════════════════════════════
  //  Attach pointer events to WINDOW (capture phase).
  //  Canvas is full-screen with pointer-events:none, so events
  //  pass through to the UI unless we intercept near the cat.
  // ════════════════════════════════════════════════════════════
  useEffect(() => {
    document.body.style.cursor = CURSORS.default

    const onDown = (e) => {
      const wp = screenToWorld(e.clientX, e.clientY)
      if (!wp) return
      const dist = Math.hypot(wp.x - catPos.current.x, wp.y - catPos.current.y)
      if (dist > 0.5) return // not near cat — let event pass through to UI

      // Near cat — intercept
      e.stopPropagation()
      e.preventDefault()
      isDragging.current = true
      hasMoved.current = false
      dragStartPos.current = { x: e.clientX, y: e.clientY }  // 屏幕像素，避開世界坐标差异
      dragHistory.current = []
      petMesh.current?.squish?.(0.15)
      document.body.style.cursor = CURSORS.grabbing
    }

    const onMove = (e) => {
      if (!isDragging.current) return
      e.stopPropagation()
      e.preventDefault()
      const wp = screenToWorld(e.clientX, e.clientY)
      if (!wp) return

      // 用屏幕像素位移判断拖拽，跨设备一致
      if (dragStartPos.current) {
        const dx = e.clientX - dragStartPos.current.x
        const dy = e.clientY - dragStartPos.current.y
        if (Math.hypot(dx, dy) > 6) hasMoved.current = true  // > 6px 算拖拽
      }

      catPos.current.set(wp.x, wp.y, 0)
      catVel.current.set(0, 0, 0)

      dragHistory.current.push({ t: performance.now(), x: wp.x, y: wp.y })
      if (dragHistory.current.length > 10) dragHistory.current.shift()
      mouseWorld.current.copy(wp)
    }

    const onUp = (e) => {
      if (!isDragging.current) return
      isDragging.current = false
      e.stopPropagation()

      if (hasMoved.current) {
        // ═══ THROW (拖拽) ═══
        // 可能只有 1 次 pointermove（手机快速拖拽），也有多次（桌面端慢拖）
        if (dragHistory.current.length >= 2) {
          const last = dragHistory.current[dragHistory.current.length - 1]
          const first = dragHistory.current[0]
          const dt = (last.t - first.t) / 1000
          if (dt > 0.01 && dt < 0.5) {
            const vx = (last.x - first.x) / dt
            const vy = (last.y - first.y) / dt
            catVel.current.set(vx * 0.5, vy * 0.5 + 2.5, 0)
          } else {
            catVel.current.set(0, 2.5, 0)
          }
        } else {
          // 拖拽记录不足 → 默认向上抛
          catVel.current.set(0, 2.5, 0)
        }
        throwingAt.current = performance.now()
        petMesh.current?.reset?.()
        onSpeechRef.current?.('咻—— 🚀')
        document.body.style.cursor = CURSORS.default
      } else {
        // ═══ TAP → STICK HIT ═══
        const wp = screenToWorld(e.clientX, e.clientY)
        const cx = catPos.current.x
        const cy = catPos.current.y

        document.body.style.cursor = CURSORS.stick
        const hid = Date.now()
        setStickHit({ x: cx + (Math.random() - 0.5) * 0.15, y: cy + 0.2, id: hid })
        setTimeout(() => { document.body.style.cursor = CURSORS.default }, 350)

        if (wp) {
          const ddx = cx - wp.x
          const ddy = cy - wp.y
          const d = Math.hypot(ddx, ddy) || 1
          if (d < 3) {
            const force = Math.max(5, (1 - d / 3) * 14)
            catVel.current.x += (ddx / d) * force
            catVel.current.y += (ddy / d) * force + 4
          }
        }

        petMesh.current?.squish?.(0.22)
        hitCount.current++
        const hc = hitCount.current
        const speak = onSpeechRef.current
        const setFace = (face, dur) => {
          onSetEmotionRef.current?.(face)
          if (emotionTimer.current) clearTimeout(emotionTimer.current)
          emotionTimer.current = setTimeout(() => onSetEmotionRef.current?.('idle'), dur)
        }
        if (hc >= 7) { setFace('angry', 3000); speak?.('我生气了！！😤') }
        else if (hc >= 5) { setFace('dizzy', 2500); speak?.('分不清东南西北了...') }
        else if (hc >= 3) { setFace('ouch', 2000); speak?.('痛痛痛！💢') }
        else { setFace('ouch', 1200); speak?.('哎呀！') }
        if (hc > 8) hitCount.current = 0
        if (emotionTimer.current) clearTimeout(emotionTimer.current)
        emotionTimer.current = setTimeout(() => { hitCount.current = 0 }, 4000)
      }

      dragHistory.current = []
    }

    // Capture phase: intercept before event reaches UI elements
    window.addEventListener('pointerdown', onDown, { capture: true, passive: false })
    window.addEventListener('pointermove', onMove, { capture: true, passive: false })
    window.addEventListener('pointerup', onUp, { capture: true })
    window.addEventListener('pointercancel', onUp, { capture: true })

    return () => {
      window.removeEventListener('pointerdown', onDown, { capture: true })
      window.removeEventListener('pointermove', onMove, { capture: true })
      window.removeEventListener('pointerup', onUp, { capture: true })
      window.removeEventListener('pointercancel', onUp, { capture: true })
      document.body.style.cursor = ''
    }
  }, [screenToWorld])

  // ════════════════════════════════════════════════════════
  //  Per-frame: custom physics — gravity, spring, damping
  //  Cat can fly anywhere on screen (even off-screen), spring
  //  brings it back to home (bottom-right area).
  // ════════════════════════════════════════════════════════
  useFrame((state, delta) => {
    const dt = Math.min(delta, 1 / 30)
    const pos = catPos.current
    const vel = catVel.current

    // Compute home position — bottom-right area of screen
    const fovH = camera.position.z * Math.tan((camera.fov * Math.PI) / 360)
    const fovW = fovH * (size.width / size.height)
    const homeX = fovW * 0.7
    const homeY = -fovH * 0.3

    // Gravity (reduced — playful floaty feel)
    if (!isDragging.current) {
      vel.y -= 3.0 * dt
    }

    // Damping
    if (!isDragging.current) {
      const damp = Math.max(0, 1 - 0.35 * dt * 4)
      vel.multiplyScalar(damp)
    }

    // Spring toward home — only after throw cooldown
    const distFromHome = Math.hypot(pos.x - homeX, pos.y - homeY)
    const inCooldown = (performance.now() - throwingAt.current) < 1500
    if (!isDragging.current && !inCooldown && distFromHome > 0.1) {
      const k = 5.0   // spring constant
      const c = 2.8   // damping
      vel.x += (-(pos.x - homeX) * k - vel.x * c) * dt
      vel.y += (-(pos.y - homeY) * k - vel.y * c) * dt
      // Snap to rest when very close
      if (distFromHome < 0.05 && Math.abs(vel.x) < 0.3 && Math.abs(vel.y) < 0.3) {
        pos.set(homeX, homeY, 0)
        vel.set(0, 0, 0)
      }
    }

    // Integrate position
    if (!isDragging.current) {
      pos.x += vel.x * dt
      pos.y += vel.y * dt
    }

    // Soft far boundary — very generous, just prevents infinite drift
    const maxR = Math.max(fovW, fovH) * 4
    const distR = Math.hypot(pos.x, pos.y)
    if (distR > maxR) {
      vel.x -= (pos.x / distR) * 20 * dt
      vel.y -= (pos.y / distR) * 20 * dt
    }

    // Apply to group
    if (catGroupRef.current) {
      catGroupRef.current.position.copy(pos)
    }
  })

  return (
    <group ref={_forwardedRef}>
      <ambientLight intensity={0.8} />
      {/* Holy light from above */}
      <pointLight position={[0, 3.5, 0]} intensity={2.5} color="#fff8dc" distance={6} decay={1.5} />
      <pointLight position={[0, 2.0, 0.8]} intensity={1.2} color="#ffe4b5" distance={5} decay={1.8} />
      <directionalLight position={[4, 5, 3]} intensity={0.8} castShadow />
      <pointLight position={[0, 1.5, 2]} intensity={0.5} color="#818cf8" />
      <pointLight position={[-2, -1, -1]} intensity={0.15} color="#a78bfa" />

      {/* Cat — custom physics, position driven by useFrame */}
      <group ref={catGroupRef} position={[0, 0.3, 0]}>
        <CatModel ref={petMesh} emotion={emotion} mouse3D={mouseWorld} />
        <SatelliteText />
      </group>

      {stickHit && (
        <StickHit
          key={stickHit.id}
          position={[stickHit.x, stickHit.y + 0.3, 0.3]}
          onComplete={() => setStickHit(null)}
        />
      )}
    </group>
  )
})

// ============================================================
// InteractivePet — main export
// ============================================================
export default function InteractivePet() {
  const [mounted, setMounted] = useState(false)
  const [speech, setSpeech] = useState(null)
  const [particles, setParticles] = useState([])
  const [emotion, setEmotion] = useState('idle')
  const pidRef = useRef(0)

  useEffect(() => {
    const id = requestAnimationFrame(() => setMounted(true))
    return () => cancelAnimationFrame(id)
  }, [])

  const spawnParticle = useCallback((emoji) => {
    const id = ++pidRef.current
    // Position particles near cat (bottom-right area)
    const x = window.innerWidth - 140 + Math.random() * 80
    const y = window.innerHeight - 160 + Math.random() * 60
    setParticles((p) => [...p.slice(-8), { id, emoji, x, y }])
    setTimeout(() => setParticles((p) => p.filter((i) => i.id !== id)), 1200)
  }, [])

  const doSpeech = useCallback((msg) => {
    setSpeech(msg)
    spawnParticle('💬')
    setTimeout(() => setSpeech(null), 2200)
  }, [spawnParticle])

  return (
    <>
      {/* Full-screen overlay — pointer-events:none so UI below still works */}
      <div
        className="fixed inset-0 z-40"
        style={{ pointerEvents: 'none' }}
      >
        {/* Speech bubble — positioned near cat (bottom-right) */}
        <AnimatePresence>
          {speech && (
            <motion.div
              initial={{ opacity: 0, y: 12, scale: 0.85 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -12, scale: 0.85 }}
              className="absolute pointer-events-none z-20 bg-black/50 backdrop-blur-xl border border-white/10 rounded-2xl px-3.5 py-2 text-xs text-white whitespace-nowrap shadow-xl"
              style={{ right: 24, bottom: 220 }}
            >
              {speech}
              <div className="absolute -bottom-1.5 right-10 w-3 h-3 bg-black/50 border-r border-b border-white/10 rotate-45 rounded-br-sm" />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Floating particles */}
        {particles.map((p) => (
          <motion.div
            key={p.id}
            initial={{ opacity: 1, y: 0, scale: 0.4 }}
            animate={{ opacity: 0, y: -70, scale: 1.4 }}
            transition={{ duration: 1, ease: 'easeOut' }}
            className="absolute pointer-events-none text-xl z-10"
            style={{ left: p.x, top: p.y }}
          >
            {p.emoji}
          </motion.div>
        ))}

        {mounted && (
          <Canvas
            camera={{ position: [0, 0, 4], fov: 35 }}
            gl={{ antialias: true, alpha: true }}
            style={{ background: 'transparent', width: '100%', height: '100%', pointerEvents: 'none' }}
            onCreated={({ gl }) => gl.setClearColor(0, 0)}
          >
            <PhysicsScene
                emotion={emotion}
                onSetEmotion={setEmotion}
                onSpeech={doSpeech}
                onDebug={() => {}}
              />
          </Canvas>
        )}
      </div>

      {/* Info hint */}
      <div className="fixed bottom-4 right-5 z-50 pointer-events-none">
        <motion.div
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 2 }}
          className="text-[10px] text-white/40 leading-relaxed text-right"
        >
          <div>🐱 点击 = 敲它</div>
          <div>🖱️ 拖拽 = 扔飞它</div>
        </motion.div>
      </div>
    </>
  )
}
