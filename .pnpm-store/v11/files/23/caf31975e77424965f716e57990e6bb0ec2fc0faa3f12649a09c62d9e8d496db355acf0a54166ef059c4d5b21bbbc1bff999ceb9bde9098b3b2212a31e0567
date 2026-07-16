"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.rewriteImportVue = exports.rewriteImportVuePlugin = void 0;
const parser_1 = require("@babel/parser");
const magic_string_1 = __importDefault(require("magic-string"));
function rewriteImportVuePlugin() {
    return {
        name: 'uni:rewrite-import-vue',
        enforce: 'post',
        async renderChunk(source, chunk) {
            if (chunk.fileName.endsWith('.js')) {
                const rewritten = rewriteImportVue(source);
                if (rewritten.hasChanged()) {
                    return {
                        code: rewritten.toString(),
                        // 必须指定hires，不然部分情况可能会无法正确映射行号。
                        map: rewritten.generateMap({ hires: 'boundary' }),
                    };
                }
            }
        },
    };
}
exports.rewriteImportVuePlugin = rewriteImportVuePlugin;
/**
 * import { xx as yy, zz } from 'vue' =>
 * const { xx: yy, zz } = globalThis.Vue
 */
function rewriteImportVue(input) {
    const ast = (0, parser_1.parse)(input, {
        sourceType: 'module',
    }).program.body;
    const s = new magic_string_1.default(input);
    ast.forEach((node) => {
        if (node.type === 'ImportDeclaration' && node.source.value === 'vue') {
            const specifiers = node.specifiers;
            const imports = [];
            specifiers.forEach((specifier) => {
                if (specifier.type === 'ImportSpecifier') {
                    const imported = specifier.imported.name;
                    const local = specifier.local.name;
                    if (imported === local) {
                        imports.push(imported);
                    }
                    else {
                        imports.push(`${imported}: ${local}`);
                    }
                }
                else if (specifier.type === 'ImportDefaultSpecifier') {
                    const local = specifier.local.name;
                    imports.push(`default: ${local}`);
                }
                else if (specifier.type === 'ImportNamespaceSpecifier') {
                    const local = specifier.local.name;
                    s.overwrite(node.start, node.end, `const ${local} = globalThis.Vue`);
                    return;
                }
            });
            if (imports.length > 0) {
                s.overwrite(node.start, node.end, `const { ${imports.join(', ')} } = globalThis.Vue`);
            }
            else {
                s.remove(node.start, node.end);
            }
        }
    });
    return s;
}
exports.rewriteImportVue = rewriteImportVue;
