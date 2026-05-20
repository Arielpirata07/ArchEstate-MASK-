/**
 * Dark Mode Toggle — ArchEstate
 * Persiste en backend via /api/profile/settings
 */

document.addEventListener('DOMContentLoaded', function() {
    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;

    const html = document.documentElement;
    const sunIcon = toggle.querySelector('.theme-sun');
    const moonIcon = toggle.querySelector('.theme-moon');

    toggle.addEventListener('click', async function() {
        const isDark = html.classList.toggle('dark-mode');
        updateIcons(isDark);

        try {
            await fetch('/api/profile/settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ theme: isDark ? 'dark' : 'light' })
            });
        } catch (e) {
            // fallback silencioso
        }
    });

    function updateIcons(isDark) {
        if (sunIcon) sunIcon.style.display = isDark ? 'none' : 'block';
        if (moonIcon) moonIcon.style.display = isDark ? 'block' : 'none';
        if (window.lucide) lucide.createIcons();
    }

    // Estado inicial
    updateIcons(html.classList.contains('dark-mode'));
});
