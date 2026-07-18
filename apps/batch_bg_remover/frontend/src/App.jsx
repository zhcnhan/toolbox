import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import SettingsPanel from './components/SettingsPanel';
import DropZone from './components/DropZone';
import ImageGrid from './components/ImageGrid';
import PromptPanel from './components/PromptPanel';
import { fetchEngines, uploadImages, removeBg, removeBgWithPrompt, getDownloadUrl, getDownloadZipUrl, getProxyConfig, updateProxyConfig } from './api';

/**
 * App.jsx — Batch Background Remover 主应用
 *
 * 流程：
 *   1. 设置页：选引擎、填 API Key
 *   2. 拖放上传图片
 *   3. 批量自动抠图
 *   4. 对不满意的图片用提示词重新抠
 *   5. 一键下载 ZIP
 */

const STORAGE_KEY = 'bg_remover_settings';

function loadSettings() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveSettings(settings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

export default function App() {
  // 引擎 & 设置
  const [engines, setEngines] = useState([]);
  const [settings, setSettings] = useState(loadSettings);
  const [showSettings, setShowSettings] = useState(false);

  // 上传的图片
  const [uploadedFiles, setUploadedFiles] = useState([]);  // { file_id, filename, size }

  // 处理结果
  const [results, setResults] = useState([]);  // { file_id, filename, result_id, status, error }
  const [processing, setProcessing] = useState(false);

  // 提示词修正
  const [promptTarget, setPromptTarget] = useState(null);  // 正在修正的图片

  // 代理配置（从服务器加载，持久化在服务端）
  const [proxyConfig, setProxyConfig] = useState({ enabled: false, url: '', auth_type: 'none', username: '', password: '' });

  // 加载引擎列表和代理配置
  useEffect(() => {
    fetchEngines().then(setEngines).catch(console.error);
    getProxyConfig().then(setProxyConfig).catch(() => {}); // 代理配置加载失败不影响使用
  }, []);

  // 保存代理配置到服务器
  const handleProxySave = useCallback(async (enabled, url, authType = 'none', username = '', password = '') => {
    const result = await updateProxyConfig(enabled, url, authType, username, password);
    setProxyConfig(result.config);
  }, []);

  // 保存设置
  useEffect(() => {
    saveSettings(settings);
  }, [settings]);

  const updateSetting = useCallback((key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  }, []);

  const getApiKey = useCallback((engineId) => {
    return settings[`key_${engineId}`] || '';
  }, [settings]);

  // 获取引擎的额外配置参数
  const getEngineExtra = useCallback((engineId) => {
    const extra = {};
    if (engineId === 'custom') {
      extra.base_url = settings.custom_base_url || '';
      extra.model_name = settings.custom_model_name || '';
    }
    // CLIPSeg 灵敏度
    if (engineId === 'clipseg_local' && settings.clipseg_sensitivity !== undefined) {
      extra.sensitivity = settings.clipseg_sensitivity;
    }
    return extra;
  }, [settings]);

  const getActiveEngine = useCallback((mode) => {
    // mode: 'auto' | 'prompt'
    const key = mode === 'auto' ? 'auto_engine' : 'prompt_engine';
    if (settings[key]) return settings[key];

    // 没有保存的设置时，从已加载的引擎中选一个支持该模式的
    if (engines.length === 0) return 'rembg_local';
    const supportKey = mode === 'auto' ? 'supports_auto' : 'supports_prompt';
    const candidates = engines.filter(e => e[supportKey]);
    if (candidates.length === 0) return 'rembg_local';
    // 优先本地引擎，其次云端
    const local = candidates.find(e => e.type === 'local');
    return (local || candidates[0]).id;
  }, [settings, engines]);

  // 上传图片
  const handleFilesDrop = useCallback(async (files) => {
    try {
      const uploaded = await uploadImages(files);
      setUploadedFiles(prev => [...prev, ...uploaded]);
    } catch (e) {
      alert('上传失败: ' + e.message);
    }
  }, []);

  // 批量自动抠图
  const handleRemoveAll = useCallback(async () => {
    if (uploadedFiles.length === 0) return;

    const engineId = getActiveEngine('auto');
    const apiKey = getApiKey(engineId);
    const extra = getEngineExtra(engineId);

    // 检查云端引擎是否填了 Key
    const engine = engines.find(e => e.id === engineId);
    if (engine && engine.needs_api_key && !apiKey) {
      alert(`使用 ${engine.name} 需要填写 API Key，请在设置中配置`);
      return;
    }
    // 自定义引擎检查 URL 和模型名
    if (engineId === 'custom') {
      if (!extra.base_url) { alert('请在设置中填写自定义引擎的 API 地址'); return; }
      if (!extra.model_name) { alert('请在设置中填写自定义引擎的模型名称'); return; }
    }

    setProcessing(true);

    const newResults = [];
    for (const file of uploadedFiles) {
      // 标记为处理中
      setResults(prev => [...prev, { file_id: file.file_id, filename: file.filename, status: 'processing' }]);

      try {
        const res = await removeBg(file.file_id, engineId, apiKey, extra);
        newResults.push({ file_id: file.file_id, filename: file.filename, result_id: res.result_id, status: 'done' });
        // 更新结果（移除 processing 状态）
        setResults(prev => {
          const filtered = prev.filter(r => r.file_id !== file.file_id);
          return [...filtered, { file_id: file.file_id, filename: file.filename, result_id: res.result_id, status: 'done' }];
        });
      } catch (e) {
        newResults.push({ file_id: file.file_id, filename: file.filename, status: 'error', error: e.message });
        setResults(prev => {
          const filtered = prev.filter(r => r.file_id !== file.file_id);
          return [...filtered, { file_id: file.file_id, filename: file.filename, status: 'error', error: e.message }];
        });
      }
    }

    setProcessing(false);
  }, [uploadedFiles, getActiveEngine, getApiKey, getEngineExtra, engines]);

  // 单张提示词修正
  const handlePromptRemove = useCallback(async (fileId, prompt) => {
    const engineId = getActiveEngine('prompt');
    const apiKey = getApiKey(engineId);
    const extra = getEngineExtra(engineId);
    const file = uploadedFiles.find(f => f.file_id === fileId);
    if (!file) return;

    // 检查引擎是否支持提示词分割
    const engine = engines.find(e => e.id === engineId);
    if (engine && !engine.supports_prompt) {
      alert(`引擎 "${engine.name}" 不支持提示词分割，请在设置中选择 CLIPSeg / Gemini / Replicate / 自定义`);
      return;
    }
    // 云端引擎检查 API Key
    if (engine && engine.needs_api_key && !apiKey) {
      alert(`使用 ${engine.name} 需要填写 API Key，请在设置中配置`);
      return;
    }
    // 自定义引擎检查 URL 和模型名
    if (engineId === 'custom') {
      if (!extra.base_url) { alert('请在设置中填写自定义引擎的 API 地址'); return; }
      if (!extra.model_name) { alert('请在设置中填写自定义引擎的模型名称'); return; }
    }

    // 标记为处理中
    setResults(prev => {
      const filtered = prev.filter(r => r.file_id !== fileId);
      return [...filtered, { file_id: fileId, filename: file.filename, status: 'processing' }];
    });

    try {
      const res = await removeBgWithPrompt(fileId, engineId, prompt, apiKey, extra);
      setResults(prev => {
        const filtered = prev.filter(r => r.file_id !== fileId);
        return [...filtered, { file_id: fileId, filename: file.filename, result_id: res.result_id, status: 'done' }];
      });
    } catch (e) {
      setResults(prev => {
        const filtered = prev.filter(r => r.file_id !== fileId);
        return [...filtered, { file_id: fileId, filename: file.filename, status: 'error', error: e.message }];
      });
    } finally {
      setPromptTarget(null);
    }
  }, [uploadedFiles, getActiveEngine, getApiKey, getEngineExtra, engines]);

  // 下载
  const doneResults = results.filter(r => r.status === 'done');

  const handleDownloadAll = useCallback(() => {
    if (doneResults.length === 0) return;
    const ids = doneResults.map(r => r.result_id);
    window.open(getDownloadZipUrl(ids), '_blank');
  }, [doneResults]);

  // 重置
  const handleReset = useCallback(() => {
    setUploadedFiles([]);
    setResults([]);
    setPromptTarget(null);
  }, []);

  return (
    <div className="min-h-screen p-4 md:p-8 max-w-6xl mx-auto">
      {/* Header */}
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-8 pt-4"
      >
        <h1 className="text-3xl md:text-4xl font-bold mb-2">
          <span className="bg-gradient-to-r from-accent-pink via-accent-purple to-accent-blue bg-clip-text text-transparent">
            ✂️ 批量抠图
          </span>
        </h1>
        <p className="text-white/40 text-sm">
          本地 & 云端双模式 · 自动抠图 + 提示词修正 · 一键打包下载
        </p>
      </motion.header>

      {/* Settings Toggle */}
      <div className="flex justify-center gap-3 mb-6">
        <button
          className={`btn-secondary text-sm ${showSettings ? 'border-accent-purple bg-accent-purple/10' : ''}`}
          onClick={() => setShowSettings(!showSettings)}
        >
          ⚙️ {showSettings ? '收起设置' : '引擎设置'}
        </button>
        <button
          className="btn-primary text-sm"
          onClick={handleRemoveAll}
          disabled={uploadedFiles.length === 0 || processing}
        >
          {processing ? (
            <span className="flex items-center gap-2">
              <span className="animate-spin">⏳</span> 抠图中...
            </span>
          ) : (
            '🚀 一键全部抠图'
          )}
        </button>
        {doneResults.length > 0 && (
          <button className="btn-secondary text-sm" onClick={handleDownloadAll}>
            📦 打包下载 ({doneResults.length}张)
          </button>
        )}
        {uploadedFiles.length > 0 && !processing && (
          <button className="btn-secondary text-sm opacity-60 hover:opacity-100" onClick={handleReset}>
            🔄 重新开始
          </button>
        )}
      </div>

      {/* Settings Panel */}
      <AnimatePresence>
        {showSettings && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden mb-6"
          >
            <SettingsPanel
              engines={engines}
              settings={settings}
              onUpdate={updateSetting}
              proxyConfig={proxyConfig}
              onProxySave={handleProxySave}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Drop Zone */}
      <DropZone onFilesDrop={handleFilesDrop} disabled={processing} />

      {/* Image Grid */}
      {uploadedFiles.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-6"
        >
          <ImageGrid
            files={uploadedFiles}
            results={results}
            onPromptFix={setPromptTarget}
            getDownloadUrl={getDownloadUrl}
          />
        </motion.div>
      )}

      {/* Prompt Panel */}
      <AnimatePresence>
        {promptTarget && (
          <PromptPanel
            file={uploadedFiles.find(f => f.file_id === promptTarget)}
            onSubmit={(prompt) => handlePromptRemove(promptTarget, prompt)}
            onCancel={() => setPromptTarget(null)}
          />
        )}
      </AnimatePresence>

      {/* Footer */}
      <footer className="text-center mt-12 pb-6 text-white/20 text-xs">
        Batch Background Remover · 本地模型 + 云端 API · 图片不会上传至第三方服务器
      </footer>
    </div>
  );
}
