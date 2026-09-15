const CONFIG = Object.freeze({
  DISPATCH_URL: 'https://api.github.com/repos/FouaadAI/BRW_CHeckin/dispatches',
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
});

const COOLDOWN_MS = 10000;
let lastSubmitTime = 0;

function assertConfigurationLoaded() {
  if (!window.APP_PIN || !window.GH_PAT) {
    throw new Error(
      'Konfiguration fehlt. Bitte config.js aus config.example.js erstellen.'
    );
  }
  return true;
}

async function loadJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Daten konnten nicht geladen werden: ${url}`);
  }
  return response.json();
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

async function initializeForm() {
  const [employees, stations] = await Promise.all([
    loadJson('employees.json'),
    loadJson('stations.json'),
  ]);

  state = Object.freeze({
    ...state,
    employees,
    stations,
  });

  populateDatalist(dom.nameList, employees);
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

async function sendCheckin(payload) {
  const response = await fetch(CONFIG.DISPATCH_URL, {
    method: 'POST',
    headers: {
      Accept: 'application/vnd.github+json',
      Authorization: `Bearer ${window.GH_PAT}`,
      'Content-Type': 'application/json',
      'X-GitHub-Api-Version': '2022-11-28',
    },
    body: JSON.stringify({
      event_type: 'checkin_event',
      client_payload: payload,
    }),
  });

  if (!response.ok) {
    throw new Error('Fehler beim Senden. Bitte erneut versuchen.');
  }
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

function handlePinSubmit(event) {
  event.preventDefault();
  clearMessage(dom.pinMessage);

  const pin = dom.pinInput.value.trim();

  if (!isValidPinFormat(pin)) {
    showMessage(dom.pinMessage, `PIN muss ${CONFIG.PIN_LENGTH} Ziffern haben.`);
    return;
  }

  if (pin !== window.APP_PIN) {
    showMessage(dom.pinMessage, 'Falscher PIN.');
    return;
  }

  showFormScreen();
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

    await sendCheckin({
      pin: window.APP_PIN,
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
    assertConfigurationLoaded();
    await initializeForm();
    dom.pinForm.addEventListener('submit', handlePinSubmit);
    dom.checkinForm.addEventListener('submit', handleCheckinSubmit);
  } catch (error) {
    showMessage(dom.pinMessage, error.message);
  }
}

initialize();
