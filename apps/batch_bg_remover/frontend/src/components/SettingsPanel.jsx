import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

/**
 * SettingsPanel.jsx — 引擎设置面板
 * 用户在此：
 *   1. 选择自动抠图引擎
 *   2. 选择提示词分割引擎
 *   3. 填写各引擎的 API Key
 */

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
        <span>⚙️</span> 引擎设置
      </h2>

      <div className="grid md:grid-cols-2 gap-6">
        {/* 自动抠图引擎 */}
        <div>
          <h3 className="text-sm font-semibold text-white/60 mb-3 uppercase tracking-wide">
            🎯 自动抠图引擎
          </h3>
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
          <h3 className="text-sm font-semibold text-white/60 mb-3 uppercase tracking-wide">
            ✂️ 提示词分割引擎
          </h3>
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
function QuotaBadge() {
  const [quota, setQuota] = useState(null);

  useEffect(() => {
    fetch('/api/engine/gemini/quota')
      .then(r => r.ok ? r.json() : null)
      .then(d => setQuota(d))
      .catch(() => setQuota(null));
    // 每 30 秒刷新一次
    const iv = setInterval(() => {
      fetch('/api/engine/gemini/quota')
        .then(r => r.ok ? r.json() : null)
        .then(d => setQuota(d))
        .catch(() => {});
    }, 30000);
    return () => clearInterval(iv);
  }, []);

  if (!quota) return null;

  const pct = quota.rpd_limit > 0
    ? Math.round(quota.rpd_remaining / quota.rpd_limit * 100)
    : 0;

  let color;
  if (pct > 30) color = 'text-emerald-400';
  else if (pct > 10) color = 'text-yellow-400';
  else color = 'text-red-400';

  return (
    <div className="flex items-center gap-1.5 mt-1.5">
      <span className="text-xs text-white/30">📊</span>
      <span className={`text-xs ${color}`}>
        今日剩余 {quota.rpd_remaining}/{quota.rpd_limit}
      </span>
      {pct <= 10 && (
        <span className="text-xs text-red-400/60">⚠️ 即将用完</span>
      )}
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
            <div className="font-semibold text-sm">{engine.name}</div>
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

      {/* Gemini 配额信息 */}
      {isGemini && isActive && <QuotaBadge />}

      {/* CLIPSeg 灵敏度滑块 */}
      {engine.id === 'clipseg_local' && isActive && (
        <div className="mt-3" onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs text-white/50">抠图灵敏度</label>
            <span className="text-xs text-white/30">{settings.clipseg_sensitivity ?? 0.5}</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            className="w-full h-1.5 rounded-full appearance-none cursor-pointer bg-white/10 accent-accent-blue"
            style={{ background: `linear-gradient(to right, #3b82f6 ${(settings.clipseg_sensitivity ?? 0.5) * 100}%, rgba(255,255,255,0.1) ${(settings.clipseg_sensitivity ?? 0.5) * 100}%)` }}
            value={settings.clipseg_sensitivity ?? 0.5}
            onChange={(e) => {
              const val = parseFloat(e.target.value);
              onUpdate('clipseg_sensitivity', val);
              e.target.style.background = `linear-gradient(to right, #3b82f6 ${val * 100}%, rgba(255,255,255,0.1) ${val * 100}%)`;
            }}
          />
          <div className="flex justify-between text-xs text-white/20 mt-0.5">
            <span>宽松</span>
            <span>默认</span>
            <span>严格</span>
          </div>
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

  const handleSave = () => {
    onProxySave({ enabled, url, auth_type: authType, username, password });
  };

  return (
    <div className="mt-6 p-4 glass-light">
      <h3 className="text-sm font-semibold text-white/60 mb-3 uppercase tracking-wide">
        🌐 代理配置
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

        <button
          className="btn-primary text-sm w-full"
          onClick={handleSave}
        >
          保存代理配置
        </button>
      </div>
    </div>
  );
}
