"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.transformDirection = void 0;
const vite_1 = require("../../../vite");
const utils_1 = require("../../utils");
const compiler_core_1 = require("@vue/compiler-core");
const shared_1 = require("@vue/shared");
/**
 * 将direction属性转化为scroll-x和scroll-y
 * 注意transformMPBuiltInTag内会讲list-view转化为scroll-view，所以此transform应该在transformMPBuiltInTag之后执行
 */
const transformDirection = function (node, context) {
    if (!(0, vite_1.isElementNode)(node)) {
        return;
    }
    if (node.tag !== 'scroll-view') {
        return;
    }
    const directionPropIndex = node.props.findIndex((prop) => (0, utils_1.isPropNameEquals)(prop, 'direction'));
    const scrollXPropIndex = node.props.findIndex((prop) => (0, utils_1.isPropNameEquals)(prop, 'scrollX'));
    const scrollYPropIndex = node.props.findIndex((prop) => (0, utils_1.isPropNameEquals)(prop, 'scrollY'));
    if (scrollXPropIndex > -1 || scrollYPropIndex > -1) {
        return;
    }
    if (directionPropIndex === -1 ||
        (scrollXPropIndex !== -1 && scrollYPropIndex !== -1)) {
        node.props.push((0, utils_1.createAttributeNode)('scroll-y', 'true'));
        return;
    }
    const directionProp = node.props[directionPropIndex];
    if ((0, vite_1.isAttributeNode)(directionProp)) {
        const directionValue = directionProp.value?.content;
        const scrollX = directionValue === 'horizontal' || directionValue === 'all';
        const scrollY = !directionValue ||
            directionValue === 'vertical' ||
            directionValue === 'all';
        node.props.splice(directionPropIndex, 1);
        scrollX && node.props.push((0, utils_1.createAttributeNode)('scroll-x', '' + scrollX));
        scrollY && node.props.push((0, utils_1.createAttributeNode)('scroll-y', '' + scrollY));
    }
    else if (directionProp.type === compiler_core_1.NodeTypes.DIRECTIVE) {
        if (!directionProp.arg ||
            !(0, vite_1.isSimpleExpressionNode)(directionProp.arg) ||
            !directionProp.exp ||
            !((0, vite_1.isSimpleExpressionNode)(directionProp.exp) ||
                (0, vite_1.isCompoundExpressionNode)(directionProp.exp))) {
            return;
        }
        const exp = stringifyExpression(directionProp.exp);
        if (!exp) {
            return;
        }
        const scrollX = `(${exp}) === 'horizontal' || (${exp}) === 'all'`;
        const scrollY = `!(${exp}) || (${exp}) === 'vertical' || (${exp}) === 'all'`;
        node.props.splice(directionPropIndex, 1);
        node.props.push((0, utils_1.createBindDirectiveNode)('scroll-x', scrollX));
        node.props.push((0, utils_1.createBindDirectiveNode)('scroll-y', scrollY));
    }
};
exports.transformDirection = transformDirection;
function stringifyExpression(exp) {
    if ((0, vite_1.isSimpleExpressionNode)(exp)) {
        return exp.content;
    }
    if ((0, vite_1.isCompoundExpressionNode)(exp)) {
        const children = [];
        for (const child of exp.children) {
            if ((0, shared_1.isString)(child)) {
                children.push(child);
            }
            else if ((0, shared_1.isSymbol)(child)) {
                return;
            }
            else {
                const content = stringifyExpression(child);
                if (content === undefined) {
                    return;
                }
                children.push(content);
            }
        }
        return children.join('');
    }
}
