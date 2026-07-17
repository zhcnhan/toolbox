// Service Worker — 缓存 3D 模型，手机/桌面通吃
const CACHE_NAME = 'toolbox-cat-v1'

self.addEventListener('install', (event) => {
  console.log('[SW] Installing...')
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching cat_model.glb')
      return cache.add('/cat_model.glb')
    })
  )
})

self.addEventListener('activate', (event) => {
  // 清理旧缓存
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  )
})

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)
  // 只拦截模型文件
  if (url.pathname === '/cat_model.glb') {
    event.respondWith(
      caches.match(event.request).then((cached) => cached || fetch(event.request))
    )
  }
  // 其他请求不拦截
})
