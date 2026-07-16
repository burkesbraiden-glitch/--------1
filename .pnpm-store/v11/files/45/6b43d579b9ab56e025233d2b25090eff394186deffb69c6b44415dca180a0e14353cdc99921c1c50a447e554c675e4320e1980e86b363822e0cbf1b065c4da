"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.uniAppCssPlugin = exports.uniAppCssPrePlugin = void 0;
const uni_cli_shared_1 = require("@dcloudio/uni-cli-shared");
const trace_mapping_1 = require("@jridgewell/trace-mapping");
const utils_1 = require("../utils");
const CSS_FILE_ID_MAP = new Map();
function uniAppCssPrePlugin() {
    const name = 'uni:app-uvue-css-pre';
    const mainPath = (0, uni_cli_shared_1.resolveMainPathOnce)(process.env.UNI_INPUT_DIR);
    const appUVuePath = (0, uni_cli_shared_1.resolveAppVue)(process.env.UNI_INPUT_DIR);
    const { parseCss } = require('@dcloudio/compiler-vapor-dom2');
    const isDom2 = process.env.UNI_APP_X_DOM2 === 'true';
    return {
        name,
        // 需要提前，因为unocss会在configResolved读取vite:css-post插件
        // 所以需要在它之前做替换
        enforce: 'pre',
        apply: 'build',
        configResolved(config) {
            (0, uni_cli_shared_1.removePlugins)(['vite:css', 'vite:css-post'], config);
            // 强制启用 css source map
            config.css.devSourcemap = true;
            const uvueCssPostPlugin = (0, uni_cli_shared_1.cssPostPlugin)(config, {
                isJsCode: true,
                platform: process.env.UNI_PLATFORM,
                includeComponentCss: false,
                preserveModules: true,
                chunkCssFilename(id) {
                    // 暂不支持多style标签
                    const { filename } = (0, uni_cli_shared_1.parseVueRequest)(id);
                    if (filename === mainPath || filename === appUVuePath) {
                        // 合并到App
                        CSS_FILE_ID_MAP.set(`App.uvue`, id);
                        return `App.uvue`;
                    }
                    if ((0, utils_1.isVue)(filename)) {
                        CSS_FILE_ID_MAP.set(filename, id);
                        return filename;
                    }
                },
                async chunkCssCode(filename, cssCode) {
                    // filename
                    cssCode = (0, uni_cli_shared_1.parseAssets)(config, cssCode);
                    const { code, bytes, messages, fontFaces } = await parseCss(cssCode, {
                        platform: process.env.UNI_UTS_PLATFORM,
                        helper: (0, uni_cli_shared_1.requireUniHelpers)(),
                        output: process.env.UNI_APP_X_DOM2_DYNAMIC === 'true' ? 'bin' : 'code',
                    });
                    if (isDom2 && fontFaces?.length) {
                        const id = CSS_FILE_ID_MAP.get(filename);
                        if (id) {
                            const cloneFontFaces = fontFaces.reduce((acc, cur) => {
                                const clone = { ...cur };
                                if (!clone.fontFamily) {
                                    clone.fontFamily = cur['font-family'];
                                    delete clone['font-family'];
                                }
                                acc.push(clone);
                                return acc;
                            }, []);
                            // 没有 @font-face 的占位符不写入缓存，后面统一清理成 {}，避免对大 chunk 反复 replace。
                            utils_1.DOM2_CSS_CACHE_MAP.set(id, JSON.stringify({ '@FONT-FACE': cloneFontFaces }));
                        }
                    }
                    messages.forEach((message) => {
                        if (message.type === 'error') {
                            (0, uni_cli_shared_1.onCompileLog)('error', { name: 'CSSError', message: message.text }, cssCode, filename, {
                                plugin: 'uni:app-uvue-css',
                                line: message.line,
                                column: message.column,
                            });
                        }
                    });
                    return code || bytes;
                },
                emitFile(filename, cssCode) {
                    const { ASDSF } = (0, uni_cli_shared_1.requireUniHelpers)();
                    ASDSF((0, uni_cli_shared_1.normalizePath)(filename), cssCode, process.env.UNI_UTS_PLATFORM);
                },
            });
            const uvueCssInlinePostPlugin = {
                name: 'uni:app-uvue-css-inline-post',
                apply: 'build',
                generateBundle(_, bundle) {
                    if (isDom2) {
                        Object.entries(bundle).forEach(([, asset]) => {
                            // 不支持多style标签
                            if (asset.type === 'chunk') {
                                if (utils_1.DOM2_CSS_CACHE_MAP.size) {
                                    for (let i = 0; i < asset.moduleIds.length; i++) {
                                        const moduleId = asset.moduleIds[i];
                                        if (utils_1.DOM2_CSS_CACHE_MAP.has(moduleId)) {
                                            const fontFaces = utils_1.DOM2_CSS_CACHE_MAP.get(moduleId);
                                            asset.code = asset.code.replace((0, uni_cli_shared_1.createJsStylePlaceholderRegExp)(moduleId), fontFaces);
                                            utils_1.DOM2_CSS_CACHE_MAP.delete(moduleId);
                                        }
                                    }
                                }
                                // 清理无用占位符
                                if (asset.code.includes(uni_cli_shared_1.JS_STYLE_PLACEHOLDER_MARKER)) {
                                    asset.code = asset.code.replace(uni_cli_shared_1.ANY_JS_STYLE_PLACEHOLDER_RE, '{}');
                                }
                            }
                        });
                    }
                },
            };
            // 增加 css plugins
            // TODO 加密插件
            (0, uni_cli_shared_1.insertBeforePlugin)((0, uni_cli_shared_1.cssPlugin)(config), name, config);
            const plugins = config.plugins;
            // 重要：必须放到 unplugin-auto-import、uni:sd 前
            const index = plugins.findIndex((p) => p.name === 'unplugin-auto-import');
            plugins.splice(index, 0, uvueCssPostPlugin);
            if (isDom2) {
                plugins.splice(index + 1, 0, uvueCssInlinePostPlugin);
            }
        },
    };
}
exports.uniAppCssPrePlugin = uniAppCssPrePlugin;
function uniAppCssPlugin() {
    let resolvedConfig;
    const { parseCss } = require('@dcloudio/compiler-vapor-dom2');
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
            const { messages } = await parseCss(source, {
                platform: process.env.UNI_UTS_PLATFORM,
                helper: (0, uni_cli_shared_1.requireUniHelpers)(),
                output: process.env.UNI_APP_X_DOM2_DYNAMIC === 'true' ? 'bin' : 'code',
            });
            let cssSourceMap;
            if (messages.find((m) => m.type === 'warning')) {
                const moduleInfo = this.getModuleInfo(filename);
                cssSourceMap = moduleInfo?.meta.uni?.cssSourceMap;
            }
            const sourceMap = (cssSourceMap ? new trace_mapping_1.TraceMap(cssSourceMap) : undefined);
            messages.forEach((message) => {
                if (message.type === 'warning') {
                    // 拆分成多行，第一行输出信息（有颜色），后续输出错误代码+文件行号
                    const originalPos = (0, trace_mapping_1.originalPositionFor)(sourceMap, {
                        line: message.line,
                        column: message.column,
                    });
                    let code = source;
                    let line = message.line;
                    let column = message.column;
                    if (originalPos.source) {
                        const sourceContent = (0, trace_mapping_1.sourceContentFor)(sourceMap, originalPos.source);
                        if (sourceContent) {
                            code = sourceContent;
                            line = originalPos.line;
                            column = originalPos.column;
                        }
                    }
                    (0, uni_cli_shared_1.onCompileLog)('warn', { name: 'CSSWarning', message: message.text }, code, filename, {
                        plugin: 'uni:app-uvue-css',
                        line,
                        column,
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
