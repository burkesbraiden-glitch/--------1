"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.createConfigResolved = void 0;
const debug_1 = __importDefault(require("debug"));
const shared_1 = require("@vue/shared");
const uni_cli_shared_1 = require("@dcloudio/uni-cli-shared");
const pagesJson_1 = require("../plugins/pagesJson");
const entry_1 = require("../plugins/entry");
const debugNVueCss = (0, debug_1.default)('uni:nvue-css');
const cssVars = `page{--status-bar-height:25px;--top-window-height:0px;--window-top:0px;--window-bottom:0px;--window-left:0px;--window-right:0px;--window-magin:0px}`;
const uvueCssVars = `page{--top-window-height:0px;--window-top:0px;--window-bottom:0px;--window-left:0px;--window-right:0px;--window-magin:0px;--uni-safe-area-inset-top:0px;--uni-safe-area-inset-left:0px;--uni-safe-area-inset-right:0px;}`;
const genShadowCss = (cdn) => {
    const url = (0, uni_cli_shared_1.createShadowImageUrl)(cdn, 'grey');
    return `page::after{position:fixed;content:'';left:-1000px;top:-1000px;-webkit-animation:shadow-preload .1s;-webkit-animation-delay:3s;animation:shadow-preload .1s;animation-delay:3s}@-webkit-keyframes shadow-preload{0%{background-image:url(${url})}100%{background-image:url(${url})}}@keyframes shadow-preload{0%{background-image:url(${url})}100%{background-image:url(${url})}}`;
};
const genComponentCustomHiddenCss = (name) => `[${name.replace(':', '')}="true"]{display: none !important;}`;
function createConfigResolved({ cdn, style: { extname }, template: { component }, }) {
    function normalizeCssChunkFilename(id, extname) {
        return ((0, uni_cli_shared_1.removeExt)((0, uni_cli_shared_1.normalizeMiniProgramFilename)(id, process.env.UNI_INPUT_DIR)) +
            extname);
    }
    return (config) => {
        const mainPath = (0, uni_cli_shared_1.resolveMainPathOnce)(process.env.UNI_INPUT_DIR);
        fixUnocss(config);
        (0, uni_cli_shared_1.injectCssPlugin)(config, process.env.UNI_COMPILE_TARGET === 'uni_modules'
            ? {
                createUrlReplacer: uni_cli_shared_1.createEncryptCssUrlReplacer,
            }
            : {});
        let unocssGlobalBuildBundleIndex = config.plugins.findIndex((p) => p.name === 'unocss:global:build:bundle');
        if (unocssGlobalBuildBundleIndex === -1) {
            unocssGlobalBuildBundleIndex = config.plugins.findIndex((p) => p.name === 'unocss:global:build:generate');
        }
        const hasUnocssGlobalBuildBundle = unocssGlobalBuildBundleIndex > -1;
        // unocss 是根据 .css 后缀来编译文件，需要先保持 css 文件后缀为 .css，等 unocss 处理完后，再重置回正确的文件后缀
        const cssExtname = hasUnocssGlobalBuildBundle ? '.css' : extname;
        (0, uni_cli_shared_1.injectCssPostPlugin)(config, (0, uni_cli_shared_1.cssPostPlugin)(config, {
            platform: process.env.UNI_PLATFORM,
            chunkCssFilename(id) {
                if (id === mainPath) {
                    return 'app' + cssExtname;
                }
                else if ((0, entry_1.isUniPageUrl)(id)) {
                    return normalizeCssChunkFilename((0, entry_1.parseVirtualPagePath)(id), cssExtname);
                }
                else if ((0, entry_1.isUniComponentUrl)(id)) {
                    return normalizeCssChunkFilename((0, entry_1.parseVirtualComponentPath)(id), cssExtname);
                }
                else if (id.startsWith('uni_modules://')) {
                    return normalizeCssChunkFilename(id.replace('uni_modules://', ''), cssExtname);
                }
            },
            chunkCssCode(filename, cssCode) {
                // 如果是加密组件，不生成css
                if (filename.startsWith('uni_modules')) {
                    const pluginId = filename.split('/')[1];
                    const encryptType = (0, uni_cli_shared_1.getUniModulesEncryptType)(pluginId);
                    if (encryptType === 'easycom') {
                        return '';
                    }
                }
                const isX = process.env.UNI_APP_X === 'true';
                cssCode = (0, uni_cli_shared_1.transformScopedCss)(cssCode);
                if (isX) {
                    /**
                     * .xxx::part(yyy)替换为.xxx .-_part__yyy_-
                     * 小程序本身不支持::part选择器，直接替换即可
                     * 运行时绑定在内置组件上的part属性生成对应的class合并到class属性内，例如：`^-_part__yyy_-`
                     * ^的作用参考：[引用页面或父组件的样式](https://developers.weixin.qq.com/miniprogram/dev/framework/custom-component/wxml-wxss.html#%E5%BC%95%E7%94%A8%E9%A1%B5%E9%9D%A2%E6%88%96%E7%88%B6%E7%BB%84%E4%BB%B6%E7%9A%84%E6%A0%B7%E5%BC%8F)
                     */
                    cssCode = (0, uni_cli_shared_1.transformPartSelector)(cssCode);
                }
                if (filename === 'app' + cssExtname) {
                    const componentCustomHiddenCss = (component &&
                        component.vShow &&
                        genComponentCustomHiddenCss(component.vShow)) ||
                        '';
                    const realCssVars = isX ? uvueCssVars : cssVars;
                    if (config.isProduction) {
                        return (cssCode +
                            (process.env.UNI_PLATFORM !== 'mp-weixin'
                                ? genShadowCss(cdn || 0)
                                : '') +
                            realCssVars +
                            componentCustomHiddenCss);
                    }
                    else {
                        return cssCode + realCssVars + componentCustomHiddenCss;
                    }
                }
                if (isX) {
                    if (component?.[':host']) {
                        const flexDirection = (0, uni_cli_shared_1.parseUniXFlexDirection)((0, uni_cli_shared_1.parseManifestJsonOnce)(process.env.UNI_INPUT_DIR));
                        // 微信小程序使用 page 标签选择器会产生警告，支付宝小程序主动添加 page，解决 :host 选择器在页面中不生效的问题 https://opendocs.alipay.com/mini/framework/component-template#%3Ahost%20%E9%80%89%E6%8B%A9%E5%99%A8
                        const selector = process.env.UNI_PLATFORM === 'mp-alipay'
                            ? ':host,page'
                            : ':host';
                        cssCode = `${selector}{display:flex;flex-direction:${flexDirection}}\n${cssCode}`;
                    }
                    if (!(0, uni_cli_shared_1.isMiniProgramPageFile)(filename)) {
                        return cssCode;
                    }
                    /**
                     * 此方法将subPackages中的页面合并到了pages内
                     */
                    const pagesJson = (0, uni_cli_shared_1.parsePagesJsonOnce)(process.env.UNI_INPUT_DIR, process.env.UNI_PLATFORM);
                    const page = pagesJson.pages.find((page) => page.path === (0, uni_cli_shared_1.removeExt)(filename));
                    if (!page) {
                        return cssCode;
                    }
                    /**
                     * 何时不重置样式？
                     * - page.style.enabelUcssReset为false
                     * - page.style.enableUcssReset为空，pagesJson.globalStyle.enableUcssReset为false
                     * - page.style.enableUcssReset为空，pagesJson.globalStyle.enableUcssReset为空，page.style.renderer为skyline
                     */
                    const shouldNotResetStyle = page.style.enableUcssReset === false ||
                        (page.style.enableUcssReset == null &&
                            pagesJson.globalStyle.enableUcssReset === false) ||
                        (page.style.enableUcssReset == null &&
                            pagesJson.globalStyle.enableUcssReset == null &&
                            page.style.renderer === 'skyline');
                    if (!shouldNotResetStyle) {
                        /**
                         * 兼容发布为小程序分包模式
                         */
                        const uvueCssPath = (0, uni_cli_shared_1.relativeFile)(filename, `uvue${extname}`);
                        cssCode = `@import "${uvueCssPath}";\n` + cssCode;
                        // let addUvueCss = false
                        // if (
                        //   process.env.UNI_APP_STYLE_ISOLATION_VERSION === '2' &&
                        //   process.env.UNI_APP_X === 'true'
                        // ) {
                        //   const basePath = path.join(
                        //     process.env.UNI_INPUT_DIR!,
                        //     removeExt(filename)
                        //   )
                        //   const styleIsolation =
                        //     findMiniProgramComponentStyleIsolation(basePath + '.uvue') ||
                        //     findMiniProgramComponentStyleIsolation(basePath + '.vue')
                        //   if (
                        //     styleIsolation &&
                        //     styleIsolation.isPage &&
                        //     styleIsolation.styleIsolation === 'isolated'
                        //   ) {
                        //     addUvueCss = true
                        //   }
                        // } else {
                        //   addUvueCss = true
                        // }
                        // if (addUvueCss) {
                        //   /**
                        //    * 兼容发布为小程序分包模式
                        //    */
                        //   const uvueCssPath = relativeFile(filename, `uvue${extname}`)
                        //   cssCode = `@import "${uvueCssPath}";\n` + cssCode
                        // }
                    }
                    return cssCode;
                }
                const nvueCssPaths = (0, pagesJson_1.getNVueCssPaths)(config);
                if (!nvueCssPaths || !nvueCssPaths.length) {
                    return cssCode;
                }
                const normalized = (0, uni_cli_shared_1.normalizePath)(filename);
                if (nvueCssPaths.find((pageCssPath) => pageCssPath === normalized)) {
                    debugNVueCss(normalized);
                    return (`@import "${(0, uni_cli_shared_1.relativeFile)(normalized, 'nvue' + extname)}";\n` +
                        cssCode);
                }
                return cssCode;
            },
        }));
        (0, uni_cli_shared_1.injectAssetPlugin)(config);
        if (hasUnocssGlobalBuildBundle && extname !== '.css') {
            ;
            config.plugins.splice(unocssGlobalBuildBundleIndex + 1, 0, adjustCssExtname(extname));
        }
    };
}
exports.createConfigResolved = createConfigResolved;
function adjustCssExtname(extname) {
    return {
        name: 'uni:adjust-css-extname',
        generateBundle: {
            order: 'post',
            handler(_, bundle) {
                const files = Object.keys(bundle);
                files.forEach((name) => {
                    if (name.endsWith('.css')) {
                        const asset = bundle[name];
                        (0, shared_1.isString)(asset.source) &&
                            (asset.source = asset.source.replace(/\*\,/g, 'page,'));
                        this.emitFile({
                            fileName: name.replace('.css', extname),
                            type: 'asset',
                            source: asset.source,
                        });
                        delete bundle[name];
                    }
                });
            },
        },
    };
}
function fixUnocss(config) {
    const unocssGlobalBuildScan = config.plugins.find((p) => p.name === 'unocss:global:build:scan');
    // TODO 原始的 scan 的 buildStart 会清空 vfsLayerMap，导致 watch 时，load 阶段 /__uno.css 获取不到
    // https://github.com/antfu/unocss/blob/main/packages/vite/src/modes/global/build.ts#L25
    if (unocssGlobalBuildScan) {
        // 隐患: task 未被清空
        unocssGlobalBuildScan.buildStart = () => { };
    }
}
