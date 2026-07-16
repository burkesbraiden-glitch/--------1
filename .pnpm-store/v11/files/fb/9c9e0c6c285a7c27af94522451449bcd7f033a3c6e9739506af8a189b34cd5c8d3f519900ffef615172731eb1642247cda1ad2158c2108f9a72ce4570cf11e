"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.ANY_JS_STYLE_PLACEHOLDER_RE = exports.createJsStylePlaceholderRegExp = exports.createJsStylePlaceholder = exports.JS_STYLE_PLACEHOLDER_MARKER = void 0;
const hash_sum_1 = __importDefault(require("hash-sum"));
exports.JS_STYLE_PLACEHOLDER_MARKER = '__js_style_placeholder__';
function createJsStylePlaceholder(id) {
    const hashId = (0, hash_sum_1.default)(id);
    return JSON.stringify({
        [exports.JS_STYLE_PLACEHOLDER_MARKER]: hashId,
    });
}
exports.createJsStylePlaceholder = createJsStylePlaceholder;
function createJsStylePlaceholderRegExp(id) {
    const hashId = (0, hash_sum_1.default)(id);
    return new RegExp(`\\{\\s*"${exports.JS_STYLE_PLACEHOLDER_MARKER}"\\s*:\\s*"${hashId}"\\s*\\}`, 'g');
}
exports.createJsStylePlaceholderRegExp = createJsStylePlaceholderRegExp;
exports.ANY_JS_STYLE_PLACEHOLDER_RE = new RegExp(`\\{\\s*"${exports.JS_STYLE_PLACEHOLDER_MARKER}"\\s*:\\s*".+?"\\s*\\}`, 'g');
