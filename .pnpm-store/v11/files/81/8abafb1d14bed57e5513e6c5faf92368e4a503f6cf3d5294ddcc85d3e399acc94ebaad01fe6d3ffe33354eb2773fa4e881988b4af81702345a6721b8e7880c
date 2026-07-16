"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveAppRootScrollViewEditRangesByCode = exports.warnDom2RootScrollView = exports.resolveDom2RootScrollViewWarnLocation = exports.hasAppRootScrollViewWrappedByIfdef = exports.resolveAppRootScrollViewEditRanges = void 0;
const fs_extra_1 = require("fs-extra");
const path_1 = require("path");
const compiler_sfc_1 = require("@vue/compiler-sfc");
const json_1 = require("../json");
const logs_1 = require("../logs");
const messages_1 = require("../messages");
const utils_1 = require("../utils");
const utils_2 = require("../vite/plugins/vitejs/utils");
const { preprocess: preprocessHtml } = require('../../lib/preprocess');
const TEMPLATE_BLOCK_RE = /<template\b[^>]*>([\s\S]*?)<\/template>/i;
const ROOT_SCROLL_VIEW_ATTR_RE = /^\s+style\s*=\s*(["'])\s*flex\s*:\s*1\s*;?\s*\1\s*$/;
const APP_ROOT_SCROLL_VIEW_RE = /^\s*<!--\s*#ifdef APP\s*-->\s*<scroll-view([^>]*)>[\s\S]*<\/scroll-view>\s*<!--\s*#endif\s*-->\s*$/;
const SPLIT_APP_ROOT_SCROLL_VIEW_RE = /^\s*<!--\s*#ifdef APP\s*-->\s*<scroll-view([^>]*)>\s*<!--\s*#endif\s*-->[\s\S]*<!--\s*#ifdef APP\s*-->\s*<\/scroll-view>\s*<!--\s*#endif\s*-->\s*$/;
/**
 * 批量定位由 `#ifdef APP` 包裹的根 scroll-view 需要移除的范围。
 * 只返回需要修改的行列号，不修改文件，也不返回修改后的文件内容。
 */
function resolveAppRootScrollViewEditRanges(vueFiles, inputDir) {
    const result = {};
    vueFiles.forEach((file) => {
        const filename = resolveVueFilename(inputDir, file);
        if (!(0, fs_extra_1.existsSync)(filename)) {
            return;
        }
        const content = (0, fs_extra_1.readFileSync)(filename, 'utf8');
        const ranges = resolveAppRootScrollViewEditRangesByCode(content, filename);
        if (ranges.length) {
            result[file] = ranges;
        }
    });
    return result;
}
exports.resolveAppRootScrollViewEditRanges = resolveAppRootScrollViewEditRanges;
/**
 * 蒸汽模式下，页面根节点会自动补一个 scroll-view。
 * 这里仅用正则做精确匹配：命中范围宁可保守，也不能误报。
 */
function hasAppRootScrollViewWrappedByIfdef(code) {
    const templateContent = getTemplateContent(code);
    if (!templateContent) {
        return false;
    }
    return (matchesAppRootScrollViewTemplate(templateContent, APP_ROOT_SCROLL_VIEW_RE) ||
        matchesAppRootScrollViewTemplate(templateContent, SPLIT_APP_ROOT_SCROLL_VIEW_RE));
}
exports.hasAppRootScrollViewWrappedByIfdef = hasAppRootScrollViewWrappedByIfdef;
/**
 * 仅在 dom2 页面整文件预处理时定位需要提示优化建议的根 scroll-view 节点。
 */
function resolveDom2RootScrollViewWarnLocation(code, filename, isVueSubRequest) {
    if (process.env.UNI_PLATFORM !== 'app' ||
        process.env.UNI_APP_X_DOM2 !== 'true' ||
        isVueSubRequest ||
        !(0, json_1.parseUniXPageOptions)(filename) ||
        !code.includes('scroll-view') ||
        !code.includes('#ifdef APP')) {
        return;
    }
    if (!hasAppRootScrollViewWrappedByIfdef(code)) {
        return;
    }
    return resolveAppRootScrollViewNodeLocByCode(code, filename);
}
exports.resolveDom2RootScrollViewWarnLocation = resolveDom2RootScrollViewWarnLocation;
function warnDom2RootScrollView(code, filename, isVueSubRequest) {
    const location = resolveDom2RootScrollViewWarnLocation(code, filename, isVueSubRequest);
    if (!location) {
        return;
    }
    (0, logs_1.onCompileLog)('warn', {
        message: messages_1.M['dom2.root.scroll.view'],
        name: 'Warn',
        loc: location.loc,
    }, createWarnCodeFrameSource(location), (0, utils_1.normalizePath)((0, path_1.relative)(process.env.UNI_INPUT_DIR, filename)));
}
exports.warnDom2RootScrollView = warnDom2RootScrollView;
function resolveVueFilename(inputDir, file) {
    if ((0, path_1.isAbsolute)(file)) {
        const root = (0, path_1.parse)(file).root;
        // HBuilderX/uni-app 里页面路径可能写成 `/pages/a/b.uvue`，
        // 这种是项目内绝对路径，不是磁盘绝对路径，需要仍然基于 inputDir 解析。
        if (root === '/' || root === '\\') {
            return (0, path_1.resolve)(inputDir, removeLeadingRootSlash(file));
        }
        return file;
    }
    return (0, path_1.resolve)(inputDir, file);
}
function removeLeadingRootSlash(file) {
    let index = 0;
    while (file.charAt(index) === '/' || file.charAt(index) === '\\') {
        index++;
    }
    return file.slice(index);
}
function getTemplateContent(code) {
    return code.match(TEMPLATE_BLOCK_RE)?.[1];
}
function matchesAppRootScrollViewTemplate(template, regex) {
    const match = template.match(regex);
    return !!match && ROOT_SCROLL_VIEW_ATTR_RE.test(match[1]);
}
function resolveAppRootScrollViewNodeLocByCode(code, filename) {
    const template = parseSfcTemplate(code, filename);
    if (!template) {
        return;
    }
    const children = template.ast.children;
    if (children.length !== 3) {
        return;
    }
    const [, scrollViewNode] = children;
    if (!isRootScrollView(scrollViewNode)) {
        return;
    }
    return {
        loc: createStartTagLoc(code, scrollViewNode),
        source: resolveStartTagSource(scrollViewNode),
    };
}
function createStartTagLoc(code, node) {
    const source = node.loc.source || '';
    const endOffsetInSource = source.indexOf('>');
    if (endOffsetInSource === -1) {
        return {
            start: node.loc.start,
            end: node.loc.end,
        };
    }
    return (0, utils_2.offsetToStartAndEnd)(code, node.loc.start.offset, node.loc.start.offset + endOffsetInSource + 1);
}
function resolveStartTagSource(node) {
    const source = node.loc.source || '';
    const endOffsetInSource = source.indexOf('>');
    if (endOffsetInSource === -1) {
        return source;
    }
    return source.slice(0, endOffsetInSource + 1);
}
function createWarnCodeFrameSource(location) {
    return `${'\n'.repeat(Math.max(location.loc.start.line - 1, 0))}${location.source}`;
}
function resolveAppRootScrollViewEditRangesByCode(code, filename) {
    const template = parseSfcTemplate(code, filename);
    if (!template) {
        return [];
    }
    const children = template.ast.children;
    if (children.length !== 3) {
        return [];
    }
    const [ifdefNode, scrollViewNode, endifNode] = children;
    if (!isAppIfdefComment(ifdefNode) ||
        !isRootScrollView(scrollViewNode) ||
        !isEndifComment(endifNode)) {
        return [];
    }
    // 使用项目既有的条件编译实现先跑一遍，再交给 Vue 编译器确认 APP 分支根节点。
    if (!isPreprocessedRootScrollView(template.content, filename)) {
        return [];
    }
    return createRootScrollViewEditRanges(ifdefNode, scrollViewNode, endifNode);
}
exports.resolveAppRootScrollViewEditRangesByCode = resolveAppRootScrollViewEditRangesByCode;
function parseSfcTemplate(code, filename) {
    const { descriptor, errors } = (0, compiler_sfc_1.parse)(code, {
        filename,
        sourceMap: false,
    });
    if (errors.length || !descriptor.template?.ast) {
        return;
    }
    return {
        content: descriptor.template.content,
        ast: descriptor.template.ast,
    };
}
function isPreprocessedRootScrollView(content, filename) {
    try {
        const preprocessed = preprocessHtml(content, createAppPreContext(), {
            type: 'html',
        });
        const template = parseSfcTemplate(`<template>${preprocessed}</template>`, filename);
        const root = template?.ast.children[0];
        return (!!root && template.ast.children.length === 1 && root.tag === 'scroll-view');
    }
    catch (e) {
        return false;
    }
}
function createAppPreContext() {
    // 这里只声明本函数需要的 APP/UVue 上下文，避免改动全局条件编译上下文。
    return {
        APP: true,
        APP_UVUE: true,
        UNI_APP_X: true,
        VUE3: true,
        VUE3_VAPOR: true,
    };
}
function isAppIfdefComment(node) {
    return (node.type === 3 /* NodeTypes.COMMENT */ && node.content?.trim() === '#ifdef APP');
}
function isEndifComment(node) {
    return node.type === 3 /* NodeTypes.COMMENT */ && node.content?.trim() === '#endif';
}
function isRootScrollView(node) {
    return (node.type === 1 /* NodeTypes.ELEMENT */ &&
        node.tag === 'scroll-view' &&
        hasOnlyFlexStyle(node));
}
function hasOnlyFlexStyle(node) {
    if (!node.props || node.props.length !== 1) {
        return false;
    }
    const style = node.props[0];
    return (style.type === 6 /* NodeTypes.ATTRIBUTE */ &&
        style.name === 'style' &&
        !!style.value &&
        normalizeFlexStyle(style.value.content) === 'flex:1');
}
function normalizeFlexStyle(style) {
    let normalized = '';
    for (let i = 0; i < style.length; i++) {
        const char = style.charAt(i);
        if (char !== ' ' && char !== '\t' && char !== '\n' && char !== '\r') {
            normalized += char;
        }
    }
    if (normalized.endsWith(';')) {
        return normalized.slice(0, -1);
    }
    return normalized;
}
function createRootScrollViewEditRanges(ifdefNode, scrollViewNode, endifNode) {
    const children = scrollViewNode.children || [];
    if (!children.length) {
        return [createEditRange(ifdefNode, endifNode)];
    }
    const firstChild = children[0];
    const lastChild = children[children.length - 1];
    // 兼容如下写法：条件编译分别包裹 scroll-view 的开始标签和结束标签。
    // <!-- #ifdef APP -->
    // <scroll-view style="flex:1">
    // <!-- #endif -->
    //   ...
    // <!-- #ifdef APP -->
    // </scroll-view>
    // <!-- #endif -->
    if (isEndifComment(firstChild) && isAppIfdefComment(lastChild)) {
        return [
            createEditRangeByLoc(ifdefNode.loc.start, firstChild.loc.end),
            createEditRangeByLoc(lastChild.loc.start, endifNode.loc.end),
        ];
    }
    return [
        createEditRangeByLoc(ifdefNode.loc.start, firstChild.loc.start, true),
        createEditRangeByLoc(lastChild.loc.end, endifNode.loc.end),
    ];
}
function createEditRange(startNode, endNode) {
    return createEditRangeByLoc(startNode.loc.start, endNode.loc.end);
}
function createEditRangeByLoc(start, end, preserveEndIndent = false) {
    const range = {
        start: toPosition(start),
        end: toPosition(end),
        preserveLineBreaks: true,
    };
    if (preserveEndIndent) {
        range.preserveEndIndent = true;
    }
    return range;
}
function toPosition(loc) {
    return {
        line: loc.line,
        column: loc.column,
    };
}
