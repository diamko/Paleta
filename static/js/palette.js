import { initPalettePage } from './palette/index.js';

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPalettePage, { once: true });
} else {
    initPalettePage();
}
