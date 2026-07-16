"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.initDefine = void 0;
const utils_1 = require("../utils");
const env_1 = require("../hbx/env");
const json_1 = require("../json");
function initDefine(stringifyBoolean = false) {
    const manifestJson = (0, json_1.parseManifestJsonOnce)(process.env.UNI_INPUT_DIR);
    const platformManifestJson = (0, json_1.getPlatformManifestJsonOnce)();
    const isRunByHBuilderX = (0, env_1.runByHBuilderX)();
    const isDebug = !!manifestJson.debug;
    const isX = process.env.UNI_APP_X === 'true';
    const isNewStyleIsolation = process.env.UNI_APP_STYLE_ISOLATION_VERSION === '2';
    // 目前仅微信小程序支持^穿透
    const isNewStyleIsolationUpArrow = isNewStyleIsolation && process.env.UNI_PLATFORM === 'mp-weixin';
    const isMP = process.env.UNI_PLATFORM && process.env.UNI_PLATFORM.startsWith('mp-');
    process.env['UNI_APP_ID'] = manifestJson.appid;
    const mpXDefine = {
        __UNI_FEATURE_VIRTUAL_HOST__: isX && isMP && platformManifestJson.enableVirtualHost !== false,
    };
    const styleIsolation = stringifyBoolean
        ? JSON.stringify(isNewStyleIsolation)
        : isNewStyleIsolation;
    return {
        ...initCustomDefine(),
        'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV),
        'process.env.UNI_DEBUG': stringifyBoolean
            ? JSON.stringify(isDebug)
            : isDebug,
        'process.env.UNI_APP_ID': JSON.stringify(manifestJson.appid || ''),
        'process.env.UNI_APP_NAME': JSON.stringify(manifestJson.name || ''),
        'process.env.UNI_APP_VERSION_NAME': JSON.stringify(manifestJson.versionName || ''),
        'process.env.UNI_APP_VERSION_CODE': JSON.stringify(manifestJson.versionCode || ''),
        'process.env.UNI_PLATFORM': JSON.stringify(process.env.UNI_PLATFORM),
        'process.env.UNI_SUB_PLATFORM': JSON.stringify(process.env.UNI_SUB_PLATFORM || ''),
        'process.env.UNI_MP_PLUGIN': JSON.stringify(process.env.UNI_MP_PLUGIN || ''),
        'process.env.UNI_SUBPACKAGE': JSON.stringify(process.env.UNI_SUBPACKAGE || ''),
        'process.env.UNI_COMPILER_VERSION': JSON.stringify(process.env.UNI_COMPILER_VERSION || ''),
        'process.env.RUN_BY_HBUILDERX': stringifyBoolean
            ? JSON.stringify(isRunByHBuilderX)
            : isRunByHBuilderX,
        'process.env.UNI_AUTOMATOR_WS_ENDPOINT': JSON.stringify(process.env.UNI_AUTOMATOR_WS_ENDPOINT || ''),
        'process.env.UNI_AUTOMATOR_APP_WEBVIEW_SRC': JSON.stringify(process.env.UNI_AUTOMATOR_APP_WEBVIEW_SRC || ''),
        'process.env.UNI_CLOUD_PROVIDER': JSON.stringify(process.env.UNI_CLOUD_PROVIDER || ''),
        'process.env.UNICLOUD_DEBUG': JSON.stringify(process.env.UNICLOUD_DEBUG || ''),
        // 兼容旧版本
        'process.env.VUE_APP_PLATFORM': JSON.stringify(process.env.UNI_PLATFORM || ''),
        'process.env.VUE_APP_DARK_MODE': JSON.stringify(platformManifestJson.darkmode || false),
        __UNI_PRELOAD_SHADOW_IMAGE__: JSON.stringify(process.env.UNI_PLATFORM === 'mp-weixin' ? (0, utils_1.getShadowImagePath)('grey') : ''),
        ...mpXDefine,
        __X_STYLE_ISOLATION__: styleIsolation,
        __X_STYLE_ISOLATION_UP_ARROW__: stringifyBoolean
            ? JSON.stringify(isNewStyleIsolationUpArrow)
            : isNewStyleIsolationUpArrow,
        // 下边这个主要是为web服务，因为ssr目前只能识别process.env中的内容
        'process.env.UNI_APP_X_NEW_STYLE_ISOLATION': styleIsolation,
    };
}
exports.initDefine = initDefine;
function initCustomDefine() {
    let define = {};
    if (process.env.UNI_CUSTOM_DEFINE) {
        try {
            define = JSON.parse(process.env.UNI_CUSTOM_DEFINE);
        }
        catch (e) { }
    }
    return Object.keys(define).reduce((res, name) => {
        res['process.env.' + name] = JSON.stringify(define[name]);
        return res;
    }, {});
}
