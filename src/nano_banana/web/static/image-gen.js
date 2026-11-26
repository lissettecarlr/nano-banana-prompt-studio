// ========================================
// Config Management
// ========================================
async function loadImageProviders() {
    try {
        const response = await fetch('/api/image-providers');
        if (!response.ok) throw new Error(response.statusText);
        state.imageProviders = await response.json();
        return true;
    } catch (error) {
        console.error('Load image providers error:', error);
        state.imageProviders = {};
        return false;
    }
}

const EMPTY_CONFIG = { chat: {}, image: { active: '', providers: {}, options: {} } };

async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) throw new Error(response.statusText);
        const config = await response.json();
        state.config = {
            chat: config.chat || {},
            image: { ...EMPTY_CONFIG.image, ...(config.image || {}) }
        };
        return true;
    } catch (error) {
        console.error('Load config error:', error);
        state.config = JSON.parse(JSON.stringify(EMPTY_CONFIG));
        return false;
    }
}

/**
 * 图片渠道的配置表单完全由 /api/image-providers 生成：
 * 后端新增一个渠道（ProviderSpec）后，这里不需要改任何代码。
 */
function renderImageProviderConfigFields() {
    const select = elements.configImageProvider;
    const container = elements.configImageProviderFields;
    select.replaceChildren();
    container.replaceChildren();

    Object.values(state.imageProviders || {}).forEach(provider => {
        select.add(new Option(provider.label || provider.id, provider.id));

        const addField = (key, labelText, input) => {
            const group = document.createElement('div');
            group.className = 'form-group image-config-group';
            group.dataset.providerConfig = provider.id;
            const label = document.createElement('label');
            label.textContent = `${provider.label} ${labelText}`;
            input.dataset.providerId = provider.id;
            input.dataset.configKey = key;
            input.id = `config-${provider.id}-${key}`;
            label.htmlFor = input.id;
            group.append(label, input);
            container.appendChild(group);
        };

        const baseUrl = document.createElement('input');
        baseUrl.type = 'text';
        baseUrl.className = 'text-input';
        baseUrl.placeholder = provider.url_placeholder || provider.default_base_url || '';
        baseUrl.value = provider.base_url || provider.default_base_url || '';
        addField('base_url', 'Base URL', baseUrl);

        const apiKey = document.createElement('input');
        apiKey.type = 'password';
        apiKey.className = 'text-input';
        apiKey.autocomplete = 'off';
        apiKey.placeholder = provider.has_api_key ? '已保存，留空则不修改' : '';
        addField('api_key', 'API Key', apiKey);

        // 模型可自由输入，建议值通过 datalist 给出
        const model = document.createElement('input');
        model.type = 'text';
        model.className = 'text-input';
        model.placeholder = provider.default_model || '';
        model.value = provider.model || provider.default_model || '';
        const suggestions = document.createElement('datalist');
        suggestions.id = `config-${provider.id}-models`;
        (provider.models || []).forEach(name => suggestions.appendChild(new Option(name, name)));
        model.setAttribute('list', suggestions.id);
        addField('model', 'Model', model);
        container.appendChild(suggestions);
    });
}

function openConfigModal() {
    const chat = state.config.chat || {};
    elements.configBaseUrl.value = chat.base_url || '';
    elements.configApiKey.value = ''; // Don't show API key
    elements.configApiKey.placeholder = chat.has_api_key ? '已保存，留空则不修改' : '';
    elements.configModel.value = chat.model || '';

    renderImageProviderConfigFields();
    const preferred = getActiveImageProvider() || state.config.image.active;
    if (state.imageProviders[preferred]) {
        elements.configImageProvider.value = preferred;
    }
    updateImageConfigVisibility();

    elements.configModal.classList.add('active');
}

async function saveConfigs() {
    const chat = {
        base_url: elements.configBaseUrl.value,
        model: elements.configModel.value
    };
    if (elements.configApiKey.value) chat.api_key = elements.configApiKey.value;

    const providers = {};
    elements.configImageProviderFields.querySelectorAll('[data-config-key]').forEach(input => {
        const key = input.dataset.configKey;
        // 密钥留空 = 不修改，避免把已保存的密钥清掉
        if (key === 'api_key' && !input.value) return;
        (providers[input.dataset.providerId] ||= {})[key] = input.value;
    });

    const selectedProvider = elements.configImageProvider.value;
    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat, image: { providers } })
        });
        if (response.ok) {
            await Promise.all([loadConfig(), loadImageProviders()]);
            await renderImageGenerationControls(selectedProvider);
            showToast('配置保存成功', 'success');
            elements.configModal.classList.remove('active');
        } else {
            const error = await response.json().catch(() => ({}));
            showToast('保存失败: ' + (error.error || response.statusText), 'error');
        }
    } catch (e) {
        showToast('保存出错: ' + e, 'error');
    }
}

