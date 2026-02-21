const t = window.t || ((key, fallback) => fallback || key);

export function copyPalette(colors, showToast) {
    const colorArray = colors.split(' ');
    navigator.clipboard.writeText(colorArray.join('\n')).then(() => {
        showToast(t('colors_copied', 'Цвета скопированы в буфер обмена!'));
    });
}
