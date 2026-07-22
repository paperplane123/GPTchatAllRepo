import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(scriptDir, "..");
const pluginName = "WPS_MAC_READER";
const pluginVersion = "0.2.0";
const pluginFolder = `${pluginName}_${pluginVersion}`;
const pluginRoot = join(projectRoot, "package", pluginFolder);

const requiredFiles = [
  "README.md",
  "install.sh",
  "uninstall.sh",
  "package.json",
  "package/publish.xml",
  `package/${pluginFolder}/ribbon.xml`,
  `package/${pluginFolder}/main.js`
];

const failures = [];

function fail(message) {
  failures.push(message);
}

function read(relativePath) {
  const path = join(projectRoot, relativePath);
  if (!existsSync(path)) {
    fail(`缺少文件：${relativePath}`);
    return "";
  }
  return readFileSync(path, "utf8");
}

for (const relativePath of requiredFiles) {
  if (!existsSync(join(projectRoot, relativePath))) {
    fail(`缺少文件：${relativePath}`);
  }
}

if (existsSync(join(pluginRoot, "index.html"))) {
  fail("插件目录不应包含 index.html；WPS 会自动生成并加载 main.js。")
}

const publishXml = read("package/publish.xml");
const ribbonXml = read(`package/${pluginFolder}/ribbon.xml`);
const mainJs = read(`package/${pluginFolder}/main.js`);
const installSh = read("install.sh");

const expectedManifestFragments = [
  `name="${pluginName}"`,
  `version="${pluginVersion}"`,
  'type="wps"',
  'url="file://"',
  'install="null"'
];
for (const fragment of expectedManifestFragments) {
  if (!publishXml.includes(fragment)) {
    fail(`publish.xml 缺少：${fragment}`);
  }
}

if (!publishXml.includes("<jsplugins>") || !publishXml.includes("</jsplugins>")) {
  fail("publish.xml 缺少 jsplugins 根节点。")
}

for (const nativeCommand of ["ViewFullScreenReadingView", "ViewPrintLayoutView"]) {
  if (!ribbonXml.includes(`idMso="${nativeCommand}"`)) {
    fail(`ribbon.xml 缺少不依赖 JavaScript 的原生命令：${nativeCommand}`);
  }
}

for (const callbackName of ["EnterStrictReadOnlyMode", "ExitStrictReadOnlyMode", "ReapplyReadOnlyLock"]) {
  if (!ribbonXml.includes(`onAction="${callbackName}"`)) {
    fail(`ribbon.xml 缺少回调：${callbackName}`);
  }
  const functionPattern = new RegExp(`function\\s+${callbackName}\\s*\\(`);
  if (!functionPattern.test(mainJs)) {
    fail(`main.js 未实现回调：${callbackName}`);
  }
}

if (!mainJs.includes("ReadingLayoutAllowEditing = false")) {
  fail("main.js 未显式禁止阅读版式编辑。")
}

if (!mainJs.includes("wps.Application")) {
  fail("main.js 未兼容部分 Mac 构建使用 wps.Application 的情况。")
}

if (/\bwindow\s*\./.test(mainJs)) {
  fail("main.js 不应依赖 window；Mac 隐藏加载上下文可能不提供标准 window。")
}

if (!installSh.includes(`PLUGIN_VERSION="${pluginVersion}"`)) {
  fail(`install.sh 未使用版本 ${pluginVersion}。`)
}

if (!installSh.includes('"${ADDON_ROOT}/${PLUGIN_NAME}_"*')) {
  fail("install.sh 未清理旧版本插件目录。")
}

function run(command, args, description) {
  const result = spawnSync(command, args, {
    cwd: projectRoot,
    encoding: "utf8"
  });
  if (result.status !== 0) {
    fail(`${description}失败：${(result.stderr || result.stdout || "未知错误").trim()}`);
  }
}

run(process.execPath, ["--check", join(pluginRoot, "main.js")], "main.js 语法校验");
run("bash", ["-n", join(projectRoot, "install.sh")], "install.sh 语法校验");
run("bash", ["-n", join(projectRoot, "uninstall.sh")], "uninstall.sh 语法校验");

if (failures.length > 0) {
  console.error("WPS Mac 严格只读阅读加载项校验失败：");
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log("WPS Mac 严格只读阅读加载项静态校验通过。")
