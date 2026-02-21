import { dataURLToBlob, showToast } from './utils.js';
import { withCsrfHeaders } from '../security/csrf.js';

const t = window.t || ((key, fallback) => fallback || key);
const currentLang = window.currentLang || 'en';

export function bindPaletteActions({ elements, state, paletteView, markerController }) {
    elements.imagePreview.addEventListener('load', () => {
        markerController.rebuildSampleCanvas();
        markerController.resetMarkersForPalette(true);
    });

    window.addEventListener('resize', () => {
        markerController.updateActiveLoupe();
    });

    elements.reanalyzeBtn.addEventListener('click', async (event) => {
        event.stopPropagation();

        const savedImageDataURL = localStorage.getItem('lastImageDataURL');
        if (!state.currentImageFile && !savedImageDataURL) {
            showToast(t('upload_image_first', 'Сначала загрузите изображение!'), 'error');
            return;
        }

        paletteView.showLoading(true);

        try {
            const formData = new FormData();
            formData.append('color_count', elements.colorCountSelect.value);

            if (state.currentImageFile) {
                formData.append('image', state.currentImageFile);
            } else if (savedImageDataURL) {
                const blob = dataURLToBlob(savedImageDataURL);
                formData.append('image', blob, 'image.png');
            }

            const response = await fetch('/api/upload', {
                method: 'POST',
                headers: withCsrfHeaders(),
                body: formData,
            });

            const data = await response.json();

            if (data.success) {
                state.currentColors = data.palette;
                paletteView.displayPalette(state.currentColors);
                localStorage.setItem('lastPalette', JSON.stringify(state.currentColors));
                showToast(t('palette_recalculated', 'Палитра пересчитана!'));
            } else {
                showToast(data.error || t('palette_recalculate_error', 'Ошибка при пересчете палитры'), 'error');
            }
        } catch (error) {
            console.error('Palette recalculation error:', error);
            showToast(t('palette_recalculate_fail', 'Произошла ошибка при пересчете'), 'error');
        } finally {
            paletteView.showLoading(false);
        }
    });

    if (elements.newImageBtn) {
        elements.newImageBtn.addEventListener('click', () => {
            paletteView.resetForNewUpload();
        });
    }

    if (elements.savePaletteBtn) {
        elements.savePaletteBtn.addEventListener('click', (event) => {
            event.stopPropagation();

            if (state.currentColors.length === 0) {
                showToast(t('create_palette_first', 'Сначала создайте палитру!'), 'error');
                return;
            }

            const modalPalette = document.getElementById('modalPalette');
            if (modalPalette) {
                modalPalette.innerHTML = '';

                state.currentColors.forEach(color => {
                    const colorDiv = document.createElement('div');
                    colorDiv.className = 'color-swatch-small';
                    colorDiv.style.backgroundColor = color;
                    colorDiv.style.width = '30px';
                    colorDiv.style.height = '30px';
                    colorDiv.style.borderRadius = '5px';
                    modalPalette.appendChild(colorDiv);
                });

                const paletteNameInput = document.getElementById('paletteName');
                if (paletteNameInput) {
                    paletteNameInput.value = '';
                }
            }
        });
    }

    if (elements.confirmSaveBtn) {
        elements.confirmSaveBtn.addEventListener('click', async () => {
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
                        colors: state.currentColors,
                    }),
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
                    } catch (_error) {
                        // Ignore JSON parse errors.
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
                console.error('Palette save error:', error);
                showToast(t('save_palette_error', 'Ошибка при сохранении палитры'), 'error');
            }
        });
    }

    elements.exportOptions.forEach(option => {
        option.addEventListener('click', async (event) => {
            event.preventDefault();
            event.stopPropagation();

            if (state.currentColors.length === 0) {
                showToast(t('create_palette_first', 'Сначала создайте палитру!'), 'error');
                return;
            }

            const format = event.target.dataset.format;

            try {
                const response = await fetch(`/api/export?format=${format}`, {
                    method: 'POST',
                    headers: withCsrfHeaders({
                        'Content-Type': 'application/json',
                    }),
                    body: JSON.stringify({ colors: state.currentColors }),
                });

                if (!response.ok) {
                    let errorMessage = t('export_error', 'Ошибка при экспорте');
                    try {
                        const errorData = await response.json();
                        errorMessage = errorData.error || errorMessage;
                    } catch (_error) {
                        // Ignore JSON parse errors.
                    }
                    showToast(errorMessage, 'error');
                    return;
                }

                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = `palette.${format}`;
                document.body.appendChild(link);
                link.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(link);
            } catch (error) {
                console.error('Palette export error:', error);
                showToast(t('export_error', 'Ошибка при экспорте'), 'error');
            }
        });
    });
}
