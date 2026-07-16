"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.transformRoot = void 0;
const compiler_core_1 = require("@vue/compiler-core");
const uni_cli_shared_1 = require("@dcloudio/uni-cli-shared");
const uni_shared_1 = require("@dcloudio/uni-shared");
const ast_1 = require("../ast");
const types_1 = require("@babel/types");
const codegen_1 = require("../codegen");
const CSS_VARS = '__cssVars()';
const STATUS_BAR_HEIGHT_VAR = '--status-bar-height';
const UNI_SAFE_AREA_INSET_BOTTOM_VAR = '--uni-safe-area-inset-bottom';
const UNIT = 'px';
const transformRoot = (node, context) => {
    if (node.type !== compiler_core_1.NodeTypes.ROOT) {
        return;
    }
    const hasBindingCssVars = context.bindingCssVars.length > 0;
    node.children.forEach((child) => {
        if (!(0, uni_cli_shared_1.isElementNode)(child)) {
            return;
        }
        hasBindingCssVars && addCssVars(child, context);
        context.isX && traverseChildren(child, context);
    });
};
exports.transformRoot = transformRoot;
function addCssVars(node, context) {
    const styleProp = (0, compiler_core_1.findProp)(node, 'style', true);
    if (!styleProp) {
        node.props.push((0, uni_cli_shared_1.createBindDirectiveNode)('style', CSS_VARS));
    }
    else {
        if (styleProp.exp && (0, uni_cli_shared_1.isSimpleExpressionNode)(styleProp.exp)) {
            let expr = (0, ast_1.parseExpr)(styleProp.exp.content, context);
            if ((0, types_1.isArrayExpression)(expr)) {
                expr.elements.push((0, types_1.identifier)(CSS_VARS));
            }
            else {
                expr = (0, types_1.arrayExpression)([expr, (0, types_1.identifier)(CSS_VARS)]);
            }
            styleProp.exp.content = (0, codegen_1.genBabelExpr)(expr);
        }
    }
}
function addStatusBarStyle(node, context) {
    const style = (0, types_1.objectExpression)([
        (0, types_1.objectProperty)((0, types_1.stringLiteral)(STATUS_BAR_HEIGHT_VAR), (0, types_1.templateLiteral)([
            (0, types_1.templateElement)({ raw: '', cooked: '' }, false),
            (0, types_1.templateElement)({ raw: UNIT, cooked: UNIT }, true),
        ], [(0, types_1.identifier)(uni_shared_1.UNI_STATUS_BAR_HEIGHT)])),
        (0, types_1.objectProperty)((0, types_1.stringLiteral)(UNI_SAFE_AREA_INSET_BOTTOM_VAR), (0, types_1.templateLiteral)([
            (0, types_1.templateElement)({ raw: '', cooked: '' }, false),
            (0, types_1.templateElement)({ raw: UNIT, cooked: UNIT }, true),
        ], [(0, types_1.identifier)(uni_shared_1.UNI_SAFE_AREA_INSET_BOTTOM)])),
    ]);
    const styleProp = (0, compiler_core_1.findProp)(node, 'style', true);
    if (!styleProp) {
        node.props.push((0, uni_cli_shared_1.createBindDirectiveNode)('style', (0, codegen_1.genBabelExpr)(style)));
    }
    else {
        if (styleProp.exp && (0, uni_cli_shared_1.isSimpleExpressionNode)(styleProp.exp)) {
            const originalExpr = (0, ast_1.parseExpr)(styleProp.exp.content, context);
            const newExpr = (0, types_1.isArrayExpression)(originalExpr)
                ? (0, types_1.arrayExpression)([...originalExpr.elements, style])
                : (0, types_1.arrayExpression)([originalExpr, style]);
            styleProp.exp.content = (0, codegen_1.genBabelExpr)(newExpr);
        }
    }
}
function traverseChildren(node, context) {
    if ((0, uni_cli_shared_1.isUserComponent)(node, context)) {
        return;
    }
    if (node.tag !== 'template' && node.tag !== 'slot') {
        (0, uni_cli_shared_1.isElementNode)(node) && addStatusBarStyle(node, context);
    }
    else {
        node.children.forEach((child) => {
            traverseChildren(child, context);
        });
    }
}
