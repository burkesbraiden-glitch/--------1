"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.initPluginViteLegacyOptions = exports.initPluginVueJsxOptions = exports.initPluginVueOptions = exports.createPluginVueInstance = void 0;
const fs_extra_1 = __importDefault(require("fs-extra"));
const shared_1 = require("@vue/shared");
const uni_shared_1 = require("@dcloudio/uni-shared");
const uni_cli_shared_1 = require("@dcloudio/uni-cli-shared");
const utils_1 = require("../utils");
const pluginVuePath = require.resolve('@vitejs/plugin-vue');
const normalizedPluginVuePath = (0, uni_cli_shared_1.normalizePath)(pluginVuePath);
/**
 * 每次创建新的 plugin-vue 实例。因为该插件内部会 cache  descriptor，而相同的vue文件在编译到vue页面和nvue页面时，不能共享缓存（条件编译，css scoped等均不同）
 * @returns
 */
function createPluginVueInstance(options) {
    delete require.cache[pluginVuePath];
    delete require.cache[normalizedPluginVuePath];
    const vuePlugin = require('@vitejs/plugin-vue');
    const vuePluginInstance = vuePlugin(options);
    if (process.env.NODE_ENV === 'development') {
        // 删除 buildEnd 逻辑，因为里边清理了缓存，导致 watch 模式失效 https://github.com/vitejs/vite-plugin-vue/commit/96dbb220ff210d2f7391f43a807bcd8cfb0da776
        delete vuePluginInstance.buildEnd;
    }
    return vuePluginInstance;
}
exports.createPluginVueInstance = createPluginVueInstance;
function initPluginVueOptions(options, UniVitePlugins, uniPluginOptions) {
    const vueOptions = options.vueOptions || (options.vueOptions = {});
    // if (!hasOwn(vueOptions, 'reactivityTransform')) {
    //   vueOptions.reactivityTransform = true
    // }
    if (!vueOptions.include) {
        vueOptions.include = [];
    }
    if (!(0, shared_1.isArray)(vueOptions.include)) {
        vueOptions.include = [vueOptions.include];
    }
    vueOptions.include.push(uni_cli_shared_1.EXTNAME_VUE_RE);
    const styleOptions = vueOptions.style || (vueOptions.style = {});
    if (!styleOptions.postcssPlugins) {
        styleOptions.postcssPlugins = [];
    }
    // 解析 scoped 中 deep 等特殊语法
    styleOptions.postcssPlugins.push((0, uni_cli_shared_1.uniPostcssScopedPlugin)());
    // 解析 :external() 语法，dom2 + 小程序平台下提升外部类选择器权重
    if (process.env.UNI_APP_STYLE_ISOLATION_VERSION === '2' &&
        process.env.UNI_APP_X === 'true') {
        styleOptions.postcssPlugins.push((0, uni_cli_shared_1.uniPostcssExternalPlugin)());
    }
    const templateOptions = vueOptions.template || (vueOptions.template = {});
    const compilerOptions = templateOptions.compilerOptions || (templateOptions.compilerOptions = {});
    const isDom2 = process.env.UNI_APP_X_DOM2 === 'true';
    compilerOptions.isX = process.env.UNI_APP_X === 'true';
    compilerOptions.dom2 = isDom2;
    // 默认就移除comments节点
    compilerOptions.comments = false;
    const { compiler, styleOptions: { postcssPlugins }, compilerOptions: { miniProgram, isNativeTag, isVoidTag, isCustomElement, nodeTransforms, directiveTransforms, whitespace, }, } = uniPluginOptions;
    if (postcssPlugins) {
        styleOptions.postcssPlugins.push(...postcssPlugins);
    }
    if (compiler) {
        templateOptions.compiler = compiler;
    }
    if (miniProgram) {
        ;
        compilerOptions.miniProgram = miniProgram;
    }
    const isDevX = process.env.UNI_HX_VERSION_DEV === 'true' &&
        process.env.UNI_APP_X === 'true';
    if (isNativeTag) {
        const userIsNativeTag = compilerOptions.isNativeTag;
        compilerOptions.isNativeTag = (tag) => {
            if (isDevX) {
                const source = (0, uni_cli_shared_1.matchEasycom)(tag);
                // 不能是uts插件的easycom组件
                if (source && !source.includes('?uts-proxy')) {
                    return false;
                }
            }
            if (isNativeTag(tag)) {
                return true;
            }
            if (userIsNativeTag && userIsNativeTag(tag)) {
                return true;
            }
            return false;
        };
    }
    if (isVoidTag) {
        const userIsVoidTag = compilerOptions.isVoidTag;
        compilerOptions.isVoidTag = (tag) => {
            if (isVoidTag(tag)) {
                return true;
            }
            if (userIsVoidTag && userIsVoidTag(tag)) {
                return true;
            }
            return false;
        };
    }
    if (whitespace) {
        compilerOptions.whitespace = whitespace;
    }
    if (isCustomElement) {
        const userIsCustomElement = compilerOptions.isCustomElement;
        compilerOptions.isCustomElement = (tag) => {
            if (isCustomElement(tag)) {
                return true;
            }
            if (userIsCustomElement && userIsCustomElement(tag)) {
                return true;
            }
            return false;
        };
    }
    compilerOptions.directiveTransforms = {
        ...compilerOptions.directiveTransforms,
        ...directiveTransforms,
    };
    if (!compilerOptions.nodeTransforms) {
        compilerOptions.nodeTransforms = [];
    }
    // 合并 transformAssetUrls
    // 内置配置
    const builtInTransformAssetUrls = (0, uni_cli_shared_1.createUniVueTransformAssetUrls)((0, uni_cli_shared_1.isExternalUrl)(options.base) ? options.base : '');
    // 用户传递配置 eg: transformAssetUrls.tags = {'my-image': ['src']}
    // docs: https://github.com/vitejs/vite-plugin-vue/tree/main/packages/plugin-vue
    const userOptionsTransformAssetUrls = templateOptions.transformAssetUrls;
    templateOptions.transformAssetUrls = builtInTransformAssetUrls;
    if (typeof userOptionsTransformAssetUrls !== 'boolean' &&
        !!userOptionsTransformAssetUrls?.tags &&
        !(0, shared_1.isArray)(userOptionsTransformAssetUrls.tags)) {
        templateOptions.transformAssetUrls = {
            ...builtInTransformAssetUrls,
            ...userOptionsTransformAssetUrls,
            tags: {
                ...builtInTransformAssetUrls.tags,
                ...userOptionsTransformAssetUrls.tags,
            },
        };
    }
    if (options.platform !== 'h5' && options.platform !== 'web') {
        compilerOptions.nodeTransforms.push(...(0, uni_cli_shared_1.getBaseNodeTransforms)(options.base, isDom2 ? (0, uni_cli_shared_1.createResolveStaticAsset)(options.inputDir) : undefined));
    }
    if (nodeTransforms) {
        compilerOptions.nodeTransforms.push(...nodeTransforms);
    }
    // const compatConfig = parseCompatConfigOnce(options.inputDir)
    // compilerOptions.compatConfig = extend(
    //   compilerOptions.compatConfig || {},
    //   compatConfig
    // )
    // App,MP 平台不支持使用静态节点
    compilerOptions.hoistStatic = false;
    compilerOptions.root = process.env.UNI_INPUT_DIR;
    const isX = process.env.UNI_APP_X === 'true';
    // app-nvue | app-uvue 需要启用 customElement 机制来内联 styles
    if (process.env.UNI_COMPILER === 'nvue' ||
        (isX && (options.platform === 'app' || options.platform === 'app-harmony'))) {
        vueOptions.customElement = true;
        if (process.env.UNI_RENDERER_NATIVE !== 'appService' || isX) {
            // nvue 需要使用自己的 compiler，来移除 scoped
            vueOptions.compiler = (0, utils_1.createNVueCompiler)();
        }
    }
    if (!vueOptions.script) {
        vueOptions.script = {};
    }
    // TODO 目前暂不支持通过@/开头引入文件，因为需要tsconfig.json配置，建议使用相对路径
    // https://github.com/vuejs/core/blob/main/packages/compiler-sfc/src/script/resolveType.ts#L911
    require('@vue/compiler-sfc').registerTS(() => {
        if (isX) {
            return (0, uni_cli_shared_1.resolveUniTypeScript)();
        }
        return require('typescript');
    });
    if (!vueOptions.script.fs) {
        function resolveFile(file) {
            if (file.startsWith('@/')) {
                file = file.replace('@/', (0, uni_cli_shared_1.normalizePath)(process.env.UNI_INPUT_DIR));
            }
            return file;
        }
        vueOptions.script.fs = {
            fileExists(file) {
                return fs_extra_1.default.existsSync(resolveFile(file));
            },
            readFile(file) {
                const filename = resolveFile(file);
                // 需要走条件编译
                return (0, uni_cli_shared_1.preJs)(fs_extra_1.default.readFileSync(filename, 'utf-8'), filename);
            },
            realpath(file) {
                return resolveFile(file);
            },
        };
    }
    if (isX) {
        if (!vueOptions.script) {
            vueOptions.script = {
                babelParserPlugins: [],
            };
        }
        if (!vueOptions.script.babelParserPlugins) {
            vueOptions.script.babelParserPlugins = [];
        }
        if (!vueOptions.script.babelParserPlugins.includes('typescript')) {
            vueOptions.script.babelParserPlugins.push('typescript');
        }
        // decorators or decorators-legacy
        if (!vueOptions.script.babelParserPlugins.includes('decorators')) {
            vueOptions.script.babelParserPlugins.push('decorators');
        }
        if (isDom2) {
            const appVue = (0, uni_cli_shared_1.resolveAppVue)(process.env.UNI_INPUT_DIR);
            function isAppVue(id) {
                return (0, uni_cli_shared_1.normalizePath)(id) === appVue;
            }
            ;
            compilerOptions.isEasyComponent = (tag) => {
                return (0, uni_shared_1.isDom2VueComponentTag)(tag) || !!(0, uni_cli_shared_1.matchEasycom)(tag);
            };
            compilerOptions.isUserComponent = (element) => {
                return (0, uni_shared_1.isDom2AppUserVueComponentTag)(element.tag);
            };
            vueOptions.script.extraOptions = (descriptor) => {
                return {
                    isWatch: process.env.NODE_ENV === 'development',
                    // TODO 目前使用全局开关，后续可能是页面级别的开关？
                    dynamicSharedData: process.env.UNI_APP_X_DOM2_DYNAMIC === 'true',
                    helper: (0, uni_cli_shared_1.requireUniHelpers)(),
                    componentType: (0, uni_cli_shared_1.isUniPageFile)(descriptor.filename)
                        ? 'page'
                        : isAppVue(descriptor.filename)
                            ? 'app'
                            : 'component',
                };
            };
            vueOptions.template.compilerOptions.extraOptions = (descriptor) => {
                return (0, uni_cli_shared_1.initVueTemplateCompilerExtraOptions)(descriptor);
            };
        }
        else {
            // 如果是 easyComponent 组件，则不需要从setup中导入组件且不支持 self 引用
            ;
            compilerOptions.isEasyComponent = (tag) => {
                return (0, uni_shared_1.isBuiltInComponent)(tag) || !!(0, uni_cli_shared_1.matchEasycom)(tag);
            };
        }
    }
    return vueOptions;
}
exports.initPluginVueOptions = initPluginVueOptions;
function initPluginVueJsxOptions(options, { isCustomElement, }, jsxOptions) {
    const vueJsxOptions = (0, shared_1.isPlainObject)(options.vueJsxOptions)
        ? options.vueJsxOptions
        : (options.vueJsxOptions = {});
    if (!(0, shared_1.hasOwn)(vueJsxOptions, 'optimize')) {
        vueJsxOptions.optimize = true;
    }
    vueJsxOptions.isCustomElement = isCustomElement;
    if (!vueJsxOptions.babelPlugins) {
        vueJsxOptions.babelPlugins = [];
    }
    if ((0, shared_1.isArray)(jsxOptions.babelPlugins)) {
        vueJsxOptions.babelPlugins.push(...jsxOptions.babelPlugins);
    }
    return vueJsxOptions;
}
exports.initPluginVueJsxOptions = initPluginVueJsxOptions;
function initPluginViteLegacyOptions(options) {
    const viteLegacyOptions = options.viteLegacyOptions || (options.viteLegacyOptions = {});
    return viteLegacyOptions;
}
exports.initPluginViteLegacyOptions = initPluginViteLegacyOptions;
