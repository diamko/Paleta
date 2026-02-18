export function collectPaletteElements(root = document) {
    return {
        uploadZone: root.getElementById('uploadZone'),
        imageInput: root.getElementById('imageInput'),
        browseBtn: root.getElementById('browseBtn'),
        uploadForm: root.getElementById('uploadForm'),
        resultSection: root.getElementById('resultSection'),
        imagePreview: root.getElementById('imagePreview'),
        imageStage: root.getElementById('imageStage'),
        markerLayer: root.getElementById('markerLayer'),
        activeLoupe: root.getElementById('activeLoupe'),
        activeLoupeCanvas: root.getElementById('activeLoupeCanvas'),
        activeLoupeHex: root.getElementById('activeLoupeHex'),
        colorPalette: root.getElementById('colorPalette'),
        loadingIndicator: root.getElementById('loadingIndicator'),
        reanalyzeBtn: root.getElementById('reanalyzeBtn'),
        newImageBtn: root.getElementById('newImageBtn'),
        colorCountSelect: root.getElementById('colorCountSelect'),
        recentUploadsSection: root.getElementById('recentUploadsSection'),
        recentUploadsRow: root.getElementById('recentUploadsRow'),
        recentUploadsEmpty: root.getElementById('recentUploadsEmpty'),
        savePaletteBtn: root.getElementById('savePaletteBtn'),
        confirmSaveBtn: root.getElementById('confirmSaveBtn'),
        exportOptions: root.querySelectorAll('.export-option'),
    };
}

export function hasPalettePageElements(elements) {
    return Boolean(
        elements.uploadZone &&
        elements.imageInput &&
        elements.browseBtn &&
        elements.resultSection &&
        elements.imagePreview &&
        elements.colorPalette
    );
}
