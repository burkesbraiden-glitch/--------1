"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveUniAppXJsEngineIndexKotlinPath = exports.genUniAppXJsEngineIndexKotlinCode = void 0;
const uni_cli_shared_1 = require("@dcloudio/uni-cli-shared");
const shared_1 = require("@vue/shared");
const path_1 = __importDefault(require("path"));
function genUniAppXJsEngineIndexKotlinCode(manifestJson) {
    const pkg = (0, uni_cli_shared_1.parseUniXAppAndroidPackage)(manifestJson.appid);
    const configCode = genUniAppConfigKotlinCode(manifestJson);
    return `package ${pkg}

import io.dcloud.uniappxv.runtime.AppConfig
import io.dcloud.uts.*
import io.dcloud.uts.Map

${configCode}
`;
}
exports.genUniAppXJsEngineIndexKotlinCode = genUniAppXJsEngineIndexKotlinCode;
function resolveUniAppXJsEngineIndexKotlinPath() {
    const kotlinDir = process.env.UNI_APP_X_DOM2_KT_DIR;
    if (!kotlinDir) {
        throw new Error('UNI_APP_X_DOM2_KT_DIR is not set');
    }
    return path_1.default.resolve(kotlinDir, 'index.kt');
}
exports.resolveUniAppXJsEngineIndexKotlinPath = resolveUniAppXJsEngineIndexKotlinPath;
function genUniAppConfigKotlinCode(manifestJson) {
    const flexDir = (0, uni_cli_shared_1.parseUniXFlexDirection)(manifestJson);
    const flexDirCode = flexDir !== 'column'
        ? `override var flexDirection: String = ${stringifyKotlinString(flexDir)};`
        : '';
    const splashScreen = (0, uni_cli_shared_1.parseUniXSplashScreen)('app-android', manifestJson);
    const splashScreenCode = splashScreen && Object.keys(splashScreen).length > 0
        ? `override var splashScreen: Map<String, Any>? = ${stringifyKotlinValue(splashScreen)};`
        : '';
    const hasAppDefaultAppTheme = (0, uni_cli_shared_1.validateThemeValue)(manifestJson.app?.defaultAppTheme);
    const hasDefaultAppTheme = (0, uni_cli_shared_1.validateThemeValue)(manifestJson.defaultAppTheme);
    const defaultAppThemeCode = hasAppDefaultAppTheme
        ? `override var defaultAppTheme: String = ${stringifyKotlinString(manifestJson.app.defaultAppTheme)};`
        : hasDefaultAppTheme
            ? `override var defaultAppTheme: String = ${stringifyKotlinString(manifestJson.defaultAppTheme)};`
            : '';
    const codes = [flexDirCode, splashScreenCode, defaultAppThemeCode]
        .filter(Boolean)
        .join('\n    ');
    return `class UniAppConfig : AppConfig() {
    override var name: String = ${stringifyKotlinString(manifestJson.name || '')};
    override var appid: String = ${stringifyKotlinString(manifestJson.appid || '')};
    override var versionName: String = ${stringifyKotlinString(manifestJson.versionName || '')};
    override var versionCode: String = ${stringifyKotlinString('' + (manifestJson.versionCode || ''))};
    override var uniCompilerVersion: String = ${stringifyKotlinString(process.env.UNI_COMPILER_VERSION || '')};
    ${codes}
}`;
}
function stringifyKotlinString(value) {
    return JSON.stringify(value).replace(/\$/g, '\\$');
}
function stringifyKotlinValue(value) {
    if (value == null) {
        return 'null';
    }
    if (typeof value === 'string') {
        return stringifyKotlinString(value);
    }
    if (typeof value === 'number' || typeof value === 'boolean') {
        return String(value);
    }
    if (Array.isArray(value)) {
        return value.length
            ? `utsArrayOf(${value
                .map((item) => stringifyKotlinValue(item))
                .join(', ')})`
            : 'utsArrayOf<Any?>()';
    }
    if ((0, shared_1.isPlainObject)(value)) {
        const entries = Object.entries(value);
        return entries.length
            ? `utsMapOf(${entries
                .map(([key, item]) => `${stringifyKotlinString(key)} to ${stringifyKotlinValue(item)}`)
                .join(', ')})`
            : 'utsMapOf<String, Any?>()';
    }
    return stringifyKotlinString(String(value));
}
