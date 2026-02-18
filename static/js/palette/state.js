export function createPaletteState() {
    return {
        currentImageFile: null,
        currentColors: [],
        paletteControls: [],
        markerPositions: [],
        markerElements: [],
        activeMarkerIndex: -1,
        draggingMarkerIndex: -1,
        draggingPointerId: null,
    };
}
