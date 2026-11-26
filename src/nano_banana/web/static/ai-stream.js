// ========================================
// AI Generate Prompt / Modify Prompt
// ========================================
let currentAiMode = null; // 'generate' or 'modify'
let aiUploadedImages = []; // Local images for AI modal
let aiAbortController = null;
let latestDiffChanges = []; // 服务端算好的差异：[{ path, label, kind, old, new }]
let latestAiDocument = null; // 服务端解析并升级后的文档；解析失败时为 null

// ========================================
// Diff View
// ========================================
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
        label.textContent = change.label;
        label.style.marginLeft = '8px';
        label.style.fontWeight = 'bold';
        label.style.cursor = 'pointer';

        header.appendChild(checkbox);
        header.appendChild(label);

        const content = document.createElement('div');
        content.style.marginLeft = '24px';
        content.style.fontSize = '13px';

        const formatVal = (v, emptyText) => {
            if (v === null || v === undefined || v === '') return emptyText;
            return typeof v === 'object' ? JSON.stringify(v) : v;
        };

        const oldDiv = document.createElement('div');
        oldDiv.className = 'diff-old';
        oldDiv.textContent = `旧: ${formatVal(change.old, '(空)')}`;

        const newDiv = document.createElement('div');
        newDiv.className = 'diff-new';
        newDiv.textContent = `新: ${formatVal(change.new, change.kind === 'removed' ? '(删除)' : '(空)')}`;

        content.appendChild(oldDiv);
        content.appendChild(newDiv);

        item.appendChild(header);
        item.appendChild(content);
        
        elements.aiDiffContainer.appendChild(item);
    });
}

function handleAiImageUpload(e) {
    addImageFilesToList(e.target.files, aiUploadedImages, renderAiUploadedImages);
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
    // 原地清空：拖拽/粘贴上传的闭包持有该数组引用，不能重新赋值
    aiUploadedImages.length = 0;
    renderAiUploadedImages();
    latestDiffChanges = [];
    latestAiDocument = null;

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
    const imagesOnly = currentAiMode === 'generate' && aiUploadedImages.length > 0;
    if (!prompt && !imagesOnly) {
        showToast('请输入内容', 'warning');
        return;
    }
    latestDiffChanges = [];
    latestAiDocument = null;
    elements.aiDiffContainer.style.display = 'none';
    elements.aiResponsePreview.style.display = 'block';

    // UI Update
    elements.aiResponsePreview.value = '';
    elements.aiStatusText.textContent = '正在思考...';
    const thinkingStatusText = elements.aiStatusText.textContent;
    let streamStatusText = '';
    elements.aiModalExecuteBtn.style.display = 'none';
    elements.aiModalStopBtn.style.display = 'inline-block';
    elements.aiModalApplyBtn.style.display = 'none';

    // 耗时反馈：生成期间实时显示已耗时
    const stopStatusTimer = startElapsedTimer(seconds => {
        elements.aiStatusText.textContent = `正在生成 · 已耗时 ${seconds}s`;
        if (streamStatusText) {
            elements.aiStatusText.textContent = streamStatusText;
        }
    });
    let aiFinalStatus = '';

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
            body.document = getFormData();
            body.modify_request = prompt;
        }

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            signal: signal
        });

        if (!response.ok) {
            let message = `API request failed (${response.status})`;
            try {
                const payload = await response.json();
                message = payload.error || message;
            } catch (_error) {
                // Keep the HTTP fallback when the response is not JSON.
            }
            throw new Error(message);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';
        const sseParser = new SseStream.SseEventParser();
        let receivedDone = false;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const dataEvents = sseParser.push(decoder.decode(value));
            for (const dataStr of dataEvents) {

                    if (dataStr === '[DONE]') {
                        aiFinalStatus = '生成完成';
                        receivedDone = true;
                        elements.aiModalStopBtn.style.display = 'none';
                        elements.aiModalApplyBtn.style.display = 'inline-block';
                        elements.aiModalExecuteBtn.style.display = 'inline-block';

                        if (!latestAiDocument) {
                            showToast('AI 返回的内容无法解析，可手动修正后再应用', 'warning');
                        } else if (currentAiMode === 'modify') {
                            renderDiff(latestDiffChanges);
                            elements.aiResponsePreview.style.display = 'none';
                            elements.aiDiffContainer.style.display = 'block';
                        }
                    } else {
                        const event = SseStream.parseSseJsonEvent(dataStr);
                        if (event.type === 'status') {
                            if (event.status === 'thinking') {
                                streamStatusText = thinkingStatusText;
                            }
                        } else if (event.type === 'result') {
                            // 解析、旧格式兼容、差异计算都由服务端完成
                            latestAiDocument = event.result.document || null;
                            latestDiffChanges = event.result.changes || [];
                        } else if (event.type === 'content') {
                            streamStatusText = '';
                            fullContent += event.content;
                            elements.aiResponsePreview.value = fullContent;
                            elements.aiResponsePreview.scrollTop = elements.aiResponsePreview.scrollHeight;
                        }
                    }
            }
        }
        sseParser.finish();
        if (!receivedDone) {
            throw new Error('AI \u6d41\u5f0f\u54cd\u5e94\u610f\u5916\u4e2d\u65ad');
        }

    } catch (e) {
        if (e.name === 'AbortError') {
            aiFinalStatus = '已停止';
            showToast('已停止生成', 'info');
        } else {
            aiFinalStatus = '错误: ' + e.message;
            showToast('错误: ' + e.message, 'error');
        }
        elements.aiModalStopBtn.style.display = 'none';
        elements.aiModalExecuteBtn.style.display = 'inline-block';
    } finally {
        stopStatusTimer();
        if (aiFinalStatus) {
            elements.aiStatusText.textContent = aiFinalStatus;
        }
        aiAbortController = null;
    }
}

function handleAiStop() {
    if (aiAbortController) {
        aiAbortController.abort();
    }
}

function applyAiResult() {
    // 修改模式：只应用勾选的差异
    if (currentAiMode === 'modify' && elements.aiDiffContainer.style.display !== 'none') {
        const data = getFormData();
        let appliedCount = 0;
        elements.aiDiffContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            const change = latestDiffChanges[parseInt(cb.dataset.idx, 10)];
            if (!cb.checked || !change) return;
            if (change.kind === 'removed') {
                window.PromptDoc.deleteAtPath(data, change.path);
            } else {
                window.PromptDoc.setAtPath(data, change.path, change.new);
            }
            appliedCount++;
        });

        setFormData(data);
        showToast(`已应用 ${appliedCount} 项更改`, 'success');
        elements.aiModal.classList.remove('active');
        return;
    }

    let aiDocument = latestAiDocument;
    if (!aiDocument) {
        // 服务端没能解析出文档：允许用户在文本框里手动修正后再应用
        try {
            aiDocument = JSON.parse(elements.aiResponsePreview.value);
        } catch (e) {
            showToast('JSON 解析失败，请检查生成内容', 'error');
            return;
        }
    }
    applyAiDocument(aiDocument);
    showToast('已应用到表单', 'success');
    elements.aiModal.classList.remove('active');
}
