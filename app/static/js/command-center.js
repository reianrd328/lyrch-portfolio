// Command center interaction effects and smooth scrolling

document.addEventListener("DOMContentLoaded", () => {
    // Dynamic interactive card hover light tracking
    const cards = document.querySelectorAll(".metric-glass-card, .project-holo-card, .telemetry-card");
    cards.forEach(card => {
        card.addEventListener("mousemove", (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            card.style.setProperty("--mouse-x", `${x}px`);
            card.style.setProperty("--mouse-y", `${y}px`);
        });
    });
});

