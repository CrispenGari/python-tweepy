$(document).on("submit", "#form", function (e) {
  e.preventDefault();
  $.ajax({
    type: "POST",
    url: "/",
    data: {
      tweet: $("#tweet").val(),
    },
    success: (res) => {
      $("#home__results").html(`
      <div class="alert alert-danger" role="alert">
        <small><strong>Error: <strong>${res.error}<strong>.</small>
      </div>
      `);
      if (res.error) {
      } else {
        $("#home__results").html(`
        <div class="alert alert-${
          res.prediction.label.label === "positive"
            ? "success"
            : res.prediction.label.label === "neutral"
            ? "light"
            : "danger"
        } alert-dismissible fade show" role="alert">
        <strong>${res.prediction.label.label}: </strong> "${$("#tweet").val()}"
        <button
          type="button"
          class="btn-close"
          data-bs-dismiss="alert"
          aria-label="Close"
        ></button>
      </div>
      <div class="alert alert-secondary" role="alert">
        <small><strong>${
          res.prediction.label.confidence * 100
        }%<strong> confidence of being <strong>${
          res.prediction.label.label
        }<strong>.</small>
      </div>
        `);
      }
    },
  });
});

$(document).on("submit", "#logout__form", function (e) {
  e.preventDefault();
  $.ajax({
    type: "POST",
    url: "/auth/logout",
    success: (res) => {
      window.location.href = "/auth/login";
    },
  });
});
