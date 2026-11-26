(() => {
    'use strict';

    let categoryOrder = ['basic', 'scene', 'subject', 'camera', 'aesthetic'];
    let categoryLabels = {
        basic: '基础设置',
        scene: '场景设置',
        subject: '主体细节',
        camera: '相机与构图',
        aesthetic: '调色与质感'
    };
    let categoryFields = {};
    let previewPaths = {};

    function hydrateFromSchema(schema) {
        if (!schema || !schema.categories) return;
        categoryOrder = schema.categories.map(category => category.id);
        categoryLabels = Object.fromEntries(
            schema.categories.map(category => [category.id, category.label])
        );
        categoryFields = Object.fromEntries(
            schema.categories.map(category => [
                category.id,
                category.fields.map(field => field.id),
            ])
        );
        previewPaths = Object.fromEntries(
            schema.categories.map(category => [
                category.id,
                category.fields.map(field => [field.label, field.path]),
            ])
        );
    }

    let activeTab = 'basic';
    let activeInspector = 'structure';
    let activeField = null;
    let openFieldControl = null;
    let fieldOptions = [];
    const fieldOptionStore = new Map();

    function nestedValue(source, path) {
        let current = source;
        for (const key of path) {
            if (current === null || current === undefined) return '';
            current = current[key];
        }
        return Array.isArray(current) ? current.join(', ') : (current ?? '');
    }

    function getCurrentData() {
        if (typeof getFormData === 'function') return getFormData();
        return {};
    }

    function closeMobileSidebar() {
        document.getElementById('sidebar')?.classList.remove('open');
        document.getElementById('sidebarOverlay')?.classList.remove('active');
    }

    function selectTab(target) {
        const panel = document.getElementById(`tab-${target}`);
        if (!panel) return;
        activeTab = target;

        document.querySelectorAll('.tab-btn[data-tab]').forEach(button => {
            button.classList.toggle('active', button.dataset.tab === target);
        });
        document.querySelectorAll('.tab-panel').forEach(item => {
            item.classList.toggle('active', item === panel);
        });

        const title = panel.dataset.title || categoryLabels[target] || '结构化提示词';
        const description = panel.dataset.description || '';
        const categoryIndex = categoryOrder.indexOf(target);
        const fieldCount = categoryFields[target]?.length || 0;
        document.getElementById('editorTitle').textContent = title;
        document.getElementById('editorDescription').textContent = description;
        document.getElementById('editorKicker').textContent = categoryIndex >= 0
            ? `第 ${categoryIndex + 1} 组 · ${fieldCount} 项约束`
            : '辅助工作区';

        updateFooter(target);
        closeMobileSidebar();
    }

    function updateFooter(target) {
        const previousButton = document.getElementById('previousCategoryBtn');
        const nextButton = document.getElementById('nextCategoryBtn');
        const index = categoryOrder.indexOf(target);
        if (index < 0) {
            previousButton.style.visibility = 'hidden';
            nextButton.style.visibility = 'hidden';
            return;
        }
        previousButton.style.visibility = index === 0 ? 'hidden' : 'visible';
        nextButton.style.visibility = 'visible';
        nextButton.textContent = index === categoryOrder.length - 1
            ? '检查完整结构'
            : `下一组：${categoryLabels[categoryOrder[index + 1]]}`;
    }

    function selectInspector(target) {
        activeInspector = target;
        const row = document.getElementById('previewAreaRow');
        row.classList.remove('view-structure', 'view-json', 'view-result', 'json-hidden');
        row.classList.add(`view-${target}`);
        if (target !== 'json') row.classList.add('json-hidden');
        document.querySelectorAll('.inspector-tab').forEach(button => {
            button.classList.toggle('active', button.dataset.inspector === target);
        });
    }

    function updateCompletion() {
        let completedTotal = 0;
        let possibleTotal = 0;
        Object.entries(categoryFields).forEach(([scope, ids]) => {
            const completed = ids.filter(id => document.getElementById(id)?.value.trim()).length;
            completedTotal += completed;
            possibleTotal += ids.length;
            document.querySelectorAll(`[data-count-scope="${scope}"]`).forEach(label => {
                label.textContent = `${completed}/${ids.length}`;
            });
        });

        document.querySelectorAll('.field-control').forEach(control => {
            const input = control.querySelector('input, textarea');
            const complete = Boolean(input?.value.trim());
            control.classList.toggle('is-complete', complete);
            const stateLabel = control.querySelector('.field-state');
            if (stateLabel) stateLabel.textContent = complete ? '已填写' : '待填写';
        });

        const percent = possibleTotal ? Math.round(completedTotal / possibleTotal * 100) : 0;
        document.getElementById('promptProgressText').textContent = `${completedTotal} / ${possibleTotal}`;
        document.getElementById('promptProgressFill').style.width = `${percent}%`;
        document.getElementById('structureReadyState').textContent = completedTotal === possibleTotal
            ? '结构完整，可以生成'
            : `还可补充 ${possibleTotal - completedTotal} 项约束`;

        const advancedCount = [
            document.getElementById('negativePromptEnabled')?.checked,
            document.getElementById('specialRequirementEnabled')?.checked,
            document.getElementById('lineArtModeEnabled')?.checked
        ].filter(Boolean).length;
        document.getElementById('advancedStatusCount').textContent = `${advancedCount} 项启用`;

        const generateButton = document.getElementById('generateImageBtn');
        if (generateButton && !state?.isGenerating) {
            generateButton.textContent = completedTotal
                ? `使用 ${completedTotal} 项约束生成`
                : '使用结构化提示词生成';
        }
    }

    function updateStructurePreview() {
        const container = document.getElementById('structurePreview');
        const data = getCurrentData();
        container.replaceChildren();

        Object.entries(previewPaths).forEach(([scope, fields]) => {
            const values = fields.map(([label, path]) => [label, nestedValue(data, path)]);
            const group = document.createElement('section');
            group.className = 'structure-group';
            group.classList.toggle('is-complete', values.every(([, value]) => String(value).trim()));

            const heading = document.createElement('div');
            heading.className = 'structure-group-title';
            heading.textContent = categoryLabels[scope];
            group.appendChild(heading);

            values.forEach(([label, value]) => {
                const row = document.createElement('div');
                row.className = 'structure-value';
                const name = document.createElement('span');
                const content = document.createElement('span');
                name.textContent = label;
                content.textContent = String(value).trim() || '待填写';
                row.append(name, content);
                group.appendChild(row);
            });
            container.appendChild(group);
        });
    }

    function refreshStructuredUi() {
        updateCompletion();
        updateStructurePreview();
        const saveState = document.getElementById('editorSaveState');
        if (saveState) {
            saveState.textContent = '草稿已保存';
            window.clearTimeout(refreshStructuredUi.saveTimer);
            refreshStructuredUi.saveTimer = window.setTimeout(() => {
                saveState.textContent = '自动保存草稿';
            }, 700);
        }
    }

    function syncPresetMirrors() {
        const source = document.getElementById('presetSelect');
        document.querySelectorAll('.preset-select-mirror').forEach(mirror => {
            mirror.innerHTML = source.innerHTML;
            mirror.value = source.value;
        });
    }

    async function loadFieldOptions(fieldName) {
        const response = await fetch(`/api/options/${encodeURIComponent(fieldName)}`);
        if (!response.ok) throw new Error('加载字段选项失败');
        const options = await response.json();
        return Array.isArray(options) ? options : [];
    }

    function closeFieldDropdown() {
        if (!openFieldControl) return;
        openFieldControl.querySelector('.field-combobox')?.classList.remove('is-open');
        openFieldControl.querySelector('.field-option-toggle')?.setAttribute('aria-expanded', 'false');
        openFieldControl = null;
    }

    function renderFieldDropdown(control, options) {
        const menu = control.querySelector('.field-option-dropdown');
        if (!menu) return;
        menu.replaceChildren();
        if (!options.length) {
            const empty = document.createElement('span');
            empty.className = 'field-option-empty';
            empty.textContent = '暂无已保存选项';
            menu.appendChild(empty);
            return;
        }
        options.forEach(option => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'field-option-choice';
            button.setAttribute('role', 'option');
            button.textContent = option;
            button.addEventListener('click', () => {
                const input = control.querySelector('input, textarea');
                input.value = option;
                input.dispatchEvent(new Event('input', { bubbles: true }));
                closeFieldDropdown();
            });
            menu.appendChild(button);
        });
    }

    function createEditableCombobox(control) {
        const row = control.querySelector('.field-input-row');
        const input = row?.querySelector('input, textarea');
        if (!row || !input || row.querySelector('.field-combobox')) return;

        const combo = document.createElement('div');
        combo.className = `field-combobox${input.tagName === 'TEXTAREA' ? ' is-multiline' : ''}`;
        row.insertBefore(combo, input);
        combo.appendChild(input);

        const toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'field-option-toggle';
        toggle.textContent = '▾';
        toggle.title = '展开已保存选项';
        toggle.setAttribute('aria-label', `展开${control.dataset.fieldName}选项`);
        toggle.setAttribute('aria-expanded', 'false');

        const menu = document.createElement('div');
        menu.className = 'field-option-dropdown';
        menu.setAttribute('role', 'listbox');
        combo.append(toggle, menu);

        const manage = row.querySelector('.field-option-manage');
        if (manage) {
            manage.title = '保存或删除字段选项';
            manage.setAttribute('aria-label', `管理${control.dataset.fieldName}选项`);
        }

        toggle.addEventListener('click', event => {
            event.stopPropagation();
            const willOpen = !combo.classList.contains('is-open');
            closeFieldDropdown();
            if (!willOpen) return;
            combo.classList.add('is-open');
            toggle.setAttribute('aria-expanded', 'true');
            openFieldControl = control;
        });
        input.addEventListener('keydown', event => {
            if (event.key === 'ArrowDown' && event.altKey) {
                event.preventDefault();
                toggle.click();
            } else if (event.key === 'Escape') {
                closeFieldDropdown();
            }
        });
    }

    function renderFieldOptionsModal() {
        const list = document.getElementById('fieldOptionsList');
        list.replaceChildren();
        if (!fieldOptions.length) {
            const empty = document.createElement('p');
            empty.className = 'muted-text';
            empty.textContent = '暂无已保存选项';
            list.appendChild(empty);
            return;
        }
        fieldOptions.forEach(option => {
            const row = document.createElement('div');
            row.className = 'field-option-row';
            const apply = document.createElement('button');
            apply.type = 'button';
            apply.className = 'field-option-apply';
            apply.textContent = option;
            apply.addEventListener('click', () => {
                activeField.input.value = option;
                activeField.input.dispatchEvent(new Event('input', { bubbles: true }));
                closeFieldOptions();
            });
            const remove = document.createElement('button');
            remove.type = 'button';
            remove.className = 'field-option-delete';
            remove.textContent = '×';
            remove.setAttribute('aria-label', `删除选项 ${option}`);
            remove.addEventListener('click', () => deleteFieldOption(option));
            row.append(apply, remove);
            list.appendChild(row);
        });
    }

    async function openFieldOptions(control) {
        const fieldName = control.dataset.fieldName;
        const input = control.querySelector('input, textarea');
        activeField = { fieldName, input, control };
        document.getElementById('fieldOptionsTitle').textContent = `管理「${fieldName}」选项`;
        document.getElementById('fieldOptionsModal').classList.add('active');
        try {
            fieldOptions = fieldOptionStore.has(fieldName)
                ? [...fieldOptionStore.get(fieldName)]
                : await loadFieldOptions(fieldName);
            fieldOptionStore.set(fieldName, [...fieldOptions]);
            renderFieldOptionsModal();
            renderFieldDropdown(control, fieldOptions);
        } catch (error) {
            if (typeof showToast === 'function') showToast(error.message, 'error');
        }
    }

    function closeFieldOptions() {
        document.getElementById('fieldOptionsModal').classList.remove('active');
    }

    async function addFieldOption(value) {
        const option = String(value || '').trim();
        if (!activeField) return;
        if (!option) {
            showToast('请先输入内容', 'error');
            return;
        }
        if (fieldOptions.includes(option)) {
            showToast('该选项已存在');
            return;
        }
        const response = await fetch(`/api/options/${encodeURIComponent(activeField.fieldName)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ value: option })
        });
        if (!response.ok) throw new Error('添加字段选项失败');
        fieldOptions.push(option);
        fieldOptionStore.set(activeField.fieldName, [...fieldOptions]);
        renderFieldOptionsModal();
        renderFieldDropdown(activeField.control, fieldOptions);
        showToast('已加入字段下拉选项');
    }

    async function deleteFieldOption(option) {
        if (!activeField) return;
        const response = await fetch(`/api/options/${encodeURIComponent(activeField.fieldName)}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ value: option })
        });
        if (!response.ok) throw new Error('删除字段选项失败');
        fieldOptions = fieldOptions.filter(item => item !== option);
        fieldOptionStore.set(activeField.fieldName, [...fieldOptions]);
        renderFieldOptionsModal();
        renderFieldDropdown(activeField.control, fieldOptions);
    }

    function initFieldOptions() {
        document.querySelectorAll('.field-control').forEach(control => {
            createEditableCombobox(control);
            control.querySelector('.field-option-manage')?.addEventListener('click', () => openFieldOptions(control));
            loadFieldOptions(control.dataset.fieldName)
                .then(options => {
                    fieldOptionStore.set(control.dataset.fieldName, [...options]);
                    renderFieldDropdown(control, options);
                })
                .catch(() => {});
        });
        document.addEventListener('click', event => {
            if (openFieldControl && !openFieldControl.contains(event.target)) closeFieldDropdown();
        });
        document.querySelector('#fieldOptionsModal .modal-close').addEventListener('click', closeFieldOptions);
        document.getElementById('fieldOptionsCloseBtn').addEventListener('click', closeFieldOptions);
        document.getElementById('fieldOptionSaveCurrentBtn').addEventListener('click', () => {
            addFieldOption(activeField?.input.value).catch(error => showToast(error.message, 'error'));
        });
    }

    function initNavigation() {
        document.querySelectorAll('.tab-btn[data-tab]').forEach(button => {
            button.addEventListener('click', event => {
                event.stopImmediatePropagation();
                selectTab(button.dataset.tab);
            }, true);
        });
        document.getElementById('previousCategoryBtn').addEventListener('click', () => {
            const index = categoryOrder.indexOf(activeTab);
            if (index > 0) selectTab(categoryOrder[index - 1]);
        });
        document.getElementById('nextCategoryBtn').addEventListener('click', () => {
            const index = categoryOrder.indexOf(activeTab);
            if (index < categoryOrder.length - 1) selectTab(categoryOrder[index + 1]);
            else selectInspector('json');
        });
    }

    function initInspector() {
        document.querySelectorAll('.inspector-tab').forEach(button => {
            button.addEventListener('click', event => {
                event.stopImmediatePropagation();
                selectInspector(button.dataset.inspector);
            }, true);
        });
        selectInspector(activeInspector);
    }

    function initPresetMirrors() {
        const source = document.getElementById('presetSelect');
        source.addEventListener('change', () => {
            window.setTimeout(() => {
                syncPresetMirrors();
                refreshStructuredUi();
            }, 0);
        });
        document.querySelectorAll('.preset-select-mirror').forEach(mirror => {
            mirror.addEventListener('change', () => {
                source.value = mirror.value;
                source.dispatchEvent(new Event('change', { bubbles: true }));
            });
        });
        document.querySelector('.preset-save-mirror').addEventListener('click', () => document.getElementById('savePresetBtn').click());
        document.querySelector('.preset-delete-mirror').addEventListener('click', () => document.getElementById('deletePresetBtn').click());

        const observer = new MutationObserver(syncPresetMirrors);
        observer.observe(source, { childList: true });
        syncPresetMirrors();
    }

    function initLiveRefresh() {
        document.querySelectorAll('.field-control input, .field-control textarea, #negativePromptInput, #specialRequirementInput, #lineArtPromptInput').forEach(input => {
            input.addEventListener('input', () => window.requestAnimationFrame(refreshStructuredUi));
        });
        ['negativePromptEnabled', 'specialRequirementEnabled', 'lineArtModeEnabled'].forEach(id => {
            document.getElementById(id)?.addEventListener('change', () => window.requestAnimationFrame(refreshStructuredUi));
        });
        document.getElementById('resetFormBtn').addEventListener('click', () => window.setTimeout(refreshStructuredUi, 0));
        document.getElementById('aiModalApplyBtn').addEventListener('click', () => window.setTimeout(refreshStructuredUi, 0));
    }

    function initResultSwitching() {
        const result = document.getElementById('resultPreview');
        let hadGeneratedContent = Boolean(result.querySelector('.generated-result-container, .generating-state'));
        const observer = new MutationObserver(() => {
            const hasGeneratedContent = Boolean(result.querySelector('.generated-result-container, .generating-state'));
            if (hasGeneratedContent && !hadGeneratedContent) selectInspector('result');
            hadGeneratedContent = hasGeneratedContent;
        });
        observer.observe(result, { childList: true, subtree: true });
    }

    function init() {
        const start = () => {
            hydrateFromSchema(window.PROMPT_SCHEMA);
            if (typeof window.setFormData === 'function') {
                const applyFormData = window.setFormData;
                window.setFormData = data => {
                    applyFormData(data);
                    window.requestAnimationFrame(refreshStructuredUi);
                };
            }
            initNavigation();
            initInspector();
            initFieldOptions();
            initPresetMirrors();
            initLiveRefresh();
            initResultSwitching();
            selectTab('basic');
            if (typeof updateJsonPreview === 'function') updateJsonPreview();
            window.setTimeout(refreshStructuredUi, 0);
        };
        const ready = window.promptSchemaPromise || Promise.resolve();
        ready.then(start).catch(error => console.error(error));
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
