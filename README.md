# 鸿蒙无用资源清理工具

扫描 HarmonyOS 项目中未使用的资源，分析完成后弹出 GUI 面板，支持查看、定位、删除。

环境要求：Python9+

## 用法

```bash
python3 find_unused_resources.py [项目根目录]
```

默认项目根目录为当前工作目录。

## 功能

- 扫描 `src/main/resources/base/media/` 目录下的所有资源
- 扫描 `src/main/resources/base/rawfile/` 目录下的所有资源
- 在 `.ets` / `.ts` 源码中搜索 `$r('app.media.xxx')` 和 `$rawfile('xxx')` 引用
- 追踪模板字符串中的动态引用（如 `$r('app.media.${iconName}')`）
- 识别前缀匹配（引用 `icon_` 前缀时，`icon_home`、`icon_1` 等视为可能被引用）
- 检测引用缺失（代码中引用了但资源不存在）

支持的资源类型：

- **图片**：png, jpg, jpeg, gif, svg, webp, bmp, ico
- **音频**：mp3, aac, wav, ogg, flac, m4a
- **视频**：mp4, avi, mkv, mov, wmv, flv, m4v, 3gp
- **字体**：ttf, otf
- **其他**：json, txt, pdf, docx, xlsx, pptx, zip

## 分析分类

| 分类 | 说明 |
|------|------|
| rawfile 未使用 | 在 rawfile 目录中但未被 `$rawfile()` 引用 |
| media 未使用 | 在 media 目录中但未被 `$r('app.media.xxx')` 引用 |
| 前缀匹配 | 匹配模板引用前缀，可能被动态引用，需人工确认 |
| 引用缺失 | 代码中有引用但资源不存在 |

## GUI 面板

![](./screenshots/demo.gif)

分析完成后自动弹出 GUI 面板：

- 顶部统计卡片：资源数量、引用数量、可释放空间等
- 列表视图：分类显示未使用资源，交替行背景、hover 高亮
- 操作方式：
  - 双击 → 在文件管理器中定位
  - 右键菜单 → 打开定位 / 复制名称 / 删除文件
  - 键盘 → `Delete` 或 `⌫` 删除，`Return` 打开

## 示例

```bash
$ python3 find_unused_resources.py /your-project-root
正在分析: /path/to/project ...
分析完成，打开 GUI 面板
```

## 排除目录

默认排除以下目录，不参与扫描：

- `oh_modules`
- `node_modules`
- `.hvigor`
- `build`
- `.preview`
