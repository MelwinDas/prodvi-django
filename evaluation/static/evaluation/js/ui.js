/**
 * PRODVI UI — Shared vanilla JS utilities
 * Toast · Loading · Password Toggle · Inline Validation · Modal · CountUp · Confetti
 */

/* ─── Toast ──────────────────────────────────────────────────────────────── */
window.ProdviUI = window.ProdviUI || {};

ProdviUI.toast = (function () {
  let container = null;

  function getContainer() {
    if (!container) {
      container = document.createElement('div');
      container.id = 'prodvi-toast-container';
      container.className = 'fixed top-5 right-5 z-[9999] flex flex-col gap-3 pointer-events-none';
      document.body.appendChild(container);
    }
    return container;
  }

  function show(message, type = 'info', duration = 3500) {
    const c = getContainer();
    const colors = {
      success: 'bg-emerald-600 text-white',
      error:   'bg-red-600   text-white',
      info:    'bg-indigo-600 text-white',
      warning: 'bg-amber-500 text-white'
    };
    const icons = { success: 'check_circle', error: 'error', info: 'info', warning: 'warning' };

    const el = document.createElement('div');
    el.className = [
      'pointer-events-auto flex items-center gap-3 px-5 py-3.5 rounded-2xl shadow-2xl',
      'text-sm font-semibold min-w-[260px] max-w-xs',
      'translate-x-full opacity-0 transition-all duration-300',
      colors[type] || colors.info
    ].join(' ');
    el.innerHTML = `<span class="material-symbols-outlined text-[20px]">${icons[type] || 'info'}</span><span>${message}</span>`;
    c.appendChild(el);

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        el.classList.remove('translate-x-full', 'opacity-0');
      });
    });

    setTimeout(() => {
      el.classList.add('translate-x-full', 'opacity-0');
      el.addEventListener('transitionend', () => el.remove(), { once: true });
    }, duration);
  }

  return { show, success: m => show(m, 'success'), error: m => show(m, 'error'), info: m => show(m, 'info'), warning: m => show(m, 'warning') };
})();

/* ─── Loading State on Submit ────────────────────────────────────────────── */
ProdviUI.loading = {
  attach(form, btnSelector = '[type="submit"]') {
    if (!form) return;
    form.addEventListener('submit', function (e) {
      const btn = form.querySelector(btnSelector);
      if (!btn) return;
      // Do a brief timeout so validation runs first
      requestAnimationFrame(() => {
        if (form.checkValidity && !form.checkValidity()) return;
        btn.disabled = true;
        const original = btn.innerHTML;
        btn.dataset.original = original;
        btn.innerHTML = `<svg class="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24" fill="none"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg> Processing…`;
        btn.classList.add('opacity-80');
      });
    });
  }
};

/* ─── Password Toggle ─────────────────────────────────────────────────────── */
ProdviUI.passwordToggle = {
  init() {
    document.querySelectorAll('[data-toggle-password]').forEach(btn => {
      const targetId = btn.dataset.togglePassword;
      const input = targetId ? document.getElementById(targetId) : btn.closest('.relative')?.querySelector('input[type="password"], input[type="text"]');
      if (!input) return;
      const icon = btn.querySelector('.material-symbols-outlined') || btn;
      btn.addEventListener('click', () => {
        const isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        if (icon.tagName === 'SPAN') icon.textContent = isPassword ? 'visibility_off' : 'visibility';
      });
    });
  }
};

/* ─── Inline Form Validation ─────────────────────────────────────────────── */
ProdviUI.validate = {
  init(form) {
    if (!form) return;
    const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
    inputs.forEach(input => {
      input.addEventListener('blur', () => this._check(input));
      input.addEventListener('input', () => this._clearError(input));
    });

    // Password match
    const pw = form.querySelector('input[name="password"]');
    const cpw = form.querySelector('input[name="confirm_password"]');
    if (pw && cpw) {
      cpw.addEventListener('input', () => {
        if (cpw.value && pw.value !== cpw.value) {
          this._setError(cpw, 'Passwords do not match');
        } else {
          this._clearError(cpw);
        }
      });
    }
  },
  _check(input) {
    if (!input.value.trim()) {
      this._setError(input, `${input.placeholder || 'This field'} is required`);
    } else if (input.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.value)) {
      this._setError(input, 'Enter a valid email address');
    } else {
      this._clearError(input);
    }
  },
  _setError(input, msg) {
    input.classList.add('ring-2', 'ring-red-400', 'outline-red-400');
    let err = input.parentElement.querySelector('.field-error');
    if (!err) {
      err = document.createElement('p');
      err.className = 'field-error text-xs text-red-500 mt-1 font-medium flex items-center gap-1';
      err.innerHTML = `<span class="material-symbols-outlined text-[14px]">error</span><span>${msg}</span>`;
      input.parentElement.appendChild(err);
    } else {
      err.querySelector('span:last-child').textContent = msg;
    }
  },
  _clearError(input) {
    input.classList.remove('ring-2', 'ring-red-400', 'outline-red-400');
    const err = input.parentElement.querySelector('.field-error');
    if (err) err.remove();
  }
};

