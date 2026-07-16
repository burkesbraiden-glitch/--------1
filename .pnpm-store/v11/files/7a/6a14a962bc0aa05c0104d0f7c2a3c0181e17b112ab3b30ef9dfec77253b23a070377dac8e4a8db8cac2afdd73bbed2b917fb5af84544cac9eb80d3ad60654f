"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.formatInstallHBuilderXPluginTips = exports.moduleAliasFormatter = exports.installHBuilderXPlugin = exports.initModuleAlias = void 0;
// 注意：该文件尽可能少依赖其他文件，否则可能会导致还没有alias的时候，就加载了目标模块
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const module_alias_1 = __importDefault(require("module-alias"));
const utils_1 = require("./utils");
const jsonc_parser_1 = require("jsonc-parser");
const hbxPlugins = {
    typescript: 'compile-typescript/node_modules/typescript',
    less: 'compile-less/node_modules/less',
    sass: 'compile-dart-sass/node_modules/sass',
    stylus: 'compile-stylus/node_modules/stylus',
    pug: 'compile-pug-cli/node_modules/pug',
};
function initModuleAlias() {
    const libDir = path_1.default.resolve(__dirname, '../../lib');
    const compilerSfcPath = path_1.default.resolve(libDir, '@vue/compiler-sfc');
    const serverRendererPath = require.resolve('@vue/server-renderer');
    // 对路径进行兼容
    if (!process.env.UNI_APP_X_DOM2_CPP_DIR &&
        process.env.UNI_APP_HARMONY_DOM2_CPP_DIR) {
        process.env.UNI_APP_X_DOM2_CPP_DIR =
            process.env.UNI_APP_HARMONY_DOM2_CPP_DIR;
    }
    // TODO 等待正式对外推出后，删除这个兼容逻辑
    if (process.env.UNI_APP_PLATFORM === 'ios' ||
        process.env.UNI_APP_PLATFORM === 'android') {
        if (process.env.UNI_INPUT_DIR) {
            const manifestJsonFilename = path_1.default.resolve(process.env.UNI_INPUT_DIR, 'manifest.json');
            if (fs_1.default.existsSync(manifestJsonFilename)) {
                const manifestJsonStr = fs_1.default.readFileSync(manifestJsonFilename, 'utf-8');
                const manifestJson = (0, jsonc_parser_1.parse)(manifestJsonStr);
                if (manifestJson?.['uni-app-x']?.vapor === true) {
                    const vaporFilename = path_1.default.resolve(process.env.UNI_INPUT_DIR, '.vapor');
                    if (fs_1.default.existsSync(vaporFilename)) {
                        process.env.UNI_APP_X_DOM2 = 'true';
                    }
                }
            }
        }
    }
    if (process.env.UNI_APP_X_DOM2 === 'true') {
        if (process.env.UNI_OUTPUT_DIR &&
            (process.env.UNI_PLATFORM === 'app' ||
                process.env.UNI_PLATFORM === 'app-plus' ||
                process.env.UNI_PLATFORM === 'app-harmony')) {
            if (!process.env.UNI_APP_X_DOM2_CPP_DIR) {
                let baseDir = '';
                const isAndroid = process.env.UNI_APP_PLATFORM === 'android';
                const isIOS = process.env.UNI_APP_PLATFORM === 'ios';
                if (process.env.NODE_ENV !== 'development' && (isAndroid || isIOS)) {
                    baseDir = path_1.default.resolve(process.env.UNI_OUTPUT_DIR, '.uniappx', isAndroid ? 'android' : 'ios');
                }
                else {
                    baseDir =
                        process.env.UNI_PLATFORM === 'app-harmony'
                            ? process.env.UNI_OUTPUT_DIR
                            : process.env.UNI_APP_X_CACHE_DIR || process.env.UNI_OUTPUT_DIR;
                }
                process.env.UNI_APP_X_DOM2_CPP_DIR = path_1.default.resolve(baseDir, 'cpp');
                process.env.UNI_APP_X_DOM2_SO_DIR = path_1.default.resolve(baseDir, 'so');
            }
            if (!process.env.UNI_APP_X_DOM2_KT_DIR) {
                if (process.env.NODE_ENV !== 'development') {
                    process.env.UNI_APP_X_DOM2_KT_DIR = path_1.default.resolve(process.env.UNI_OUTPUT_DIR, '.uniappx/android', 'src');
                }
                else {
                    process.env.UNI_APP_X_DOM2_KT_DIR = path_1.default.resolve(process.env.UNI_APP_X_CACHE_DIR ||
                        path_1.default.resolve(process.env.UNI_OUTPUT_DIR, '../.cache'), 'src');
                }
            }
        }
        if (process.env.UNI_APP_PLATFORM ||
            process.env.UNI_PLATFORM === 'app-harmony') {
            if (!process.env.UNI_APP_X_VAPOR_RENDER_TARGET) {
                // 默认 app 平台使用 bytecode 目标
                process.env.UNI_APP_X_VAPOR_RENDER_TARGET = 'bytecode';
            }
            if (process.env.UNI_APP_X_VAPOR_RENDER_TARGET?.includes('bytecode')) {
                process.env.UNI_APP_X_DOM2_DYNAMIC = 'true';
            }
            // 如果是 ext-api 目标，强制使用 nativecode 目标
            if (process.env.UNI_COMPILE_TARGET === 'ext-api') {
                delete process.env.UNI_APP_X_DOM2_DYNAMIC;
            }
        }
    }
    if (process.env.UNI_APP_X_DOM2 === 'true') {
        const vuePkgs = [
            '@vue/compiler-core',
            '@vue/compiler-dom',
            '@vue/compiler-sfc',
            '@vue/compiler-vapor',
            '@vue/shared',
        ];
        vuePkgs.forEach((pkg) => {
            module_alias_1.default.addAlias(pkg, path_1.default.resolve(libDir, 'dom2', 'app', '@vue', pkg.split('/').pop()));
        });
        module_alias_1.default.addAlias('@vitejs/plugin-vue', path_1.default.resolve(libDir, 'dom2', 'app', '@vitejs', 'plugin-vue'));
        module_alias_1.default.addAlias('@dcloudio/compiler-vapor-dom2', path_1.default.resolve(libDir, 'dom2', 'app', '@vue', 'compiler-vapor-dom2'));
    }
    else {
        module_alias_1.default.addAliases({
            '@vue/shared': require.resolve('@vue/shared'),
            '@vue/shared/dist/shared.esm-bundler.js': require.resolve('@vue/shared/dist/shared.esm-bundler.js'),
            '@vue/compiler-core': path_1.default.resolve(libDir, '@vue/compiler-core'),
            '@vue/compiler-dom': require.resolve('@vue/compiler-dom'),
            '@vue/compiler-sfc': compilerSfcPath,
            '@vue/server-renderer': serverRendererPath,
            'vue/compiler-sfc': compilerSfcPath,
            'vue/server-renderer': serverRendererPath,
        });
    }
    if (process.env.VITEST) {
        module_alias_1.default.addAliases({
            vue: '@dcloudio/uni-h5-vue',
            'vue/package.json': '@dcloudio/uni-h5-vue/package.json',
        });
    }
    if ((0, utils_1.isInHBuilderX)()) {
        // 又是为了复用 HBuilderX 的插件逻辑，硬编码映射
        Object.keys(hbxPlugins).forEach((lang) => {
            const realPath = path_1.default.resolve(process.env.UNI_HBUILDERX_PLUGINS, hbxPlugins[lang]);
            module_alias_1.default.addAlias(lang, 
            // @ts-expect-error
            () => {
                try {
                    require.resolve(realPath);
                }
                catch (e) {
                    const msg = exports.moduleAliasFormatter.format(`Preprocessor dependency "${lang}" not found. Did you install it?`);
                    console.error(msg);
                    process.exit(0);
                }
                return realPath;
            });
        });
        // web 平台用了 vite 内置 css 插件，该插件会加载预编译器如scss、less等，需要转向到 HBuilderX 的对应编译器插件
        if (process.env.UNI_PLATFORM === 'h5' ||
            process.env.UNI_PLATFORM === 'web') {
            // https://github.com/vitejs/vite/blob/main/packages/vite/src/node/packages.ts#L92
            // 拦截预编译器
            const join = path_1.default.join;
            path_1.default.join = function (...paths) {
                if (paths.length === 4) {
                    // path.join(basedir, 'node_modules', pkgName, 'package.json')
                    // const basedir = paths[0]
                    const nodeModules = paths[1]; // = node_modules
                    const pkgName = paths[2];
                    const packageJson = paths[3]; // = package.json
                    if (nodeModules === 'node_modules' &&
                        packageJson === 'package.json' &&
                        hbxPlugins[pkgName]) {
                        return path_1.default.resolve(process.env.UNI_HBUILDERX_PLUGINS, hbxPlugins[pkgName], packageJson);
                    }
                }
                return join(...paths);
            };
            // https://github.com/vitejs/vite/blob/892916d040a035edde1add93c192e0b0c5c9dd86/packages/vite/src/node/plugins/css.ts#L1481
            // const oldSync = resovle.sync
            // resovle.sync = (id: string, opts?: SyncOpts) => {
            //   if ((hbxPlugins as any)[id]) {
            //     return path.resolve(
            //       process.env.UNI_HBUILDERX_PLUGINS,
            //       hbxPlugins[id as keyof typeof hbxPlugins]
            //     )
            //   }
            //   return oldSync(id, opts)
            // }
        }
    }
}
exports.initModuleAlias = initModuleAlias;
function supportAutoInstallPlugin() {
    return !!process.env.HX_Version;
}
function installHBuilderXPlugin(plugin) {
    if (!supportAutoInstallPlugin()) {
        return;
    }
    return console.error(`%HXRunUniAPPPluginName%${plugin}%HXRunUniAPPPluginName%`);
}
exports.installHBuilderXPlugin = installHBuilderXPlugin;
const installPreprocessorTips = {};
exports.moduleAliasFormatter = {
    test(msg) {
        return msg.includes('Preprocessor dependency');
    },
    format(msg) {
        let lang = '';
        let preprocessor = '';
        if (msg.includes(`"pug"`)) {
            lang = 'pug';
            preprocessor = 'compile-pug-cli';
        }
        else if (msg.includes(`"sass"`)) {
            lang = 'sass';
            preprocessor = 'compile-dart-sass';
        }
        else if (msg.includes(`"less"`)) {
            lang = 'less';
            preprocessor = 'compile-less';
        }
        else if (msg.includes('"stylus"')) {
            lang = 'stylus';
            preprocessor = 'compile-stylus';
        }
        else if (msg.includes('"typescript"')) {
            lang = 'typescript';
            preprocessor = 'compile-typescript';
        }
        if (lang) {
            // 仅提醒一次
            if (installPreprocessorTips[lang]) {
                return '';
            }
            installPreprocessorTips[lang] = true;
            installHBuilderXPlugin(preprocessor);
            return formatInstallHBuilderXPluginTips(lang, preprocessor);
        }
        return msg;
    },
};
function formatInstallHBuilderXPluginTips(lang, preprocessor) {
    return `预编译器错误：代码使用了${lang}语言，但未安装相应的编译器插件，${supportAutoInstallPlugin() ? '正在从' : '请前往'}插件市场安装该插件:
https://ext.dcloud.net.cn/plugin?name=${preprocessor}`;
}
exports.formatInstallHBuilderXPluginTips = formatInstallHBuilderXPluginTips;
