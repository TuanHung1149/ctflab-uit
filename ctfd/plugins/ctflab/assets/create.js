/**
 * CTFLab challenge creation script.
 *
 * Serialises the admin creation form and POSTs to the CTFd challenges API.
 */

CTFd.plugin.run((_CTFd) => {
  const $ = _CTFd.lib.$;

  function csrfToken() {
    return $('meta[name="csrf-token"]').attr("content") || CTFd.config.csrfNonce || "";
  }

  /**
   * Gather form data and submit a new ctflab challenge.
   */
  function submitChallenge(event) {
    event.preventDefault();

    const params = {};
    $(event.target)
      .serializeArray()
      .forEach(function (item) {
        params[item.name] = item.value;
      });

    // Ensure required fields
    params.type = "ctflab";
    params.value = parseInt(params.value) || 0;
    params.instance_timeout = parseInt(params.instance_timeout) || 14400;

    // Validate docker_image
    if (!params.docker_image) {
      alert("Docker image is required.");
      return;
    }

    // Validate flag_prefix
    if (!params.flag_prefix) {
      alert("Flag prefix is required.");
      return;
    }

    // Validate JSON for env vars
    try {
      JSON.parse(params.box_env_json || "{}");
    } catch (e) {
      alert("Environment Variables must be valid JSON.");
      return;
    }

    $.ajax({
      url: "/api/v1/challenges",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "CSRF-Token": csrfToken(),
      },
      data: JSON.stringify(params),
      success: function (resp) {
        if (resp.success) {
          window.location =
            CTFd.config.urlRoot +
            "/admin/challenges/" +
            resp.data.id;
        }
      },
      error: function (xhr) {
        var msg = "Failed to create challenge";
        if (xhr.responseJSON && xhr.responseJSON.message) {
          msg = xhr.responseJSON.message;
        }
        alert(msg);
      },
    });
  }

  // Bind to the form submit
  $("#challenge-create-form").on("submit", submitChallenge);

  // Also handle the Next button if CTFd uses a wizard-style flow
  $(".challenge-create-options #create-chal-submit").on("click", function (e) {
    e.preventDefault();
    $("#challenge-create-form").trigger("submit");
  });
});
