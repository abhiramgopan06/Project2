// Rental Platform - small bits of JavaScript.
// This file is loaded at the bottom of templates/base.html.

document.addEventListener("DOMContentLoaded", () => {
    // ------------------------------------------------------------------
    // 1) Close message boxes (green "saved" / red "error" bars) after 5 seconds
    // ------------------------------------------------------------------
    document.querySelectorAll(".alert").forEach((alert) => {
        setTimeout(() => {
            if (window.bootstrap) bootstrap.Alert.getOrCreateInstance(alert).close();
        }, 5000);
    });

    // ------------------------------------------------------------------
    // 2) Light / dark mode button
    // The small script in the <head> of base.html has already chosen the
    // starting theme. Here we only make the button switch it and remember it.
    // ------------------------------------------------------------------
    const themeButton = document.getElementById("theme-toggle");
    const themeIcon = document.getElementById("theme-icon");
    const themeLabel = document.getElementById("theme-label");

    if (themeButton) {
        // Show the right icon and text for the theme that is on right now.
        const updateButton = (theme) => {
            if (theme === "dark") {
                themeIcon.className = "bi bi-sun-fill";
                themeLabel.textContent = "Light mode";
                themeButton.title = "Switch to light mode";
            } else {
                themeIcon.className = "bi bi-moon-stars-fill";
                themeLabel.textContent = "Dark mode";
                themeButton.title = "Switch to dark mode";
            }
        };

        updateButton(document.documentElement.getAttribute("data-bs-theme"));

        themeButton.addEventListener("click", () => {
            const current = document.documentElement.getAttribute("data-bs-theme");
            const next = current === "dark" ? "light" : "dark";

            // Bootstrap and style.css both react to this attribute.
            document.documentElement.setAttribute("data-bs-theme", next);
            updateButton(next);

            // Remember the choice for next time (the browser may block this,
            // in which case the theme still changes, it just isn't saved).
            try {
                localStorage.setItem("theme", next);
            } catch (error) {
                /* ignore */
            }
        });
    }

    // ------------------------------------------------------------------
    // 3) Property image gallery (property detail page)
    // - the row of small pictures can be dragged left/right with the mouse
    //   (on a phone the browser already lets you swipe it)
    // - clicking a small picture shows it in the big picture above
    // ------------------------------------------------------------------
    const strip = document.getElementById("gallery-strip");
    const mainImage = document.getElementById("gallery-main");

    if (strip && mainImage) {
        let isDragging = false;
        let startX = 0;
        let startScroll = 0;
        let moved = false; // true if the mouse travelled, so it was a drag and not a click

        strip.addEventListener("mousedown", (event) => {
            isDragging = true;
            moved = false;
            startX = event.pageX;
            startScroll = strip.scrollLeft;
            strip.classList.add("dragging");
        });

        window.addEventListener("mousemove", (event) => {
            if (!isDragging) return;
            const distance = event.pageX - startX;
            if (Math.abs(distance) > 5) moved = true;
            strip.scrollLeft = startScroll - distance;
        });

        window.addEventListener("mouseup", () => {
            isDragging = false;
            strip.classList.remove("dragging");
        });

        strip.querySelectorAll(".gallery-thumb").forEach((thumb) => {
            thumb.addEventListener("click", () => {
                if (moved) return; // it was a drag, so don't change the big picture

                mainImage.src = thumb.dataset.full;
                mainImage.alt = thumb.alt;

                strip.querySelectorAll(".gallery-thumb").forEach((other) => {
                    other.classList.remove("active");
                });
                thumb.classList.add("active");
            });
        });
    }
});
