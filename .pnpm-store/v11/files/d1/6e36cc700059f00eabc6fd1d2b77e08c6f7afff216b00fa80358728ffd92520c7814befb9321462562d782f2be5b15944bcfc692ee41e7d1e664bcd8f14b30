"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.transformIdentifier = void 0;
const compiler_core_1 = require("@vue/compiler-core");
const utils_1 = require("./utils");
const transformClass_1 = require("./transformClass");
const transformStyle_1 = require("./transformStyle");
const transformHidden_1 = require("./transformHidden");
const transformId_1 = require("./transformId");
const runtimeHelpers_1 = require("../runtimeHelpers");
const transformSlot_1 = require("./transformSlot");
const vSlot_1 = require("./vSlot");
const transformRef_1 = require("./transformRef");
const transformComponent_1 = require("./transformComponent");
const uni_cli_shared_1 = require("@dcloudio/uni-cli-shared");
const uni_cli_shared_2 = require("@dcloudio/uni-cli-shared");
const fs_1 = __importDefault(require("fs"));
const compiler_sfc_1 = require("@vue/compiler-sfc");
const transformUniElement_1 = require("./transformUniElement");
// externalClasses 缓存，包含 mtime 用于检测文件变化
const UNI_APP_STYLE_CLASSES = process.env.UNI_APP_STYLE_ISOLATION_VERSION === '2' &&
    process.env.UNI_APP_X === 'true' &&
    process.env.UNI_PLATFORM?.startsWith('mp-');
