// ========================================
// 全局状态管理
// ========================================
const state = {
    currentData: null,
    presets: [],
    // GET /api/config 的嵌套结构：{ chat, image: { active, providers, options } }
    config: { chat: {}, image: { active: '', providers: {}, options: {} } },

    imageProviders: {},
    activeImageProvider: '',
    activeImageModel: '',
    imageSettingsSaveQueue: Promise.resolve(),
    uploadedImages: [], // Base64 strings
    isGenerating: false,
    imageGenAbortController: null,
    generationHistory: [] // 本次会话生成的图片 dataURL，最新在末尾
};

// 默认反向提示词以 schema 为准（/api/schema 的 negativePrompt overlay）
function defaultNegativePrompt() {
    return window.PromptDoc.overlayDefault('negativePrompt');
}
const DRAFT_STORAGE_KEY = 'nano-banana-form-draft';

// ========================================
// 本机草稿：防刷新/关页丢失表单内容
// ========================================
let draftSaveTimer = null;

function saveDraftNow() {
    try {
        localStorage.setItem(
            DRAFT_STORAGE_KEY,
            JSON.stringify({ savedAt: Date.now(), data: getFormData() })
        );
        return true;
    } catch (e) {
        return false;
    }
}

function scheduleDraftSave() {
    clearTimeout(draftSaveTimer);
    draftSaveTimer = setTimeout(() => {
        const ok = saveDraftNow();
        const saveState = document.getElementById('editorSaveState');
        if (saveState && !ok) saveState.textContent = '草稿保存失败';
    }, 500);
}

function draftHasMeaningfulContent(data) {
    const walk = (value, path) => {
        if (typeof value === 'string') {
            // 默认反向提示词不算用户输入
            if (path === '反向提示词' && value.trim() === defaultNegativePrompt()) return false;
            return Boolean(value.trim());
        }
        if (Array.isArray(value)) return value.some(item => walk(item, path));
        if (value && typeof value === 'object') {
            return Object.entries(value).some(([key, item]) => walk(item, key));
        }
        return false;
    };
    return walk(data, '');
}

function restoreDraft() {
    try {
        const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
        if (!raw) return;
        const draft = JSON.parse(raw);
        if (!draft || !draft.data || typeof draft.data !== 'object') return;
        if (!draftHasMeaningfulContent(draft.data)) return;
        setFormData(draft.data);
        showToast('已恢复上次编辑的草稿');
    } catch (e) {
        console.error('恢复草稿失败', e);
    }
}

function categoryPresetConfig() {
    return window.PromptDoc ? window.PromptDoc.categoryPresetConfig() : {};
}

