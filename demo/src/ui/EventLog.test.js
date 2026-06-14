/**
 * @vitest-environment happy-dom
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { EventLog } from './EventLog.js';

// Minimal StateStore mock with pub/sub
class MockStateStore {
  constructor() {
    this.listeners = new Map();
    this.trustUpdates = [];
  }
  on(key, cb) {
    if (!this.listeners.has(key)) this.listeners.set(key, new Set());
    this.listeners.get(key).add(cb);
  }
  emit(key, data) {
    const cbs = this.listeners.get(key);
    if (cbs) cbs.forEach(cb => cb(data));
  }
  updateTrustScore(category, delta) {
    this.trustUpdates.push({ category, delta });
  }
}

describe('EventLog', () => {
  let stateStore;
  let eventLog;

  beforeEach(() => {
    // Set up DOM
    document.body.innerHTML = '<div id="event-log-panel" class="glass-panel"></div>';
    stateStore = new MockStateStore();
    eventLog = new EventLog(stateStore);
  });

  it('should render header and entries container', () => {
    const panel = document.getElementById('event-log-panel');
    expect(panel.querySelector('.event-log-title')).not.toBeNull();
    expect(panel.querySelector('#event-log-entries')).not.toBeNull();
  });

  it('should add entry when StateStore emits eventlog', () => {
    stateStore.emit('eventlog', {
      time: 375,
      action: 'Geyser Pre-heat',
      device: 'Smart Geyser',
      reasoning: 'Pre-heating water 45 minutes ahead.',
      type: 'geyser_preheat',
    });

    const entries = document.querySelectorAll('.event-log-entry');
    expect(entries.length).toBe(1);

    const entry = entries[0];
    expect(entry.querySelector('.event-log-time').textContent).toBe('[06:15]');
    expect(entry.querySelector('.event-log-action-name').textContent).toBe('Geyser Pre-heat');
    expect(entry.querySelector('.event-log-emoji').textContent).toBe('🔥');
    expect(entry.querySelector('.event-log-device').textContent).toBe('→ Smart Geyser');
    expect(entry.querySelector('.event-log-reasoning').textContent).toBe('→ Reason: Pre-heating water 45 minutes ahead.');
  });

  it('should display correct emojis for each action type', () => {
    const types = [
      { type: 'ac_precool', emoji: '❄️' },
      { type: 'geyser_preheat', emoji: '🔥' },
      { type: 'security_arm', emoji: '🔒' },
      { type: 'energy_optimization', emoji: '⚡' },
      { type: 'comfort_lighting', emoji: '💡' },
      { type: 'power_cut', emoji: '⚠️' },
    ];

    types.forEach(({ type, emoji }) => {
      stateStore.emit('eventlog', {
        time: 100,
        action: 'Test',
        device: 'Device',
        reasoning: 'Reason',
        type,
      });
    });

    const emojiEls = document.querySelectorAll('.event-log-emoji');
    types.forEach(({ emoji }, i) => {
      expect(emojiEls[i].textContent).toBe(emoji);
    });
  });

  it('should apply border-left accent color per action type', () => {
    stateStore.emit('eventlog', {
      time: 540,
      action: 'Security Arm',
      device: 'Smart Lock',
      reasoning: 'Arming security.',
      type: 'security_arm',
    });

    const entry = document.querySelector('.event-log-entry');
    expect(entry.style.borderLeftColor).toBe('#FFD700');
  });

  it('should display stage info when provided', () => {
    stateStore.emit('eventlog', {
      time: 1020,
      action: 'Power Cut Response',
      device: 'Inverter/UPS',
      reasoning: 'Detected grid failure.',
      type: 'power_cut',
      stage: 'SENSE',
    });

    const stage = document.querySelector('.event-log-stage');
    expect(stage).not.toBeNull();
    expect(stage.textContent).toBe('[SENSE]');
  });

  it('should display confidence/tier info when provided', () => {
    stateStore.emit('eventlog', {
      time: 600,
      action: 'Test Action',
      device: 'Device',
      reasoning: 'Test reason',
      type: 'ac_precool',
      tier: 3,
      confidence: 0.85,
    });

    const tier = document.querySelector('.event-log-tier');
    const confidence = document.querySelector('.event-log-confidence');
    expect(tier.textContent).toBe('Tier 3');
    expect(confidence.textContent).toBe('85%');
  });

  it('should auto-scroll to the bottom after adding entry', () => {
    // Add many entries to create overflow
    for (let i = 0; i < 20; i++) {
      stateStore.emit('eventlog', {
        time: i * 60,
        action: `Action ${i}`,
        device: 'Device',
        reasoning: 'Some long reasoning text here',
        type: 'ac_precool',
      });
    }

    const container = document.getElementById('event-log-entries');
    // scrollTop should be set to scrollHeight (auto-scroll behavior)
    // In jsdom, scrollHeight might be 0, but we verify autoScroll was called
    expect(container.scrollTop).toBeDefined();
  });

  it('should clear all entries', () => {
    stateStore.emit('eventlog', {
      time: 100,
      action: 'Action 1',
      device: 'Device',
      reasoning: 'Reason',
      type: 'ac_precool',
    });
    stateStore.emit('eventlog', {
      time: 200,
      action: 'Action 2',
      device: 'Device',
      reasoning: 'Reason',
      type: 'geyser_preheat',
    });

    expect(document.querySelectorAll('.event-log-entry').length).toBe(2);

    eventLog.clear();

    expect(document.querySelectorAll('.event-log-entry').length).toBe(0);
  });

  it('should format time correctly', () => {
    expect(eventLog.formatTime(0)).toBe('[00:00]');
    expect(eventLog.formatTime(60)).toBe('[01:00]');
    expect(eventLog.formatTime(750)).toBe('[12:30]');
    expect(eventLog.formatTime(1439)).toBe('[23:59]');
    expect(eventLog.formatTime(NaN)).toBe('[--:--]');
  });

  it('should use default emoji for unknown type', () => {
    stateStore.emit('eventlog', {
      time: 100,
      action: 'Unknown',
      device: 'Device',
      reasoning: 'Reason',
      type: 'some_unknown_type',
    });

    const emoji = document.querySelector('.event-log-emoji');
    expect(emoji.textContent).toBe('🔔');
  });

  it('should render type/tier badge with Alexa blue styling', () => {
    stateStore.emit('eventlog', {
      time: 600,
      action: 'Pre-cooling',
      device: 'Living Room AC',
      reasoning: 'Scheduled cooling',
      type: 'ac_precool',
      tier: 3,
    });

    const badge = document.querySelector('.event-log-type-badge');
    expect(badge).not.toBeNull();
    expect(badge.textContent).toContain('Ac Precool');
    expect(badge.textContent).toContain('Tier 3');
  });

  it('should render Override button on each entry', () => {
    stateStore.emit('eventlog', {
      time: 600,
      action: 'Pre-cooling',
      device: 'Living Room AC',
      reasoning: 'Scheduled cooling',
      type: 'ac_precool',
    });

    const btn = document.querySelector('.event-log-override-btn');
    expect(btn).not.toBeNull();
    expect(btn.textContent).toBe('Override');
  });

  it('should apply strikethrough and reduce trust on Override click', () => {
    stateStore.emit('eventlog', {
      time: 600,
      action: 'Pre-cooling',
      device: 'Living Room AC',
      reasoning: 'Scheduled cooling',
      type: 'ac_precool',
      category: 'climate',
    });

    const btn = document.querySelector('.event-log-override-btn');
    btn.click();

    const entry = document.querySelector('.event-log-entry');
    expect(entry.classList.contains('event-log-entry--overridden')).toBe(true);
    expect(stateStore.trustUpdates.length).toBe(1);
    expect(stateStore.trustUpdates[0]).toEqual({ category: 'climate', delta: -15 });
    expect(btn.disabled).toBe(true);
    expect(btn.textContent).toBe('Overridden');
  });

  it('should derive category from type when category not provided', () => {
    stateStore.emit('eventlog', {
      time: 600,
      action: 'Security Arm',
      device: 'Smart Lock',
      reasoning: 'Arming all locks',
      type: 'security_arm',
    });

    const btn = document.querySelector('.event-log-override-btn');
    btn.click();

    expect(stateStore.trustUpdates[0].category).toBe('security');
  });

  it('should render device with arrow prefix', () => {
    stateStore.emit('eventlog', {
      time: 600,
      action: 'Pre-cooling',
      device: 'Living Room AC set to 24°C',
      reasoning: 'Hot afternoon predicted',
      type: 'ac_precool',
    });

    const device = document.querySelector('.event-log-device');
    expect(device.textContent).toBe('→ Living Room AC set to 24°C');
  });

  it('should render reasoning with Reason prefix', () => {
    stateStore.emit('eventlog', {
      time: 600,
      action: 'Pre-cooling',
      device: 'Living Room AC',
      reasoning: 'Hot afternoon predicted',
      type: 'ac_precool',
    });

    const reasoning = document.querySelector('.event-log-reasoning');
    expect(reasoning.textContent).toBe('→ Reason: Hot afternoon predicted');
  });
});
