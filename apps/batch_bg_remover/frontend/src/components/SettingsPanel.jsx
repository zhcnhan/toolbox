import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';

/**
 * SettingsPanel.jsx — 引擎设置面板
 * 用户在此：
 *   1. 选择自动抠图引擎
 *   2. 选择提示词分割引擎
 *   3. 填写各引擎的 API Key
 */

// ── 小白引导提示（给妮妮的专属说明） ──────────────────────────
const ENGINE_TIPS = {
  rembg_local:
    '🎈 这个最厉害啦！不用联网、不用Key、不用花钱！\n把图片拖进来它就自己帮你把背景去掉啦～ 适合抠普通照片、人物、物品，啥都能抠！',
  icon_bg:
    '🎨 这个是专门用来抠图标的！\n如果你的图片背景是纯白色或者纯黑色的图标/Logo/按钮，就用这个，又快又好！',
  sam_local:
    '🤖 这个最聪明了，能认出图片里有什么东西。\n但是它需要一个 1.2GB 的大脑（模型文件），第一次用的时候要下载一下。\n等下载完了之后，连头发丝都能抠干净！',
  gemini_mask:
    '☁️ 这个需要找开发者要一个叫 API Key 的东西才能用哦。\n它是 Google 家的 AI，会把你的图片发到 Google 去处理。\n按次数收费的，省着点用～',
  remove_bg:
    '☁️ 这个是另一个云端引擎，也需要 API Key。\n它是专门做抠图的网站，抠人像效果很好，但也要花钱的。',
  kimi:
    '☁️ 月之暗面的 Kimi AI，也需要 Key。\n适合抠一些小的物体，比如杯子、手机、玩具这种。\n也是按次数收费的～',
  custom:
    '🔧 这个是给开发者调试用的，可以连接各种 AI 接口。\n妮妮用不到这个～',
  gemini:
    '☁️ Google 的 Gemini AI，需要 API Key。\n跟上面的 Gemini Mask 一样，只是这个模式不一样。',
};

// ── 引擎模式下对妮妮不友好的警告 ───────────────────────────
const ENGINE_MODE_WARNINGS = {
  gemini_mask_polygon: (
    <div className="text-[11px] text-amber-300/80 bg-amber-500/10 p-2 rounded-lg mt-2 leading-relaxed">
      ⚠️ 妮妮注意：这个「坐标模式」是让 AI 自己猜要抠哪里，但 AI 猜得不准！<br />
      经常抠出来乱七八糟的。建议不要用这个模式哦～<br />
      用上面那个「掩膜 PNG」模式效果会好很多，但需要 Key 绑卡才能用。<br />
      所以妮妮还是用最上面那个自动的 <b>rembg</b> 吧！又快又好！
    </div>
  ),
  kimi_coords: (
    <div className="text-[11px] text-amber-300/80 bg-amber-500/10 p-2 rounded-lg mt-2 leading-relaxed">
      ⚠️ 妮妮注意：Kimi 的坐标模式也是一样的情况～<br />
      AI 画出来的框经常歪歪扭扭的，效果不太稳定。<br />
      可以试试看，但如果不好看不要失望哦，换回 rembg 就好啦！🐣
    </div>
  ),
};


