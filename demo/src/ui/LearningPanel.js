import { eventBus, EVENTS } from '../utils/eventBus.js';

/**
 * Family members available in the event form.
 */
const FAMILY_MEMBERS = ['Rajesh', 'Priya', 'Arjun', 'Ananya', 'Dadaji', 'Dadiji'];

/**
 * Event type options for the form.
 */
const EVENT_TYPES = [
  'Wake up',
  'Leave home',
  'Arrive home',
  'Start cooking',
  'Online class',
  'Afternoon rest',
  'TV time',
  'Bedtime',
  'Custom',
];

/**
 * Room options for the form.
 */
const ROOMS = [
  'Living Room',
  'Kitchen',
  'Master Bedroom',
  'Kids Room',
  'Study Room',
  'Bathroom',
  'Balcony',
];

/**
 * Device options for the multi-select checkboxes.
 */
const DEVICES = ['AC', 'Lights', 'Geyser', 'TV', 'Lock', 'Camera', 'Purifier', 'Kitchen Hub', 'Echo'];

/**
 * Default events representing typical Sharma family routines.
 * Pre-populated in the Learning Phase for immediate demonstration.
 *
 * Requirements: 4.4
 */
const DEFAULT_EVENTS = [
  // Rajesh
  { id: 'default-1', member: 'Rajesh', type: 'Wake up', time: '06:30', room: 'Master Bedroom', devices: ['Lights', 'Geyser'] },
  { id: 'default-2', member: 'Rajesh', type: 'Leave home', time: '08:00', room: 'Balcony', devices: ['Lock', 'Camera'] },
  { id: 'default-3', member: 'Rajesh', type: 'Arrive home', time: '18:30', room: 'Balcony', devices: ['Lock', 'AC', 'Lights'] },
  { id: 'default-4', member: 'Rajesh', type: 'Bedtime', time: '23:00', room: 'Master Bedroom', devices: ['AC', 'Lights'] },

  // Priya
  { id: 'default-5', member: 'Priya', type: 'Wake up', time: '06:00', room: 'Master Bedroom', devices: ['Lights', 'Geyser'] },
  { id: 'default-6', member: 'Priya', type: 'Start cooking', time: '07:00', room: 'Kitchen', devices: ['Kitchen Hub', 'Lights'] },
  { id: 'default-7', member: 'Priya', type: 'Start cooking', time: '12:00', room: 'Kitchen', devices: ['Kitchen Hub', 'Lights'] },
  { id: 'default-8', member: 'Priya', type: 'Bedtime', time: '22:30', room: 'Master Bedroom', devices: ['AC', 'Lights'] },

  // Arjun
  { id: 'default-9', member: 'Arjun', type: 'Wake up', time: '07:00', room: 'Kids Room', devices: ['Lights'] },
  { id: 'default-10', member: 'Arjun', type: 'Online class', time: '16:00', room: 'Study Room', devices: ['Lights', 'AC', 'Echo'] },
  { id: 'default-11', member: 'Arjun', type: 'Bedtime', time: '22:00', room: 'Kids Room', devices: ['Lights', 'AC'] },

  // Ananya
  { id: 'default-12', member: 'Ananya', type: 'Wake up', time: '07:30', room: 'Kids Room', devices: ['Lights'] },
  { id: 'default-13', member: 'Ananya', type: 'TV time', time: '15:00', room: 'Living Room', devices: ['TV', 'Lights'] },
  { id: 'default-14', member: 'Ananya', type: 'Bedtime', time: '21:00', room: 'Kids Room', devices: ['Lights', 'AC'] },

  // Dadaji
  { id: 'default-15', member: 'Dadaji', type: 'Wake up', time: '06:00', room: 'Master Bedroom', devices: ['Lights'] },
  { id: 'default-16', member: 'Dadaji', type: 'Afternoon rest', time: '13:00', room: 'Living Room', devices: ['AC', 'Lights'] },
  { id: 'default-17', member: 'Dadaji', type: 'Bedtime', time: '21:30', room: 'Master Bedroom', devices: ['AC', 'Lights'] },

  // Dadiji
  { id: 'default-18', member: 'Dadiji', type: 'Wake up', time: '05:30', room: 'Master Bedroom', devices: ['Lights'] },
  { id: 'default-19', member: 'Dadiji', type: 'Custom', time: '06:00', room: 'Balcony', devices: ['Lights'] },
  { id: 'default-20', member: 'Dadiji', type: 'Bedtime', time: '21:00', room: 'Master Bedroom', devices: ['Lights', 'AC'] },
];

/**
 * LearningPanel manages the event configuration form in the Learning Phase.
 * Users can add, view, and remove household events before deploying the simulation.
 *
 * Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
 */
export class LearningPanel {
  /**
   * @param {import('./UIManager.js').UIManager} uiManager — receives the UIManager to call deploy()
   */
  constructor(uiManager) {
    this.uiManager = uiManager;
    /** @type {Array<{id: string, member: string, type: string, time: string, room: string, devices: string[]}>} */
    this.events = [...DEFAULT_EVENTS];
    this.render();
    this.bindEvents();
  }

  /**
   * Add a new event to the list, render it, and emit EVENT_ADDED.
   * @param {{member: string, type: string, time: string, room: string, devices: string[]}} eventData
   */
  addEvent(eventData) {
    const event = {
      id: 'evt-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8),
      ...eventData,
    };
    this.events.push(event);
    this.renderEventList();
    this.updateCounter();
    eventBus.emit(EVENTS.EVENT_ADDED, event);
  }