function getActiveImageProvider() {
    return state.activeImageProvider || elements.imageProviderSelect.value || '';
}

function getActiveImageModel() {
    return state.activeImageModel || elements.imageModelSelect.value || '';
}

function getAvailableImageProviders() {
    return Object.entries(state.imageProviders || {})
        .filter(([, config]) => config.is_configured);
}

async function renderImageGenerationControls(preferredProvider = '') {
    const availableProviders = getAvailableImageProviders();
    elements.imageProviderSelect.replaceChildren();

    if (availableProviders.length === 0) {
        const emptyOption = new Option('请先配置图片渠道', '');
        elements.imageProviderSelect.add(emptyOption);
        elements.imageProviderSelect.disabled = true;
        elements.imageModelSelect.replaceChildren();
        elements.imageModelSelect.add(new Option('暂无可用模型', ''));
        elements.imageModelSelect.disabled = true;
        state.activeImageProvider = '';
        state.activeImageModel = '';
        elements.imageProviderOptions.replaceChildren();
        updateImageGenerationAvailability();
        return;
    }

    availableProviders.forEach(([provider, config]) => {
        elements.imageProviderSelect.add(new Option(config.label || provider, provider));
    });
    elements.imageProviderSelect.disabled = false;

    const availableIds = availableProviders.map(([provider]) => provider);
    const selectedProvider = [preferredProvider, state.config.image.active]
        .find(provider => availableIds.includes(provider)) || availableIds[0];
    elements.imageProviderSelect.value = selectedProvider;
    state.activeImageProvider = selectedProvider;
    renderImageModelChoices(selectedProvider);
    await persistImageGenerationSettings(false, true);
}

function renderImageModelChoices(provider, preferredModel = '') {
    const providerConfig = state.imageProviders[provider];
    elements.imageModelSelect.replaceChildren();
    if (!providerConfig) {
        state.activeImageModel = '';
        elements.imageModelSelect.disabled = true;
        renderImageProviderOptions();
        return;
    }

    const configuredModel = providerConfig.configured_model
        || providerConfig.default_model
        || '';
    const models = [...(providerConfig.models || [])];
    if (configuredModel && !models.includes(configuredModel)) models.push(configuredModel);
    models.forEach(model => elements.imageModelSelect.add(new Option(model, model)));

    const selectedModel = [preferredModel, configuredModel, providerConfig.default_model]
        .find(model => model && models.includes(model)) || models[0] || '';
    elements.imageModelSelect.value = selectedModel;
    elements.imageModelSelect.disabled = models.length === 0;
    state.activeImageModel = selectedModel;
    renderImageProviderOptions();
}

function getSavedImageOptions(provider, model) {
    const allOptions = state.config.image.options || {};
    const providerOptions = allOptions[provider] || {};
    return providerOptions[model || '__default__'] || {};
}

function renderImageProviderOptions() {
    if (!elements.imageProviderOptions) return;

    const provider = getActiveImageProvider();
    const model = getActiveImageModel();
    const providerConfig = state.imageProviders[provider];
    const capabilities = providerConfig?.capabilities?.[model];
    const providerOptions = capabilities?.options || {};
    const savedOptions = getSavedImageOptions(provider, model);

    if (!providerConfig || Object.keys(providerOptions).length === 0) {
        elements.imageProviderOptions.replaceChildren();
        updateImageGenerationAvailability();
        return;
    }

    elements.imageProviderOptions.innerHTML = Object.entries(providerOptions).map(([key, option]) => {
        const values = option.values || [];
        const options = values.map(value => {
            const savedValue = savedOptions[key];
            const selectedValue = values.includes(savedValue) ? savedValue : option.default;
            const selected = value === selectedValue ? 'selected' : '';
            return `<option value="${value}" ${selected}>${value}</option>`;
        }).join('');

        return `
            <div class="form-group">
                <label>${option.label}</label>
                <select class="select-input image-option-input" data-option-key="${key}">
                    ${options}
                </select>
            </div>
        `;
    }).join('');

    document.querySelectorAll('.image-option-input').forEach(input => {
        input.addEventListener('change', () => persistImageGenerationSettings(true));
    });
    updateImageGenerationAvailability();
}

