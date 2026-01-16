/**
 * Main UI for the terrarium monitor dashboard.
 */

import { useEffect, useMemo, useState } from "react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  ReferenceArea,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { fetchMeasurements, fetchSummary } from "./api";
import {
  formatChartTime,
  formatMeasurementValue,
  formatMetricLabel,
  formatTimestamp,
  loadUnitPreference,
  normalizeTemperature,
  saveUnitPreference,
} from "./utils";
import "./styles.css";

const REFRESH_INTERVAL_MS = 30000;
const CHART_WINDOW_HOURS = 12;
const METRIC_STYLES = {
  temperature: { line: "#E07A5F", soft: "#F8D9CF" },
  humidity: { line: "#3E7CB1", soft: "#D6E7F5" },
  pressure: { line: "#6D6A8E", soft: "#E4E3F1" },
  uv_index: { line: "#D08C28", soft: "#F6E2C6" },
  ambient_light: { line: "#2C7F9B", soft: "#D3E8F0" },
  illuminance: { line: "#7A9A2F", soft: "#E3ECCD" },
};

/**
 * Build a list of cards from the summary payload.
 */
function buildCardItems(summary, unitPreference) {
  const cards = [];
  summary.forEach((sensor) => {
    sensor.metrics.forEach((metric) => {
      cards.push({
        id: `${sensor.key}-${metric.metric}`,
        title: formatMetricLabel(metric.metric),
        value: formatMeasurementValue(
          metric.metric,
          metric.value,
          metric.unit,
          unitPreference,
        ),
        sensor: sensor.name,
        location: sensor.location || "",
        timestamp: formatTimestamp(metric.recorded_at),
      });
    });
  });
  return cards;
}

/**
 * Build a start/end window for chart queries.
 */
function buildRange(hours) {
  const end = new Date();
  const start = new Date(end.getTime() - hours * 60 * 60 * 1000);
  return { start: start.toISOString(), end: end.toISOString() };
}

/**
 * Build a list of chart series definitions from the summary payload.
 */
function buildChartSeries(summary) {
  const series = [];
  summary.forEach((sensor) => {
    sensor.metrics.forEach((metric) => {
      series.push({
        sensorKey: sensor.key,
        sensorName: sensor.name,
        location: sensor.location || "",
        model: sensor.model,
        metric: metric.metric,
        unit: metric.unit,
      });
    });
  });
  return series;
}

/**
 * Prepare chart data with unit conversion for the selected metric.
 */
function prepareChartData(measurements, metric, unitPreference) {
  return measurements.map((measurement) => {
    if (metric === "temperature") {
      const normalized = normalizeTemperature(
        measurement.value,
        measurement.unit,
        unitPreference,
      );
      return {
        ...measurement,
        value: normalized.value,
        unit: normalized.unit,
      };
    }
    return measurement;
  });
}

/**
 * Build a unique key for a sensor/metric series.
 */
function buildSeriesKey(sensorKey, metric) {
  return `${sensorKey}-${metric}`;
}

/**
 * Format a unit label for chart headers.
 */
function formatChartUnit(metric, unit, unitPreference) {
  if (metric === "temperature") {
    return unitPreference === "f" ? "°F" : "°C";
  }
  if (unit === "pct") {
    return "%";
  }
  if (unit === "hpa") {
    return "hPa";
  }
  if (unit === "lux") {
    return "lux";
  }
  if (unit === "als") {
    return "ALS";
  }
  if (unit === "uv_index") {
    return "UV";
  }
  return unit || "";
}

/**
 * Return the style tuple for a metric chart.
 */
function getMetricStyle(metric) {
  return METRIC_STYLES[metric] || { line: "#1b7f6b", soft: "#D8EEE8" };
}

/**
 * Compute a min/max range for the series.
 */
function computeRange(values) {
  const numeric = values.filter((value) => typeof value === "number");
  if (!numeric.length) {
    return null;
  }
  return {
    min: Math.min(...numeric),
    max: Math.max(...numeric),
  };
}

