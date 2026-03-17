const $ = (id) => document.getElementById(id);

const statusOptions = {
  good: {
    label: "Good to spray",
    badgeClass: "badge-good",
    dotClass: "dot-good",
    summaryClass: "status-good",
  },
  bad: {
    label: "Do not spray",
    badgeClass: "badge-bad",
    dotClass: "dot-bad",
    summaryClass: "status-bad",
  },
  iffy: {
    label: "Ify weather",
    badgeClass: "badge-iffy",
    dotClass: "dot-iffy",
    summaryClass: "status-iffy",
  },
};

function formatShortDay(date) {
  return date.toLocaleDateString(undefined, { weekday: "short" }).toUpperCase();
}

function formatDetailDate(date) {
  return date.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatStandardTime(timeText) {
  const match = /^([01]?\d|2[0-3]):([0-5]\d)$/.exec(String(timeText || "").trim());
  if (!match) return timeText;

  const hour24 = Number(match[1]);
  const minutes = match[2];
  const period = hour24 >= 12 ? "pm" : "am";
  const hour12 = hour24 % 12 || 12;

  if (minutes === "00") {
    return `${hour12} ${period}`;
  }

  return `${hour12}:${minutes} ${period}`;
}

const METRIC_INFO = {
  wind: { label: "Wind", unit: "km/h" },
  temp: { label: "Temperature", unit: "°C" },
  humidity: { label: "Humidity", unit: "%" },
  precip: { label: "Precipitation", unit: "mm" },
  dew: { label: "Dew point gap", unit: "°C" },
  pressure: { label: "Pressure trend", unit: "hPa/3h" },
  gdd: { label: "GDD stage", unit: "" },
};

let currentMetric = "wind";
let currentForecast = [];
const DEFAULT_LOCATION = {
  label: "SASKATOON, SK",
  query: "Saskatoon, SK",
  lat: 52.13,
  lon: -106.67,
};

const FORECAST_QUERY = {
  growth_stage: "3",
  start_date: "2025-06-15",
  end_date: "2025-06-21",
};

let currentLocation = { ...DEFAULT_LOCATION };
let activeRequestId = 0;

function buildBackendApiUrl(location) {
  const params = new URLSearchParams({
    lat: String(location.lat),
    lon: String(location.lon),
    ...FORECAST_QUERY,
  });

  return `http://localhost:8000/api/forecast?${params.toString()}`;
}

function formatLocationLabel(location) {
  const parts = [location.name, location.admin1 || location.country_code || location.country].filter(Boolean);
  return parts.join(", ").toUpperCase();
}

async function geocodeLocation(query) {
  const params = new URLSearchParams({
    name: query,
    count: "1",
    language: "en",
    format: "json",
  });

  const response = await fetch(`https://geocoding-api.open-meteo.com/v1/search?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`Geocoding API ${response.status}`);
  }

  const payload = await response.json();
  const match = payload.results && payload.results[0];
  if (!match) {
    throw new Error("Location not found");
  }

  return {
    query,
    lat: match.latitude,
    lon: match.longitude,
    name: match.name,
    admin1: match.admin1,
    country: match.country,
    country_code: match.country_code,
    label: formatLocationLabel(match),
  };
}

function setLocationFeedback(message, type = "") {
  const feedback = $("locationFeedback");
  if (!feedback) return;

  feedback.textContent = message;
  feedback.className = `location-feedback${type ? ` ${type}` : ""}`;
}

function updateHeaderLocation(location) {
  const label = $("locationLabel");
  const updated = $("updatedText");

  if (label) {
    label.innerHTML = `<span class="location-dot"></span>${location.label}`;
  }

  if (updated) {
    updated.textContent = `Updated just now • Open-Meteo • ${location.label}`;
  }
}

function getMetricStatus(metric, value) {
  if (metric === "wind") {
    if (value <= 10) return "good";
    if (value <= 15) return "iffy";
    return "bad";
  }

  if (metric === "temp") {
    if (value < 10 || value > 30) return "bad";
    if ((value >= 10 && value <= 11) || (value >= 26 && value <= 30)) return "iffy";
    return "good";
  }

  if (metric === "humidity") {
    if (value < 40 || value > 90) return "bad";
    if ((value >= 40 && value <= 49) || (value >= 71 && value <= 90)) return "iffy";
    return "good";
  }

  if (metric === "precip") {
    if (value === 0) return "good";
    if (value < 2) return "iffy";
    return "bad";
  }

  if (metric === "dew") {
    if (value < 3 || value > 20) return "bad";
    if ((value >= 3 && value <= 4) || (value >= 16 && value <= 20)) return "iffy";
    return "good";
  }

  if (metric === "pressure") {
    if (value >= 1 && value <= 3) return "good";
    if (value >= -1 && value <= 1) return "iffy";
    return "bad";
  }

  if (metric === "gdd") {
    if (value < 200 || value > 800) return "bad";
    if ((value >= 200 && value <= 349) || (value >= 602 && value <= 800)) return "iffy";
    return "good";
  }

  return "good";
}

function getMetricRange(metric) {
  const ranges = {
    wind: { min: 0, max: 25 },
    temp: { min: -5, max: 40 },
    humidity: { min: 0, max: 100 },
    precip: { min: 0, max: 5 },
    dew: { min: 0, max: 25 },
    pressure: { min: -5, max: 5 },
    gdd: { min: 0, max: 1000 },
  };
  return ranges[metric] || { min: 0, max: 100 };
}

function generateMetricSeries(day, metric) {
  const backendSeries = day.hourly && Array.isArray(day.hourly[metric]) ? day.hourly[metric] : null;
  const backendTimeLabels = day.hourly && Array.isArray(day.hourly.timeLabels) ? day.hourly.timeLabels : [];

  if (backendSeries && backendSeries.length > 0) {
    return backendSeries.map((value, idx) => ({
      time: backendTimeLabels[idx] || `${String(idx).padStart(2, "0")}:00`,
      value,
      status: getMetricStatus(metric, value),
    }));
  }

  const base = {
    wind: day.windKmh,
    temp: day.temperatureC,
    humidity: day.humidityPct,
    precip: day.precipitationMm,
    dew: day.dewPointGap,
    pressure: day.pressureTrend,
    gdd: day.gddStage,
  }[metric];

  const range = getMetricRange(metric);
  const jitter = (range.max - range.min) * 0.12; // ~12% jitter

  return Array.from({ length: 24 }).map((_, idx) => {
    const noise = (Math.random() - 0.5) * jitter;
    const seasonal = Math.sin((idx / 24) * Math.PI * 2) * jitter * 0.5;
    const value = Math.min(range.max, Math.max(range.min, base + noise + seasonal));

    return {
      time: `${String(idx).padStart(2, "0")}:00`,
      value,
      status: getMetricStatus(metric, value),
    };
  });
}

function mapBackendDayToUi(day) {
  return {
    date: new Date(`${day.date}T12:00:00`),
    status: day.status,
    reasons: Array.isArray(day.reasons) ? day.reasons : [],
    windKmh: Number(day.windKmh ?? 0),
    temperatureC: Number(day.temperatureC ?? 0),
    humidityPct: Number(day.humidityPct ?? 0),
    precipitationMm: Number(day.precipitationMm ?? 0),
    dewPointGap: Number(day.dewPointGap ?? 0),
    pressureTrend: Number(day.pressureTrend ?? 0),
    gddStage: Number(day.gddStage ?? 0),
    hourly: day.hourly || {},
  };
}

async function loadForecastData(location = currentLocation) {
  try {
    const response = await fetch(buildBackendApiUrl(location));
    if (!response.ok) {
      throw new Error(`Backend API ${response.status}`);
    }

    const payload = await response.json();
    if (!payload.days || !Array.isArray(payload.days) || payload.days.length === 0) {
      throw new Error("Backend returned no forecast days");
    }

    return payload.days.map(mapBackendDayToUi);
  } catch (error) {
    console.warn("Using fallback forecast data:", error.message);
    return createFallbackForecastData();
  }
}

async function refreshForecast(location, options = {}) {
  const requestId = ++activeRequestId;
  const submitButton = $("locationSubmit");
  const input = $("locationInput");

  if (submitButton) submitButton.disabled = true;
  if (input) input.disabled = true;

  if (!options.silent) {
    setLocationFeedback(`Loading forecast for ${location.label}...`);
  }

  try {
    const forecast = await loadForecastData(location);
    if (requestId !== activeRequestId) return;

    currentLocation = { ...currentLocation, ...location };
    currentForecast = forecast;
    currentMetric = "wind";

    updateHeaderLocation(currentLocation);
    renderSummary(currentForecast);
    renderForecastRow(currentForecast, 0);
    renderDetail(currentForecast[0]);

    if (!options.silent) {
      setLocationFeedback(`Showing forecast for ${currentLocation.label}.`, "success");
    }
  } catch (error) {
    if (requestId !== activeRequestId) return;
    setLocationFeedback(error.message || "Unable to update location.", "error");
  } finally {
    if (requestId === activeRequestId) {
      if (submitButton) submitButton.disabled = false;
      if (input) input.disabled = false;
    }
  }
}

function setupLocationForm() {
  const form = $("locationForm");
  const input = $("locationInput");
  if (!form || !input) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const query = input.value.trim();

    if (!query) {
      setLocationFeedback("Enter a city or region to update the forecast.", "error");
      return;
    }

    try {
      setLocationFeedback("Finding location...");
      const location = await geocodeLocation(query);
      input.value = location.query;
      await refreshForecast(location);
    } catch (error) {
      setLocationFeedback(error.message || "Unable to find that location.", "error");
    }
  });
}

function evaluateWeather({ windKmh, temperatureC, humidityPct, precipitationMm, dewPointGap, pressureTrend, gddStage }) {
  const reasons = [];
  const levels = {
    wind: getMetricStatus("wind", windKmh),
    temp: getMetricStatus("temp", temperatureC),
    humidity: getMetricStatus("humidity", humidityPct),
    precip: getMetricStatus("precip", precipitationMm),
    dew: getMetricStatus("dew", dewPointGap),
    pressure: getMetricStatus("pressure", pressureTrend),
    gdd: getMetricStatus("gdd", gddStage),
  };

  if (levels.wind === "bad") reasons.push("Wind is too strong");
  if (levels.temp === "bad") reasons.push("Temperature is outside the safe range");
  if (levels.humidity === "bad") reasons.push("Humidity is outside the safe range");
  if (levels.precip === "bad") reasons.push("Rain is too heavy");
  if (levels.dew === "bad") reasons.push("Dew point gap is too small/large");
  if (levels.pressure === "bad") reasons.push("Pressure trend is too extreme");
  if (levels.gdd === "bad") reasons.push("Growth stage is outside optimal range");

  if (levels.wind === "iffy") reasons.push("Wind is close to limit");
  if (levels.temp === "iffy") reasons.push("Temperature is getting high/low");
  if (levels.humidity === "iffy") reasons.push("Humidity is getting high/low");
  if (levels.precip === "iffy") reasons.push("Chance of rain is rising");
  if (levels.dew === "iffy") reasons.push("Dew point gap is near limit");
  if (levels.pressure === "iffy") reasons.push("Pressure trend is close to limit");
  if (levels.gdd === "iffy") reasons.push("Growth stage proximity to optimal range");

  const status = Object.values(levels).includes("bad")
    ? "bad"
    : Object.values(levels).includes("iffy")
    ? "iffy"
    : "good";

  return { status, reasons };
}

function createFallbackForecastData() {
  const startDate = new Date("2025-06-15T12:00:00");

  // Guarantee 4 green days, 2 red days, and 1 yellow day
  const forcedStatuses = ["good", "good", "iffy", "good", "bad", "bad", "good"];

  return Array.from({ length: 7 }).map((_, idx) => {
    const day = new Date(startDate);
    day.setDate(startDate.getDate() + idx);

    // Use calendar day names so the rules stay consistent even if start date shifts.
    const weekday = day.getDay(); // 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat

    let windKmh = 10;
    let temperatureC = 20;
    let humidityPct = 50;
    let precipitationMm = 0;
    let dewPointGap = 10;
    let pressureTrend = 2;
    let gddStage = 450;

    if (weekday === 6) {
      // Saturday: optimal
      windKmh = 10;
      temperatureC = 20;
      humidityPct = 50;
      precipitationMm = 0;
      dewPointGap = 10;
      pressureTrend = 2;
      gddStage = 500;
    } else if (weekday === 1) {
      // Monday: optimal
      windKmh = 9;
      temperatureC = 19;
      humidityPct = 52;
      precipitationMm = 0;
      dewPointGap = 11;
      pressureTrend = 2;
      gddStage = 480;
    } else if (weekday === 2) {
      // Tuesday: iffy (close to threshold) — not hot & humid
      windKmh = 13;
      temperatureC = 29;
      humidityPct = 30;
      precipitationMm = 0;
      dewPointGap = 7;
      pressureTrend = 0.5;
      gddStage = 580;
    } else if (weekday === 3) {
      // Wednesday: lower wind, still good
      windKmh = 9;
      temperatureC = 18;
      humidityPct = 60;
      precipitationMm = 0;
      dewPointGap = 12;
      pressureTrend = 2;
      gddStage = 520;
    } else if (weekday === 5) {
      // Friday: not optimal (red) - cannot be hot and raining
      windKmh = 18;
      temperatureC = 32;
      humidityPct = 75;
      precipitationMm = 0;
      dewPointGap = 5;
      pressureTrend = -2;
      gddStage = 620;
    } else {
      // Default pattern for other days
      windKmh = 8 + idx * 2;
      temperatureC = 14 + idx;
      humidityPct = 55 + idx * 3;
      precipitationMm = idx % 3 === 0 ? 0 : (idx % 2) * 2;
      dewPointGap = 10;
      pressureTrend = 1;
      gddStage = 460 + idx * 20;
    }

    const { status, reasons } = evaluateWeather({
      windKmh,
      temperatureC,
      humidityPct,
      precipitationMm,
      dewPointGap,
      pressureTrend,
      gddStage,
    });

    // Build quarter-hour status bars (6:00–7:45) based on the computed status.
    const hourly = Array.from({ length: 8 }).map((_, i) => {
      const time = `${6 + Math.floor(i / 4)}:${String((i % 4) * 15).padStart(2, "0")}`;
      return {
        time,
        status: status,
      };
    });

    return {
      date: day,
      status: forcedStatuses[idx],
      reasons,
      windKmh,
      temperatureC,
      humidityPct,
      precipitationMm,
      dewPointGap,
      pressureTrend,
      gddStage,
      hourly,
    };
  });
}


function renderSummary(forecast) {
  const badge = $("summaryBadge");
  const goodCount = forecast.filter((day) => day.status === "good").length;
  const iffyCount = forecast.filter((day) => day.status === "iffy").length;
  const badCount = forecast.filter((day) => day.status === "bad").length;

  let label = `${goodCount} of 7 days good to spray`;
  let summaryClass = statusOptions.good.summaryClass;
  let icon = "✔";

  if (iffyCount >= goodCount && iffyCount >= badCount) {
    label = `${iffyCount} of 7 days are iffy`;
    summaryClass = statusOptions.iffy.summaryClass;
    icon = "!";
  } else if (badCount > goodCount && badCount > iffyCount) {
    label = `${badCount} of 7 days are not suitable`;
    summaryClass = statusOptions.bad.summaryClass;
    icon = "x";
  }

  badge.innerHTML = `
    <span class="summary-check">${icon}</span>
    <span class="summary-text">${label}</span>
  `;
  badge.className = `summary-pill ${summaryClass}`;
}

function renderForecastRow(forecast, selectedIndex) {
  const row = $("forecastRow");
  row.innerHTML = "";

  forecast.forEach((day, index) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = `forecast-day status-${day.status} ${index === selectedIndex ? "selected" : ""}`.trim();
    card.innerHTML = `
      <div class="day-name">${formatShortDay(day.date)}</div>
      <div class="day-date">${day.date.getDate()}</div>
      <span class="day-dot ${statusOptions[day.status].dotClass}"></span>
    `;

    card.addEventListener("click", () => {
      currentMetric = "wind"; // default to wind chart on day select
      renderForecastRow(forecast, index);
      renderDetail(day);
    });

    row.appendChild(card);
  });
}

function renderDetail(day) {
  $("detailDate").textContent = formatDetailDate(day.date);

  const status = statusOptions[day.status];
  const badge = $("detailBadge");
  badge.textContent = status.label;
  badge.className = `detail-badge ${status.badgeClass}`;

  if (day.reasons && day.reasons.length) {
    $("detailSubtitle").textContent = day.reasons.join(" • ");
  } else {
    $("detailSubtitle").textContent = "All conditions are within optimal spray thresholds.";
  }

  $("detailWind").textContent = `${day.windKmh} km/h`;
  $("detailTemp").textContent = `${day.temperatureC}°C`;
  $("detailHumidity").textContent = `${day.humidityPct}%`;
  $("detailPrecip").textContent = `${day.precipitationMm} mm`;
  $("detailDew").textContent = `${day.dewPointGap}°C`;
  $("detailPressure").textContent = `${day.pressureTrend.toFixed(1)} hPa/3h`;
  $("detailGdd").textContent = `${day.gddStage}`;

  // Sync each metric card dot color with its own threshold status.
  const metricStatusMap = {
    wind: getMetricStatus("wind", day.windKmh),
    temp: getMetricStatus("temp", day.temperatureC),
    humidity: getMetricStatus("humidity", day.humidityPct),
    precip: getMetricStatus("precip", day.precipitationMm),
    dew: getMetricStatus("dew", day.dewPointGap),
    pressure: getMetricStatus("pressure", day.pressureTrend),
    gdd: getMetricStatus("gdd", day.gddStage),
  };

  document.querySelectorAll(".detail-card").forEach((card) => {
    const metric = card.dataset.metric;
    card.dataset.status = metricStatusMap[metric] || "good";
    card.classList.toggle("active", metric === currentMetric);
  });

  renderHourlyChart(day, currentMetric);
}

function renderHourlyChart(day, metric) {
  const title = $("chartMetricTitle");
  const overall = $("chartOverall");
  const info = METRIC_INFO[metric] || { label: metric, unit: "" };
  title.innerHTML = `Hourly <span>${info.label}</span>`;

  const series = generateMetricSeries(day, metric);
  const range = getMetricRange(metric);
  const chart = $("hourlyChart");
  const labels = $("chartLabels");
  chart.innerHTML = "";
  labels.innerHTML = "";

  if (!series.length) {
    chart.innerHTML = "<div style='grid-column: 1 / -1; text-align:center; color:#6b7b88;'>No hourly data</div>";
    overall.textContent = "Overall suggestion: No hourly data available.";
    overall.className = "chart-overall";
    return;
  }

  const counts = series.reduce(
    (acc, point) => {
      acc[point.status] += 1;
      return acc;
    },
    { good: 0, iffy: 0, bad: 0 }
  );

  let overallStatus = "good";
  let message = "Overall suggestion: Good window for spraying.";

  if (counts.bad > 0) {
    overallStatus = "bad";
    message = "Overall suggestion: Not recommended today for this metric.";
  } else if (counts.iffy > 0) {
    overallStatus = "iffy";
    message = "Overall suggestion: Use caution and monitor closely.";
  }

  overall.textContent = message;
  overall.className = `chart-overall ${overallStatus}`;

  series.forEach((point) => {
    const bar = document.createElement("div");
    bar.className = `chart-bar ${point.status}`;
    const displayTime = formatStandardTime(point.time);

    const heightPct = Math.round(((point.value - range.min) / (range.max - range.min)) * 100);

    bar.innerHTML = `
      <div class="bar-fill" style="height: ${heightPct}%"></div>
      <span class="bar-label">${Math.round(point.value)}${info.unit}</span>
    `;

    bar.title = `${displayTime} — ${point.value.toFixed(1)} ${info.unit}`;
    chart.appendChild(bar);

    const label = document.createElement("div");
    label.textContent = displayTime;
    labels.appendChild(label);
  });

  const colTemplate = `repeat(${series.length}, minmax(44px, 1fr))`;
  chart.style.gridTemplateColumns = colTemplate;
  labels.style.gridTemplateColumns = colTemplate;
}

function setupMetricSelector() {
  const grid = document.querySelector(".detail-grid");
  if (!grid) return;

  grid.addEventListener("click", (event) => {
    const card = event.target.closest(".detail-card");
    if (!card) return;

    const metric = card.dataset.metric;
    if (!metric || !METRIC_INFO[metric]) return;

    currentMetric = metric;

    // Re-render detail to update chart for currently selected day
    const selectedDayIndex = Array.from(document.querySelectorAll(".forecast-day")).findIndex((btn) =>
      btn.classList.contains("selected")
    );
    if (selectedDayIndex === -1) return;

    renderDetail(currentForecast[selectedDayIndex]);
  });
}

window.addEventListener("DOMContentLoaded", async () => {
  setupLocationForm();
  setupMetricSelector();
  updateHeaderLocation(currentLocation);
  await refreshForecast(currentLocation, { silent: true });
});
