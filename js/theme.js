(function () {
  var MANIFEST = "/images/site/theme.json";
  function $(sel, root) { return (root || document).querySelector(sel); }
  function applyHero(theme) {
    var video = $("[data-hero-video]") || $(".hero-photo video");
    var img = $(".hero-photo img");
    if (img && theme.poster) img.src = theme.poster;
    if (video && theme.heroVideo) {
      var source = video.querySelector("source");
      if (source) source.src = theme.heroVideo;
      else video.src = theme.heroVideo;
      video.setAttribute("poster", theme.poster || "");
      try { video.load(); } catch (e) {}
      var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (!reduce) { var play = video.play(); if (play && play.catch) play.catch(function () {}); }
    }
  }
  function card(item, isVideo) {
    var fig = document.createElement("figure");
    fig.className = "mascot-card";
    if (isVideo) {
      var v = document.createElement("video");
      v.src = item.src; v.muted = true; v.loop = true; v.playsInline = true;
      v.setAttribute("playsinline", ""); v.preload = "metadata";
      v.addEventListener("mouseenter", function () { v.play().catch(function () {}); });
      v.addEventListener("mouseleave", function () { v.pause(); });
      fig.appendChild(v);
    } else {
      var i = document.createElement("img");
      i.src = item.src; i.alt = item.name || "Santa Bayanian";
      fig.appendChild(i);
    }
    if (item.name) {
      var cap = document.createElement("figcaption");
      cap.textContent = item.name.replace(/[-_]+/g, " ");
      fig.appendChild(cap);
    }
    return fig;
  }
  function applyReel(theme) {
    var grid = $("[data-mascot-grid]");
    if (!grid) return;
    grid.innerHTML = "";
    (theme.clips || []).forEach(function (c) { grid.appendChild(card(c, true)); });
    (theme.stills || []).forEach(function (s) {
      if ((theme.clips || []).length && s.src.indexOf("mascot.jpg") !== -1) return;
      grid.appendChild(card(s, false));
    });
    if (!grid.childNodes.length) {
      var band = $("[data-mascot-reel]");
      if (band) band.hidden = true;
    }
  }
  function applyAbout(theme) {
    if (!theme.about) return;
    document.querySelectorAll("[data-about-photo], .about-photo img").forEach(function (el) {
      if (el.tagName === "IMG") el.src = theme.about;
    });
  }
  fetch(MANIFEST, { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (theme) { applyHero(theme); applyReel(theme); applyAbout(theme); })
    .catch(function () {});
})();
