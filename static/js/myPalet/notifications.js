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
