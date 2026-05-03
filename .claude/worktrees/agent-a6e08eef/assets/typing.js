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

    // --- Pipeline Progress with Rotating Quotes ---
    _quoteInterval: null,
    _quoteIndex: 0,
    _QUOTES: [
        "Roads are the arteries of economic development. Their condition determines the cost of everything.",
        "In rural Africa, a road improvement can cut travel time to the nearest hospital by 60%.",
        "Every frame tells a story about the people who depend on this road.",
        "Transport infrastructure is the largest determinant of access to opportunity in rural communities.",
        "Good roads don\u2019t just move vehicles \u2014 they connect communities to healthcare, education, and markets.",
        "78% of Uganda\u2019s freight moves by road. Road condition directly impacts the cost of food and goods.",
        "TARA combines AI vision with engineering methodology to see what traditional surveys miss.",
        "A single road improvement can transform economic access for an entire district.",
        "Road investment decisions affect millions of lives. They deserve rigorous, people-centred analysis.",
        "Traditional road appraisal takes months. TARA aims to make it accessible in minutes.",
    ],

    startProgress: function(n_clicks) {
        if (!n_clicks) return window.dash_clientside.no_update;
        var tara = window.dash_clientside.tara;
        var container = document.getElementById('pipeline-progress-container');
        var quote = document.getElementById('pipeline-progress-quote');
        var el = document.getElementById('video-pipeline-result');

        // Clear previous result content
        if (el) el.innerHTML = '';

        if (!container) return window.dash_clientside.no_update;
        container.style.display = 'block';

        // Show first quote
        tara._quoteIndex = 0;
        if (quote) {
            quote.textContent = tara._QUOTES[0];
            quote.style.opacity = '1';
        }

        // Clear any existing interval
        if (tara._quoteInterval) clearInterval(tara._quoteInterval);

        // Rotate quotes every 8 seconds
        tara._quoteInterval = setInterval(function() {
            if (!quote) return;
            tara._quoteIndex = (tara._quoteIndex + 1) % tara._QUOTES.length;
            quote.style.opacity = '0';
            setTimeout(function() {
                quote.textContent = tara._QUOTES[tara._quoteIndex];
                quote.style.opacity = '1';
            }, 300);
        }, 8000);

        return window.dash_clientside.no_update;
    },

    stopProgress: function() {
        var tara = window.dash_clientside.tara;
        var container = document.getElementById('pipeline-progress-container');
        if (container) container.style.display = 'none';
        if (tara._quoteInterval) {
            clearInterval(tara._quoteInterval);
            tara._quoteInterval = null;
        }
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
