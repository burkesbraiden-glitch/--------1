"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveDistDir = exports.resolveVueDistDir = exports.resolveFrameworkDistDir = void 0;
function resolveFrameworkDistDir() {
    return resolveDistDir();
}
exports.resolveFrameworkDistDir = resolveFrameworkDistDir;
function resolveVueDistDir() {
    return resolveDistDir();
}
exports.resolveVueDistDir = resolveVueDistDir;
function resolveDistDir() {
    // // 重要：目前只要manifest.json中配置了vapor:true，就认为是vapor版本（虽然还没有支持）
    // process.env.UNI_APP_X_VAPOR === 'true'
    //   ? 'dist-x-vapor'
    //   :
    return process.env.UNI_APP_X === 'true' ? 'dist-x' : 'dist';
}
exports.resolveDistDir = resolveDistDir;
