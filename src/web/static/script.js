// ========================================
// 全局状态管理
// ========================================
const state = {
    currentData: null,
    presets: [],
    config: {},
    uploadedImages: [], // Base64 strings
    isGenerating: false
};

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
    accessories: document.getElementById('accessories'),
    background: document.getElementById('background'),

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
    negativeElementsContainer: document.getElementById('negativeElementsContainer'),
    negativeStylesContainer: document.getElementById('negativeStylesContainer'),

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
    genAspectRatio: document.getElementById('genAspectRatio'),
    genImageSize: document.getElementById('genImageSize'),
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
    // Gemini Config
    configGeminiBaseUrl: document.getElementById('configGeminiBaseUrl'),
    configGeminiApiKey: document.getElementById('configGeminiApiKey'),
    configGeminiModel: document.getElementById('configGeminiModel'),

    saveConfigBtn: document.getElementById('saveConfigBtn'),

    // Toast
    toast: document.getElementById('toast')
};

// ========================================
// 工具函数
// ========================================
function showToast(message, type = 'info') {
    elements.toast.textContent = message;
    elements.toast.className = `toast ${type} show`;
    setTimeout(() => {
        elements.toast.classList.remove('show');
    }, 3000);
}

// ========================================
// 表单数据处理 (保持原有的逻辑)
// ========================================
function getFormData() {
    function stringToArray(str) {
        if (!str || !str.trim()) return [];
        return str.split(',').map(item => item.trim()).filter(item => item);
    }

    const materialRealismValue = elements.materialRealism.value.trim();
    const materialRealismArray = materialRealismValue ? stringToArray(materialRealismValue) : [];

    // Helper to get checked values from container
    function getCheckedValues(container) {
        const checked = [];
        const checkboxes = container.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(cb => {
            if (cb.checked) checked.push(cb.value);
        });
        return checked;
    }

    const data = {
        "风格模式": elements.styleMode.value,
        "画面气质": elements.atmosphere.value,
        "场景": {
            "环境": {
                "地点设定": elements.location.value,
                "光线": elements.lighting.value,
                "天气氛围": elements.weather.value
            },
            "主体": {
                "整体描述": elements.description.value,
                "外形特征": {
                    "身材": elements.bodyShape.value,
                    "面部": elements.face.value,
                    "头发": elements.hair.value,
                    "眼睛": elements.eyes.value
                },
                "表情与动作": {
                    "情绪": elements.emotion.value,
                    "动作": elements.action.value
                },
                "服装": {
                    "穿着": elements.clothing.value,
                    // Note: Clothing Detail field removed in simplified HTML to save space, skipping or mocking?
                    // Re-adding if needed, but for now let's map what we have.
                    // "细节": ... 
                },
                "配饰": elements.accessories.value
            },
            "背景": {
                "描述": elements.background.value,
                // "景深": ...
            }
        },
        "相机": {
            "机位角度": elements.angle.value,
            "构图": elements.composition.value,
            "镜头特性": elements.lensCharacteristics.value,
            "传感器画质": elements.sensorQuality.value
        },
        "审美控制": {
            "呈现意图": elements.intent.value,
            "材质真实度": materialRealismArray.length > 0 ? materialRealismArray : [elements.materialRealism.value],
            "色彩风格": {
                "整体色调": elements.overallTone.value,
                "对比度": elements.contrast.value,
                "特殊效果": elements.specialEffects.value
            }
        }
    };

    // Add Special Requirements if enabled
    if (elements.specialRequirementEnabled.checked) {
        data["特别要求"] = elements.specialRequirementInput.value;
    }

    // Add Line Art if enabled
    if (elements.lineArtModeEnabled.checked) {
        data["角色线稿生成"] = {
            "启用": true,
            "提示词": elements.lineArtPromptInput.value
        };
    }

    // Add Negative Prompt if enabled
    if (elements.negativePromptEnabled.checked) {
        const negativeElements = getCheckedValues(elements.negativeElementsContainer);
        const negativeStyles = getCheckedValues(elements.negativeStylesContainer);
        
        data["反向提示词"] = {
            "禁止元素": negativeElements,
            "禁止风格": negativeStyles
        };
    }

    return data;
}

