(function () {
  var MANIFEST = "/images/site/theme.json";
  var path = (location.pathname || "/").replace(/\/index\.html$/, "") || "/";
  var isHome = path === "/";
  var isBlogPost = path.indexOf("/blog/") === 0 && path !== "/blog" && path !== "/blog/";

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  if (isBlogPost) {
    document.documentElement.classList.add("is-blog-post");
    $all(".mascot-band, .hero-photo, [data-mascot-reel]").forEach(function (el) { el.remove(); });
    $all('img[src*="/images/site/mascot"]').forEach(function (el) {
      var inHeader = el.closest(".site-header, .wordmark");
      if (!inHeader) el.remove();
    });
    return;
  }

  function hideVideo(video) {
    if (!video) return;
    video.classList.remove("is-ready");
    video.removeAttribute("src");
    var source = video.querySelector("source");
    if (source) source.removeAttribute("src");
    try { video.load(); } catch (e) {}
    video.style.display = "none";
  }

  function applyHero(theme) {
    if (!isHome) return;
    var video = $("[data-hero-video]") || $(".hero-photo video");
    var img = $(".hero-photo img");
    if (img && theme.poster) {
      img.src = theme.poster;
      img.alt = "Santa Bayanian";
    }
    if (!video) return;
    if (!theme.heroVideo) {
      hideVideo(video);
      return;
    }
    video.style.display = "";
    video.classList.remove("is-ready");
    video.addEventListener("loadeddata", function () { video.classList.add("is-ready"); }, { once: true });
    video.addEventListener("error", function () { hideVideo(video); }, { once: true });
    var source = video.querySelector("source");
    if (source) source.src = theme.heroVideo;
    else video.src = theme.heroVideo;
    try { video.load(); } catch (e) {}
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!reduce) {
      var play = video.play();
      if (play && play.catch) play.catch(function () { hideVideo(video); });
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
      i.src = item.src;
      i.alt = item.name || "Santa Bayanian";
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
    if (!isHome) return;
    var grid = $("[data-mascot-grid]");
    if (!grid) return;
    grid.innerHTML = "";
    (theme.clips || []).forEach(function (c) { grid.appendChild(card(c, true)); });
    (theme.stills || []).forEach(function (s) { grid.appendChild(card(s, false)); });
    if (!grid.childNodes.length) {
      var band = $("[data-mascot-reel]");
      if (band) band.hidden = true;
    }
  }

  function applyAbout(theme) {
    if (!theme.about) return;
    if (path.indexOf("/about") !== 0) return;
    $all("[data-about-photo], .about-photo img").forEach(function (el) {
      if (el.tagName === "IMG") el.src = theme.about;
    });
  }

  fetch(MANIFEST, { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (theme) { applyHero(theme); applyReel(theme); applyAbout(theme); })
    .catch(function () {});
})();
