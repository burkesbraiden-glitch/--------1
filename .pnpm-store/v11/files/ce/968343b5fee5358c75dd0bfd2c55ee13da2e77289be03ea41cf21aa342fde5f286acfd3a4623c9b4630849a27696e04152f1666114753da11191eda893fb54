import type { PluginCreator } from 'postcss';
/**
 * 基于页面 externalClasses 使用情况提升页面样式优先级
 *
 * 小程序平台（mp-*）：
 *   - 页面没有使用 externalClasses：不做转换
 *   - 页面存在动态 externalClasses：选择器最后一个 class 追加 [class]
 *     .a -> .a[class]
 *   - 页面只有静态 externalClasses：仅命中静态 class 的选择器追加 [class]
 *     .foo -> .foo[class]（foo 在 staticClasses 中）
 *     .bar -> .bar（bar 不在 staticClasses 中）
 *
 * 追加 [class] 可以提升 class 选择器优先级，同时避免原先插入 page 带来的结构影响。
 */
declare const externalPlugin: PluginCreator<void>;
export default externalPlugin;