export default function SettingsPanel({ engines, settings, onUpdate, proxyConfig, onProxySave }) {
  const autoEngines = engines.filter(e => e.supports_auto);
  const promptEngines = engines.filter(e => e.supports_prompt);

  // 从已加载引擎中选默认值（避免选了不存在的引擎）
  const firstAuto = autoEngines[0]?.id || 'rembg_local';
  const firstPrompt = promptEngines[0]?.id || 'rembg_local';
  const activeAuto = settings.auto_engine || firstAuto;
  const activePrompt = settings.prompt_engine || firstPrompt;

  return (
    <div className="glass p-6">
      <h2 className="text-lg font-bold mb-5 flex items-center gap-2">
        <span>🎀</span> 选一个工具吧~
      </h2>

      <div className="grid md:grid-cols-2 gap-6">
        {/* 自动抠图引擎 */}
        <div>
          <h3 className="text-sm font-semibold text-pink-300/60 mb-3 tracking-wide">
            🎯 选一个来自动抠图
          </h3>
          <p className="text-xs text-pink-300/30 mb-3 -mt-2">鼠标在名字上停一下，会告诉你怎么用的～</p>
          <div className="space-y-2">
            {autoEngines.map((engine) => (
              <EngineCard
                key={engine.id}
                engine={engine}
                isActive={activeAuto === engine.id}
                onSelect={() => onUpdate('auto_engine', engine.id)}
                apiKey={settings[`key_${engine.id}`] || ''}
                onApiKeyChange={(val) => onUpdate(`key_${engine.id}`, val)}
                settings={settings}
                onUpdate={onUpdate}
                group="auto"
              />
            ))}
          </div>
        </div>

        {/* 提示词分割引擎 */}
        <div>
          <h3 className="text-sm font-semibold text-pink-300/60 mb-3 tracking-wide">
            ✂️ 选一个来修图（用文字告诉它要扣啥）
          </h3>
          <p className="text-xs text-pink-300/30 mb-3 -mt-2">比如在框框里写「把小猫抠出来」</p>
          <div className="space-y-2">
            {promptEngines.map((engine) => (
              <EngineCard
                key={engine.id}
                engine={engine}
                isActive={activePrompt === engine.id}
                onSelect={() => onUpdate('prompt_engine', engine.id)}
                apiKey={settings[`key_${engine.id}`] || ''}
                onApiKeyChange={(val) => onUpdate(`key_${engine.id}`, val)}
                settings={settings}
                onUpdate={onUpdate}
                group="prompt"
              />
            ))}
          </div>
        </div>
      </div>

      {/* 代理配置 */}
      <ProxySettings proxyConfig={proxyConfig} onProxySave={onProxySave} />
    </div>
  );
}

// ── 配额显示组件 ──────────────────────────────────────────────
function QuotaBadge({ apiKey }) {
  const [data, setData] = useState(null);

  const fetchUsage = useCallback(async () => {
    if (!apiKey) return;
    try {
      const form = new FormData();
      form.append('api_key', apiKey);
      const res = await fetch('/api/engine/gemini/usage', { method: 'POST', body: form });
      const json = await res.json();
      setData(json.usage || null);
    } catch {}
  }, [apiKey]);

  useEffect(() => { fetchUsage(); }, [fetchUsage]);

  if (!data || !apiKey) return null;

  const { rpd_used, rpm_current, rpm_range } = data;
  const rpm_max = rpm_range ? rpm_range[1] : '?';

  // 根据使用量着色：少=绿，多=黄，很多=红
  let color = 'text-emerald-400';
  if (rpd_used > 100) color = 'text-yellow-400';
  if (rpd_used > 300) color = 'text-red-400';

  return (
    <div className="flex items-center gap-1.5 mt-1.5">
      <span className="text-xs text-white/30">📊</span>
      <span className={`text-xs ${color}`}>
        今日已使用 {rpd_used} 次
      </span>
      <span className="text-xs text-white/20">
        | {rpm_current}/{rpm_max} RPM
      </span>
      <a
        href="https://aistudio.google.com/rate-limit"
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs text-accent-blue/60 hover:text-accent-blue"
      >
        查看配额 →
      </a>
    </div>
  );
}