function setFormData(data) {
    if (!data) return;

    function getValue(obj, ...path) {
        let current = obj;
        for (const key of path) {
            if (current === null || current === undefined) return '';
            current = current[key];
        }
        return current === null || current === undefined ? '' : current;
    }

    function arrayToString(val) {
        if (Array.isArray(val)) return val.join(', ');
        return val || '';
    }

    elements.styleMode.value = getValue(data, "风格模式");
    elements.atmosphere.value = getValue(data, "画面气质");

    elements.location.value = getValue(data, "场景", "环境", "地点设定");
    elements.lighting.value = getValue(data, "场景", "环境", "光线");
    elements.weather.value = getValue(data, "场景", "环境", "天气氛围");

    elements.description.value = getValue(data, "场景", "主体", "整体描述");
    elements.bodyShape.value = getValue(data, "场景", "主体", "外形特征", "身材");
    elements.face.value = getValue(data, "场景", "主体", "外形特征", "面部");
    elements.hair.value = getValue(data, "场景", "主体", "外形特征", "头发");
    elements.eyes.value = getValue(data, "场景", "主体", "外形特征", "眼睛");

    const emotionVal = getValue(data, "场景", "主体", "表情与动作", "情绪");
    const actionVal = getValue(data, "场景", "主体", "表情与动作", "动作");

    // Legacy support for merged string
    const expressionActionParams = getValue(data, "场景", "主体", "表情与动作");
    if (typeof expressionActionParams === 'string') {
        elements.action.value = expressionActionParams;
        elements.emotion.value = '';
    } else {
        elements.emotion.value = emotionVal;
        elements.action.value = actionVal;
    }

    elements.clothing.value = getValue(data, "场景", "主体", "服装", "穿着");
    elements.accessories.value = getValue(data, "场景", "主体", "配饰");
    elements.background.value = getValue(data, "场景", "背景", "描述");

    elements.angle.value = getValue(data, "相机", "机位角度");
    elements.composition.value = getValue(data, "相机", "构图");
    elements.lensCharacteristics.value = getValue(data, "相机", "镜头特性");
    elements.sensorQuality.value = getValue(data, "相机", "传感器画质");

    elements.intent.value = getValue(data, "审美控制", "呈现意图");
    elements.materialRealism.value = arrayToString(getValue(data, "审美控制", "材质真实度"));
    elements.overallTone.value = getValue(data, "审美控制", "色彩风格", "整体色调");
    elements.contrast.value = getValue(data, "审美控制", "色彩风格", "对比度");
    elements.specialEffects.value = getValue(data, "审美控制", "色彩风格", "特殊效果");

    // Special Requirements
    const specialReq = getValue(data, "特别要求");
    if (specialReq) {
        elements.specialRequirementEnabled.checked = true;
        elements.specialRequirementInput.value = specialReq;
        elements.specialRequirementGroup.style.display = 'block';
    } else {
        elements.specialRequirementEnabled.checked = false;
        elements.specialRequirementInput.value = '';
        elements.specialRequirementGroup.style.display = 'none';
    }

    // Line Art
    const lineArt = getValue(data, "角色线稿生成");
    if (lineArt && lineArt["启用"]) {
        elements.lineArtModeEnabled.checked = true;
        elements.lineArtPromptInput.value = lineArt["提示词"] || '';
        elements.lineArtGroup.style.display = 'block';
        // Trigger event to disable other fields (will add listener later)
        elements.lineArtModeEnabled.dispatchEvent(new Event('change'));
    } else {
        elements.lineArtModeEnabled.checked = false;
        elements.lineArtPromptInput.value = '';
        elements.lineArtGroup.style.display = 'none';
        elements.lineArtModeEnabled.dispatchEvent(new Event('change'));
    }

    // Negative Prompt
    const negativePrompt = getValue(data, "反向提示词");
    
    function setCheckedValues(container, values) {
        const checkboxes = container.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(cb => {
            cb.checked = values.includes(cb.value);
        });
    }

    if (negativePrompt) {
        elements.negativePromptEnabled.checked = true;
        elements.negativePromptGroup.style.display = 'flex';
        
        const negativeElements = negativePrompt["禁止元素"] || [];
        const negativeStyles = negativePrompt["禁止风格"] || [];
        
        setCheckedValues(elements.negativeElementsContainer, negativeElements);
        setCheckedValues(elements.negativeStylesContainer, negativeStyles);
    } else {
        elements.negativePromptEnabled.checked = false;
        elements.negativePromptGroup.style.display = 'none';
        setCheckedValues(elements.negativeElementsContainer, []);
        setCheckedValues(elements.negativeStylesContainer, []);
    }

    // Trigger update for preview
    updateJsonPreview();
}

