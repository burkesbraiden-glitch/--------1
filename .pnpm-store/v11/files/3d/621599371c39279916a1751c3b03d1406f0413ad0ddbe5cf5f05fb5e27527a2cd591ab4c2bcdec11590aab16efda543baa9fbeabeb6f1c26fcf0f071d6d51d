"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.initUts2jsSharedDataOptions = exports.initSourceFileCallback = exports.uniSharedDataPlugin = void 0;
const uts_1 = require("../uts");
const pages_1 = require("../json/pages");
const utils_1 = require("../utils");
const asset_1 = require("../vite/plugins/vitejs/plugins/asset");
const x_1 = require("../x");
const manifest_1 = require("../json/uni-x/manifest");
const manifest_2 = require("../json/manifest");
function initSharedDataOptions() {
    const compiler = require('@dcloudio/compiler-vapor-dom2');
    const manifest = (0, manifest_2.parseManifestJsonOnce)(process.env.UNI_INPUT_DIR);
    return {
        platform: process.env.UNI_UTS_PLATFORM,
        compilerVaporDom2: compiler,
        utsCompiler: (0, uts_1.resolveUTSCompiler)(),
        isUniPageFile: pages_1.isUniPageFile,
        getSharedDataResult: compiler.getSharedDataResult,
        getAssetFilenameById: asset_1.getAssetFilenameById,
        uvueScriptEngine: (0, x_1.isUniAppXAndroidNative)() ? 'native' : 'js',
        compilerVersion: process.env.HX_Version || process.env.UNI_COMPILER_VERSION,
        androidOptions: (0, x_1.isUniAppXAndroidJsEngine)()
            ? {
                package: process.env.UNI_COMPILE_TARGET === 'ext-api'
                    ? 'io.dcloud.uniapp.extapi'
                    : (0, manifest_1.parseUniXAppAndroidPackage)(manifest.appid),
            }
            : undefined,
    };
}
function uniSharedDataPlugin() {
    return (0, utils_1.requireUniHelpers)().USDP(initSharedDataOptions());
}
exports.uniSharedDataPlugin = uniSharedDataPlugin;
function initSourceFileCallback() {
    if (process.env.UNI_APP_X_DOM2 === 'true' && (0, x_1.isUniAppXAndroidNative)()) {
        const { TSDBSF } = (0, utils_1.requireUniHelpers)();
        const options = initSharedDataOptions();
        return (sourceFile) => {
            TSDBSF(sourceFile, options);
        };
    }
}
exports.initSourceFileCallback = initSourceFileCallback;
function initUts2jsSharedDataOptions() {
    if (process.env.UNI_APP_X_DOM2 === 'true') {
        return {
            resolveFieldMeta: require('@dcloudio/compiler-vapor-dom2')
                .resolveSharedDataFieldMeta,
        };
    }
}
exports.initUts2jsSharedDataOptions = initUts2jsSharedDataOptions;
