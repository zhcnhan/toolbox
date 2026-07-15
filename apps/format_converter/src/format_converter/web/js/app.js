/**
 * Format Converter — Frontend Application
 * Vanilla JS · No framework · Clean architecture
 */

// ═══════════════════════════════════════════════════
// State
// ═══════════════════════════════════════════════════

const state = {
    category: "data",
    formats: {},           // { data: {inputs:[], outputs:[]}, ... }
    files: [],             // [{path, name}]
    selectedFiles: new Set(),
    taskId: null,
    pollingTimer: null,
    converting: false,
};

// ═══════════════════════════════════════════════════
// DOM Refs
// ═══════════════════════════════════════════════════

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
    tabBtns: () => $$(".tab-btn"),
    srcFormat: $("#srcFormat"),
    dstFormat: $("#dstFormat"),
    outputDir: $("#outputDir"),
    dropZone: $("#dropZone"),
    fileList: $("#fileList"),
    fileCount: $("#fileCount"),
    btnConvert: $("#btnConvert"),
    btnCancel: $("#btnCancel"),
    progressSection: $("#progressSection"),
    overallFill: $("#overallFill"),
    fileFill: $("#fileFill"),
    progressPercent: $("#progressPercent"),
    currentFile: $("#currentFile"),
    logOutput: $("#logOutput"),
    statusDot: $("#statusDot"),
    statusText: $("#statusText"),
    formatInfo: $("#formatInfo"),
};

// ═══════════════════════════════════════════════════
// API Helpers
// ═══════════════════════════════════════════════════