/**
 * Dashboard application component.
 */
export default function App() {
  const [summary, setSummary] = useState([]);
  const [summaryMeta, setSummaryMeta] = useState({ generatedAt: null });
  const [seriesData, setSeriesData] = useState({});
  const [unitPreference, setUnitPreference] = useState(loadUnitPreference());
  const [status, setStatus] = useState({ loading: true, error: null });

  const cardItems = useMemo(
    () => buildCardItems(summary, unitPreference),
    [summary, unitPreference],
  );
  const chartSeries = useMemo(() => buildChartSeries(summary), [summary]);

  useEffect(() => {
    let cancelled = false;

    /**
     * Fetch summary data on an interval.
     */
    const loadSummary = async () => {
      try {
        const data = await fetchSummary();
        if (cancelled) {
          return;
        }
        setSummary(data.sensors || []);
        setSummaryMeta({ generatedAt: data.generated_at });
        setStatus({ loading: false, error: null });
      } catch (error) {
        if (cancelled) {
          return;
        }
        setStatus({ loading: false, error: error.message });
      }
    };

    loadSummary();
    const interval = setInterval(loadSummary, REFRESH_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (!chartSeries.length) {
      return;
    }
    let cancelled = false;

    /**
     * Fetch chart data for every sensor/metric series.
     */
    const loadMeasurements = async () => {
      try {
        const range = buildRange(CHART_WINDOW_HOURS);
        const responses = await Promise.all(
          chartSeries.map((series) =>
            fetchMeasurements({
              sensor_key: series.sensorKey,
              metric: series.metric,
              start: range.start,
              end: range.end,
              limit: 2000,
            }),
          ),
        );
        if (cancelled) {
          return;
        }
        const nextData = {};
        responses.forEach((data, index) => {
          const series = chartSeries[index];
          nextData[buildSeriesKey(series.sensorKey, series.metric)] =
            data.measurements || [];
        });
        setSeriesData(nextData);
      } catch (error) {
        if (cancelled) {
          return;
        }
        setStatus((prev) => ({ ...prev, error: error.message }));
      }
    };

    loadMeasurements();
    return () => {
      cancelled = true;
    };
  }, [chartSeries]);

  /**
   * Update the unit preference and persist it locally.
   */
  const handleUnitToggle = (value) => {
    setUnitPreference(value);
    saveUnitPreference(value);
  };

  return (
    <div className="app">
      <header className="hero">
        <div>
          <p className="eyebrow">Terrarium Monitor</p>
          <h1>Habitat Climate Overview</h1>
          <p className="subhead">
            Live readings with a {CHART_WINDOW_HOURS}-hour sensor history.
          </p>
        </div>
        <div className="controls">
          <div className="unit-toggle" role="group" aria-label="Temperature unit">
            <button
              type="button"
              className={unitPreference === "f" ? "active" : ""}
              onClick={() => handleUnitToggle("f")}
            >
              F
            </button>
            <button
              type="button"
              className={unitPreference === "c" ? "active" : ""}
              onClick={() => handleUnitToggle("c")}
            >
              C
            </button>
          </div>
          <div className="status">
            <span>Last update</span>
            <strong>{formatTimestamp(summaryMeta.generatedAt)}</strong>
          </div>
        </div>
      </header>

      <section className="cards">
        {cardItems.length ? (
          cardItems.map((card, index) => (
            <article
              key={card.id}
              className="card"
              style={{ "--delay": `${index * 70}ms` }}
            >
              <div className="card-label">{card.title}</div>
              <div className="card-value">{card.value}</div>
              <div className="card-meta">
                {card.sensor}
                {card.location ? ` - ${card.location}` : ""}
              </div>
              <div className="card-time">{card.timestamp}</div>
            </article>
          ))
        ) : (
          <div className="empty">No readings yet. Waiting for sensor data.</div>
        )}
      </section>

      <section className="charts">
        <header className="charts-header">
          <p className="eyebrow">Sensor Trends</p>
          <h2>Every reading, every sensor</h2>
          <p className="charts-subhead">
            Showing the last {CHART_WINDOW_HOURS} hours for each metric.
          </p>
        </header>
        {status.error ? <div className="empty">{status.error}</div> : null}
        {summary.length ? (
          summary.map((sensor) => (
            <div className="sensor-panel" key={sensor.key}>
              <header className="sensor-header">
                <div>
                  <h3>{sensor.name}</h3>
                  <p className="sensor-meta">
                    {sensor.location || "Terrarium"} {sensor.model ? `· ${sensor.model}` : ""}
                  </p>
                </div>
                <span className="sensor-pill">{sensor.key}</span>
              </header>
              <div className="sensor-charts">
                {sensor.metrics.map((metric) => {
                  const seriesKey = buildSeriesKey(sensor.key, metric.metric);
                  const rawData = seriesData[seriesKey] || [];
                  const chartData = prepareChartData(
                    rawData,
                    metric.metric,
                    unitPreference,
                  );
                  const metricStyle = getMetricStyle(metric.metric);
                  const range = computeRange(chartData.map((item) => item.value));
                  const unitLabel = formatChartUnit(
                    metric.metric,
                    metric.unit,
                    unitPreference,
                  );
                  const formattedValue = formatMeasurementValue(
                    metric.metric,
                    metric.value,
                    metric.unit,
                    unitPreference,
                  );
                  const recordedLabel = metric.recorded_at
                    ? `Updated ${formatTimestamp(metric.recorded_at)}`
                    : "Waiting for data";

                  return (
                    <article
                      className="metric-chart"
                      key={seriesKey}
                      style={{
                        "--metric-line": metricStyle.line,
                        "--metric-soft": metricStyle.soft,
                      }}
                    >
                      <header className="metric-header">
                        <div>
                          <p className="eyebrow">{formatMetricLabel(metric.metric)}</p>
                          <h4>{unitLabel}</h4>
                        </div>
                        <div className="metric-reading">
                          <span className="metric-value">{formattedValue}</span>
                          <span className="metric-time">{recordedLabel}</span>
                        </div>
                        <span className="metric-pill">{metric.metric}</span>
                      </header>
                      <div className="chart-body">
                        {chartData.length ? (
                          <ResponsiveContainer width="100%" height={220}>
                            <LineChart
                              data={chartData}
                              margin={{ top: 10, right: 24, left: 0, bottom: 0 }}
                            >
                              <XAxis dataKey="recorded_at" tickFormatter={formatChartTime} />
                              <YAxis
                                tickFormatter={(value) =>
                                  metric.metric === "temperature" && typeof value === "number"
                                    ? value.toFixed(0)
                                    : value
                                }
                              />
                              {range ? (
                                <ReferenceArea
                                  y1={range.min}
                                  y2={range.max}
                                  fill={metricStyle.soft}
                                  fillOpacity={0.35}
                                  strokeOpacity={0}
                                />
                              ) : null}
                              <Tooltip
                                labelFormatter={formatTimestamp}
                                formatter={(value, name, props) => {
                                  const data = props.payload || {};
                                  return [
                                    formatMeasurementValue(
                                      metric.metric,
                                      data.value,
                                      data.unit,
                                      unitPreference,
                                    ),
                                    formatMetricLabel(metric.metric),
                                  ];
                                }}
                              />
                              <Line
                                type="monotone"
                                dataKey="value"
                                stroke={metricStyle.line}
                                strokeWidth={2.6}
                                dot={false}
                              />
                            </LineChart>
                          </ResponsiveContainer>
                        ) : (
                          <div className="empty">Waiting for readings.</div>
                        )}
                      </div>
                    </article>
                  );
                })}
              </div>
            </div>
          ))
        ) : (
          <div className="empty">No readings yet. Waiting for sensor data.</div>
        )}
      </section>
    </div>
  );
}
