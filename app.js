const CONFIG = Object.freeze({
  MAX_DISTANCE_METERS: 200,
  EARTH_RADIUS_METERS: 6_371_000,
  PIN_LENGTH: 6,
});

const SHIFT_OPTIONS = Object.freeze(['Früh', 'Spät', 'Nacht']);

const dom = Object.freeze({
  pinScreen: document.getElementById('pin-screen'),
  formScreen: document.getElementById('form-screen'),
  pinForm: document.getElementById('pin-form'),
  pinInput: document.getElementById('pin'),
  pinMessage: document.getElementById('pin-message'),
  checkinForm: document.getElementById('checkin-form'),
  nameInput: document.getElementById('name'),
  nameList: document.getElementById('name-list'),
  stationInput: document.getElementById('station'),
  stationList: document.getElementById('station-list'),
  shiftSelect: document.getElementById('shift'),
  submitBtn: document.getElementById('submit-btn'),
  formMessage: document.getElementById('form-message'),
});

let state = Object.freeze({
  employees: [],
  stations: [],
  pin: '',
});

const COOLDOWN_MS = 10000;
let lastSubmitTime = 0;

function getProxyUrl() {
  if (!window.PROXY_URL) {
    throw new Error(
      'Konfiguration fehlt. Bitte config.js aus config.example.js erstellen und PROXY_URL setzen.'
    );
  }
  return window.PROXY_URL.replace(/\/$/, '');
}

async function loadJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Daten konnten nicht geladen werden: ${url}`);
  }
  return response.json();
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const text = await response.text().catch(() => '');
  if (!response.ok) {
    let message = 'Fehler beim Senden. Bitte erneut versuchen.';
    try {
      const parsed = JSON.parse(text);
      if (parsed.error) message = parsed.error;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  return text ? JSON.parse(text) : null;
}

function populateDatalist(datalistElement, optionValues) {
  const fragment = document.createDocumentFragment();

  optionValues.forEach((value) => {
    const option = document.createElement('option');
    option.value = value;
    fragment.appendChild(option);
  });

  datalistElement.innerHTML = '';
  datalistElement.appendChild(fragment);
}

async function loadStations() {
  const stations = await loadJson('stations.json');
  state = Object.freeze({ ...state, stations });
  populateDatalist(
    dom.stationList,
    stations.map((station) => station.name)
  );
}

function isValidPinFormat(pin) {
  return /^\d{6}$/.test(pin);
}

function isValidEmployee(name) {
  return state.employees.includes(name);
}

function isValidStation(name) {
  return state.stations.some((station) => station.name === name);
}

function findStationByName(name) {
  return state.stations.find((station) => station.name === name);
}

function toRadians(degrees) {
  return (degrees * Math.PI) / 180;
}

function calculateDistance(lat1, lng1, lat2, lng2) {
  const φ1 = toRadians(lat1);
  const φ2 = toRadians(lat2);
  const deltaPhi = toRadians(lat2 - lat1);
  const deltaLambda = toRadians(lng2 - lng1);

  const a =
    Math.sin(deltaPhi / 2) * Math.sin(deltaPhi / 2) +
    Math.cos(φ1) *
      Math.cos(φ2) *
      Math.sin(deltaLambda / 2) *
      Math.sin(deltaLambda / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return CONFIG.EARTH_RADIUS_METERS * c;
}

function getCurrentPosition() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('GPS wird von diesem Gerät nicht unterstützt. Check-in blockiert.'));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      resolve,
      (error) => {
        switch (error.code) {
          case error.PERMISSION_DENIED:
            reject(new Error('GPS-Zugriff abgelehnt. Check-in blockiert.'));
            break;
          case error.POSITION_UNAVAILABLE:
            reject(new Error('GPS-Position nicht verfügbar. Check-in blockiert.'));
            break;
          case error.TIMEOUT:
            reject(new Error('GPS-Timeout. Bitte erneut versuchen.'));
            break;
          default:
            reject(new Error('Unbekannter GPS-Fehler. Check-in blockiert.'));
        }
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  });
}

function showMessage(element, message, type = 'error') {
  element.textContent = message;
  element.className = type === 'success' ? 'message success' : 'message';
}

function clearMessage(element) {
  element.textContent = '';
  element.className = 'message';
}

function showFormScreen() {
  dom.pinScreen.hidden = true;
  dom.formScreen.hidden = false;
}

async function handlePinSubmit(event) {
  event.preventDefault();
  clearMessage(dom.pinMessage);

  const pin = dom.pinInput.value.trim();

  if (!isValidPinFormat(pin)) {
    showMessage(dom.pinMessage, `PIN muss ${CONFIG.PIN_LENGTH} Ziffern haben.`);
    return;
  }

  try {
    const proxyUrl = getProxyUrl();
    const { employees } = await postJson(`${proxyUrl}/employees`, { pin });

    if (!Array.isArray(employees) || employees.length === 0) {
      throw new Error('Keine Mitarbeiter geladen.');
    }

    state = Object.freeze({ ...state, employees, pin });
    populateDatalist(dom.nameList, employees);
    await loadStations();
    showFormScreen();
  } catch (error) {
    showMessage(dom.pinMessage, error.message);
  }
}

function isOnCooldown() {
  const remaining = COOLDOWN_MS - (Date.now() - lastSubmitTime);
  return remaining > 0;
}

function setSubmitCooldown() {
  lastSubmitTime = Date.now();
  dom.submitBtn.disabled = true;
  setTimeout(() => {
    dom.submitBtn.disabled = false;
  }, COOLDOWN_MS);
}

async function handleCheckinSubmit(event) {
  event.preventDefault();
  clearMessage(dom.formMessage);

  if (isOnCooldown()) {
    showMessage(dom.formMessage, 'Bitte warte einen Moment vor dem nächsten Check-in.');
    return;
  }

  const name = dom.nameInput.value.trim();
  const stationName = dom.stationInput.value.trim();
  const shift = dom.shiftSelect.value;

  if (!isValidEmployee(name)) {
    showMessage(dom.formMessage, 'Bitte wähle einen gültigen Namen.');
    return;
  }

  if (!isValidStation(stationName)) {
    showMessage(dom.formMessage, 'Bitte wähle eine gültige Station.');
    return;
  }

  if (!SHIFT_OPTIONS.includes(shift)) {
    showMessage(dom.formMessage, 'Bitte wähle eine Schicht.');
    return;
  }

  setSubmitCooldown();

  try {
    const position = await getCurrentPosition();
    const station = findStationByName(stationName);
    const distance = calculateDistance(
      position.coords.latitude,
      position.coords.longitude,
      station.lat,
      station.lng
    );

    if (distance > CONFIG.MAX_DISTANCE_METERS) {
      showMessage(dom.formMessage, `Du bist ${Math.round(distance)} Meter entfernt.`);
      return;
    }

    const proxyUrl = getProxyUrl();
    await postJson(`${proxyUrl}/checkin`, {
      pin: state.pin,
      name,
      station: stationName,
      shift,
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
      distance_m: Math.round(distance),
      timestamp: new Date().toISOString(),
    });

    showMessage(dom.formMessage, 'Check-in erfolgreich gesendet.', 'success');
    dom.checkinForm.reset();
  } catch (error) {
    showMessage(dom.formMessage, error.message);
  }
}

async function initialize() {
  try {
    getProxyUrl();
    dom.pinForm.addEventListener('submit', handlePinSubmit);
    dom.checkinForm.addEventListener('submit', handleCheckinSubmit);
  } catch (error) {
    showMessage(dom.pinMessage, error.message);
  }
}

initialize();