/* ─── Password Strength ───────────────────────────────────────────────────── */
ProdviUI.passwordStrength = {
  init(inputEl, barEl, labelEl) {
    if (!inputEl || !barEl) return;
    inputEl.addEventListener('input', () => {
      const val = inputEl.value;
      let score = 0;
      if (val.length >= 8) score++;
      if (/[A-Z]/.test(val)) score++;
      if (/[0-9]/.test(val)) score++;
      if (/[^A-Za-z0-9]/.test(val)) score++;
      const levels = [
        { w: '0%', color: 'bg-gray-200', label: '' },
        { w: '25%', color: 'bg-red-500', label: 'Weak' },
        { w: '50%', color: 'bg-amber-400', label: 'Fair' },
        { w: '75%', color: 'bg-blue-400', label: 'Good' },
        { w: '100%', color: 'bg-emerald-500', label: 'Strong' },
      ];
      const lvl = val.length === 0 ? levels[0] : levels[score] || levels[4];
      barEl.style.width = lvl.w;
      barEl.className = `h-full rounded-full transition-all duration-400 ${lvl.color}`;
      if (labelEl) labelEl.textContent = lvl.label;
    });
  }
};

/* ─── Count-Up Animation ─────────────────────────────────────────────────── */
ProdviUI.countUp = {
  init(selector = '[data-countup]') {
    document.querySelectorAll(selector).forEach(el => {
      const target = parseFloat(el.dataset.countup || el.textContent.replace(/[^0-9.]/g, ''));
      if (isNaN(target)) return;
      const suffix = el.dataset.suffix || '';
      const duration = 1000;
      const start = Date.now();
      const isFloat = target % 1 !== 0;
      function step() {
        const elapsed = Date.now() - start;
        const progress = Math.min(elapsed / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3);
        const value = isFloat ? (ease * target).toFixed(1) : Math.round(ease * target);
        el.textContent = value + suffix;
        if (progress < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    });
  }
};

/* ─── Table Search Filter ────────────────────────────────────────────────── */
ProdviUI.tableSearch = {
  init(inputId, tableId) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    if (!input || !table) return;
    input.addEventListener('input', () => {
      const q = input.value.toLowerCase();
      table.querySelectorAll('tbody tr').forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }
};

/* ─── Collapsible Rows ───────────────────────────────────────────────────── */
ProdviUI.collapsible = {
  init(triggerSelector, contentSelector) {
    document.querySelectorAll(triggerSelector).forEach(trigger => {
      const target = trigger.closest('tr')?.nextElementSibling;
      if (!target) return;
      target.style.display = 'none';
      trigger.style.cursor = 'pointer';
      trigger.addEventListener('click', () => {
        const hidden = target.style.display === 'none';
        target.style.display = hidden ? '' : 'none';
        const icon = trigger.querySelector('.material-symbols-outlined.collapse-icon');
        if (icon) icon.textContent = hidden ? 'expand_less' : 'expand_more';
      });
    });
  }
};

/* ─── Modal ──────────────────────────────────────────────────────────────── */
ProdviUI.modal = {
  open(id) {
    const m = document.getElementById(id);
    if (m) { m.classList.remove('hidden'); m.classList.add('flex'); }
  },
  close(id) {
    const m = document.getElementById(id);
    if (m) { m.classList.add('hidden'); m.classList.remove('flex'); }
  },
  init() {
    document.querySelectorAll('[data-modal-open]').forEach(btn => {
      btn.addEventListener('click', () => this.open(btn.dataset.modalOpen));
    });
    document.querySelectorAll('[data-modal-close]').forEach(btn => {
      btn.addEventListener('click', () => this.close(btn.dataset.modalClose));
    });
    document.querySelectorAll('.prodvi-modal-backdrop').forEach(modal => {
      modal.addEventListener('click', e => {
        if (e.target === modal) this.close(modal.id);
      });
    });
  }
};

/* ─── Confetti ───────────────────────────────────────────────────────────── */
ProdviUI.confetti = {
  burst() {
    const colors = ['#3952bc', '#72479e', '#a78bfa', '#10b981', '#f59e0b'];
    for (let i = 0; i < 80; i++) {
      const el = document.createElement('div');
      const size = Math.random() * 8 + 4;
      el.style.cssText = `
        position:fixed; pointer-events:none; z-index:9999;
        width:${size}px; height:${size}px; border-radius:${Math.random() > 0.5 ? '50%' : '2px'};
        background:${colors[Math.floor(Math.random() * colors.length)]};
        left:${Math.random() * 100}vw; top:-10px;
        animation: confetti-fall ${1.5 + Math.random() * 2}s linear ${Math.random() * 0.5}s forwards;
      `;
      document.body.appendChild(el);
      el.addEventListener('animationend', () => el.remove());
    }
  }
};

// Inject confetti keyframe once
(function () {
  if (document.getElementById('prodvi-confetti-style')) return;
  const style = document.createElement('style');
  style.id = 'prodvi-confetti-style';
  style.textContent = `
    @keyframes confetti-fall {
      0%   { transform: translateY(0) rotate(0deg);   opacity: 1; }
      100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
    }
    .btn-primary {
      background: linear-gradient(135deg, #3952bc 0%, #72479e 100%);
      color: #f2f1ff;
      font-weight: 700;
      transition: transform 0.15s, box-shadow 0.15s;
      box-shadow: 0 4px 15px rgba(57,82,188,0.3);
    }
    .btn-primary:hover  { transform: translateY(-2px) scale(1.02); box-shadow: 0 8px 25px rgba(57,82,188,0.4); }
    .btn-primary:active { transform: scale(0.97); box-shadow: none; }
    .btn-secondary {
      background: white; color: #3952bc;
      border: 2px solid #3952bc; font-weight: 700;
      transition: background 0.15s, transform 0.15s;
    }
    .btn-secondary:hover  { background: #f3e8ff; transform: translateY(-1px); }
    .btn-secondary:active { transform: scale(0.97); }
    .card-hover {
      transition: transform 0.2s, box-shadow 0.2s;
    }
    .card-hover:hover {
      transform: translateY(-4px);
      box-shadow: 0 12px 40px rgba(57,82,188,0.12);
    }
  `;
  document.head.appendChild(style);
})();
