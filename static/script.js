const SPAM_COOLDOWN = 1000; // ms cooldown pro chat/hlášky

let isCooldown = false;

document.getElementById("chatInput").addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    processTextInput(document.getElementById("chatInput").value, "user");
  }
});

function sendMessage(messageText, sender) {
  if (isCooldown && sender === "user") return;

  const messages = document.getElementById("chatMessages");
  const trimmedText = messageText.trim();
  if (trimmedText.length < 2) return;

  const messageWrapper = document.createElement("div");
  messageWrapper.classList.add("chat-message", sender);

  if (sender === "system") {
    messageWrapper.innerText = messageText; // bez prefixu a bez bubble
  } else {
    const bubble = document.createElement("div");
    bubble.classList.add("chat-bubble");
    bubble.innerText = `${
      sender === "user" ? "User" : "Bot"
    }: "${trimmedText}"`;
    messageWrapper.appendChild(bubble);
  }
  messages.appendChild(messageWrapper);
  messages.scrollTop = messages.scrollHeight;
}

function processTextInput(messageText) {
  speechCloud.dm_send_message({
    type: "chat_input",
    data: { type: "chat_input", data: messageText },
  });
  sendMessage(messageText, "user");
  document.getElementById("chatInput").value = "";
}

function sendControlCommand(type, payload) {
  if (window.speechCloud && speechCloud.dm_send_message) {
    speechCloud.dm_send_message({
      data: {
        type: type,
        ...payload,
      },
    });
  } else {
    console.error("SpeechCloud nebo WebSocket není dostupný.");
  }
}
function runAfterDelay(callback, delay) {
  const start = Date.now();
  const interval = setInterval(() => {
    if (Date.now() - start >= delay) {
      clearInterval(interval);
      callback();
    }
  }, 10);
}
// zap/vyp
function toggleLight(entityId) {
  sendControlCommand("toggle_light", { entity_id: entityId });
  runAfterDelay(() => {
    speechCloud.dm_send_message({ data: { type: "get_light_states" } });
  }, 1000);
}

function hexToRgb(hex) {
  const bigint = parseInt(hex.slice(1), 16);
  return {
    r: (bigint >> 16) & 255,
    g: (bigint >> 8) & 255,
    b: bigint & 255,
  };
}
// Změna barvy světla
function getNearestColorName(hex) {
  const knownColors = {
    "#ff0000": "red",
    "#00ff00": "green",
    "#0000ff": "blue",
    "#ffffff": "white",
    "#ffff00": "yellow",
    "#ffa500": "orange",
    "#800080": "purple",
    "#ffc0cb": "pink",
    "#00ffff": "cyan",
    "#f5deb3": "warmwhite",
    "#add8e6": "coldwhite",
  };

  // najít barvu s nejmenší vzdáleností (euclidean distance v RGB prostoru)
  const inputRGB = hexToRgb(hex);
  let closest = null;
  let minDist = Infinity;

  for (const [colorHex, name] of Object.entries(knownColors)) {
    const rgb = hexToRgb(colorHex);
    const dist = Math.sqrt(
      Math.pow(rgb.r - inputRGB.r, 2) +
        Math.pow(rgb.g - inputRGB.g, 2) +
        Math.pow(rgb.b - inputRGB.b, 2)
    );
    if (dist < minDist) {
      minDist = dist;
      closest = name;
    }
  }

  return closest;
}

function changeLightColor(event, entityId) {
  const hex = event.target.value.toLowerCase();
  const colorName = getNearestColorName(hex);

  if (!colorName) {
    console.warn("Neznámá barva nebo barva není podporována:", hex);
    return;
  }

  sendControlCommand("set_light_color", {
    entity_id: entityId,
    color: colorName,
  });
  runAfterDelay(() => {
    speechCloud.dm_send_message({ data: { type: "get_light_states" } });
  }, 1000);
}

// Změna jasu
function setBrightness(event, entityId) {
  const brightness = parseInt(event.target.value);
  sendControlCommand("set_brightness", {
    entity_id: entityId,
    brightness: brightness,
  });
  runAfterDelay(() => {
    speechCloud.dm_send_message({ data: { type: "get_light_states" } });
  }, 1000);
}

// Změna teploty
function setTemperature(entityId, inputId) {
  const temperature = parseFloat(document.getElementById(inputId).value);
  sendControlCommand("set_temperature", {
    entity_id: entityId,
    temperature: temperature,
  });
}

