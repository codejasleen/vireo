(() => {
  "use strict";

  const data = window.VIREO_DATA;
  const colors = ["#0b6b67", "#d97706", "#486da8"];
  const formatNumber = new Intl.NumberFormat("en-IN");
  const formatCurrency = (value) => `₹${formatNumber.format(value)}`;
  const formatDate = (iso, options = {}) => new Intl.DateTimeFormat("en-IN", {
    day: "numeric", month: "short", year: "numeric", ...options,
  }).format(new Date(`${iso}T00:00:00`));

  function activateView(name) {
    document.querySelectorAll(".view").forEach((view) => view.classList.toggle("is-active", view.id === name));
    document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("is-active", tab.dataset.view === name));
    history.replaceState(null, "", `#${name}`);
  }

  document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => activateView(tab.dataset.view)));

  function weekEnd(week) {
    const end = new Date(`${week}T00:00:00`);
    end.setDate(end.getDate() + 6);
    return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" }).format(end);
  }

  function changeText(current, previous, unit = "%") {
    if (previous === null || previous === undefined || previous === 0) return "No prior-week comparison";
    const change = unit === "%" ? ((current - previous) / previous) * 100 : current - previous;
    const direction = change >= 0 ? "up" : "down";
    return `${direction} ${Math.abs(change).toFixed(unit === "%" ? 1 : 2)}${unit} vs prior week`;
  }

  function selectedTopIssues(week) {
    const issues = data.overview.by_week[week].issues;
    return Object.entries(issues).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 3);
  }

  function rankedIssues(week) {
    return Object.entries(data.overview.by_week[week].issues)
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .map(([name, count], index) => ({ name, count, rank: index + 1 }));
  }

  function renderIssueList(week) {
    const total = data.overview.by_week[week].tickets_created;
    const allIssues = rankedIssues(week);
    const topIssue = allIssues[0];
    document.getElementById("issue-summary").textContent = `${topIssue.name} was the top customer issue this week with ${formatNumber.format(topIssue.count)} tickets.`;
    document.getElementById("weekly-issue-list").innerHTML = allIssues.map((issue) => `
      <div class="issue-row">
        <span class="issue-name" title="${issue.name}"><strong>${issue.rank}.</strong>${issue.name}</span>
        <span class="issue-count">${formatNumber.format(issue.count)}</span>
        <span class="issue-share">${(issue.count / total * 100).toFixed(1)}%</span>
      </div>`).join("");
  }

  function trendForWeek(week) {
    const selectedIndex = data.overview.weeks.indexOf(week);
    const weeks = data.overview.weeks.slice(Math.max(0, selectedIndex - 7), selectedIndex + 1);
    const topIssues = selectedTopIssues(week).map(([name]) => name);
    return {
      weeks,
      series: topIssues.map((name) => ({
        name,
        values: weeks.map((itemWeek) => data.overview.by_week[itemWeek].issues[name] || 0),
      })),
    };
  }

  function renderTrend(week) {
    const { weeks, series } = trendForWeek(week);
    const width = 760, height = 270;
    const margin = { top: 20, right: 18, bottom: 42, left: 38 };
    const chartW = width - margin.left - margin.right;
    const chartH = height - margin.top - margin.bottom;
    const maxValue = Math.max(1, ...series.flatMap((item) => item.values));
    const yMax = Math.ceil(maxValue / 5) * 5 || 5;
    const x = (i) => margin.left + (weeks.length === 1 ? chartW / 2 : (i / (weeks.length - 1)) * chartW);
    const y = (v) => margin.top + chartH - (v / yMax) * chartH;
    const gridValues = [0, .25, .5, .75, 1].map((n) => Math.round(yMax * n));
    const grid = gridValues.map((v) => `
      <line class="grid-line" x1="${margin.left}" y1="${y(v)}" x2="${width - margin.right}" y2="${y(v)}"></line>
      <text class="axis-label" x="${margin.left - 9}" y="${y(v) + 4}" text-anchor="end">${v}</text>`).join("");
    const xLabels = weeks.map((itemWeek, i) => `<text class="axis-label" x="${x(i)}" y="${height - 12}" text-anchor="middle">${formatDate(itemWeek, { day: "numeric", month: "short", year: undefined })}</text>`).join("");
    const lines = series.map((item, index) => {
      const points = item.values.map((v, i) => `${x(i)},${y(v)}`).join(" ");
      const dots = item.values.map((v, i) => `<circle class="dot" cx="${x(i)}" cy="${y(v)}" r="4" fill="${colors[index]}"><title>${item.name}: ${v}</title></circle>`).join("");
      return `<polyline class="line" points="${points}" stroke="${colors[index]}"></polyline>${dots}`;
    }).join("");
    document.getElementById("trend-chart").innerHTML = `<svg viewBox="0 0 ${width} ${height}" aria-hidden="true">${grid}${xLabels}${lines}</svg>`;
    document.getElementById("trend-legend").innerHTML = series.map((item, i) => `<span><i style="background:${colors[i]}"></i>${item.name}</span>`).join("");
  }

  function renderDigest(week) {
    const metrics = data.overview.by_week[week];
    const weekIndex = data.overview.weeks.indexOf(week);
    const previousWeek = weekIndex > 0 ? data.overview.weeks[weekIndex - 1] : null;
    const previous = previousWeek ? data.overview.by_week[previousWeek] : null;
    const [topIssue = "No classified theme", topIssueCount = 0] = selectedTopIssues(week)[0] || [];
    const topIssueShare = metrics.tickets_created ? topIssueCount / metrics.tickets_created * 100 : 0;

    document.getElementById("reporting-period").textContent = `${formatDate(week)}–${weekEnd(week)} · complete week in the saved export`;
    const kpis = [
      ["Tickets handled", formatNumber.format(metrics.tickets_handled), `${metrics.resolved} resolved · ${metrics.auto_closed} auto-closed`, ""],
      ["New tickets", formatNumber.format(metrics.tickets_created), previous ? changeText(metrics.tickets_created, previous.tickets_created) : "No prior-week comparison", ""],
      ["Top complaint theme", topIssue, `${formatNumber.format(topIssueCount)} tickets · ${topIssueShare.toFixed(1)}% of new tickets`, "textual"],
      ["Average CSAT", metrics.average_csat === null ? "—" : metrics.average_csat.toFixed(2), `${formatNumber.format(metrics.csat_responses)} survey responses`, ""],
    ];
    document.getElementById("overview-kpis").innerHTML = kpis.map(([label, value, meta, cls]) => `
      <article class="kpi-card">
        <div class="kpi-label">${label}</div>
        <div class="kpi-value ${cls}">${value}</div>
        <div class="kpi-meta">${meta}</div>
      </article>`).join("");

    const chatShare = metrics.tickets_created ? metrics.chat / metrics.tickets_created * 100 : 0;
    const insights = [
      `The team handled ${formatNumber.format(metrics.tickets_handled)} tickets${previous ? `, ${changeText(metrics.tickets_handled, previous.tickets_handled).replace(" vs prior week", " from the prior week")}.` : "."}`,
      `New demand was ${formatNumber.format(metrics.tickets_created)} tickets${previous ? `, ${changeText(metrics.tickets_created, previous.tickets_created).replace(" vs prior week", " from the prior week")}.` : "."}`,
      `${topIssue} led the tracked themes with ${formatNumber.format(topIssueCount)} tickets (${topIssueShare.toFixed(1)}% of new demand).`,
      `Chat represented ${chatShare.toFixed(1)}% of new contacts${previous && metrics.average_csat !== null && previous.average_csat !== null ? `; CSAT was ${changeText(metrics.average_csat, previous.average_csat, " points")}.` : "."}`,
    ];
    document.getElementById("weekly-insights").innerHTML = insights.map((text) => `<li>${text}</li>`).join("");
    renderIssueList(week);
    renderTrend(week);
  }

  const categories = data.repeat_contacts.categories.slice(0, 5);
  const maxContacts = Math.max(...categories.map((item) => item.contacts));
  document.getElementById("repeat-categories").innerHTML = categories.map((item, index) => `
    <div class="bar-row">
      <span class="bar-label" title="${item.name}">${index + 1}. ${item.name}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${item.contacts / maxContacts * 100}%"></span></span>
      <span class="bar-count">${item.contacts}</span>
      <span class="bar-cost">${formatCurrency(item.capacity_inr)}</span>
    </div>`).join("");

  function renderLeaderboard(week) {
    const rows = data.leaderboard.by_week[week] || [];
    const total = rows.reduce((sum, row) => sum + row.closed, 0);
    document.getElementById("leaderboard-summary").textContent = `${rows.length} ranked agents · ${formatNumber.format(total)} tickets closed`;
    document.getElementById("leaderboard-body").innerHTML = rows.map((row, index) => `
      <tr>
        <td><span class="rank-badge">${index + 1}</span></td>
        <td><strong>${row.name}</strong></td>
        <td>${row.team}<br><small>${row.site}</small></td>
        <td class="numeric"><strong>${formatNumber.format(row.closed)}</strong></td>
      </tr>`).join("");
  }

  const digestSelect = document.getElementById("digest-week-select");
  const leaderboardSelect = document.getElementById("leaderboard-week-select");
  const options = [...data.overview.weeks].reverse().map((week) => `<option value="${week}">${formatDate(week)}</option>`).join("");
  digestSelect.innerHTML = options;
  leaderboardSelect.innerHTML = options;

  function setSelectedWeek(week) {
    digestSelect.value = week;
    leaderboardSelect.value = week;
    renderDigest(week);
    renderLeaderboard(week);
  }
  digestSelect.addEventListener("change", () => setSelectedWeek(digestSelect.value));
  leaderboardSelect.addEventListener("change", () => setSelectedWeek(leaderboardSelect.value));
  setSelectedWeek(data.overview.default_week);

  const initialView = location.hash.slice(1);
  if (["overview", "leaderboard", "opportunities"].includes(initialView)) activateView(initialView);
})();
