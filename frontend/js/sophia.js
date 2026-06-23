/**
 * sophía.js — Decorative geometric shape renderer for the landing page hero.
 * Draws animated Sophía-style composition onto an SVG or Canvas element.
 */

/**
 * Render the hero SVG composition.
 * Call after DOM is ready.
 */
export function renderHeroComposition(containerId = 'hero-canvas') {
  const container = document.getElementById(containerId);
  if (!container) return;

  // SVG composition: Sophía-inspired geometric shapes
  const svg = `
    <svg viewBox="0 0 600 500" xmlns="http://www.w3.org/2000/svg" class="hero-svg" aria-hidden="true">
      <!-- Background rectangle — blue -->
      <rect x="320" y="0" width="280" height="500" fill="var(--primary-blue)" opacity="0.9"/>

      <!-- Large red circle -->
      <circle cx="220" cy="180" r="160" fill="var(--primary-red)"/>

      <!-- Yellow rectangle bar -->
      <rect x="0" y="360" width="600" height="60" fill="var(--primary-yellow)"/>

      <!-- Black square (overlapping) -->
      <rect x="300" y="60" width="120" height="120" fill="var(--primary-black)"/>

      <!-- Small white circle -->
      <circle cx="480" cy="100" r="50" fill="var(--primary-white)" opacity="0.85"/>

      <!-- Triangle (red accent) -->
      <polygon points="520,280 600,420 440,420" fill="var(--primary-red)" opacity="0.7"/>

      <!-- Thin vertical line -->
      <rect x="316" y="0" width="4" height="500" fill="var(--primary-yellow)"/>

      <!-- Small squares scattered -->
      <rect x="40" y="40" width="30" height="30" fill="var(--primary-yellow)"/>
      <rect x="140" y="420" width="20" height="20" fill="var(--primary-black)"/>
      <rect x="560" y="200" width="25" height="25" fill="var(--primary-yellow)"/>
    </svg>
  `;

  container.innerHTML = svg;
}

/**
 * Animate floating geometric shapes in a background element.
 * Creates small shapes that drift slowly for visual depth.
 */
export function animateBackgroundShapes(containerId = 'bg-shapes') {
  const container = document.getElementById(containerId);
  if (!container) return;

  const shapes = [
    { type: 'circle',   color: 'var(--primary-red)',    size: 60, x: 10, y: 20, speed: 0.3 },
    { type: 'square',   color: 'var(--primary-blue)',   size: 40, x: 80, y: 60, speed: 0.2 },
    { type: 'circle',   color: 'var(--primary-yellow)', size: 30, x: 50, y: 80, speed: 0.4 },
    { type: 'square',   color: 'var(--primary-red)',    size: 20, x: 20, y: 70, speed: 0.25 },
    { type: 'circle',   color: 'var(--primary-blue)',   size: 15, x: 90, y: 30, speed: 0.35 },
  ];

  shapes.forEach((s, i) => {
    const el = document.createElement('div');
    el.style.cssText = `
      position: absolute;
      width: ${s.size}px;
      height: ${s.size}px;
      background-color: ${s.color};
      border-radius: ${s.type === 'circle' ? '50%' : '0'};
      left: ${s.x}%;
      top: ${s.y}%;
      opacity: 0.08;
      pointer-events: none;
      animation: floatShape${i} ${8 + i * 2}s ease-in-out infinite alternate;
    `;

    // Inject keyframes
    const style = document.createElement('style');
    style.textContent = `
      @keyframes floatShape${i} {
        0%   { transform: translate(0, 0) rotate(0deg); }
        50%  { transform: translate(${10 + i * 5}px, ${-15 + i * 3}px) rotate(${15 + i * 10}deg); }
        100% { transform: translate(${-8 + i * 3}px, ${12 + i * 4}px) rotate(${-10 + i * 5}deg); }
      }
    `;
    document.head.appendChild(style);
    container.appendChild(el);
  });
}