const thermostatIds = [];

function loadControls(entities) {
  storeEntitiesForScenes(entities); // Uloží entity pro výběr při vytváření scén
  const mountPoint = document.getElementById("controls_point");
  if (!mountPoint) {
    console.warn("Mount point #controls_point nebyl nalezen.");
    return;
  }

  mountPoint.innerHTML = "";

  const wrapper = document.createElement("div");
  wrapper.id = "devicesWrapper";
  wrapper.className = "devices-wrapper";

  const title = document.createElement("div");
  title.className = "devices-title";
  title.textContent = "Dostupná zařízení";

  const container = document.createElement("div");
  container.id = "dynamicContainer";
  container.className = "dynamic-container";

  wrapper.appendChild(title);
  wrapper.appendChild(container);
  mountPoint.appendChild(wrapper);

  // Proměnná pro sledování termostatů
  thermostatIds.length = 0;

  // Vykresli ovládací prvky
  entities.forEach((entity) => {
    const entityId = entity.entity_id;
    const friendlyName = entity.attributes?.friendly_name || entityId;

    if (entityId.startsWith("light.") || entityId.startsWith("climate.")) {
      const controlItem = document.createElement("div");
      controlItem.className = "control-item";

      if (entityId.startsWith("light.")) {
        const iconId = `icon_${entityId.replace(/\./g, "_")}`;

        controlItem.innerHTML = `
          <div class="device-name">${friendlyName}</div>
          <div class="top-row">
            <i id="${iconId}" class="fas fa-lightbulb bulb-icon"></i>
            <button onclick="toggleLight('${entityId}')">Zap/Vyp</button>
            <input type="color" onchange="changeLightColor(event, '${entityId}')" />
          </div>
          <input type="range" min="0" max="255" onchange="setBrightness(event, '${entityId}')" />
        `;
      } else if (entityId.startsWith("climate.")) {
        const temperatureElementId = `currentTemp_${entityId.replace(
          /\./g,
          "_"
        )}`;

        const inputElementId = `setTemp_${entityId.replace(/\./g, "_")}`;

        controlItem.innerHTML = `
          <div class="device-name">${friendlyName}</div>
          <div class="current-temperature" id="${temperatureElementId}">Načítání...</div>
          <input type="number" id="${inputElementId}" min="10" max="30" value="20" step="0.5" />
          <button onclick="setTemperature('${entityId}', '${inputElementId}')">Nastavit</button>
        `;

        thermostatIds.push({ entityId, elementId: temperatureElementId });
      }

      container.appendChild(controlItem);
    }
  });
  updateAllTemperatures();
  // Pravidelná aktualizace teploty
  setInterval(updateAllTemperatures, 60000);
  setInterval(() => {
    speechCloud.dm_send_message({ data: { type: "get_light_states" } });
  }, 120000); // každé 2min
  speechCloud.dm_send_message({
    data: { type: "get_scenes" },
  });
  document.getElementById("loadingOverlay").style.display = "none";
}

function updateLightIcon(entity) {
  const icon = document.getElementById(
    `icon_${entity.entity_id.replace(/\./g, "_")}`
  );
  if (!icon) return;

  const isOn = entity.state === "on";
  const brightness = entity.attributes.brightness || 0;
  const color = entity.attributes.rgb_color || [255, 255, 255];
  const rgb = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;

  icon.style.color = isOn ? rgb : "gray";
  icon.style.opacity = isOn ? brightness / 255 : 0.3;
}

function updateAllLights(entities) {
  entities
    .filter((e) => e.entity_id.startsWith("light."))
    .forEach(updateLightIcon);
}

function updateAllTemperatures() {
  thermostatIds.forEach(({ entityId, elementId }) => {
    speechCloud.dm_send_message({
      type: "get_temperature",
      data: {
        type: "get_temperature",
        entity_id: entityId,
        elementId: elementId,
      },
    });
  });
}

//  Zapnutí mikrofonu
function toggleMicrophone() {
  const icon = document.getElementById("microphone-icon");
  if (icon.classList.contains("fa-microphone")) {
    icon.classList.remove("fa-microphone");
    icon.classList.add("fa-microphone-slash");
    recognizing = false;
    speechCloud.dm_send_message({
      type: "toggleRec",
      data: { type: "toggleRec" },
    });
    speechCloud.asr_pause();
  } else {
    icon.classList.remove("fa-microphone-slash");
    icon.classList.add("fa-microphone");
    recognizing = true;
    speechCloud.dm_send_message({
      type: "toggleRec",
      data: { type: "toggleRec" },
    });
    speechCloud.asr_recognize();
  }
}

