document.addEventListener('DOMContentLoaded', function() {
    initScrollAnimations();
    initParallax();
    initTypingEffect();
    fetchAndAnimateCounters();
    initMagneticHover();
    initHeroReveal();
    initTitleReveal();
    initSubtitleReveal();
    initStepConnectorDraw();
    initNavbarShrink();

    // FAQ: make keyboard accessible and add ARIA attributes
    document.querySelectorAll('.faq-question').forEach((q, i) => {
        const answer = q.nextElementSibling;
        if (!answer) return;
        const answerId = answer.id || `faq-answer-${i+1}`;
        answer.id = answerId;
        q.setAttribute('tabindex', '0');
        q.setAttribute('role', 'button');
        q.setAttribute('aria-controls', answerId);
        q.setAttribute('aria-expanded', 'false');
        q.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggleFaq(q);
            }
        });
    });

    // Ensure counters have ARIA and respect reduced motion
    document.querySelectorAll('.counter').forEach(c => {
        if (!c.getAttribute('role')) c.setAttribute('role', 'status');
        if (!c.getAttribute('aria-live')) c.setAttribute('aria-live', 'polite');
    });
});

// --- Scroll Animations ---
function initScrollAnimations() {
    if (!('IntersectionObserver' in window)) {
        document.querySelectorAll('[data-scroll]').forEach(el => el.classList.add('animate'));
        return;
    }

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    document.querySelectorAll('[data-scroll]').forEach(el => observer.observe(el));
}

// --- Title Reveal Animation ---
function initTitleReveal() {
    const titleEl = document.querySelector('h1.title-reveal');
    if (!titleEl) return;

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.2 });

    observer.observe(titleEl);
}

// --- Subtitle Reveal Animation ---
function initSubtitleReveal() {
    const subtitleEl = document.querySelector('.subtitle-reveal');
    if (!subtitleEl) return;

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.2 });

    observer.observe(subtitleEl);
}

// --- Parallax ---
function initParallax() {
    const parallaxEl = document.querySelector('.parallax');
    if (!parallaxEl) return;

    let ticking = false;
    window.addEventListener('scroll', () => {
        if (!ticking) {
            window.requestAnimationFrame(() => {
                const scrolled = window.pageYOffset;
                const rate = scrolled * -0.3;
                parallaxEl.style.transform = `translateY(${rate}px) scale(${1 + scrolled * 0.0002})`;
                ticking = false;
            });
            ticking = true;
        }
    });
}

// --- Typing Effect ---
function initTypingEffect() {
    const typingElement = document.querySelector('.typing-effect');
    if (!typingElement) return;

    const text = typingElement.textContent;
    typingElement.textContent = '';
    typingElement.style.borderRight = '2px solid var(--accent)';
    let i = 0;
    const typeWriter = () => {
        if (i < text.length) {
            typingElement.textContent += text.charAt(i);
            i++;
            setTimeout(typeWriter, 80 + Math.random() * 60);
        } else {
            setTimeout(() => { typingElement.style.borderRight = 'none'; }, 500);
        }
    };
    setTimeout(typeWriter, 800);
}

// --- Contadores Dinamicos con API ---
async function fetchAndAnimateCounters() {
    const counters = document.querySelectorAll('.counter');
    if (!counters.length) return;

    // Mostrar loading state
    counters.forEach(c => { c.textContent = '...'; });

    let data = null;
    try {
        const response = await fetch('/api/landing/stats');
        if (response.ok) data = await response.json();
    } catch (e) {
        console.error('Error fetching landing stats:', e);
    }

    if (!data) {
        // Fallback si la API falla
        data = { total_leads: 0, total_professionals: 0, total_zones: 0, leads_this_month: 0 };
    }

    const targets = [
        data.total_leads,
        data.total_professionals,
        data.total_zones,
        data.leads_this_month
    ];

    // Animar cada contador con stagger
    counters.forEach((counter, index) => {
        const target = targets[index] || 0;
        counter.setAttribute('data-target', target);

        // Stagger: cada contador inicia 200ms despues del anterior
        setTimeout(() => {
            animateLandingCounter(counter, target, 2000);
        }, 300 + (index * 200));
    });
}

