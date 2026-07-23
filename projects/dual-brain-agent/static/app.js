const taskEl = document.querySelector("#task");
const contextEl = document.querySelector("#context");
const constraintsEl = document.querySelector("#constraints");
const runButton = document.querySelector("#runButton");
const statusEl = document.querySelector("#status");
const resultsEl = document.querySelector("#results");
const modeBadge = document.querySelector("#modeBadge");

async function loadHealth() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    modeBadge.textContent = data.mode === "demo" ? "DEMO 模式" : data.mode;
  } catch {
    modeBadge.textContent = "服务未连接";
  }
}

runButton.addEventListener("click", async () => {
  const task = taskEl.value.trim();
  if (!task) {
    statusEl.textContent = "请先输入任务";
    taskEl.focus();
    return;
  }

  setRunning(true);
  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task,
        context: contextEl.value.trim(),
        constraints: constraintsEl.value.split("\n").map(v => v.trim()).filter(Boolean),
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "运行失败");

    renderAgent("right", data.right_brain);
    renderAgent("left", data.left_brain);
    renderAgent("arbiter", data.arbiter);
    document.querySelector("#runMeta").textContent =
      `运行 ${data.duration_ms} ms · ${data.mode} · ${data.run_id.slice(0, 8)}`;
    resultsEl.classList.remove("hidden");
    statusEl.textContent = "推演完成";
  } catch (error) {
    statusEl.textContent = error.message;
  } finally {
    setRunning(false, false);
  }
});

function renderAgent(prefix, output) {
  const root = document.querySelector(`#${prefix}Output`);
  root.replaceChildren();
  root.appendChild(section("结论", [output.summary], "summary"));
  root.appendChild(section("判断依据", output.reasoning_points));
  root.appendChild(section("风险", output.risks));
  root.appendChild(section("建议", output.recommendations));
  document.querySelector(`#${prefix}Confidence`).textContent =
    `${Math.round((output.confidence || 0) * 100)}%`;
}

function section(title, items, className = "") {
  const wrapper = document.createElement("section");
  if (className) wrapper.className = className;
  const heading = document.createElement("h3");
  heading.textContent = title;
  wrapper.appendChild(heading);

  const list = document.createElement("ul");
  (items || []).filter(Boolean).forEach(item => {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  });
  wrapper.appendChild(list);
  return wrapper;
}

function setRunning(running, updateStatus = true) {
  runButton.disabled = running;
  runButton.textContent = running ? "左右脑推演中…" : "启动双脑推演";
  if (running && updateStatus) statusEl.textContent = "并行思考中";
}

loadHealth();