function clearForm() {
    Object.values(elements).forEach(el => {
        if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT')) {
            if (!el.id.startsWith('gen') && !el.id.startsWith('config') && el.id !== 'presetSelect') {
                if (el.type === 'checkbox') {
                    el.checked = false;
                    el.dispatchEvent(new Event('change'));
                } else {
                    el.value = '';
                }
            }
        }
    });
    // Clear negative prompt checkboxes
    [elements.negativeElementsContainer, elements.negativeStylesContainer].forEach(container => {
        if (container) {
            container.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
        }
    });

    updateJsonPreview();
}

function updateJsonPreview() {
    let finalOutput = "";

    if (elements.lineArtModeEnabled.checked) {
        // Line Art Mode: Use raw prompt + special requirements
        let prompt = elements.lineArtPromptInput.value.trim();
        if (elements.specialRequirementEnabled.checked) {
            const special = elements.specialRequirementInput.value.trim();
            if (special) {
                prompt += "\n\n额外要求：" + special;
            }
        }
        finalOutput = prompt;
    } else {
        // Normal Mode: Use JSON + special requirements
        const data = getFormData();
        let jsonStr = JSON.stringify(data, null, 2);
        
        if (elements.specialRequirementEnabled.checked) {
            const special = elements.specialRequirementInput.value.trim();
            if (special) {
                // Append special requirements outside of JSON
                jsonStr += "\n\n特别要求：" + special;
            }
        }
        finalOutput = jsonStr;
    }
    
    elements.jsonPreviewText.value = finalOutput;
}

// ========================================
// Config Management
// ========================================
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        state.config = config;
    } catch (error) {
        console.error('Load config error:', error);
    }
}

function openConfigModal() {
    elements.configBaseUrl.value = state.config.base_url || '';
    elements.configApiKey.value = ''; // Don't show API key
    elements.configModel.value = state.config.model || '';

    elements.configGeminiBaseUrl.value = state.config.gemini_base_url || '';
    elements.configGeminiApiKey.value = '';
    elements.configGeminiModel.value = state.config.gemini_model || '';

    elements.configModal.classList.add('active');
}

async function saveConfigs() {
    const payload = {
        base_url: elements.configBaseUrl.value,
        api_key: elements.configApiKey.value,
        model: elements.configModel.value,
        gemini_base_url: elements.configGeminiBaseUrl.value,
        gemini_api_key: elements.configGeminiApiKey.value,
        gemini_model: elements.configGeminiModel.value
    };

    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (response.ok) {
            showToast('配置保存成功', 'success');
            elements.configModal.classList.remove('active');
            loadConfig();
        } else {
            showToast('保存失败', 'error');
        }
    } catch (e) {
        showToast('保存出错: ' + e, 'error');
    }
}

// ========================================
// Image Upload for Reference (Shared)
// ========================================
function handleImageUpload(e) {
    const files = Array.from(e.target.files);
    files.forEach(file => {
        if (!file.type.startsWith('image/')) {
            showToast('请选择图片', 'error');
            return;
        }
        const reader = new FileReader();
        reader.onload = (evt) => {
            const data = evt.target.result;
            if (state.uploadedImages.length >= 3) {
                showToast('最多上传3张', 'warning');
                return;
            }
            state.uploadedImages.push(data);
            renderUploadedImages();
        };
        reader.readAsDataURL(file);
    });
    e.target.value = ''; // reset
}

function renderUploadedImages() {
    elements.imagePreview.innerHTML = '';
    state.uploadedImages.forEach((data, idx) => {
        const div = document.createElement('div');
        div.className = 'image-preview-item';
        div.style.position = 'relative';

        const img = document.createElement('img');
        img.src = data;
        img.style.objectFit = 'cover';
        img.style.borderRadius = '4px';
        img.style.cursor = 'pointer';
        img.onclick = (e) => {
            e.stopPropagation();
            openImagePreview(data);
        };

        const btn = document.createElement('button');
        btn.innerHTML = '×';
        btn.style.position = 'absolute';
        btn.style.top = '-5px';
        btn.style.right = '-5px';
        btn.style.background = 'red';
        btn.style.color = 'white';
        btn.style.border = 'none';
        btn.style.borderRadius = '50%';
        btn.style.width = '18px';
        btn.style.height = '18px';
        btn.style.cursor = 'pointer';
        btn.onclick = () => {
            state.uploadedImages.splice(idx, 1);
            renderUploadedImages();
        };

        div.appendChild(img);
        div.appendChild(btn);
        elements.imagePreview.appendChild(div);
    });
}