let ttsEnabled = false;

function toggleTTS() {
  ttsEnabled = !ttsEnabled;
  const ttsButton = document.getElementById("toggle-tts");
  const icon = ttsButton.querySelector("i");

  if (ttsEnabled) {
    icon.classList.remove("fa-volume-mute");
    icon.classList.add("fa-volume-up");
  } else {
    icon.classList.remove("fa-volume-up");
    icon.classList.add("fa-volume-mute");
  }

  speechCloud.dm_send_message({
    type: "toggleTTS",
    data: { type: "toggleTTS" },
  });
}

let dialogRunning = true;

function toggleDialog() {
  dialogRunning = !dialogRunning;
  const dialogButton = document.getElementById("dialog-toggle");
  dialogButton.textContent = dialogRunning ? "Stop dialog" : "Start dialog";

  if (dialogRunning) {
    location.reload(); // restart dialogu
  } else {
    hlog("<b>Terminating dialog</b>");
    speechCloud.terminate();
  }
}

function requestSettings() {
  speechCloud.dm_send_message({ data: { type: "settings" } });
}

function handleSettingsMessage(data) {
  openSettingsModal();
  const list = document.getElementById("friendlyList");
  list.innerHTML = "";

  const table = document.createElement("table");
  table.style.width = "100%";
  table.innerHTML = `
    <thead>
      <tr>
        <th style="text-align:left;">Entity ID</th>
        <th style="text-align:left;">Friendly Names (oddělené čárkou)</th>
      </tr>
    </thead>
    <tbody></tbody>
  `;

  const tbody = table.querySelector("tbody");

  Object.entries(data).forEach(([entityId, entry]) => {
    const row = document.createElement("tr");

    const cell1 = document.createElement("td");
    cell1.textContent = entityId;

    const cell2 = document.createElement("td");
    const input = document.createElement("input");
    input.type = "text";
    input.value = (entry.friendly_names || []).join(", ");
    input.dataset.entity = entityId;
    cell2.appendChild(input);

    row.appendChild(cell1);
    row.appendChild(cell2);
    tbody.appendChild(row);
  });

  list.appendChild(table);
}

function saveSettings() {
  const inputs = document.querySelectorAll("#friendlyList input");
  const data = {};

  inputs.forEach((input) => {
    const id = input.dataset.entity;
    const raw = input.value.trim();
    const names = raw
      .split(",")
      .map((name) => name.trim())
      .filter((name) => name.length > 0);

    if (names.length > 0) {
      data[id] = { friendly_names: names };
    }
  });

  speechCloud.dm_send_message({
    data: {
      type: "set_friendly_names",
      data: data,
    },
  });
  document.getElementById("settingsOverlay")?.remove();
}

function openSettingsModal() {
  createSettingsModal();
  const overlay = document.getElementById("settingsOverlay");
  if (overlay) overlay.style.display = "flex";
}

function closeSettingsModal(event) {
  const overlay = document.getElementById("settingsOverlay");
  if (overlay) overlay.style.display = "none";
}

function createSettingsModal() {
  if (document.getElementById("settingsOverlay")) return;

  const overlay = document.createElement("div");
  overlay.id = "settingsOverlay";
  overlay.className = "modal-overlay";
  overlay.style.display = "none";
  overlay.onclick = closeSettingsModal;

  const modal = document.createElement("div");
  modal.className = "modal";
  modal.onclick = (e) => e.stopPropagation();

  modal.innerHTML = `
    <span class="modal-close" onclick="closeSettingsModal(event)">×</span>
    <h2>Upravit názvy zařízení</h2>
    <div id="friendlyList"></div>
    <button onclick="saveSettings()">Uložit</button>
  `;

  overlay.appendChild(modal);
  document.body.appendChild(overlay);
}