const transformIdentifier = (node, context) => {
    return function transformIdentifier() {
        if (node.type === compiler_core_1.NodeTypes.INTERPOLATION) {
            const content = node.content;
            let isFilter = (0, utils_1.isFilterExpr)(content, context);
            if (!isFilter) {
                node.content = (0, utils_1.rewriteExpression)((0, compiler_core_1.createCompoundExpression)([
                    `${context.helperString(runtimeHelpers_1.TO_DISPLAY_STRING)}(`,
                    content,
                    `)`,
                ]), context);
            }
        }
        else if ((0, compiler_core_1.isSlotOutlet)(node)) {
            (0, transformSlot_1.rewriteSlot)(node, context);
        }
        else if ((0, uni_cli_shared_1.isElementNode)(node)) {
            let hasClassBinding = false;
            let hasStyleBinding = false;
            let hasHiddenBinding = false;
            let hasIdBinding = false;
            const { props, tagType } = node;
            const virtualHost = !!(context.miniProgram.component?.mergeVirtualHostAttributes &&
                context.rootNode === node);
            const isElement = tagType === compiler_core_1.ElementTypes.ELEMENT;
            (0, transformRef_1.rewriteRef)(node, context);
            if (context.isX) {
                if (virtualHost) {
                    for (let i = 0; i < props.length; i++) {
                        const dir = props[i];
                        if ((0, uni_cli_shared_1.isDirectiveNode)(dir)) {
                            if ((0, transformId_1.isIdBinding)(dir)) {
                                hasIdBinding = true;
                                (0, transformId_1.rewriteId)(i, dir, props, virtualHost, context, true);
                            }
                        }
                    }
                    if (!hasIdBinding) {
                        hasIdBinding = true;
                        props.push((0, transformId_1.createVirtualHostId)(props, context, true));
                    }
                    const staticIdIndex = (0, transformId_1.findStaticIdIndex)(props);
                    if (staticIdIndex > -1) {
                        props.splice(staticIdIndex, 1);
                    }
                }
                (0, transformUniElement_1.rewriteId)(node, context);
            }
            // 获取组件的 externalClasses，用于后续跳过已处理的绑定
            let externalClasses = [];
            if ((0, uni_cli_shared_1.isUserComponent)(node, context)) {
                externalClasses = getExternalClasses(node, context.filename, context.expressionPlugins);
                // 收集页面使用的 externalClasses 信息（静态值和是否有动态绑定）
                if (UNI_APP_STYLE_CLASSES &&
                    context.filename &&
                    (0, uni_cli_shared_2.isUniPageFile)(context.filename)) {
                    let hasAppAndPageStyle = false;
                    // 仅发行模式下检测
                    if (process.env.NODE_ENV !== 'development') {
                        const source = resolveSource(node);
                        if (source) {
                            hasAppAndPageStyle = checkComponentAppAndPageIsolation(source, context);
                        }
                    }
                    if (externalClasses.length > 0 || hasAppAndPageStyle) {
                        collectPageExternalClasses(context.filename, node, externalClasses, hasAppAndPageStyle);
                    }
                }
                // 微信小程序不需要处理 externalClasses
                if (process.env.UNI_PLATFORM === 'mp-weixin') {
                    externalClasses = [];
                }
                (0, transformComponent_1.rewriteBinding)(node, context, externalClasses);
            }
            let elementId = '';
            let skipIndex = [];
            // 第一步：在 x 中，先处理 id 属性，用于提前获取 elementId 对应的变量名
            if (context.isX) {
                for (let i = 0; i < props.length; i++) {
                    const dir = props[i];
                    if ((0, uni_cli_shared_1.isDirectiveNode)(dir)) {
                        const { arg, exp } = dir;
                        if (arg && exp && (0, uni_cli_shared_1.isSimpleExpressionNode)(arg)) {
                            if (arg.content === 'id' || arg.content === utils_1.ATTR_ELEMENT_ID) {
                                dir.exp = (0, utils_1.rewriteExpression)(exp, context);
                                elementId = dir.exp.content;
                                skipIndex.push(i);
                            }
                        }
                    }
                }
            }
            // 合并part class到class内
            if (context.isX && isElement) {
                const partProp = props.find((prop) => {
                    if ((0, uni_cli_shared_1.isDirectiveNode)(prop)) {
                        const { arg } = prop;
                        if (arg && (0, uni_cli_shared_1.isSimpleExpressionNode)(arg)) {
                            return arg.content === 'part';
                        }
                    }
                    else {
                        return prop.name === 'part';
                    }
                });
                if (partProp) {
                    const classProp = props.find((prop) => {
                        if ((0, uni_cli_shared_1.isDirectiveNode)(prop)) {
                            const { arg } = prop;
                            if (arg && (0, uni_cli_shared_1.isSimpleExpressionNode)(arg)) {
                                return arg.content === 'class';
                            }
                        }
                        else {
                            return prop.name === 'class';
                        }
                        return false;
                    });
                    if (classProp == null) {
                        const newClassDirExpr = (0, utils_1.rewriteExpression)((0, compiler_core_1.createCompoundExpression)([
                            context.helperString(runtimeHelpers_1.MERGE_PART_CLASS),
                            `(`,
                            (0, uni_cli_shared_1.isDirectiveNode)(partProp)
                                ? partProp.exp
                                : (0, compiler_core_1.createSimpleExpression)(`'${partProp.value?.content || ''}'`),
                            `)`,
                        ]), context);
                        props.push({
                            type: compiler_core_1.NodeTypes.DIRECTIVE,
                            name: 'bind',
                            exp: newClassDirExpr,
                            arg: (0, compiler_core_1.createSimpleExpression)('class', true),
                            modifiers: [],
                            loc: partProp.loc,
                        });
                        skipIndex.push(props.length - 1);
                    }
                    else if ((0, uni_cli_shared_1.isDirectiveNode)(classProp)) {
                        const originalClassExpr = classProp.exp;
                        classProp.exp = (0, utils_1.rewriteExpression)((0, compiler_core_1.createCompoundExpression)([
                            context.helperString(runtimeHelpers_1.MERGE_PART_CLASS),
                            `(`,
                            (0, uni_cli_shared_1.isDirectiveNode)(partProp)
                                ? partProp.exp
                                : (0, compiler_core_1.createSimpleExpression)(`'${partProp.value?.content || ''}'`),
                            `, `,
                            originalClassExpr,
                            `)`,
                        ]), context);
                        skipIndex.push(props.indexOf(classProp));
                    }
                    else {
                        const staticClass = classProp.value?.content || '';
                        const newClassDirExpr = (0, utils_1.rewriteExpression)((0, compiler_core_1.createCompoundExpression)([
                            context.helperString(runtimeHelpers_1.MERGE_PART_CLASS),
                            `(`,
                            (0, uni_cli_shared_1.isDirectiveNode)(partProp)
                                ? partProp.exp
                                : (0, compiler_core_1.createSimpleExpression)(`'${partProp.value?.content || ''}'`),
                            `, '${staticClass}')`,
                        ]), context);
                        const classPropIndex = props.indexOf(classProp);
                        props.splice(classPropIndex, 1, {
                            type: compiler_core_1.NodeTypes.DIRECTIVE,
                            name: 'bind',
                            exp: newClassDirExpr,
                            arg: (0, compiler_core_1.createSimpleExpression)('class', true),
                            modifiers: [],
                            loc: classProp.loc,
                        });
                        skipIndex.push(classPropIndex);
                    }
                }
            }
            for (let i = 0; i < props.length; i++) {
                if (context.isX) {
                    // 已经处理过了
                    if (skipIndex.includes(i)) {
                        continue;
                    }
                }
                const dir = props[i];
                if ((0, uni_cli_shared_1.isDirectiveNode)(dir)) {
                    const arg = dir.arg;
                    if (arg) {
                        // TODO 指令暂不不支持动态参数,v-bind:[arg] v-on:[event]
                        if (!((0, uni_cli_shared_1.isSimpleExpressionNode)(arg) && arg.isStatic)) {
                            // v-slot:[slotName] 支持
                            if (dir.name === 'slot') {
                                (0, vSlot_1.rewriteVSlot)(dir, context);
                            }
                            else {
                                props.splice(i, 1);
                                i--;
                                continue;
                            }
                        }
                    }
                    const exp = dir.exp;
                    if (exp) {
                        if (isBuiltIn(dir)) {
                            // noop
                        }
                        else if ((0, transformClass_1.isClassBinding)(dir)) {
                            hasClassBinding = true;
                            (0, transformClass_1.rewriteClass)(i, dir, props, virtualHost, context);
                        }
                        else if ((0, transformStyle_1.isStyleBinding)(dir)) {
                            hasStyleBinding = true;
                            (0, transformStyle_1.rewriteStyle)(i, dir, props, virtualHost, context, elementId);
                        }
                        else if ((0, transformHidden_1.isHiddenBinding)(dir)) {
                            hasHiddenBinding = true;
                            (0, transformHidden_1.rewriteHidden)(i, dir, props, virtualHost, context);
                        }
                        else if ((0, transformId_1.isIdBinding)(dir)) {
                            hasIdBinding = true;
                            (0, transformId_1.rewriteId)(i, dir, props, virtualHost, context);
                        }
                        else if ((0, transformComponent_1.isPropsBinding)(dir)) {
                            (0, transformComponent_1.rewritePropsBinding)(dir, node, context);
                        }
                        else {
                            if (context.isX &&
                                elementId &&
                                arg &&
                                (0, uni_cli_shared_1.isSimpleExpressionNode)(arg)) {
                                if (arg.content === utils_1.ATTR_SET_ELEMENT_STYLE) {
                                    dir.exp = (0, compiler_core_1.createSimpleExpression)(`$eS[${elementId}]`);
                                }
                                else if (arg.content === utils_1.ATTR_SET_ELEMENT_ANIMATION) {
                                    dir.exp = (0, compiler_core_1.createSimpleExpression)(`$eA[${elementId}]`);
                                }
                                else {
                                    dir.exp = (0, utils_1.rewriteExpression)(exp, context);
                                }
                            }
                            else {
                                dir.exp = (0, utils_1.rewriteExpression)(exp, context);
                            }
                        }
                    }
                }
            }
            if (virtualHost) {
                if (!hasClassBinding) {
                    hasClassBinding = true;
                    props.push((0, transformClass_1.createVirtualHostClass)(props, context));
                }
                if (!hasStyleBinding) {
                    hasStyleBinding = true;
                    props.push((0, transformStyle_1.createVirtualHostStyle)(props, context));
                }
                if (!hasHiddenBinding) {
                    hasHiddenBinding = true;
                    props.push((0, transformHidden_1.createVirtualHostHidden)(props, context));
                }
                if (!hasIdBinding) {
                    hasIdBinding = true;
                    props.push((0, transformId_1.createVirtualHostId)(props, context));
                }
            }
            if (hasClassBinding) {
                const staticClassIndex = (0, transformClass_1.findStaticClassIndex)(props);
                if (staticClassIndex > -1) {
                    props.splice(staticClassIndex, 1);
                }
            }
            if (hasStyleBinding) {
                const staticStyleIndex = (0, transformStyle_1.findStaticStyleIndex)(props);
                if (staticStyleIndex > -1) {
                    props.splice(staticStyleIndex, 1);
                }
            }
            if (hasHiddenBinding) {
                const staticHiddenIndex = (0, transformHidden_1.findStaticHiddenIndex)(props);
                if (staticHiddenIndex > -1) {
                    props.splice(staticHiddenIndex, 1);
                }
            }
            if (hasIdBinding) {
                const staticIdIndex = (0, transformId_1.findStaticIdIndex)(props);
                if (staticIdIndex > -1) {
                    props.splice(staticIdIndex, 1);
                }
            }
        }
    };
};
exports.transformIdentifier = transformIdentifier;
const builtInProps = [utils_1.ATTR_VUE_SLOTS];
function isBuiltIn({ arg, exp }) {
    return (arg &&
        (0, uni_cli_shared_1.isSimpleExpressionNode)(arg) &&
        builtInProps.includes(arg.content) &&
        exp &&
        (0, uni_cli_shared_1.isSimpleExpressionNode)(exp));
}
/**
 * 获取组件的 externalClasses
 * @param source 组件文件绝对路径
 * @param babelParserPlugins babel parser 插件
 * @returns externalClasses 数组，未找到时返回 undefined
 */
