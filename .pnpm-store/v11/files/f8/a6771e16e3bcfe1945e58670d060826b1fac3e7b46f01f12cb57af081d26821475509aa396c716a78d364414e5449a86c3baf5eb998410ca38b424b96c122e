"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.uniAppCssPlugin = exports.uniAppCssPrePlugin = void 0;
const path_1 = __importDefault(require("path"));
const uni_cli_shared_1 = require("@dcloudio/uni-cli-shared");
const uni_nvue_styler_1 = require("@dcloudio/uni-nvue-styler");
const descriptorCache_1 = require("./uvue/descriptorCache");
const utils_1 = require("../utils");
const utils_2 = require("./utils");
function uniAppCssPrePlugin() {
    const name = 'uni:app-uvue-css-pre';
    const descriptorOptions = {
        ...(0, descriptorCache_1.getResolvedOptions)(),
        sourceMap: false,
    };
    const mainPath = (0, uni_cli_shared_1.resolveMainPathOnce)(process.env.UNI_INPUT_DIR);
    return {
        name,
        // 需要提前，因为unocss会在configResolved读取vite:css-post插件
        // 所以需要在它之前做替换
        enforce: 'pre',
        apply: 'build',
        configResolved(config) {
            (0, uni_cli_shared_1.removePlugins)(['vite:css', 'vite:css-post'], config);
            const uvueCssPostPlugin = (0, uni_cli_shared_1.cssPostPlugin)(config, {
                isJsCode: true,
                platform: process.env.UNI_PLATFORM,
                includeComponentCss: false,
                chunkCssFilename(id) {
                    const { filename } = (0, uni_cli_shared_1.parseVueRequest)(id);
                    if (filename === mainPath) {
                        // 合并到App
                        return `App.uvue.style.uts`;
                    }
                    if ((0, utils_1.isVue)(filename)) {
                        return (0, uni_cli_shared_1.normalizeNodeModules)((path_1.default.isAbsolute(filename)
                            ? path_1.default.relative(process.env.UNI_INPUT_DIR, filename)
                            : filename) + '.style.uts');
                    }
                },
                async chunkCssCode(filename, cssCode) {
                    cssCode = (0, uni_cli_shared_1.parseAssets)(config, cssCode);
                    const { code, messages } = await (0, uni_nvue_styler_1.parse)(cssCode, {
                        filename,
                        logLevel: 'ERROR',
                        mapOf: '_uM',
                        padStyleMapOf: '_pS',
                        chunk: 100,
                        type: 'uvue',
                        platform: process.env.UNI_UTS_PLATFORM,
                        trim: true,
                    });
                    messages.forEach((message) => {
                        if (message.type === 'error') {
                            (0, uni_cli_shared_1.onCompileLog)('error', { name: 'CSSError', message: message.text }, cssCode, filename, {
                                plugin: 'uni:app-uvue-css',
                                line: message.line,
                                column: message.column,
                            });
                        }
                    });
                    const fileName = filename.replace('.style.uts', '');
                    const className = (0, utils_2.genUVueClassName)(fileName, descriptorOptions.classNamePrefix);
                    return `export const ${className}Styles = ${code}`;
                },
            });
            // 增加 css plugins
            // TODO 加密插件
            (0, uni_cli_shared_1.insertBeforePlugin)((0, uni_cli_shared_1.cssPlugin)(config, {
                isAndroidX: true,
                getDescriptor: (filename) => {
                    return (0, descriptorCache_1.getDescriptor)(filename, descriptorOptions, false);
                },
            }), name, config);
            const plugins = config.plugins;
            const index = plugins.findIndex((p) => p.name === 'uni:app-uvue');
            plugins.splice(index, 0, uvueCssPostPlugin);
        },
    };
}
exports.uniAppCssPrePlugin = uniAppCssPrePlugin;
function uniAppCssPlugin() {
    let resolvedConfig;
    return {
        name: 'uni:app-uvue-css',
        apply: 'build',
        configResolved(config) {
            resolvedConfig = config;
        },
        async transform(source, filename) {
            if (!uni_cli_shared_1.cssLangRE.test(filename) || uni_cli_shared_1.commonjsProxyRE.test(filename)) {
                return;
            }
            if (filename.endsWith('__uno.css')) {
                return;
            }
            if (source.includes('#endif')) {
                source = (0, uni_cli_shared_1.preUVueCss)(source, filename);
            }
            source = (0, uni_cli_shared_1.parseAssets)(resolvedConfig, source);
            // 仅做校验使用
            const { messages } = await (0, uni_nvue_styler_1.parse)(source, {
                filename,
                logLevel: 'WARNING',
                map: true,
                ts: true,
                noCode: true,
                type: 'uvue',
                platform: process.env.UNI_UTS_PLATFORM,
            });
            messages.forEach((message) => {
                if (message.type === 'warning') {
                    // 拆分成多行，第一行输出信息（有颜色），后续输出错误代码+文件行号
                    (0, uni_cli_shared_1.onCompileLog)('warn', { name: 'CSSWarning', message: message.text }, source, filename, {
                        plugin: 'uni:app-uvue-css',
                        line: message.line,
                        column: message.column,
                    });
                }
            });
            return {
                code: source,
                map: {
                    mappings: '',
                },
            };
        },
    };
}
exports.uniAppCssPlugin = uniAppCssPlugin;
