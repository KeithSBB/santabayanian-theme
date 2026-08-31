(function () {
  var MANIFEST = "/images/site/theme.json";
  var path = (location.pathname || "/").replace(/\/index\.html$/, "") || "/";
  var isHome = path === "/";
  var isBlogIndex = path === "/blog" || path === "/blog/";
  var isBlogPost = path.indexOf("/blog/") === 0 && !isBlogIndex;

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  $all(".mascot-band, [data-mascot-reel], [data-theme-atmosphere]").forEach(function (el) { el.remove(); });
  if (!isHome) {
    $all(".hero-photo").forEach(function (el) { el.remove(); });
  }

  if (isBlogPost) {
    document.documentElement.classList.add("is-blog-post");
    $all('img.blog-title-mascot, img[src*="/images/site/mascot"]').forEach(function (el) {
      if (!el.closest(".site-header, .wordmark, .post-body, .blog-body, article .content")) el.remove();
    });
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

  function applyHomeHero(theme) {
    if (!isHome) return;
    var root = $(".hero-photo");
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

  function applyBlogTitleMascot(theme) {
    if (!isBlogIndex || !theme.poster) return;
    if ($(".blog-title-mascot")) {
      $(".blog-title-mascot").src = theme.poster;
      return;
    }
    var h1 = $("main h1") || $("h1");
    if (!h1) return;
    var wrap = h1.closest(".title-with-mascot");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.className = "title-with-mascot";
      h1.parentNode.insertBefore(wrap, h1);
      wrap.appendChild(h1);
    }
    var img = document.createElement("img");
    img.className = "blog-title-mascot";
    img.src = theme.poster;
    img.alt = "";
    wrap.appendChild(img);
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
    .then(function (theme) {
      applyHomeHero(theme);
      applyBlogTitleMascot(theme);
      applyAbout(theme);
    })
    .catch(function () {});
})();
