function getNextPath() {
    const params = new URLSearchParams(window.location.search);
    const rawNext = params.get('next') || '/';
    if (!rawNext.startsWith('/') || rawNext.startsWith('//')) {
        return '/';
    }
    if (rawNext === '/auth' || rawNext.startsWith('/auth?')) {
        return '/';
    }
    return rawNext;
}

const nextPath = getNextPath();

const authStatus = document.getElementById('authStatus');
const loginTab = document.getElementById('loginTab');
const registerTab = document.getElementById('registerTab');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');

function setStatus(message, isSuccess = false) {
    authStatus.textContent = message || '';
    authStatus.classList.toggle('success', isSuccess);
}

function switchTo(mode) {
    const loginActive = mode === 'login';
    loginTab.classList.toggle('active', loginActive);
    registerTab.classList.toggle('active', !loginActive);
    loginTab.setAttribute('aria-selected', loginActive ? 'true' : 'false');
    registerTab.setAttribute('aria-selected', !loginActive ? 'true' : 'false');
    loginForm.classList.toggle('active', loginActive);
    registerForm.classList.toggle('active', !loginActive);
    setStatus('');
}

async function checkAlreadyAuthenticated() {
    try {
        const response = await fetch('/api/me');
        if (response.ok) {
            if (window.location.pathname === '/auth') {
                window.location.replace(nextPath);
            }
        }
    } catch (_error) {
        // Ignore bootstrap failures.
    }
}

async function submitLogin(event) {
    event.preventDefault();
    const formData = new FormData(loginForm);

    const payload = {
        username: String(formData.get('username') || ''),
        password: String(formData.get('password') || '')
    };

    setStatus('Signing in...');

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || 'Login failed.');
        }

        setStatus('Welcome back.', true);
        window.location.replace(nextPath);
    } catch (error) {
        setStatus(error.message || 'Login failed.');
    }
}

async function submitRegister(event) {
    event.preventDefault();
    const formData = new FormData(registerForm);

    const payload = {
        display_name: String(formData.get('display_name') || ''),
        username: String(formData.get('username') || ''),
        password: String(formData.get('password') || ''),
        invite_code: String(formData.get('invite_code') || '')
    };

    setStatus('Creating account...');

    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || 'Registration failed.');
        }

        setStatus('Account created. Redirecting...', true);
        window.location.replace(nextPath);
    } catch (error) {
        setStatus(error.message || 'Registration failed.');
    }
}

loginTab.addEventListener('click', () => switchTo('login'));
registerTab.addEventListener('click', () => switchTo('register'));
loginForm.addEventListener('submit', submitLogin);
registerForm.addEventListener('submit', submitRegister);

checkAlreadyAuthenticated();
