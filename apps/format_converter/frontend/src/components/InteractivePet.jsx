import React, { useRef, useState, useMemo, useCallback, useEffect } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js'
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

// ── Generate a radial-glow halo texture (off-canvas canvas) ──
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
  ctx.shadowColor = color
  ctx.shadowBlur = 28; ctx.fillStyle = color; ctx.fillText(char, s / 2, s / 2)
  ctx.shadowBlur = 16; ctx.fillText(char, s / 2, s / 2)
  ctx.shadowBlur = 8;  ctx.fillStyle = '#fff'; ctx.fillText(char, s / 2, s / 2)
  return new THREE.CanvasTexture(c)
}
const linTexture = createGlowCharTexture('林', '#60a5fa')
const canTexture = createGlowCharTexture('参', '#c084fc')

// ============================================================
// Web Audio — 程序化猫叫声（无需音频文件）
// ============================================================
let _audioCtx = null
function _getAudioCtx() {
  if (!_audioCtx) {
    try { _audioCtx = new (window.AudioContext || window.webkitAudioContext)() } catch (_) { /* noop */ }
  }
  return _audioCtx
}

function playMeow() {
  const ctx = _getAudioCtx()
  if (!ctx) return
  // 短促上升滑音模拟"喵~"
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  osc.type = 'triangle'
  osc.frequency.setValueAtTime(400, ctx.currentTime)
  osc.frequency.linearRampToValueAtTime(650, ctx.currentTime + 0.08)
  osc.frequency.linearRampToValueAtTime(520, ctx.currentTime + 0.2)
  gain.gain.setValueAtTime(0, ctx.currentTime)
  gain.gain.linearRampToValueAtTime(0.08, ctx.currentTime + 0.02)
  gain.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.25)
  osc.connect(gain)
  gain.connect(ctx.destination)
  osc.start(ctx.currentTime)
  osc.stop(ctx.currentTime + 0.3)
}

// ============================================================
// CatModel — loads external GLB model with holy backlight
// Module-level model cache per URL — loads ONCE, shared across all renders
// ============================================================
let _cachedScenes = {}
let _loadPromises = {}

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

function _getOrLoadModel(url) {
  if (_cachedScenes[url]) return Promise.resolve(_cachedScenes[url])
  if (_loadPromises[url]) return _loadPromises[url]
  _loadPromises[url] = new Promise((resolve, reject) => {
    const loader = new GLTFLoader()
    // Draco 解压缩
    const dracoLoader = new DRACOLoader()
    dracoLoader.setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.7/')
    loader.setDRACOLoader(dracoLoader)
    loader.load(
      url,
      (gltf) => { _cachedScenes[url] = _processModel(gltf.scene); resolve(_cachedScenes[url]) },
      undefined,
      (err) => { _loadPromises[url] = null; reject(err) },
    )
  })
  return _loadPromises[url]
}
// Preload default cat model
const DEFAULT_MODEL_URL = '/cat_model.glb'
_getOrLoadModel(DEFAULT_MODEL_URL)

// ── 可用模型列表 ──
const MODELS = [
  { id: 'cat', name: '🐱 小猫', url: '/cat_model.glb', tip: '默认模型',
    settings: { noHalo: false, scaleMult: 1.0, brightness: 0.8 } },
  { id: 'shen', name: '🗿 Shen', url: '/shen_model.glb', tip: '新模型',
    settings: { noHalo: true, scaleMult: 1.4, brightness: 1.3 } },
]

