/**
 * Main UI for the terrarium monitor dashboard.
 */

import { useEffect, useMemo, useState } from "react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
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
 * Extract available metric options from the summary payload.
 */
function buildMetricOptions(summary) {
  const metrics = new Set();
  summary.forEach((sensor) => {
    sensor.metrics.forEach((metric) => metrics.add(metric.metric));
  });
  return Array.from(metrics).sort();
}

/**
 * Extract available sensor options from the summary payload.
 */
function buildSensorOptions(summary) {
  return summary.map((sensor) => ({
    key: sensor.key,
    label: sensor.location ? `${sensor.name} (${sensor.location})` : sensor.name,
  }));
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
 * Dashboard application component.
 */
export default function App() {
  const [summary, setSummary] = useState([]);
  const [summaryMeta, setSummaryMeta] = useState({ generatedAt: null });
  const [measurements, setMeasurements] = useState([]);
  const [chartMetric, setChartMetric] = useState("temperature");
  const [chartSensor, setChartSensor] = useState("ambient_bme280");
  const [unitPreference, setUnitPreference] = useState(loadUnitPreference());
  const [status, setStatus] = useState({ loading: true, error: null });

  const metricOptions = useMemo(() => buildMetricOptions(summary), [summary]);
  const sensorOptions = useMemo(() => buildSensorOptions(summary), [summary]);
  const cardItems = useMemo(
    () => buildCardItems(summary, unitPreference),
    [summary, unitPreference],
  );
  const chartData = useMemo(
    () => prepareChartData(measurements, chartMetric, unitPreference),
    [measurements, chartMetric, unitPreference],
  );

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
    if (!metricOptions.length && !sensorOptions.length) {
      return;
    }
    if (metricOptions.length && !metricOptions.includes(chartMetric)) {
      setChartMetric(metricOptions[0]);
    }
    if (sensorOptions.length && !sensorOptions.find((item) => item.key === chartSensor)) {
      setChartSensor(sensorOptions[0].key);
    }
  }, [metricOptions, sensorOptions, chartMetric, chartSensor]);

  useEffect(() => {
    if (!chartMetric || !chartSensor) {
      return;
    }
    let cancelled = false;

    /**
     * Fetch chart data for the selected sensor and metric.
     */
    const loadMeasurements = async () => {
      try {
        const range = buildRange(CHART_WINDOW_HOURS);
        const data = await fetchMeasurements({
          sensor_key: chartSensor,
          metric: chartMetric,
          start: range.start,
          end: range.end,
          limit: 2000,
        });
        if (cancelled) {
          return;
        }
        setMeasurements(data.measurements || []);
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
  }, [chartMetric, chartSensor]);

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
            Live readings with a {CHART_WINDOW_HOURS}-hour trend line.
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

      <section className="chart-panel">
        <header className="chart-header">
          <div>
            <p className="eyebrow">Trend View</p>
            <h2>{formatMetricLabel(chartMetric)}</h2>
          </div>
          <div className="chart-controls">
            <label>
              Metric
              <select
                value={metricOptions.includes(chartMetric) ? chartMetric : ""}
                onChange={(event) => setChartMetric(event.target.value)}
              >
                {!metricOptions.length ? (
                  <option value="">Waiting for data</option>
                ) : null}
                {metricOptions.map((metric) => (
                  <option key={metric} value={metric}>
                    {formatMetricLabel(metric)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Sensor
              <select
                value={sensorOptions.find((sensor) => sensor.key === chartSensor) ? chartSensor : ""}
                onChange={(event) => setChartSensor(event.target.value)}
              >
                {!sensorOptions.length ? (
                  <option value="">Waiting for data</option>
                ) : null}
                {sensorOptions.map((sensor) => (
                  <option key={sensor.key} value={sensor.key}>
                    {sensor.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </header>

        <div className="chart-body">
          {status.error ? (
            <div className="empty">{status.error}</div>
          ) : (
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={chartData} margin={{ top: 10, right: 24, left: 0, bottom: 0 }}>
                <XAxis dataKey="recorded_at" tickFormatter={formatChartTime} />
                <YAxis
                  tickFormatter={(value) =>
                    chartMetric === "temperature" && typeof value === "number"
                      ? value.toFixed(0)
                      : value
                  }
                />
                <Tooltip
                  labelFormatter={formatTimestamp}
                  formatter={(value, name, props) => {
                    const data = props.payload || {};
                    return [
                      formatMeasurementValue(chartMetric, data.value, data.unit, unitPreference),
                      formatMetricLabel(chartMetric),
                    ];
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#1b7f6b"
                  strokeWidth={3}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>
    </div>
  );
}
