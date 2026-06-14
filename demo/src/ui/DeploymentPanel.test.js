/**
 * @vitest-environment happy-dom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { DeploymentPanel } from './DeploymentPanel.js';

function setupDOM() {
  document.body.innerHTML = `
    <div id="timeline-panel" class="glass-panel"></div>
    <div id="speed-controls"></div>
  `;
}

function createMockSimulation() {
  return {
    currentTimeMinutes: 0,
    isRunning: true,
    speedMultiplier: 60,
    start: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
    seekTo: vi.fn(),
    setSpeed: vi.fn(),
    onTick: vi.fn(),
    offTick: vi.fn(),
  };
}

function createMockUIManager() {
  return {
    currentPhase: 'deployment',
    getCurrentPhase: vi.fn(() => 'deployment'),
  };
}

describe('DeploymentPanel', () => {
  let panel;
  let mockSimulation;
  let mockUIManager;

  beforeEach(() => {
    setupDOM();
    mockSimulation = createMockSimulation();
    mockUIManager = createMockUIManager();
    panel = new DeploymentPanel(mockUIManager, mockSimulation);
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  describe('render()', () => {
    it('renders play/pause button with id "play-pause-btn"', () => {
      const btn = document.getElementById('play-pause-btn');
      expect(btn).not.toBeNull();
      expect(btn.textContent).toBe('⏸');
    });

    it('renders time display with initial "00:00"', () => {
      const display = document.getElementById('time-display');
      expect(display).not.toBeNull();
      expect(display.textContent).toBe('00:00');
    });

    it('renders four speed buttons with correct data-speed attributes', () => {
      const container = document.getElementById('timeline-panel');
      const buttons = container.querySelectorAll('.speed-btn');
      expect(buttons.length).toBe(4);

      const speeds = Array.from(buttons).map((b) => b.getAttribute('data-speed'));
      expect(speeds).toEqual(['1', '10', '60', '120']);
    });

    it('renders 60x speed button as active by default', () => {
      const activeBtn = document.querySelector('.speed-btn.active');
      expect(activeBtn).not.toBeNull();
      expect(activeBtn.getAttribute('data-speed')).toBe('60');
    });

    it('renders timeline scrubber with correct attributes', () => {
      const scrubber = document.getElementById('timeline-scrubber');
      expect(scrubber).not.toBeNull();
      expect(scrubber.getAttribute('min')).toBe('0');
      expect(scrubber.getAttribute('max')).toBe('1439');
      expect(scrubber.getAttribute('step')).toBe('1');
      expect(scrubber.value).toBe('0');
    });

    it('renders scrubber markers (00:00, 06:00, 12:00, 18:00, 23:59)', () => {
      const markers = document.querySelectorAll('.scrubber-markers span');
      expect(markers.length).toBe(5);

      const labels = Array.from(markers).map((m) => m.textContent);
      expect(labels).toEqual(['00:00', '06:00', '12:00', '18:00', '23:59']);
    });

    it('renders event markers container', () => {
      const eventMarkers = document.getElementById('event-markers');
      expect(eventMarkers).not.toBeNull();
    });
  });

  describe('bindTimeline()', () => {
    it('calls simulation.seekTo() with scrubber value on input', () => {
      const scrubber = document.getElementById('timeline-scrubber');
      scrubber.value = '720';
      scrubber.dispatchEvent(new Event('input'));

      expect(mockSimulation.seekTo).toHaveBeenCalledWith(720);
    });

    it('calls seekTo with different values', () => {
      const scrubber = document.getElementById('timeline-scrubber');

      scrubber.value = '0';
      scrubber.dispatchEvent(new Event('input'));
      expect(mockSimulation.seekTo).toHaveBeenCalledWith(0);

      scrubber.value = '1439';
      scrubber.dispatchEvent(new Event('input'));
      expect(mockSimulation.seekTo).toHaveBeenCalledWith(1439);
    });
  });

  describe('bindSpeedControls()', () => {
    it('calls simulation.setSpeed() with the button speed value', () => {
      const buttons = document.querySelectorAll('.speed-btn');
      buttons[0].click(); // 1x
      expect(mockSimulation.setSpeed).toHaveBeenCalledWith(1);

      buttons[1].click(); // 10x
      expect(mockSimulation.setSpeed).toHaveBeenCalledWith(10);

      buttons[3].click(); // 120x
      expect(mockSimulation.setSpeed).toHaveBeenCalledWith(120);
    });

    it('toggles active class to the clicked button', () => {
      const buttons = document.querySelectorAll('.speed-btn');

      buttons[0].click(); // Click 1x
      expect(buttons[0].classList.contains('active')).toBe(true);
      expect(buttons[2].classList.contains('active')).toBe(false); // 60x no longer active

      buttons[3].click(); // Click 120x
      expect(buttons[3].classList.contains('active')).toBe(true);
      expect(buttons[0].classList.contains('active')).toBe(false);
    });
  });

  describe('bindPlayPause()', () => {
    it('pauses simulation on first click (starts as playing)', () => {
      const btn = document.getElementById('play-pause-btn');
      btn.click();

      expect(mockSimulation.pause).toHaveBeenCalledTimes(1);
      expect(btn.textContent).toBe('▶');
      expect(panel.isPlaying).toBe(false);
    });

    it('resumes simulation on second click', () => {
      const btn = document.getElementById('play-pause-btn');
      btn.click(); // pause
      btn.click(); // resume

      expect(mockSimulation.resume).toHaveBeenCalledTimes(1);
      expect(btn.textContent).toBe('⏸');
      expect(panel.isPlaying).toBe(true);
    });

    it('toggles aria-label between Play and Pause', () => {
      const btn = document.getElementById('play-pause-btn');

      btn.click(); // pause
      expect(btn.getAttribute('aria-label')).toBe('Play simulation');

      btn.click(); // resume
      expect(btn.getAttribute('aria-label')).toBe('Pause simulation');
    });
  });

  describe('simulation.onTick updates', () => {
    it('registers a tick callback on the simulation', () => {
      expect(mockSimulation.onTick).toHaveBeenCalledTimes(1);
      expect(typeof mockSimulation.onTick.mock.calls[0][0]).toBe('function');
    });

    it('updates scrubber value on tick', () => {
      const tickCallback = mockSimulation.onTick.mock.calls[0][0];
      tickCallback(720);

      const scrubber = document.getElementById('timeline-scrubber');
      expect(scrubber.value).toBe('720');
    });

    it('updates time display on tick', () => {
      const tickCallback = mockSimulation.onTick.mock.calls[0][0];
      tickCallback(720); // 12:00

      const display = document.getElementById('time-display');
      expect(display.textContent).toBe('12:00');
    });

    it('formats time correctly for various values', () => {
      const tickCallback = mockSimulation.onTick.mock.calls[0][0];
      const display = document.getElementById('time-display');

      tickCallback(0);
      expect(display.textContent).toBe('00:00');

      tickCallback(390); // 06:30
      expect(display.textContent).toBe('06:30');

      tickCallback(1439); // 23:59
      expect(display.textContent).toBe('23:59');
    });

    it('floors fractional minutes for scrubber', () => {
      const tickCallback = mockSimulation.onTick.mock.calls[0][0];
      tickCallback(90.7);

      const scrubber = document.getElementById('timeline-scrubber');
      expect(scrubber.value).toBe('90');
    });
  });

  describe('formatTime()', () => {
    it('returns "HH:MM" format for 0 minutes', () => {
      expect(panel.formatTime(0)).toBe('00:00');
    });

    it('returns "HH:MM" format for 720 minutes (noon)', () => {
      expect(panel.formatTime(720)).toBe('12:00');
    });

    it('returns "HH:MM" format for 1439 minutes (end of day)', () => {
      expect(panel.formatTime(1439)).toBe('23:59');
    });

    it('pads single-digit hours and minutes', () => {
      expect(panel.formatTime(65)).toBe('01:05');
    });
  });

  describe('speed controls', () => {
    it('renders 4 speed buttons in the timeline panel', () => {
      const container = document.getElementById('timeline-panel');
      const buttons = container.querySelectorAll('.speed-btn');
      expect(buttons.length).toBe(4);
    });

    it('renders speed buttons with correct data-speed attributes', () => {
      const container = document.getElementById('timeline-panel');
      const buttons = container.querySelectorAll('.speed-btn');
      const speeds = Array.from(buttons).map((b) => b.getAttribute('data-speed'));
      expect(speeds).toEqual(['1', '10', '60', '120']);
    });

    it('has 60x active by default', () => {
      const container = document.getElementById('timeline-panel');
      const activeBtn = container.querySelector('.speed-btn.active');
      expect(activeBtn).not.toBeNull();
      expect(activeBtn.getAttribute('data-speed')).toBe('60');
    });
  });

  describe('power cut button', () => {
    it('renders the Power Cut button with correct id', () => {
      const btn = document.getElementById('power-cut-btn');
      expect(btn).not.toBeNull();
    });

    it('renders with "⚡ Power Cut" text', () => {
      const btn = document.getElementById('power-cut-btn');
      expect(btn.textContent).toBe('⚡ Power Cut');
    });

    it('lives inside the timeline panel', () => {
      const btn = document.getElementById('power-cut-btn');
      expect(btn.closest('#timeline-panel')).not.toBeNull();
    });

    it('has aria-label for accessibility', () => {
      const btn = document.getElementById('power-cut-btn');
      expect(btn.getAttribute('aria-label')).toBe('Trigger power cut scenario');
    });

    it('does not create duplicate buttons on re-render', () => {
      // Creating another panel re-renders the timeline; still one button
      new DeploymentPanel(mockUIManager, mockSimulation);
      const buttons = document.querySelectorAll('#power-cut-btn');
      expect(buttons.length).toBe(1);
    });
  });
});
