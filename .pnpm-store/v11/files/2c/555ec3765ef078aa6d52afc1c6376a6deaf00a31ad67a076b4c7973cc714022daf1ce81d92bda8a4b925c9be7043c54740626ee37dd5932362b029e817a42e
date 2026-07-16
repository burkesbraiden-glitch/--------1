"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.createCopyComponentDirs = exports.isMiniProgramAssetFile = void 0;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const utils_1 = require("../vite/plugins/vitejs/utils");
const json_1 = require("../json");
const EXTNAMES = [
    '.png',
    '.jpg',
    '.jpeg',
    '.gif',
    '.svg',
    '.json',
    '.cer',
    '.mp3',
    '.aac',
    '.m4a',
    '.mp4',
    '.wav',
    '.ogg',
    '.silk',
    '.wasm',
    '.br',
    '.cert',
];
function isMiniProgramAssetFile(filename) {
    if (!path_1.default.isAbsolute(filename)) {
        return false;
    }
    return EXTNAMES.includes(path_1.default.extname(filename));
}
exports.isMiniProgramAssetFile = isMiniProgramAssetFile;
function createCopyComponentDirs(dir) {
    const dirs = [dir];
    const uniModulesDir = 'uni_modules/*/' + dir + '/**/*';
    dirs.push(uniModulesDir);
    const inputDir = process.env.UNI_INPUT_DIR;
    const platform = process.env.UNI_PLATFORM;
    if (!inputDir || !platform) {
        return dirs;
    }
    const pagesJsonFile = path_1.default.resolve((0, utils_1.normalizePath)(inputDir), 'pages.json');
    if (!fs_1.default.existsSync(pagesJsonFile)) {
        return dirs;
    }
    const { appJson } = (0, json_1.parseMiniProgramPagesJson)(fs_1.default.readFileSync(pagesJsonFile, 'utf8'), platform, { subpackages: true });
    const roots = Object.values(appJson.subPackages || appJson.subpackages || {})
        .map(({ root }) => root)
        .filter(Boolean);
    roots.forEach((root) => {
        dirs.push((0, utils_1.normalizePath)(path_1.default.join(root, dir)), (0, utils_1.normalizePath)(path_1.default.join(root, uniModulesDir)));
    });
    return dirs;
}
exports.createCopyComponentDirs = createCopyComponentDirs;