// ========================================
// DOM 元素
// ========================================
const elements = {
    // 侧边栏表单 - 基础设置
    styleMode: document.getElementById('styleMode'),
    atmosphere: document.getElementById('atmosphere'),

    // 场景设置
    location: document.getElementById('location'),
    lighting: document.getElementById('lighting'),
    weather: document.getElementById('weather'),

    // 主体设置
    description: document.getElementById('description'),
    bodyShape: document.getElementById('bodyShape'),
    face: document.getElementById('face'),
    hair: document.getElementById('hair'),
    eyes: document.getElementById('eyes'),
    emotion: document.getElementById('emotion'),
    action: document.getElementById('action'),
    clothing: document.getElementById('clothing'),
    clothingDetails: document.getElementById('clothingDetails'),
    accessories: document.getElementById('accessories'),
    background: document.getElementById('background'),
    depth: document.getElementById('depth'),

    // 相机设置
    angle: document.getElementById('angle'),
    composition: document.getElementById('composition'),
    lensCharacteristics: document.getElementById('lensCharacteristics'),
    sensorQuality: document.getElementById('sensorQuality'),

    // 审美控制
    intent: document.getElementById('intent'),
    materialRealism: document.getElementById('materialRealism'),
    overallTone: document.getElementById('overallTone'),
    contrast: document.getElementById('contrast'),
    specialEffects: document.getElementById('specialEffects'),

    // 高级设置
    specialRequirementEnabled: document.getElementById('specialRequirementEnabled'),
    specialRequirementGroup: document.getElementById('specialRequirementGroup'),
    specialRequirementInput: document.getElementById('specialRequirementInput'),

    lineArtModeEnabled: document.getElementById('lineArtModeEnabled'),
    lineArtGroup: document.getElementById('lineArtGroup'),
    lineArtPromptInput: document.getElementById('lineArtPromptInput'),
    saveLineArtPromptBtn: document.getElementById('saveLineArtPromptBtn'),

    negativePromptEnabled: document.getElementById('negativePromptEnabled'),
    negativePromptGroup: document.getElementById('negativePromptGroup'),
    negativeTagsContainer: document.getElementById('negativeTagsContainer'),
    negativeTagInput: document.getElementById('negativeTagInput'),
    addNegativeTagBtn: document.getElementById('addNegativeTagBtn'),
    negativePromptInput: document.getElementById('negativePromptInput'),

    // 预设
    presetSelect: document.getElementById('presetSelect'),
    savePresetBtn: document.getElementById('savePresetBtn'),
    deletePresetBtn: document.getElementById('deletePresetBtn'),

    // 顶部工具栏
    aiGenerateOpenBtn: document.getElementById('aiGenerateOpenBtn'),
    aiModifyOpenBtn: document.getElementById('aiModifyOpenBtn'),
    configBtn: document.getElementById('configBtn'),
    resetFormBtn: document.getElementById('resetFormBtn'),

    // JSON 预览（可折叠）
    jsonPreviewPane: document.getElementById('jsonPreviewPane'),
    jsonPreviewToggleBtn: document.getElementById('jsonPreviewToggleBtn'),
    jsonPreviewHideBtn: document.getElementById('jsonPreviewHideBtn'),
    jsonPreviewText: document.getElementById('jsonPreviewText'),
    copyJsonBtn: document.getElementById('copyJsonBtn'),

    // 生图区域
    activeImageProvider: document.getElementById('activeImageProvider'),
    imageProviderStatus: document.getElementById('imageProviderStatus'),
    imageProviderStatusButton: document.getElementById('imageProviderStatusButton'),
    imageProviderStatusPopover: document.getElementById('imageProviderStatusPopover'),
    imageProviderSelect: document.getElementById('imageProviderSelect'),
    imageModelSelect: document.getElementById('imageModelSelect'),
    imageProviderOptions: document.getElementById('imageProviderOptions'),
    // genThinkingLevel: document.getElementById('genThinkingLevel'), // Removed from HTML
    imageInput: document.getElementById('imageInput'),
    uploadImageBtn: document.getElementById('uploadImageBtn'),
    imagePreview: document.getElementById('imagePreview'),
    generateImageBtn: document.getElementById('generateImageBtn'),
    resultPreview: document.getElementById('resultPreview'),

    // AI 对话框
    aiModal: document.getElementById('aiModal'),
    aiModalTitle: document.getElementById('aiModalTitle'),
    aiModalLabel: document.getElementById('aiModalLabel'),
    aiPromptInput: document.getElementById('aiPromptInput'),
    // aiProgress: document.getElementById('aiProgress'), // Removed
    
    // AI Modal New Elements
    aiImageInput: document.getElementById('aiImageInput'),
    aiUploadImageBtn: document.getElementById('aiUploadImageBtn'),
    aiImagePreview: document.getElementById('aiImagePreview'),
    aiResponsePreview: document.getElementById('aiResponsePreview'),
    aiStatusText: document.getElementById('aiStatusText'),
    
    aiModalCancelBtn: document.getElementById('aiModalCancelBtn'),
    aiModalExecuteBtn: document.getElementById('aiModalExecuteBtn'),
    aiModalStopBtn: document.getElementById('aiModalStopBtn'),
    aiModalApplyBtn: document.getElementById('aiModalApplyBtn'),
    aiDiffContainer: document.getElementById('aiDiffContainer'),

    // 配置对话框
    configModal: document.getElementById('configModal'),
    // OpenAI Config
    configBaseUrl: document.getElementById('configBaseUrl'),
    configApiKey: document.getElementById('configApiKey'),
    configModel: document.getElementById('configModel'),
    // Image generation Config
    configImageProvider: document.getElementById('configImageProvider'),
    configImageProviderFields: document.getElementById('configImageProviderFields'),

    saveConfigBtn: document.getElementById('saveConfigBtn')
};