  /**
   * Remove an event by its id, re-render the list, and emit EVENT_REMOVED.
   * @param {string} id
   */
  removeEvent(id) {
    const removed = this.events.find(e => e.id === id);
    this.events = this.events.filter(e => e.id !== id);
    this.renderEventList();
    this.updateCounter();
    if (removed) {
      eventBus.emit(EVENTS.EVENT_REMOVED, removed);
    }
  }

  /**
   * Render the full form HTML inside the learning panel (#event-form div).
   */
  render() {
    const formEl = document.getElementById('event-form');
    if (!formEl) return;

    const uniqueMembers = new Set(this.events.map(e => e.member)).size;

    formEl.innerHTML = `
      <div class="learning-panel-header">
        <h3>📋 Configure Household Events</h3>
        <p id="routine-counter" class="routine-counter">Alexa has learned ${this.events.length} routines for ${uniqueMembers} family members</p>
      </div>
      <form id="add-event-form" class="event-form">
        <div class="form-row">
          <select name="member" required aria-label="Family member">
            <option value="">Family Member...</option>
            ${FAMILY_MEMBERS.map(m => `<option value="${m}">${m}</option>`).join('')}
          </select>
          <select name="eventType" required aria-label="Event type">
            <option value="">Event Type...</option>
            ${EVENT_TYPES.map(t => `<option value="${t}">${t}</option>`).join('')}
          </select>
        </div>
        <div class="form-row">
          <input type="time" name="time" required aria-label="Event time" />
          <select name="room" required aria-label="Room">
            <option value="">Room...</option>
            ${ROOMS.map(r => `<option value="${r}">${r}</option>`).join('')}
          </select>
        </div>
        <div class="form-row devices-row">
          <label class="devices-label">Devices:</label>
          <div class="devices-checkboxes">
            ${DEVICES.map(d => `
              <label class="device-checkbox">
                <input type="checkbox" name="devices" value="${d}" />
                <span>${d}</span>
              </label>
            `).join('')}
          </div>
        </div>
        <button type="submit" class="btn-accent">+ Add Event</button>
      </form>
    `;

    this.renderEventList();
  }

  /**
   * Render the #event-list div with all events grouped by family member,
   * each with a remove button.
   */
  renderEventList() {
    const listEl = document.getElementById('event-list');
    if (!listEl) return;

    if (this.events.length === 0) {
      listEl.innerHTML = '<p class="event-list-empty">No events configured. Add some above.</p>';
      return;
    }

    // Group events by family member
    const grouped = {};
    for (const evt of this.events) {
      if (!grouped[evt.member]) grouped[evt.member] = [];
      grouped[evt.member].push(evt);
    }

    let html = '';
    for (const member of FAMILY_MEMBERS) {
      if (!grouped[member] || grouped[member].length === 0) continue;
      html += `<div class="event-group">
        <h4 class="event-group-title">${member}</h4>`;
      for (const evt of grouped[member]) {
        html += `<div class="event-item" data-id="${evt.id}">
          <div class="event-item-info">
            <span class="event-time">${evt.time}</span>
            <span class="event-type">${evt.type}</span>
            <span class="event-room">${evt.room}</span>
            <span class="event-devices">${evt.devices.join(', ')}</span>
          </div>
          <button class="event-remove-btn" data-id="${evt.id}" title="Remove event" aria-label="Remove event">✕</button>
        </div>`;
      }
      html += '</div>';
    }

    listEl.innerHTML = html;
  }

  /**
   * Update the counter display: "Alexa has learned X routines for Y family members"
   */
  updateCounter() {
    const counterEl = document.getElementById('routine-counter');
    if (!counterEl) return;
    const uniqueMembers = new Set(this.events.map(e => e.member)).size;
    counterEl.textContent = `Alexa has learned ${this.events.length} routines for ${uniqueMembers} family members`;
  }

  /**
   * Bind form submit and deploy button events.
   */
  bindEvents() {
    // Form submission — delegated on #event-form container
    const formEl = document.getElementById('event-form');
    if (formEl) {
      formEl.addEventListener('submit', (e) => {
        e.preventDefault();
        const form = document.getElementById('add-event-form');
        if (!form) return;

        const formData = new FormData(form);
        const member = formData.get('member');
        const type = formData.get('eventType');
        const time = formData.get('time');
        const room = formData.get('room');

        // Collect checked devices
        const devices = [];
        form.querySelectorAll('input[name="devices"]:checked').forEach(cb => {
          devices.push(cb.value);
        });

        if (!member || !type || !time || !room) return;

        this.addEvent({ member, type, time, room, devices });
        form.reset();
      });
    }

    // Remove event — delegated click handler on event list
    const listEl = document.getElementById('event-list');
    if (listEl) {
      listEl.addEventListener('click', (e) => {
        const removeBtn = e.target.closest('.event-remove-btn');
        if (removeBtn) {
          e.preventDefault();
          this.removeEvent(removeBtn.dataset.id);
        }
      });
    }

    // Deploy button — calls uiManager.deploy() and emits phase change
    const deployBtn = document.getElementById('deploy-btn');
    if (deployBtn) {
      deployBtn.addEventListener('click', () => {
        if (this.uiManager) {
          this.uiManager.deploy();
        }
        eventBus.emit(EVENTS.PHASE_CHANGE, { phase: 'deployment', events: this.events });
      });
    }
  }

  /**
   * Returns the current list of configured events.
   * @returns {Array}
   */
  getEvents() {
    return [...this.events];
  }
}
