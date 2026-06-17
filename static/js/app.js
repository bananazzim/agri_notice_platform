(() => {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const revealItems = document.querySelectorAll(".motion-reveal, .metric-panel, .filter-panel");
  if (!reduceMotion && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return;
          }
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.08 }
    );
    revealItems.forEach((item) => observer.observe(item));
  } else {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  }

  document.querySelectorAll("[data-count-to]").forEach((element) => {
    const target = Number.parseInt(element.dataset.countTo || "0", 10);
    if (!Number.isFinite(target) || reduceMotion) {
      element.textContent = String(target);
      return;
    }

    const duration = 780;
    const startTime = performance.now();
    const animate = (time) => {
      const progress = Math.min((time - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = String(Math.round(target * eased));
      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };
    requestAnimationFrame(animate);
  });

  document.querySelectorAll(".notice-card[data-href]").forEach((card) => {
    card.addEventListener("click", (event) => {
      if (event.target.closest("a, button, input, select, textarea")) {
        return;
      }
      window.location.href = card.dataset.href;
    });

    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        window.location.href = card.dataset.href;
      }
    });

    if (reduceMotion || !window.matchMedia("(hover: hover)").matches) {
      return;
    }

    card.addEventListener("pointermove", (event) => {
      const rect = card.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;
      card.style.setProperty("--tilt-x", `${(-y * 2.8).toFixed(2)}deg`);
      card.style.setProperty("--tilt-y", `${(x * 2.8).toFixed(2)}deg`);
    });

    card.addEventListener("pointerleave", () => {
      card.style.removeProperty("--tilt-x");
      card.style.removeProperty("--tilt-y");
    });
  });

  document.querySelectorAll(".dashboard-hero, .detail-hero").forEach((hero) => {
    if (reduceMotion || !window.matchMedia("(hover: hover)").matches) {
      return;
    }

    hero.addEventListener("pointermove", (event) => {
      const rect = hero.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;
      hero.style.setProperty("--hero-pan-x", `${50 + x * 4}%`);
      hero.style.setProperty("--hero-pan-y", `${50 + y * 4}%`);
    });

    hero.addEventListener("pointerleave", () => {
      hero.style.removeProperty("--hero-pan-x");
      hero.style.removeProperty("--hero-pan-y");
    });
  });

  document.querySelectorAll("[data-copy-current-url]").forEach((button) => {
    button.addEventListener("click", async () => {
      const original = button.innerHTML;
      try {
        await navigator.clipboard.writeText(window.location.href);
        button.innerHTML = '<i class="bi bi-check2 me-1"></i>복사됨';
      } catch {
        button.innerHTML = '<i class="bi bi-exclamation-circle me-1"></i>실패';
      }
      window.setTimeout(() => {
        button.innerHTML = original;
      }, 1300);
    });
  });
})();