// ========================================
// 工具函数
// ========================================
let toastContainer = null;

function showToast(message, type = 'info') {
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }
    const item = document.createElement('div');
    item.className = `toast-item ${type}`;
    item.setAttribute('role', 'status');
    item.textContent = message;
    toastContainer.appendChild(item);
    requestAnimationFrame(() => item.classList.add('show'));
    setTimeout(() => {
        item.classList.remove('show');
        setTimeout(() => item.remove(), 300);
    }, 3000);
}

/**
 * 启动一个秒级计时器，每秒回调 setText(已耗时秒数)，返回停止函数。
 * 用于生图等长任务的耗时反馈。
 */
function startElapsedTimer(setText) {
    const startTime = Date.now();
    setText(0);
    const timerId = setInterval(() => {
        setText(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(timerId);
}

// ========================================
// 表单数据处理 (保持原有的逻辑)
// ========================================
function getFormData() {
    const data = window.PromptDoc.nestFromElements(elements);
    if (elements.specialRequirementEnabled.checked) {
        data["特别要求"] = elements.specialRequirementInput.value;
    }
    if (elements.lineArtModeEnabled.checked) {
        data["角色线稿生成"] = {
            "启用": true,
            "提示词": elements.lineArtPromptInput.value
        };
    }
    if (elements.negativePromptEnabled.checked) {
        data["反向提示词"] = elements.negativePromptInput.value.trim();
    }
    return data;
}

function setFormData(data) {
    if (!data) return;
    window.PromptDoc.fillElementsFromData(elements, data);

    const specialReq = window.PromptDoc.getAtPath(data, ["特别要求"]) || '';
    if (specialReq) {
        elements.specialRequirementEnabled.checked = true;
        elements.specialRequirementInput.value = specialReq;
        elements.specialRequirementGroup.style.display = 'block';
    } else {
        elements.specialRequirementEnabled.checked = false;
        elements.specialRequirementInput.value = '';
        elements.specialRequirementGroup.style.display = 'none';
    }

    const lineArt = window.PromptDoc.getAtPath(data, ["角色线稿生成"]);
    if (lineArt && lineArt["启用"]) {
        elements.lineArtModeEnabled.checked = true;
        elements.lineArtPromptInput.value = lineArt["提示词"] || '';
        elements.lineArtGroup.style.display = 'block';
        elements.lineArtModeEnabled.dispatchEvent(new Event('change'));
    } else {
        elements.lineArtModeEnabled.checked = false;
        elements.lineArtPromptInput.value = '';
        elements.lineArtGroup.style.display = 'none';
        elements.lineArtModeEnabled.dispatchEvent(new Event('change'));
    }

    const negativeValue = window.PromptDoc.getAtPath(data, ["反向提示词"]);
    const negativePrompt = typeof negativeValue === 'string' ? negativeValue : '';
    elements.negativePromptInput.value = negativePrompt;
    elements.negativePromptEnabled.checked = Boolean(negativePrompt);
    elements.negativePromptGroup.style.display = negativePrompt ? 'flex' : 'none';
    updateJsonPreview();
}

function setNestedValue(target, path, value) {
    let current = target;
    path.slice(0, -1).forEach(key => {
        if (!current[key]) current[key] = {};
        current = current[key];
    });
    current[path[path.length - 1]] = value;
}

function collectCategoryPresetData(scope) {
    return window.PromptDoc.subsetFromData(getFormData(), scope);
}

function applyCategoryPresetData(scope, data) {
    (categoryPresetConfig()[scope] || []).forEach(([elementId, path]) => {
        const value = getNestedValue(data, path);
        if (value === undefined) return;
        const element = document.getElementById(elementId);
        if (!element) return;
        element.value = Array.isArray(value) ? value.join(', ') : (value ?? '');
        element.dispatchEvent(new Event('input', { bubbles: true }));
    });
    updateJsonPreview();
}

async function loadCategoryPresetOptions(scope, selectedName = '') {
    const bar = document.querySelector(`.category-preset-bar[data-preset-scope="${scope}"]`);
    if (!bar) return;
    const selector = bar.querySelector('select');
    try {
        const response = await fetch(`/api/category-presets/${scope}`);
        if (!response.ok) throw new Error('加载分类预设失败');
        const presets = await response.json();
        selector.innerHTML = '<option value="">分类预设...</option>';
        presets.forEach(preset => {
            const option = document.createElement('option');
            option.value = preset.name;
            option.textContent = preset.name;
            selector.appendChild(option);
        });
        if (selectedName) selector.value = selectedName;
    } catch (error) {
        console.error(error);
    }
}

function initCategoryPresets() {
    document.querySelectorAll('.category-preset-bar').forEach(bar => {
        const scope = bar.dataset.presetScope;
        const label = bar.dataset.presetLabel;
        bar.innerHTML = `
            <span class="category-preset-label">分类预设</span>
            <select class="select-input" aria-label="${label}预设">
                <option value="">分类预设...</option>
            </select>
            <button type="button" class="btn btn-secondary btn-compact" data-action="save">保存当前分类</button>
            <button type="button" class="btn btn-danger btn-compact" data-action="delete">删除</button>
        `;
        const selector = bar.querySelector('select');

        selector.addEventListener('change', async () => {
            if (!selector.value) return;
            try {
                const name = encodeURIComponent(selector.value);
                const response = await fetch(`/api/category-presets/${scope}/${name}`);
                if (!response.ok) throw new Error('加载分类预设失败');
                applyCategoryPresetData(scope, await response.json());
                showToast(`已应用${label}预设: ${selector.value}`);
            } catch (error) {
                console.error(error);
                showToast('分类预设加载失败');
            }
        });

        bar.querySelector('[data-action="save"]').addEventListener('click', async () => {
            const name = prompt(`请输入${label}预设名称:`, selector.value);
            if (!name || !name.trim()) return;
            const response = await fetch(`/api/category-presets/${scope}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name.trim(), data: collectCategoryPresetData(scope) })
            });
            if (!response.ok) {
                showToast('分类预设保存失败');
                return;
            }
            await loadCategoryPresetOptions(scope, name.trim());
            showToast(`${label}预设已保存: ${name.trim()}`);
        });

        bar.querySelector('[data-action="delete"]').addEventListener('click', async () => {
            const name = selector.value;
            if (!name || !confirm(`确定删除${label}预设「${name}」吗?`)) return;
            const response = await fetch(
                `/api/category-presets/${scope}/${encodeURIComponent(name)}`,
                { method: 'DELETE' }
            );
            if (!response.ok) {
                showToast('分类预设删除失败');
                return;
            }
            await loadCategoryPresetOptions(scope);
            showToast(`已删除分类预设: ${name}`);
        });

        loadCategoryPresetOptions(scope);
    });
}

function clearForm() {
    if (!confirm('确定清空所有提示词字段吗？此操作不可撤销。')) return;

    // 只清结构化提示词字段，不碰生图渠道、配置、AI 弹窗等无关控件
    document.querySelectorAll('.tab-panel .field-control input, .tab-panel .field-control textarea').forEach(el => {
        el.value = '';
        el.dispatchEvent(new Event('input', { bubbles: true }));
    });

    elements.specialRequirementEnabled.checked = false;
    elements.specialRequirementInput.value = '';
    elements.specialRequirementEnabled.dispatchEvent(new Event('change'));

    elements.lineArtModeEnabled.checked = false;
    elements.lineArtPromptInput.value = '';
    elements.lineArtModeEnabled.dispatchEvent(new Event('change'));

    elements.negativePromptEnabled.checked = true;
    elements.negativePromptInput.value = defaultNegativePrompt();
    elements.negativePromptGroup.style.display = 'flex';

    updateJsonPreview();
    showToast('已清空提示词字段');
}

// 最终提示词由服务端渲染（POST /api/prompt/render），前端不再自己拼。
// 生图请求提交的也是文档本身，所以这里的预览与实际请求永远一致。
let renderTimer = null;
let renderSeq = 0;

function updateJsonPreview() {
    scheduleDraftSave();
    clearTimeout(renderTimer);
    renderTimer = setTimeout(renderFinalPrompt, 120);
}

async function renderFinalPrompt() {
    const seq = ++renderSeq;
    try {
        const response = await fetch('/api/prompt/render', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ document: getFormData() })
        });
        if (!response.ok) throw new Error(response.statusText);
        const rendered = await response.json();
        if (seq !== renderSeq) return; // 已有更新的请求在路上，丢弃过期结果
        elements.jsonPreviewText.value = rendered.text;
    } catch (error) {
        console.error('Render prompt error:', error);
    }
}

/**
 * 把 AI 返回的文档应用到表单。
 * ui_only 的 overlay（特别要求、线稿）不归 AI 管，始终保留当前值；
 * 其余 overlay（反向提示词）只有 AI 明确给出时才覆盖。
 */
function applyAiDocument(aiDocument) {
    const current = getFormData();
    const next = JSON.parse(JSON.stringify(aiDocument || {}));
    (window.PromptDoc.getSchema()?.overlays || []).forEach(overlay => {
        const currentValue = window.PromptDoc.getAtPath(current, overlay.path);
        const hasNew = window.PromptDoc.getAtPath(next, overlay.path) !== undefined;
        if (overlay.ui_only || !hasNew) {
            if (currentValue === undefined) {
                window.PromptDoc.deleteAtPath(next, overlay.path);
            } else {
                window.PromptDoc.setAtPath(next, overlay.path, currentValue);
            }
        }
    });
    setFormData(next);
}

// ========================================
// Init
// ========================================
function init() {
    const start = () => {
    Promise.all([loadImageProviders(), loadConfig()])
        .then(() => renderImageGenerationControls())
        .catch(error => console.error('Initialize image generation controls error:', error));

    // === 移动端侧边栏切换 ===
    const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    if (sidebarToggleBtn && sidebar && sidebarOverlay) {
        sidebarToggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            sidebarOverlay.classList.toggle('active');
        });
        sidebarOverlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            sidebarOverlay.classList.remove('active');
        });
    }

    // Event Listeners
    elements.configBtn.addEventListener('click', openConfigModal);
    elements.configModal.querySelector('.modal-close').addEventListener('click', () => {
        elements.configModal.classList.remove('active');
    });
    elements.saveConfigBtn.addEventListener('click', saveConfigs);
    elements.configImageProvider.addEventListener('change', updateImageConfigVisibility);
    elements.imageProviderStatusButton.addEventListener('pointerenter', event => {
        if (event.pointerType === 'mouse') {
            elements.imageProviderStatus.classList.remove('is-touch-input');
        }
    });
    elements.imageProviderStatusButton.addEventListener('pointerdown', event => {
        elements.imageProviderStatus.classList.toggle('is-touch-input', event.pointerType !== 'mouse');
        elements.imageProviderStatusButton.dataset.openOnPointerDown =
            elements.imageProviderStatusButton.getAttribute('aria-expanded');
    });
    elements.imageProviderStatusButton.addEventListener('click', event => {
        event.stopPropagation();
        const wasOpen = elements.imageProviderStatusButton.dataset.openOnPointerDown;
        const isOpen = elements.imageProviderStatusButton.getAttribute('aria-expanded') === 'true';
        const nextOpen = event.detail > 0 && wasOpen !== undefined
            ? wasOpen !== 'true'
            : !isOpen;
        delete elements.imageProviderStatusButton.dataset.openOnPointerDown;
        setImageProviderStatusOpen(nextOpen);
    });
    elements.imageProviderStatusButton.addEventListener('focus', () => {
        setImageProviderStatusOpen(true);
    });
    elements.imageProviderStatusButton.addEventListener('blur', () => {
        window.setTimeout(() => {
            if (!elements.imageProviderStatus.contains(document.activeElement)) {
                setImageProviderStatusOpen(false);
            }
        }, 0);
    });
    elements.imageProviderStatusButton.addEventListener('keydown', event => {
        if (event.key === 'Escape') {
            setImageProviderStatusOpen(false);
            elements.imageProviderStatusButton.blur();
        }
    });
    document.addEventListener('click', event => {
        if (!elements.imageProviderStatus.contains(event.target)) {
            setImageProviderStatusOpen(false);
        }
    });
    elements.imageProviderSelect.addEventListener('change', async () => {
        state.activeImageProvider = elements.imageProviderSelect.value;
        renderImageModelChoices(state.activeImageProvider);
        await persistImageGenerationSettings(false);
    });
    elements.imageModelSelect.addEventListener('change', async () => {
        state.activeImageModel = elements.imageModelSelect.value;
        renderImageProviderOptions();
        await persistImageGenerationSettings(false);
    });

    elements.resetFormBtn.addEventListener('click', clearForm);

    // AI Tools
    elements.aiGenerateOpenBtn.addEventListener('click', () => openAiModal('generate'));
    elements.aiModifyOpenBtn.addEventListener('click', () => openAiModal('modify'));
    elements.aiModal.querySelector('.modal-close').addEventListener('click', () => {
        if (aiAbortController) aiAbortController.abort();
        elements.aiModal.classList.remove('active');
    });
    
    // New AI Modal Listeners
    if (elements.aiModalCancelBtn) {
        elements.aiModalCancelBtn.addEventListener('click', () => {
             if (aiAbortController) aiAbortController.abort();
             elements.aiModal.classList.remove('active');
        });
    }
    if (elements.aiModalExecuteBtn) elements.aiModalExecuteBtn.addEventListener('click', handleAiExecute);
    if (elements.aiModalStopBtn) elements.aiModalStopBtn.addEventListener('click', handleAiStop);
    if (elements.aiModalApplyBtn) elements.aiModalApplyBtn.addEventListener('click', applyAiResult);
    
    // AI Modal Image Upload
    if (elements.aiUploadImageBtn) elements.aiUploadImageBtn.addEventListener('click', () => elements.aiImageInput.click());
    if (elements.aiImageInput) elements.aiImageInput.addEventListener('change', handleAiImageUpload);

    // Image Upload
    elements.uploadImageBtn.addEventListener('click', () => elements.imageInput.click());
    elements.imageInput.addEventListener('change', handleImageUpload);
    initImageUploadExtras();

    // Form inputs change -> update JSON
    document.querySelectorAll('.app-container input, .app-container textarea').forEach(el => {
        if (!el.id.startsWith('gen') && !el.id.startsWith('ai') && !el.id.startsWith('config')) {
            el.addEventListener('input', updateJsonPreview);
        }
    });

    // 复制最终提示词（JSON 或线稿文本，与预览一致）
    elements.copyJsonBtn.addEventListener('click', () => {
        if (!elements.jsonPreviewText.value) return;
        navigator.clipboard.writeText(elements.jsonPreviewText.value).then(() => {
            showToast('已复制提示词');
        });
    });

    // JSON 预览 显示/隐藏（通过在 preview-area-row 上切换 json-hidden）
    const previewAreaRow = document.getElementById('previewAreaRow');
    elements.jsonPreviewToggleBtn.addEventListener('click', () => {
        previewAreaRow.classList.remove('json-hidden');
    });
    elements.jsonPreviewHideBtn.addEventListener('click', () => {
        previewAreaRow.classList.add('json-hidden');
    });

    // Generate Image Button
    elements.generateImageBtn.addEventListener('click', generateImage);

    // Tab Switching Logic
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            // Update buttons
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update panels
            tabPanels.forEach(panel => {
                if (panel.id === `tab-${targetTab}`) {
                    panel.classList.add('active');
                } else {
                    panel.classList.remove('active');
                }
            });
        });
    });

    // Load presets logic
    loadPresets();
    initCategoryPresets();

    // Init Advanced Settings
    initAdvancedSettings();

    elements.presetSelect.addEventListener('change', async () => {
        const name = elements.presetSelect.value;
        if (name) {
            try {
                const res = await fetch(`/api/presets/${encodeURIComponent(name)}`);
                if (!res.ok) throw new Error('预设不存在');
                setFormData(await res.json());
                showToast('预设加载成功');
            } catch (e) {
                console.error(e);
                showToast('预设加载失败', 'error');
            }
        }
    });

    // Save Preset
    elements.savePresetBtn.addEventListener('click', async () => {
        const name = prompt('预设名称:');
        if (!name) return;
        const res = await fetch('/api/presets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, data: getFormData() })
        });
        if (!res.ok) {
            showToast('保存失败', 'error');
            return;
        }
        showToast('保存成功');
        loadPresets();
    });

    // Delete Preset
    elements.deletePresetBtn.addEventListener('click', async () => {
        const name = elements.presetSelect.value;
        if (!name) return;
        if (!confirm('确定删除?')) return;
        const res = await fetch(`/api/presets/${encodeURIComponent(name)}`, { method: 'DELETE' });
        if (!res.ok) {
            showToast('删除失败', 'error');
            return;
        }
        showToast('删除成功');
        loadPresets();
    });

    // 恢复本机草稿（刷新/关页不丢）
    restoreDraft();
    };

    const ready = window.promptSchemaPromise || Promise.resolve();
    ready.then(start).catch(error => console.error('Load prompt schema error:', error));
}

async function initAdvancedSettings() {
    // 1. Toggle Special Requirements
    elements.specialRequirementEnabled.addEventListener('change', () => {
        elements.specialRequirementGroup.style.display = elements.specialRequirementEnabled.checked ? 'block' : 'none';
        updateJsonPreview();
    });
    elements.specialRequirementInput.addEventListener('input', updateJsonPreview);

    // 2. Toggle Line Art Mode
    elements.lineArtModeEnabled.addEventListener('change', () => {
        const enabled = elements.lineArtModeEnabled.checked;
        elements.lineArtGroup.style.display = enabled ? 'block' : 'none';
        
        // Disable other inputs
        const allInputs = document.querySelectorAll('.field-control input, .field-control textarea, .field-control button, #negativePromptEnabled, #negativePromptInput, #negativeTagInput');
        allInputs.forEach(el => {
            // Skip control buttons/checkboxes and special req
            if (el.id === 'lineArtModeEnabled' || 
                el.id === 'lineArtPromptInput' || 
                el.id === 'specialRequirementEnabled' || 
                el.id === 'specialRequirementInput' ||
                el.id.startsWith('gen') || // Generation controls
                el.id.startsWith('config') || // Config controls
                el.id === 'presetSelect' // Preset select
            ) {
                return;
            }
            // Skip buttons
            if (el.type === 'button' || el.type === 'submit') return;

            el.disabled = enabled;
        });

        if (enabled) {
            // Load saved prompt if empty
            if (!elements.lineArtPromptInput.value) {
                loadLineArtPrompt();
            }
        }
        updateJsonPreview();
    });
    elements.lineArtPromptInput.addEventListener('input', updateJsonPreview);

    // Save Line Art Prompt
    elements.saveLineArtPromptBtn.addEventListener('click', async () => {
        const prompt = elements.lineArtPromptInput.value;
        if (!prompt) return;
        try {
            await fetch('/api/line-art-prompt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            });
            showToast('线稿提示词保存成功', 'success');
        } catch (e) {
            showToast('保存失败: ' + e, 'error');
        }
    });

    async function loadLineArtPrompt() {
        try {
            const res = await fetch('/api/line-art-prompt');
            const data = await res.json();
            if (data.prompt) {
                elements.lineArtPromptInput.value = data.prompt;
                updateJsonPreview();
            }
        } catch (e) { console.error(e); }
    }

    // 3. Toggle Negative Prompt
    elements.negativePromptEnabled.addEventListener('change', () => {
        elements.negativePromptGroup.style.display = elements.negativePromptEnabled.checked ? 'flex' : 'none';
        updateJsonPreview();
    });

    const negativeTagEndpoint =
        '/api/options/' + encodeURIComponent('反向提示词标签');

    const applyNegativeTag = item => {
        const current = elements.negativePromptInput.value.trim();
        if (!current) {
            elements.negativePromptInput.value = item;
        } else if (!current.includes(item)) {
            const separator = /[,，\s]$/.test(current) ? '' : ', ';
            elements.negativePromptInput.value = current + separator + item;
        }
        elements.negativePromptInput.dispatchEvent(
            new Event('input', { bubbles: true })
        );
        elements.negativePromptInput.focus();
    };

    const renderNegativeTags = items => {
        elements.negativeTagsContainer.innerHTML = '';
        if (!items || items.length === 0) {
            elements.negativeTagsContainer.innerHTML =
                '<span style="color: var(--text-tertiary);">无标签</span>';
            return;
        }

        items.forEach(item => {
            const tag = document.createElement('span');
            tag.className = 'negative-tag';

            const applyButton = document.createElement('button');
            applyButton.type = 'button';
            applyButton.className = 'negative-tag-value';
            applyButton.textContent = item;
            applyButton.addEventListener('click', () => applyNegativeTag(item));

            const deleteButton = document.createElement('button');
            deleteButton.type = 'button';
            deleteButton.className = 'negative-tag-delete';
            deleteButton.textContent = '×';
            deleteButton.title = '删除标签：' + item;
            deleteButton.setAttribute('aria-label', '删除标签：' + item);
            deleteButton.addEventListener('click', () => deleteNegativeTag(item));

            tag.appendChild(applyButton);
            tag.appendChild(deleteButton);
            elements.negativeTagsContainer.appendChild(tag);
        });
    };

    async function loadNegativeTags() {
        try {
            const response = await fetch(negativeTagEndpoint);
            if (!response.ok) throw new Error(response.statusText);
            renderNegativeTags(await response.json());
        } catch (e) {
            console.error('Failed to load negative prompt tags', e);
        }
    }

    const deleteNegativeTag = async item => {
        try {
            const response = await fetch(negativeTagEndpoint, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ value: item })
            });
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.error || response.statusText);
            }
            await loadNegativeTags();
            showToast('标签已删除', 'success');
        } catch (e) {
            showToast('删除失败: ' + e.message, 'error');
        }
    };

    const addNegativeTag = async () => {
        const value = elements.negativeTagInput.value.trim();
        if (!value) {
            showToast('请输入标签内容', 'error');
            return;
        }

        try {
            const response = await fetch(negativeTagEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ value })
            });
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.error || response.statusText);
            }

            elements.negativeTagInput.value = '';
            await loadNegativeTags();
            showToast('标签已添加', 'success');
        } catch (e) {
            showToast('添加失败: ' + e.message, 'error');
        }
    };

    elements.addNegativeTagBtn.addEventListener('click', addNegativeTag);
    elements.negativeTagInput.addEventListener('keydown', event => {
        if (event.key === 'Enter') {
            event.preventDefault();
            addNegativeTag();
        }
    });
    await loadNegativeTags();
}

async function loadPresets() {
    try {
        const res = await fetch('/api/presets');
        const list = await res.json();
        elements.presetSelect.innerHTML = '<option value="">选择预设...</option>';
        list.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.name;
            opt.textContent = p.name;
            elements.presetSelect.appendChild(opt);
        });
    } catch (e) { console.error(e); }
}

function getNestedValue(obj, path) {
    let current = obj;
    for (const key of path) {
        if (current === null || current === undefined) return undefined;
        current = current[key];
    }
    return current;
}

document.addEventListener('DOMContentLoaded', init);
