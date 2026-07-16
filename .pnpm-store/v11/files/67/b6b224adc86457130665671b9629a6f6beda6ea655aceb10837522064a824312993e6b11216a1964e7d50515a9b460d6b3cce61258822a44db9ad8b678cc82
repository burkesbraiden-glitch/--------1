"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.onCompileLog = exports.output = exports.resetOutput = exports.formatWarnMsg = exports.formatInfoMsg = exports.formatErrMsg = void 0;
const picocolors_1 = __importDefault(require("picocolors"));
const constants_1 = require("../constants");
const utils_1 = require("../vite/utils/utils");
const log_1 = require("../hbx/log");
const utils_2 = require("../vite/plugins/vitejs/utils");
var format_1 = require("./format");
Object.defineProperty(exports, "formatErrMsg", { enumerable: true, get: function () { return format_1.formatErrMsg; } });
Object.defineProperty(exports, "formatInfoMsg", { enumerable: true, get: function () { return format_1.formatInfoMsg; } });
Object.defineProperty(exports, "formatWarnMsg", { enumerable: true, get: function () { return format_1.formatWarnMsg; } });
let lastType;
let lastMsg;
function resetOutput(type) {
    if (type === lastType) {
        lastType = undefined;
        lastMsg = '';
    }
}
exports.resetOutput = resetOutput;
function output(type, msg) {
    if (type === lastType && msg === lastMsg) {
        return;
    }
    lastMsg = msg;
    lastType = type;
    const method = type === 'info' ? 'log' : type;
    console[method](msg);
}
exports.output = output;
function onCompileLog(type, error, code, relativeFileName, options) {
    const char = type === 'warn' ? constants_1.SPECIAL_CHARS.WARN_BLOCK : constants_1.SPECIAL_CHARS.ERROR_BLOCK;
    if (options?.plugin) {
        // CSS 插件格式
        const colorFn = type === 'warn' ? picocolors_1.default.yellow : (s) => s;
        console[type](char + colorFn(`[plugin:${options.plugin}] ${error.message}`));
        let msg = (0, log_1.formatAtFilename)(relativeFileName, options.line, options.column);
        if (options.line && options.column) {
            msg += `\n${(0, utils_2.generateCodeFrame)(code, {
                line: options.line,
                column: options.column,
            }).replace(/\t/g, ' ')}\n`;
        }
        console.log(msg + char);
    }
    else {
        console[type](char + type + ': ' + error.message + (error.loc ? '' : char));
        if (error.loc) {
            const start = error.loc.start;
            console.log('at ' + relativeFileName + ':' + start.line + ':' + start.column);
            console.log((0, utils_1.generateCodeFrameColumns)(code, error.loc) + char);
        }
    }
}
exports.onCompileLog = onCompileLog;
