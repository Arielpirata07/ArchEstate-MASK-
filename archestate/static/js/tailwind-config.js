/**
 * CONFIGURACIÓN DE TAILWIND CSS
 * Define los colores y tipografías personalizados de ArchEstate
 */
tailwind.config = {
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
    }
}
