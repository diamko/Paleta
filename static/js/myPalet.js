import { initMyPaletPage } from './myPalet/index.js';

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMyPaletPage, { once: true });
} else {
    initMyPaletPage();
}