// ========================================
// AI Generate Prompt / Modify Prompt
// ========================================
let currentAiMode = null; // 'generate' or 'modify'
let aiUploadedImages = []; // Local images for AI modal
let aiAbortController = null;
let latestDiffChanges = []; // Store diff changes

// ========================================
// Diff Utils
// ========================================
function isObject(item) {
    return (item && typeof item === 'object' && !Array.isArray(item));
}

function diffJson(obj1, obj2, path = []) {
    let changes = [];
    
    // Union of keys
    const keys1 = isObject(obj1) ? Object.keys(obj1) : [];
    const keys2 = isObject(obj2) ? Object.keys(obj2) : [];
    const allKeys = new Set([...keys1, ...keys2]);

    for (const key of allKeys) {
        const val1 = isObject(obj1) ? obj1[key] : undefined;
        const val2 = isObject(obj2) ? obj2[key] : undefined;
        const currentPath = [...path, key];

        if (isObject(val1) && isObject(val2)) {
            changes = changes.concat(diffJson(val1, val2, currentPath));
        } else if (Array.isArray(val1) && Array.isArray(val2)) {
            // Simple array comparison
            if (JSON.stringify(val1) !== JSON.stringify(val2)) {
                changes.push({
                    path: currentPath,
                    pathStr: currentPath.join(' > '),
                    oldValue: val1,
                    newValue: val2
                });
            }
        } else if (val1 !== val2) {
             // Ignore if both are empty/null/undefined equivalent
             const v1Empty = val1 === null || val1 === undefined || val1 === '';
             const v2Empty = val2 === null || val2 === undefined || val2 === '';
             if (v1Empty && v2Empty) continue;

             changes.push({
                path: currentPath,
                pathStr: currentPath.join(' > '),
                oldValue: val1 === undefined ? '(空)' : val1,
                newValue: val2 === undefined ? '(删除)' : val2
             });
        }
    }
    return changes;
}

function renderDiff(changes) {
    elements.aiDiffContainer.innerHTML = '';
    latestDiffChanges = changes;
    
    if (changes.length === 0) {
        elements.aiDiffContainer.innerHTML = '<div class="empty-state">未检测到更改</div>';
        return;
    }

    changes.forEach((change, idx) => {
        const item = document.createElement('div');
        item.className = 'diff-item';
        
        const header = document.createElement('div');
        header.style.display = 'flex';
        header.style.alignItems = 'center';
        header.style.marginBottom = '5px';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = true;
        checkbox.id = `diff-check-${idx}`;
        checkbox.dataset.idx = idx;
        
        const label = document.createElement('label');
        label.htmlFor = `diff-check-${idx}`;
        label.textContent = change.pathStr;
        label.style.marginLeft = '8px';
        label.style.fontWeight = 'bold';
        label.style.cursor = 'pointer';

        header.appendChild(checkbox);
        header.appendChild(label);

        const content = document.createElement('div');
        content.style.marginLeft = '24px';
        content.style.fontSize = '13px';

        // Format values for display
        const formatVal = (v) => {
            if (Array.isArray(v)) return JSON.stringify(v);
            return v;
        };

        const oldDiv = document.createElement('div');
        oldDiv.className = 'diff-old';
        oldDiv.textContent = `旧: ${formatVal(change.oldValue)}`;
        
        const newDiv = document.createElement('div');
        newDiv.className = 'diff-new';
        newDiv.textContent = `新: ${formatVal(change.newValue)}`;

        content.appendChild(oldDiv);
        content.appendChild(newDiv);

        item.appendChild(header);
        item.appendChild(content);
        
        elements.aiDiffContainer.appendChild(item);
    });
}

function handleAiImageUpload(e) {
    const files = Array.from(e.target.files);
    files.forEach(file => {
        if (!file.type.startsWith('image/')) {
            showToast('请选择图片', 'error');
            return;
        }
        const reader = new FileReader();
        reader.onload = (evt) => {
            const data = evt.target.result;
            if (aiUploadedImages.length >= 3) {
                showToast('最多上传3张', 'warning');
                return;
            }
            aiUploadedImages.push(data);
            renderAiUploadedImages();
        };
        reader.readAsDataURL(file);
    });
    e.target.value = ''; // reset
}

