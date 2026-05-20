(function() {
    var STORAGE_KEY = 'archestate-theme';

    var html = document.documentElement;
    var toggle1 = document.getElementById('theme-toggle');
    var toggle2 = document.getElementById('theme-toggle-mobile');
    var label = document.getElementById('theme-toggle-label');
    var toggles = [];

    if (toggle1) toggles.push(toggle1);
    if (toggle2) toggles.push(toggle2);
    if (!toggles.length) return;

    function persist(theme) {
        localStorage.setItem(STORAGE_KEY, theme);
        try {
            fetch('/api/profile/settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ theme: theme })
            });
        } catch (e) {}
    }

    function applyTheme(theme) {
        var isDark = theme === 'dark';
        html.classList.toggle('dark', isDark);
        if (label) label.textContent = isDark ? 'Modo Claro' : 'Modo Oscuro';
    }

    function getSystemTheme() {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function resolveInitialTheme() {
        var saved = localStorage.getItem(STORAGE_KEY);
        if (saved) return saved;
        if (html.classList.contains('dark')) return 'dark';
        return getSystemTheme();
    }

    var mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', function(e) {
        if (!localStorage.getItem(STORAGE_KEY)) {
            applyTheme(e.matches ? 'dark' : 'light');
        }
    });

    for (var i = 0; i < toggles.length; i++) {
        (function(btn) {
            btn.addEventListener('click', function() {
                var isDark = !html.classList.contains('dark');
                applyTheme(isDark ? 'dark' : 'light');
                persist(isDark ? 'dark' : 'light');
            });
        })(toggles[i]);
    }

    applyTheme(resolveInitialTheme());
})();
