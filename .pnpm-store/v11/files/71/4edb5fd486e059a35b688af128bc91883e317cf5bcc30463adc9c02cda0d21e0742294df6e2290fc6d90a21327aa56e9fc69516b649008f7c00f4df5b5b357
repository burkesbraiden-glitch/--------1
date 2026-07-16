"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.uniAppManifestPlugin = exports.getOutputManifestJson = void 0;
const path_1 = __importDefault(require("path"));
const fs_extra_1 = __importDefault(require("fs-extra"));
const uni_cli_shared_1 = require("@dcloudio/uni-cli-shared");
const utils_1 = require("../utils");
const utils_2 = require("../android-dom2/utils");
let outputManifestJson = undefined;
const isXHarmony = process.env.UNI_APP_X === 'true' &&
    process.env.UNI_UTS_PLATFORM === 'app-harmony';
function getOutputManifestJson() {
    return outputManifestJson;
}
exports.getOutputManifestJson = getOutputManifestJson;
function uniAppManifestPlugin(platform) {
    const manifestJsonPath = path_1.default.resolve(process.env.UNI_INPUT_DIR, 'manifest.json');
    const manifestJsonUTSPath = path_1.default.resolve(process.env.UNI_INPUT_DIR, uni_cli_shared_1.MANIFEST_JSON_UTS);
    const isDom2Dynamic = process.env.UNI_APP_X_DOM2_DYNAMIC === 'true';
    let manifestJson = {};
    let kotlinCode = '';
    return {
        name: 'uni:app-manifest',
        apply: 'build',
        resolveId(id) {
            if ((0, utils_1.isManifest)(id)) {
                return manifestJsonUTSPath;
            }
        },
        load(id) {
            if ((0, utils_1.isManifest)(id)) {
                return fs_extra_1.default.readFileSync(manifestJsonPath, 'utf8');
            }
        },
        transform(code, id) {
            if ((0, utils_1.isManifest)(id)) {
                this.addWatchFile(path_1.default.resolve(process.env.UNI_INPUT_DIR, 'manifest.json'));
                manifestJson = (0, uni_cli_shared_1.parseJson)(code, false, id);
                return {
                    code: `export default ${JSON.stringify(manifestJson)}`,
                    map: {
                        mappings: '',
                    },
                };
            }
        },
        writeBundle() {
            if ((0, uni_cli_shared_1.isUniAppXAndroidJsEngine)() &&
                process.env.UNI_APP_X_DOM2_KT_DIR &&
                !isDom2Dynamic) {
                const newKotlinCode = (0, utils_2.genUniAppXJsEngineIndexKotlinCode)(manifestJson);
                if (kotlinCode !== newKotlinCode) {
                    fs_extra_1.default.outputFileSync((0, utils_2.resolveUniAppXJsEngineIndexKotlinPath)(), newKotlinCode);
                    kotlinCode = newKotlinCode;
                    process.env.UNI_APP_X_DOM2_KT_CHANGED = 'true';
                }
            }
        },
        buildEnd() {
            outputManifestJson = (0, utils_1.normalizeManifestJson)(platform, manifestJson);
            const manifest = outputManifestJson;
            const hasAppDefaultAppTheme = (0, uni_cli_shared_1.validateThemeValue)(manifestJson.app?.defaultAppTheme);
            if (hasAppDefaultAppTheme) {
                const selectedTheme = manifestJson.app.defaultAppTheme;
                outputManifestJson.app = outputManifestJson.app || {};
                outputManifestJson.app.defaultAppTheme = selectedTheme;
            }
            if (process.env.NODE_ENV !== 'development' || isXHarmony) {
                // 生产模式，记录使用到的modules
                const ids = Array.from(this.getModuleIds());
                const uniExtApis = new Set();
                ids.forEach((id) => {
                    const moduleInfo = this.getModuleInfo(id);
                    if (moduleInfo &&
                        moduleInfo.meta &&
                        Array.isArray(moduleInfo.meta.uniExtApis)) {
                        moduleInfo.meta.uniExtApis.forEach((api) => {
                            uniExtApis.add(api);
                        });
                    }
                });
                const { parseInjectModules, getPluginInjectApis, getPluginInjectComponents, } = (0, uni_cli_shared_1.resolveUTSCompiler)();
                const extApiComponents = (0, utils_1.getExtApiComponents)();
                // uts 插件里使用的 ext api 和组件
                const pluginInjectApis = getPluginInjectApis();
                const pluginInjectComponents = getPluginInjectComponents();
                if (uniExtApis.size ||
                    extApiComponents.size ||
                    pluginInjectApis.length ||
                    pluginInjectComponents.length) {
                    const modules = parseInjectModules([...uniExtApis, ...pluginInjectApis], {}, [...extApiComponents, ...pluginInjectComponents]);
                    if (modules.length) {
                        // 执行了摇树逻辑，就需要设置 modules 节点
                        if (isXHarmony) {
                            (0, utils_1.updateHarmonyManifestModules)(manifest, modules);
                        }
                        else {
                            (0, utils_1.updateManifestModules)(platform, manifest, modules);
                        }
                    }
                }
            }
            // TODO 目前android即使配置了vapor也不使用，后续支持后，需要移除下边的代码
            if (process.env.UNI_APP_X_DOM2 !== 'true') {
                delete manifest['uni-app-x']?.vapor;
            }
            fs_extra_1.default.outputFileSync(path_1.default.resolve(process.env.UNI_OUTPUT_DIR, 'manifest.json'), JSON.stringify(manifest, null, 2));
        },
    };
}
exports.uniAppManifestPlugin = uniAppManifestPlugin;
