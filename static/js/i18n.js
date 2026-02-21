(function initI18n(global) {
    const dictionary = global.__I18N__ || {};
    const fallbackLang = (global.__LANG__ || 'en').toLowerCase();

    function template(text, params = {}) {
        return String(text).replace(/\{(\w+)\}/g, (_, key) => (
            Object.prototype.hasOwnProperty.call(params, key) ? String(params[key]) : `{${key}}`
        ));
    }

    global.currentLang = fallbackLang;
    global.t = function translate(key, fallback, params = {}) {
        const source = Object.prototype.hasOwnProperty.call(dictionary, key)
            ? dictionary[key]
            : (fallback || key);
        return template(source, params);
    };
})(window);
