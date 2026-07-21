// ===== Scroll reveal (IntersectionObserver, reduced-motion safe) =====
(function () {
  const els = document.querySelectorAll(".reveal");
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (reduce || !("IntersectionObserver" in window)) {
    els.forEach((el) => el.classList.add("in"));
    return;
  }

  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const el = entry.target;
          // small stagger among siblings entering together
          const delay = Math.min((el.dataset.idx || 0) * 70, 350);
          setTimeout(() => el.classList.add("in"), delay);
          io.unobserve(el);
        }
      });
    },
    { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
  );

  // assign per-group stagger index
  let idx = 0;
  let lastParent = null;
  els.forEach((el) => {
    if (el.parentElement !== lastParent) {
      idx = 0;
      lastParent = el.parentElement;
    }
    el.dataset.idx = idx++;
    io.observe(el);
  });
})();

// ===== Mobile nav toggle =====
(function () {
  const toggle = document.getElementById("navToggle");
  const links = document.getElementById("navLinks");
  if (!toggle || !links) return;

  toggle.addEventListener("click", () => {
    const open = links.classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(open));
    toggle.textContent = open ? "CLOSE" : "MENU";
  });

  links.querySelectorAll("a").forEach((a) =>
    a.addEventListener("click", () => {
      links.classList.remove("open");
      toggle.setAttribute("aria-expanded", "false");
      toggle.textContent = "MENU";
    })
  );
})();

// ===== Footer year =====
(function () {
  const y = document.getElementById("year");
  if (y) y.textContent = new Date().getFullYear();
})();