function renderAiUploadedImages() {
    elements.aiImagePreview.innerHTML = '';
    aiUploadedImages.forEach((data, idx) => {
        const div = document.createElement('div');
        div.className = 'image-preview-item';
        div.style.position = 'relative';

        const img = document.createElement('img');
        img.src = data;
        img.style.objectFit = 'cover';
        img.style.borderRadius = '4px';
        img.style.cursor = 'pointer';
        img.onclick = (e) => {
            e.stopPropagation();
            openImagePreview(data);
        };

        const btn = document.createElement('button');
        btn.innerHTML = '×';
        btn.style.position = 'absolute';
        btn.style.top = '-5px';
        btn.style.right = '-5px';
        btn.style.background = 'red';
        btn.style.color = 'white';
        btn.style.border = 'none';
        btn.style.borderRadius = '50%';
        btn.style.width = '18px';
        btn.style.height = '18px';
        btn.style.cursor = 'pointer';
        btn.onclick = () => {
            aiUploadedImages.splice(idx, 1);
            renderAiUploadedImages();
        };

        div.appendChild(img);
        div.appendChild(btn);
        elements.aiImagePreview.appendChild(div);
    });
}

function openAiModal(mode) {
    currentAiMode = mode;
    elements.aiModal.classList.add('active');
    
    // Reset State
    elements.aiPromptInput.value = '';
    elements.aiResponsePreview.value = '';
    elements.aiStatusText.textContent = '';
    aiUploadedImages = [];
    renderAiUploadedImages();
    latestDiffChanges = [];

    // Reset View
    elements.aiDiffContainer.style.display = 'none';
    elements.aiResponsePreview.style.display = 'block';
    elements.aiDiffContainer.innerHTML = '';
    
    // Reset Buttons
    elements.aiModalExecuteBtn.style.display = 'inline-block';
    elements.aiModalExecuteBtn.disabled = false;
    elements.aiModalStopBtn.style.display = 'none';
    elements.aiModalApplyBtn.style.display = 'none';

    if (mode === 'generate') {
        elements.aiModalTitle.textContent = 'AI 生成提示词';
        elements.aiModalLabel.textContent = '描述你想要的画面';
    } else {
        elements.aiModalTitle.textContent = 'AI 修改提示词';
        elements.aiModalLabel.textContent = '描述修改要求';
    }
}

async function handleAiExecute() {
    const prompt = elements.aiPromptInput.value.trim();
    if (!prompt) {
        showToast('请输入内容', 'warning');
        return;
    }

    // UI Update
    elements.aiResponsePreview.value = '';
    elements.aiStatusText.textContent = '正在思考...';
    elements.aiModalExecuteBtn.style.display = 'none';
    elements.aiModalStopBtn.style.display = 'inline-block';
    elements.aiModalApplyBtn.style.display = 'none';
    
    // Create AbortController
    aiAbortController = new AbortController();
    const signal = aiAbortController.signal;

    try {
        let url = currentAiMode === 'generate' ? '/api/generate' : '/api/modify';
        let body = {
            images: aiUploadedImages // Use local images
        };

        if (currentAiMode === 'generate') {
            body.prompt = prompt;
        } else {
            body.current_data = elements.jsonPreviewText.value;
            body.modify_request = prompt;
        }

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            signal: signal
        });

        if (!response.ok) throw new Error('API request failed');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6);
                    if (dataStr === '[DONE]') {
                        elements.aiStatusText.textContent = '生成完成';
                        elements.aiModalStopBtn.style.display = 'none';
                        elements.aiModalApplyBtn.style.display = 'inline-block';
                        elements.aiModalExecuteBtn.style.display = 'inline-block';

                        // Logic for Modify Mode: Show Diff
                        if (currentAiMode === 'modify') {
                            try {
                                let jsonText = fullContent;
                                // Try to extract JSON from Markdown
                                const jsonMatch = jsonText.match(/```json\s*([\s\S]*?)\s*```/);
                                if (jsonMatch) {
                                    jsonText = jsonMatch[1];
                                } else {
                                     const firstBrace = jsonText.indexOf('{');
                                     const lastBrace = jsonText.lastIndexOf('}');
                                     if (firstBrace !== -1 && lastBrace !== -1) {
                                         jsonText = jsonText.substring(firstBrace, lastBrace + 1);
                                     }
                                }
                                
                                const newData = JSON.parse(jsonText);
                                const currentData = getFormData();
                                const changes = diffJson(currentData, newData);
                                
                                renderDiff(changes);
                                
                                // Switch View
                                elements.aiResponsePreview.style.display = 'none';
                                elements.aiDiffContainer.style.display = 'block';
                                
                            } catch (e) {
                                console.error('Diff calculation failed:', e);
                                showToast('对比生成失败，显示原始结果', 'warning');
                                // Fallback to raw view
                                elements.aiResponsePreview.style.display = 'block';
                                elements.aiDiffContainer.style.display = 'none';
                            }
                        }
                    } else {
                        try {
                            const parsed = JSON.parse(dataStr);
                            if (parsed.content) {
                                fullContent += parsed.content;
                                elements.aiResponsePreview.value = fullContent;
                                elements.aiResponsePreview.scrollTop = elements.aiResponsePreview.scrollHeight;
                            }
                            if (parsed.error) throw new Error(parsed.error);
                        } catch (e) {
                            // ignore partial chunks
                        }
                    }
                }
            }
        }

    } catch (e) {
        if (e.name === 'AbortError') {
            elements.aiStatusText.textContent = '已停止';
            showToast('已停止生成', 'info');
        } else {
            elements.aiStatusText.textContent = '错误: ' + e.message;
            showToast('错误: ' + e.message, 'error');
        }
        elements.aiModalStopBtn.style.display = 'none';
        elements.aiModalExecuteBtn.style.display = 'inline-block';
    } finally {
        aiAbortController = null;
    }
}

