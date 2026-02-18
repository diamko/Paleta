export function dataURLToBlob(dataURL) {
    const parts = dataURL.split(';base64,');
    const contentType = parts[0].split(':')[1];
    const raw = window.atob(parts[1]);
    const rawLength = raw.length;
    const uInt8Array = new Uint8Array(rawLength);

    for (let i = 0; i < rawLength; ++i) {
        uInt8Array[i] = raw.charCodeAt(i);
    }

    return new Blob([uInt8Array], { type: contentType });
}

export function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

export function rgbToHex(r, g, b) {
    return `#${[r, g, b].map(channel => channel.toString(16).padStart(2, '0')).join('').toUpperCase()}`;
}

export function normalizeHexColor(value) {
    if (typeof value !== 'string') return null;
    const sanitized = value.trim().toUpperCase();

    if (/^#[0-9A-F]{6}$/.test(sanitized)) return sanitized;
    if (/^[0-9A-F]{6}$/.test(sanitized)) return `#${sanitized}`;

    if (/^#[0-9A-F]{3}$/.test(sanitized)) {
        return `#${sanitized[1]}${sanitized[1]}${sanitized[2]}${sanitized[2]}${sanitized[3]}${sanitized[3]}`;
    }
    if (/^[0-9A-F]{3}$/.test(sanitized)) {
        return `#${sanitized[0]}${sanitized[0]}${sanitized[1]}${sanitized[1]}${sanitized[2]}${sanitized[2]}`;
    }

    return null;
}

export function hexToRgb(hex) {
    const normalized = normalizeHexColor(hex);
    if (!normalized) return null;

    return {
        r: parseInt(normalized.slice(1, 3), 16),
        g: parseInt(normalized.slice(3, 5), 16),
        b: parseInt(normalized.slice(5, 7), 16),
    };
}

export function showToast(message, type = 'success') {
    if (typeof window.showToast === 'function') {
        window.showToast(message, type);
        return;
    }

    const toast = document.createElement('div');
    toast.className = `position-fixed bottom-0 end-0 m-3 p-3 ${type === 'error' ? 'bg-danger' : 'bg-success'} text-white rounded shadow`;
    toast.style.zIndex = '1060';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 2000);
}

export async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('HEX код скопирован!');
    } catch (error) {
        console.error('Ошибка копирования:', error);
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showToast('HEX код скопирован!');
    }
}
