import { showToast } from './utils.js';

export function createUploadController({ elements, state, paletteView, markerController }) {
    function preventDefaults(event) {
        event.preventDefault();
        event.stopPropagation();
    }

    async function handleImageFile(file) {
        if (!file.type.match('image.*')) {
            alert('Пожалуйста, выберите изображение');
            return;
        }

        if (file.size > 16 * 1024 * 1024) {
            alert('Файл слишком большой. Максимальный размер: 16MB');
            return;
        }

        state.currentImageFile = file;
        markerController.clearMarkers();
        paletteView.showLoading(true);

        try {
            const reader = new FileReader();
            reader.onload = function (event) {
                elements.imagePreview.src = event.target.result;
                elements.imagePreview.style.display = 'block';
                localStorage.setItem('lastImageDataURL', event.target.result);
            };
            reader.readAsDataURL(file);

            const formData = new FormData();
            formData.append('image', file);

            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) throw new Error('Ошибка загрузки изображения');

            const data = await response.json();

            if (data.success) {
                state.currentColors = data.palette;
                paletteView.displayPalette(state.currentColors);
                paletteView.showResults();

                localStorage.setItem('lastImageFilename', data.filename);
                localStorage.setItem('lastPalette', JSON.stringify(state.currentColors));

                addRecentUploadCard(data.filename);
            } else {
                alert(data.error || 'Ошибка при анализе изображения');
            }
        } catch (error) {
            console.error('Ошибка при загрузке изображения:', error);
            alert('Произошла ошибка при загрузке файла');
        } finally {
            paletteView.showLoading(false);
        }
    }

    async function useExistingUpload(filename) {
        if (!filename) return;

        try {
            const response = await fetch(`/static/uploads/${filename}`);
            if (!response.ok) {
                showToast('Не удалось загрузить сохранённое изображение', 'error');
                return;
            }

            const blob = await response.blob();
            const file = new File([blob], filename, { type: blob.type || 'image/png' });

            await handleImageFile(file);
        } catch (error) {
            console.error('Ошибка при использовании сохранённого изображения:', error);
            showToast('Произошла ошибка при использовании сохранённого изображения', 'error');
        }
    }

    function addRecentUploadCard(filename) {
        if (!elements.recentUploadsSection || !elements.recentUploadsRow || !filename) return;

        if (elements.recentUploadsEmpty) {
            elements.recentUploadsEmpty.classList.add('d-none');
        }
        elements.recentUploadsRow.classList.remove('d-none');

        const now = new Date();
        const formatted = now.toLocaleString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        }).replace(',', '');

        const col = document.createElement('div');
        col.className = 'col-6 col-md-4 col-lg-3';
        col.innerHTML = `
            <div class="card h-100 shadow-sm">
                <div class="ratio ratio-4x3">
                    <img src="/static/uploads/${filename}"
                         class="card-img-top object-fit-cover"
                         alt="Недавнее изображение">
                </div>
                <div class="card-body p-2">
                    <small class="text-muted d-block mb-2">
                        ${formatted}
                    </small>
                    <button type="button"
                            class="btn btn-sm btn-outline-primary w-100 btn-use-upload"
                            data-filename="${filename}">
                        Использовать
                    </button>
                </div>
            </div>
        `;

        if (elements.recentUploadsRow.firstChild) {
            elements.recentUploadsRow.insertBefore(col, elements.recentUploadsRow.firstChild);
        } else {
            elements.recentUploadsRow.appendChild(col);
        }
    }

    function restoreFromStorage() {
        const savedFilename = localStorage.getItem('lastImageFilename');
        const savedPalette = localStorage.getItem('lastPalette');
        const savedImageDataURL = localStorage.getItem('lastImageDataURL');

        if (!savedFilename || !savedPalette || !savedImageDataURL) return;

        try {
            const palette = JSON.parse(savedPalette);
            state.currentColors = palette;
            paletteView.displayPalette(palette);

            elements.imagePreview.src = savedImageDataURL;
            elements.imagePreview.style.display = 'block';
            elements.resultSection.classList.remove('d-none');
            elements.uploadZone.style.display = 'none';

            console.log('Загружены сохраненные данные из localStorage');
        } catch (error) {
            console.error('Ошибка загрузки сохраненных данных:', error);
        }
    }

    function bindUploadEvents() {
        elements.browseBtn.addEventListener('click', () => elements.imageInput.click());

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            elements.uploadZone.addEventListener(eventName, preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            elements.uploadZone.addEventListener(eventName, () => {
                elements.uploadZone.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            elements.uploadZone.addEventListener(eventName, () => {
                elements.uploadZone.classList.remove('dragover');
            }, false);
        });

        elements.uploadZone.addEventListener('drop', (event) => {
            const files = event.dataTransfer?.files;
            if (files && files.length > 0) {
                handleImageFile(files[0]);
            }
        }, false);

        elements.imageInput.addEventListener('change', (event) => {
            if (event.target.files.length > 0) {
                handleImageFile(event.target.files[0]);
            }
        });

        document.addEventListener('click', (event) => {
            const target = event.target;
            if (target.classList.contains('btn-use-upload')) {
                const filename = target.dataset.filename;
                useExistingUpload(filename);
            }
        });
    }

    return {
        bindUploadEvents,
        restoreFromStorage,
        handleImageFile,
        useExistingUpload,
    };
}
