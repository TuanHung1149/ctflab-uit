/**
 * CTFLab challenge view script - CTFd 3.7.x compatible.
 */

var API_BASE = "/api/ctflab";
var pollTimer = null;
var currentPassword = null;

function ctflabCsrf() {
  return init.csrfNonce || "";
}

function ctflabUserName() {
  return init.userName || "user";
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

function ctflabCopyPassword() {
  if (!currentPassword) return;
  navigator.clipboard.writeText(currentPassword).then(function() {
    var btn = document.getElementById("btn-copy-pass");
    if (btn) { btn.innerHTML = '<i class="fas fa-check"></i>'; setTimeout(function() { btn.innerHTML = '<i class="fas fa-copy"></i>'; }, 1500); }
  });
}

function ctflabRenderNoInstance() {
  var el = document.getElementById("instance-status");
  if (el) {
    el.innerHTML =
      '<div style="text-align:center; padding: 20px;">' +
      '<i class="fas fa-server" style="font-size: 32px; color: #30363d; margin-bottom: 8px;"></i>' +
      '<p style="color: #8b949e; margin: 8px 0 0;">No running instance</p>' +
      '</div>';
  }

  var actions = document.getElementById("instance-actions");
  if (actions) {
    actions.style.display = "block";
    actions.innerHTML =
      '<button class="btn btn-block" id="btn-launch" style="background: linear-gradient(90deg, #238636, #2ea043); color: #fff; border: none; border-radius: 6px; padding: 10px; font-size: 14px; font-weight: 600; cursor: pointer; width: 100%;">' +
      '<i class="fas fa-play"></i> Start Machine</button>';
    document.getElementById("btn-launch").addEventListener("click", ctflabLaunchInstance);
  }

  var guide = document.getElementById("instance-guide");
  if (guide) guide.style.display = "none";

  // Set username in VPN filename
  var confName = document.getElementById("vpn-conf-name");
  if (confName) confName.textContent = ctflabUserName();
  var vpnFile = document.getElementById("vpn-filename");
  if (vpnFile) vpnFile.textContent = ctflabUserName() + ".conf";
}

function ctflabRenderInstance(inst) {
  var statusColor = "#238636";
  var statusText = "Running";
  var statusIcon = "fa-circle";
  if (inst.status === "starting") { statusColor = "#d29922"; statusText = "Starting..."; statusIcon = "fa-spinner fa-spin"; }
  else if (inst.status !== "running") { statusColor = "#6e7681"; statusText = inst.status; }

  var el = document.getElementById("instance-status");
  if (el) {
    el.innerHTML =
      '<div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">' +
        '<div style="display: flex; align-items: center; gap: 12px;">' +
          '<span style="display:inline-flex; align-items:center; gap:6px; background:' + statusColor + '22; color:' + statusColor + '; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:600;">' +
            '<i class="fas ' + statusIcon + '" style="font-size:8px;"></i> ' + statusText +
          '</span>' +
          '<span style="color: #e6edf3; font-size: 14px;">' +
            '<i class="fas fa-network-wired" style="color: #58a6ff; margin-right: 4px;"></i>' +
            '<code style="background:#0d1117; padding:2px 8px; border-radius:4px; color:#7ee787; font-size:13px; font-weight:bold;">' + (inst.container_ip || "pending") + '</code>' +
          '</span>' +
        '</div>' +
        '<span style="color: #8b949e; font-size: 12px;"><i class="fas fa-clock"></i> ' + ctflabTimeRemaining(inst.expires_at) + '</span>' +
      '</div>';
  }

  var html = '<div style="display: flex; gap: 8px;">';
  if (inst.status === "running") {
    html += '<button class="btn btn-sm" onclick="ctflabResetInstance(' + inst.id + ')" style="background:#0d1117; color:#d29922; border:1px solid #d29922; border-radius:4px; padding:4px 12px; font-size:12px; cursor:pointer;"><i class="fas fa-redo"></i> Reset</button>';
  }
  html += '<button class="btn btn-sm" onclick="ctflabDestroyInstance(' + inst.id + ')" style="background:#0d1117; color:#f85149; border:1px solid #f85149; border-radius:4px; padding:4px 12px; font-size:12px; cursor:pointer;"><i class="fas fa-stop"></i> Stop Machine</button>';
  html += '</div>';

  var actions = document.getElementById("instance-actions");
  if (actions) { actions.style.display = "block"; actions.innerHTML = html; }

  // Show guide
  var guide = document.getElementById("instance-guide");
  if (guide) guide.style.display = "block";

  // Set dynamic values
  var sshCmd = document.getElementById("ssh-command");
  if (sshCmd && inst.container_ip) sshCmd.textContent = "ssh taylor@" + inst.container_ip;

  var confName = document.getElementById("vpn-conf-name");
  if (confName) confName.textContent = ctflabUserName();
  var vpnFile = document.getElementById("vpn-filename");
  if (vpnFile) vpnFile.textContent = ctflabUserName() + ".conf";

  // Set password
  currentPassword = inst.ssh_password || null;
  var passEl = document.getElementById("ssh-password");
  if (passEl && inst.ssh_password) {
    passEl.textContent = inst.ssh_password;
    passEl.title = "Click to copy";
    passEl.onclick = ctflabCopyPassword;
  }
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
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Launching...';
    btn.style.opacity = "0.7";
  }

  var xhr = new XMLHttpRequest();
  xhr.open("POST", API_BASE + "/instances");
  xhr.setRequestHeader("Content-Type", "application/json");
  xhr.setRequestHeader("CSRF-Token", ctflabCsrf());
  xhr.onload = function () { ctflabFetchStatus(); };
  xhr.onerror = function () { ctflabFetchStatus(); };
  xhr.send(JSON.stringify({ challenge_id: challengeId }));
}

function ctflabDestroyInstance(id) {
  if (!confirm("Stop your running instance? You will lose current progress.")) return;
  var xhr = new XMLHttpRequest();
  xhr.open("DELETE", API_BASE + "/instances/" + id);
  xhr.setRequestHeader("Content-Type", "application/json");
  xhr.setRequestHeader("CSRF-Token", ctflabCsrf());
  xhr.onload = function () { ctflabFetchStatus(); };
  xhr.send();
}

function ctflabResetInstance(id) {
  if (!confirm("Reset instance to initial state? Services will restart.")) return;
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
