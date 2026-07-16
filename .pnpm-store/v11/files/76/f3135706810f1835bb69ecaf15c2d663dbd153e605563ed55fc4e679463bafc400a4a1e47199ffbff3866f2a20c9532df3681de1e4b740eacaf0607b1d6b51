"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.initVueTemplateCompilerExtraOptions = void 0;
const path_1 = __importDefault(require("path"));
const utils_1 = require("../utils");
const json_1 = require("../json");
const vue_1 = require("../vue");
function initVueTemplateCompilerExtraOptions(descriptor) {
    const filename = (0, utils_1.normalizePath)(descriptor.filename.split('?')[0]);
    const relativeFilename = (0, utils_1.normalizePath)(path_1.default.relative(process.env.UNI_INPUT_DIR, filename));
    const rootScrollView = (0, json_1.parseUniXPageOptions)(filename);
    const componentType = rootScrollView || (0, json_1.isUniPageFile)(filename) ? 'page' : 'component';
    const isDevX = process.env.UNI_HX_VERSION_DEV === 'true' &&
        process.env.UNI_APP_X === 'true';
    const isDynamic = process.env.UNI_APP_X_DOM2_DYNAMIC === 'true';
    let disableStaticStyle = false;
    if (isDevX &&
        // 动态渲染时，仍旧使用静态样式，避免性能问题。
        !isDynamic &&
        process.env.NODE_ENV === 'development') {
        if (process.env.UNI_UTS_PLATFORM === 'app-harmony') {
            // 开发版本、开发模式下，非鸿蒙release模式打包
            disableStaticStyle = process.env.UNI_APP_HARMONY_RUN_MODE !== 'release';
        }
    }
    const helper = (0, utils_1.requireUniHelpers)();
    return {
        root: (0, utils_1.normalizePath)(process.env.UNI_INPUT_DIR),
        platform: process.env.UNI_UTS_PLATFORM,
        componentType,
        filename: filename,
        relativeFilename,
        helper,
        enableRootScrollViewTransform: true,
        // 仅页面透传 rootScrollView，避免非页面组件误触发 ROOT 自动包裹逻辑。
        rootScrollView: componentType === 'page' ? rootScrollView : undefined,
        scriptCppBlocks: descriptor.scriptCppBlocks,
        disableStaticStyle,
        onVueTemplateCompileLog(type, error) {
            return (0, vue_1.onVueTemplateCompileLog)(type, error, descriptor.source, relativeFilename);
        },
        r: helper.K,
        className: helper.GCN(descriptor.filename, process.env.UNI_INPUT_DIR),
        inlineRender: !isDynamic && process.env.UNI_UTS_PLATFORM === 'app-android',
    };
}
exports.initVueTemplateCompilerExtraOptions = initVueTemplateCompilerExtraOptions;
