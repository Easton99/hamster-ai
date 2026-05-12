/* Hamster AI Docs — shared site JS */

const BASE = window.location.hostname.includes('github.io') ? '/hamster-ai' : '';

const NAV = [
  { label: 'Home', href: '/' },
  { label: 'Getting Started', href: '/getting-started/' },
  {
    label: 'Functionality', href: '/functionality/',
    children: [
      { label: 'Memory & Notes',  href: '/functionality/memory' },
      { label: 'Modes',           href: '/functionality/modes' },
      { label: 'Commands',        href: '/functionality/commands' },
      { label: 'Mini Widget',     href: '/functionality/mini-widget' },
    ],
  },
  {
    label: 'Plugins', href: '/plugins/',
    children: [
      { label: 'Default Plugins',  href: '/plugins/default' },
      { label: 'Optional Plugins', href: '/plugins/optional' },
    ],
  },
  {
    label: 'Settings', href: '/settings/',
    children: [
      { label: 'General',       href: '/settings/general' },
      { label: 'Appearance',    href: '/settings/appearance' },
      { label: 'Mode Settings', href: '/settings/modes' },
    ],
  },
  {
    label: 'Diagnostics', href: '/diagnostics/',
    children: [
      { label: 'Health Checks', href: '/diagnostics/health-checks' },
      { label: 'Logs',          href: '/diagnostics/logs' },
      { label: 'Self-Fix',      href: '/diagnostics/self-fix' },
    ],
  },
  { label: 'Privacy', href: '/privacy/' },
  { label: 'FAQ',     href: '/faq/' },
];

function currentPath() {
  let p = window.location.pathname;
  if (BASE) p = p.replace(BASE, '');
  if (!p.endsWith('/')) p = p + '/';
  return p;
}

function isActive(href) {
  const cur = currentPath();
  let h = href.endsWith('/') ? href : href + '/';
  if (h === '//') h = '/';
  return cur === h;
}

function isSection(item) {
  const cur = currentPath();
  const base = item.href.endsWith('/') ? item.href : item.href + '/';
  return base !== '/' && cur.startsWith(base);
}

function buildNav() {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar) return;

  const logo = document.createElement('a');
  logo.className = 'sidebar-logo';
  logo.href = BASE + '/';
  logo.innerHTML = `
    <svg width="36" height="36" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <ellipse cx="16" cy="12" rx="10" ry="10" fill="#F5E6D3" stroke="#A67C52" stroke-width="2"/>
      <ellipse cx="48" cy="12" rx="10" ry="10" fill="#F5E6D3" stroke="#A67C52" stroke-width="2"/>
      <ellipse cx="32" cy="36" rx="24" ry="22" fill="#F5E6D3" stroke="#A67C52" stroke-width="2"/>
      <ellipse cx="13" cy="41" rx="9" ry="7" fill="#F2B880"/>
      <ellipse cx="51" cy="41" rx="9" ry="7" fill="#F2B880"/>
      <ellipse cx="32" cy="44" rx="6" ry="4" fill="#A67C52"/>
    </svg>
    <div class="sidebar-logo-text">
      <strong>Hamster AI</strong>
      <span>Documentation</span>
    </div>`;
  sidebar.appendChild(logo);

  const nav = document.createElement('nav');
  nav.className = 'sidebar-nav';

  NAV.forEach(item => {
    const active = isActive(item.href);
    const section = isSection(item);

    const link = document.createElement('a');
    link.className = 'nav-item' + (active || section ? ' active' : '');
    link.href = BASE + item.href;
    link.textContent = item.label;
    nav.appendChild(link);

    if (item.children && (section || active)) {
      item.children.forEach(child => {
        const cl = document.createElement('a');
        cl.className = 'nav-child' + (isActive(child.href) ? ' active' : '');
        cl.href = BASE + child.href;
        cl.textContent = child.label;
        nav.appendChild(cl);
      });
    }
  });

  sidebar.appendChild(nav);

  // Hamburger toggle
  const toggle = document.getElementById('nav-toggle');
  if (toggle) {
    toggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });
    document.addEventListener('click', e => {
      if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    });
  }
}

function buildFooter() {
  const footer = document.querySelector('.site-footer');
  if (!footer) return;
  footer.innerHTML = `
    <span>Hamster AI &mdash; local-first Windows AI companion</span>
    <span>
      <a href="https://github.com/Easton99/hamster-ai" target="_blank">GitHub</a> &middot;
      <a href="${BASE}/privacy/">Privacy</a> &middot;
      <a href="${BASE}/faq/">FAQ</a>
    </span>`;
}

document.addEventListener('DOMContentLoaded', () => {
  buildNav();
  buildFooter();
});
