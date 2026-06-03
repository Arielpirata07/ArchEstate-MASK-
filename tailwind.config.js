/**
 * Tailwind config para ArchEstate.
 *
 * REFLEJA static/js/tailwind-config.js — si actualizás uno, actualizá el otro.
 * El CLI no puede leer el .js que se carga en runtime, por eso este duplicado.
 *
 * Uso:
 *   scripts/tailwindcss -c tailwind.config.js \
 *       -i static/css/tailwind.src.css -o static/css/tailwind.css --minify
 */
module.exports = {
    darkMode: 'class',
    content: [
        './templates/**/*.html',
        './static/js/**/*.js',
    ],
    theme: {
        extend: {
            colors: {
                midnight: '#000410',
                'midnight-light': '#101E33',
                gold: '#735A3A',
                'gold-light': '#A68A64',
                paper: '#FAF9F7',
                'paper-dark': '#F4F3F1',
            },
            fontFamily: {
                serif: ['Newsreader', 'serif'],
                sans: ['Manrope', 'sans-serif'],
            }
        }
    },
    plugins: [],
}
