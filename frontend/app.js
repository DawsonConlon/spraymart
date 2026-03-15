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
  });
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

function getMetricStatus(metric, value) {
  const thresholds = {
    wind: { goodMax: 10, okayMax: 15 },
    temp: { goodMin: 12, goodMax: 25, badMin: 30 },
    humidity: { goodMin: 50, goodMax: 80, badMin: 90 },
    precip: { good: 0, okayMax: 2, bad: 2 },
    dew: { goodMin: 5, goodMax: 15, badMax: 3, badMin: 20 },
    pressure: { goodMin: 1, goodMax: 3, okayMin: -1, okayMax: 1 },
    gdd: { goodMin: 350, goodMax: 600, okayMin: 200, okayMax: 800, badMin: 800 },
  };

  if (metric === "wind") {
    return value <= thresholds.wind.goodMax
      ? "good"
      : value <= thresholds.wind.okayMax
      ? "iffy"
      : "bad";
  }

  if (metric === "temp") {
    if (value < thresholds.temp.goodMin || value > thresholds.temp.badMin) return "bad";
    return value <= thresholds.temp.goodMax ? "good" : "iffy";
  }

  if (metric === "humidity") {
    if (value < thresholds.humidity.goodMin || value > thresholds.humidity.badMin) return "bad";
    return value <= thresholds.humidity.goodMax ? "good" : "iffy";
  }

  if (metric === "precip") {
    if (value > thresholds.precip.bad) return "bad";
    return value === thresholds.precip.good ? "good" : "iffy";
  }

  if (metric === "dew") {
    if (value < thresholds.dew.badMax || value > thresholds.dew.badMin) return "bad";
    return value >= thresholds.dew.goodMin && value <= thresholds.dew.goodMax ? "good" : "iffy";
  }

  if (metric === "pressure") {
    if (value >= thresholds.pressure.goodMin && value <= thresholds.pressure.goodMax) return "good";
    if (value >= thresholds.pressure.okayMin && value <= thresholds.pressure.okayMax) return "iffy";
    return "bad";
  }

  if (metric === "gdd") {
    if (value < thresholds.gdd.goodMin || value > thresholds.gdd.badMin) return "bad";
    return value <= thresholds.gdd.goodMax ? "good" : "iffy";
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

  return Array.from({ length: 8 }).map((_, idx) => {
    const noise = (Math.random() - 0.5) * jitter;
    const seasonal = Math.sin((idx / 7) * Math.PI * 2) * jitter * 0.5;
    const value = Math.min(range.max, Math.max(range.min, base + noise + seasonal));

    return {
      time: `${6 + Math.floor(idx / 4)}:${String((idx % 4) * 15).padStart(2, "0")}`,
      value,
      status: getMetricStatus(metric, value),
    };
  });
}

function evaluateWeather({ windKmh, temperatureC, humidityPct, precipitationMm, dewPointGap, pressureTrend, gddStage }) {
  const thresholds = {
    wind: { goodMax: 10, okayMax: 15 },
    temp: { goodMin: 12, goodMax: 25, badMin: 30 },
    humidity: { goodMin: 50, goodMax: 80, badMin: 90 },
    precip: { good: 0, okayMax: 2, bad: 2 },
    dew: { goodMin: 5, goodMax: 15, badMax: 3, badMin: 20 },
    pressure: { goodMin: 1, goodMax: 3, okayMin: -1, okayMax: 1 },
    gdd: { goodMin: 350, goodMax: 600, okayMin: 200, okayMax: 800, badMin: 800 },
  };

  const reasons = [];
  const levels = {
    wind:
      windKmh <= thresholds.wind.goodMax
        ? "good"
        : windKmh <= thresholds.wind.okayMax
        ? "iffy"
        : "bad",
    temp:
      temperatureC < thresholds.temp.goodMin || temperatureC > thresholds.temp.badMin
        ? "bad"
        : temperatureC <= thresholds.temp.goodMax
        ? "good"
        : "iffy",
    humidity:
      humidityPct < thresholds.humidity.goodMin || humidityPct > thresholds.humidity.badMin
        ? "bad"
        : humidityPct <= thresholds.humidity.goodMax
        ? "good"
        : "iffy",
    precip:
      precipitationMm > thresholds.precip.bad
        ? "bad"
        : precipitationMm === thresholds.precip.good
        ? "good"
        : "iffy",
    dew:
      dewPointGap < thresholds.dew.badMax || dewPointGap > thresholds.dew.badMin
        ? "bad"
        : dewPointGap >= thresholds.dew.goodMin && dewPointGap <= thresholds.dew.goodMax
        ? "good"
        : "iffy",
    pressure:
      pressureTrend >= thresholds.pressure.goodMin && pressureTrend <= thresholds.pressure.goodMax
        ? "good"
        : pressureTrend >= thresholds.pressure.okayMin && pressureTrend <= thresholds.pressure.okayMax
        ? "iffy"
        : "bad",
    gdd:
      gddStage < thresholds.gdd.goodMin || gddStage > thresholds.gdd.badMin
        ? "bad"
        : gddStage <= thresholds.gdd.goodMax
        ? "good"
        : "iffy",
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

function createForecastData() {
  const today = new Date();

  // Guarantee 4 green days, 2 red days, and 1 yellow day
  const forcedStatuses = ["good", "good", "iffy", "good", "bad", "bad", "good"];

  return Array.from({ length: 7 }).map((_, idx) => {
    const day = new Date(today);
    day.setDate(today.getDate() + idx);

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
  badge.innerHTML = `
    <span class="summary-check">✔</span>
    <span class="summary-text">${goodCount} of 7 days good to spray</span>
  `;
  badge.className = `summary-pill ${statusOptions.good.summaryClass}`;
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

  // Sync card dot color with status
  document.querySelectorAll(".detail-card").forEach((card) => {
    const metric = card.dataset.metric;
    card.dataset.status = day.status;
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
  chart.innerHTML = "";

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

    const heightPct = Math.round(((point.value - range.min) / (range.max - range.min)) * 100);

    bar.innerHTML = `
      <div class="bar-fill" style="height: ${heightPct}%"></div>
      <span class="bar-label">${Math.round(point.value)}${info.unit}</span>
    `;

    bar.title = `${point.time} — ${point.value.toFixed(1)} ${info.unit}`;
    chart.appendChild(bar);
  });
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

    const forecast = createForecastData();
    renderDetail(forecast[selectedDayIndex]);
  });
}

window.addEventListener("DOMContentLoaded", () => {
  const forecast = createForecastData();
  renderSummary(forecast);
  renderForecastRow(forecast, 0);
  renderDetail(forecast[0]);
  setupMetricSelector();
});
