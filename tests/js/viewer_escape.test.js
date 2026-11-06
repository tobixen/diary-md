// Run by tests/test_viewer_js.py: node tests/js/viewer_escape.test.js
const assert = require('node:assert/strict');
const path = require('node:path');
const { MarkdownViewerBase } = require(path.join(__dirname, '..', '..', 'viewer', 'md-viewer-common.js'));

const v = new MarkdownViewerBase('unused');
const tests = {
    'raw HTML is escaped': () => {
        const html = v.markdownToHtml('a <img src=x onerror=alert(1)> b');
        assert.ok(!html.includes('<img'), html);
        assert.ok(html.includes('&lt;img'), html);
    },
    'headers and list items are escaped': () => {
        const html = v.markdownToHtml('# <b>x</b>\n\n* <script>y</script>');
        assert.ok(!html.includes('<b>') && !html.includes('<script>'), html);
    },
    'javascript: links are not links': () => {
        const html = v.markdownToHtml('[click](javascript:alert(1))');
        assert.ok(!html.includes('href'), html);
        assert.ok(html.includes('click'), html);
    },
    'http(s) and relative links are kept': () => {
        for (const url of ['https://example.com/a?b=1&c=2', 'http://example.com', '/solveig/x.html', 'x.html', '#top']) {
            const html = v.markdownToHtml(`[t](${url})`);
            assert.ok(html.includes('<a href="'), `${url}: ${html}`);
        }
    },
    'mailto: and relative links with a colon are kept': () => {
        for (const url of ['mailto:a@example.com', 'x.html#a:b', '?t=12:30', '/log/12:30']) {
            const html = v.markdownToHtml(`[t](${url})`);
            assert.ok(html.includes('<a href="'), `${url}: ${html}`);
        }
        for (const url of ['tel:123', 'data:text/html,x', ' javascript:alert(1)']) {
            const html = v.markdownToHtml(`[t](${url})`);
            assert.ok(!html.includes('href'), `${url}: ${html}`);
        }
    },
    'no markup inside an href': () => {
        const html = v.markdownToHtml('[*t*](https://a.example.com/*y*/**z**)');
        assert.ok(html.includes('<a href="https://a.example.com/*y*/**z**"><em>t</em></a>'), html);
        assert.ok(!v.highlightText(html, 'y').includes('*<span'), v.highlightText(html, 'y'));
    },
    'search terms with special characters are highlighted': () => {
        const html = v.markdownToHtml('R&D <3');
        assert.equal(v.highlightText(html, 'r&d'), '<p><span class="highlight">R&amp;D</span> &lt;3</p>\n');
        assert.equal(v.highlightText(html, '<3'), '<p>R&amp;D <span class="highlight">&lt;3</span></p>\n');
    },
    'a quote cannot leave the href attribute': () => {
        const html = v.markdownToHtml('[t](https://example.com/" onmouseover="alert(1))');
        assert.ok(!html.includes('" onmouseover'), html);
    },
    'bold and italic still work': () => {
        assert.equal(v.markdownToHtml('**a** and *b*'), '<p><strong>a</strong> and <em>b</em></p>\n');
    },
    'highlight leaves tags and entities alone': () => {
        const html = v.highlightText('<p class="x">class &amp; amp</p>', 'class');
        assert.equal(html, '<p class="x"><span class="highlight">class</span> &amp; amp</p>');
        assert.equal(v.highlightText('<p>&amp; amp</p>', 'amp'), '<p>&amp; <span class="highlight">amp</span></p>');
    },
    'highlight escapes nothing it should not': () => {
        assert.equal(v.highlightText('<p>a b</p>', 'b'), '<p>a <span class="highlight">b</span></p>');
    },
    'escapeHtml': () => {
        assert.equal(v.escapeHtml(`<a href="x">'&`), '&lt;a href=&quot;x&quot;&gt;&#39;&amp;');
    },
};

let failed = 0;
for (const [name, fn] of Object.entries(tests)) {
    try { fn(); } catch (e) { failed++; console.log(`FAIL ${name}: ${e.message}`); }
}
if (failed) process.exit(1);
console.log(`${Object.keys(tests).length} passed`);
