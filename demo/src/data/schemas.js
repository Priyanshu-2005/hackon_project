/**
 * @file JSDoc type definitions for the Data Layer API responses.
 * These types mirror the backend REST API structure and are shared
 * between MockProvider and ApiProvider.
 */

/**
 * @typedef {Object} DeviceState
 * @property {string} [power] - Power state ('on' | 'off')
 * @property {number} [temperature] - Current temperature value
 * @property {string} [mode] - Operating mode (e.g. 'cool', 'standby')
 * @property {number} [brightness] - Brightness level (0-100)
 * @property {number} [colorTemp] - Color temperature in Kelvin
 * @property {boolean} [recording] - Whether device is recording
 * @property {boolean} [motionDetected] - Whether motion is detected
 * @property {boolean} [locked] - Lock state
 * @property {number} [battery] - Battery percentage (0-100)
 * @property {string|null} [activeAppliance] - Currently active appliance
 * @property {number} [filterLife] - Filter life percentage
 * @property {string} [waterLevel] - Water level ('full' | 'low' | 'empty')
 * @property {number} [targetTemp] - Target temperature
 * @property {number} [charge] - Charge percentage (0-100)
 * @property {number} [load] - Current load percentage
 * @property {string} [input] - Active input source
 * @property {boolean} [online] - Online status
 * @property {number} [volume] - Volume level (0-10)
 */

/**
 * @typedef {Object} Device
 * @property {string} id - Unique device identifier
 * @property {string} name - Human-readable device name
 * @property {string} category - Device category (climate, lighting, security, kitchen, utility, power, entertainment, assistant)
 * @property {string} room - Room assignment (livingRoom, kitchen, balcony, bath, utility, all)
 * @property {string} brand - Device manufacturer
 * @property {DeviceState} state - Current device state
 */

/**
 * @typedef {Object} DevicesResponse
 * @property {Device[]} devices - Array of all devices
 * @property {number} count - Total number of devices
 */

/**
 * @typedef {Object} CommandResponse
 * @property {boolean} success - Whether the command was accepted
 * @property {string} deviceId - Target device ID
 * @property {Object} command - The command that was sent
 * @property {string} timestamp - ISO 8601 timestamp of execution
 */

/**
 * @typedef {Object} Environmentals
 * @property {number} temperature - Ambient temperature in Celsius
 * @property {number} humidity - Relative humidity percentage
 * @property {string} powerGrid - Grid status ('stable' | 'unstable' | 'down')
 */

/**
 * @typedef {Object} ContextSnapshot
 * @property {string} timestamp - ISO 8601 snapshot timestamp
 * @property {Array<{id: string, state: DeviceState}>} deviceStates - Current state of all devices
 * @property {Array<Object>} activeActivities - Currently active household activities
 * @property {Environmentals} environmentals - Environmental conditions
 */

/**
 * @typedef {Object} Pattern
 * @property {string} id - Pattern identifier
 * @property {number} confidence - Confidence score (0.0 to 1.0)
 * @property {string} schedule - Trigger time in HH:MM format
 * @property {string[]} actions - List of action identifiers triggered by this pattern
 */

/**
 * @typedef {Object} PatternsResponse
 * @property {Pattern[]} patterns - Array of detected temporal patterns
 */

/**
 * @typedef {Object} TierEntry
 * @property {string} category - Device category name
 * @property {number} currentTier - Current autonomy tier (1-5)
 * @property {number} trustScore - Trust score (0-100)
 */

/**
 * @typedef {Object} TiersResponse
 * @property {TierEntry[]} tiers - Array of tier configurations per category
 */

/**
 * @typedef {Object} TierUpdateResponse
 * @property {boolean} success - Whether the update was applied
 * @property {string} device - Device category that was updated
 */

export default {};
