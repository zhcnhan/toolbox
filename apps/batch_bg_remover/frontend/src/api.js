/**
 * api.js — 后端 API 客户端
 */

const BASE = '/api';

export async function fetchEngines() {
  const res = await fetch(`${BASE}/engines`);
  if (!res.ok) throw new Error('获取引擎列表失败');
  const data = await res.json();
  return data.engines;
}

export async function uploadImages(files) {
  const form = new FormData();
  for (const f of files) {
    form.append('files', f);
  }
  const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form });
  if (!res.ok) throw new Error('上传失败');
  const data = await res.json();
  return data.files;
}

export async function removeBg(fileId, engineId, apiKey, extra = {}) {
  const form = new FormData();
  form.append('file_id', fileId);
  form.append('engine_id', engineId);
  if (apiKey) form.append('api_key', apiKey);
  if (extra.base_url) form.append('base_url', extra.base_url);
  if (extra.model_name) form.append('model_name', extra.model_name);

  const res = await fetch(`${BASE}/remove-bg`, { method: 'POST', body: form });
  if (!res.ok) {
    let msg = '抠图失败';
    try {
      const err = await res.json();
      msg = err.detail || msg;
    } catch { /* response body not JSON */ }
    throw new Error(msg);
  }
  return await res.json();
}

export async function removeBgWithPrompt(fileId, engineId, prompt, apiKey, extra = {}) {
  const form = new FormData();
  form.append('file_id', fileId);
  form.append('engine_id', engineId);
  form.append('prompt', prompt);
  if (apiKey) form.append('api_key', apiKey);
  if (extra.base_url) form.append('base_url', extra.base_url);
  if (extra.model_name) form.append('model_name', extra.model_name);

  const res = await fetch(`${BASE}/remove-bg-prompt`, { method: 'POST', body: form });
  if (!res.ok) {
    let msg = '提示词抠图失败';
    try {
      const err = await res.json();
      msg = err.detail || msg;
    } catch { /* response body not JSON */ }
    throw new Error(msg);
  }
  return await res.json();
}

export function getDownloadUrl(resultId) {
  return `${BASE}/download/${resultId}`;
}

export function getDownloadZipUrl(resultIds) {
  return `${BASE}/download-zip?result_ids=${resultIds.join(',')}`;
}

export async function getProxyConfig() {
  const res = await fetch(`${BASE}/proxy`);
  if (!res.ok) throw new Error('获取代理配置失败');
  return await res.json();
}

export async function updateProxyConfig(enabled, url) {
  const form = new FormData();
  form.append('enabled', enabled);
  form.append('url', url);
  const res = await fetch(`${BASE}/proxy`, { method: 'PUT', body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || '保存代理配置失败');
  }
  return await res.json();
}
