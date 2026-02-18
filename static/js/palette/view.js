import { copyToClipboard, normalizeHexColor, showToast } from './utils.js';

export function createPaletteView({ elements, state, markerController }) {
    function setColorAtIndex(index, rawValue, options = {}) {
        const normalized = normalizeHexColor(rawValue);
        const showError = !!options.showError;

        if (!normalized || index < 0 || index >= state.currentColors.length) {
            if (showError && state.paletteControls[index]?.hexInput) {
                state.paletteControls[index].hexInput.value = state.currentColors[index] || '#000000';
                showToast('Введите корректный HEX-код, например #A1B2C3', 'error');
            }
            return false;
        }

        state.currentColors[index] = normalized;

        const controls = state.paletteControls[index];
        if (controls) {
            controls.preview.style.backgroundColor = normalized;
            controls.picker.value = normalized.toLowerCase();
            controls.hexInput.value = normalized;
        }

        markerController.setMarkerColor(index, normalized);
        localStorage.setItem('lastPalette', JSON.stringify(state.currentColors));

        if (state.activeMarkerIndex === index) {
            markerController.updateActiveLoupe();
        }

        return true;
    }

    function displayPalette(colors) {
        elements.colorPalette.innerHTML = '';
        state.paletteControls = [];

        if (!Array.isArray(colors) || colors.length === 0) {
            state.currentColors = [];
            localStorage.removeItem('lastPalette');
            markerController.clearMarkers();
            return;
        }

        state.currentColors = colors.map(color => normalizeHexColor(color) || '#000000');
        markerController.resetMarkersForPalette(true);

        state.currentColors.forEach((color, index) => {
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
            state.paletteControls[index] = { preview, picker, hexInput };
            setColorAtIndex(index, color);

            preview.addEventListener('click', () => copyToClipboard(state.currentColors[index]));

            picker.addEventListener('input', () => {
                setColorAtIndex(index, picker.value);
            });

            hexInput.addEventListener('input', () => {
                hexInput.value = hexInput.value.toUpperCase();
                const normalized = normalizeHexColor(hexInput.value);
                if (normalized) {
                    setColorAtIndex(index, normalized);
                }
            });

            hexInput.addEventListener('keydown', (event) => {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    hexInput.blur();
                }
            });

            hexInput.addEventListener('blur', () => {
                setColorAtIndex(index, hexInput.value, { showError: true });
            });

            elements.colorPalette.appendChild(item);
        });

        localStorage.setItem('lastPalette', JSON.stringify(state.currentColors));
        markerController.updateActiveLoupe();
    }

    function showLoading(show) {
        if (show) {
            elements.loadingIndicator.classList.remove('d-none');
            elements.uploadZone.style.opacity = '0.5';
        } else {
            elements.loadingIndicator.classList.add('d-none');
            elements.uploadZone.style.opacity = '1';
        }
    }

    function showResults() {
        elements.resultSection.classList.remove('d-none');
        elements.resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function resetForNewUpload() {
        state.currentImageFile = null;
        state.currentColors = [];
        state.paletteControls = [];
        markerController.clearMarkers();

        elements.uploadZone.style.display = 'block';
        elements.resultSection.classList.add('d-none');
        elements.imagePreview.src = '';
        elements.imagePreview.style.display = 'none';
        elements.colorPalette.innerHTML = '';

        localStorage.removeItem('lastImageFilename');
        localStorage.removeItem('lastPalette');
        localStorage.removeItem('lastImageDataURL');

        elements.uploadZone.scrollIntoView({ behavior: 'smooth' });
        showToast('Готово для новой загрузки!');
    }

    return {
        setColorAtIndex,
        displayPalette,
        showLoading,
        showResults,
        resetForNewUpload,
    };
}
