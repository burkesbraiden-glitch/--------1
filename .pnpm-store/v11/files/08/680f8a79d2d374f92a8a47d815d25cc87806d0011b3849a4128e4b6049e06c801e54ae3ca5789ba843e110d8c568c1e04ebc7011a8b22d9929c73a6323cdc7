"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.transformVBindAttrs = void 0;
const compiler_core_1 = require("@vue/compiler-core");
const uni_cli_shared_1 = require("@dcloudio/uni-cli-shared");
const V_BIND_ATTRS = '$attrs';
const transformVBindAttrs = (node, context) => {
    // 仅在 uni-app-x 微信/支付宝小程序下兜底处理原生节点的 v-bind="$attrs"，
    // 这样可以避免误伤 uni-app 以及 uni-app-x 的其他平台。
    if (!supportVBindAttrs(context) || !(0, uni_cli_shared_1.isPlainElementNode)(node)) {
        return;
    }
    const { props } = node;
    for (let i = 0; i < props.length; i++) {
        const prop = props[i];
        if (!isVBindAttrsDirective(prop)) {
            continue;
        }
        const attrsExp = prop.exp.content;
        const newProps = [];
        // class/style/click 需要尽量保留原有声明顺序，避免覆盖规则变化。
        mergeBindProp(props, 'class', `${attrsExp}.class`, i, newProps);
        mergeBindProp(props, 'style', `${attrsExp}.style`, i, newProps);
        mergeOnProp(props, 'click', `${attrsExp}.onClick`, i, newProps);
        // id 与现有逻辑保持一致：只在后面没有显式 id 时补充，
        // 这样可以继续复用“后写覆盖前写”的规则。
        if (!hasFollowingId(props, i)) {
            newProps.push((0, uni_cli_shared_1.createBindDirectiveNode)('id', `${attrsExp}.id`));
        }
        props.splice(i, 1, ...newProps);
        i += newProps.length - 1;
    }
};
exports.transformVBindAttrs = transformVBindAttrs;
function supportVBindAttrs(context) {
    return (context.isX &&
        (process.env.UNI_PLATFORM === 'mp-weixin' ||
            process.env.UNI_PLATFORM === 'mp-alipay'));
}
function isVBindAttrsDirective(prop) {
    return ((0, uni_cli_shared_1.isDirectiveNode)(prop) &&
        prop.name === 'bind' &&
        !prop.arg &&
        prop.modifiers.length === 0 &&
        prop.exp?.type === compiler_core_1.NodeTypes.SIMPLE_EXPRESSION &&
        prop.exp.content === V_BIND_ATTRS);
}
function mergeBindProp(props, name, attrsExp, vBindIndex, newProps) {
    const propIndex = props.findIndex((prop) => (0, uni_cli_shared_1.isDirectiveNode)(prop) &&
        prop.name === 'bind' &&
        (0, compiler_core_1.isStaticArgOf)(prop.arg, name));
    if (propIndex < 0) {
        newProps.push((0, uni_cli_shared_1.createBindDirectiveNode)(name, attrsExp));
        return;
    }
    const prop = props[propIndex];
    if (prop.exp?.type !== compiler_core_1.NodeTypes.SIMPLE_EXPRESSION) {
        return;
    }
    prop.exp.content =
        propIndex < vBindIndex
            ? `[${prop.exp.content}, ${attrsExp}]`
            : `[${attrsExp}, ${prop.exp.content}]`;
}
function mergeOnProp(props, name, attrsExp, vBindIndex, newProps) {
    const propIndex = props.findIndex((prop) => (0, uni_cli_shared_1.isDirectiveNode)(prop) &&
        prop.name === 'on' &&
        (0, compiler_core_1.isStaticArgOf)(prop.arg, name));
    if (propIndex < 0) {
        newProps.push((0, uni_cli_shared_1.createOnDirectiveNode)(name, attrsExp));
        return;
    }
    const prop = props[propIndex];
    if (prop.exp?.type !== compiler_core_1.NodeTypes.SIMPLE_EXPRESSION) {
        return;
    }
    prop.exp.content =
        propIndex < vBindIndex
            ? `[${prop.exp.content}, ${attrsExp}]`
            : `[${attrsExp}, ${prop.exp.content}]`;
}
function hasFollowingId(props, index) {
    return props.slice(index + 1).some((prop) => {
        return (((0, uni_cli_shared_1.isAttributeNode)(prop) && prop.name === 'id') ||
            ((0, uni_cli_shared_1.isDirectiveNode)(prop) &&
                prop.name === 'bind' &&
                (0, compiler_core_1.isStaticArgOf)(prop.arg, 'id')));
    });
}
