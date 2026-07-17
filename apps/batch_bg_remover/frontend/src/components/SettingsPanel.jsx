import { motion } from 'framer-motion';

/**
 * SettingsPanel.jsx — 引擎设置面板
 * 用户在此：
 *   1. 选择自动抠图引擎
 *   2. 选择提示词分割引擎
 *   3. 填写各引擎的 API Key
 */

export default function SettingsPanel({ engines, settings, onUpdate }) {
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
