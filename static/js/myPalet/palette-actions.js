export function createPaletteActions({ state, showToast }) {
    function exportPalette(format, colors, name) {
        return fetch(`/api/export?format=${format}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ colors }),
        }).then(async response => {
            if (!response.ok) {
                console.error('Не удалось экспортировать палитру, статус:', response.status);
                showToast('Ошибка при экспорте', 'error');
                return;
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `${name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.${format}`;
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
            deleteModalText.textContent = `Вы уверены, что хотите удалить палитру "${name}"?`;
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
            headers: {
                'Content-Type': 'application/json',
            },
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('Палитра удалена!');
                    setTimeout(() => {
                        location.reload();
                    }, 500);
                } else {
                    showToast('Ошибка при удалении: ' + data.error, 'error');
                }
            })
            .catch(error => {
                console.error('Ошибка при удалении палитры:', error);
                showToast('Произошла ошибка при удалении', 'error');
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
            showToast('Название палитры не может быть пустым.', 'error');
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
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name: newName }),
        })
            .then(response => {
                if (!response.ok) {
                    if (response.status === 401) {
                        showToast('Сессия истекла. Пожалуйста, войдите снова.', 'error');
                        window.location.href = '/login';
                        return null;
                    }
                    return response.json().then(data => {
                        throw new Error(data.error || 'Ошибка при переименовании палитры');
                    }).catch(() => {
                        throw new Error('Ошибка при переименовании палитры');
                    });
                }
                return response.json();
            })
            .then(data => {
                if (!data) return;

                if (data.success) {
                    showToast('Название палитры обновлено!');
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
                    showToast(data.error || 'Ошибка при переименовании палитры', 'error');
                }
            })
            .catch(error => {
                console.error('Ошибка при переименовании палитры:', error);
                showToast(error.message || 'Произошла ошибка при переименовании палитры', 'error');
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
