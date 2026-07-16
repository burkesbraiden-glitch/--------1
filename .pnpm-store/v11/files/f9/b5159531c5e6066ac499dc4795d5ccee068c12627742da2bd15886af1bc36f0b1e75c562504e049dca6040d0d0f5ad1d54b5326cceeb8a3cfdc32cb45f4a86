import { type Program } from '@babel/types';
import type { SFCStyleBlock } from '@vue/compiler-sfc';
/**
 * 页面使用的 externalClasses 信息
 * - staticClasses: 静态绑定的 class 值集合，如 my-class="foo" 中的 "foo"
 * - hasDynamic: 是否存在动态绑定，如 :my-class="bar"
 * - hasAppAndPageStyle: 是否存在 styleIsolation: 'app-and-page'
 */
export interface PageExternalClassesInfo {
    staticClasses: Set<string>;
    hasDynamic: boolean;
    hasAppAndPageStyle?: boolean;
}
export type StyleIsolation = 'isolated' | 'app' | 'app-and-page';
export declare function findPageExternalClasses(filename: string): PageExternalClassesInfo | undefined;
export declare function updatePageExternalClasses(filename: string, info: PageExternalClassesInfo): void;
export declare function addPageExternalClasses(filename: string, staticClasses: string[], hasDynamic: boolean, hasAppAndPageStyle?: boolean): void;
export declare function clearPageExternalClasses(filename: string): void;
export declare function hasExternalClasses(code: string): boolean;
export declare function findMiniProgramComponentExternalClasses(filename: string): {
    mtime: number;
    classes: string[];
} | undefined;
export declare function updateMiniProgramComponentExternalClasses(filename: string, value: {
    mtime: number;
    classes: string[];
}): void;
export declare function parseExternalClasses(ast: Program): string[];
export declare function parseStyleIsolation(ast: Program): StyleIsolation | '';
/**
 * 目前只有小程序平台才会走这个逻辑
 * @param pagePahth
 * @param value
 * @param isPage
 */
export declare function updateMiniProgramComponentStyleIsolation(pagePahth: string, value: StyleIsolation, isPage?: boolean): void;
export declare function findMiniProgramComponentStyleIsolation(pagePahth: string): {
    styleIsolation: StyleIsolation;
    isPage: boolean;
} | undefined;
export declare function createDefaultSFCStyleBlock(source: string): SFCStyleBlock;
