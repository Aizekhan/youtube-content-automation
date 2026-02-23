// ==UserScript==
// @name         Topics Manager Auto-Patcher
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Auto-patch Lambda URLs for Topics Manager
// @author       Claude
// @match        https://n8n-creator.space/topics-manager.html
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    
    console.log('🔧 Topics Manager Auto-Patcher activated');
    
    // Wait for LAMBDA_URLS to be defined
    const checkInterval = setInterval(() => {
        if (window.LAMBDA_URLS) {
            clearInterval(checkInterval);
            
            // Patch URLs
            window.LAMBDA_URLS = {
                LIST: 'https://o7oswstatxulqezia6fvli4iny0uizlg.lambda-url.eu-central-1.on.aws/',
                ADD: 'https://vmipd7m6v63qqn5nud6xg3huum0poewo.lambda-url.eu-central-1.on.aws/',
                GET_NEXT: 'https://rk7q7vapiwyrb5ydvzfqvnxyta0bytjr.lambda-url.eu-central-1.on.aws/',
                UPDATE_STATUS: 'https://zwjkxakffcgnqyfm74xq5uxwvy0cckpe.lambda-url.eu-central-1.on.aws/',
                BULK_ADD: 'https://24khhggitezt5uwhx7z53hdyzm0yizht.lambda-url.eu-central-1.on.aws/'
            };
            
            console.log('✅ Lambda URLs auto-patched!');
        }
    }, 100);
})();
