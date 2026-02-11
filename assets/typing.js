/**
 * TARA — AI Typing Animation
 * Clientside callback for character-by-character text reveal.
 * Zero server round-trips — uses pure setTimeout in the browser.
 */

if (!window.dash_clientside) {
    window.dash_clientside = {};
}

window.dash_clientside.tara = {
    fitBounds: function(bounds) {
        if (!bounds) return window.dash_clientside.no_update;
        // dash-leaflet stores the Leaflet map instance; find it via DOM
        var attempts = 0;
        function tryFit() {
            var mapEl = document.getElementById('main-map');
            if (!mapEl) return;
            // dash-leaflet renders a child div that holds the Leaflet instance
            var leafletEl = mapEl.querySelector('.leaflet-container');
            if (leafletEl && leafletEl._leaflet_map) {
                leafletEl._leaflet_map.fitBounds(bounds, {padding: [30, 30]});
                return;
            }
            // Fallback: look for _leaflet_id on child elements
            var children = mapEl.querySelectorAll('[class*="leaflet"]');
            for (var i = 0; i < children.length; i++) {
                if (children[i]._leaflet_map) {
                    children[i]._leaflet_map.fitBounds(bounds, {padding: [30, 30]});
                    return;
                }
            }
            // Try window.map_ patterns used by some dash-leaflet versions
            if (window._leaflet_map) {
                window._leaflet_map.fitBounds(bounds, {padding: [30, 30]});
                return;
            }
            // Retry a few times while map initializes
            if (attempts < 10) {
                attempts++;
                setTimeout(tryFit, 200);
            }
        }
        setTimeout(tryFit, 100);
        return window.dash_clientside.no_update;
    },

    typeText: function(storeData) {
        if (!storeData || !storeData.text || !storeData.targetId) {
            return window.dash_clientside.no_update;
        }

        var targetId = storeData.targetId;
        var fullText = storeData.text;
        var el = document.getElementById(targetId);

        if (!el) {
            return window.dash_clientside.no_update;
        }

        // Build the AI block wrapper
        el.innerHTML =
            '<span class="tara-typing-dot"></span>' +
            '<div class="tara-ai-block">' +
                '<span id="tara-typed-text"></span>' +
                '<span class="tara-ai-cursor"></span>' +
            '</div>';

        var typedEl = document.getElementById('tara-typed-text');
        var dotEl = el.querySelector('.tara-typing-dot');
        var cursorEl = el.querySelector('.tara-ai-cursor');
        var idx = 0;
        var speed = 12; // ms per character

        function typeNext() {
            if (idx < fullText.length) {
                var ch = fullText[idx];
                if (ch === '\n') {
                    typedEl.innerHTML += '<br>';
                } else {
                    typedEl.innerHTML += ch;
                }
                idx++;
                setTimeout(typeNext, speed);
            } else {
                // Done typing
                if (cursorEl) cursorEl.remove();
                if (dotEl) dotEl.classList.add('dim');
            }
        }

        setTimeout(typeNext, 300); // small initial delay

        return window.dash_clientside.no_update;
    }
};
