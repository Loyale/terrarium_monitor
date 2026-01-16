/**
 * Formatting and unit conversion helpers for the UI.
 */

const DEGREE_SYMBOL = "\u00b0";
const UNIT_STORAGE_KEY = "terrarium-unit-preference";

const METRIC_LABELS = {
  temperature: "Temperature",
  humidity: "Humidity",
  pressure: "Pressure",
  uv_index: "UV Index",
  ambient_light: "Ambient Light",
  illuminance: "Illuminance",
  light: "Light",
};

const UNIT_LABELS = {
  c: `${DEGREE_SYMBOL}C`,
  f: `${DEGREE_SYMBOL}F`,
  pct: "%",
  hpa: "hPa",
  lux: "lux",
  als: "ALS",
  uv_index: "UV",
};

/**
 * Load the persisted temperature unit preference.
 */
export function loadUnitPreference() {
  return localStorage.getItem(UNIT_STORAGE_KEY) || "f";
}

/**
 * Persist the temperature unit preference.
 */
export function saveUnitPreference(value) {
  localStorage.setItem(UNIT_STORAGE_KEY, value);
}

/**
 * Convert a temperature value to the requested unit.
 */
export function normalizeTemperature(value, unit, preference) {
  if (unit === preference) {
    return { value, unit };
  }
  if (unit === "c" && preference === "f") {
    return { value: value * 1.8 + 32, unit: "f" };
  }
  if (unit === "f" && preference === "c") {
    return { value: (value - 32) / 1.8, unit: "c" };
  }
  return { value, unit };
}

/**
 * Format a metric name into a human readable label.
 */
export function formatMetricLabel(metric) {
  return METRIC_LABELS[metric] || metric.replace(/_/g, " ");
}

/**
 * Format a measurement value with unit-aware display.
 */
export function formatMeasurementValue(metric, value, unit, preference) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  if (metric === "temperature") {
    const normalized = normalizeTemperature(value, unit, preference);
    return `${normalized.value.toFixed(1)} ${UNIT_LABELS[normalized.unit] || normalized.unit}`;
  }
  if (unit === "pct") {
    return `${value.toFixed(0)} ${UNIT_LABELS.pct}`;
  }
  if (unit === "hpa") {
    return `${value.toFixed(0)} ${UNIT_LABELS.hpa}`;
  }
  if (metric === "uv_index") {
    return value.toFixed(2);
  }
  if (unit === "lux") {
    return `${value.toFixed(0)} ${UNIT_LABELS.lux}`;
  }
  if (unit === "als") {
    return `${value.toFixed(0)} ${UNIT_LABELS.als}`;
  }
  return `${value.toFixed(2)} ${UNIT_LABELS[unit] || unit}`;
}

/**
 * Format a timestamp into a local date/time string.
 */
export function formatTimestamp(value) {
  if (!value) {
    return "--";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "--";
  }
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
    day: "2-digit",
  }).format(parsed);
}

/**
 * Format timestamps for compact chart ticks.
 */
export function formatChartTime(value) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}
