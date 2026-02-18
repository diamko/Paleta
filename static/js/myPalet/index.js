import { copyPalette } from './clipboard.js';
import { createFiltersController } from './filters.js';
import { showToast } from './notifications.js';
import { createPaletteActions } from './palette-actions.js';
import { createMyPaletState } from './state.js';

function collectMyPaletElements(root = document) {
    return {
        deleteModalElement: root.getElementById('deleteModal'),
        renameModalElement: root.getElementById('renameModal'),
        confirmDeleteBtn: root.getElementById('confirmDeleteBtn'),
        confirmRenameBtn: root.getElementById('confirmRenameBtn'),
        searchInput: root.getElementById('paletteSearch'),
        colorCountFilter: root.getElementById('colorCountFilter'),
        sortSelect: root.getElementById('paletteSort'),
        palettesContainer: root.getElementById('palettesContainer'),
        visibleCountEl: root.getElementById('paletteCountVisible'),
        totalCountEl: root.getElementById('paletteCountTotal'),
    };
}

export function initMyPaletPage() {
    const elements = collectMyPaletElements();

    if (!elements.palettesContainer && !elements.deleteModalElement && !elements.renameModalElement) {
        return;
    }

    const state = createMyPaletState();
    const filtersController = createFiltersController(elements);
    const actions = createPaletteActions({ state, showToast });

    if (elements.deleteModalElement) {
        elements.deleteModalElement.addEventListener('hidden.bs.modal', () => {
            state.currentDeleteId = null;
            state.currentDeleteName = null;
        });
    }

    if (elements.renameModalElement) {
        elements.renameModalElement.addEventListener('hidden.bs.modal', () => {
            state.currentRenameId = null;
        });
    }

    if (elements.confirmDeleteBtn) {
        elements.confirmDeleteBtn.addEventListener('click', () => {
            actions.confirmDelete();
        });
    }

    if (elements.confirmRenameBtn) {
        elements.confirmRenameBtn.addEventListener('click', () => {
            actions.confirmRename();
        });
    }

    filtersController.bind();

    document.addEventListener('click', async (event) => {
        const target = event.target;

        if (target.classList.contains('export-option')) {
            event.preventDefault();
            const format = target.dataset.format;
            const colors = JSON.parse(target.dataset.colors);
            const name = target.dataset.name;

            try {
                console.log(`Экспорт ${name} в формате ${format}`, colors);
                await actions.exportPalette(format, colors, name);
            } catch (error) {
                console.error('Ошибка при экспорте палитры:', error);
                showToast('Ошибка при экспорте', 'error');
            }
            return;
        }

        if (target.classList.contains('btn-delete-palette')) {
            actions.deletePalette(target.dataset.paletteId, target.dataset.paletteName);
            return;
        }

        if (target.classList.contains('btn-rename-palette')) {
            actions.renamePalette(target.dataset.paletteId, target.dataset.paletteName);
        }
    });

    window.copyPalette = (colors) => copyPalette(colors, showToast);
}
