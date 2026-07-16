"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.uniAppXAndroidEngineDevPlugin = void 0;
const uni_cli_shared_1 = require("@dcloudio/uni-cli-shared");
const path_1 = __importDefault(require("path"));
const fs_extra_1 = __importDefault(require("fs-extra"));
function uniAppXAndroidEngineDevPlugin() {
    const { compileVaporApp, getKotlinCompilerServer } = (0, uni_cli_shared_1.resolveUTSCompiler)();
    const compilerServer = getKotlinCompilerServer();
    if (!compilerServer) {
        console.error(`项目使用了uts插件，正在安装 uts Android 运行扩展...`);
        process.exit(0);
    }
    const outputDir = process.env.UNI_OUTPUT_DIR;
    const uvueOutputDir = (0, uni_cli_shared_1.uvueOutDir)('app-android');
    const { UKF } = (0, uni_cli_shared_1.requireUniHelpers)();
    const appId = (0, uni_cli_shared_1.parseManifestJsonOnce)(process.env.UNI_INPUT_DIR).appid || uni_cli_shared_1.DEFAULT_APPID;
    return {
        name: 'uni:app-x-android-dev',
        async writeBundle() {
            if (!compilerServer) {
                return;
            }
            if (process.env.UNI_APP_X_DOM2_CPP_CHANGED === 'true' ||
                process.env.UNI_APP_X_DOM2_KT_CHANGED === 'true') {
                const { changed, files } = UKF();
                await compileVaporApp({
                    filename: 'index.kt',
                    changed: changed,
                    chunks: files,
                    inputDir: uvueOutputDir,
                    outputDir: outputDir,
                });
            }
            if (process.env.UNI_APP_X_DOM2_CPP_CHANGED === 'true') {
                const soOutDir = process.env.UNI_APP_X_DOM2_SO_DIR;
                const res = await compilerServer.compileCpp({
                    appId,
                    projectPath: process.env.UNI_INPUT_DIR,
                    cppPath: process.env.UNI_APP_X_DOM2_CPP_DIR,
                    outDir: soOutDir,
                });
                if (res.code) {
                    throw new Error(res.msg);
                }
                const soList = res.data?.soList;
                if (!soList || !soList.length) {
                    return;
                }
                soList.forEach((so) => {
                    const soFile = path_1.default.resolve(soOutDir, so);
                    const targetSoFile = path_1.default.resolve(outputDir, so);
                    fs_extra_1.default.copySync(soFile, targetSoFile);
                });
            }
        },
    };
}
exports.uniAppXAndroidEngineDevPlugin = uniAppXAndroidEngineDevPlugin;
