"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createTransformTag = void 0;
const compiler_core_1 = require("@vue/compiler-core");
const ast_1 = require("../../vite/utils/ast");
function createTransformTag(opts) {
    return function transformTag(node, context) {
        if (!(0, ast_1.isElementNode)(node)) {
            return;
        }
        const oldTag = node.tag;
        const newTag = opts[oldTag];
        if (!newTag) {
            return;
        }
        // TODO: 临时 dom2 硬编码处理 tagType，待后续优化
        if (process.env.UNI_APP_X_DOM2 === 'true' && oldTag === 'cover-view') {
            node.tagType = compiler_core_1.ElementTypes.ELEMENT;
        }
        node.tag = newTag;
    };
}
exports.createTransformTag = createTransformTag;
