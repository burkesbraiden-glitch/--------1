"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.initUniAppXHarmonyPlugin = exports.initUniAppJsEngineDom1CssPlugin = exports.transformExtApiVueFile = exports.transformVue = exports.genClassName = void 0;
const plugins_1 = require("./plugins");
exports.default = () => {
    if (process.env.UNI_UTS_PLATFORM === 'app-android' &&
        process.env.UNI_APP_X_DOM2 === 'true') {
        return (0, plugins_1.initAndroidDom2)();
    }
    return process.env.UNI_UTS_PLATFORM === 'app-android'
        ? (0, plugins_1.initAndroid)()
        : process.env.UNI_UTS_PLATFORM === 'app-ios'
            ? (0, plugins_1.initIOS)()
            : [];
};
var uni_cli_shared_1 = require("@dcloudio/uni-cli-shared");
Object.defineProperty(exports, "genClassName", { enumerable: true, get: function () { return uni_cli_shared_1.genUTSClassName; } });
// transformVue 被内部仓库 vuejs-core 使用，编译android框架内置组件了
var main_1 = require("./plugins/android/uvue/sfc/main");
Object.defineProperty(exports, "transformVue", { enumerable: true, get: function () { return main_1.transformMain; } });
var extApiComponents_1 = require("./extApiComponents");
Object.defineProperty(exports, "transformExtApiVueFile", { enumerable: true, get: function () { return extApiComponents_1.transformExtApiVueFile; } });
var plugin_1 = require("./plugins/js/plugin");
Object.defineProperty(exports, "initUniAppJsEngineDom1CssPlugin", { enumerable: true, get: function () { return plugin_1.initUniAppJsEngineDom1CssPlugin; } });
var harmony_1 = require("./plugins/harmony");
Object.defineProperty(exports, "initUniAppXHarmonyPlugin", { enumerable: true, get: function () { return harmony_1.init; } });
