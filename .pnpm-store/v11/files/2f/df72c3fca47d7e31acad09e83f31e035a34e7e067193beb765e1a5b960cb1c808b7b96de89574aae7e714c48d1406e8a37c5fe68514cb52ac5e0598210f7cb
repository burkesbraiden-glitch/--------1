"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.stopProfiler = exports.runBuild = exports.runDev = void 0;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const picocolors_1 = __importDefault(require("picocolors"));
const shared_1 = require("@vue/shared");
const vite_1 = require("vite");
const uni_cli_shared_1 = require("@dcloudio/uni-cli-shared");
const build_1 = require("./build");
const server_1 = require("./server");
const utils_1 = require("./utils");
const easycom_1 = require("../utils/easycom");
const uvue_1 = require("./uvue");
const configResolved_1 = require("../configResolved");
async function runDev(options) {
    (0, shared_1.extend)(options, {
        watch: {},
    });
    if (process.env.UNI_MINIMIZE === 'true') {
        ;
        options.minify = true;
    }
    (0, utils_1.initEnv)('dev', options);
    if ((0, uni_cli_shared_1.isUniAppXAndroidNative)()) {
        return (0, uvue_1.runUVueAndroidDev)(options);
    }
    const createLogger = await Promise.resolve().then(() => __importStar(require('vite'))).then(({ createLogger }) => createLogger);
    try {
        if (options.platform === 'h5') {
            const server = await (options.ssr
                ? (0, server_1.createSSRServer)(options)
                : (0, server_1.createServer)(options));
            (0, easycom_1.initEasycom)(server.watcher);
        }
        else {
            (0, easycom_1.initEasycom)();
            let isFirstStart = true;
            let isFirstEnd = true;
            await (0, build_1.build)(options, async (event) => {
                if (event.code === 'BUNDLE_START') {
                    if (isFirstStart) {
                        isFirstStart = false;
                        return;
                    }
                    (0, uni_cli_shared_1.output)('log', uni_cli_shared_1.M['dev.watching.start']);
                }
                else if (event.code === 'BUNDLE_END') {
                    event.result.close();
                    if (isFirstEnd) {
                        // 首次全量同步
                        if (options.platform === 'app' ||
                            options.platform === 'app-harmony' ||
                            options.platform === 'mp-harmony') {
                            process.env.UNI_APP_CHANGED_FILES = '';
                            process.env.UNI_APP_UTS_CHANGED = '';
                        }
                        if (options.platform === 'app') {
                            process.env.UNI_APP_CHANGED_PAGES = '';
                            process.env.UNI_APP_UTS_CHANGED_FILES = '';
                        }
                        isFirstEnd = false;
                        (0, uni_cli_shared_1.output)('log', uni_cli_shared_1.M['dev.watching.end']);
                        (0, utils_1.showRunPrompt)(options.platform);
                        (0, utils_1.printStartupDuration)(createLogger(options.logLevel), false);
                        if (process.env.UNI_UTS_ERRORS) {
                            console.error(process.env.UNI_UTS_ERRORS);
                        }
                        if (process.env.UNI_UTS_TIPS) {
                            console.warn(process.env.UNI_UTS_TIPS);
                        }
                        await (0, exports.stopProfiler)((message) => createLogger(options.logLevel).info(message));
                        return;
                    }
                    const utsChanged = process.env.UNI_APP_UTS_CHANGED === 'true';
                    process.env.UNI_APP_UTS_CHANGED = '';
                    let changedFiles = '';
                    let hasBinFiles = false;
                    if (options.platform === 'app') {
                        const files = process.env.UNI_APP_CHANGED_FILES;
                        const pages = process.env.UNI_APP_CHANGED_PAGES;
                        const dex = process.env.UNI_APP_UTS_CHANGED_FILES;
                        hasBinFiles = getHasBinFiles();
                        changedFiles = pages || files;
                        process.env.UNI_APP_CHANGED_PAGES = '';
                        process.env.UNI_APP_CHANGED_FILES = '';
                        process.env.UNI_APP_UTS_CHANGED_FILES = '';
                        if (process.env.UNI_APP_X_DOM2_DYNAMIC === 'true') {
                            process.env.UNI_APP_X_DOM2_BIN_CHANGED_FILES = '';
                        }
                        const hasIncrementalFiles = changedFiles &&
                            !changedFiles.includes(uni_cli_shared_1.APP_CONFIG_SERVICE) &&
                            !changedFiles.includes(uni_cli_shared_1.APP_SERVICE_FILENAME);
                        if (
                        // 目前动态渲染下，只要bin有变更，就需要全量同步，后续可以优化成bin变更时输出bin变更文件列表
                        !hasBinFiles &&
                            (hasIncrementalFiles || dex)) {
                            if (pages) {
                                return (0, uni_cli_shared_1.output)('log', uni_cli_shared_1.M['dev.watching.end.pages'].replace('{pages}', changedFiles));
                            }
                            return (0, uni_cli_shared_1.output)('log', uni_cli_shared_1.M['dev.watching.end.files'].replace('{files}', JSON.stringify(JSON.parse(changedFiles || JSON.stringify([])).concat(JSON.parse(dex || JSON.stringify([]))))));
                        }
                    }
                    else if (options.platform === 'app-harmony' ||
                        options.platform === 'mp-harmony') {
                        hasBinFiles = getHasBinFiles();
                        // 动态化且没有uts插件变更时，输出变更文件列表
                        if (process.env.UNI_APP_X_DOM2_DYNAMIC === 'true' &&
                            !utsChanged &&
                            !hasBinFiles) {
                            const changed = [];
                            const files = process.env.UNI_APP_CHANGED_FILES;
                            process.env.UNI_APP_CHANGED_PAGES = '';
                            if (files) {
                                try {
                                    changed.push(...JSON.parse(files));
                                }
                                catch { }
                            }
                            // 鸿蒙平台暂不启用 bin 文件热更新，先不合并到 changes 中。
                            // const binFiles = process.env.UNI_APP_X_DOM2_BIN_CHANGED_FILES
                            process.env.UNI_APP_X_DOM2_BIN_CHANGED_FILES = '';
                            // if (binFiles) {
                            //   try {
                            //     changed.push(...JSON.parse(binFiles))
                            //   } catch {}
                            // }
                            if (changed.length) {
                                return (0, uni_cli_shared_1.output)('log', uni_cli_shared_1.M['dev.watching.end.files'].replace('{files}', JSON.stringify(changed)));
                            }
                        }
                        // 鸿蒙平台cpp/uts插件变更需要整体编译
                        if (process.env.UNI_APP_X_DOM2_CPP_CHANGED !== 'true' &&
                            !utsChanged &&
                            !hasBinFiles) {
                            const files = process.env.UNI_APP_CHANGED_FILES;
                            process.env.UNI_APP_CHANGED_FILES = '';
                            if (files) {
                                return (0, uni_cli_shared_1.output)('log', uni_cli_shared_1.M['dev.watching.end.files'].replace('{files}', files));
                            }
                        }
                    }
                    // dom2 下仅 cpp/uts插件 变更需要整体编译
                    // 如果有changedFiles就增量输出，否则就不要输出，而是打印无变更，静态资源走额外的全量同步
                    // 之前之所以没有增量就全量同步，是为了兼容性，怕出意外。
                    if (process.env.UNI_APP_X_DOM2 === 'true') {
                        if (process.env.UNI_APP_X_DOM2_CPP_CHANGED === 'true' ||
                            utsChanged) {
                            return (0, uni_cli_shared_1.output)('log', uni_cli_shared_1.M['dev.watching.end']);
                        }
                        // 没有cpp/uts插件变更，且没有增量js/bin文件变更，就输出无变更
                        if (!changedFiles && !hasBinFiles) {
                            return (0, uni_cli_shared_1.output)('log', uni_cli_shared_1.M['uvue.dev.watching.end.empty']);
                        }
                    }
                    return (0, uni_cli_shared_1.output)('log', uni_cli_shared_1.M['dev.watching.end']);
                }
                else if (event.code === 'END') {
                    // 重要：1.0 的APP端是自实现的AppWatcher，它是不会触发END事件的，这里边的逻辑只有非1.0的APP端会触发
                    if (process.env.UNI_AUTOMATOR_WS_ENDPOINT) {
                        setTimeout(() => {
                            (0, uni_cli_shared_1.output)('log', uni_cli_shared_1.M['build.failed']);
                            process.exit(0);
                        }, 2000);
                    }
                }
                else if (event.code === 'ERROR') {
                    if ((0, uni_cli_shared_1.runByHBuilderX)()) {
                        setTimeout(() => {
                            console.error(`Build failed with errors.`);
                        });
                    }
                }
            });
        }
    }
    catch (e) {
        if (options.platform === 'h5') {
            console.error(`error when starting dev server:\n${e.stack || e}`);
        }
        else {
            console.error(`error during build:\n${e.stack || e}`);
        }
        process.exit(1);
    }
}
exports.runDev = runDev;
async function runBuild(options) {
    (0, utils_1.initEnv)('build', options);
    if ((0, uni_cli_shared_1.isUniAppXAndroidNative)()) {
        return (0, uvue_1.runUVueAndroidBuild)(options);
    }
    try {
        await (options.ssr && options.platform === 'h5'
            ? (0, build_1.buildSSR)(options)
            : (0, build_1.build)(options));
        await (0, exports.stopProfiler)((message) => (0, vite_1.createLogger)(options.logLevel).info(message));
        console.log(uni_cli_shared_1.M['build.done']);
        if (options.platform !== 'h5') {
            (0, utils_1.showRunPrompt)(options.platform);
        }
        // 开发者可能用了三方插件，三方插件有可能阻止退出，导致HBuilderX打包状态识别不正确
        if ((0, uni_cli_shared_1.isInHBuilderX)() ||
            /* 需要排查为什么ext-api编译时没有自动结束 */ process.env
                .UNI_COMPILE_TARGET === 'ext-api') {
            process.exit(0);
        }
    }
    catch (e) {
        if ((0, uni_cli_shared_1.isInHBuilderX)()) {
            (0, configResolved_1.initLogger)({
                logger: (0, vite_1.createLogger)(options.logLevel),
            }).error(e.message || e);
        }
        else {
            console.error(e.message || e);
        }
        console.error(`Build failed with errors.`);
        process.exit(1);
    }
}
exports.runBuild = runBuild;
let profileSession = global.__vite_profile_session;
let profileCount = 0;
const stopProfiler = (log) => {
    if (!profileSession)
        return;
    return new Promise((res, rej) => {
        profileSession.post('Profiler.stop', (err, result) => {
            // Write profile to disk, upload, etc.
            if (!err) {
                const outPath = path_1.default.resolve(process.env.UNI_INPUT_DIR, `./profile-${profileCount++}.cpuprofile`);
                fs_1.default.writeFileSync(outPath, JSON.stringify(result.profile));
                log(picocolors_1.default.yellow(`CPU profile written to ${picocolors_1.default.white(picocolors_1.default.dim(outPath))}`));
                profileSession = undefined;
                res();
            }
            else {
                rej(err);
            }
        });
    });
};
exports.stopProfiler = stopProfiler;
function getHasBinFiles() {
    const binFiles = process.env.UNI_APP_X_DOM2_DYNAMIC === 'true'
        ? process.env.UNI_APP_X_DOM2_BIN_CHANGED_FILES
        : '';
    return !!(binFiles && binFiles !== '[]');
}