function animateLandingCounter(element, target, duration) {
    const start = 0;
    const startTime = performance.now();

    const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);

    const update = (currentTime) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easedProgress = easeOutCubic(progress);
        const currentValue = Math.round(start + (target - start) * easedProgress);

        element.textContent = currentValue.toLocaleString('es-AR');

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            element.classList.add('counter-glow-flash');
        }
    };

    requestAnimationFrame(update);
}

// --- Magnetic Hover Effect ---
function initMagneticHover() {
    if (window.matchMedia('(hover: none)').matches) return;

    document.querySelectorAll('.magnetic-hover').forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;
            card.style.transform = `translate(${x * 0.06}px, ${y * 0.06}px)`;
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translate(0, 0)';
        });
    });
}

// --- Hero Image Grayscale Reveal ---
function initHeroReveal() {
    const heroImg = document.querySelector('.hero-img');
    if (!heroImg) return;

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        heroImg.classList.add('revealed');
                    });
                });
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    observer.observe(heroImg);
}

// --- FAQ Toggle ---
function toggleFaq(questionEl) {
    const faqItem = questionEl.closest('.faq-item');
    const answer = faqItem.querySelector('.faq-answer');
    const isOpen = faqItem.classList.contains('open');

    // Cerrar todos los demas
    document.querySelectorAll('.faq-item.open').forEach(item => {
        if (item !== faqItem) {
            item.classList.remove('open');
            const otherAnswer = item.querySelector('.faq-answer');
            const otherQuestion = item.querySelector('.faq-question');
            if (otherAnswer) {
                otherAnswer.classList.remove('open');
                otherAnswer.setAttribute('aria-hidden', 'true');
            }
            if (otherQuestion) {
                otherQuestion.setAttribute('aria-expanded', 'false');
            }
        }
    });

    // Toggle el actual
    faqItem.classList.toggle('open');
    answer.classList.toggle('open');
    answer.setAttribute('aria-hidden', (!isOpen).toString());
    // Update aria-expanded on the control
    try {
        questionEl.setAttribute('aria-expanded', (!isOpen).toString());
    } catch (e) {}

    // Re-init lucide icons
    if (window.lucide) lucide.createIcons();
}

// --- Alerta de solicitud enviada (30 segundos) ---
(function() {
    var alertEl = document.getElementById('submit-alert');
    if (alertEl && sessionStorage.getItem('submit_success') === 'true') {
        sessionStorage.removeItem('submit_success');
        alertEl.classList.remove('hidden');
        if (window.lucide) lucide.createIcons();
        setTimeout(function() {
            alertEl.classList.add('opacity-0', '-translate-y-4');
            setTimeout(function() {
                alertEl.classList.add('hidden');
                alertEl.classList.remove('opacity-0', '-translate-y-4');
            }, 500);
        }, 30000);
    }
})();

function dismissAlert() {
    var alertEl = document.getElementById('submit-alert');
    if (alertEl) {
        alertEl.classList.add('opacity-0', '-translate-y-4');
        setTimeout(function() {
            alertEl.classList.add('hidden');
            alertEl.classList.remove('opacity-0', '-translate-y-4');
        }, 500);
    }
}

// --- Step Connector Draw on Scroll ---
function initStepConnectorDraw() {
    if (!('IntersectionObserver' in window)) return;

    var connectors = document.querySelectorAll('.step-connector');
    if (!connectors.length) return;

    var observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                var delay = Array.from(connectors).indexOf(entry.target) * 200;
                setTimeout(function() {
                    entry.target.classList.add('drawn');
                }, delay);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    connectors.forEach(function(el) {
        observer.observe(el);
    });
}

// --- Navbar Shrink on Scroll ---
function initNavbarShrink() {
    var navbar = document.getElementById('main-navbar');
    if (!navbar) return;

    var ticking = false;
    window.addEventListener('scroll', function() {
        if (!ticking) {
            window.requestAnimationFrame(function() {
                if (window.pageYOffset > 80) {
                    navbar.classList.add('navbar-shrunk');
                } else {
                    navbar.classList.remove('navbar-shrunk');
                }
                ticking = false;
            });
            ticking = true;
        }
    });
}
