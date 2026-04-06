/**
 * CTFLab challenge update script.
 *
 * Serialises the admin update form and PATCHes the CTFd challenges API.
 */

CTFd.plugin.run((_CTFd) => {
  const $ = _CTFd.lib.$;

  function csrfToken() {
    return $('meta[name="csrf-token"]').attr("content") || CTFd.config.csrfNonce || "";
  }

  /**
   * Gather form data and update an existing ctflab challenge.
   */
  function updateChallenge(event) {
    event.preventDefault();

    const params = {};
    $(event.target)
      .serializeArray()
      .forEach(function (item) {
        params[item.name] = item.value;
      });

    const challengeId = params.id;
    if (!challengeId) {
      alert("Challenge ID missing.");
      return;
    }

    params.value = parseInt(params.value) || 0;
    params.max_attempts = parseInt(params.max_attempts) || 0;
    params.instance_timeout = parseInt(params.instance_timeout) || 14400;

    // Validate JSON for env vars
    try {
      JSON.parse(params.box_env_json || "{}");
    } catch (e) {
      alert("Environment Variables must be valid JSON.");
      return;
    }

    $.ajax({
      url: "/api/v1/challenges/" + challengeId,
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "CSRF-Token": csrfToken(),
      },
      data: JSON.stringify(params),
      success: function (resp) {
        if (resp.success) {
          alert("Challenge updated successfully.");
        }
      },
      error: function (xhr) {
        var msg = "Failed to update challenge";
        if (xhr.responseJSON && xhr.responseJSON.message) {
          msg = xhr.responseJSON.message;
        }
        alert(msg);
      },
    });
  }

  // Bind to the form submit
  $("#challenge-update-form").on("submit", updateChallenge);

  // Handle the Save button in CTFd admin panel
  $(".challenge-update-options #challenge-update-container .btn-primary").on(
    "click",
    function (e) {
      e.preventDefault();
      $("#challenge-update-form").trigger("submit");
    }
  );
});
