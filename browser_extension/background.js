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
    if (downloadItem.url.startsWith('http') && isAllowed(downloadItem.url)) {
        // Automatically notify the app to catch the download
        sendToTurbo(downloadItem.url);

        // Cancel the browser download to avoid duplicates
        chrome.downloads.cancel(downloadItem.id);
    }
});

function sendToTurbo(url) {
    fetch(`http://localhost:5555/add?url=${encodeURIComponent(url)}`)
        .then(response => {
            console.log("Sent to Turbo Downloader!");
        })
        .catch(error => {
            console.error("Error sending to Turbo. Is the app running?", error);
        });
}
