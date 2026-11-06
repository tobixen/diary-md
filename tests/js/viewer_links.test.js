// Run by tests/test_viewer_js.py: node tests/js/viewer_links.test.js
const assert = require('node:assert/strict');
const path = require('node:path');
const { MarkdownViewerBase, CollapsibleManager } = require(path.join(__dirname, '..', '..', 'viewer', 'md-viewer-common.js'));

const v = new MarkdownViewerBase('unused');
const tests = {
    'a day is linked as #YYYY-MM-DD': () => {
        assert.equal(v.dayFromHash('#2026-10-15'), '2026-10-15');
    },
    'anything else is no day': () => {
        for (const hash of ['', '#', '#top', '#2026-10-15x', '#<b>', undefined]) {
            assert.equal(v.dayFromHash(hash), null, String(hash));
        }
    },
    'collapsible headers get one click listener however often init runs': () => {
        let listeners = 0;
        const container = { addEventListener: () => listeners++ };
        global.document = { querySelector: () => container };
        const m = new CollapsibleManager('#c');
        m.init();
        m.init();
        assert.equal(listeners, 1);
        delete global.document;
    },
};

let failed = 0;
for (const [name, fn] of Object.entries(tests)) {
    try { fn(); } catch (e) { failed++; console.log(`FAIL ${name}: ${e.message}`); }
}
if (failed) process.exit(1);
console.log(`${Object.keys(tests).length} passed`);
