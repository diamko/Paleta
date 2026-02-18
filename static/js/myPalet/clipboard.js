export function copyPalette(colors, showToast) {
    const colorArray = colors.split(' ');
    navigator.clipboard.writeText(colorArray.join('\n')).then(() => {
        showToast('Цвета скопированы в буфер обмена!');
    });
}
