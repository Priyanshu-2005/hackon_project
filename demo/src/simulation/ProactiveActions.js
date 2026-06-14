/**
 * ProactiveActions — defines all proactive action triggers for the
 * Alexa Thinks Ahead 3D demo simulation.
 *
 * Each action specifies a trigger time (minutes since midnight), the target
 * device, category, room, reasoning text, and tailored announcements for
 * different family member roles (elder, parent, child).
 *
 * Requirements: 8.1, 8.3, 9.2
 */

export const PROACTIVE_ACTIONS = [
  {
    name: 'Geyser Pre-heat',
    actionType: 'geyser_preheat',
    triggerTime: 375, // 06:15 — 45 min before 07:00 alarm
    targetDevice: 'smart_geyser',
    category: 'utility',
    room: 'bath',
    reasoning:
      'Family wakes at 07:00. Pre-heating water 45 minutes ahead ensures hot water is ready.',
    announcement: {
      elder: 'Good morning! Hot water is ready for you.',
      parent: 'Geyser warmed up for the morning rush.',
      child: "Hot water's ready!",
    },
  },
  {
    name: 'Pre-cooling Living Room',
    actionType: 'ac_precool',
    triggerTime: 1050, // 17:30 — Rajesh returns ~18:00
    targetDevice: 'living_room_ac',
    category: 'climate',
    room: 'livingRoom',
    reasoning:
      'Rajesh typically returns at 18:00. Pre-cooling ensures comfortable temperature on arrival.',
    announcement: {
      parent: 'Cooling the living room before you get home.',
    },
  },
  {
    name: 'Security Arm',
    actionType: 'security_arm',
    triggerTime: 540, // 09:00 — After parents leave for work
    targetDevice: 'smart_lock',
    category: 'security',
    room: 'balcony',
    reasoning:
      'All adults have departed. Arming security camera and lock for daytime protection.',
    announcement: {
      elder: 'Security has been armed. You are safe inside.',
    },
  },
  {
    name: 'Energy Optimization',
    actionType: 'energy_optimization',
    triggerTime: 840, // 14:00 — Peak tariff period
    targetDevice: 'inverter_ups',
    category: 'power',
    room: 'utility',
    reasoning:
      'Peak electricity tariff begins. Shifting non-essential loads to inverter backup.',
    announcement: {
      parent: 'Switched to inverter for non-essentials to save on peak tariff.',
    },
  },
  {
    name: 'Comfort Lighting',
    actionType: 'comfort_lighting',
    triggerTime: 1065, // 17:45 — Sunset minus 15 min
    targetDevice: 'smart_lights',
    category: 'lighting',
    room: 'livingRoom',
    reasoning:
      'Sunset approaching. Transitioning to warm indoor lighting for comfort.',
    announcement: {
      elder: 'Turning on warm lights for the evening.',
    },
  },
];
