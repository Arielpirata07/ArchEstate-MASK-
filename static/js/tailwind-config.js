/**
 * CONFIGURACIÓN DE TAILWIND CSS
 * Define los colores y tipografías personalizados de ArchEstate
 */
if (typeof tailwind !== 'undefined' && tailwind.config) {
    tailwind.config = {
        darkMode: 'class',
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
                    serif: ['Newsreader', 'Iowan Old Style', 'Palatino Linotype', 'Palatino', 'Georgia', 'Times New Roman', 'serif'],
                    sans: ['Manrope', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Helvetica Neue', 'Arial', 'sans-serif'],
                }
            }
        }
    }
}
