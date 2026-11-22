/* ==========================================================================
   PrettyDocs — Motor de Presentación (Teclado, Escalado 16:9, Overview,
   Tema Claro/Oscuro, Fullscreen y Cronómetro Regresivo 20:00)
   100 % Offline · Compatible con file:// y servidores locales
   ========================================================================== */

(function () {
  const ns = (window.PrettyDocsPresentation = window.PrettyDocsPresentation || {});

  const LOGICAL_W = 1280;
  const LOGICAL_H = 720;
  const TIMER_INITIAL_S = 20 * 60; // 20:00 minutos reglamentarios
  const WARN_REMAINING_S = 3 * 60; // Minuto 17 transcurrido -> ámbar
  const DANGER_REMAINING_S = 1 * 60; // Minuto 19 transcurrido -> rojo

  class PrettyDocsDeck {
    constructor() {
      this.stage = document.getElementById('deck-stage');
      this.slides = Array.from(document.querySelectorAll('.slide'));
      this.total = this.slides.length;
      this.current = 0;

      // Controles HUD
      this.progressBar = document.getElementById('deck-progress-bar');
      this.counterEl = document.getElementById('hud-counter');
      this.timerEl = document.getElementById('hud-timer');
      this.overviewEl = document.getElementById('overview-overlay');
      this.overviewGrid = document.getElementById('overview-grid');
      this.helpEl = document.getElementById('help-overlay');

      // Estado del cronómetro
      this.remainingSeconds = TIMER_INITIAL_S;
      this.timerInterval = null;

      // Touch swipe
      this.touchStartX = null;

      this.init();
    }

    init() {
      // Renderizar datos y gráficas SVG desde data.js
      if (ns.Charts && ns.DATA) {
        ns.Charts.renderAll(ns.DATA);
      }

      this.buildOverview();
      this.bindEvents();
      this.scaleStage();

      // Leer slide inicial del hash (#slide-N)
      const initialIndex = this.readHashIndex();
      this.goTo(initialIndex, { updateHash: false });
      this.renderTimer();
    }

    scaleStage() {
      if (!this.stage) return;
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const scale = Math.min(vw / LOGICAL_W, vh / LOGICAL_H);
      this.stage.style.transform = `scale(${scale})`;
    }

    readHashIndex() {
      const match = window.location.hash.match(/slide-(\d+)/i);
      if (!match) return 0;
      const idx = parseInt(match[1], 10) - 1;
      return Number.isNaN(idx) ? 0 : Math.max(0, Math.min(this.total - 1, idx));
    }

    goTo(index, { updateHash = true } = {}) {
      const clamped = Math.max(0, Math.min(this.total - 1, index));
      this.current = clamped;

      this.slides.forEach((slide, i) => {
        const active = i === clamped;
        slide.classList.toggle('is-active', active);
        slide.setAttribute('aria-hidden', active ? 'false' : 'true');
      });

      // Actualizar barra de progreso y contador
      const pct = ((clamped + 1) / this.total) * 100;
      if (this.progressBar) this.progressBar.style.width = `${pct}%`;
      if (this.counterEl) {
        const cur = String(clamped + 1).padStart(2, '0');
        const tot = String(this.total).padStart(2, '0');
        this.counterEl.textContent = `${cur} / ${tot}`;
      }

      // Actualizar estado en overview
      if (this.overviewGrid) {
        Array.from(this.overviewGrid.children).forEach((card, i) => {
          card.classList.toggle('is-current', i === clamped);
        });
      }

      if (updateHash) {
        history.replaceState(null, '', `#slide-${clamped + 1}`);
      }

      // Animar conteo numérico si la lámina contiene contadores (Slide 07)
      this.animateCounters(this.slides[clamped]);
    }

    next() {
      if (this.current < this.total - 1) this.goTo(this.current + 1);
    }

    prev() {
      if (this.current > 0) this.goTo(this.current - 1);
    }

    animateCounters(slideEl) {
      if (!slideEl) return;
      const els = slideEl.querySelectorAll('[data-count-target]');
      els.forEach((el) => {
        const target = parseInt(el.dataset.countTarget, 10);
        const suffix = el.dataset.countSuffix || '';
        if (Number.isNaN(target)) return;

        const duration = 650;
        const start = performance.now();
        const step = (now) => {
          const t = Math.min(1, (now - start) / duration);
          const eased = 1 - Math.pow(1 - t, 3);
          const current = Math.round(eased * target);
          el.textContent = `${current}${suffix}`;
          if (t < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
      });
    }

    /* ----------------------------------------------------------------------
       Cronómetro regresivo 20:00 (C = iniciar/pausar, R = reiniciar)
       ---------------------------------------------------------------------- */
    toggleTimer() {
      if (this.timerInterval) {
        clearInterval(this.timerInterval);
        this.timerInterval = null;
      } else {
        if (this.remainingSeconds <= 0) this.remainingSeconds = TIMER_INITIAL_S;
        this.timerInterval = setInterval(() => {
          if (this.remainingSeconds > 0) {
            this.remainingSeconds -= 1;
            this.renderTimer();
          } else {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
            this.renderTimer();
          }
        }, 1000);
      }
      this.renderTimer();
    }

    resetTimer() {
      if (this.timerInterval) {
        clearInterval(this.timerInterval);
        this.timerInterval = null;
      }
      this.remainingSeconds = TIMER_INITIAL_S;
      this.renderTimer();
    }

    renderTimer() {
      if (!this.timerEl) return;
      const mins = Math.floor(this.remainingSeconds / 60);
      const secs = this.remainingSeconds % 60;
      this.timerEl.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

      this.timerEl.classList.toggle('is-running', Boolean(this.timerInterval));
      this.timerEl.classList.toggle(
        'is-warning',
        this.remainingSeconds <= WARN_REMAINING_S && this.remainingSeconds > DANGER_REMAINING_S
      );
      this.timerEl.classList.toggle('is-danger', this.remainingSeconds <= DANGER_REMAINING_S);
    }

    /* ----------------------------------------------------------------------
       Vista de cuadrícula Overview (tecla G)
       ---------------------------------------------------------------------- */
    buildOverview() {
      if (!this.overviewGrid) return;
      this.overviewGrid.innerHTML = '';

      this.slides.forEach((slide, i) => {
        const title = slide.dataset.title || `Diapositiva ${i + 1}`;
        const kicker = slide.dataset.kicker || '';
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'overview-card';
        btn.innerHTML = `
          <div>
            <div class="overview-card__num">${String(i + 1).padStart(2, '0')} / ${String(this.total).padStart(2, '0')}</div>
            <div class="overview-card__title">${title}</div>
          </div>
          <div class="overview-card__kicker">${kicker}</div>
        `;
        btn.addEventListener('click', () => {
          this.goTo(i);
          this.toggleOverview(false);
        });
        this.overviewGrid.appendChild(btn);
      });
    }

    toggleOverview(force) {
      if (!this.overviewEl) return;
      const willOpen = typeof force === 'boolean' ? force : this.overviewEl.hidden;
      this.overviewEl.hidden = !willOpen;
    }

    toggleHelp(force) {
      if (!this.helpEl) return;
      const willOpen = typeof force === 'boolean' ? force : this.helpEl.hidden;
      this.helpEl.hidden = !willOpen;
    }

    /* ----------------------------------------------------------------------
       Tema Claro / Oscuro (tecla T) y Pantalla Completa (tecla F)
       ---------------------------------------------------------------------- */
    toggleTheme() {
      const root = document.documentElement;
      const current = root.getAttribute('data-theme');
      if (current === 'dark') {
        root.removeAttribute('data-theme');
      } else {
        root.setAttribute('data-theme', 'dark');
      }
    }

    toggleFullscreen() {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen?.().catch(() => {});
      } else {
        document.exitFullscreen?.().catch(() => {});
      }
    }

    bindEvents() {
      window.addEventListener('resize', () => this.scaleStage());
      window.addEventListener('hashchange', () => {
        this.goTo(this.readHashIndex(), { updateHash: false });
      });

      // Teclado (incluye puntero presentador: PageUp / PageDown / ArrowLeft / ArrowRight)
      document.addEventListener('keydown', (e) => {
        if (e.metaKey || e.ctrlKey || e.altKey) return;

        const key = e.key;
        if (key === 'Escape') {
          this.toggleOverview(false);
          this.toggleHelp(false);
          return;
        }

        if (key === 'g' || key === 'G') {
          e.preventDefault();
          this.toggleHelp(false);
          this.toggleOverview();
          return;
        }

        if (key === '?' || key === 'h' || key === 'H') {
          e.preventDefault();
          this.toggleOverview(false);
          this.toggleHelp();
          return;
        }

        if (key === 'c' || key === 'C') {
          e.preventDefault();
          this.toggleTimer();
          return;
        }

        if (key === 'r' || key === 'R') {
          e.preventDefault();
          this.resetTimer();
          return;
        }

        if (key === 't' || key === 'T') {
          e.preventDefault();
          this.toggleTheme();
          return;
        }

        if (key === 'f' || key === 'F') {
          e.preventDefault();
          this.toggleFullscreen();
          return;
        }

        // Navegación (ignorar si overview está abierto)
        if (this.overviewEl && !this.overviewEl.hidden) return;

        if (key === 'ArrowRight' || key === ' ' || key === 'PageDown' || key === 'Enter') {
          e.preventDefault();
          this.next();
        } else if (key === 'ArrowLeft' || key === 'PageUp' || key === 'Backspace') {
          e.preventDefault();
          this.prev();
        } else if (key === 'Home') {
          e.preventDefault();
          this.goTo(0);
        } else if (key === 'End') {
          e.preventDefault();
          this.goTo(this.total - 1);
        }
      });

      // Botones HUD
      document.getElementById('btn-prev')?.addEventListener('click', () => this.prev());
      document.getElementById('btn-next')?.addEventListener('click', () => this.next());
      document.getElementById('btn-overview')?.addEventListener('click', () => this.toggleOverview());
      document.getElementById('btn-close-overview')?.addEventListener('click', () => this.toggleOverview(false));
      document.getElementById('btn-theme')?.addEventListener('click', () => this.toggleTheme());
      document.getElementById('btn-fullscreen')?.addEventListener('click', () => this.toggleFullscreen());
      document.getElementById('btn-help')?.addEventListener('click', () => this.toggleHelp());
      this.timerEl?.addEventListener('click', () => this.toggleTimer());
      this.helpEl?.addEventListener('click', (e) => {
        if (e.target === this.helpEl) this.toggleHelp(false);
      });

      // Gestos táctiles
      this.stage?.addEventListener('touchstart', (e) => {
        this.touchStartX = e.changedTouches[0].clientX;
      }, { passive: true });
      this.stage?.addEventListener('touchend', (e) => {
        if (this.touchStartX === null) return;
        const dx = e.changedTouches[0].clientX - this.touchStartX;
        if (Math.abs(dx) > 48) {
          if (dx < 0) this.next();
          else this.prev();
        }
        this.touchStartX = null;
      }, { passive: true });
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    ns.deck = new PrettyDocsDeck();
  });
})();
