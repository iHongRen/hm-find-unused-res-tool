# 鸿蒙无用资源清理工具

扫描 HarmonyOS 项目中未使用的资源，分析完成后弹出 GUI 面板，支持查看、定位、删除。

环境要求：Python 3.9+

## 用法

```bash
python3 find_unused_resources.py [项目根目录]
```

默认项目根目录为当前工作目录。

## 功能

- 扫描 `src/main/resources/base/media/` 目录下的所有资源
- 扫描 `src/main/resources/base/rawfile/` 目录下的所有资源
- 在源码中搜索 `$r('app.media.xxx')`、`$rawfile('xxx')`、`getRawFileContent('xxx')` 引用
- 追踪模板字符串中的动态引用（如 `$r('app.media.${iconName}')`）
- 追踪变量赋值，尝试解析动态引用的实际值
- 识别编译模板引用（如 `params: ['app.media.${var}']`）
- 识别前缀匹配（引用 `icon_` 前缀时，`icon_home`、`icon_1` 等视为可能被引用）
- 识别裸资源名引用（如 `'ic_plus_red'` 出现在代码中，参与"已使用"判断）
- 识别 JSON 配置文件中的模块引用（如 `"[reslib].media.xxx"`）
- 识别 rawfile 路径引用（如 `"rawfile/images/icon.png"`）
- 检测引用缺失（代码中引用了但资源不存在）

支持的资源类型：

- **图片**：png, jpg, jpeg, gif, svg, webp, bmp, ico
- **音频**：mp3, aac, wav, ogg, flac, m4a
- **视频**：mp4, avi, mkv, mov, wmv, flv, m4v, 3gp
- **字体**：ttf, otf
- **其他**：json, txt, pdf, docx, xlsx, pptx, zip

扫描的源码文件类型：

- **鸿蒙/TS**：ets, ts, js, mjs, cjs
- **配置文件**：json, json5, jsonc, xml, yaml, yml, toml, properties, ini, cfg, conf
- **样式文件**：css, less, scss, sass
- **文档/脚本**：html, htm, md, txt, sh, bat, ps1
- **其他代码**：java, kt, swift, dart, lua, py, rb, php, go, rs, c, cpp, h, hpp

## 分析分类

| 分类 | 说明 |
|------|------|
| rawfile 未使用 | 在 rawfile 目录中但未被 `$rawfile()` 引用 |
| media 未使用 | 在 media 目录中但未被 `$r('app.media.xxx')` 引用 |
| 前缀匹配 | 匹配模板引用前缀，可能被动态引用，需人工确认 |
| 引用缺失 | 代码中有引用但资源不存在 |

## GUI 面板

![](./screenshots/demo.gif)

分析完成后自动弹出 GUI 面板（终端显示加载动画）：

- 顶部统计卡片：资源数量、引用数量、可释放空间等（分类着色）
- 列表视图：按分类分组显示，交替行背景、hover 高亮
- 导出报告：标题栏"导出报告"按钮，生成包含统计概览和分类明细的 TXT 报告
- 操作方式：
  - 双击 → 在文件管理器中定位
  - 多选 → Cmd/Ctrl + 点击，支持批量删除
  - 右键菜单 → 打开定位 / 复制名称 / 删除文件
  - 键盘 → `Delete` 或 `⌫` 删除，`Return` 打开

## 示例

```bash
$ python3 find_unused_resources.py /your-project-root
正在分析: /path/to/project ...
分析完成，打开 GUI 面板
```

## 排除目录

默认排除以下目录 `EXCLUDE_DIRS `，不参与扫描：

- `oh_modules`
- `node_modules`
- `.hvigor`
- `build`
- `.preview`
- `AppScope`



# 作者 [@仙银](https://github.com/iHongRen)

鸿蒙开源作品，欢迎持续关注 [Star](https://github.com/iHongRen/https://github.com/iHongRen/) ，[赞助](https://ihongren.github.io/donate.html)

1、[hpack](https://github.com/iHongRen/hpack) - 鸿蒙 HarmonyOS 一键打包上传分发测试工具

2、[Open-in-DevEco-Studio](https://github.com/iHongRen/Open-in-DevEco-Studio)  - macOS  Finder 工具栏 app，使用 DevEco-Studio 打开鸿蒙工程

3、[cxy-theme](https://github.com/iHongRen/cxy-theme) - DevEco-Studio 绿色护眼背景主题

4、[harmony-udid-tool](https://github.com/iHongRen/harmony-udid-tool) - 简单易用的 HarmonyOS 设备 UDID 获取工具，适用于非开发人员

5、[SandboxFinder](https://github.com/iHongRen/SandboxFinder) - 鸿蒙沙箱文件浏览器，支持模拟器和真机

6、[WebServer](https://github.com/iHongRen/WebServer) - 鸿蒙轻量级Web服务器框架，类 Express.js API 风格

7、[SelectableMenu](https://github.com/iHongRen/SelectableMenu) - 适用于聊天对话框中的文本选择菜单

8、[RefreshList](https://github.com/iHongRen/RefreshList) - 功能完善的上拉下拉加载组件，支持各种自定义

9、[hm-app-check-tool](https://github.com/iHongRen/hm-app-check-tool) - macOS 鸿蒙扫描工具，扫描HAP、HSP、App包内容并输出检测结果报告

10、[hm-find-unused-res-tool](https://github.com/iHongRen/hm-find-unused-res-tool) - 鸿蒙无用资源清理工具，一个有UI的 Python 脚本