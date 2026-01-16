/**
 * API helpers for fetching backend data.
 */

const DEFAULT_HEADERS = {
  Accept: "application/json",
};

/**
 * Fetch the latest summary payload from the backend.
 */
export async function fetchSummary(signal) {
  const response = await fetch("/api/summary", { headers: DEFAULT_HEADERS, signal });
  if (!response.ok) {
    throw new Error(`Summary request failed: ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch measurements for a sensor/metric pair over a time range.
 */
export async function fetchMeasurements(params, signal) {
  const url = new URL("/api/measurements", window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });
  const response = await fetch(url.toString(), { headers: DEFAULT_HEADERS, signal });
  if (!response.ok) {
    throw new Error(`Measurements request failed: ${response.status}`);
  }
  return response.json();
}
