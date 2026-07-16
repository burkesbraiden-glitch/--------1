"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.isUniAppXAndroidNative = exports.isUniAppXAndroidJsEngine = exports.isUniAppXJsEngine = exports.isUniAppXAndroidVapor = exports.isUniAppXVapor = exports.isUniAppXIOS = exports.isUniAppXAndroid = exports.isUniAppX = void 0;
function isUniAppX() {
    return process.env.UNI_APP_X === 'true';
}
exports.isUniAppX = isUniAppX;
function isUniAppXAndroid(platform = process.env.UNI_UTS_PLATFORM) {
    return isUniAppX() && platform === 'app-android';
}
exports.isUniAppXAndroid = isUniAppXAndroid;
function isUniAppXIOS(platform = process.env.UNI_UTS_PLATFORM) {
    return isUniAppX() && platform === 'app-ios';
}
exports.isUniAppXIOS = isUniAppXIOS;
function isUniAppXVapor() {
    return isUniAppX() && process.env.UNI_APP_X_DOM2 === 'true';
}
exports.isUniAppXVapor = isUniAppXVapor;
function isUniAppXAndroidVapor(platform = process.env.UNI_UTS_PLATFORM) {
    return isUniAppXAndroid(platform) && process.env.UNI_APP_X_DOM2 === 'true';
}
exports.isUniAppXAndroidVapor = isUniAppXAndroidVapor;
function isUniAppXJsEngine() {
    return isUniAppX() && process.env.UNI_APP_X_UVUE_SCRIPT_ENGINE === 'js';
}
exports.isUniAppXJsEngine = isUniAppXJsEngine;
function isUniAppXAndroidJsEngine(platform = process.env.UNI_UTS_PLATFORM) {
    return (isUniAppXAndroid(platform) &&
        process.env.UNI_APP_X_UVUE_SCRIPT_ENGINE === 'js');
}
exports.isUniAppXAndroidJsEngine = isUniAppXAndroidJsEngine;
function isUniAppXAndroidNative(platform = process.env.UNI_UTS_PLATFORM) {
    return (isUniAppXAndroid(platform) &&
        // 非 Vapor 或者 Vapor 但使用 native 引擎
        (process.env.UNI_APP_X_DOM2 !== 'true' ||
            process.env.UNI_APP_X_UVUE_SCRIPT_ENGINE === 'native'));
}
exports.isUniAppXAndroidNative = isUniAppXAndroidNative;
