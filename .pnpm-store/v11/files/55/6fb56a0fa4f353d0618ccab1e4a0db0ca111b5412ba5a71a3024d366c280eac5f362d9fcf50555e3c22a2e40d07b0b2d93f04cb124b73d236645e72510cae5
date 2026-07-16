import { type ComponentNode, type DirectiveNode, type ElementNode } from '@vue/compiler-core';
import { type NodeTransform, type TransformContext } from '../transform';
export declare const transformComponent: NodeTransform;
/**
 * 重写组件 props 绑定
 * @param node
 * @param context
 * @param externalClasses 组件的 externalClasses 数组
 */
export declare function rewriteBinding({ tag, props }: ComponentNode, context: TransformContext, externalClasses?: string[]): void;
export declare function isPropsBinding({ arg }: DirectiveNode): boolean | undefined;
export declare function rewritePropsBinding(dir: DirectiveNode, node: ElementNode, context: TransformContext): void;