// ── 引擎卡片 ──────────────────────────────────────────────────
function EngineCard({ engine, isActive, onSelect, apiKey, onApiKeyChange, settings, onUpdate, group }) {
  const isGemini = engine.id === 'gemini' || engine.id === 'gemini_mask';

  return (
    <motion.div
      whileHover={{ scale: 1.01 }}
      className={`glass-light p-4 cursor-pointer transition-all ${
        isActive ? 'border-accent-purple bg-accent-purple/5' : ''
      }`}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">{engine.icon}</span>
          <div>
            <div className="font-semibold text-sm flex items-center gap-1">
              {engine.name}
              {/* 悬浮提示图标 */}
              <span className="group relative inline-flex">
                <span className="text-xs text-pink-300/40 cursor-help hover:text-pink-300/70 transition">💡</span>
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2
                             hidden group-hover:block whitespace-pre-line
                             px-4 py-3 rounded-2xl text-xs text-pink-100
                             bg-purple-900/95 backdrop-blur shadow-xl z-50
                             min-w-[260px] leading-relaxed pointer-events-none">
                  {ENGINE_TIPS[engine.id] || '把这个图片拖进来试试看～'}
                  <div className="absolute top-full left-1/2 -translate-x-1/2
                                  border-4 border-transparent border-t-purple-900/95" />
                </div>
              </span>
            </div>
            <span className={`tag ${engine.type === 'local' ? 'tag-local' : 'tag-cloud'}`}>
              {engine.type === 'local' ? '本地' : '云端'}
            </span>
          </div>
        </div>
        <div onClick={(e) => e.stopPropagation()}>
          <label className="toggle">
            <input
              type="radio"
              name={`engine_${group}`}
              checked={isActive}
              onChange={onSelect}
            />
            <span className="slider"></span>
          </label>
        </div>
      </div>

      <p className="text-white/40 text-xs leading-relaxed">{engine.description}</p>

      {/* Gemini 配额信息（按 API Key 独立追踪） */}
      {isGemini && isActive && <QuotaBadge apiKey={apiKey} />}

      {/* Kimi 精细度滑块 */}
      {engine.id === 'kimi' && isActive && (
        <div className="mt-3" onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs text-white/50">轮廓精细度</label>
            <span className="text-xs text-white/30">{settings.kimi_num_points || 100} 点</span>
          </div>
          <input
            type="range"
            min="15"
            max="500"
            step="5"
            className="w-full h-1.5 rounded-full appearance-none cursor-pointer bg-white/10 accent-accent-pink"
            style={{ background: `linear-gradient(to right, #f472b6 ${((settings.kimi_num_points || 100) - 15) / 485 * 100}%, rgba(255,255,255,0.1) ${((settings.kimi_num_points || 100) - 15) / 485 * 100}%)` }}
            value={settings.kimi_num_points || 100}
            onChange={(e) => {
              const val = parseInt(e.target.value);
              onUpdate('kimi_num_points', val);
              e.target.style.background = `linear-gradient(to right, #f472b6 ${(val - 15) / 485 * 100}%, rgba(255,255,255,0.1) ${(val - 15) / 485 * 100}%)`;
            }}
          />
          <div className="flex justify-between text-xs text-white/20 mt-0.5">
            <span>粗糙 (15)</span>
            <span>推荐 (100)</span>
            <span>精细 (500)</span>
          </div>
          {ENGINE_MODE_WARNINGS.kimi_coords}
        </div>
      )}

      {/* Gemini Mask 模式切换 */}
      {engine.id === 'gemini_mask' && isActive && (
        <div className="mt-3" onClick={(e) => e.stopPropagation()}>
          <label className="text-xs text-white/50 block mb-1">选一个模式</label>
          <div className="flex gap-2">
            <button
              className={`flex-1 px-3 py-1.5 rounded-lg text-xs transition ${
                (settings.mask_mode || 'polygon') === 'mask'
                  ? 'bg-accent-pink/20 text-accent-pink'
                  : 'bg-white/5 text-white/40 hover:bg-white/10'
              }`}
              onClick={() => onUpdate('mask_mode', 'mask')}
            >
              🖼️ 掩膜 PNG
              <span className="block text-[10px] text-pink-300/40">效果好，但需要 Key 绑卡</span>
            </button>
            <button
              className={`flex-1 px-3 py-1.5 rounded-lg text-xs transition ${
                (settings.mask_mode || 'polygon') === 'polygon'
                  ? 'bg-accent-pink/20 text-accent-pink'
                  : 'bg-white/5 text-white/40 hover:bg-white/10'
              }`}
              onClick={() => onUpdate('mask_mode', 'polygon')}
            >
              📐 坐标模式
              <span className="block text-[10px] text-amber-300/50">⚠️ 不太准，试试看就好</span>
            </button>
          </div>
          {(!settings.mask_mode || settings.mask_mode === 'polygon') && ENGINE_MODE_WARNINGS.gemini_mask_polygon}
        </div>
      )}

      {engine.needs_api_key && isActive && (
        <div className="mt-3" onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs text-white/50">{engine.api_key_label}</label>
            {engine.api_key_help_url && (
              <a
                href={engine.api_key_help_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-accent-blue hover:underline"
              >
                获取 Key →
              </a>
            )}
          </div>
          <input
            type="password"
            className="input-field text-sm"
            placeholder="粘贴 API Key..."
            value={apiKey}
            onChange={(e) => onApiKeyChange(e.target.value)}
          />

          {/* 自定义引擎额外字段 */}
          {engine.id === 'custom' && (
            <div className="mt-2 space-y-2">
              <div>
                <label className="text-xs text-white/50 block mb-1">API 地址 (Base URL)</label>
                <input
                  type="text"
                  className="input-field text-sm"
                  placeholder="如: https://generativelanguage.googleapis.com/v1beta"
                  value={settings.custom_base_url || ''}
                  onChange={(e) => onUpdate('custom_base_url', e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs text-white/50 block mb-1">模型名称</label>
                <input
                  type="text"
                  className="input-field text-sm"
                  placeholder="如: gemini-2.5-flash-image"
                  value={settings.custom_model_name || ''}
                  onChange={(e) => onUpdate('custom_model_name', e.target.value)}
                />
              </div>
              <p className="text-white/30 text-xs leading-relaxed mt-2">
                已支持 API 风格：<br/>
                · <b>Gemini</b>（googleapis.com，?key= 鉴权）<br/>
                · <b>硅基流动 SiliconFlow</b>（/images/generations，Bearer Token）<br/>
                · <b>OpenAI 兼容</b>（/chat/completions，Bearer Token）<br/>
              </p>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}

// ── 代理配置组件 ──────────────────────────────────────────────
function ProxySettings({ proxyConfig, onProxySave }) {
  const [enabled, setEnabled] = useState(proxyConfig.enabled || false);
  const [url, setUrl] = useState(proxyConfig.url || '');
  const [authType, setAuthType] = useState(proxyConfig.auth_type || 'none');
  const [username, setUsername] = useState(proxyConfig.username || '');
  const [password, setPassword] = useState(proxyConfig.password || '');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null); // {success, latency_ms, error}

  const handleSave = () => {
    onProxySave({ enabled, url, auth_type: authType, username, password });
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    const form = new FormData();
    if (url) {
      form.append('url', url);
      form.append('auth_type', authType);
      form.append('username', username);
      form.append('password', password);
    }
    try {
      const res = await fetch('/api/proxy/test', { method: 'POST', body: form });
      const data = await res.json();
      setTestResult(data);
    } catch (e) {
      setTestResult({ success: false, error: e.message });
    }
    setTesting(false);
  };

  return (
    <div className="mt-6 p-4 glass-light">
      <h3 className="text-sm font-semibold text-pink-300/60 mb-3 tracking-wide">
        🌐 网络设置（一般用不到，需要的话找开发者）
      </h3>
      <div className="space-y-3">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="accent-accent-blue"
          />
          <span className={enabled ? 'text-white' : 'text-white/30'}>启用代理</span>
        </label>

        <input
          type="text"
          className="input-field text-sm"
          placeholder="http://127.0.0.1:7890"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={!enabled}
        />

        <select
          className="input-field text-sm"
          value={authType}
          onChange={(e) => setAuthType(e.target.value)}
          disabled={!enabled}
        >
          <option value="none">无认证</option>
          <option value="basic">Basic 认证</option>
        </select>

        {authType === 'basic' && (
          <div className="grid grid-cols-2 gap-2">
            <input
              type="text"
              className="input-field text-sm"
              placeholder="用户名"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <input
              type="password"
              className="input-field text-sm"
              placeholder="密码"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
        )}

        {/* 测试结果 */}
        {testResult && (
          <div className="space-y-1.5">
            <div className={`text-xs p-2 rounded-lg ${testResult.success ? 'bg-emerald-500/10' : 'bg-red-500/10'}`}>
              <div className={testResult.success ? 'text-emerald-400' : 'text-red-400'}>
                {testResult.summary}
              </div>
            </div>
            {testResult.results && testResult.results.map((r, i) => (
              <div key={i} className={`flex items-center justify-between text-xs px-2 py-1 rounded ${r.ok ? 'bg-emerald-500/5' : 'bg-red-500/5'}`}>
                <span className="text-white/60">{r.url.replace('https://', '')}</span>
                <span className={r.ok ? 'text-emerald-400' : 'text-red-400'}>
                  {r.ok
                    ? `${r.latency_ms}ms`
                    : r.error.split(':')[1]?.trim()?.slice(0, 20) || '不通'
                  }
                </span>
              </div>
            ))}
          </div>
        )}

        <div className="flex gap-2">
          <button
            className="flex-1 px-3 py-2 bg-white/5 text-white/60 rounded-xl text-sm hover:bg-white/10 transition disabled:opacity-30"
            onClick={handleTest}
            disabled={!enabled || !url || testing}
          >
            {testing ? '测试中...' : '测试代理'}
          </button>
          <button
            className="flex-1 btn-primary text-sm"
            onClick={handleSave}
          >
            保存配置
          </button>
        </div>
      </div>
    </div>
  );
}
