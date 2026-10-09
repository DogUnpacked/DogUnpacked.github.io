/**
 * Breed directory filter. The full A-to-Z list is in the HTML, so the page
 * still works if this file does not run.
 */
(function () {
  "use strict";

  var input = document.getElementById("breed-search");
  var empty = document.getElementById("breed-empty");
  var cards = document.querySelectorAll(".breed-card");
  var buttons = document.querySelectorAll(".group-filter");
  if (!cards.length) return;

  var group = "";

  function apply() {
    var query = input ? input.value.trim().toLowerCase() : "";
    var shown = 0;
    for (var i = 0; i < cards.length; i++) {
      var card = cards[i];
      var name = card.getAttribute("data-name") || "";
      var cardGroup = card.getAttribute("data-group") || "";
      var match = (!query || name.indexOf(query) !== -1) && (!group || cardGroup === group);
      card.hidden = !match;
      if (match) shown += 1;
    }
    if (empty) empty.hidden = shown !== 0;
  }

  if (input) input.addEventListener("input", apply);

  for (var b = 0; b < buttons.length; b++) {
    buttons[b].addEventListener("click", function (event) {
      var button = event.currentTarget;
      group = button.getAttribute("data-group") || "";
      for (var i = 0; i < buttons.length; i++) {
        buttons[i].setAttribute("aria-pressed", buttons[i] === button ? "true" : "false");
      }
      apply();
    });
  }
})();
