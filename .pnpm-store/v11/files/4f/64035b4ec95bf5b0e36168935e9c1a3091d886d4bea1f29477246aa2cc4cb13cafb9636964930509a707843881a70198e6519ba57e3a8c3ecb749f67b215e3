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
const path_1 = __importDefault(require("path"));
const plugin_basic_ssl_1 = __importDefault(require("@vitejs/plugin-basic-ssl"));
const uni_cli_shared_1 = require("@dcloudio/uni-cli-shared");
const vueCompilerDom = __importStar(require("@vue/compiler-dom"));
const uniCliShared = __importStar(require("@dcloudio/uni-cli-shared"));
const plugin_1 = require("./plugin");
const config_1 = require("./plugin/config");
const css_1 = require("./plugins/css");
const easycom_1 = require("./plugins/easycom");
const inject_1 = require("./plugins/inject");
const mainJs_1 = require("./plugins/mainJs");
const manifestJson_1 = require("./plugins/manifestJson");
const pagesJson_1 = require("./plugins/pagesJson");
const postVue_1 = require("./plugins/postVue");
const renderjs_1 = require("./plugins/renderjs");
const resolveId_1 = require("./plugins/resolveId");
const setup_1 = require("./plugins/setup");
const ssr_1 = require("./plugins/ssr");
const sourcemap_1 = require("./plugins/sourcemap");
const customElement_1 = require("./plugins/customElement");
const api_1 = require("./plugins/api");
const polyfill_1 = require("./utils/polyfill");
if (process.env.UNI_APP_STYLE_ISOLATION_VERSION === '2' &&
    process.env.UNI_APP_X === 'true') {
    (0, polyfill_1.rewriteCompilerSfcParse)();
}
exports.default = () => {
    const isNewStyleIsolation = process.env.UNI_APP_STYLE_ISOLATION_VERSION === '2';
    // 从 manifest.json 的 h5.devServer 中解析 HTTPS 扩展配置，按需注入 basic-ssl 插件。
    const h5BasicSslPlugin = resolveH5BasicSslPlugin();
    return [
        ...(process.env.UNI_APP_X === 'true' && (0, uni_cli_shared_1.isNormalCompileTarget)()
            ? [(0, uni_cli_shared_1.uniWorkersPlugin)(), (0, uni_cli_shared_1.uniJavaScriptWorkersPlugin)()]
            : []),
        ...((0, uni_cli_shared_1.isEnableConsole)() ? [(0, uni_cli_shared_1.uniHBuilderXConsolePlugin)('uni.__f__')] : []),
        ...(process.env.UNI_APP_X === 'true'
            ? [
                (0, uni_cli_shared_1.uniDecryptUniModulesPlugin)(),
                (0, uni_cli_shared_1.uniUTSUVueJavaScriptPlugin)(),
                (0, uni_cli_shared_1.resolveUTSCompiler)().uts2js({
                    platform: 'web',
                    inputDir: process.env.UNI_INPUT_DIR,
                    version: process.env.UNI_COMPILER_VERSION,
                    sourceMap: (0, uni_cli_shared_1.enableSourceMap)(),
                    cacheRoot: path_1.default.resolve(process.env.UNI_APP_X_CACHE_DIR, '.uts2js/cache'),
                    modules: {
                        vueCompilerDom,
                        uniCliShared,
                    },
                    workers: {
                        extname: '.js',
                        resolve: () => {
                            return (0, uni_cli_shared_1.getWorkers)();
                        },
                    },
                }),
            ]
            : []),
        (0, easycom_1.uniEasycomPlugin)({ exclude: uni_cli_shared_1.UNI_EASYCOM_EXCLUDE }),
        (0, uni_cli_shared_1.uniCssScopedPlugin)({
            filter: (id) => {
                // Vapor 模式下，App.vue 也需要处理
                if (isNewStyleIsolation) {
                    return (0, uni_cli_shared_1.isVueSfcFile)(id);
                }
                return (0, uni_cli_shared_1.isVueSfcFile)(id) && !(0, uni_cli_shared_1.isAppVue)(id);
            },
        }),
        (0, resolveId_1.uniResolveIdPlugin)(),
        ...(process.env.UNI_COMPILE_TARGET === 'uni_modules'
            ? []
            : [(0, mainJs_1.uniMainJsPlugin)(), (0, manifestJson_1.uniManifestJsonPlugin)(), (0, pagesJson_1.uniPagesJsonPlugin)()]),
        (0, inject_1.uniInjectPlugin)(),
        (0, css_1.uniCssPlugin)(),
        (0, ssr_1.uniSSRPlugin)(),
        (0, setup_1.uniSetupPlugin)(),
        (0, renderjs_1.uniRenderjsPlugin)(),
        ...(h5BasicSslPlugin ? [h5BasicSslPlugin] : []),
        (0, plugin_1.uniH5Plugin)(),
        ...(process.env.UNI_COMPILE_TARGET === 'uni_modules'
            ? [(0, uni_cli_shared_1.uniEncryptUniModulesAssetsPlugin)(), (0, uni_cli_shared_1.uniEncryptUniModulesPlugin)()]
            : []),
        (0, postVue_1.uniPostVuePlugin)(),
        (0, sourcemap_1.uniPostSourceMapPlugin)(),
        (0, customElement_1.uniCustomElementPlugin)(),
        (0, api_1.uniApiPlugin)(),
    ];
};
function resolveH5BasicSslPlugin() {
    const inputDir = process.env.UNI_INPUT_DIR;
    if (!inputDir) {
        return;
    }
    // 这里只关心是否启用自动证书，以及透传给 basic-ssl 的那部分参数。
    const { enableBasicSsl, basicSslOptions } = (0, config_1.resolveManifestServerOptions)(inputDir);
    if (!enableBasicSsl) {
        return;
    }
    // 需要在真正的 Vite 插件数组中注册，才能参与 configResolved 并注入证书。
    return Object.assign((0, plugin_basic_ssl_1.default)(basicSslOptions), {
        apply: 'serve',
    });
}
