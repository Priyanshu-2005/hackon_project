/**
 * Family schedule mapping room names to RoomDefinitions IDs.
 * Times are in minutes from midnight (0 = 00:00, 1440 = 24:00).
 *
 * Extracted as a standalone data module so it can be imported without
 * pulling in Three.js dependencies.
 */
export const FAMILY_SCHEDULE = {
  rajesh: [
    { start: 0, end: 390, room: 'master_bedroom', activity: 'sleeping' },
    { start: 390, end: 480, room: 'bath', activity: 'morning routine' },
    { start: 480, end: 540, room: 'kitchen', activity: 'breakfast' },
    { start: 540, end: 1110, room: null, activity: 'at work' },
    { start: 1110, end: 1380, room: 'living_room', activity: 'relaxing' },
    { start: 1380, end: 1440, room: 'master_bedroom', activity: 'sleeping' },
  ],
  priya: [
    { start: 0, end: 360, room: 'master_bedroom', activity: 'sleeping' },
    { start: 360, end: 420, room: 'kitchen', activity: 'cooking' },
    { start: 420, end: 720, room: 'kitchen', activity: 'household' },
    { start: 720, end: 1350, room: 'living_room', activity: 'family time' },
    { start: 1350, end: 1440, room: 'master_bedroom', activity: 'sleeping' },
  ],
  arjun: [
    { start: 0, end: 420, room: 'kids_room', activity: 'sleeping' },
    { start: 420, end: 480, room: 'kitchen', activity: 'breakfast' },
    { start: 480, end: 900, room: null, activity: 'at school' },
    { start: 900, end: 960, room: 'kitchen', activity: 'snack' },
    { start: 960, end: 1140, room: 'study_room', activity: 'tuition/study' },
    { start: 1140, end: 1320, room: 'kids_room', activity: 'relaxing' },
    { start: 1320, end: 1440, room: 'kids_room', activity: 'sleeping' },
  ],
  ananya: [
    { start: 0, end: 450, room: 'kids_room', activity: 'sleeping' },
    { start: 450, end: 480, room: 'kitchen', activity: 'breakfast' },
    { start: 480, end: 900, room: null, activity: 'at school' },
    { start: 900, end: 1020, room: 'living_room', activity: 'TV time' },
    { start: 1020, end: 1260, room: 'kids_room', activity: 'relaxing' },
    { start: 1260, end: 1440, room: 'kids_room', activity: 'sleeping' },
  ],
  dadaji: [
    { start: 0, end: 360, room: 'master_bedroom', activity: 'sleeping' },
    { start: 360, end: 420, room: 'balcony', activity: 'morning walk' },
    { start: 420, end: 780, room: 'living_room', activity: 'reading/TV' },
    { start: 780, end: 900, room: 'living_room', activity: 'afternoon rest' },
    { start: 900, end: 1290, room: 'living_room', activity: 'relaxing' },
    { start: 1290, end: 1440, room: 'master_bedroom', activity: 'sleeping' },
  ],
  dadiji: [
    { start: 0, end: 330, room: 'master_bedroom', activity: 'sleeping' },
    { start: 330, end: 360, room: 'balcony', activity: 'prayer' },
    { start: 360, end: 480, room: 'kitchen', activity: 'tea/prayers' },
    { start: 480, end: 720, room: 'living_room', activity: 'watching TV' },
    { start: 720, end: 900, room: 'master_bedroom', activity: 'rest' },
    { start: 900, end: 1260, room: 'living_room', activity: 'family time' },
    { start: 1260, end: 1440, room: 'master_bedroom', activity: 'sleeping' },
  ],
};
