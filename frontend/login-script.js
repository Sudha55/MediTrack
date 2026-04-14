const API_BASE = '/api';

document.addEventListener('DOMContentLoaded', function() {
    checkIfLoggedIn();
    
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    document.getElementById('registerForm').addEventListener('submit', handleRegister);
});

function checkIfLoggedIn() {
    const token = localStorage.getItem('authToken');
    if (token) {
        window.location.href = 'index.html';
    }
}

function showLoginForm() {
    document.getElementById('login-form-container').style.display = 'block';
    document.getElementById('register-form-container').style.display = 'none';
    document.getElementById('error-message').classList.remove('show');
}

function showRegisterForm() {
    document.getElementById('login-form-container').style.display = 'none';
    document.getElementById('register-form-container').style.display = 'block';
    document.getElementById('error-message-reg').classList.remove('show');
}

async function handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('error-message');
    
    console.log('Attempting login...');
    
    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        console.log('Response status:', response.status);
        const data = await response.json();
        console.log('Response data:', data);
        
        if (response.ok && data.token) {
            console.log('Login successful, saving token');
            localStorage.setItem('authToken', data.token);
            console.log('Token saved, redirecting...');
            window.location.href = 'index.html';
        } else {
            errorDiv.textContent = data.error || 'Login failed';
            errorDiv.classList.add('show');
        }
    } catch (error) {
        console.error('Login error:', error);
        errorDiv.textContent = 'Connection error: ' + error.message;
        errorDiv.classList.add('show');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    
    const firstName = document.getElementById('reg-first-name').value;
    const lastName = document.getElementById('reg-last-name').value;
    const username = document.getElementById('reg-username').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const errorDiv = document.getElementById('error-message-reg');
    
    try {
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ first_name: firstName, last_name: lastName, username, email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            errorDiv.classList.remove('show');
            alert('Account created successfully! Please login.');
            showLoginForm();
            document.getElementById('loginForm').reset();
            document.getElementById('username').value = username;
        } else {
            errorDiv.textContent = data.error || 'Registration failed';
            errorDiv.classList.add('show');
        }
    } catch (error) {
        errorDiv.textContent = 'Connection error. Please try again.';
        errorDiv.classList.add('show');
    }
}

function showError(elementId, message) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = message;
        el.classList.add('show');
    }
}