function handleAiStop() {
    if (aiAbortController) {
        aiAbortController.abort();
    }
}

function applyAiResult() {
    try {
        // If in Modify Mode and Diff View is active
        if (currentAiMode === 'modify' && elements.aiDiffContainer.style.display !== 'none') {
            const checkboxes = elements.aiDiffContainer.querySelectorAll('input[type="checkbox"]');
            const data = getFormData(); // Start with current data
            
            let appliedCount = 0;
            checkboxes.forEach(cb => {
                if (cb.checked) {
                    const idx = parseInt(cb.dataset.idx);
                    const change = latestDiffChanges[idx];
                    if (change) {
                        // Apply change to data object
                        // Helper to set deep value
                        let current = data;
                        for (let i = 0; i < change.path.length - 1; i++) {
                            const key = change.path[i];
                            if (!current[key]) current[key] = {};
                            current = current[key];
                        }
                        const lastKey = change.path[change.path.length - 1];
                        
                        if (change.newValue === undefined) {
                            delete current[lastKey];
                        } else {
                            current[lastKey] = change.newValue;
                        }
                        appliedCount++;
                    }
                }
            });
            
            setFormData(data);
            showToast(`已应用 ${appliedCount} 项更改`, 'success');
            elements.aiModal.classList.remove('active');
            return;
        }

        // Fallback / Generate Mode Logic
        const jsonText = elements.aiResponsePreview.value;
        // Attempt to find JSON if wrapped in markdown
        let cleanJson = jsonText;
        const jsonMatch = jsonText.match(/```json\s*([\s\S]*?)\s*```/);
        if (jsonMatch) {
            cleanJson = jsonMatch[1];
        } else {
             // Try to find the first '{' and last '}'
             const firstBrace = jsonText.indexOf('{');
             const lastBrace = jsonText.lastIndexOf('}');
             if (firstBrace !== -1 && lastBrace !== -1) {
                 cleanJson = jsonText.substring(firstBrace, lastBrace + 1);
             }
        }

        const jsonData = JSON.parse(cleanJson);
        setFormData(jsonData);
        showToast('已应用到表单', 'success');
        elements.aiModal.classList.remove('active');
    } catch (e) {
        showToast('JSON 解析失败，请检查生成内容', 'error');
    }
}

