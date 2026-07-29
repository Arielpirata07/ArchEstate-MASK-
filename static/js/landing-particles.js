(function() {
    'use strict';

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    var canvas = document.getElementById('hero-particles');
    if (!canvas) return;

    var ctx = canvas.getContext('2d');
    var particles = [];
    var mouse = { x: -9999, y: -9999 };
    var W, H;
    var animationId = null;

    var COLORS = [
        'rgba(166, 138, 100,',  // gold-light
        'rgba(115, 90, 58,',    // gold
        'rgba(255, 255, 255,',  // white
    ];

    function resize() {
        var rect = canvas.getBoundingClientRect();
        var w = Math.round(rect.width);
        var h = Math.round(rect.height);
        if (w !== canvas.width || h !== canvas.height) {
            canvas.width = w;
            canvas.height = h;
        }
        W = canvas.width;
        H = canvas.height;
    }

    function Particle() {
        this.reset();
    }

    Particle.prototype.reset = function() {
        this.x = Math.random() * W;
        this.y = Math.random() * H;
        this.baseX = this.x;
        this.baseY = this.y;
        this.size = 1.5 + Math.random() * 2.5;
        var c = COLORS[Math.floor(Math.random() * COLORS.length)];
        this.color = c + (0.02 + Math.random() * 0.06) + ')';
        this.opacity = 0.02 + Math.random() * 0.06;
        this.phaseX = Math.random() * Math.PI * 2;
        this.phaseY = Math.random() * Math.PI * 2;
        this.speedX = 0.0003 + Math.random() * 0.0004;
        this.speedY = 0.0004 + Math.random() * 0.0005;
        this.driftAmpX = 20 + Math.random() * 40;
        this.driftAmpY = 10 + Math.random() * 30;
        this.floatSpeed = 0.15 + Math.random() * 0.25;
        this.vx = 0;
        this.vy = 0;
    };

    function init() {
        resize();
        var count = Math.min(60, Math.floor(W * H / 18000));
        particles = [];
        for (var i = 0; i < count; i++) {
            particles.push(new Particle());
        }
    }

    function update(time) {
        var t = time * 0.001;
        var mouseInfluence = 150;
        var repulsionForce = 0.8;

        for (var i = 0; i < particles.length; i++) {
            var p = particles[i];

            var targetX = p.baseX + Math.sin(t * p.speedX * 10 + p.phaseX) * p.driftAmpX * 0.5
                        + Math.cos(t * p.speedY * 7 + p.phaseY) * p.driftAmpX * 0.5;
            var targetY = p.baseY + Math.sin(t * p.speedY * 8 + p.phaseY) * p.driftAmpY * 0.5
                        + Math.cos(t * p.speedX * 6 + p.phaseX) * p.driftAmpY * 0.5
                        - p.floatSpeed * 0.3;

            var dx = mouse.x - p.x;
            var dy = mouse.y - p.y;
            var dist = Math.sqrt(dx * dx + dy * dy);

            if (dist < mouseInfluence && dist > 0) {
                var force = (mouseInfluence - dist) / mouseInfluence * repulsionForce;
                var angle = Math.atan2(dy, dx);
                targetX -= Math.cos(angle) * force * 40;
                targetY -= Math.sin(angle) * force * 40;
            }

            p.vx += (targetX - p.x) * 0.02;
            p.vy += (targetY - p.y) * 0.02;
            p.vx *= 0.92;
            p.vy *= 0.92;
            p.x += p.vx;
            p.y += p.vy;

            if (p.y < -20) p.y = H + 20;
            if (p.y > H + 20) p.y = -20;
            if (p.x < -20) p.x = W + 20;
            if (p.x > W + 20) p.x = -20;
        }
    }

    function draw() {
        ctx.clearRect(0, 0, W, H);

        for (var i = 0; i < particles.length; i++) {
            var p = particles[i];
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fillStyle = p.color;
            ctx.fill();
        }
    }

    function loop(time) {
        if (W > 0 && H > 0) {
            update(time);
            draw();
        }
        animationId = requestAnimationFrame(loop);
    }

    function onMouseMove(e) {
        var rect = canvas.getBoundingClientRect();
        mouse.x = e.clientX - rect.left;
        mouse.y = e.clientY - rect.top;
    }

    function onMouseLeave() {
        mouse.x = -9999;
        mouse.y = -9999;
    }

    function onResize() {
        resize();
        for (var i = 0; i < particles.length; i++) {
            var p = particles[i];
            p.baseX = Math.min(p.baseX, W);
            p.baseY = Math.min(p.baseY, H);
            if (p.x > W) p.x = W * 0.8;
            if (p.y > H) p.y = H * 0.8;
        }
    }

    canvas.addEventListener('mousemove', onMouseMove, { passive: true });
    canvas.addEventListener('mouseleave', onMouseLeave, { passive: true });
    window.addEventListener('resize', onResize, { passive: true });

    init();
    requestAnimationFrame(loop);
})();