function collectImageOptions() {
    const options = {};
    document.querySelectorAll('.image-option-input').forEach(input => {
        options[input.dataset.optionKey] = input.value;
    });
    return options;
}

function persistImageGenerationSettings(includeOptions = true, quiet = false) {
    const save = () => saveImageGenerationSettings(includeOptions, quiet);
    state.imageSettingsSaveQueue = state.imageSettingsSaveQueue.then(save, save);
    return state.imageSettingsSaveQueue;
}

async function saveImageGenerationSettings(includeOptions, quiet) {
    const provider = getActiveImageProvider();
    const model = getActiveImageModel();
    if (!provider || !model) return false;

    const payload = { provider, model };
    if (includeOptions) payload.options = collectImageOptions();

    try {
        const response = await fetch('/api/image-generation-settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || response.statusText);
        }

        state.config.image.active = provider;
        const providerConfig = state.imageProviders[provider];
        providerConfig.configured_model = model;
        if (includeOptions) {
            const allOptions = (state.config.image.options ||= {});
            (allOptions[provider] ||= {})[model] = payload.options;
        }
        return true;
    } catch (error) {
        console.error('Save image generation settings error:', error);
        if (!quiet) showToast('生图设置保存失败: ' + error.message, 'error');
        return false;
    }
}

function renderImageProviderStatus() {
    const providers = Object.values(state.imageProviders || {});
    const configuredProviders = providers.filter(config => config.is_configured);
    const unconfiguredCount = providers.length - configuredProviders.length;

    elements.activeImageProvider.hidden = configuredProviders.length > 0;
    elements.activeImageProvider.textContent = configuredProviders.length === 0
        ? '尚未配置图片渠道，请点击右上角“设置”添加渠道密钥'
        : '';
    elements.imageProviderStatusButton.hidden = configuredProviders.length === 0;
    elements.imageProviderStatusButton.setAttribute(
        'aria-label',
        `图片渠道状态：${configuredProviders.length} 个已配置，${unconfiguredCount} 个未配置`
    );

    const popover = elements.imageProviderStatusPopover;
    popover.replaceChildren();
    const title = document.createElement('strong');
    title.className = 'provider-status-title';
    title.textContent = '图片渠道状态';
    popover.appendChild(title);
    providers.forEach(config => {
        const row = document.createElement('div');
        row.className = `provider-status-row${config.is_configured ? ' is-configured' : ''}`;
        const dot = document.createElement('span');
        dot.className = 'provider-status-dot';
        dot.setAttribute('aria-hidden', 'true');
        const label = document.createElement('span');
        label.textContent = config.label;
        const value = document.createElement('span');
        value.textContent = config.is_configured ? '已配置' : '未配置';
        row.append(dot, label, value);
        popover.appendChild(row);
    });
}

function setImageProviderStatusOpen(open) {
    if (elements.imageProviderStatusButton.hidden) open = false;
    elements.imageProviderStatus.classList.toggle('is-open', open);
    elements.imageProviderStatusButton.setAttribute('aria-expanded', String(open));
}

function updateImageGenerationAvailability() {
    const provider = getActiveImageProvider();
    const providerConfig = state.imageProviders[provider];
    const ready = Boolean(providerConfig?.is_configured && getActiveImageModel());

    renderImageProviderStatus();
    // 生成中按钮保持可点，作为取消入口
    elements.generateImageBtn.disabled = state.isGenerating ? false : !ready;
}

function updateImageConfigVisibility() {
    const provider = elements.configImageProvider.value;
    document.querySelectorAll('.image-config-group').forEach(group => {
        group.style.display = group.dataset.providerConfig === provider ? '' : 'none';
    });
}

// ========================================
// Image Upload for Reference (Shared)
// ========================================

/**
 * 把文件加入参考图列表（文件选择/拖拽/粘贴共用入口）。
 * 同步按剩余名额截断，修复多选时 FileReader 异步竞态导致超限的问题。
 */
