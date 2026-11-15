/* Found at Home - category filter + live render from products.json.
   The list is already pre-rendered into index.html by build.py; this only
   (1) filters by category and (2) re-renders if products.json is newer than the HTML. */
(function () {
  "use strict";
  document.documentElement.classList.add("js");

  var LABELS = { kitchen: "Kitchen", cleaning: "Cleaning", organization: "Organization", decor: "Decor", gifts: "Gifts" };

  function $(sel) { return document.querySelector(sel); }
  function $$(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

  function cats(p) { return typeof p.category === "string" ? [p.category] : (p.category || []); }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function card(p, i) {
    var c = cats(p).filter(function (k) { return LABELS[k]; });
    var li = el("li", "card");
    li.id = p.id;
    li.setAttribute("data-cat", c.join(" "));
    var img = el("img", "card-img");
    img.src = p.image; img.alt = p.image_alt || p.name;
    img.width = 400; img.height = 500; img.decoding = "async";
    if (i > 1) img.loading = "lazy";
    var body = el("div", "card-body");
    body.appendChild(el("p", "card-cat", c.map(function (k) { return LABELS[k]; }).join(" · ")));
    body.appendChild(el("h3", "card-name", p.name));
    body.appendChild(el("p", "card-note", p.note));
    var a = el("a", "btn", "Check it on Amazon");
    a.href = p.link; a.rel = "sponsored nofollow noopener"; a.target = "_blank";
    a.appendChild(el("span", "sr-only", " (opens Amazon in a new tab)"));
    body.appendChild(a);
    body.appendChild(el("p", "card-ad", "Affiliate link"));
    li.appendChild(img); li.appendChild(body);
    return li;
  }

  function okLink(u) { return /^https:\/\/(amzn\.to|(www\.)?amazon\.com)\//.test(u); }

  function render(list) {
    var grid = $("#grid");
    if (!grid) return;
    grid.textContent = "";
    list.forEach(function (p, i) { grid.appendChild(card(p, i)); });
    var has = list.length > 0;
    $(".chips").hidden = !has;
    $(".finds").hidden = !has;
    $("#soon").hidden = has;
  }

  function applyFilter(f) {
    var shown = 0;
    $$(".chip").forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-filter") === f)); });
    $$("#grid .card").forEach(function (c) {
      var show = f === "all" || (" " + c.getAttribute("data-cat") + " ").indexOf(" " + f + " ") > -1;
      c.hidden = !show;
      if (show) shown++;
    });
    var empty = $("#filter-empty");
    if (empty) empty.hidden = shown > 0 || !$$("#grid .card").length;
  }

  document.addEventListener("click", function (e) {
    var chip = e.target.closest && e.target.closest(".chip");
    if (chip) { applyFilter(chip.getAttribute("data-filter")); return; }
    if (e.target.closest && e.target.closest("[data-show-all]")) { e.preventDefault(); applyFilter("all"); }
  });

  // If products.json has changed since build.py last ran, show the JSON version.
  if (window.fetch && location.protocol !== "file:") {
    fetch("products.json", { cache: "no-cache" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        var list = (Array.isArray(data) ? data : data.products || []).filter(function (p) {
          return p && p.id && p.name && p.link && okLink(p.link);
        });
        list = list.map(function (p, i) { return { p: p, i: i }; })
          .sort(function (a, b) { return a.p.added === b.p.added ? b.i - a.i : (a.p.added < b.p.added ? 1 : -1); })
          .map(function (x) { return x.p; });
        var now = $$("#grid .card").map(function (c) { return c.id; }).join(",");
        if (list.map(function (p) { return p.id; }).join(",") !== now) render(list);
        var active = $(".chip[aria-pressed='true']");
        applyFilter(active ? active.getAttribute("data-filter") : "all");
      })
      .catch(function () { /* keep the pre-rendered list */ });
  }
})();
