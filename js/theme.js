(function () {
  var MANIFEST = "/images/site/theme.json";
  var path = (location.pathname || "/").replace(/\/index\.html$/, "") || "/";
  var isHome = path === "/";
  var isBlogIndex = path === "/blog" || path === "/blog/";
  var isBlogPost = path.indexOf("/blog/") === 0 && !isBlogIndex;
  var useAtmosphere = isHome || isBlogIndex;

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  $all(".mascot-band, [data-mascot-reel]").forEach(function (el) { el.remove(); });

  if (isBlogPost) {
    document.documentElement.classList.add("is-blog-post");
    $all(".hero-photo, [data-theme-atmosphere]").forEach(function (el) { el.remove(); });
    $all('img[src*="/images/site/mascot"]').forEach(function (el) {
      if (!el.closest(".site-header, .wordmark")) el.remove();
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

  function ensureAtmosphere() {
    if (isHome) return;
    if ($(".hero-photo") || $("[data-theme-atmosphere]")) return;
    var wrap = document.createElement("div");
    wrap.className = "theme-atmosphere";
    wrap.setAttribute("data-theme-atmosphere", "");
    wrap.setAttribute("aria-hidden", "true");
    wrap.innerHTML = '<video muted loop playsinline data-hero-video></video><img alt="">';
    var main = $("main");
    if (main) main.insertBefore(wrap, main.firstChild);
    else document.body.insertBefore(wrap, document.body.firstChild);
  }

  function applyAtmosphere(theme) {
    if (!useAtmosphere) return;
    ensureAtmosphere();
    var root = $(".hero-photo") || $("[data-theme-atmosphere]");
    if (!root) return;
    var video = root.querySelector("[data-hero-video], video");
    var img = root.querySelector("img");
    if (img && theme.poster) {
      img.src = theme.poster;
      img.alt = "";
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

  function applyAbout(theme) {
    if (!theme.about) return;
    if (path.indexOf("/about") !== 0) return;
    $all("[data-about-photo], .about-photo img").forEach(function (el) {
      if (el.tagName === "IMG") el.src = theme.about;
    });
  }

  fetch(MANIFEST, { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (theme) { applyAtmosphere(theme); applyAbout(theme); })
    .catch(function () {});
})();
