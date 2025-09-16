// No inline JS allowed. All interactive behavior implemented here.
// Copy-to-clipboard and raw toggle.

document.addEventListener("DOMContentLoaded", function () {
  // Copy link
  var copyBtn = document.getElementById("copyBtn");
  var shareInput = document.getElementById("shareUrl");
  if (copyBtn && shareInput) {
    function revealShare() {
      if (!shareInput.value) {
        var v = shareInput.getAttribute('data-share') || '';
        shareInput.value = v;
      }
    }

    copyBtn.addEventListener("click", function () {
      revealShare();
      try {
        shareInput.select();
        var ok = document.execCommand("copy");
        if (!ok) {
          navigator.clipboard.writeText(shareInput.value).then(function () {
            copyBtn.innerText = "Copied!";
            setTimeout(function () { copyBtn.innerText = "Copy link"; }, 2000);
          });
        } else {
          copyBtn.innerText = "Copied!";
          setTimeout(function () { copyBtn.innerText = "Copy link"; }, 2000);
        }
      } catch (e) {
        navigator.clipboard.writeText(shareInput.value).then(function () {
          copyBtn.innerText = "Copied!";
          setTimeout(function () { copyBtn.innerText = "Copy link"; }, 2000);
        });
      }
    });

    // Open button: open deliberately to avoid accidental prefetch
    var openBtn = document.getElementById('openBtn');
    if (openBtn) {
      openBtn.addEventListener('click', function () {
        revealShare();
        var v = shareInput.value;
        if (v) window.open(v, '_blank', 'noopener');
      });
    }
  }

  // Toggle raw/markdown
  var toggleBtn = document.getElementById("toggleRawBtn");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", function () {
      var raw = document.getElementById("raw");
      var rendered = document.getElementById("rendered");
      if (!raw || !rendered) return;
      if (raw.style.display === "none" || raw.style.display === "") {
        raw.style.display = "block";
        rendered.style.display = "none";
        toggleBtn.innerText = "View rendered";
      } else {
        raw.style.display = "none";
        rendered.style.display = "block";
        toggleBtn.innerText = "View raw";
      }
    });
  }

});
