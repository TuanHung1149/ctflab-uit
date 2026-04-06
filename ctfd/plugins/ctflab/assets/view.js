/**
 * CTFLab challenge view script - CTFd 3.7.x compatible.
 * Uses CTFd._internal.challenge pattern.
 */

var API_BASE = "/api/ctflab";
var pollTimer = null;

function ctflabCsrf() {
  return init.csrfNonce || "";
}

function ctflabHeaders() {
  return {
    "Content-Type": "application/json",
    "CSRF-Token": ctflabCsrf(),
  };
}

function ctflabTimeRemaining(expiresAt) {
  if (!expiresAt) return "N/A";
  var diff = new Date(expiresAt) - new Date();
  if (diff <= 0) return "Expired";
  var h = Math.floor(diff / 3600000);
  var m = Math.floor((diff % 3600000) / 60000);
  var s = Math.floor((diff % 60000) / 1000);
  return h + "h " + m + "m " + s + "s";
}

function ctflabRenderNoInstance() {
  var el = document.getElementById("instance-status");
  if (el) el.innerHTML = '<p class="text-muted">No running instance.</p>';
  var actions = document.getElementById("instance-actions");
  if (actions) {
    actions.style.display = "block";
    actions.innerHTML =
      '<button class="btn btn-success btn-sm" id="btn-launch">' +
      '<i class="fas fa-play"></i> Launch Instance</button>';
    var btn = document.getElementById("btn-launch");
    if (btn) btn.addEventListener("click", ctflabLaunchInstance);
  }
}

function ctflabRenderInstance(inst) {
  var badge = "";
  if (inst.status === "running") badge = '<span class="badge badge-success">Running</span>';
  else if (inst.status === "starting") badge = '<span class="badge badge-warning">Starting</span>';
  else badge = '<span class="badge badge-secondary">' + inst.status + "</span>";

  var el = document.getElementById("instance-status");
  if (el) {
    el.innerHTML =
      "<p>" + badge +
      '  <strong>IP:</strong> <code>' + (inst.container_ip || "pending") + "</code>" +
      '  <strong>Expires:</strong> ' + ctflabTimeRemaining(inst.expires_at) + "</p>";
  }

  var html = "";
  if (inst.has_vpn) {
    html += '<a class="btn btn-info btn-sm mr-1" href="' + API_BASE + "/instances/" + inst.id + '/vpn" target="_blank"><i class="fas fa-download"></i> VPN</a>';
  }
  if (inst.status === "running") {
    html += '<button class="btn btn-warning btn-sm mr-1" onclick="ctflabResetInstance(' + inst.id + ')"><i class="fas fa-redo"></i> Reset</button>';
  }
  html += '<button class="btn btn-danger btn-sm" onclick="ctflabDestroyInstance(' + inst.id + ')"><i class="fas fa-trash"></i> Destroy</button>';

  var actions = document.getElementById("instance-actions");
  if (actions) { actions.style.display = "block"; actions.innerHTML = html; }
}

function ctflabFetchStatus() {
  var dockerImage = "";
  var el = document.getElementById("ctflab-docker-image");
  if (el) dockerImage = el.value || "";

  var url = API_BASE + "/instances";
  if (dockerImage) url += "?docker_image=" + encodeURIComponent(dockerImage);

  var xhr = new XMLHttpRequest();
  xhr.open("GET", url);
  xhr.setRequestHeader("CSRF-Token", ctflabCsrf());
  xhr.onload = function () {
    try {
      var resp = JSON.parse(xhr.responseText);
      if (resp.instance) ctflabRenderInstance(resp.instance);
      else ctflabRenderNoInstance();
    } catch (e) {
      ctflabRenderNoInstance();
    }
  };
  xhr.onerror = function () { ctflabRenderNoInstance(); };
  xhr.send();
}

function ctflabLaunchInstance() {
  var challengeId = parseInt(document.getElementById("challenge-id").value);
  if (!challengeId) return;

  var btn = document.getElementById("btn-launch");
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Launching...'; }

  var xhr = new XMLHttpRequest();
  xhr.open("POST", API_BASE + "/instances");
  xhr.setRequestHeader("Content-Type", "application/json");
  xhr.setRequestHeader("CSRF-Token", ctflabCsrf());
  xhr.onload = function () { ctflabFetchStatus(); };
  xhr.onerror = function () { ctflabFetchStatus(); };
  xhr.send(JSON.stringify({ challenge_id: challengeId }));
}

function ctflabDestroyInstance(id) {
  if (!confirm("Destroy your running instance?")) return;
  var xhr = new XMLHttpRequest();
  xhr.open("DELETE", API_BASE + "/instances/" + id);
  xhr.setRequestHeader("Content-Type", "application/json");
  xhr.setRequestHeader("CSRF-Token", ctflabCsrf());
  xhr.onload = function () { ctflabFetchStatus(); };
  xhr.send();
}

function ctflabResetInstance(id) {
  if (!confirm("Reset instance to initial state?")) return;
  var xhr = new XMLHttpRequest();
  xhr.open("POST", API_BASE + "/instances/" + id + "/reset");
  xhr.setRequestHeader("Content-Type", "application/json");
  xhr.setRequestHeader("CSRF-Token", ctflabCsrf());
  xhr.onload = function () { ctflabFetchStatus(); };
  xhr.send();
}

// CTFd 3.7 challenge type interface
CTFd._internal.challenge.data = undefined;
CTFd._internal.challenge.renderer = null;

CTFd._internal.challenge.preRender = function () {};
CTFd._internal.challenge.render = null;

CTFd._internal.challenge.postRender = function () {
  ctflabFetchStatus();
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(ctflabFetchStatus, 5000);
};

CTFd._internal.challenge.submit = function (preview) {
  var challenge_id = parseInt(CTFd.lib.$("#challenge-id").val());
  var submission = CTFd.lib.$("#challenge-input").val();

  var body = { challenge_id: challenge_id, submission: submission };
  var params = {};
  if (preview) params["preview"] = true;

  return CTFd.api.post_challenge_attempt(params, body).then(function (response) {
    return response;
  });
};