// ========================================
// Image Generation
// ========================================
async function generateImage() {
    // 移动端点击生成后自动关闭侧边栏
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    if (sidebar) sidebar.classList.remove('open');
    if (sidebarOverlay) sidebarOverlay.classList.remove('active');

    const prompt = elements.jsonPreviewText.value;
    if (!prompt || prompt.length < 5) {
        showToast('请先配置提示词', 'warning');
        return;
    }

    elements.generateImageBtn.disabled = true;
    elements.generateImageBtn.innerHTML = '⏳ 生成中...';
    elements.resultPreview.innerHTML = '<div class="empty-state"><p>生成中...</p></div>';

    try {
        const response = await fetch('/api/generate-image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: prompt,
                images: state.uploadedImages,
                aspect_ratio: elements.genAspectRatio.value,
                image_size: elements.genImageSize.value,
                // thinking_level: elements.genThinkingLevel.value // Removed
            })
        });

        const data = await response.json();

        if (response.ok && data.image) {
            state.currentGeneratedImage = data.image;
            
            elements.resultPreview.innerHTML = `
                <div class="generated-result-container" style="position: relative; text-align: center; width: 100%;">
                    <div style="position: relative; display: inline-block; max-width: 100%;">
                        <img src="${data.image}" alt="Generated Image" 
                             style="cursor: zoom-in; max-width: 100%; max-height: 300px; object-fit: contain; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); transition: transform 0.2s;"
                             onmouseover="this.style.transform='scale(1.01)'"
                             onmouseout="this.style.transform='scale(1)'"
                             onclick="openImagePreview('${data.image}')">
                        <div style="position: absolute; bottom: 10px; right: 10px; background: rgba(0,0,0,0.6); padding: 5px; border-radius: 4px;">
                            <span style="color: white; font-size: 12px;">🔍 点击放大</span>
                        </div>
                    </div>
                </div>
            `;
            showToast('图片生成成功!', 'success');
        } else {
            throw new Error(data.error || '生成失败');
        }

    } catch (e) {
        showToast('生成错误: ' + e.message, 'error');
        elements.resultPreview.innerHTML = `
            <div class="empty-state">
                <p style="color: var(--error-color)">生成失败</p>
                <p class="hint">${e.message}</p>
            </div>
        `;
    } finally {
        elements.generateImageBtn.disabled = false;
        elements.generateImageBtn.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z" />
            </svg>
            生成图片
        `;
    }
}

function openImagePreview(src) {
    const modal = document.getElementById('imagePreviewModal');
    const img = document.getElementById('fullImagePreview');
    const downloadBtn = document.getElementById('downloadFullImageBtn');
    
    if (modal && img) {
        img.src = src;
        modal.classList.add('active');
        
        // Close on background click
        modal.onclick = (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        };
        
        // Setup download button in modal
        if (downloadBtn) {
            downloadBtn.onclick = () => downloadImage(src);
        }
    }
}

function downloadImage(dataUrl) {
    if (!dataUrl) return;
    
    const link = document.createElement('a');
    link.href = dataUrl;
    
    // Determine extension
    let ext = 'png';
    if (dataUrl.startsWith('data:image/jpeg')) ext = 'jpg';
    if (dataUrl.startsWith('data:image/webp')) ext = 'webp';
    
    link.download = `generated-${new Date().getTime()}.${ext}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// ========================================
// Init
// ========================================
function init() {
    loadConfig();

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

    // Form inputs change -> update JSON
    document.querySelectorAll('.app-container input, .app-container textarea').forEach(el => {
        if (!el.id.startsWith('gen') && !el.id.startsWith('ai') && !el.id.startsWith('config')) {
            el.addEventListener('input', updateJsonPreview);
        }
    });

    // Copy JSON
    elements.copyJsonBtn.addEventListener('click', () => {
        if (!elements.jsonPreviewText.value) return;
        navigator.clipboard.writeText(elements.jsonPreviewText.value).then(() => {
            showToast('已复制 JSON');
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
    updateFieldSuggestions();

    // Init Advanced Settings
    initAdvancedSettings();

    elements.presetSelect.addEventListener('change', async () => {
        const name = elements.presetSelect.value;
        if (name) {
            try {
                const res = await fetch(`/api/presets/${name}`);
                const data = await res.json();
                setFormData(data);
                showToast('预设加载成功');
            } catch (e) { console.error(e); }
        }
    });

    // Save Preset
    elements.savePresetBtn.addEventListener('click', async () => {
        const name = prompt('预设名称:');
        if (!name) return;
        const data = getFormData();
        await fetch('/api/presets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, data })
        });
        showToast('保存成功');
        loadPresets();
        updateFieldSuggestions();
    });

    // Delete Preset
    elements.deletePresetBtn.addEventListener('click', async () => {
        const name = elements.presetSelect.value;
        if (!name) return;
        if (!confirm('确定删除?')) return;
        await fetch(`/api/presets/${name}`, { method: 'DELETE' });
        showToast('删除成功');
        loadPresets();
        updateFieldSuggestions();
    });
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
        const allInputs = document.querySelectorAll('.app-container input, .app-container textarea, .app-container select');
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

    // Load Negative Prompt Options
    try {
        const res = await fetch('/api/options');
        const options = await res.json();
        
        const renderCheckboxes = (container, items) => {
            container.innerHTML = '';
            if (!items || items.length === 0) {
                container.innerHTML = '<span style="color: var(--text-tertiary);">无选项</span>';
                return;
            }
            items.forEach(item => {
                const label = document.createElement('label');
                label.style.display = 'flex';
                label.style.alignItems = 'center';
                label.style.marginRight = '10px';
                label.style.cursor = 'pointer';
                label.style.fontSize = '12px';
                
                const cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.value = item;
                cb.style.marginRight = '4px';
                cb.addEventListener('change', updateJsonPreview);
                
                label.appendChild(cb);
                label.appendChild(document.createTextNode(item));
                container.appendChild(label);
            });
        };

        renderCheckboxes(elements.negativeElementsContainer, options['禁止元素']);
        renderCheckboxes(elements.negativeStylesContainer, options['禁止风格']);

    } catch (e) {
        console.error('Failed to load options for negative prompts', e);
    }
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

// ========================================
// Field Suggestions from Presets
// ========================================
const fieldPresetPaths = {
    styleMode: ["风格模式"],
    atmosphere: ["画面气质"],
    location: ["场景", "环境", "地点设定"],
    lighting: ["场景", "环境", "光线"],
    weather: ["场景", "环境", "天气氛围"],
    description: ["场景", "主体", "整体描述"],
    bodyShape: ["场景", "主体", "外形特征", "身材"],
    face: ["场景", "主体", "外形特征", "面部"],
    hair: ["场景", "主体", "外形特征", "头发"],
    eyes: ["场景", "主体", "外形特征", "眼睛"],
    emotion: ["场景", "主体", "表情与动作", "情绪"],
    action: ["场景", "主体", "表情与动作", "动作"],
    clothing: ["场景", "主体", "服装", "穿着"],
    accessories: ["场景", "主体", "配饰"],
    background: ["场景", "背景", "描述"],
    angle: ["相机", "机位角度"],
    composition: ["相机", "构图"],
    lensCharacteristics: ["相机", "镜头特性"],
    sensorQuality: ["相机", "传感器画质"],
    intent: ["审美控制", "呈现意图"],
    materialRealism: ["审美控制", "材质真实度"],
    overallTone: ["审美控制", "色彩风格", "整体色调"],
    contrast: ["审美控制", "色彩风格", "对比度"],
    specialEffects: ["审美控制", "色彩风格", "特殊效果"],
};

function getNestedValue(obj, path) {
    let current = obj;
    for (const key of path) {
        if (current === null || current === undefined) return undefined;
        current = current[key];
    }
    return current;
}

async function updateFieldSuggestions() {
    try {
        const res = await fetch('/api/presets');
        const list = await res.json();
        const presetDataList = await Promise.all(
            list.map(async (p) => {
                try {
                    const r = await fetch(`/api/presets/${p.name}`);
                    return await r.json();
                } catch (e) { return null; }
            })
        );

        for (const [fieldId, path] of Object.entries(fieldPresetPaths)) {
            const values = new Set();
            presetDataList.forEach(data => {
                if (!data) return;
                const val = getNestedValue(data, path);
                if (val !== null && val !== undefined) {
                    const str = Array.isArray(val) ? val.join(', ') : String(val);
                    if (str.trim()) values.add(str.trim());
                }
            });

            const el = document.getElementById(fieldId);
            if (!el) continue;

            if (el.tagName === 'INPUT') {
                const datalistId = `dl-${fieldId}`;
                let datalist = document.getElementById(datalistId);
                if (values.size === 0) {
                    if (datalist) { datalist.remove(); el.removeAttribute('list'); }
                    continue;
                }
                if (!datalist) {
                    datalist = document.createElement('datalist');
                    datalist.id = datalistId;
                    document.body.appendChild(datalist);
                }
                datalist.innerHTML = '';
                values.forEach(v => {
                    const opt = document.createElement('option');
                    opt.value = v;
                    datalist.appendChild(opt);
                });
                el.setAttribute('list', datalistId);
            } else if (el.tagName === 'TEXTAREA') {
                const selectId = `ps-${fieldId}`;
                let select = document.getElementById(selectId);
                if (values.size === 0) {
                    if (select) select.remove();
                    continue;
                }
                if (!select) {
                    select = document.createElement('select');
                    select.id = selectId;
                    select.className = 'preset-suggest-select';
                    select.addEventListener('change', () => {
                        if (select.value) {
                            el.value = select.value;
                            el.dispatchEvent(new Event('input'));
                            select.value = '';
                        }
                    });
                    el.parentNode.insertBefore(select, el.nextSibling);
                }
                select.innerHTML = '<option value="">从预设选择...</option>';
                values.forEach(v => {
                    const opt = document.createElement('option');
                    opt.value = v;
                    opt.textContent = v.length > 50 ? v.substring(0, 50) + '...' : v;
                    select.appendChild(opt);
                });
            }
        }
    } catch (e) {
        console.error('Failed to update field suggestions:', e);
    }
}

document.addEventListener('DOMContentLoaded', init);
