/**
 * CTFLab challenge view script.
 *
 * Handles instance lifecycle (launch / destroy / reset),
 * VPN download, status polling, and flag submission.
 */

CTFd.plugin.run((_CTFd) => {
  const $ = _CTFd.lib.$;
  const API_BASE = "/api/ctflab";

  let pollTimer = null;
  let currentChallengeId = null;

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function csrfToken() {
    return $('meta[name="csrf-token"]').attr("content") || CTFd.config.csrfNonce || "";
  }

  function apiHeaders() {
    return {
      "Content-Type": "application/json",
      "CSRF-Token": csrfToken(),
    };
  }

  function formatTimeRemaining(expiresAt) {
    if (!expiresAt) return "N/A";
    const diff = new Date(expiresAt) - new Date();
    if (diff <= 0) return "Expired";
    const hours = Math.floor(diff / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    return hours + "h " + minutes + "m " + seconds + "s";
  }

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------

  function renderNoInstance() {
    $("#instance-status").html(
      '<p class="text-muted">No running instance.</p>'
    );
    $("#instance-actions")
      .show()
      .html(
        '<button class="btn btn-success btn-sm" id="btn-launch">' +
        '<i class="fas fa-play"></i> Launch Instance</button>'
      );
    $("#btn-launch").on("click", launchInstance);
  }

  function renderInstance(inst) {
    let statusBadge = "";
    if (inst.status === "running") {
      statusBadge = '<span class="badge bg-success">Running</span>';
    } else if (inst.status === "starting") {
      statusBadge = '<span class="badge bg-warning text-dark">Starting</span>';
    } else {
      statusBadge = '<span class="badge bg-secondary">' + inst.status + "</span>";
    }

    const timeLeft = formatTimeRemaining(inst.expires_at);

    $("#instance-status").html(
      "<p>" +
      statusBadge +
      '  <strong>IP:</strong> <code>' +
      (inst.container_ip || "pending") +
      "</code>" +
      '  <strong>Expires in:</strong> <span id="time-remaining">' +
      timeLeft +
      "</span></p>"
    );

    let actions = "";

    if (inst.has_vpn) {
      actions +=
        '<a class="btn btn-info btn-sm me-1" href="' +
        API_BASE +
        "/instances/" +
        inst.id +
        '/vpn" target="_blank">' +
        '<i class="fas fa-download"></i> Download VPN</a>';
    }

    if (inst.status === "running") {
      actions +=
        '<button class="btn btn-warning btn-sm me-1" id="btn-reset">' +
        '<i class="fas fa-redo"></i> Reset</button>';
    }

    actions +=
      '<button class="btn btn-danger btn-sm" id="btn-destroy">' +
      '<i class="fas fa-trash"></i> Destroy</button>';

    $("#instance-actions").show().html(actions);

    $("#btn-reset").on("click", function () {
      resetInstance(inst.id);
    });
    $("#btn-destroy").on("click", function () {
      destroyInstance(inst.id);
    });
  }

  // ---------------------------------------------------------------------------
  // API calls
  // ---------------------------------------------------------------------------

  function fetchStatus() {
    $.ajax({
      url: API_BASE + "/instances",
      method: "GET",
      headers: apiHeaders(),
      success: function (resp) {
        if (resp.instance) {
          renderInstance(resp.instance);
        } else {
          renderNoInstance();
        }
      },
      error: function () {
        $("#instance-status").html(
          '<p class="text-danger">Failed to load instance status.</p>'
        );
      },
    });
  }

  function launchInstance() {
    if (!currentChallengeId) return;

    $("#btn-launch")
      .prop("disabled", true)
      .html('<i class="fas fa-spinner fa-spin"></i> Launching...');

    $.ajax({
      url: API_BASE + "/instances",
      method: "POST",
      headers: apiHeaders(),
      data: JSON.stringify({ challenge_id: currentChallengeId }),
      success: function (resp) {
        fetchStatus();
      },
      error: function (xhr) {
        const msg =
          (xhr.responseJSON && xhr.responseJSON.error) ||
          "Failed to launch instance";
        $("#instance-status").html(
          '<p class="text-danger">' + msg + "</p>"
        );
        renderNoInstance();
      },
    });
  }

  function destroyInstance(instanceId) {
    if (!confirm("Destroy your running instance?")) return;

    $("#btn-destroy")
      .prop("disabled", true)
      .html('<i class="fas fa-spinner fa-spin"></i> Destroying...');

    $.ajax({
      url: API_BASE + "/instances/" + instanceId,
      method: "DELETE",
      headers: apiHeaders(),
      success: function () {
        fetchStatus();
      },
      error: function () {
        fetchStatus();
      },
    });
  }

  function resetInstance(instanceId) {
    if (!confirm("Reset the instance to its initial state?")) return;

    $("#btn-reset")
      .prop("disabled", true)
      .html('<i class="fas fa-spinner fa-spin"></i> Resetting...');

    $.ajax({
      url: API_BASE + "/instances/" + instanceId + "/reset",
      method: "POST",
      headers: apiHeaders(),
      success: function () {
        fetchStatus();
      },
      error: function (xhr) {
        const msg =
          (xhr.responseJSON && xhr.responseJSON.error) || "Reset failed";
        alert(msg);
        fetchStatus();
      },
    });
  }

  // ---------------------------------------------------------------------------
  // Flag submission
  // ---------------------------------------------------------------------------

  function submitFlag() {
    const input = $("#challenge-input").val();
    if (!input) return;

    const challengeId = currentChallengeId;

    $.ajax({
      url: "/api/v1/challenges/attempt",
      method: "POST",
      headers: apiHeaders(),
      data: JSON.stringify({
        challenge_id: challengeId,
        submission: input,
      }),
      success: function (resp) {
        const result = resp.data;
        if (result.status === "correct") {
          $("#result-message").html(
            '<div class="alert alert-success">Correct! Challenge solved.</div>'
          );
        } else if (result.status === "incorrect") {
          $("#result-message").html(
            '<div class="alert alert-danger">Incorrect flag. Try again.</div>'
          );
        } else if (result.status === "already_solved") {
          $("#result-message").html(
            '<div class="alert alert-info">You already solved this challenge.</div>'
          );
        } else {
          $("#result-message").html(
            '<div class="alert alert-warning">' +
            (result.message || "Unknown response") +
            "</div>"
          );
        }
      },
      error: function (xhr) {
        const msg =
          (xhr.responseJSON && xhr.responseJSON.message) ||
          "Submission failed";
        $("#result-message").html(
          '<div class="alert alert-danger">' + msg + "</div>"
        );
      },
    });
  }

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------

  /**
   * CTFd calls this for custom challenge types.
   * `challenge` is the challenge object from the API.
   */
  CTFd.plugin.challenge = {
    id: "ctflab",
    name: "ctflab",

    preRender: function () {},

    render: function (markdown) {
      return CTFd.lib.markdown()(markdown);
    },

    postRender: function () {
      currentChallengeId = parseInt(
        $("#challenge-id").val() ||
        $(".challenge-id").data("challenge-id") ||
        window.challenge_id ||
        window.init && window.init.challenge_id ||
        0
      );

      // Attempt to get challenge_id from the modal
      if (!currentChallengeId) {
        const match = window.location.hash.match(/#ctflab-(\d+)/);
        if (match) {
          currentChallengeId = parseInt(match[1]);
        }
      }

      fetchStatus();

      // Poll every 5 seconds
      if (pollTimer) clearInterval(pollTimer);
      pollTimer = setInterval(fetchStatus, 5000);

      // Submit button
      $("#challenge-submit").off("click").on("click", submitFlag);
      $("#challenge-input")
        .off("keypress")
        .on("keypress", function (e) {
          if (e.which === 13) submitFlag();
        });
    },

    submit: function (callback, preview) {
      const input = $("#challenge-input").val();
      const challengeId = currentChallengeId;

      $.ajax({
        url: "/api/v1/challenges/attempt",
        method: "POST",
        headers: apiHeaders(),
        data: JSON.stringify({
          challenge_id: challengeId,
          submission: input,
        }),
        success: function (resp) {
          callback(resp);
        },
        error: function (xhr) {
          callback({
            data: {
              status: "incorrect",
              message: "Submission error",
            },
          });
        },
      });
    },
  };
});
