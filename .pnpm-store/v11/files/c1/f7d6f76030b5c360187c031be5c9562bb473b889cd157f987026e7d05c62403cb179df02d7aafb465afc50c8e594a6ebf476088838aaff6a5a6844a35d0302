"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.transformPartSelector = exports.transformScopedCss = void 0;
const tags_1 = require("./tags");
const logs_1 = require("../logs");
const uni_shared_1 = require("@dcloudio/uni-shared");
const HTML_TAG_SELECTOR_RE = new RegExp(`/\\*[\\s\\S]*?(?:\\*/|$)|[\\s,}](${Object.keys(tags_1.HTML_TO_MINI_PROGRAM_TAGS).join('|')})\\s*(?=,|\\{)`, 'g');
function transformScopedCss(cssCode) {
    checkHtmlTagSelector(cssCode);
    return cssCode.replace(/\[(data-v-[a-f0-9]{8})\]/gi, (_, scopedId) => {
        return '.' + scopedId;
    });
}
exports.transformScopedCss = transformScopedCss;
function transformPartSelector(cssCode) {
    return cssCode.replace(/::part\(([^)]+)\)/gi, (_, partName) => {
        return ' .' + (0, uni_shared_1.getPartClass)(partName.trim());
    });
}
exports.transformPartSelector = transformPartSelector;
function checkHtmlTagSelector(cssCode) {
    HTML_TAG_SELECTOR_RE.lastIndex = 0;
    let match;
    while ((match = HTML_TAG_SELECTOR_RE.exec(cssCode))) {
        const tag = match[1];
        if (tag) {
            (0, logs_1.output)('warn', `小程序端 style 暂不支持 ${tag} 标签选择器，推荐使用 class 选择器，详情参考：https://uniapp.dcloud.net.cn/tutorial/migration-to-vue3.html#style`);
            break;
        }
    }
}
