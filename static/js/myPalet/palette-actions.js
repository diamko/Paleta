import { withCsrfHeaders } from '../security/csrf.js';

const t = window.t || ((key, fallback) => fallback || key);
const currentLang = window.currentLang || 'en';

export function createPaletteActions({ state, showToast }) {
    function buildDownloadFilename(name, format) {
        const safeName = (name || '')
            .trim()
            .replace(/[\\/:*?"<>|]/g, '_')
            .replace(/^\.+|\.+$/g, '');

        return `${safeName || 'palette'}.${format}`;
    }

    function exportPalette(format, colors, name) {
        return fetch(`/api/export?format=${format}`, {
            method: 'POST',
            headers: withCsrfHeaders({
                'Content-Type': 'application/json',
            }),
            body: JSON.stringify({ colors }),
        }).then(async response => {
            if (!response.ok) {
                showToast(t('export_error', 'Ошибка при экспорте'), 'error');
                return;
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = buildDownloadFilename(name, format);
            document.body.appendChild(link);
            link.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(link);
        });
    }

    function deletePalette(id, name) {
        state.currentDeleteId = id;
        state.currentDeleteName = name;

        const deleteModalText = document.getElementById('deleteModalText');
        if (deleteModalText) {
            deleteModalText.textContent = `${t('delete_modal_prompt', 'Вы уверены, что хотите удалить палитру')} "${name}"?`;
        }

        const deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
        deleteModal.show();
    }

    function confirmDelete() {
        if (!state.currentDeleteId) {
            return;
        }

        const idToDelete = state.currentDeleteId;

        const deleteModalElement = document.getElementById('deleteModal');
        const deleteModal = bootstrap.Modal.getInstance(deleteModalElement);
        if (deleteModal) {
            deleteModal.hide();
        }

        fetch(`/api/palettes/delete/${idToDelete}`, {
            method: 'DELETE',
            headers: withCsrfHeaders({
                'Content-Type': 'application/json',
            }),
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast(t('palette_deleted', 'Палитра удалена!'));
                    setTimeout(() => {
                        location.reload();
                    }, 500);
                } else {
                    showToast(`${t('delete_error_prefix', 'Ошибка при удалении:')} ${data.error}`, 'error');
                }
            })
            .catch(error => {
                console.error('Delete palette error:', error);
                showToast(t('delete_error', 'Произошла ошибка при удалении'), 'error');
            });
    }

    function renamePalette(id, name) {
        state.currentRenameId = id;

        const input = document.getElementById('newPaletteName');
        if (input) {
            input.value = name;
            input.focus();
        }

        const renameModal = new bootstrap.Modal(document.getElementById('renameModal'));
        renameModal.show();
    }

    function confirmRename() {
        if (!state.currentRenameId) {
            return;
        }

        const input = document.getElementById('newPaletteName');
        const newName = (input?.value || '').trim();

        if (!newName) {
            showToast(t('rename_empty', 'Название палитры не может быть пустым.'), 'error');
            return;
        }

        const idToRename = state.currentRenameId;

        const renameModalElement = document.getElementById('renameModal');
        const renameModal = bootstrap.Modal.getInstance(renameModalElement);
        if (renameModal) {
            renameModal.hide();
        }

        fetch(`/api/palettes/rename/${idToRename}`, {
            method: 'POST',
            headers: withCsrfHeaders({
                'Content-Type': 'application/json',
            }),
            body: JSON.stringify({ name: newName }),
        })
            .then(response => {
                if (!response.ok) {
                    if (response.status === 401) {
                        showToast(t('session_expired_login', 'Сессия истекла. Пожалуйста, войдите снова.'), 'error');
                        window.location.href = `/${currentLang}/login`;
                        return null;
                    }
                    return response.json().then(data => {
                        throw new Error(data.error || t('rename_error', 'Ошибка при переименовании палитры'));
                    }).catch(() => {
                        throw new Error(t('rename_error', 'Ошибка при переименовании палитры'));
                    });
                }
                return response.json();
            })
            .then(data => {
                if (!data) return;

                if (data.success) {
                    showToast(t('rename_success', 'Название палитры обновлено!'));
                    const card = document.querySelector(`.palette-card[data-palette-id="${idToRename}"]`);
                    if (card) {
                        const titleEl = card.querySelector('.card-title');
                        if (titleEl) titleEl.textContent = newName;
                        card.dataset.name = newName.toLowerCase();
                        card.dataset.paletteName = newName;

                        const renameBtn = card.querySelector(`button.btn-rename-palette[data-palette-id="${idToRename}"]`);
                        if (renameBtn) {
                            renameBtn.dataset.paletteName = newName;
                        }

                        const deleteBtn = card.querySelector(`button.btn-delete-palette[data-palette-id="${idToRename}"]`);
                        if (deleteBtn) {
                            deleteBtn.dataset.paletteName = newName;
                        }
                    }
                } else {
                    showToast(data.error || t('rename_error', 'Ошибка при переименовании палитры'), 'error');
                }
            })
            .catch(error => {
                console.error('Rename palette error:', error);
                showToast(error.message || t('rename_unknown_error', 'Произошла ошибка при переименовании палитры'), 'error');
            });
    }

    return {
        exportPalette,
        deletePalette,
        confirmDelete,
        renamePalette,
        confirmRename,
    };
}
