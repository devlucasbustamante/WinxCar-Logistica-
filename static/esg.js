/* ============================================================
   Animação dos cards ESG / ODS
   - Fade + slide-up ao entrar na viewport
   - Pulso nas tags ODS
   - Hover "lift" reforçado (complementa CSS)
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {

    const cards = document.querySelectorAll('.esg-card');
    if (!cards.length) return;

    // Marca todos como escondidos antes de animar
    cards.forEach(card => card.classList.add('esg-hidden'));

    // Observa quando cada card entra na tela
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;

            const card = entry.target;
            const delay = Array.from(cards).indexOf(card) * 120;

            setTimeout(() => {
                card.classList.remove('esg-hidden');
                card.classList.add('esg-show');

                // Pulso escalonado nas tags ODS
                card.querySelectorAll('.esg-tag').forEach((tag, idx) => {
                    setTimeout(() => {
                        tag.classList.add('esg-pulse');
                        setTimeout(() => tag.classList.remove('esg-pulse'), 700);
                    }, 300 + idx * 120);
                });
            }, delay);

            observer.unobserve(card);
        });
    }, {
        threshold: 0.15,
        rootMargin: '0px 0px -40px 0px'
    });

    cards.forEach(card => observer.observe(card));
});