function getComponentExternalClasses(source, parentFile, babelParserPlugins) {
    if (!UNI_APP_STYLE_CLASSES) {
        return undefined;
    }
    let mtime;
    try {
        mtime = fs_1.default.statSync(source).mtimeMs;
    }
    catch {
        return undefined;
    }
    const cached = (0, uni_cli_shared_1.findMiniProgramComponentExternalClasses)(source);
    if (cached && cached.mtime === mtime) {
        return cached.classes;
    }
    let code;
    try {
        code = fs_1.default.readFileSync(source, 'utf-8');
    }
    catch {
        return undefined;
    }
    if (!(0, uni_cli_shared_1.hasExternalClasses)(code) && !code.includes('styleIsolation')) {
        (0, uni_cli_shared_1.updateMiniProgramComponentExternalClasses)(source, { mtime, classes: [] });
        return [];
    }
    let scriptContent;
    if (source) {
        const { descriptor } = (0, compiler_sfc_1.parse)(code, { filename: source });
        scriptContent =
            descriptor.scriptSetup?.content || descriptor.script?.content || '';
    }
    else {
        scriptContent = code;
    }
    if (!scriptContent ||
        (!(0, uni_cli_shared_1.hasExternalClasses)(scriptContent) &&
            !scriptContent.includes('styleIsolation'))) {
        (0, uni_cli_shared_1.updateMiniProgramComponentExternalClasses)(source, { mtime, classes: [] });
        return [];
    }
    let program;
    try {
        program = (0, uni_cli_shared_1.parseProgram)(scriptContent, source, {
            babelParserPlugins,
        });
    }
    catch (error) { }
    if (program) {
        const classes = (0, uni_cli_shared_1.parseExternalClasses)(program);
        (0, uni_cli_shared_1.updateMiniProgramComponentExternalClasses)(source, { mtime, classes });
        return classes;
    }
}
function getExternalClasses(node, parentFile, babelParserPlugins) {
    // @ts-expect-error importSource 是编译时扩展的属性
    const importSource = node.importSource;
    if (importSource) {
        if (fs_1.default.existsSync(importSource)) {
            return (getComponentExternalClasses(importSource, parentFile, babelParserPlugins) || []);
        }
        // 尝试添加扩展名
        for (const ext of ['.uvue', '.vue']) {
            const fullPath = importSource + ext;
            if (fs_1.default.existsSync(fullPath)) {
                return (getComponentExternalClasses(fullPath, parentFile, babelParserPlugins) || []);
            }
        }
    }
    const tag = node.tag;
    const easycomSource = (0, uni_cli_shared_1.matchEasycom)(tag);
    if (easycomSource) {
        return (getComponentExternalClasses(easycomSource, parentFile, babelParserPlugins) || []);
    }
    const globalComponentSource = (0, uni_cli_shared_1.getGlobalComponentSource)(tag);
    if (globalComponentSource) {
        return (getComponentExternalClasses(globalComponentSource, parentFile, babelParserPlugins) || []);
    }
    return [];
}
function resolveSource(node) {
    // @ts-expect-error importSource 是编译时扩展的属性
    const importSource = node.importSource;
    if (importSource) {
        if (fs_1.default.existsSync(importSource)) {
            return importSource;
        }
        // 尝试添加扩展名
        for (const ext of ['.uvue', '.vue']) {
            const fullPath = importSource + ext;
            if (fs_1.default.existsSync(fullPath)) {
                return fullPath;
            }
        }
    }
    const tag = node.tag;
    const easycomSource = (0, uni_cli_shared_1.matchEasycom)(tag);
    if (easycomSource) {
        return easycomSource;
    }
    const globalComponentSource = (0, uni_cli_shared_1.getGlobalComponentSource)(tag);
    if (globalComponentSource) {
        return globalComponentSource;
    }
}
function checkComponentAppAndPageIsolation(source, context) {
    return checkRecursive(source, new Set(), context);
}
function checkRecursive(source, visited, context) {
    if (visited.has(source)) {
        return false;
    }
    visited.add(source);
    try {
        const code = fs_1.default.readFileSync(source, 'utf-8');
        if (code.includes('styleIsolation') && code.includes('app-and-page')) {
            return true;
        }
        const { descriptor } = (0, compiler_sfc_1.parse)(code, { filename: source });
        const template = descriptor.template?.content || '';
        const ast = (0, compiler_core_1.baseParse)(template);
        const nodeTags = new Set();
        const walk = (node) => {
            if (node.type === 1) {
                // Element
                nodeTags.add(node);
                node.children.forEach(walk);
            }
            else if (node.type === 11) {
                // For
                node.children.forEach(walk);
            }
            else if (node.type === 9) {
                // If
                node.branches.forEach(walk);
            }
        };
        ast.children.forEach(walk);
        for (const nodeTag of nodeTags) {
            let childSource;
            if ((0, uni_cli_shared_1.isUserComponent)(nodeTag, context)) {
                childSource = resolveSource(nodeTag);
            }
            if (childSource && fs_1.default.existsSync(childSource)) {
                if (checkRecursive(childSource, visited, context)) {
                    return true;
                }
            }
        }
    }
    catch (e) { }
    return false;
}
/**
 * 收集页面使用的 externalClasses 信息
 * @param filename 页面文件路径
 * @param node 组件节点
 * @param externalClasses 组件定义的 externalClasses 数组
 */
function collectPageExternalClasses(filename, node, externalClasses, hasAppAndPageStyle = false) {
    const staticClasses = [];
    let hasDynamic = false;
    for (const prop of node.props) {
        if ((0, uni_cli_shared_1.isAttributeNode)(prop)) {
            // 静态属性，如 my-class="foo"
            if (externalClasses.includes(prop.name) && prop.value?.content) {
                // 可能有多个 class，如 my-class="foo bar"
                const classes = prop.value.content.split(/\s+/).filter(Boolean);
                staticClasses.push(...classes);
            }
        }
        else if ((0, uni_cli_shared_1.isDirectiveNode)(prop) && prop.name === 'bind') {
            // 动态绑定，如 :my-class="bar"
            const { arg } = prop;
            if (arg && (0, uni_cli_shared_1.isSimpleExpressionNode)(arg) && arg.isStatic) {
                if (externalClasses.includes(arg.content)) {
                    hasDynamic = true;
                }
            }
        }
    }
    if (staticClasses.length > 0 || hasDynamic || hasAppAndPageStyle) {
        (0, uni_cli_shared_1.addPageExternalClasses)(filename, staticClasses, hasDynamic, hasAppAndPageStyle);
    }
}