async function apiGet(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

async function apiPost(path, body) {
    const res = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

// ═══════════════════════════════════════════════════
// Init
// ═══════════════════════════════════════════════════

async function init() {
    await loadFormats();
    switchTab("data");
    bindEvents();
}

async function loadFormats() {
    try {
        const data = await apiGet("/api/formats");
        state.formats = data.categories;
        updateFormatInfo();
    } catch (e) {
        console.error("Failed to load formats:", e);
        toast("加载格式信息失败，请检查后端服务");
    }
}

function bindEvents() {
    // Tabs
    dom.tabBtns().forEach(btn => {
        btn.addEventListener("click", () => switchTab(btn.dataset.category));
    });

    // Format changes
    dom.srcFormat.addEventListener("change", updateFormatInfo);
    dom.dstFormat.addEventListener("change", updateFormatInfo);

    // Drop zone
    const dz = dom.dropZone;
    dz.addEventListener("click", () => browseFiles());
    dz.addEventListener("dragover", (e) => {
        e.preventDefault();
        dz.classList.add("drag-over");
    });
    dz.addEventListener("dragleave", () => dz.classList.remove("drag-over"));
    dz.addEventListener("drop", (e) => {
        e.preventDefault();
        dz.classList.remove("drag-over");
        const paths = [];
        for (const file of e.dataTransfer.files) {
            paths.push(file.path || file.name);
        }
        if (paths.length) addFiles(paths);
    });

    // Buttons
    $("#btnAddFiles").addEventListener("click", () => browseFiles());
    $("#btnBrowseDir").addEventListener("click", () => browseOutputDir());
    $("#btnConvert").addEventListener("click", () => startConversion());
    dom.btnCancel.addEventListener("click", () => cancelConversion());
    $("#btnRemoveSel").addEventListener("click", removeSelected);
    $("#btnClearAll").addEventListener("click", clearAllFiles);
    $("#btnClearLog").addEventListener("click", clearLog);
}

// ═══════════════════════════════════════════════════
// Tab Switching
// ═══════════════════════════════════════════════════

function switchTab(category) {
    state.category = category;
    state.files = [];
    state.selectedFiles.clear();

    // Update tab buttons
    dom.tabBtns().forEach(b => {
        b.classList.toggle("active", b.dataset.category === category);
    });

    // Update format dropdowns
    const fmt = state.formats[category];
    if (!fmt) return;

    // Source format
    dom.srcFormat.innerHTML = '<option value="auto">自动检测</option>';
    for (const f of fmt.inputs) {
        dom.srcFormat.innerHTML += `<option value="${f}">${f.toUpperCase()}</option>`;
    }

    // Target format
    dom.dstFormat.innerHTML = "";
    for (const f of fmt.outputs) {
        dom.dstFormat.innerHTML += `<option value="${f}">${f.toUpperCase()}</option>`;
    }
    if (fmt.outputs.length) dom.dstFormat.value = fmt.outputs[0];

    // Reset
    renderFileList();
    updateConvertBtn();
    updateFormatInfo();
    clearLog();
}

// ═══════════════════════════════════════════════════
// Format Info
// ═══════════════════════════════════════════════════

function updateFormatInfo() {
    const cat = state.category;
    const fmt = state.formats[cat];
    if (!fmt) return;

    const srcFmt = dom.srcFormat.value === "auto" ? null : dom.srcFormat.value;
    const dstFmt = dom.dstFormat.value;

    const deps = {
        data: "PyYAML · xmltodict · tomli-w (MIT)",
        audio: "pydub (MIT) + FFmpeg (LGPL/GPL)",
        video: "ffmpeg-python (Apache-2.0) + FFmpeg (LGPL/GPL)",
        image: "Pillow (HPND)",
    };

    dom.formatInfo.innerHTML = `
        <strong>输入格式：</strong>${fmt.inputs.map(f => f.toUpperCase()).join(" · ")}<br>
        <strong>输出格式：</strong>${fmt.outputs.map(f => f.toUpperCase()).join(" · ")}<br>
        <strong>依赖：</strong>${deps[cat] || "无"}
    `;
}

// ═══════════════════════════════════════════════════
// File Management
// ═══════════════════════════════════════════════════

async function browseFiles() {
    try {
        const data = await apiPost("/api/browse-files", { category: state.category });
        if (data.files && data.files.length) addFiles(data.files);
    } catch (e) {
        toast("文件选择失败");
    }
}

async function browseOutputDir() {
    try {
        const data = await apiPost("/api/browse-dir", {});
        if (data.dir) dom.outputDir.value = data.dir;
    } catch (e) {
        toast("目录选择失败");
    }
}

function addFiles(paths) {
    const existing = new Set(state.files.map(f => f.path));
    let added = 0;
    for (const p of paths) {
        if (!existing.has(p)) {
            const name = p.split(/[/\\]/).pop();
            state.files.push({ path: p, name });
            existing.add(p);
            added++;
        }
    }
    if (added) {
        renderFileList();
        updateConvertBtn();
    }
}

function removeSelected() {
    if (state.selectedFiles.size === 0) {
        if (state.files.length) {
            // Remove last if nothing selected
            state.files.pop();
        }
    } else {
        state.files = state.files.filter(f => !state.selectedFiles.has(f.path));
        state.selectedFiles.clear();
    }
    renderFileList();
    updateConvertBtn();
}

function clearAllFiles() {
    state.files = [];
    state.selectedFiles.clear();
    renderFileList();
    updateConvertBtn();
}

function renderFileList() {
    const el = dom.fileList;
    if (state.files.length === 0) {
        el.innerHTML = '<div class="file-list-empty"><span>📭</span><p>尚未添加文件</p></div>';
    } else {
        el.innerHTML = state.files.map(f => {
            const sel = state.selectedFiles.has(f.path) ? " selected" : "";
            const ext = f.name.split(".").pop()?.toLowerCase() || "";
            const icon = getFileIcon(ext);
            return `
                <div class="file-item${sel}" data-path="${escHtml(f.path)}" onclick="toggleFileSelect('${escHtml(f.path)}', event)">
                    <span class="file-item-icon">${icon}</span>
                    <span class="file-item-name">${escHtml(f.name)}</span>
                    <span class="file-item-path">${escHtml(f.path)}</span>
                    <button class="file-item-remove" onclick="event.stopPropagation(); removeFile('${escHtml(f.path)}')">✕</button>
                </div>`;
        }).join("");
    }
    dom.fileCount.textContent = `${state.files.length} 个文件`;
}

function getFileIcon(ext) {
    const icons = {
        json: "📋", yaml: "📋", yml: "📋", csv: "📊", xml: "📋", toml: "⚙️",
        mp3: "🎵", wav: "🎵", flac: "🎵", ogg: "🎵", aac: "🎵", m4a: "🎵", wma: "🎵",
        mp4: "🎬", avi: "🎬", mkv: "🎬", mov: "🎬", webm: "🎬", flv: "🎬",
        jpg: "🖼️", jpeg: "🖼️", png: "🖼️", webp: "🖼️", bmp: "🖼️", gif: "🖼️", tiff: "🖼️", ico: "🖼️",
    };
    return icons[ext] || "📄";
}

function escHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function toggleFileSelect(path, event) {
    // Multi-select with Ctrl/Cmd
    if (!event.ctrlKey && !event.metaKey) {
        state.selectedFiles.clear();
    }
    if (state.selectedFiles.has(path)) {
        state.selectedFiles.delete(path);
    } else {
        state.selectedFiles.add(path);
    }
    renderFileList();
}

function removeFile(path) {
    state.files = state.files.filter(f => f.path !== path);
    state.selectedFiles.delete(path);
    renderFileList();
    updateConvertBtn();
}

function updateConvertBtn() {
    dom.btnConvert.disabled = state.files.length === 0 || state.converting;
}

// ═══════════════════════════════════════════════════
// Conversion
// ═══════════════════════════════════════════════════

async function startConversion() {
    if (state.files.length === 0 || state.converting) return;

    const sourceFmt = dom.srcFormat.value === "auto" ? null : dom.srcFormat.value;
    const targetFmt = dom.dstFormat.value;
    const outputDir = dom.outputDir.value.trim() || null;

    try {
        const data = await apiPost("/api/convert", {
            files: state.files.map(f => f.path),
            source_fmt: sourceFmt,
            target_fmt: targetFmt,
            output_dir: outputDir,
        });

        state.taskId = data.task_id;
        state.converting = true;
        updateConvertBtn();
        dom.btnCancel.style.display = "";
        dom.progressSection.classList.add("active");
        setStatus("running", "正在转换...");
        clearLog();

        // Start polling
        pollTaskStatus();
    } catch (e) {
        toast("启动转换失败: " + e.message);
    }
}

async function cancelConversion() {
    if (!state.taskId) return;
    try {
        await apiPost(`/api/task/${state.taskId}/cancel`, {});
    } catch (e) { /* ignore */ }
    stopPolling();
    resetUI();
    setStatus("ready", "已取消");
    appendLog("⚠️ 转换已取消", "error");
}

function pollTaskStatus() {
    if (!state.taskId) return;

    state.pollingTimer = setInterval(async () => {
        try {
            const task = await apiGet(`/api/task/${state.taskId}`);
            if (!task || task.error) return;

            // Update progress
            dom.overallFill.style.width = task.overall_progress + "%";
            dom.fileFill.style.width = task.file_progress + "%";
            dom.progressPercent.textContent = task.overall_progress + "%";
            dom.currentFile.textContent = task.current_file || "";

            // Update status
            if (task.status === "running") {
                setStatus("running", `转换中 (${task.completed}/${task.total})`);
            }

            // Append new logs
            if (task.logs) {
                for (const line of task.logs) {
                    appendLog(line, classifyLog(line));
                }
            }

            // Done?
            if (task.status === "completed" || task.status === "cancelled") {
                stopPolling();
                if (task.status === "completed") {
                    setStatus("ready", "转换完成");
                    const ok = task.results ? task.results.filter(r => r[0]).length : 0;
                    const fail = task.results ? task.results.filter(r => !r[0]).length : 0;
                    appendLog(`✅ 完成: ${ok} 成功, ${fail} 失败`, ok > 0 ? "success" : "error");
                }
                resetUI();
            }
        } catch (e) {
            console.error("Poll error:", e);
        }
    }, 500);
}

function stopPolling() {
    if (state.pollingTimer) {
        clearInterval(state.pollingTimer);
        state.pollingTimer = null;
    }
}

function resetUI() {
    state.converting = false;
    state.taskId = null;
    updateConvertBtn();
    dom.btnCancel.style.display = "none";
    dom.progressSection.classList.remove("active");
    setTimeout(() => {
        dom.overallFill.style.width = "0%";
        dom.fileFill.style.width = "0%";
        dom.progressPercent.textContent = "0%";
        dom.currentFile.textContent = "";
    }, 500);
}

// ═══════════════════════════════════════════════════
// Status & Logging
// ═══════════════════════════════════════════════════

function setStatus(state, text) {
    dom.statusDot.className = "status-dot " + state;
    dom.statusText.textContent = text;
}

function appendLog(message, level = "") {
    dom.logOutput.querySelector(".log-empty")?.remove();
    const div = document.createElement("div");
    div.className = "log-line" + (level ? " " + level : "");
    div.textContent = message;
    dom.logOutput.appendChild(div);
    dom.logOutput.scrollTop = dom.logOutput.scrollHeight;

    // Limit lines
    while (dom.logOutput.children.length > 200) {
        dom.logOutput.firstChild.remove();
    }
}

function clearLog() {
    dom.logOutput.innerHTML = '<div class="log-empty">等待转换任务...</div>';
}

function classifyLog(line) {
    if (line.includes("错误") || line.includes("失败") || line.includes("Error")) return "error";
    if (line.includes("完成") || line.includes("成功")) return "success";
    if (line.includes("开始")) return "info";
    return "";
}

// ═══════════════════════════════════════════════════
// Toast
// ═══════════════════════════════════════════════════

function toast(message) {
    const el = document.createElement("div");
    el.className = "toast";
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3000);
}

// ═══════════════════════════════════════════════════
// Boot
// ═══════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", init);
