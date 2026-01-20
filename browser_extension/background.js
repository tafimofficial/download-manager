// Context Menu
chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: "turboDownload",
        title: "Download with Turbo",
        contexts: ["link"]
    });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === "turboDownload") {
        sendToTurbo(info.linkUrl);
    }
});

// Download Interception
const ALLOWED_EXTS = new Set([
    '3GP', '7Z', 'AAC', 'ACE', 'AIF', 'APK', 'ARJ', 'ASF', 'AVI', 'BIN', 'BZ2', 'EXE', 'GZ', 'GZIP', 'IMG', 'ISO', 'LZH',
    'M4A', 'M4V', 'MKV', 'MOV', 'MP3', 'MP4', 'MPA', 'MPE', 'MPEG', 'MPG', 'MSI', 'MSU', 'OGG', 'OGV', 'PDF', 'PLJ',
    'PPS', 'PPT', 'QT', 'RA', 'RAR', 'RM', 'RMVB', 'SEA', 'SIT', 'SITX', 'TAR', 'TIF', 'TIFF', 'WAV', 'WMA', 'WMV', 'Z', 'ZIP'
]);

function isAllowed(url) {
    try {
        const path = new URL(url).pathname.toLowerCase();
        const ext = path.split('.').pop().toUpperCase();

        if (ALLOWED_EXTS.has(ext)) return true;

        // Handle wildcards R0* and R1* (RAR parts)
        if (/R0\d+$/i.test(ext) || /R1\d+$/i.test(ext)) return true;

        return false;
    } catch (e) {
        return false;
    }
}

chrome.downloads.onCreated.addListener((downloadItem) => {
    // MV3 Service Worker wake-up check
    chrome.storage.session.get(["sessionStart"], (result) => {
        let start = result.sessionStart;
        if (!start) {
            start = Date.now();
            chrome.storage.session.set({ sessionStart: start });
        }

        // 2-second grace period for Browser Session Restore
        if (Date.now() - start < 2000) {
            return;
        }

        if (downloadItem.url.startsWith('http') && isAllowed(downloadItem.url)) {
            // 1. Pause immediately so it doesn't make progress in the browser
            chrome.downloads.pause(downloadItem.id, () => {
                // 2. Try to send to Turbo App
                sendToTurbo(downloadItem.url)
                    .then(() => {
                        // Success: App took it. Cancel and Erase from browser history/shelf.
                        chrome.downloads.cancel(downloadItem.id, () => {
                            chrome.downloads.erase({ id: downloadItem.id });
                        });
                        console.log("Handed off to Turbo Downloader");
                    })
                    .catch((err) => {
                        // Fail: App not running. Resume in browser.
                        console.log("App not reachable, resuming in browser.", err);
                        chrome.downloads.resume(downloadItem.id);
                    });
            });
        }
    }); // End storage.get
});

function sendToTurbo(url) {
    return fetch(`http://localhost:5555/add?url=${encodeURIComponent(url)}`);
}
