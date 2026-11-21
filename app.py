// ==UserScript==
// @name         Ollie Link Unroller
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Bypass ad gates and shorteners client-side
// @match        *://links.lootlabs.gg/*
// @match        *://*.linkvertise.com/*
// @match        *://*.work.ink/*
// @run-at       document-start
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    
    console.log("[Ollie Bypasser] Active on target gate.");

    function extractDestination() {
        const urlParams = new URLSearchParams(window.location.search);
        
        // 1. LootLabs Base64 'cc' parameter un-shielding
        if (urlParams.has('cc')) {
            try {
                let base64Val = urlParams.get('cc');
                let decoded = atob(base64Val);
                let json = JSON.parse(decoded);
                if (json.url) {
                    window.location.replace(json.url);
                    return;
                }
            } catch(e) {}
        }

        // 2. Generic DOM target scraping
        let scripts = document.querySelectorAll('script');
        for (let s of scripts) {
            let text = s.innerText;
            let match = text.match(/["']destination["']\s*:\s*["'](https?:\/\/[^"']+)["']/);
            if (match && match[1]) {
                window.location.replace(match[1]);
                return;
            }
        }
    }

    window.addEventListener('DOMContentLoaded', extractDestination);
})();
