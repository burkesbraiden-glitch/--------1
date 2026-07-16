"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.createUniAppJsEnginePlugin = exports.initUniAppJsEngineDom1CssPlugin = void 0;
const path_1 = __importDefault(require("path"));
const fs_extra_1 = __importDefault(require("fs-extra"));
const uni_cli_shared_1 = require("@dcloudio/uni-cli-shared");
const utils_1 = require("../utils");
const css_1 = require("./css");
const js_1 = require("./js");
const rewriteImportVue_1 = require("./rewriteImportVue");
function initUniAppJsEngineDom1CssPlugin(config) {
    (0, uni_cli_shared_1.injectCssPlugin)(config, process.env.UNI_COMPILE_TARGET === 'uni_modules'
        ? {
            createUrlReplacer: uni_cli_shared_1.createEncryptCssUrlReplacer,
        }
        : {});
    (0, uni_cli_shared_1.injectCssPostPlugin)(config, (0, css_1.uniAppCssPlugin)(config));
}
exports.initUniAppJsEngineDom1CssPlugin = initUniAppJsEngineDom1CssPlugin;
function createUniAppJsEnginePlugin(platform) {
    return function uniAppJsEnginePlugin() {
        const inputDir = (0, uni_cli_shared_1.normalizePath)(process.env.UNI_INPUT_DIR);
        const outputDir = process.env.UNI_OUTPUT_DIR;
        const uvueOutputDir = (0, uni_cli_shared_1.uvueOutDir)(platform);
        const tscOutputDir = (0, uni_cli_shared_1.tscOutDir)(platform);
        // 开始编译时，清空输出目录
        function emptyOutDir() {
            // ext-api 编译时，需要同时编译多个平台，并保留多个平台的输出目录
            if (process.env.UNI_COMPILE_TARGET === 'ext-api') {
                return;
            }
            if (fs_extra_1.default.existsSync(outputDir)) {
                (0, uni_cli_shared_1.emptyDir)(outputDir);
            }
        }
        emptyOutDir();
        function emptyUVueDir() {
            if (fs_extra_1.default.existsSync(uvueOutputDir)) {
                (0, uni_cli_shared_1.emptyDir)(uvueOutputDir);
            }
        }
        emptyUVueDir();
        function emptyTscDir() {
            if (fs_extra_1.default.existsSync(tscOutputDir)) {
                (0, uni_cli_shared_1.emptyDir)(tscOutputDir);
            }
        }
        emptyTscDir();
        if (process.env.UNI_UTS_PLATFORM === 'app-harmony' &&
            (0, uni_cli_shared_1.isNormalCompileTarget)()) {
            // 拆分模式
            process.env.UNI_APP_OUTPUT_FORMAT = 'esm';
            // 动态导入
            process.env.UNI_APP_DYNAMIC_IMPORT = 'true';
        }
        const isESM = process.env.UNI_APP_OUTPUT_FORMAT === 'esm';
        const paths = isESM
            ? {
                // vue: '@dcloudio/uni-app-x-runtime',
                '@vue/shared': '@dcloudio/uni-app-x-runtime',
            }
            : {};
        const isDom2 = process.env.UNI_APP_X_DOM2 === 'true';
        const isAndroid = platform === 'app-android';
        const isIOS = platform === 'app-ios';
        const isHarmony = platform === 'app-harmony';
        const globals = {
            vue: 'Vue',
            '@vue/shared': 'uni.VueShared',
        };
        if (isDom2 && (isAndroid || isIOS)) {
            globals[utils_1.SHARED_DATA_LIB_NAME] = '__uniSharedDataLib';
        }
        return {
            name: 'uni:app-uts',
            apply: 'build',
            uni: (0, utils_1.createUniOptions)(platform),
            config(config) {
                const sourcemap = (0, uni_cli_shared_1.withSourcemap)(config);
                return {
                    base: '/', // 强制 base
                    build: {
                        sourcemap,
                        emptyOutDir: false,
                        assetsInlineLimit: 0,
                        target: isIOS
                            ? [
                                'ios12',
                                'es2020',
                                'edge88',
                                'firefox78',
                                'chrome87',
                                'safari14',
                            ]
                            : isHarmony
                                ? ['es2022']
                                : undefined,
                        rollupOptions: {
                            input: (0, uni_cli_shared_1.resolveMainPathOnce)(inputDir),
                            // import "libentry.so"
                            external: ['vue', '@vue/shared', /.*\.so$/],
                            output: {
                                name: 'AppService',
                                banner: ``,
                                format: isESM ? 'esm' : 'iife',
                                entryFileNames: uni_cli_shared_1.APP_SERVICE_FILENAME,
                                globals,
                                paths,
                                plugins: isESM ? [(0, rewriteImportVue_1.rewriteImportVuePlugin)()] : [],
                                manualChunks(id) {
                                    if (isESM) {
                                        const chunkName = (0, uni_cli_shared_1.normalizePath)(id.split('?')[0]);
                                        if (chunkName.startsWith('\0plugin-vue:')) {
                                            return 'plugin-vue-' + chunkName.split(':')[1];
                                        }
                                        if (chunkName.includes('/@dcloudio/uni-cloud/')) {
                                            return '@dcloudio/uni-cloud';
                                        }
                                        if (chunkName.startsWith(inputDir)) {
                                            return (0, uni_cli_shared_1.removeExt)((0, uni_cli_shared_1.normalizePath)(path_1.default.relative(inputDir, chunkName)));
                                        }
                                    }
                                },
                                inlineDynamicImports: false,
                                chunkFileNames: isESM ? 'assets/[name].js' : undefined,
                                sourcemapPathTransform: (relativeSourcePath, sourcemapPath) => {
                                    return (0, uni_cli_shared_1.normalizePath)(path_1.default.relative(process.env.UNI_INPUT_DIR, path_1.default.resolve(path_1.default.dirname(sourcemapPath), relativeSourcePath)));
                                },
                            },
                            treeshake: {
                                moduleSideEffects: (id, external) => {
                                    if (id === '@vue/shared') {
                                        return false;
                                    }
                                    return true;
                                },
                            },
                        },
                    },
                };
            },
            configResolved(config) {
                (0, utils_1.configResolved)(config);
                if (!isDom2) {
                    initUniAppJsEngineDom1CssPlugin(config);
                }
                (0, uni_cli_shared_1.insertBeforePlugin)((0, js_1.uniAppJsPlugin)(config), 'uni:app-main', config);
                // 如果开启了 vapor 模式，则禁用 vue 的 devtools，让 @vitejs/plugin-vue 不管是开发还是发行，均生成发行代码
                // 理论上非 vapor 也应该禁用，但为了不引发其他问题，暂时只禁用 vapor 模式
                if (isDom2) {
                    const plugin = config.plugins.find((p) => p.name === 'vite:vue');
                    if (plugin?.api?.options) {
                        plugin.api.options.devToolsEnabled = false;
                        plugin.api.options.isProduction = true;
                        // TODO 临时禁用，目前有bug 等待 https://github.com/vuejs/core/pull/13630 合并
                        // 使用内部自己定义的 transformAssetUrls
                        plugin.api.options.template.transformAssetUrls = false;
                    }
                }
            },
            generateBundle(_, bundle) {
                // 调整所有sourceMap文件
                const sourceRoot = (0, uni_cli_shared_1.normalizePath)(inputDir);
                Object.entries(bundle).forEach(([file, asset]) => {
                    if (file.endsWith('.js.map') && asset.type === 'asset') {
                        const source = JSON.parse(asset.source);
                        source.sourceRoot = sourceRoot;
                        const newSourceMapFileName = path_1.default.resolve(process.env.UNI_APP_X_CACHE_DIR, 'sourcemap', file);
                        fs_extra_1.default.outputFileSync(newSourceMapFileName, JSON.stringify(source));
                        if (isIOS) {
                            const jsFile = file.replace('.js.map', '.js');
                            const outputChunk = bundle[jsFile];
                            if (outputChunk) {
                                outputChunk.code = outputChunk.code.replace(`//# sourceMappingURL=${path_1.default.basename(file)}`, `//# sourceMappingURL=` +
                                    (0, uni_cli_shared_1.normalizePath)(path_1.default.relative(process.env.UNI_OUTPUT_DIR, newSourceMapFileName)));
                            }
                        }
                        // 非鸿蒙平台不需要保留 sourceMap 文件
                        if (process.env.UNI_PLATFORM !== 'app-harmony') {
                            delete bundle[file];
                        }
                    }
                });
            },
            async writeBundle() {
                // x 上暂时编译所有uni ext api，不管代码里是否调用了
                // 框架内部编译时，不需要
                if (process.env.UNI_COMPILE_TARGET !== 'ext-api') {
                    await (0, uni_cli_shared_1.buildUniExtApis)(process.env.UNI_UTS_PLATFORM === 'app-harmony');
                    await (0, uni_cli_shared_1.buildNonTreeShakingUniModules)();
                }
            },
        };
    };
}
exports.createUniAppJsEnginePlugin = createUniAppJsEnginePlugin;