const CatModel = React.forwardRef(function CatModel(props, ref) {
  const { emotion, mouse3D, isSleeping, wantsLean, leanTarget, modelUrl = DEFAULT_MODEL_URL,
          noHalo = false, scaleMult = 1.0, brightness = 0.8 } = props
  const groupRef = useRef()
  const haloRef = useRef()
  const bodyTarget = useRef(new THREE.Vector3(1, 1, 1))
  const squishing = useRef(false)
  const [modelScene, setModelScene] = useState(() => _cachedScenes[modelUrl] || null)

  useEffect(() => {
    let cancelled = false
    _getOrLoadModel(modelUrl).then((scene) => { if (!cancelled) setModelScene(scene) })
    return () => { cancelled = true }
  }, [modelUrl])

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
    // Breathing — slower when sleeping
    if (!squishing.current) {
      const rate = isSleeping ? 1.2 : 2.5
      const amp = isSleeping ? 0.015 : 0.03
      const b = 1 + Math.sin(t * rate) * amp
      bodyTarget.current.set(b, b, b)
    }
    if (groupRef.current) {
      groupRef.current.scale.lerp(bodyTarget.current, 0.12)
      // Normal sway vs sleepy sway
      if (isSleeping) {
        groupRef.current.rotation.z += (-0.01 - groupRef.current.rotation.z) * 0.02
      } else {
        groupRef.current.rotation.z = Math.sin(t * 1.5) * 0.03
      }
      // Paw tracking — lean toward cursor when nearby
      if (!isSleeping && wantsLean && leanTarget) {
        const lx = leanTarget.x * 0.15
        groupRef.current.rotation.y += (lx - groupRef.current.rotation.y) * 0.05
      }
    }
    // Halo — dimmer when sleeping
    if (haloRef.current) {
      const pulse = 1 + Math.sin(t * (isSleeping ? 0.6 : 1.8)) * 0.08
      haloRef.current.scale.setScalar(pulse)
      haloRef.current.material.opacity = (isSleeping ? 0.25 : 0.75) + Math.sin(t * 2.2) * 0.15
    }
  })

  return (
    <group ref={groupRef} scale={[scaleMult, scaleMult, scaleMult]}>
      {!noHalo && (
        <>
          <mesh ref={haloRef} position={[0, 0, 0]} renderOrder={-1}>
            <planeGeometry args={[1.0, 1.0]} />
            <meshBasicMaterial map={haloTexture} transparent depthWrite={false} depthTest={false}
              blending={THREE.AdditiveBlending} opacity={0.7} />
          </mesh>
          <mesh position={[0, 0, 0]} renderOrder={-1}>
            <planeGeometry args={[0.6, 0.6]} />
            <meshBasicMaterial map={haloTexture} transparent depthWrite={false} depthTest={false}
              blending={THREE.AdditiveBlending} opacity={0.35} />
          </mesh>
        </>
      )}
      {modelScene && <primitive object={modelScene} />}
      <mesh position={[0, -0.35, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.2, 32]} />
        <meshBasicMaterial color="#000" transparent opacity={0.12} />
      </mesh>
    </group>
  )
})

