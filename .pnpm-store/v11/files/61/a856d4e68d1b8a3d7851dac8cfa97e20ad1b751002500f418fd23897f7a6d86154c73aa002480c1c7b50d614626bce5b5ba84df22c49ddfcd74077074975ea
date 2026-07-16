"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createDefaultSFCStyleBlock = exports.findMiniProgramComponentStyleIsolation = exports.updateMiniProgramComponentStyleIsolation = exports.parseStyleIsolation = exports.parseExternalClasses = exports.updateMiniProgramComponentExternalClasses = exports.findMiniProgramComponentExternalClasses = exports.hasExternalClasses = exports.clearPageExternalClasses = exports.addPageExternalClasses = exports.updatePageExternalClasses = exports.findPageExternalClasses = void 0;
const types_1 = require("@babel/types");
const estree_walker_1 = require("estree-walker");
const utils_1 = require("../utils");
const externalClassesCache = new Map();
const pageStyleIsolationCache = new Map();
const pageExternalClassesCache = new Map();
function findPageExternalClasses(filename) {
    return pageExternalClassesCache.get((0, utils_1.normalizePath)(filename));
}
exports.findPageExternalClasses = findPageExternalClasses;
function updatePageExternalClasses(filename, info) {
    pageExternalClassesCache.set((0, utils_1.normalizePath)(filename), info);
}
exports.updatePageExternalClasses = updatePageExternalClasses;
function addPageExternalClasses(filename, staticClasses, hasDynamic, hasAppAndPageStyle) {
    const normalizedFilename = (0, utils_1.normalizePath)(filename);
    let info = pageExternalClassesCache.get(normalizedFilename);
    if (!info) {
        info = { staticClasses: new Set(), hasDynamic: false };
        pageExternalClassesCache.set(normalizedFilename, info);
    }
    staticClasses.forEach((cls) => info.staticClasses.add(cls));
    if (hasDynamic) {
        info.hasDynamic = true;
    }
    if (hasAppAndPageStyle) {
        info.hasAppAndPageStyle = true;
    }
}
exports.addPageExternalClasses = addPageExternalClasses;
function clearPageExternalClasses(filename) {
    pageExternalClassesCache.delete((0, utils_1.normalizePath)(filename));
}
exports.clearPageExternalClasses = clearPageExternalClasses;
function hasExternalClasses(code) {
    return code.includes('externalClasses');
}
exports.hasExternalClasses = hasExternalClasses;
function findMiniProgramComponentExternalClasses(filename) {
    return externalClassesCache.get((0, utils_1.normalizePath)(filename));
}
exports.findMiniProgramComponentExternalClasses = findMiniProgramComponentExternalClasses;
function updateMiniProgramComponentExternalClasses(filename, value) {
    externalClassesCache.set((0, utils_1.normalizePath)(filename), value);
}
exports.updateMiniProgramComponentExternalClasses = updateMiniProgramComponentExternalClasses;
function parseExternalClasses(ast) {
    const classes = [];
    estree_walker_1.walk(ast, {
        enter(child, parent) {
            if (!(0, types_1.isIdentifier)(child) || child.name !== 'externalClasses') {
                return;
            }
            // export default { externalClasses: ['my-class'] }
            if (!(0, types_1.isObjectProperty)(parent)) {
                return;
            }
            if (!(0, types_1.isArrayExpression)(parent.value)) {
                return;
            }
            parent.value.elements.forEach((element) => {
                if ((0, types_1.isStringLiteral)(element)) {
                    classes.push(element.value);
                }
            });
        },
    });
    return classes;
}
exports.parseExternalClasses = parseExternalClasses;
function parseStyleIsolation(ast) {
    let styleIsolationValue = '';
    estree_walker_1.walk(ast, {
        enter(child, parent) {
            if (!(0, types_1.isIdentifier)(child) || child.name !== 'styleIsolation') {
                return;
            }
            if (!(0, types_1.isObjectProperty)(parent)) {
                return;
            }
            if (!(0, types_1.isStringLiteral)(parent.value)) {
                return;
            }
            if (parent.value.value === 'app' ||
                parent.value.value === 'app-and-page' ||
                parent.value.value === 'isolated') {
                styleIsolationValue = parent.value.value;
            }
            return parent.value.value;
        },
    });
    return styleIsolationValue;
}
exports.parseStyleIsolation = parseStyleIsolation;
/**
 * 目前只有小程序平台才会走这个逻辑
 * @param pagePahth
 * @param value
 * @param isPage
 */
function updateMiniProgramComponentStyleIsolation(pagePahth, value, isPage = false) {
    pageStyleIsolationCache.set((0, utils_1.normalizePath)(pagePahth), {
        styleIsolation: value,
        isPage,
    });
}
exports.updateMiniProgramComponentStyleIsolation = updateMiniProgramComponentStyleIsolation;
function findMiniProgramComponentStyleIsolation(pagePahth) {
    return pageStyleIsolationCache.get((0, utils_1.normalizePath)(pagePahth));
}
exports.findMiniProgramComponentStyleIsolation = findMiniProgramComponentStyleIsolation;
function createDefaultSFCStyleBlock(source) {
    const offset = source.length;
    return {
        type: 'style',
        content: '',
        attrs: {},
        loc: {
            source: '',
            start: { line: 1, column: 1, offset },
            end: { line: 1, column: 1, offset },
        },
    };
}
exports.createDefaultSFCStyleBlock = createDefaultSFCStyleBlock;