function addImageFilesToList(files, list, renderFn, maxCount = 3) {
    const imageFiles = Array.from(files).filter(file => file.type.startsWith('image/'));
    if (!imageFiles.length) {
        showToast('请选择图片文件', 'error');
        return;
    }
    const remaining = maxCount - list.length;
    if (remaining <= 0) {
        showToast(`最多上传${maxCount}张`, 'warning');
        return;
    }
    if (imageFiles.length > remaining) {
        showToast(`最多上传${maxCount}张，已忽略多余的 ${imageFiles.length - remaining} 张`, 'warning');
    }
    imageFiles.slice(0, remaining).forEach(file => {
        const reader = new FileReader();
        reader.onload = evt => {
            list.push(evt.target.result);
            renderFn();
        };
        reader.readAsDataURL(file);
    });
}

function handleImageUpload(e) {
    addImageFilesToList(e.target.files, state.uploadedImages, renderUploadedImages);
    e.target.value = ''; // reset
}

/**
 * 拖拽 + 粘贴上传参考图。
 * 拖到生图面板上传区 / AI 弹窗上传区即可添加；
 * Ctrl+V 粘贴剪贴板图片：AI 弹窗打开时进弹窗，否则进生图参考图。
 */
function initImageUploadExtras() {
    const bindDropZone = (zone, list, renderFn) => {
        if (!zone) return;
        zone.addEventListener('dragover', e => {
            e.preventDefault();
            zone.classList.add('is-drag-over');
        });
        zone.addEventListener('dragleave', () => zone.classList.remove('is-drag-over'));
        zone.addEventListener('drop', e => {
            e.preventDefault();
            zone.classList.remove('is-drag-over');
            if (e.dataTransfer?.files?.length) {
                addImageFilesToList(e.dataTransfer.files, list, renderFn);
            }
        });
    };

    bindDropZone(
        document.querySelector('.reference-upload'),
        state.uploadedImages,
        renderUploadedImages
    );
    bindDropZone(
        document.querySelector('#aiModal .image-upload-area'),
        aiUploadedImages,
        renderAiUploadedImages
    );

    document.addEventListener('paste', e => {
        const files = Array.from(e.clipboardData?.files || [])
            .filter(file => file.type.startsWith('image/'));
        if (!files.length) return;
        e.preventDefault();
        if (elements.aiModal.classList.contains('active')) {
            addImageFilesToList(files, aiUploadedImages, renderAiUploadedImages);
            showToast('已粘贴到 AI 参考图');
        } else {
            addImageFilesToList(files, state.uploadedImages, renderUploadedImages);
            showToast('已粘贴到生图参考图');
        }
    });
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
// Image Generation
// ========================================
async function generateImage() {
    // 生成中再次点击 = 取消
    if (state.isGenerating) {
        if (state.imageGenAbortController) state.imageGenAbortController.abort();
        return;
    }

    // 移动端点击生成后自动关闭侧边栏
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    if (sidebar) sidebar.classList.remove('open');
    if (sidebarOverlay) sidebarOverlay.classList.remove('active');

    const provider = getActiveImageProvider();
    const model = getActiveImageModel();
    const providerConfig = state.imageProviders[provider];
    if (!providerConfig?.is_configured || !model) {
        showToast('请先完成当前图片渠道配置', 'warning');
        updateImageGenerationAvailability();
        return;
    }

    state.isGenerating = true;
    state.imageGenAbortController = new AbortController();
    updateImageGenerationAvailability();

    // 生成中状态：骨架屏 + 实时耗时反馈
    const genBtnDefaultHtml = elements.generateImageBtn.innerHTML;
    elements.resultPreview.classList.remove('has-error');
    elements.resultPreview.replaceChildren();
    const generatingState = document.createElement('div');
    generatingState.className = 'generating-state';
    const skeleton = document.createElement('div');
    skeleton.className = 'result-skeleton';
    const elapsedText = document.createElement('div');
    elapsedText.className = 'gen-elapsed';
    generatingState.appendChild(skeleton);
    generatingState.appendChild(elapsedText);
    elements.resultPreview.appendChild(generatingState);

    const stopTimer = startElapsedTimer(seconds => {
        elapsedText.innerHTML = `图片生成中 · 已耗时 <strong>${seconds}</strong> 秒`;
        elements.generateImageBtn.textContent = `取消生成 · ${seconds}s`;
    });

    try {
        const response = await fetch('/api/generate-image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            // 提交文档本身，最终提示词由服务端渲染（与预览同一份逻辑）
            body: JSON.stringify({
                document: getFormData(),
                images: state.uploadedImages,
                provider,
                model,
                options: collectImageOptions()
            }),
            signal: state.imageGenAbortController.signal
        });

        // 网关 502 等场景返回的可能是 HTML，直接 .json() 会抛
        // "Unexpected token" 这种没有意义的错误
        let data = null;
        try {
            data = await response.json();
        } catch (parseError) {
            data = null;
        }

        if (response.ok && data && data.image) {
            state.generationHistory.push(data.image);
            if (state.generationHistory.length > 8) state.generationHistory.shift();
            renderGenerationResult(data.image);
            showToast('图片生成成功!', 'success');
        } else {
            throw new Error(
                (data && data.error) || `请求失败 (HTTP ${response.status} ${response.statusText})`
            );
        }

    } catch (e) {
        if (e.name === 'AbortError') {
            if (state.generationHistory.length) {
                // 取消后回显最近一张历史图
                renderGenerationResult(state.generationHistory[state.generationHistory.length - 1]);
            } else {
                const cancelledState = document.createElement('div');
                cancelledState.className = 'empty-state';
                const text = document.createElement('p');
                text.textContent = '已取消生成';
                cancelledState.appendChild(text);
                elements.resultPreview.replaceChildren(cancelledState);
            }
            showToast('已取消生成');
        } else {
            showToast('生成错误: ' + e.message, 'error');
            elements.resultPreview.classList.add('has-error');
            const errorState = document.createElement('div');
            errorState.className = 'generation-error';
            errorState.setAttribute('role', 'alert');
            const title = document.createElement('strong');
            title.className = 'generation-error-title';
            title.textContent = '生成失败';
            const message = document.createElement('p');
            message.className = 'generation-error-message';
            message.textContent = e.message;
            errorState.appendChild(title);
            errorState.appendChild(message);
            elements.resultPreview.replaceChildren(errorState);
        }
    } finally {
        stopTimer();
        state.isGenerating = false;
        state.imageGenAbortController = null;
        updateImageGenerationAvailability();
        elements.generateImageBtn.innerHTML = genBtnDefaultHtml;
    }
}

