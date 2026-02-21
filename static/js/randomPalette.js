// Генерация случайной палитры и взаимодействие с пользователем
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

    // Генерация палитры при клике на кнопку
    generateBtn.addEventListener('click', () => {
        const count = parseInt(colorCountSelect.value);
        currentColors = generateRandomColors(count);
        displayPalette(currentColors);
    });

    // Функция генерации случайных цветов
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

    // Функция отображения палитры
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
                <button type="button" class="palette-edit-preview" title="Скопировать HEX"></button>
                <div class="palette-edit-controls">
                    <input type="color" class="palette-edit-picker" value="${color.toLowerCase()}" aria-label="Выбор цвета ${index + 1}">
                    <input type="text" class="palette-edit-hex" value="${color}" maxlength="7" spellcheck="false" aria-label="HEX цвета ${index + 1}">
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
                        showToast('Введите корректный HEX-код, например #A1B2C3', 'error');
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

        // Показываем секцию с действиями (сохранить, экспортировать)
        const actionsSection = document.getElementById('actionsSection');
        if (actionsSection) {
            actionsSection.classList.remove('d-none');
        }
    }

    // Копирование HEX-кода в буфер обмена
    async function copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            showToast('HEX код скопирован!');
        } catch (err) {
            console.error('Ошибка копирования:', err);
            // Резервный способ для старых браузеров
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            showToast('HEX код скопирован!');
        }
    }

    // Обработчик для сохранения палитры
    if (savePaletteBtn) {
        savePaletteBtn.addEventListener('click', () => {
            if (currentColors.length === 0) {
                showToast('Сначала сгенерируйте палитру!', 'error');
                return;
            }

            // Заполняем модальное окно текущими цветами
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

            // Очищаем поле ввода названия палитры
            const paletteNameInput = document.getElementById('paletteName');
            if (paletteNameInput) {
                paletteNameInput.value = '';
            }
        });
    }

    // Обработчик для подтверждения сохранения палитры
    if (confirmSaveBtn) {
        confirmSaveBtn.addEventListener('click', async () => {
            const paletteNameInput = document.getElementById('paletteName');
            const originalValue = paletteNameInput?.value || '';
            const paletteName = originalValue.trim();

            // Если пользователь ввел только пробелы, это ошибка.
            if (originalValue && !paletteName) {
                showToast('Название палитры не может состоять только из пробелов', 'error');
                return;
            }

            // Если название пустое (пользователь ничего не ввел), используем значение по умолчанию.
            const finalName = paletteName || 'Моя палитра';

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
                        showToast('Сессия истекла. Пожалуйста, войдите снова.', 'error');
                        window.location.href = '/login';
                        return;
                    }
                    // Для других ошибок пробуем получить сообщение из ответа.
                    let errorMessage = 'Ошибка при сохранении';
                    try {
                        const errorData = await response.json();
                        errorMessage = errorData.error || errorMessage;
                    } catch (e) {
                        // Если ответ не JSON, оставляем общее сообщение.
                    }
                    showToast(errorMessage, 'error');
                    return;
                }

                const data = await response.json();

                if (data.success) {
                    showToast('Палитра сохранена!');
                    if (saveModal) saveModal.hide();
                } else {
                    showToast(data.error || 'Ошибка при сохранении', 'error');
                }
            } catch (error) {
                console.error('Ошибка сохранения:', error);
                showToast('Ошибка при сохранении палитры', 'error');
            }
        });
    }

    // Обработчики для экспорта палитры
    exportOptions.forEach(option => {
        option.addEventListener('click', async (e) => {
            e.preventDefault();

            if (currentColors.length === 0) {
                showToast('Сначала сгенерируйте палитру!', 'error');
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
                    let errorMessage = 'Ошибка при экспорте';
                    try {
                        const errorData = await response.json();
                        errorMessage = errorData.error || errorMessage;
                    } catch (_error) {
                        // Игнорируем ошибки разбора.
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
                console.error('Ошибка экспорта:', error);
                showToast('Ошибка при экспорте', 'error');
            }
        });
    });
});
