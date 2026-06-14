/**
 * @vitest-environment happy-dom
 */
import { beforeEach, describe, expect, it } from 'vitest';
import { FloorPlan2D } from './FloorPlan2D.js';

function setupDOM() {
  document.head.innerHTML = '';
  document.body.innerHTML = '<div id="floor-root" style="width: 900px; height: 620px;"></div>';
  return document.getElementById('floor-root');
}

describe('FloorPlan2D', () => {
  let container;

  beforeEach(() => {
    container = setupDOM();
  });

  it('renders rooms and clickable device components', () => {
    new FloorPlan2D(container);

    expect(container.querySelector('.floor-plan-wrapper')).not.toBeNull();
    expect(container.querySelector('.fp-roof')).not.toBeNull();
    expect(container.querySelector('.fp-house-shell')).not.toBeNull();
    expect(container.querySelectorAll('.fp-room')).toHaveLength(7);

    const bath = container.querySelector('[data-room-id="bath"]');
    const livingRoom = container.querySelector('[data-room-id="living_room"]');
    expect(bath.style.left).toBe('42%');
    expect(bath.style.top).toBe('42%');
    expect(bath.style.height).toBe('58%');
    expect(livingRoom.style.left).toBe('0%');
    expect(livingRoom.style.width).toBe('42%');
    expect(livingRoom.querySelector('.fp-prop-sofa')).not.toBeNull();

    const devices = container.querySelectorAll('.fp-device');
    expect(devices.length).toBeGreaterThan(10);
    expect(devices[0].tagName).toBe('BUTTON');
  });

  it('opens component details and toggles local device state on device click', () => {
    new FloorPlan2D(container);

    const ac = container.querySelector('[data-device-id="living_room_ac"]');
    ac.click();

    expect(ac.classList.contains('selected')).toBe(true);
    expect(container.querySelector('.fp-component-info').textContent).toContain('AC');
    expect(container.querySelector('.fp-component-info').textContent).toContain('Off');

    container.querySelector('[data-action="toggle"]').click();

    expect(ac.dataset.state).toBe('on');
    expect(container.querySelector('.fp-component-info').textContent).toContain('Cooling');
  });

  it('opens room details with clickable components inside the room', () => {
    new FloorPlan2D(container);

    container.querySelector('[data-room-id="living_room"]').click();

    const roomInfo = container.querySelector('.fp-room-info');
    expect(roomInfo.textContent).toContain('Living Room');
    expect(roomInfo.querySelectorAll('.fp-component-row').length).toBeGreaterThan(0);

    roomInfo.querySelector('[data-device-id="smart_tv"]').click();

    expect(container.querySelector('.fp-room-info')).toBeNull();
    expect(container.querySelector('.fp-component-info').textContent).toContain('TV');
  });
});
