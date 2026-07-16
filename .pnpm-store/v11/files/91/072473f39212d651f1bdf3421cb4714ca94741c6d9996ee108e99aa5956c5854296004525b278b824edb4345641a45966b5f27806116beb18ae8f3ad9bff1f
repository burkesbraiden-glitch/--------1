"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.rewriteCompilerSfcParse = void 0;
const uni_cli_shared_1 = require("@dcloudio/uni-cli-shared");
/**
 * 重写 @vue/compiler-sfc 的 parse 函数
 * web 平台下，如果 SFC 没有 style，注入一个默认的空 style
 */
function rewriteCompilerSfcParse() {
    const compilerSfc = require((0, uni_cli_shared_1.resolveBuiltIn)('@vue/compiler-sfc'));
    const { parse } = compilerSfc;
    compilerSfc.parse = (source, options) => {
        const result = parse(source, options);
        // 如果没有 style，注入一个默认的空 style
        if (result.descriptor.styles.length === 0) {
            result.descriptor.styles = [(0, uni_cli_shared_1.createDefaultSFCStyleBlock)(source)];
        }
        return result;
    };
}
exports.rewriteCompilerSfcParse = rewriteCompilerSfcParse;
