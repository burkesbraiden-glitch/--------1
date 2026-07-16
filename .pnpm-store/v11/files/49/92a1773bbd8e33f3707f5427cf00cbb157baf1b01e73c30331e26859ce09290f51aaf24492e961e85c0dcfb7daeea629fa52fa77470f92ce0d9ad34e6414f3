"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.transformAttributePart = void 0;
const uni_shared_1 = require("@dcloudio/uni-shared");
const compiler_core_1 = require("@vue/compiler-core");
const transformAttributePart = (node, context) => {
    if (node.type !== compiler_core_1.NodeTypes.ELEMENT) {
        return;
    }
    const staticClassProp = node.props.find((prop) => prop.type === compiler_core_1.NodeTypes.ATTRIBUTE && prop.name === 'class');
    const dynamicClassProp = node.props.find((prop) => prop.type === compiler_core_1.NodeTypes.DIRECTIVE &&
        prop.arg?.type === compiler_core_1.NodeTypes.SIMPLE_EXPRESSION &&
        prop.arg.content === 'class');
    node.props.forEach((prop) => {
        // 将part属性计算后添加到class中，支持动态part，支持多part
        if (prop.type === compiler_core_1.NodeTypes.ATTRIBUTE && prop.name === 'part') {
            // 静态part属性
            const partClasses = (0, uni_shared_1.batchGetPartClass)(prop.value?.content || '');
            if (staticClassProp) {
                // 已有静态class属性
                staticClassProp.value.content += ` ${partClasses}`;
            }
            else if (dynamicClassProp) {
                // 已有动态class属性
                dynamicClassProp.exp = (0, compiler_core_1.createCompoundExpression)([
                    dynamicClassProp.exp,
                    ` + ' ${partClasses}'`,
                ]);
            }
            else {
                // 无class属性
                node.props.push({
                    type: compiler_core_1.NodeTypes.ATTRIBUTE,
                    name: 'class',
                    value: {
                        type: compiler_core_1.NodeTypes.TEXT,
                        content: partClasses,
                        loc: compiler_core_1.locStub,
                    },
                    loc: compiler_core_1.locStub,
                    nameLoc: compiler_core_1.locStub,
                });
            }
        }
        else if (prop.type === compiler_core_1.NodeTypes.DIRECTIVE &&
            prop.arg?.type === compiler_core_1.NodeTypes.SIMPLE_EXPRESSION &&
            prop.arg.content === 'part') {
            // 动态part属性
            // TODO 使用uni-shared内的getPartClass
            const partClassExp = (0, compiler_core_1.createCompoundExpression)([
                `(`,
                prop.exp,
                `).split(/\\s+/).filter(Boolean).map(partName => \`-_part__\${partName}_-\`).join(' ')`,
            ]);
            if (staticClassProp) {
                // 已有静态class属性，需要转为动态class属性
                node.props.splice(node.props.indexOf(staticClassProp), 1);
                node.props.push({
                    type: compiler_core_1.NodeTypes.DIRECTIVE,
                    name: 'bind',
                    exp: (0, compiler_core_1.createCompoundExpression)([
                        staticClassProp.value.content,
                        `+ ' ' +`,
                        partClassExp,
                    ]),
                    arg: {
                        type: compiler_core_1.NodeTypes.SIMPLE_EXPRESSION,
                        content: 'class',
                        isStatic: true,
                        loc: compiler_core_1.locStub,
                        constType: compiler_core_1.ConstantTypes.NOT_CONSTANT,
                    },
                    loc: compiler_core_1.locStub,
                    modifiers: [],
                });
            }
            else if (dynamicClassProp) {
                // 已有动态class属性
                dynamicClassProp.exp = (0, compiler_core_1.createCompoundExpression)([
                    dynamicClassProp.exp,
                    ` + ' ' +`,
                    partClassExp,
                ]);
            }
            else {
                // 无class属性
                node.props.push({
                    type: compiler_core_1.NodeTypes.DIRECTIVE,
                    name: 'bind',
                    exp: partClassExp,
                    arg: {
                        type: compiler_core_1.NodeTypes.SIMPLE_EXPRESSION,
                        content: 'class',
                        isStatic: true,
                        loc: compiler_core_1.locStub,
                        constType: compiler_core_1.ConstantTypes.NOT_CONSTANT,
                    },
                    loc: compiler_core_1.locStub,
                    modifiers: [],
                });
            }
        }
    });
};
exports.transformAttributePart = transformAttributePart;
