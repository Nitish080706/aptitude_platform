/**
 * sidebar.js — Renders and manages the sidebar navigation.
 *
 * Usage:
 *   import { initSidebar } from './sidebar.js';
 *   initSidebar({ role: 'user', activePage: 'dashboard', scrollMode: false, profile });
 *
 * scrollMode: true  = landing page (sidebar appears after hero leaves viewport)
 *             false = inner pages (sidebar always visible)
 */

const USER_NAV = [
  { id: 'dashboard',        label: 'Dashboard',          href: '/dashboard.html',              icon: 'square'   },
  { id: 'topics',           label: 'Browse Topics',       href: '/topics.html',                 icon: 'circle'   },
  { id: 'paragraph_recall', label: 'Paragraph Recall',    href: '/paragraph-recall.html',       icon: 'brain'    },
  { id: 'history',          label: 'My History',          href: '/history.html',                icon: 'bars'     },
  { id: 'leaderboard',      label: 'Leaderboard',         href: '/leaderboard.html',            icon: 'diamond'  },
];

const ADMIN_NAV = [
  { id: 'dashboard',        label: 'Dashboard',           href: '/admin/dashboard.html',             icon: 'square'   },
  { id: 'topics',           label: 'Manage Topics',        href: '/admin/topics.html',                icon: 'circle'   },
  { id: 'questions',        label: 'Questions',            href: '/admin/questions.html',             icon: 'triangle' },
  { id: 'test_questions',   label: 'Test Questions',       href: '/admin/question_for_test.html',     icon: 'triangle' },
  { id: 'tests',            label: 'Tests',                href: '/admin/tests.html',                 icon: 'bars'     },
  { id: 'paragraph_recall', label: 'Paragraph Recall',     href: '/admin/paragraph-recall.html',      icon: 'brain'    },
  { id: 'notes',            label: 'Notes',                href: '/admin/notes.html',                 icon: 'diamond'  },
];

function iconHTML(type) {
  switch (type) {
    case 'circle':   return `<span class="icon-circle"></span>`;
    case 'square':   return `<span class="icon-square"></span>`;
    case 'triangle': return `<span class="icon-triangle"></span>`;
    case 'bars':     return `<span class="icon-bar-group"><span></span><span></span><span></span></span>`;
    case 'diamond':  return `<span class="icon-diamond"></span>`;
    case 'brain':    return `<span style="font-size:0.85em;">🧠</span>`;
    default:         return `<span class="icon-square"></span>`;
  }
}

function buildSidebar({ role, activePage, profile }) {
  const nav       = role === 'admin' ? ADMIN_NAV : USER_NAV;
  const username  = profile?.username || profile?.name || 'User';
  const initial   = (username[0] || 'U').toUpperCase();
  const roleLabel = role === 'admin' ? 'Admin' : 'Student';
  const homeHref  = role === 'admin' ? '/admin/dashboard.html' : '/dashboard.html';

  const navItems = nav.map(item => `
    <a class="nav-item ${item.id === activePage ? 'active' : ''}"
       href="${item.href}" id="nav-${item.id}">
      <span class="nav-icon">${iconHTML(item.icon)}</span>
      ${item.label}
    </a>
  `).join('');

  return `
    <a class="sidebar-brand" href="${homeHref}">
      <div class="sidebar-brand-mark">
        <div class="brand-sq" style="background:var(--primary-red);"></div>
        <div class="brand-sq" style="background:var(--primary-blue);"></div>
        <div class="brand-sq" style="background:var(--primary-yellow);"></div>
      </div>
      <div>
        <div class="sidebar-brand-name">Sophía<br>Study</div>
      </div>
    </a>

    <div class="sidebar-section">
      <div class="sidebar-section-label">${role === 'admin' ? 'Admin Panel' : 'Navigation'}</div>
      ${navItems}
    </div>

    <div class="sidebar-footer">
      <div class="sidebar-user">
        <div class="sidebar-avatar">${initial}</div>
        <div>
          <div class="sidebar-username">@${username}</div>
          <div class="sidebar-role">${roleLabel}</div>
        </div>
      </div>
      <div class="sidebar-footer-actions">
        <button class="theme-toggle" id="sidebar-theme-toggle" aria-label="Toggle theme">🌙</button>
        <button class="btn-logout" id="btn-logout">Logout</button>
      </div>
    </div>
  `;
}

export function initSidebar({ role = 'user', activePage = '', scrollMode = false, profile = null } = {}) {
  const sidebarEl = document.getElementById('sidebar');
  if (!sidebarEl) return;

  sidebarEl.className = 'sidebar' + (scrollMode ? ' hidden-until-scroll' : '');
  sidebarEl.innerHTML = buildSidebar({ role, activePage, profile });

  // ── Wire logout (dynamic import inside async handler — fine here) ──
  const logoutBtn = document.getElementById('btn-logout');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async () => {
      try {
        const mod = await import('./auth.js');
        await mod.logout();
      } catch (e) {
        window.location.href = '/index.html';
      }
    });
  }

  // ── Wire theme toggle (sync — use already-loaded theme logic) ──
  const themeBtn = document.getElementById('sidebar-theme-toggle');
  if (themeBtn) {
    // Set initial icon based on current theme
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    themeBtn.textContent = currentTheme === 'dark' ? '☀️' : '🌙';

    themeBtn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const next    = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('sophía-theme', next);
      // Update all toggle buttons on page
      document.querySelectorAll('.theme-toggle').forEach(btn => {
        btn.textContent = next === 'dark' ? '☀️' : '🌙';
      });
    });
  }

  // ── Scroll mode: show sidebar after hero leaves viewport ──
  if (scrollMode) {
    const heroEl = document.getElementById('hero');
    if (heroEl && 'IntersectionObserver' in window) {
      const observer = new IntersectionObserver(
        ([entry]) => {
          if (!entry.isIntersecting) sidebarEl.classList.add('visible');
          else                        sidebarEl.classList.remove('visible');
        },
        { threshold: 0.1 }
      );
      observer.observe(heroEl);
    }
  }

  // ── Mobile hamburger ──
  const hamburger = document.getElementById('hamburger');
  const overlay   = document.getElementById('sidebar-overlay');
  if (hamburger) {
    hamburger.addEventListener('click', () => {
      sidebarEl.classList.toggle('mobile-open');
      overlay?.classList.toggle('active');
    });
  }
  if (overlay) {
    overlay.addEventListener('click', () => {
      sidebarEl.classList.remove('mobile-open');
      overlay.classList.remove('active');
    });
  }
}
