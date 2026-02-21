const t = window.t || ((key, fallback) => fallback || key);
const currentLang = window.currentLang || 'en';

document.addEventListener('DOMContentLoaded', function() {
    const generateBtn = document.getElementById('generateBtn');
    const colorPalette = document.getElementById('colorPalette');
    const colorCountSelect = document.getElementById('colorCount');
    const savePaletteBtn = document.getElementById('savePaletteBtn');
    const confirmSaveBtn = document.getElementById('confirmSaveBtn');
    const exportOptions = document.querySelectorAll('.export-option');

    let currentColors = [];

    function getCsrfToken() {
        const tokenElement = document.querySelector('meta[name="csrf-token"]');
        return tokenElement ? tokenElement.getAttribute('content') || '' : '';
    }

    function withCsrfHeaders(headers = {}) {
        const csrfToken = getCsrfToken();
        if (!csrfToken) return { ...headers };
        return {
            ...headers,
            'X-CSRF-Token': csrfToken,
        };
    }

    generateBtn.addEventListener('click', () => {
        const count = parseInt(colorCountSelect.value, 10);
        currentColors = generateRandomColors(count);
        displayPalette(currentColors);
    });

    function generateRandomColors(count) {
        const colors = [];
        for (let i = 0; i < count; i++) {
            const color = `#${Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0').toUpperCase()}`;
            colors.push(color);
        }
        return colors;
    }

    function normalizeHexColor(value) {
        if (typeof value !== 'string') return null;
        const sanitized = value.trim().toUpperCase();

        if (/^#[0-9A-F]{6}$/.test(sanitized)) return sanitized;
        if (/^[0-9A-F]{6}$/.test(sanitized)) return `#${sanitized}`;

        if (/^#[0-9A-F]{3}$/.test(sanitized)) {
            return `#${sanitized[1]}${sanitized[1]}${sanitized[2]}${sanitized[2]}${sanitized[3]}${sanitized[3]}`;
        }
        if (/^[0-9A-F]{3}$/.test(sanitized)) {
            return `#${sanitized[0]}${sanitized[0]}${sanitized[1]}${sanitized[1]}${sanitized[2]}${sanitized[2]}`;
        }

        return null;
    }

    function showToast(message, type = 'success') {
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
            return;
        }

        const toast = document.createElement('div');
        toast.className = `position-fixed bottom-0 end-0 m-3 p-3 ${type === 'error' ? 'bg-danger' : 'bg-success'} text-white rounded shadow`;
        toast.style.zIndex = '1060';
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 2000);
    }

    function displayPalette(colors) {
        colorPalette.innerHTML = '';

        if (!Array.isArray(colors) || colors.length === 0) {
            currentColors = [];
            return;
        }

        currentColors = colors.map(color => normalizeHexColor(color) || '#000000');

        currentColors.forEach((color, index) => {
            const item = document.createElement('div');
            item.className = 'palette-edit-item';
            item.innerHTML = `
                <button type="button" class="palette-edit-preview" title="${t('copy_hex_title', 'Скопировать HEX')}"></button>
                <div class="palette-edit-controls">
                    <input type="color" class="palette-edit-picker" value="${color.toLowerCase()}" aria-label="${t('color_picker_label', 'Выбор цвета {index}', { index: index + 1 })}">
                    <input type="text" class="palette-edit-hex" value="${color}" maxlength="7" spellcheck="false" aria-label="${t('color_hex_label', 'HEX цвета {index}', { index: index + 1 })}">
                </div>
            `;

            const preview = item.querySelector('.palette-edit-preview');
            const picker = item.querySelector('.palette-edit-picker');
            const hexInput = item.querySelector('.palette-edit-hex');

            preview.style.backgroundColor = color;

            const applyColor = (rawValue, showError = false) => {
                const normalized = normalizeHexColor(rawValue);
                if (!normalized) {
                    if (showError) {
                        hexInput.value = currentColors[index];
                        showToast(t('hex_validation_error', 'Введите корректный HEX-код, например #A1B2C3'), 'error');
                    }
                    return false;
                }

                currentColors[index] = normalized;
                preview.style.backgroundColor = normalized;
                picker.value = normalized.toLowerCase();
                hexInput.value = normalized;
                return true;
            };

            preview.addEventListener('click', () => copyToClipboard(currentColors[index]));

            picker.addEventListener('input', () => {
                applyColor(picker.value);
            });

            hexInput.addEventListener('input', () => {
                hexInput.value = hexInput.value.toUpperCase();
                const normalized = normalizeHexColor(hexInput.value);
                if (normalized) {
                    applyColor(normalized);
                }
            });

            hexInput.addEventListener('keydown', (event) => {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    hexInput.blur();
                }
            });

            hexInput.addEventListener('blur', () => {
                applyColor(hexInput.value, true);
            });

            colorPalette.appendChild(item);
        });

        const actionsSection = document.getElementById('actionsSection');
        if (actionsSection) {
            actionsSection.classList.remove('d-none');
        }
    }

    async function copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            showToast(t('hex_copied', 'HEX код скопирован!'));
        } catch (err) {
            console.error(t('copy_error', 'Ошибка копирования:'), err);
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            showToast(t('hex_copied', 'HEX код скопирован!'));
        }
    }

    if (savePaletteBtn) {
        savePaletteBtn.addEventListener('click', () => {
            if (currentColors.length === 0) {
                showToast(t('generate_palette_first', 'Сначала сгенерируйте палитру!'), 'error');
                return;
            }

            const modalPalette = document.getElementById('modalPalette');
            if (modalPalette) {
                modalPalette.innerHTML = '';

                currentColors.forEach(color => {
                    const colorDiv = document.createElement('div');
                    colorDiv.className = 'color-swatch-small';
                    colorDiv.style.backgroundColor = color;
                    colorDiv.style.width = '30px';
                    colorDiv.style.height = '30px';
                    colorDiv.style.borderRadius = '5px';
                    modalPalette.appendChild(colorDiv);
                });
            }

            const paletteNameInput = document.getElementById('paletteName');
            if (paletteNameInput) {
                paletteNameInput.value = '';
            }
        });
    }

    if (confirmSaveBtn) {
        confirmSaveBtn.addEventListener('click', async () => {
            const paletteNameInput = document.getElementById('paletteName');
            const originalValue = paletteNameInput?.value || '';
            const paletteName = originalValue.trim();

            if (originalValue && !paletteName) {
                showToast(t('palette_name_spaces', 'Название палитры не может состоять только из пробелов'), 'error');
                return;
            }

            const finalName = paletteName || t('default_palette_name', 'Моя палитра');

            const saveModal = bootstrap.Modal.getInstance(document.getElementById('saveModal'));

            try {
                const response = await fetch('/api/palettes/save', {
                    method: 'POST',
                    headers: withCsrfHeaders({
                        'Content-Type': 'application/json',
                    }),
                    body: JSON.stringify({
                        name: finalName,
                        colors: currentColors
                    })
                });

                if (!response.ok) {
                    if (response.status === 401) {
                        showToast(t('session_expired_login', 'Сессия истекла. Пожалуйста, войдите снова.'), 'error');
                        window.location.href = `/${currentLang}/login`;
                        return;
                    }
                    let errorMessage = t('save_error', 'Ошибка при сохранении');
                    try {
                        const errorData = await response.json();
                        errorMessage = errorData.error || errorMessage;
                    } catch (_e) {
                        // Ignore parse errors.
                    }
                    showToast(errorMessage, 'error');
                    return;
                }

                const data = await response.json();

                if (data.success) {
                    showToast(t('palette_saved', 'Палитра сохранена!'));
                    if (saveModal) saveModal.hide();
                } else {
                    showToast(data.error || t('save_error', 'Ошибка при сохранении'), 'error');
                }
            } catch (error) {
                console.error('Random palette save error:', error);
                showToast(t('save_palette_error', 'Ошибка при сохранении палитры'), 'error');
            }
        });
    }

    exportOptions.forEach(option => {
        option.addEventListener('click', async (e) => {
            e.preventDefault();

            if (currentColors.length === 0) {
                showToast(t('generate_palette_first', 'Сначала сгенерируйте палитру!'), 'error');
                return;
            }

            const format = e.target.dataset.format;

            try {
                const response = await fetch(`/api/export?format=${format}`, {
                    method: 'POST',
                    headers: withCsrfHeaders({
                        'Content-Type': 'application/json',
                    }),
                    body: JSON.stringify({ colors: currentColors })
                });

                if (!response.ok) {
                    let errorMessage = t('export_error', 'Ошибка при экспорте');
                    try {
                        const errorData = await response.json();
                        errorMessage = errorData.error || errorMessage;
                    } catch (_error) {
                        // Ignore parse errors.
                    }
                    showToast(errorMessage, 'error');
                    return;
                }

                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `palette.${format}`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } catch (error) {
                console.error('Random palette export error:', error);
                showToast(t('export_error', 'Ошибка при экспорте'), 'error');
            }
        });
    });
});
