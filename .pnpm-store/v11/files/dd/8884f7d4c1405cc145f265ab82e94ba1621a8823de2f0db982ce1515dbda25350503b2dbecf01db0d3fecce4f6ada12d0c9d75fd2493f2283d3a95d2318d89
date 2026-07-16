"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.uniAppXIOSEngineDevPlugin = void 0;
const uni_cli_shared_1 = require("@dcloudio/uni-cli-shared");
function uniAppXIOSEngineDevPlugin() {
    const { getSwiftCompilerServer } = (0, uni_cli_shared_1.resolveUTSCompiler)();
    const compilerServer = getSwiftCompilerServer();
    if (!compilerServer) {
        console.error(`项目使用了uts插件，正在安装 uts iOS 运行扩展...`);
        process.exit(0);
    }
    if (compilerServer.checkEnv) {
        const { code, msg } = compilerServer.checkEnv();
        if (code) {
            console.error(msg);
        }
    }
    const appId = (0, uni_cli_shared_1.parseManifestJsonOnce)(process.env.UNI_INPUT_DIR).appid || uni_cli_shared_1.DEFAULT_APPID;
    return {
        name: 'uni:app-x-ios-dev',
        async writeBundle() {
            if (!compilerServer) {
                return;
            }
            if (process.env.UNI_APP_X_DOM2_CPP_CHANGED === 'true') {
                const res = await compilerServer.compileCpp({
                    appId,
                    projectPath: process.env.UNI_INPUT_DIR,
                    cppPath: process.env.UNI_APP_X_DOM2_CPP_DIR,
                });
                if (res.code) {
                    throw new Error(res.msg);
                }
            }
        },
    };
}
exports.uniAppXIOSEngineDevPlugin = uniAppXIOSEngineDevPlugin;