/**
 * 渲染生成结果：大图 + 下载按钮 + 历史缩略图条。
 * 用 DOM 构建，避免把几 MB 的 dataURL 写进 HTML 属性。
 */
function renderGenerationResult(src) {
    state.currentGeneratedImage = src;
    elements.resultPreview.classList.remove('has-error');

    const container = document.createElement('div');
    container.className = 'generated-result-container';

    const wrap = document.createElement('div');
    wrap.className = 'generated-img-wrap';
    const img = document.createElement('img');
    img.src = src;
    img.alt = '生成结果';
    img.className = 'generated-img';
    img.addEventListener('click', () => openImagePreview(src));
    const hint = document.createElement('div');
    hint.className = 'img-zoom-hint';
    hint.textContent = '🔍 点击放大';
    wrap.appendChild(img);
    wrap.appendChild(hint);
    container.appendChild(wrap);

    const actions = document.createElement('div');
    actions.className = 'result-actions';
    const downloadBtn = document.createElement('button');
    downloadBtn.type = 'button';
    downloadBtn.className = 'btn btn-secondary btn-sm';
    downloadBtn.textContent = '下载图片';
    downloadBtn.addEventListener('click', () => downloadImage(src));
    actions.appendChild(downloadBtn);
    container.appendChild(actions);

    if (state.generationHistory.length > 1) {
        const strip = document.createElement('div');
        strip.className = 'result-history';
        strip.setAttribute('aria-label', '生成历史');
        state.generationHistory.forEach((item, idx) => {
            const thumb = document.createElement('img');
            thumb.src = item;
            thumb.className = 'result-history-thumb' + (item === src ? ' is-active' : '');
            thumb.alt = `历史结果 ${idx + 1}`;
            thumb.title = `查看第 ${idx + 1} 张`;
            thumb.addEventListener('click', () => renderGenerationResult(item));
            strip.appendChild(thumb);
        });
        container.appendChild(strip);
    }

    elements.resultPreview.replaceChildren(container);
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