function renderSceneButtons(sceneNames) {
  const mountPoint = document.getElementById("scenes");
  if (!mountPoint) {
    console.warn("Mount point #scenes nebyl nalezen.");
    return;
  }
  mountPoint.innerHTML = "";

  const wrapper = document.createElement("div");
  wrapper.id = "devicesWrapper";
  wrapper.className = "devices-wrapper";

  const title = document.createElement("div");
  title.className = "devices-title";
  title.textContent = "Scény";

  const container = document.createElement("div");
  container.id = "dynamicContainer";
  container.className = "dynamic-container";

  wrapper.appendChild(title);
  wrapper.appendChild(container);
  mountPoint.appendChild(wrapper);

  sceneNames.forEach((scene) => {
    const btn = document.createElement("button");
    btn.textContent = scene.charAt(0).toUpperCase() + scene.slice(1);
    btn.onclick = () => activateScene(scene);
    container.appendChild(btn);
  });
}

function activateScene(sceneName) {
  sendControlCommand("activate_scene", { scene: sceneName });
}

const availableEntities = [];

function storeEntitiesForScenes(entities) {
  availableEntities.length = 0;
  availableEntities.push(...entities);
}

function addSceneAction() {
  const container = document.getElementById("sceneActionsContainer");

  const wrapper = document.createElement("div");
  wrapper.className = "scene-action-block";

  const entitySelect = document.createElement("select");
  const actionSelect = document.createElement("select");
  const inputHolder = document.createElement("div");
  const deleteButton = document.createElement("button");

  deleteButton.textContent = "x";
  deleteButton.type = "button";
  deleteButton.onclick = () => wrapper.remove();

  entitySelect.innerHTML = `<option hidden selected>Vyber zařízení</option>`;
  const relevantEntities = availableEntities.filter(
    (e) =>
      e.entity_id.startsWith("light.") || e.entity_id.startsWith("climate.")
  );

  relevantEntities.forEach((e) => {
    const opt = document.createElement("option");
    opt.value = e.entity_id;
    opt.textContent = e.attributes?.friendly_name || e.entity_id;
    opt.dataset.domain = e.entity_id.split(".")[0];
    entitySelect.appendChild(opt);
  });

  actionSelect.disabled = true;
  inputHolder.className = "input-holder";

  wrapper.appendChild(entitySelect);
  wrapper.appendChild(actionSelect);
  wrapper.appendChild(inputHolder);
  wrapper.appendChild(deleteButton);
  container.appendChild(wrapper);

  entitySelect.onchange = () => {
    const domain = entitySelect.selectedOptions[0]?.dataset.domain;
    actionSelect.disabled = false;
    actionSelect.innerHTML = "";
    inputHolder.innerHTML = "";

    if (domain === "light") {
      actionSelect.innerHTML = `
        <option hidden selected>Vyber akci</option>
        <option value="on">Zapnout</option>
        <option value="off">Vypnout</option>
      `;
    } else if (domain === "climate") {
      actionSelect.innerHTML = `<option value="temperature" selected>Nastavit teplotu</option>`;
      actionSelect.disabled = true;

      const input = document.createElement("input");
      input.type = "number";
      input.placeholder = "Teplota (např. 22)";
      inputHolder.appendChild(input);
    }
  };

  actionSelect.onchange = () => {
    const domain = entitySelect.selectedOptions[0]?.dataset.domain;
    const action = actionSelect.value;
    inputHolder.innerHTML = "";

    if (domain === "light" && action === "on") {
      const brightness = document.createElement("input");
      brightness.type = "number";
      brightness.placeholder = "Jas (0–255)";
      brightness.className = "brightness";

      const color = document.createElement("input");
      color.type = "color";
      color.className = "color";

      inputHolder.appendChild(brightness);
      inputHolder.appendChild(color);
    }
  };
}

function saveScene() {
  const name = document
    .getElementById("newSceneName")
    .value.trim()
    .toLowerCase();
  const blocks = document.querySelectorAll(".scene-action-block");

  if (!name || blocks.length === 0) {
    alert("Zadejte název a alespoň jednu akci.");
    return;
  }

  const actions = [];

  blocks.forEach((block) => {
    const selects = block.querySelectorAll("select");
    const entitySelect = selects[0];
    const actionSelect = selects[1];

    const entity = entitySelect?.value;
    const action = actionSelect?.value;

    if (!entity || !action) return;

    const actionObj = { type: "control_light", entity_id: entity };

    if (action === "on") {
      actionObj.action = "on";

      const brightnessInput = block.querySelector("input.brightness");
      const colorInput = block.querySelector("input.color");
      const colorT = colorInput?.value.trim().toLowerCase();
      const colorName = getNearestColorName(colorT);
      const color = colorName?.trim();
      const brightness = brightnessInput?.value.trim();
      if (brightness) {
        const val = parseInt(brightness);
        if (!isNaN(val)) {
          actionObj.brightness = val;
        }
      }

      if (color) {
        actionObj.color = color.replace("#", "").toLowerCase();
      }
    } else if (action === "off") {
      actionObj.action = "off";
    } else if (action === "temperature") {
      const input = block.querySelector("input[type='number']");
      const temp = input?.value.trim();
      if (temp) {
        actionObj.type = "set_temperature";
        actionObj.temperature = parseFloat(temp);
      } else return;
    }

    actions.push(actionObj);
  });

  if (actions.length === 0) {
    alert("Nebyla zadána žádná validní akce.");
    return;
  }

  sendControlCommand("save_scene", { name, actions });
}