// ============================================================
// SatelliteText
// ============================================================
function SatelliteText() {
  const linRef = useRef()
  const canRef = useRef()
  useFrame((state) => {
    const t = state.clock.getElapsedTime()
    const radius = 0.5
    const speed = 1.3
    if (linRef.current) {
      const a = t * speed
      linRef.current.position.set(Math.cos(a) * radius, Math.sin(a) * radius * 0.55, Math.sin(a) * 0.35 + 0.1)
      linRef.current.scale.setScalar(1 + Math.sin(t * 3) * 0.08)
    }
    if (canRef.current) {
      const a = t * speed + Math.PI
      canRef.current.position.set(Math.cos(a) * radius, Math.sin(a) * radius * 0.55, Math.sin(a) * 0.35 + 0.1)
      canRef.current.scale.setScalar(1 + Math.sin(t * 3 + 1.5) * 0.08)
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
      ref.current.scale.set(1 - t, 1 - t, 1 - t)
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
// SleepZ — floating "Z" particles when cat is sleeping
// ============================================================
function SleepZ() {
  const zs = useRef([
    { id: 0, offset: 0, speed: 0.8, size: 0.06 },
    { id: 1, offset: 1.5, speed: 0.6, size: 0.05 },
    { id: 2, offset: 3.0, speed: 0.7, size: 0.04 },
  ])
  const zRefs = useRef([])

  useFrame((state) => {
    const t = state.clock.getElapsedTime()
    zRefs.current.forEach((ref, i) => {
      if (!ref) return
      const z = zs.current[i]
      const phase = (t * z.speed + z.offset) % 4
      ref.position.set(Math.sin(phase * 0.5) * 0.08, 0.3 + phase * 0.12, 0.2)
      ref.material.opacity = Math.max(0, 1 - phase / 4) * 0.6
      ref.scale.setScalar(z.size * (1 + phase * 0.3))
    })
  })

  return (
    <>
      {zs.current.map((z, i) => (
        <mesh key={z.id} ref={(el) => { zRefs.current[i] = el }} renderOrder={5}>
          <planeGeometry args={[0.12, 0.12]} />
          <meshBasicMaterial transparent depthWrite={false} depthTest={false}
            blending={THREE.AdditiveBlending} color="#a78bfa" />
        </mesh>
      ))}
    </>
  )
}

// ============================================================
// PhysicsScene — all interaction and physics logic
// ============================================================
const PhysicsScene = React.forwardRef((props, _forwardedRef) => {
  const { emotion, onSetEmotion, onSpeech, onSpawnParticle, onMood, onSleep,
          modelUrl, modelSettings = {} } = props
  const { noHalo, scaleMult, brightness = 0.8 } = modelSettings

  const petMesh = useRef()
  const catGroupRef = useRef()
  const catPos = useRef(new THREE.Vector3(0, 0.3, 0))
  const catVel = useRef(new THREE.Vector3(0, 0, 0))
  const mouseWorld = useRef(new THREE.Vector3())
  const leanTarget = useRef(new THREE.Vector3())
  const wantsLean = useRef(false)
  const hitCount = useRef(0)
  const emotionTimer = useRef(null)
  const [stickHit, setStickHit] = useState(null)
  const { camera, size, gl } = useThree()

  // ── drag state ──
  const isDragging = useRef(false)
  const dragStartPos = useRef(null)
  const dragHistory = useRef([])
  const hasMoved = useRef(false)
  const throwingAt = useRef(0)

  // ── mood / idle / sleep ──
  const mood = useRef(5)           // 0=angry, 5=neutral, 10=happy
  const lastInteraction = useRef(performance.now())
  const idleTimer = useRef(0)
  const idleAction = useRef(null)  // { type, startTime, duration }
  const isSleepingRef = useRef(false)
  const sleepTimer = useRef(0)
  const nextMeow = useRef(15 + Math.random() * 30)  // seconds between meows

  // stable callbacks
  const onSpeechRef = useRef(onSpeech); onSpeechRef.current = onSpeech
  const onSetEmotionRef = useRef(onSetEmotion); onSetEmotionRef.current = onSetEmotion
  const onSpawnRef = useRef(onSpawnParticle); onSpawnRef.current = onSpawnParticle
  const onMoodRef = useRef(onMood); onMoodRef.current = onMood
  const onSleepRef = useRef(onSleep); onSleepRef.current = onSleep

  const _markInteraction = useCallback(() => {
    lastInteraction.current = performance.now()
    sleepTimer.current = 0
    if (isSleepingRef.current) {
      isSleepingRef.current = false
      onSleepRef.current?.(false)
      onSpeechRef.current?.('喵~ 睡醒了！')
      idleTimer.current = 0
      idleAction.current = null
    }
  }, [])

  // ── screen → world ──
  const screenToWorld = useCallback((clientX, clientY) => {
    const rect = gl.domElement.getBoundingClientRect()
    const x = ((clientX - rect.left) / rect.width) * 2 - 1
    const y = -((clientY - rect.top) / rect.height) * 2 + 1
    const vec = new THREE.Vector3(x, y, 0.5)
    vec.unproject(camera)
    const dir = vec.sub(camera.position).normalize()
    const t = -camera.position.z / dir.z
    return new THREE.Vector3(camera.position.x + dir.x * t, camera.position.y + dir.y * t, 0)
  }, [camera, gl])

  // ── pointer events ──
  useEffect(() => {
    document.body.style.cursor = CURSORS.default

    const _endDrag = () => {
      document.body.style.userSelect = ''
      document.body.style.webkitUserSelect = ''
      document.body.style.cursor = CURSORS.default
    }

    const onDown = (e) => {
      const wp = screenToWorld(e.clientX, e.clientY)
      if (!wp) return
      const dist = Math.hypot(wp.x - catPos.current.x, wp.y - catPos.current.y)
      if (dist > 0.5) return

      _markInteraction()
      e.stopPropagation()
      e.preventDefault()
      isDragging.current = true
      hasMoved.current = false
      dragStartPos.current = { x: e.clientX, y: e.clientY }
      dragHistory.current = []
      document.body.style.userSelect = 'none'
      document.body.style.webkitUserSelect = 'none'
      petMesh.current?.squish?.(0.15)
      document.body.style.cursor = CURSORS.grabbing
    }

    const onMove = (e) => {
      if (!isDragging.current) return
      e.stopPropagation()
      e.preventDefault()
      const wp = screenToWorld(e.clientX, e.clientY)
      if (!wp) return
      if (dragStartPos.current) {
        const dx = e.clientX - dragStartPos.current.x
        const dy = e.clientY - dragStartPos.current.y
        if (Math.hypot(dx, dy) > 6) hasMoved.current = true
      }
      catPos.current.set(wp.x, wp.y, 0)
      catVel.current.set(0, 0, 0)
      dragHistory.current.push({ t: performance.now(), x: wp.x, y: wp.y })
      if (dragHistory.current.length > 10) dragHistory.current.shift()
      mouseWorld.current.copy(wp)
    }

    const onTouchMove = (e) => {
      if (isDragging.current) e.preventDefault()
    }

    const onUp = (e) => {
      if (!isDragging.current) return
      isDragging.current = false
      e.stopPropagation()
      _endDrag()

      if (hasMoved.current) {
        // THROW
        if (dragHistory.current.length >= 2) {
          const last = dragHistory.current[dragHistory.current.length - 1]
          const first = dragHistory.current[0]
          const dt = (last.t - first.t) / 1000
          if (dt > 0.01 && dt < 0.5) {
            catVel.current.set((last.x - first.x) / dt * 0.5, (last.y - first.y) / dt * 0.5 + 2.5, 0)
          } else {
            catVel.current.set(0, 2.5, 0)
          }
        } else {
          catVel.current.set(0, 2.5, 0)
        }
        throwingAt.current = performance.now()
        petMesh.current?.reset?.()
        onSpeechRef.current?.('咻—— 🚀')
        // throw = -1 mood
        mood.current = Math.max(0, mood.current - 1)
        onMoodRef.current?.(mood.current)
      } else {
        // TAP → STICK HIT
        const wp = screenToWorld(e.clientX, e.clientY)
        const cx = catPos.current.x
        const cy = catPos.current.y
        document.body.style.cursor = CURSORS.stick
        setStickHit({ x: cx + (Math.random() - 0.5) * 0.15, y: cy + 0.2, id: Date.now() })
        setTimeout(() => { document.body.style.cursor = CURSORS.default }, 350)
        if (wp) {
          const ddx = cx - wp.x; const ddy = cy - wp.y
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
        // hit = -2 mood
        mood.current = Math.max(0, mood.current - 2)
        onMoodRef.current?.(mood.current)
        if (emotionTimer.current) clearTimeout(emotionTimer.current)
        emotionTimer.current = setTimeout(() => { hitCount.current = 0 }, 4000)
      }
      dragHistory.current = []
    }

    const onCancel = () => {
      if (!isDragging.current) return
      isDragging.current = false
      hasMoved.current = false
      dragHistory.current = []
      _endDrag()
      petMesh.current?.reset?.()
    }

    window.addEventListener('pointerdown', onDown, { capture: true, passive: false })
    window.addEventListener('pointermove', onMove, { capture: true, passive: false })
    window.addEventListener('pointerup', onUp, { capture: true })
    window.addEventListener('pointercancel', onCancel, { capture: true })
    document.addEventListener('touchmove', onTouchMove, { passive: false })

    return () => {
      window.removeEventListener('pointerdown', onDown, { capture: true })
      window.removeEventListener('pointermove', onMove, { capture: true })
      window.removeEventListener('pointerup', onUp, { capture: true })
      window.removeEventListener('pointercancel', onCancel, { capture: true })
      document.removeEventListener('touchmove', onTouchMove)
      document.body.style.cursor = ''
    }
  }, [screenToWorld, _markInteraction])

  // ════════════════════════════════════════════════════════════
  // Per-frame: physics + idle actions + mood + sleep + meow
  // ════════════════════════════════════════════════════════════
  useFrame((state, delta) => {
    const dt = Math.min(delta, 1 / 30)
    const pos = catPos.current
    const vel = catVel.current
    const now = performance.now()
    const idleSince = (now - lastInteraction.current) / 1000

    const fovH = camera.position.z * Math.tan((camera.fov * Math.PI) / 360)
    const fovW = fovH * (size.width / size.height)
    const homeX = fovW * 0.7
    const homeY = -fovH * 0.3

    // ── mood decay toward neutral ──
    if (!isDragging.current && idleSince > 3) {
      const decayRate = 0.05
      if (mood.current > 5) mood.current = Math.max(5, mood.current - decayRate * dt * 4)
      else if (mood.current < 5) mood.current = Math.min(5, mood.current + decayRate * dt * 4)
      onMoodRef.current?.(mood.current)
    }

    // ── idle actions ──
    if (!isDragging.current && !isSleepingRef.current) {
      idleTimer.current += dt
      if (!idleAction.current) {
        // choose random action when idle long enough
        if (idleTimer.current > 5 + Math.random() * 8) {
          const actions = ['stretch', 'nod', 'lean', 'nothing']
          idleAction.current = { type: actions[Math.floor(Math.random() * actions.length)], startTime: now, duration: 1.2 }
          idleTimer.current = 0
        }
      } else {
        const elapsed = (now - idleAction.current.startTime) / 1000
        if (elapsed > idleAction.current.duration) {
          idleAction.current = null
          idleTimer.current = 0
        }
      }
    } else {
      idleTimer.current = 0
      idleAction.current = null
    }

    // Apply idle action to body (via CatModel's squish-like effect)
    if (idleAction.current?.type === 'stretch' && petMesh.current) {
      const p = (now - idleAction.current.startTime) / 1000 / idleAction.current.duration
      if (p < 0.15) petMesh.current.squish(0.08) // quick stretch
    }

    // ── sleep ──
    if (!isDragging.current && !isSleepingRef.current) {
      sleepTimer.current += dt
      if (sleepTimer.current > 30) {
        isSleepingRef.current = true
        onSleepRef.current?.(true)
      }
    }

    // ── meow ──
    if (!isSleepingRef.current) {
      nextMeow.current -= dt
      if (nextMeow.current <= 0) {
        playMeow()
        onSpawnRef.current?.('🎵')
        nextMeow.current = 20 + Math.random() * 40
      }
    }

    // ── paw tracking (cursor nearby but not dragging) ──
    if (!isDragging.current && !isSleepingRef.current && mouseWorld.current.lengthSq() > 0.001) {
      const dx = mouseWorld.current.x - pos.x
      const dy = mouseWorld.current.y - pos.y
      const cursorDist = Math.hypot(dx, dy)
      if (cursorDist < 1.5 && cursorDist > 0.1) {
        wantsLean.current = true
        leanTarget.current.set(dx / cursorDist, dy / cursorDist, 0)
      } else {
        wantsLean.current = false
      }
    } else {
      wantsLean.current = false
    }

    // ── gravity ──
    if (!isDragging.current) vel.y -= 3.0 * dt

    // ── damping ──
    if (!isDragging.current) {
      const damp = Math.max(0, 1 - 0.35 * dt * 4)
      vel.multiplyScalar(damp)
    }

    // ── spring toward home ──
    const distFromHome = Math.hypot(pos.x - homeX, pos.y - homeY)
    const inCooldown = (now - throwingAt.current) < 1500
    if (!isDragging.current && !inCooldown && distFromHome > 0.1) {
      const k = 5.0; const c = 2.8
      vel.x += (-(pos.x - homeX) * k - vel.x * c) * dt
      vel.y += (-(pos.y - homeY) * k - vel.y * c) * dt
      if (distFromHome < 0.05 && Math.abs(vel.x) < 0.3 && Math.abs(vel.y) < 0.3) {
        pos.set(homeX, homeY, 0)
        vel.set(0, 0, 0)
      }
    }

    if (!isDragging.current) { pos.x += vel.x * dt; pos.y += vel.y * dt }

    // ── soft boundary ──
    const maxR = Math.max(fovW, fovH) * 4
    const distR = Math.hypot(pos.x, pos.y)
    if (distR > maxR) {
      vel.x -= (pos.x / distR) * 20 * dt
      vel.y -= (pos.y / distR) * 20 * dt
    }

    if (catGroupRef.current) catGroupRef.current.position.copy(pos)
  })

  return (
    <group ref={_forwardedRef}>
      <ambientLight intensity={brightness} />
      <pointLight position={[0, 3.5, 0]} intensity={2.5 * (brightness / 0.8)} color="#fff8dc" distance={6} decay={1.5} />
      <pointLight position={[0, 2.0, 0.8]} intensity={1.2 * (brightness / 0.8)} color="#ffe4b5" distance={5} decay={1.8} />
      <directionalLight position={[4, 5, 3]} intensity={0.8 * (brightness / 0.8)} castShadow />
      <pointLight position={[0, 1.5, 2]} intensity={0.5 * (brightness / 0.8)} color="#818cf8" />
      <pointLight position={[-2, -1, -1]} intensity={0.15 * (brightness / 0.8)} color="#a78bfa" />

      <group ref={catGroupRef} position={[0, 0.3, 0]}>
        <CatModel ref={petMesh} emotion={emotion} mouse3D={mouseWorld}
          isSleeping={isSleepingRef.current}
          wantsLean={wantsLean.current}
          leanTarget={leanTarget.current}
          modelUrl={modelUrl}
          noHalo={noHalo}
          scaleMult={scaleMult}
          brightness={brightness} />
        <SatelliteText />
        {isSleepingRef.current && <SleepZ />}
      </group>

      {stickHit && (
        <StickHit key={stickHit.id} position={[stickHit.x, stickHit.y + 0.3, 0.3]}
          onComplete={() => setStickHit(null)} />
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
  const [moodVal, setMoodVal] = useState(5)
  const [isSleeping, setIsSleeping] = useState(false)
  const [modelIdx, setModelIdx] = useState(0)
  const currentModel = MODELS[modelIdx]
  const pidRef = useRef(0)

  useEffect(() => {
    const id = requestAnimationFrame(() => setMounted(true))
    return () => cancelAnimationFrame(id)
  }, [])

  const spawnParticle = useCallback((emoji) => {
    const id = ++pidRef.current
    const x = window.innerWidth - 140 + Math.random() * 80
    const y = window.innerHeight - 160 + Math.random() * 60
    setParticles((p) => [...p.slice(-8), { id, emoji, x, y }])
    setTimeout(() => setParticles((p) => p.filter((i) => i.id !== id)), 1200)
  }, [])

  const doSpeech = useCallback((msg) => {
    setSpeech(msg)
    setTimeout(() => setSpeech(null), 2200)
  }, [])

  const doMood = useCallback((val) => {
    setMoodVal(val)
    // mood particles
    if (val > 7) spawnParticle('❤️')
    if (val < 3) spawnParticle('💢')
  }, [spawnParticle])

  return (
    <>
      <div className="fixed inset-0 z-40 select-none" style={{ pointerEvents: 'none' }}>
        {/* Speech bubble */}
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
          <motion.div key={p.id} initial={{ opacity: 1, y: 0, scale: 0.4 }}
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
              onSpawnParticle={spawnParticle}
              onMood={doMood}
              onSleep={setIsSleeping}
              modelUrl={currentModel.url}
              modelSettings={currentModel.settings}
              onDebug={() => {}}
            />
          </Canvas>
        )}
      </div>

      {/* Model switcher */}
      <div className="fixed top-4 right-5 z-50">
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-white/30">模型</span>
          {MODELS.map((m, i) => (
            <button
              key={m.id}
              onClick={() => setModelIdx(i)}
              disabled={m.url === '/' || !m.url}
              title={m.tip || m.name}
              className={`text-[11px] px-2 py-0.5 rounded-full transition-all pointer-events-auto
                ${i === modelIdx
                  ? 'bg-white/15 text-white/80 border border-white/15'
                  : 'bg-white/5 text-white/30 border border-transparent hover:bg-white/10 hover:text-white/50'}`}
            >
              {m.name}
            </button>
          ))}
        </div>
      </div>

      {/* Info hint */}
      <div className="fixed bottom-4 right-5 z-50 pointer-events-none">
        <motion.div
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 2 }}
          className="text-[10px] text-white/40 leading-relaxed text-right"
        >
          {isSleeping ? (
            <div>😴 睡着了... 点它叫醒</div>
          ) : (
            <>
              <div>🐱 点击 = 敲它</div>
              <div>🖱️ 拖拽 = 扔飞它</div>
              <div>⏰ 30s不理 → 睡觉</div>
            </>
          )}
        </motion.div>
      </div>
    </>
  )
}
