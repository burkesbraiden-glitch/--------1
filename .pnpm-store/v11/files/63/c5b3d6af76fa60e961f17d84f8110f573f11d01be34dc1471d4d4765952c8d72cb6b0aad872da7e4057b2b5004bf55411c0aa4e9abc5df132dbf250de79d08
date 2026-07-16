"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.transformTeleport = void 0;
const utils_1 = require("../utils");
const vite_1 = require("../../vite");
const compiler_core_1 = require("@vue/compiler-core");
const shared_1 = require("@vue/shared");
const transformTeleport = function (node) {
    if (!(0, vite_1.isElementNode)(node)) {
        return;
    }
    if (node.tag !== 'teleport') {
        return;
    }
    node.tag = 'root-portal';
    node.tagType = compiler_core_1.ElementTypes.ELEMENT;
    const disabledProp = (0, compiler_core_1.findProp)(node, 'disabled', false, true);
    if (disabledProp) {
        // transform `disabled` prop to `enable` prop with inverse value
        if ((0, vite_1.isAttributeNode)(disabledProp)) {
            const disabledPropIndex = node.props.indexOf(disabledProp);
            node.props.splice(disabledPropIndex, 1, (0, utils_1.createBindDirectiveNode)('enable', (0, compiler_core_1.createSimpleExpression)('false', false)));
        }
        else if ((0, vite_1.isDirectiveNode)(disabledProp)) {
            disabledProp.arg = (0, compiler_core_1.createSimpleExpression)('enable', true);
            disabledProp.exp = createEnableExpression(disabledProp.exp);
        }
    }
    const toProp = (0, compiler_core_1.findProp)(node, 'to');
    if (toProp) {
        // delete `to` prop since it is not supported in mini program
        node.props.splice(node.props.indexOf(toProp), 1);
    }
    const deferProp = (0, compiler_core_1.findProp)(node, 'defer', false, true);
    if (deferProp) {
        // delete `defer` prop since it is not supported in mini program
        node.props.splice(node.props.indexOf(deferProp), 1);
    }
};
exports.transformTeleport = transformTeleport;
function createEnableExpression(exp) {
    const content = exp && stringifyExpression(exp);
    return (0, compiler_core_1.createSimpleExpression)(content ? `!(${content})` : 'true', false);
}
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