function openSceneModal() {
  let overlay = document.getElementById("sceneModalOverlay");
  if (overlay) {
    overlay.style.display = "flex";
    return;
  }

  overlay = document.createElement("div");
  overlay.id = "sceneModalOverlay";
  overlay.className = "modal-overlay";
  overlay.style.display = "flex";

  const modal = document.createElement("div");
  modal.className = "modal";

  const closeBtn = document.createElement("span");
  closeBtn.className = "modal-close";
  closeBtn.innerHTML = "&times;";
  closeBtn.onclick = () => overlay.remove();

  modal.innerHTML = `
    <h3 style="margin-top: 0;">Vytvořit novou scénu</h3>
    <input id="newSceneName" placeholder="Název scény" style="width:100%;margin-bottom:10px;" />
    <div id="sceneActionsContainer"></div>
    <div style="margin-top:10px; display:flex; flex-wrap:wrap; gap:10px;">
      <button onclick="addSceneAction()">Přidat akci</button>
      <button onclick="saveScene(); closeSceneModal();">Uložit scénu</button>
    </div>
  `;

  modal.appendChild(closeBtn);
  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  document.getElementById("sceneActionsContainer").innerHTML = "";
  document.getElementById("newSceneName").value = "";
}
function closeSceneModal() {
  const modal = document.getElementById("sceneModalOverlay");
  if (modal) modal.remove();
}

function requestGrammar() {
  speechCloud.dm_send_message({ data: { type: "get_grammar" } });
}

function handleGrammarMessage(data) {
  openGrammarModal();

  const list = document.getElementById("grammarList");
  list.innerHTML = "";

  Object.entries(data).forEach(([slotName, entries]) => {
    const slotSection = document.createElement("div");
    slotSection.className = "slot-section";

    const slotTitle = document.createElement("h4");
    slotTitle.textContent = slotName;
    slotSection.appendChild(slotTitle);

    Object.entries(entries).forEach(([value, synonyms]) => {
      const row = document.createElement("div");
      row.className = "grammar-row";
      const label = document.createElement("label");
      label.textContent = value;
      const input = document.createElement("input");
      input.type = "text";
      input.value = synonyms.join(", ");
      input.dataset.slot = slotName;
      input.dataset.value = value;

      row.appendChild(label);
      row.appendChild(input);
      slotSection.appendChild(row);
    });

    list.appendChild(slotSection);
  });
}

function openGrammarModal() {
  if (document.getElementById("grammarOverlay")) return;

  const overlay = document.createElement("div");
  overlay.id = "grammarOverlay";
  overlay.className = "modal-overlay";
  overlay.style.display = "flex";
  overlay.onclick = () => overlay.remove();

  const modal = document.createElement("div");
  modal.className = "modal";
  modal.onclick = (e) => e.stopPropagation();

  modal.innerHTML = `
    <span class="modal-close" onclick="document.getElementById('grammarOverlay').remove()">×</span>
    <h2>Upravit gramatiku</h2>
    <div id="grammarList"></div>
    <button onclick="saveGrammar()">Uložit</button>
  `;

  overlay.appendChild(modal);
  document.body.appendChild(overlay);
}
function saveGrammar() {
  const inputs = document.querySelectorAll("#grammarList input");
  const grammar = {};

  inputs.forEach((input) => {
    const slot = input.dataset.slot;
    const value = input.dataset.value;
    const raw = input.value.trim();

    const synonyms = raw
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    if (!grammar[slot]) {
      grammar[slot] = {};
    }

    grammar[slot][value] = synonyms;
  });

  speechCloud.dm_send_message({
    data: {
      type: "set_grammar",
      data: grammar,
    },
  });

  document.getElementById("grammarOverlay")?.remove();
}
