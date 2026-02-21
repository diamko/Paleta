const t = window.t || ((key, fallback) => fallback || key);

window.addEventListener('scroll', function () {
    const header = document.querySelector('header');
    if (window.scrollY > 50) {
        header.classList.add('scrolled');
    } else {
        header.classList.remove('scrolled');
    }
});

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const targetId = this.getAttribute('href');
        if (targetId === '#') return;

        const targetElement = document.querySelector(targetId);
        if (targetElement) {
            window.scrollTo({
                top: targetElement.offsetTop - 80,
                behavior: 'smooth'
            });
        }
    });
});

document.querySelectorAll('.btn-primary:not(#reanalyzeBtn), .btn-outline-primary:not(#reanalyzeBtn), .btn-secondary:not(#reanalyzeBtn)').forEach(button => {
    button.addEventListener('mouseenter', function () {
        if (!this.id.includes('reanalyze')) {
            this.style.transform = 'translateY(-3px)';
        }
    });

    button.addEventListener('mouseleave', function () {
        if (!this.id.includes('reanalyze')) {
            this.style.transform = 'translateY(0)';
        }
    });
});

document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', function () {
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        this.classList.add('active');
    });
});

const logo = document.querySelector('.header__logo');
if (logo) {
    logo.addEventListener('mouseenter', () => {
        const logoImg = logo.querySelector('.header_img');
        if (logoImg) {
            logoImg.style.transform = 'rotate(-5deg) scale(1.05)';
        }
    });

    logo.addEventListener('mouseleave', () => {
        const logoImg = logo.querySelector('.header_img');
        if (logoImg) {
            logoImg.style.transform = 'rotate(0) scale(1)';
        }
    });
}

window.addEventListener('load', function () {
    document.body.style.opacity = '0';
    document.body.style.transition = 'opacity 0.5s';

    setTimeout(() => {
        document.body.style.opacity = '1';
    }, 100);
});

document.addEventListener('DOMContentLoaded', function () {
    if (typeof bootstrap === 'undefined') {
        console.error(t('bootstrap_missing', 'Bootstrap не загружен!'));
    } else {
        console.log(t('bootstrap_loaded', 'Bootstrap загружен успешно'));
    }

    const saveModalElement = document.getElementById('saveModal');
    if (saveModalElement) {
        saveModalElement.addEventListener('hidden.bs.modal', function () {
            const paletteNameInput = document.getElementById('paletteName');
            if (paletteNameInput) paletteNameInput.value = '';
        });
    }

    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    const logoutForm = document.getElementById('logoutForm');
    if (logoutForm) {
        logoutForm.addEventListener('submit', () => {
            localStorage.removeItem('lastImageFilename');
            localStorage.removeItem('lastPalette');
            localStorage.removeItem('lastImageDataURL');
        });
    }
});

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `position-fixed bottom-0 end-0 m-3 p-3 ${type === 'error' ? 'bg-danger' : 'bg-success'} text-white rounded shadow`;
    toast.style.zIndex = '1060';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 2000);
}
