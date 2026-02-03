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

    // 预设
    presetSelect: document.getElementById('presetSelect'),
    savePresetBtn: document.getElementById('savePresetBtn'),
    deletePresetBtn: document.getElementById('deletePresetBtn'),

    // 顶部工具栏
    aiGenerateOpenBtn: document.getElementById('aiGenerateOpenBtn'),
    aiModifyOpenBtn: document.getElementById('aiModifyOpenBtn'),
    configBtn: document.getElementById('configBtn'),
    resetFormBtn: document.getElementById('resetFormBtn'),

    // JSON 预览
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

    return {
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

    // Trigger update for preview
    updateJsonPreview();
}

function clearForm() {
    Object.values(elements).forEach(el => {
        if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT')) {
            if (!el.id.startsWith('gen') && !el.id.startsWith('config') && el.id !== 'presetSelect') {
                el.value = '';
            }
        }
    });
    updateJsonPreview();
}

function updateJsonPreview() {
    const data = getFormData();
    elements.jsonPreviewText.value = JSON.stringify(data, null, 2);
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
        // img.style.width = '80px'; // Removed to fix size mismatch
        // img.style.height = '80px'; // Removed to fix size mismatch
        img.style.objectFit = 'cover';
        img.style.borderRadius = '4px';

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
        // img.style.width = '80px'; // Removed to fix size mismatch
        // img.style.height = '80px'; // Removed to fix size mismatch
        img.style.objectFit = 'cover';
        img.style.borderRadius = '4px';

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
    const prompt = elements.jsonPreviewText.value;
    if (!prompt || prompt.length < 5) {
        showToast('请先配置提示词', 'warning');
        return;
    }

    elements.generateImageBtn.disabled = true;
    elements.generateImageBtn.innerHTML = '⏳ 生成中... (Generating)';
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
                             style="cursor: zoom-in; max-width: 100%; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); transition: transform 0.2s;"
                             onmouseover="this.style.transform='scale(1.01)'"
                             onmouseout="this.style.transform='scale(1)'"
                             onclick="openImagePreview('${data.image}')">
                        <div style="position: absolute; bottom: 10px; right: 10px; background: rgba(0,0,0,0.6); padding: 5px; border-radius: 4px;">
                            <span style="color: white; font-size: 12px;">🔍 点击放大</span>
                        </div>
                    </div>
                    <div style="margin-top: 15px;">
                        <button onclick="downloadImage('${data.image}')" class="btn btn-primary" style="width: 100%;">⬇ 保存图片</button>
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
    });

    // Delete Preset
    elements.deletePresetBtn.addEventListener('click', async () => {
        const name = elements.presetSelect.value;
        if (!name) return;
        if (!confirm('确定删除?')) return;
        await fetch(`/api/presets/${name}`, { method: 'DELETE' });
        showToast('删除成功');
        loadPresets();
    });
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

document.addEventListener('DOMContentLoaded', init);
