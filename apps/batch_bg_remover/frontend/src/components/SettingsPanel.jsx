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
            ✨ 提示词分割引擎
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

      {/* 代理设置 */}
      <div className="mt-6 pt-5 border-t border-white/10">
        <ProxySettings proxyConfig={proxyConfig} onProxySave={onProxySave} />
      </div>
    </div>
  );
}

function ProxySettings({ proxyConfig, onProxySave }) {
  const [editing, setEditing] = useState(false);
  const [url, setUrl] = useState(proxyConfig?.url || '');
  const [enabled, setEnabled] = useState(proxyConfig?.enabled || false);
  const [saving, setSaving] = useState(false);

  // 当外部 proxyConfig 变化时同步
  useEffect(() => {
    setUrl(proxyConfig?.url || '');
    setEnabled(proxyConfig?.enabled || false);
  }, [proxyConfig]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onProxySave(enabled, url);
      setEditing(false);
    } catch (e) {
      alert('保存失败: ' + e.message);
    } finally {
      setSaving(false);
    }
  };

  if (!editing) {
    return (
      <div className="flex items-center justify-between">
        <div>
          <span className="text-sm font-semibold text-white/60">🔗 代理设置</span>
          <span className="ml-2 text-xs text-white/30">
            {proxyConfig?.enabled && proxyConfig?.url
              ? `已启用 · ${proxyConfig.url}`
              : '未启用（直连）'}
          </span>
        </div>
        <button
          className="text-xs text-accent-blue hover:underline"
          onClick={() => setEditing(true)}
        >
          配置 →
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold text-white/60">🔗 代理设置</span>
        <button
          className="text-xs text-white/30 hover:text-white/60"
          onClick={() => setEditing(false)}
        >
          取消
        </button>
      </div>

      <div className="p-4 glass-light space-y-3">
        {/* 启用开关 */}
        <label className="flex items-center justify-between">
          <span className="text-sm text-white/70">启用代理</span>
          <div className="toggle" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
            />
            <span className="slider"></span>
          </div>
        </label>

        {/* 代理地址 */}
        <div>
          <label className="text-xs text-white/50 block mb-1">代理地址</label>
          <input
            type="text"
            className="input-field text-sm"
            placeholder="如: http://127.0.0.1:7890"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={!enabled}
          />
        </div>

        <p className="text-white/30 text-xs leading-relaxed">
          针对服务器部署场景：部分云服务器可能限制访问国外 API，可通过 HTTP 代理转发流量。支持 Clash / V2Ray 等本地代理。
        </p>

        <button
          className="btn-primary text-sm w-full"
          onClick={handleSave}
          disabled={saving || (enabled && !url)}
        >
          {saving ? '保存中...' : '保存'}
        </button>
      </div>
    </div>
  );
}


function EngineCard({ engine, isActive, onSelect, apiKey, onApiKeyChange, settings, onUpdate, group }) {
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
              <div className="mt-3 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                <p className="text-yellow-400/80 text-xs leading-relaxed font-medium">
                  ⚠️ 重要：模型必须支持「图像分割/抠图」功能
                </p>
                <p className="text-yellow-400/60 text-xs leading-relaxed mt-1">
                  文生图/图生图模型（如 FLUX、Stable Diffusion、Qwen-Image-Edit）会根据提示词<b>画新图</b>，不能用于抠图。只有能输出透明背景或分割 mask 的模型才行。
                </p>
              </div>
              <p className="text-white/30 text-xs leading-relaxed mt-2">
                已支持 API 风格：<br/>
                · <b>Gemini</b>（googleapis.com，?key= 鉴权）<br/>
                · <b>硅基流动 SiliconFlow</b>（/images/generations，Bearer Token）<br/>
                · <b>OpenAI 兼容</b>（/chat/completions，Bearer Token）<br/>
                系统会根据 URL 和模型名自动判断风格。
              </p>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}
