const SAFE_PATHS = ['/', '/index.html', '/auth'];

async function loadUserProfile() {
    const email = localStorage.getItem('userEmail');
    const currentPath = window.location.pathname;

    // 1. Check Auth (skip for login pages)
    if (!email) {
        if (!SAFE_PATHS.includes(currentPath)) {
            console.warn("No user email found, redirecting to login.");
            window.location.href = '/';
        }
        return;
    }

    // 2. Fetch Profile
    try {
        const response = await fetch(`/api/user/profile?email=${encodeURIComponent(email)}`);

        if (!response.ok) {
            console.error(`API Error: ${response.status} ${response.statusText}`);
            // DO NOT REDIRECT ON API ERROR to prevent loops. Just log.
            return;
        }

        const data = await response.json();

        // 3. Update Sidebar (if elements exist)
        const nameEl = document.getElementById('sidebar-user-name');
        const roleEl = document.getElementById('sidebar-user-role');
        const initialEl = document.getElementById('sidebar-user-initial');
        const avatarEl = document.getElementById('sidebar-user-avatar'); // Handle image if it exists

        if (nameEl) nameEl.textContent = data.nome;
        if (roleEl) roleEl.textContent = data.role;

        // Handle Initials Code
        if (initialEl) {
            const initials = data.nome.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
            initialEl.textContent = initials;
        }

        // Handle Avatar Image (if user adds one later or if ID matches img)
        if (avatarEl && avatarEl.tagName === 'IMG') {
            // Placeholder for avatar logic if backend supported it
        }

        // 4. Update Settings Page (if on definicoes.html)
        if (currentPath.includes('definicoes')) {
            populateSettingsForm(data);
        }

    } catch (e) {
        console.error("Network/Script Error:", e);
    }
}

function populateSettingsForm(data) {
    const nameInput = document.getElementById('name');
    const emailInput = document.getElementById('email');
    const aiModeSelect = document.getElementById('ai-mode');
    const toggleAlerts = document.getElementById('toggle1'); // Correct ID from HTML
    const toggleReports = document.getElementById('toggle2');

    if (nameInput) nameInput.value = data.nome;
    if (emailInput) {
        emailInput.value = data.email;
        emailInput.disabled = true;
    }
    if (aiModeSelect) {
        aiModeSelect.value = data.preferencia_ia;
        localStorage.setItem('aiMode', data.preferencia_ia);
    }
    if (toggleAlerts) toggleAlerts.checked = data.notificacoes.alertas;
    if (toggleReports) toggleReports.checked = data.notificacoes.relatorios;
}

// 5. Expose Global Functions for Buttons (Settings Page)
window.updateProfile = async function () {
    const email = localStorage.getItem('userEmail');
    const newName = document.getElementById('name').value;
    const newAiMode = document.getElementById('ai-mode').value;
    const alertNotif = document.getElementById('toggle1').checked;
    const reportNotif = document.getElementById('toggle2').checked;

    const payload = {
        email_atual: email,
        novo_nome: newName,
        novas_preferencias: newAiMode,
        novas_notificacoes: {
            alertas: alertNotif,
            relatorios: reportNotif
        }
    };

    try {
        const res = await fetch('/api/user/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
            alert('Perfil atualizado com sucesso!');
            localStorage.setItem('aiMode', newAiMode);
            location.reload();
        } else {
            alert('Erro ao atualizar: ' + data.detail);
        }
    } catch (e) { console.error(e); alert('Erro de conexão'); }
};

window.changePassword = async function () {
    const newPw = prompt("Insira a nova password:");
    if (!newPw) return;

    const email = localStorage.getItem('userEmail');
    try {
        const res = await fetch('/api/user/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email, nova_password: newPw })
        });
        if (res.ok) {
            alert('Password alterada com sucesso! Por favor, faça login novamente.');
            localStorage.removeItem('userEmail');
            window.location.href = '/';
        } else {
            const data = await res.json();
            alert('Erro ao alterar password: ' + (data.detail || "Erro desconhecido"));
        }
    } catch (e) { console.error(e); alert('Erro de conexão'); }
};

window.deleteAccount = async function () {
    if (!confirm("Tem a certeza absoluta? Esta ação é irreversível.")) return;

    const email = localStorage.getItem('userEmail');
    try {
        const res = await fetch('/api/user/delete', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email })
        });
        if (res.ok) {
            alert('Conta eliminada.');
            localStorage.removeItem('userEmail');
            window.location.href = '/';
        } else {
            alert('Erro ao eliminar conta.');
        }
    } catch (e) { console.error(e); }
};

// Run on Load
document.addEventListener('DOMContentLoaded', loadUserProfile);
