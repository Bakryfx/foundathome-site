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

  function proofText(p) {
    return String(p.social_proof || "").trim().replace(/\d[\d,]{3,}/g, function (m) {
      var n = parseInt(m.replace(/,/g, ""), 10);
      if (n >= 1e6) return (+(n / 1e6).toFixed(n >= 1e7 ? 0 : 1)) + "M";
      if (n >= 1e3) return (+(n / 1e3).toFixed(n >= 1e4 ? 0 : 1)) + "K";
      return String(n);
    });
  }

  function card(p, i) {
    var c = cats(p).filter(function (k) { return LABELS[k]; });
    var li = el("li", "card");
    li.id = p.id;
    li.setAttribute("data-cat", c.join(" "));
    var href = "p/" + (p.slug || p.id) + "/";
    var imgLink = el("a", "card-imglink");
    imgLink.href = href; imgLink.tabIndex = -1; imgLink.setAttribute("aria-hidden", "true");
    var img = el("img", "card-img");
    img.src = p.image; img.alt = "";
    img.width = 400; img.height = 500; img.decoding = "async";
    if (i > 1) img.loading = "lazy";
    imgLink.appendChild(img);
    var sp = proofText(p);
    if (sp) imgLink.appendChild(el("span", "proof-badge", "🔥 " + sp));
    var body = el("div", "card-body");
    body.appendChild(el("p", "card-cat", c.map(function (k) { return LABELS[k]; }).join(" · ")));
    var h = el("h3", "card-name");
    var na = el("a", null, p.name); na.href = href; h.appendChild(na);
    body.appendChild(h);
    body.appendChild(el("p", "card-note", p.short_note || p.note));
    var a = el("a", "btn", "See the find");
    a.href = href;
    body.appendChild(a);
    li.appendChild(imgLink); li.appendChild(body);
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

  function hashFilter() {
    var m = /^#filter-([a-z]+)$/.exec(location.hash);
    if (m && $(".chip[data-filter='" + m[1] + "']")) applyFilter(m[1]);
  }

  // Product pages: YouTube Shorts load only after the visitor presses play.
  document.addEventListener("click", function (e) {
    var yt = e.target.closest && e.target.closest(".hero-video[data-yt] .yt-play");
    if (!yt) return;
    e.preventDefault();
    var box = yt.parentNode, f = document.createElement("iframe");
    f.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(box.getAttribute("data-yt")) + "?autoplay=1&rel=0&playsinline=1";
    f.title = "Short video"; f.allow = "autoplay; encrypted-media; picture-in-picture"; f.allowFullscreen = true;
    f.className = "yt-frame";
    box.textContent = ""; box.appendChild(f);
  });

  document.addEventListener("click", function (e) {
    var chip = e.target.closest && e.target.closest(".chip");
    if (chip) { applyFilter(chip.getAttribute("data-filter")); return; }
    if (e.target.closest && e.target.closest("[data-show-all]")) { e.preventDefault(); applyFilter("all"); }
  });

  window.addEventListener("hashchange", hashFilter);
  hashFilter();

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
        hashFilter();
      })
      .catch(function () { /* keep the pre-rendered list */ });
  }
})();
