"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.uniAppCssPlugin = void 0;
const uni_cli_shared_1 = require("@dcloudio/uni-cli-shared");
const uni_nvue_styler_1 = require("@dcloudio/uni-nvue-styler");
function uniAppCssPlugin(resolvedConfig) {
    return {
        name: 'vite:css-post',
        buildStart() {
            // 用于覆盖原始插件方法
            // noop
        },
        async transform(source, filename) {
            if (!uni_cli_shared_1.cssLangRE.test(filename) || uni_cli_shared_1.commonjsProxyRE.test(filename)) {
                return;
            }
            if (source.includes('#endif')) {
                source = (0, uni_cli_shared_1.preUVueCss)(source, filename);
            }
            source = (0, uni_cli_shared_1.parseAssets)(resolvedConfig, source);
            // 仅做校验使用
            const { messages, code } = await (0, uni_nvue_styler_1.parse)(source, {
                filename,
                logLevel: 'WARNING',
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
            return { code: `export default ${code}`, map: { mappings: '' } };
        },
        generateBundle() {
            // 用于覆盖原始插件方法
            // noop
        },
    };
}
exports.uniAppCssPlugin = uniAppCssPlugin;
