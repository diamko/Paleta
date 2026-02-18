import { bindPaletteActions } from './actions.js';
import { collectPaletteElements, hasPalettePageElements } from './dom.js';
import { createMarkerController } from './markers.js';
import { createPaletteState } from './state.js';
import { createUploadController } from './uploads.js';
import { createPaletteView } from './view.js';

export function initPalettePage() {
    const elements = collectPaletteElements();
    if (!hasPalettePageElements(elements)) {
        return;
    }

    const state = createPaletteState();
    const markerController = createMarkerController({ elements, state });
    const paletteView = createPaletteView({ elements, state, markerController });

    markerController.setColorSetter((index, rawValue, options = {}) =>
        paletteView.setColorAtIndex(index, rawValue, options)
    );

    const uploadController = createUploadController({
        elements,
        state,
        paletteView,
        markerController,
    });

    bindPaletteActions({
        elements,
        state,
        paletteView,
        markerController,
    });

    uploadController.restoreFromStorage();
    uploadController.bindUploadEvents();
}
