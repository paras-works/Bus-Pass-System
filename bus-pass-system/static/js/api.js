// =====================================================================
// api.js
// -----------------------------------------------------------------
// One small helper, loaded by every page, so every page talks to the
// Flask backend the exact same way:
//
//     HTML page -> apiRequest() -> fetch() -> Flask route -> MySQL
//                                                |
//     HTML page <-------- JSON response  <-------
//
// `credentials: "include"` on every call is what makes the browser
// send Flask's session cookie back on every request after login - this
// is how the backend knows "who" is calling without you having to
// pass the user id around yourself.
//
// (The page URLs below - "/login", "/admin/login", "/" - are Flask page
// routes defined in app.py. They replaced the old "login.html" style links.)
// =====================================================================

async function apiRequest(path, method = "GET", body = null) {
  const options = {
    method: method,
    credentials: "include",
  };

  if (body instanceof FormData) {
    // Uploading a file (e.g. profile photo). Do NOT set Content-Type
    // manually here - the browser adds the correct multipart boundary.
    options.body = body;
  } else if (body !== null) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }

  const response = await fetch(path, options);

  let data;
  try {
    data = await response.json();
  } catch (err) {
    data = { success: false, message: "Unexpected server response" };
  }

  data.status = response.status;
  return data;
}

// ---------------------------------------------------------------
// Every STUDENT page calls this once when it loads. If nobody is
// logged in (or an admin is logged in), it sends them back to the
// login page instead of showing protected content.
// ---------------------------------------------------------------
async function requireStudentLogin() {
  const result = await apiRequest("/api/me");

  if (!result.success) {
    window.location.href = "/login";
    return null;
  }

  if (result.user.role !== "student") {
    window.location.href = "/admin/login";
    return null;
  }

  const nameEl = document.getElementById("username");
  if (nameEl) nameEl.innerText = result.user.name;

  return result.user;
}

// Same idea, for ADMIN pages.
async function requireAdminLogin() {
  const result = await apiRequest("/api/me");

  if (!result.success || result.user.role !== "admin") {
    window.location.href = "/admin/login";
    return null;
  }

  return result.user;
}

async function logout() {
  await apiRequest("/api/logout", "POST");
  window.location.href = "/";
}

// Turns "2026-10-01" into "01 Oct 2026" for nicer display in tables/cards.
function formatDate(isoDateString) {
  if (!isoDateString) return "-";
  const parts = isoDateString.split("-");
  if (parts.length !== 3) return isoDateString;
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${parts[2]} ${months[parseInt(parts[1], 10) - 1]} ${parts[0]}`;
}

// Makes text safe to put inside innerHTML. Names, emails, addresses and so
// on are typed by users, so they must never be inserted as raw HTML
// (otherwise a name like <script>... would run in the admin's browser).
function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
