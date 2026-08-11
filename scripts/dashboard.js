/* RV News — client-side filtering.
   Everything is already in the page; this only shows and hides. No network,
   which also keeps the generated page usable as an offline snapshot.

   Filter state is mirrored into the URL hash so a filtered view can be shared
   as a link — "look at the competitor items" is a message someone will want to
   send. */
(function () {
  "use strict";

  var rows    = Array.prototype.slice.call(document.querySelectorAll("[data-item]"));
  var groups  = Array.prototype.slice.call(document.querySelectorAll("[data-group]"));
  var chips   = Array.prototype.slice.call(document.querySelectorAll("[data-filter]"));
  var tiles   = Array.prototype.slice.call(document.querySelectorAll("[data-tile]"));
  var search  = document.getElementById("q");
  var status  = document.getElementById("status");
  var empty   = document.getElementById("empty");
  var reset   = document.getElementById("reset");

  var state = { cat: "all", country: "all", q: "" };

  function readHash() {
    var h = (location.hash || "").replace(/^#/, "");
    if (!h) return;
    h.split("&").forEach(function (pair) {
      var kv = pair.split("=");
      var k = decodeURIComponent(kv[0] || "");
      var v = decodeURIComponent(kv[1] || "");
      if (k === "cat" || k === "country") state[k] = v || "all";
      if (k === "q") state.q = v;
    });
    if (search) search.value = state.q;
  }

  function writeHash() {
    var parts = [];
    if (state.cat !== "all") parts.push("cat=" + encodeURIComponent(state.cat));
    if (state.country !== "all") parts.push("country=" + encodeURIComponent(state.country));
    if (state.q) parts.push("q=" + encodeURIComponent(state.q));
    var next = parts.length ? "#" + parts.join("&") : "#";
    if (next !== location.hash) history.replaceState(null, "", next);
  }

  function matches(row) {
    if (state.cat === "competitor") {
      if (row.getAttribute("data-competitor") !== "1") return false;
    } else if (state.cat !== "all" && row.getAttribute("data-cat") !== state.cat) {
      return false;
    }
    if (state.country !== "all" && row.getAttribute("data-country") !== state.country) return false;
    if (state.q) {
      var needle = state.q.toLowerCase();
      // Every word must appear, so "truma panel" narrows rather than widens.
      var hay = row.getAttribute("data-text") || "";
      var words = needle.split(/\s+/).filter(Boolean);
      for (var i = 0; i < words.length; i++) {
        if (hay.indexOf(words[i]) === -1) return false;
      }
    }
    return true;
  }

  function apply() {
    var shown = 0;
    rows.forEach(function (row) {
      var ok = matches(row);
      row.hidden = !ok;
      if (ok) shown++;
    });

    // A section heading with nothing under it is noise.
    groups.forEach(function (group) {
      var visible = group.querySelectorAll("[data-item]:not([hidden])").length;
      group.hidden = visible === 0;
      var counter = group.querySelector("[data-group-count]");
      if (counter) counter.textContent = visible === 1 ? "1 item" : visible + " items";
    });

    chips.forEach(function (chip) {
      var isActive = chip.getAttribute("data-filter-value") === state[chip.getAttribute("data-filter")];
      chip.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
    tiles.forEach(function (tile) {
      tile.setAttribute("aria-pressed", tile.getAttribute("data-tile") === state.cat ? "true" : "false");
    });

    if (status) {
      status.textContent = shown === rows.length
        ? "Showing all " + rows.length + " items"
        : "Showing " + shown + " of " + rows.length + " items";
    }
    if (empty) empty.hidden = shown !== 0;
    writeHash();
  }

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      var key = chip.getAttribute("data-filter");
      var val = chip.getAttribute("data-filter-value");
      state[key] = state[key] === val ? "all" : val;   // click again to clear
      apply();
    });
  });

  tiles.forEach(function (tile) {
    tile.addEventListener("click", function () {
      var val = tile.getAttribute("data-tile");
      state.cat = state.cat === val ? "all" : val;
      apply();
      var reg = document.getElementById("register");
      if (reg) reg.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  if (search) {
    search.addEventListener("input", function () {
      state.q = search.value.trim();
      apply();
    });
    search.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { search.value = ""; state.q = ""; apply(); }
    });
  }

  if (reset) {
    reset.addEventListener("click", function () {
      state = { cat: "all", country: "all", q: "" };
      if (search) search.value = "";
      apply();
    });
  }

  readHash();
  apply();
})();
