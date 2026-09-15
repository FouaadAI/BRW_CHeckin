/**
 * Cloudflare Worker proxy for the BRW Check-in app.
 *
 * This worker is the ONLY component that holds the GitHub PAT (GH_PAT) and
 * the application PIN (APP_PIN). The static frontend never sees these values.
 *
 * Endpoints:
 *   POST /employees  - validates PIN and returns the employee whitelist
 *   POST /checkin    - validates PIN, employee, station, shift, geofencing and
 *                      forwards the check-in to GitHub Repository Dispatch API
 *
 * Required Cloudflare Worker environment variables/secrets:
 *   APP_PIN              - 6-digit numeric PIN
 *   GH_PAT               - GitHub Personal Access Token (repo scope or fine-grained Actions:write)
 *   DISPATCH_SECRET      - shared secret included in the dispatch payload so the
 *                          GitHub Actions workflow can verify the request origin
 *   EMPLOYEES_JSON       - JSON array of employee names (e.g. ["Max Mustermann"])
 *   REPO_OWNER           - GitHub owner of the check-in repository
 *   REPO_NAME            - GitHub repository name
 *   ALLOWED_ORIGIN       - optional CORS origin of the GitHub Pages frontend
 *   MAX_DISTANCE_METERS  - optional geofencing radius (default 200)
 */

const EARTH_RADIUS_METERS = 6_371_000;
const DEFAULT_MAX_DISTANCE_METERS = 200;
const VALID_SHIFTS = Object.freeze(["Früh", "Spät", "Nacht"]);

function getEnv(env) {
  const required = [
    "APP_PIN",
    "GH_PAT",
    "DISPATCH_SECRET",
    "EMPLOYEES_JSON",
    "REPO_OWNER",
    "REPO_NAME",
  ];
  const missing = required.filter((key) => !env[key]);
  if (missing.length > 0) {
    throw new Error(`Missing worker env/secrets: ${missing.join(", ")}`);
  }
  return env;
}

function corsHeaders(env, requestOrigin) {
  const allowedOrigin = env.ALLOWED_ORIGIN || "*";
  return {
    "Access-Control-Allow-Origin": allowedOrigin === "*" ? "*" : requestOrigin || allowedOrigin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function haversine(lat1, lng1, lat2, lng2) {
  const toRad = (value) => (value * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) *
      Math.cos(toRad(lat2)) *
      Math.sin(dLng / 2) ** 2;
  return EARTH_RADIUS_METERS * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

async function loadStations(env) {
  const url = `https://raw.githubusercontent.com/${env.REPO_OWNER}/${env.REPO_NAME}/main/stations.json`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Could not load stations.json: ${response.status}`);
  }
  return response.json();
}

function loadEmployees(env) {
  try {
    const parsed = JSON.parse(env.EMPLOYEES_JSON);
    if (!Array.isArray(parsed)) {
      throw new Error("EMPLOYEES_JSON must be a JSON array");
    }
    return parsed;
  } catch (error) {
    throw new Error(`Invalid EMPLOYEES_JSON: ${error.message}`);
  }
}

function isValidPin(pin) {
  return typeof pin === "string" && /^\d{6}$/.test(pin);
}

function isNumeric(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function jsonResponse(body, status, env, requestOrigin) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders(env, requestOrigin) },
  });
}

async function handleEmployees(request, env) {
  const requestOrigin = request.headers.get("Origin") || undefined;

  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: corsHeaders(env, requestOrigin),
    });
  }

  if (request.method !== "POST") {
    return jsonResponse({ error: "Method not allowed" }, 405, env, requestOrigin);
  }

  const body = await request.json().catch(() => ({}));

  if (!isValidPin(body.pin)) {
    return jsonResponse({ error: "Ungültige PIN" }, 400, env, requestOrigin);
  }

  if (body.pin !== env.APP_PIN) {
    return jsonResponse({ error: "Falscher PIN" }, 401, env, requestOrigin);
  }

  const employees = loadEmployees(env);
  return jsonResponse({ employees }, 200, env, requestOrigin);
}

async function handleCheckin(request, env) {
  const requestOrigin = request.headers.get("Origin") || undefined;

  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: corsHeaders(env, requestOrigin),
    });
  }

  if (request.method !== "POST") {
    return jsonResponse({ error: "Method not allowed" }, 405, env, requestOrigin);
  }

  const body = await request.json().catch(() => ({}));

  if (!isValidPin(body.pin)) {
    return jsonResponse({ error: "Ungültige PIN" }, 400, env, requestOrigin);
  }

  if (body.pin !== env.APP_PIN) {
    return jsonResponse({ error: "Falscher PIN" }, 401, env, requestOrigin);
  }

  const employees = loadEmployees(env);
  if (!employees.includes(body.name)) {
    return jsonResponse({ error: "Ungültiger Mitarbeiter" }, 400, env, requestOrigin);
  }

  const stations = await loadStations(env);
  const station = stations.find((s) => s.name === body.station);
  if (!station) {
    return jsonResponse({ error: "Ungültige Station" }, 400, env, requestOrigin);
  }

  if (!VALID_SHIFTS.includes(body.shift)) {
    return jsonResponse({ error: "Ungültige Schicht" }, 400, env, requestOrigin);
  }

  if (!isNumeric(body.latitude) || !isNumeric(body.longitude)) {
    return jsonResponse({ error: "Ungültige Koordinaten" }, 400, env, requestOrigin);
  }

  const maxDistance = parseInt(env.MAX_DISTANCE_METERS || DEFAULT_MAX_DISTANCE_METERS, 10);
  const recomputedDistance = haversine(
    body.latitude,
    body.longitude,
    station.lat,
    station.lng,
  );

  if (recomputedDistance > maxDistance) {
    return jsonResponse(
      { error: `Du bist ${Math.round(recomputedDistance)} Meter entfernt` },
      403,
      env,
      requestOrigin,
    );
  }

  const dispatchPayload = {
    event_type: "checkin_event",
    client_payload: {
      dispatch_secret: env.DISPATCH_SECRET,
      name: body.name,
      station: body.station,
      shift: body.shift,
      latitude: body.latitude,
      longitude: body.longitude,
      distance_m: Math.round(recomputedDistance),
      timestamp: body.timestamp || new Date().toISOString(),
    },
  };

  const githubUrl = `https://api.github.com/repos/${env.REPO_OWNER}/${env.REPO_NAME}/dispatches`;
  const githubResponse = await fetch(githubUrl, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${env.GH_PAT}`,
      "Content-Type": "application/json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify(dispatchPayload),
  });

  if (!githubResponse.ok) {
    const text = await githubResponse.text();
    throw new Error(`GitHub dispatch failed ${githubResponse.status}: ${text}`);
  }

  return new Response(null, {
    status: 204,
    headers: corsHeaders(env, requestOrigin),
  });
}

export default {
  async fetch(request, env) {
    try {
      const safeEnv = getEnv(env);
      const url = new URL(request.url);

      if (url.pathname === "/employees") {
        return handleEmployees(request, safeEnv);
      }

      if (url.pathname === "/checkin") {
        return handleCheckin(request, safeEnv);
      }

      return jsonResponse({ error: "Not found" }, 404, safeEnv);
    } catch (error) {
      // Never leak internal details to the client.
      console.error(error);
      return new Response(
        JSON.stringify({ error: "Serverfehler" }),
        {
          status: 500,
          headers: { "Content-Type": "application/json" },
        },
      );
    }
  },
};
