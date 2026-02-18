export function createFiltersController(elements) {
    function updateCounts() {
        const cards = document.querySelectorAll('.palette-card');
        const total = cards.length;
        let visible = 0;

        cards.forEach(card => {
            if (!card.classList.contains('d-none')) {
                visible += 1;
            }
        });

        if (elements.visibleCountEl) {
            elements.visibleCountEl.textContent = visible.toString();
        }
        if (elements.totalCountEl) {
            elements.totalCountEl.textContent = total.toString();
        }
    }

    function applyFilters() {
        const searchValue = (elements.searchInput?.value || '').toLowerCase().trim();
        const countValue = elements.colorCountFilter?.value || '';

        const cards = document.querySelectorAll('.palette-card');
        cards.forEach(card => {
            const name = (card.dataset.name || '').toLowerCase();
            const colorCount = card.dataset.colorCount || '';

            const matchesName = !searchValue || name.includes(searchValue);
            const matchesCount = !countValue || colorCount === countValue;

            if (matchesName && matchesCount) {
                card.classList.remove('d-none');
            } else {
                card.classList.add('d-none');
            }
        });

        updateCounts();
    }

    function applySort() {
        if (!elements.palettesContainer || !elements.sortSelect) return;

        const cards = Array.from(elements.palettesContainer.querySelectorAll('.palette-card'));
        const sortValue = elements.sortSelect.value;

        const getCreatedAt = (card) => {
            const raw = card.dataset.createdAt || '0';
            const num = Number(raw);
            return Number.isNaN(num) ? 0 : num;
        };

        cards.sort((a, b) => {
            switch (sortValue) {
                case 'created_asc':
                    return getCreatedAt(a) - getCreatedAt(b);
                case 'created_desc':
                    return getCreatedAt(b) - getCreatedAt(a);
                case 'name_asc':
                    return (a.dataset.name || '').localeCompare(b.dataset.name || '', 'ru');
                case 'name_desc':
                    return (b.dataset.name || '').localeCompare(a.dataset.name || '', 'ru');
                case 'colors_asc':
                    return Number(a.dataset.colorCount || '0') - Number(b.dataset.colorCount || '0');
                case 'colors_desc':
                    return Number(b.dataset.colorCount || '0') - Number(a.dataset.colorCount || '0');
                default:
                    return getCreatedAt(b) - getCreatedAt(a);
            }
        });

        cards.forEach(card => elements.palettesContainer.appendChild(card));
    }

    function bind() {
        if (elements.searchInput) {
            elements.searchInput.addEventListener('input', applyFilters);
        }

        if (elements.colorCountFilter) {
            elements.colorCountFilter.addEventListener('change', applyFilters);
        }

        if (elements.sortSelect) {
            elements.sortSelect.addEventListener('change', () => {
                applySort();
                applyFilters();
            });
        }

        if (elements.palettesContainer) {
            applySort();
        }
        applyFilters();
    }

    return {
        bind,
        applyFilters,
    };
}
