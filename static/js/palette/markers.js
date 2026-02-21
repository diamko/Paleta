import { clamp, hexToRgb, rgbToHex } from './utils.js';

const t = window.t || ((key, fallback, params = {}) => {
    let text = fallback || key;
    Object.keys(params).forEach((paramKey) => {
        text = text.replace(`{${paramKey}}`, String(params[paramKey]));
    });
    return text;
});

export function createMarkerController({ elements, state }) {
    const sampleCanvas = document.createElement('canvas');
    const sampleCtx = sampleCanvas.getContext('2d', { willReadFrequently: true });
    const loupeCtx = elements.activeLoupeCanvas ? elements.activeLoupeCanvas.getContext('2d') : null;

    if (loupeCtx) {
        loupeCtx.imageSmoothingEnabled = false;
    }

    let setColorAtIndex = null;

    function setColorSetter(setter) {
        setColorAtIndex = setter;
    }

    function buildDefaultMarkerPositions(count) {
        if (count <= 0) return [];

        if (count === 1) {
            return [{ x: 0.5, y: 0.5 }];
        }

        const cols = Math.ceil(Math.sqrt(count));
        const rows = Math.ceil(count / cols);
        const points = [];

        for (let i = 0; i < count; i++) {
            const col = i % cols;
            const row = Math.floor(i / cols);
            points.push({
                x: (col + 0.5) / cols,
                y: (row + 0.5) / rows,
            });
        }

        return points;
    }

    function rebuildSampleCanvas() {
        if (!elements.imagePreview || !sampleCtx || !elements.imagePreview.naturalWidth || !elements.imagePreview.naturalHeight) {
            return false;
        }

        sampleCanvas.width = elements.imagePreview.naturalWidth;
        sampleCanvas.height = elements.imagePreview.naturalHeight;
        sampleCtx.clearRect(0, 0, sampleCanvas.width, sampleCanvas.height);
        sampleCtx.drawImage(elements.imagePreview, 0, 0, sampleCanvas.width, sampleCanvas.height);
        return true;
    }

    function buildMarkerPositionsFromPaletteColors(colors) {
        if (!Array.isArray(colors) || colors.length === 0) return null;

        if (!sampleCanvas.width || !sampleCanvas.height) {
            if (!rebuildSampleCanvas()) return null;
        }

        const maxSide = 240;
        const scale = Math.min(1, maxSide / Math.max(sampleCanvas.width, sampleCanvas.height));
        const searchWidth = Math.max(1, Math.round(sampleCanvas.width * scale));
        const searchHeight = Math.max(1, Math.round(sampleCanvas.height * scale));

        const searchCanvas = document.createElement('canvas');
        searchCanvas.width = searchWidth;
        searchCanvas.height = searchHeight;
        const searchCtx = searchCanvas.getContext('2d', { willReadFrequently: true });

        if (!searchCtx) return null;

        searchCtx.drawImage(sampleCanvas, 0, 0, searchWidth, searchHeight);
        const data = searchCtx.getImageData(0, 0, searchWidth, searchHeight).data;
        const pixelCount = searchWidth * searchHeight;
        const usedMask = new Uint8Array(pixelCount);
        const usedRadius = 3;

        const markUsedNeighborhood = (index) => {
            const centerX = index % searchWidth;
            const centerY = Math.floor(index / searchWidth);

            for (let y = centerY - usedRadius; y <= centerY + usedRadius; y++) {
                if (y < 0 || y >= searchHeight) continue;
                for (let x = centerX - usedRadius; x <= centerX + usedRadius; x++) {
                    if (x < 0 || x >= searchWidth) continue;
                    const dx = x - centerX;
                    const dy = y - centerY;
                    if (dx * dx + dy * dy <= usedRadius * usedRadius) {
                        usedMask[y * searchWidth + x] = 1;
                    }
                }
            }
        };

        const positions = [];

        colors.forEach((hexColor) => {
            const target = hexToRgb(hexColor);
            if (!target) {
                positions.push(null);
                return;
            }

            let bestIndex = -1;
            let bestDistance = Number.POSITIVE_INFINITY;

            for (let i = 0; i < pixelCount; i++) {
                if (usedMask[i]) continue;

                const offset = i * 4;
                const dr = target.r - data[offset];
                const dg = target.g - data[offset + 1];
                const db = target.b - data[offset + 2];
                const distance = dr * dr + dg * dg + db * db;

                if (distance < bestDistance) {
                    bestDistance = distance;
                    bestIndex = i;
                    if (distance === 0) break;
                }
            }

            if (bestIndex < 0) {
                for (let i = 0; i < pixelCount; i++) {
                    const offset = i * 4;
                    const dr = target.r - data[offset];
                    const dg = target.g - data[offset + 1];
                    const db = target.b - data[offset + 2];
                    const distance = dr * dr + dg * dg + db * db;

                    if (distance < bestDistance) {
                        bestDistance = distance;
                        bestIndex = i;
                    }
                }
            }

            if (bestIndex < 0) {
                positions.push(null);
                return;
            }

            markUsedNeighborhood(bestIndex);

            const x = bestIndex % searchWidth;
            const y = Math.floor(bestIndex / searchWidth);
            positions.push({
                x: searchWidth > 1 ? x / (searchWidth - 1) : 0.5,
                y: searchHeight > 1 ? y / (searchHeight - 1) : 0.5,
            });
        });

        if (positions.some(position => !position)) return null;

        return positions;
    }

    function sampleHexAtNormalized(normX, normY) {
        if (!sampleCanvas.width || !sampleCanvas.height) {
            if (!rebuildSampleCanvas()) return null;
        }

        const x = Math.round(clamp(normX, 0, 1) * (sampleCanvas.width - 1));
        const y = Math.round(clamp(normY, 0, 1) * (sampleCanvas.height - 1));
        const pixel = sampleCtx.getImageData(x, y, 1, 1).data;

        return rgbToHex(pixel[0], pixel[1], pixel[2]);
    }

    function hideActiveLoupe() {
        if (elements.activeLoupe) {
            elements.activeLoupe.classList.add('d-none');
        }
    }

    function drawLoupe(normX, normY) {
        if (!loupeCtx || !elements.activeLoupeCanvas) return;

        if (!sampleCanvas.width || !sampleCanvas.height) {
            if (!rebuildSampleCanvas()) return;
        }

        const sourceRadius = 6;
        const centerX = Math.round(clamp(normX, 0, 1) * (sampleCanvas.width - 1));
        const centerY = Math.round(clamp(normY, 0, 1) * (sampleCanvas.height - 1));
        const srcX = clamp(centerX - sourceRadius, 0, sampleCanvas.width - 1);
        const srcY = clamp(centerY - sourceRadius, 0, sampleCanvas.height - 1);
        const srcWidth = Math.min(sourceRadius * 2 + 1, sampleCanvas.width - srcX);
        const srcHeight = Math.min(sourceRadius * 2 + 1, sampleCanvas.height - srcY);

        loupeCtx.clearRect(0, 0, elements.activeLoupeCanvas.width, elements.activeLoupeCanvas.height);
        loupeCtx.imageSmoothingEnabled = false;
        loupeCtx.drawImage(
            sampleCanvas,
            srcX, srcY, srcWidth, srcHeight,
            0, 0, elements.activeLoupeCanvas.width, elements.activeLoupeCanvas.height
        );

        const center = elements.activeLoupeCanvas.width / 2;
        loupeCtx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
        loupeCtx.lineWidth = 1.5;
        loupeCtx.beginPath();
        loupeCtx.moveTo(center - 10, center);
        loupeCtx.lineTo(center + 10, center);
        loupeCtx.moveTo(center, center - 10);
        loupeCtx.lineTo(center, center + 10);
        loupeCtx.stroke();
    }

    function updateActiveLoupe() {
        if (
            !elements.activeLoupe ||
            !elements.imageStage ||
            state.activeMarkerIndex < 0 ||
            !state.markerPositions[state.activeMarkerIndex] ||
            elements.imagePreview.style.display === 'none'
        ) {
            hideActiveLoupe();
            return;
        }

        const markerPosition = state.markerPositions[state.activeMarkerIndex];
        const stageRect = elements.imageStage.getBoundingClientRect();
        const imageRect = elements.imagePreview.getBoundingClientRect();

        if (!stageRect.width || !imageRect.width || !imageRect.height) {
            hideActiveLoupe();
            return;
        }

        drawLoupe(markerPosition.x, markerPosition.y);

        const markerX = (imageRect.left - stageRect.left) + markerPosition.x * imageRect.width;
        const markerY = (imageRect.top - stageRect.top) + markerPosition.y * imageRect.height;

        const loupeWidth = elements.activeLoupe.offsetWidth || 116;
        const loupeHeight = elements.activeLoupe.offsetHeight || 132;
        let loupeLeft = markerX + 18;
        let loupeTop = markerY - loupeHeight - 12;

        if (loupeLeft + loupeWidth > stageRect.width) {
            loupeLeft = stageRect.width - loupeWidth - 6;
        }
        if (loupeLeft < 6) {
            loupeLeft = 6;
        }
        if (loupeTop < 6) {
            loupeTop = markerY + 18;
        }
        if (loupeTop + loupeHeight > stageRect.height - 4) {
            loupeTop = stageRect.height - loupeHeight - 4;
        }

        elements.activeLoupe.style.left = `${loupeLeft}px`;
        elements.activeLoupe.style.top = `${loupeTop}px`;
        elements.activeLoupe.classList.remove('d-none');

        if (elements.activeLoupeHex) {
            elements.activeLoupeHex.textContent = state.currentColors[state.activeMarkerIndex] || '#000000';
        }
    }

    function setActiveMarker(index) {
        if (!Array.isArray(state.markerElements) || state.markerElements.length === 0) return;

        state.activeMarkerIndex = index;
        state.markerElements.forEach((markerElement, markerIndex) => {
            markerElement.classList.toggle('active', markerIndex === state.activeMarkerIndex);
        });
        updateActiveLoupe();
    }

    function clearMarkers() {
        window.removeEventListener('pointermove', handleMarkerPointerMove);
        window.removeEventListener('pointerup', handleMarkerPointerUp);
        window.removeEventListener('pointercancel', handleMarkerPointerUp);

        state.markerPositions = [];
        state.markerElements = [];
        state.activeMarkerIndex = -1;
        state.draggingMarkerIndex = -1;
        state.draggingPointerId = null;

        if (elements.markerLayer) {
            elements.markerLayer.innerHTML = '';
        }

        hideActiveLoupe();
    }

    function moveMarkerFromClient(index, clientX, clientY, sampleColor = true) {
        if (!elements.imagePreview || !state.markerPositions[index]) return;

        const imageRect = elements.imagePreview.getBoundingClientRect();
        if (!imageRect.width || !imageRect.height) return;

        const normX = clamp((clientX - imageRect.left) / imageRect.width, 0, 1);
        const normY = clamp((clientY - imageRect.top) / imageRect.height, 0, 1);
        state.markerPositions[index] = { x: normX, y: normY };

        const markerElement = state.markerElements[index];
        if (markerElement) {
            markerElement.style.left = `${normX * 100}%`;
            markerElement.style.top = `${normY * 100}%`;
        }

        if (sampleColor && typeof setColorAtIndex === 'function') {
            const sampledHex = sampleHexAtNormalized(normX, normY);
            if (sampledHex) {
                setColorAtIndex(index, sampledHex);
            }
        }

        setActiveMarker(index);
    }

    function handleMarkerPointerMove(event) {
        if (event.pointerId !== state.draggingPointerId || state.draggingMarkerIndex < 0) return;
        moveMarkerFromClient(state.draggingMarkerIndex, event.clientX, event.clientY, true);
    }

    function handleMarkerPointerUp(event) {
        if (event.pointerId !== state.draggingPointerId) return;

        if (state.draggingMarkerIndex >= 0 && state.markerElements[state.draggingMarkerIndex]) {
            state.markerElements[state.draggingMarkerIndex].classList.remove('dragging');
        }

        state.draggingMarkerIndex = -1;
        state.draggingPointerId = null;

        window.removeEventListener('pointermove', handleMarkerPointerMove);
        window.removeEventListener('pointerup', handleMarkerPointerUp);
        window.removeEventListener('pointercancel', handleMarkerPointerUp);
    }

    function renderMarkers() {
        if (!elements.markerLayer) return;

        elements.markerLayer.innerHTML = '';
        state.markerElements = [];

        state.markerPositions.forEach((position, index) => {
            const markerButton = document.createElement('button');
            markerButton.type = 'button';
            markerButton.className = 'palette-marker';
            markerButton.style.left = `${position.x * 100}%`;
            markerButton.style.top = `${position.y * 100}%`;
            markerButton.style.backgroundColor = state.currentColors[index] || '#000000';
            markerButton.setAttribute(
                'aria-label',
                t('color_marker_label', 'Маркер цвета {index}', { index: index + 1 })
            );

            markerButton.addEventListener('pointerdown', (event) => {
                if (event.button !== 0) return;

                event.preventDefault();
                state.draggingMarkerIndex = index;
                state.draggingPointerId = event.pointerId;
                markerButton.classList.add('dragging');

                rebuildSampleCanvas();
                moveMarkerFromClient(index, event.clientX, event.clientY, true);

                window.addEventListener('pointermove', handleMarkerPointerMove);
                window.addEventListener('pointerup', handleMarkerPointerUp);
                window.addEventListener('pointercancel', handleMarkerPointerUp);
            });

            markerButton.addEventListener('click', (event) => {
                event.preventDefault();
                setActiveMarker(index);
            });

            elements.markerLayer.appendChild(markerButton);
            state.markerElements.push(markerButton);
        });

        if (state.markerElements.length > 0) {
            setActiveMarker(state.activeMarkerIndex >= 0 ? state.activeMarkerIndex : 0);
        } else {
            hideActiveLoupe();
        }
    }

    function resetMarkersForPalette(forceReset = false) {
        if (!Array.isArray(state.currentColors) || state.currentColors.length === 0) {
            clearMarkers();
            return;
        }

        if (forceReset || state.markerPositions.length !== state.currentColors.length) {
            state.markerPositions =
                buildMarkerPositionsFromPaletteColors(state.currentColors) ||
                buildDefaultMarkerPositions(state.currentColors.length);
            state.activeMarkerIndex = state.markerPositions.length ? 0 : -1;
        }

        renderMarkers();
        updateActiveLoupe();
    }

    function setMarkerColor(index, color) {
        const markerElement = state.markerElements[index];
        if (markerElement) {
            markerElement.style.backgroundColor = color;
        }

        if (state.activeMarkerIndex === index) {
            updateActiveLoupe();
        }
    }

    return {
        setColorSetter,
        rebuildSampleCanvas,
        hideActiveLoupe,
        updateActiveLoupe,
        setActiveMarker,
        clearMarkers,
        resetMarkersForPalette,
        setMarkerColor,
    };
}
