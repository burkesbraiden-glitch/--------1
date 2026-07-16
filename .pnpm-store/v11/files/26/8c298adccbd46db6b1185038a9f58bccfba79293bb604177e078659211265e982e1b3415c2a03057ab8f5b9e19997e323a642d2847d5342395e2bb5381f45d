export interface VueCodePosition {
    line: number;
    column: number;
}
export interface VueCodeEditRange {
    start: VueCodePosition;
    end: VueCodePosition;
    /**
     * 调用方替换时建议只移除非换行字符，用于尽量保持错误定位和调试行号不变。
     */
    preserveLineBreaks: true;
    /**
     * 开始范围包含首个子节点前的缩进，调用方需要保留这段缩进，避免改变子节点格式。
     */
    preserveEndIndent?: true;
}
export type VueCodeEditRangesResult = Record<string, VueCodeEditRange[]>;
/**
 * 批量定位由 `#ifdef APP` 包裹的根 scroll-view 需要移除的范围。
 * 只返回需要修改的行列号，不修改文件，也不返回修改后的文件内容。
 */
export declare function resolveAppRootScrollViewEditRanges(vueFiles: string[], inputDir: string): VueCodeEditRangesResult;
/**
 * 蒸汽模式下，页面根节点会自动补一个 scroll-view。
 * 这里仅用正则做精确匹配：命中范围宁可保守，也不能误报。
 */
export declare function hasAppRootScrollViewWrappedByIfdef(code: string): boolean;
/**
 * 仅在 dom2 页面整文件预处理时定位需要提示优化建议的根 scroll-view 节点。
 */
export declare function resolveDom2RootScrollViewWarnLocation(code: string, filename: string, isVueSubRequest: boolean): {
    loc: import("@vue/compiler-core").SourceLocation | {
        start: {
            line: number;
            column: number;
            offset: number;
        };
        end: {
            line: number;
            column: number;
            offset: number;
        };
    };
    source: string;
} | undefined;
export declare function warnDom2RootScrollView(code: string, filename: string, isVueSubRequest: boolean): void;
export declare function resolveAppRootScrollViewEditRangesByCode(code: string, filename: string): VueCodeEditRange[];
