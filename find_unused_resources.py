#!/usr/bin/env python3
"""分析 HarmonyOS 项目中未使用的资源。

资源存储在 src/main/resources/base/media/ 目录，
通过 $r('app.media.xxx') 、 $rawfile('xxx') 、 getRawFileContent('xxx') 方式引用。

用法:
    python3 find_unused_resources.py [项目根目录]

默认项目根目录为当前工作目录。
分析完成后会弹出 GUI 面板，支持查看、定位、删除资源。
"""

import base64
import itertools
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

# ─── 常量 ───
RESOURCE_EXTENSIONS = {
    # 图片
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico',
    # 音频
    '.mp3', '.aac', '.wav', '.ogg', '.flac', '.m4a',
    # 视频
    '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.m4v', '.3gp',
    # 字体
    '.ttf', '.otf',
    # 其他
    '.json', '.txt', '.pdf', '.docx', '.xlsx', '.pptx', '.zip',
}
SOURCE_EXTENSIONS = {
    # 鸿蒙/TS
    '.ets', '.ts', '.js', '.mjs', '.cjs',
    # 配置
    '.json', '.json5', '.jsonc',
    '.xml', '.yaml', '.yml', '.toml',
    '.properties', '.ini', '.cfg', '.conf',
    # 样式
    '.css', '.less', '.scss', '.sass',
    # 文档/脚本
    '.html', '.htm', '.md', '.txt',
    '.sh', '.bat', '.ps1',
    # 其他代码
    '.java', '.kt', '.swift', '.dart', '.lua',
    '.py', '.rb', '.php', '.go', '.rs', '.c', '.cpp', '.h', '.hpp',
}

# ─── 忽略目录 ───扫描时会跳过这些目录，避免误删第三方库或构建产物中的资源
EXCLUDE_DIRS = {'oh_modules', 'node_modules', '.hvigor', 'build', '.preview', 'AppScope'}

# ─── 字体 ───
MONO_FONT = 'Consolas' if sys.platform == 'win32' else 'Menlo'

# ─── 主题颜色 ───
C_BG = '#f5f5f5'
C_CARD_BG = '#ffffff'
C_ACCENT_RED = '#e05555'
C_ACCENT_ORANGE = '#e09040'
C_ACCENT_BLUE = '#4a90d9'
C_ACCENT_GREEN = '#4caf84'
C_TEXT = '#2c2c2c'
C_TEXT_SEC = '#888888'
C_BORDER = '#e0e0e0'
C_ROW_HOVER = '#f0f4ff'
C_ROW_DELETED = '#cccccc'
C_ROW_EVEN = '#ffffff'
C_ROW_ODD = '#f5f7fa'

CAT_COLORS = {
    'rawfile未使用': ('#ffe8e8', '#c0392b', 'rawfile 未使用'),
    'media未使用': ('#fff0f0', '#d44545', 'media 未使用'),
    '前缀匹配': ('#fffbe6', '#c0820a', '前缀匹配 · 可能被模板引用'),
    '引用缺失': ('#eaf4ff', '#2e6aab', '引用缺失 · 文件不存在'),
}

# ─── 内嵌图标（PNG，128x128）───
ICON_DATA = 'iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAAE/0lEQVR4nO2dzXHUMBiGP+9QCamB4cKFCyVACkgDDKdUwCmTBihgNyVw4cKFSQ1JK+HAaPE6/pH0/cp6nwszZLEVvY8+SbbXDGTIy5e3L5bna5nh9DyYnEfz4AhcDi0hxA+K0PWRlEHsQAjeHgkR2AdA8P5wRDhwTozwY8DJococBB+X0mpQXAEQfmxK8ykSAOG3QUlO2QIg/LbIzStLAITfJjm5bQqA8NtmK79VARD+PljLcVEAhL8vlvJkXQgC7TMrAEb/PpnL9ZUACH/fTPPFFNA5FwJg9PfBOGdUgM45C4DR3xcpb1SAzoEAnTMQofz3DCpA50CAzoEAnXPA/N83b7wbcMHxybsFdlxfebeAiIiGEBWgp+CnOIsQqwL8+eXdAjvef/RuARFFWASm0d9T+ET/f1/n6ucvAHAFAnQOBOgcCNA5sXYBe2BudR94gYsKIMnS1i7Ilm8OCCDFVshBJYAAEuSGG1ACCMClNNRgEkCAzoEAnQMBOgcCcLm79W4BCwjA4ffPf3+WSBDsohAEkCJHgmDhE0GAetLoH7MmQcDwiSBAHXPhJ+YkCBo+EW4G6XB3S/Thk3crsrAXoPUHQNdG//RzuRKkPnF4QNR2Cugl/NrPH5/M+8hOAK1frLSTralpn6EENgJoh28hAeccgSXQF8DKZk0JJI4dVIJ2t4FzHYrpoJh2BVhi2sn3N7LH4xJM0jYF2OrE9PMUfq0EWmEFkqBNAXKYhn5/w68GkgSRoD0Bcjru8WH5Z7kSBAlIm7YE4Iaf2KoGnYRP1JoAW+SEPybSlOBEOzeDtkZlafiJJMHXH3nnkeDc1u/659pgHxWgNvwx9zfG4cegDQHWgpHs0McH3YCChU/UigBLaHWo9HG1xWIQX4Cl0a/doVKhBQ0+EVsAr/ClzhU8fKKWdgEJj05N53z3uezzDRC3AsyNfu+OzTm/dxsLiSvAlCgdu7Y2iNLGAmIKMB39ETt23KbAq/wt4q8BInds5LZlEq8CjEf/Djo4OrEEQPjmxBIggfDNiCNAGv0I35Q4AhAhfAfiCPDN/964KY7fBxwTaxvY+ncHG8RfgPEI6FEA59/ZX4AeQw+EvwC9kTPnTwfF8UltraD/v4ZhhPPCm/afsAhxdgF75PqKH9j0GMIDCgJoIV2ylSSAABpo7e0VJIAA0mhf2BGWAAJIYnVVT1ACCCCF9SVdIQkggAQ14Y9fCVf7ejgB6SAAl9rwS/4+5/yVVQACdA4E4OB8K/cMowpAgM7RFyDKKAGzoALUEk3symnARoBonQXO2FUASBAS2ykAEoTDfg0gcY8ciOH3SFirEuzsCafDcHoevBsB/MA2sHMgQOdAgFKYd9/UqPyq2YGICOsAY5ZCMl4YD6fnAV8M8WIctuOOCFNADdGmAcY3jc8CYBroi5Q3KkAtElUgPQvIPca4PYVcCIAqUElNgHNfALU4L13mjArAofbRbImHQsefZSwiXwmAKlCIxwsuGOFP852tAJCgEEsJBMMnwhQgR4kEtReChMr+mEUBUAUq4EigHP5Snpshq79BZI9IvtVD4FhrgzlrlEOCSuaqQM07gnL/3QxblTy7zEMCBpyFIaN65EzjRfM8JBAgRwaBBV7uGq54oQcJ4lOygC/eBmJ3EJvSfFhhohrEoXZgsi4EoRrEgJODWICoBvZIDEDxEQwR9JGsvKolHDLIoTXd/gVYRM4zNYdp+QAAAABJRU5ErkJggg=='

# ─── 预编译正则（固定模式，只编译一次）───
_RE_STATIC = re.compile(r'\$r\(\s*[\'"]app\.media\.(\w+)[\'"]\s*\)')
_RE_TEMPLATE = re.compile(r'\$r\(\s*[`\'"]app\.media\.([^`\'"]*)\$\{[^}]+\}([^`\'"]*)[`\'"]?\s*\)')
_RE_COMPILED_TEMPLATE = re.compile(r'params:\s*\[`app\.media\.([^`]*)\$\{[^}]+\}([^`]*)`\]')
_RE_COMPILED_STATIC = re.compile(r'params:\s*\[[\'"]app\.media\.(\w+)[\'"]\]')
_RE_TERNARY = re.compile(r'[\'"]app\.media\.(\w+)[\'"]')
_RE_BARE_STR = re.compile(r'[\'"]app\.media\.([\w]+)[\'"]')
_RE_BARE_RES_NAME = re.compile(r'[\'"](\w+_\w+)[\'"]')
_RE_MODULE_MEDIA = re.compile(r'["\']\[[\w]+\]\.media\.(\w+)["\']')
_RE_RAWFILE = re.compile(r'\$rawfile\(\s*[\'"]([^\'"]+)[\'"]\s*\)')
_RE_GET_RAWFILE = re.compile(r'getRawFileContent\(\s*[\'"]([^\'"]+)[\'"]')
_RE_RAWFILE_PATH = re.compile(r'["\']rawfile/([^"\']+)["\']')
_RE_VAR_IN_TEMPLATE = re.compile(r'\$\{(\w+)')


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f'{size_bytes}B'
    elif size_bytes < 1024 * 1024:
        return f'{size_bytes / 1024:.1f}KB'
    else:
        return f'{size_bytes / (1024 * 1024):.1f}MB'


# ═══════════════════════════════════════════════
# 扫描逻辑（不变）
# ═══════════════════════════════════════════════


def trace_variable_values(content: str, var_name: str) -> set[str]:
    values = set()
    assign_pattern = re.compile(rf'{var_name}\s*(?:=\s*|:\s*\w*\s*=\s*)[\'"]([\w]+)[\'"]')
    for match in assign_pattern.finditer(content):
        values.add(match.group(1))
    prop_pattern = re.compile(rf'@\w+\s+{var_name}\s*:\s*\w+\s*=\s*[\'"]([\w]+)[\'"]')
    for match in prop_pattern.finditer(content):
        values.add(match.group(1))
    builder_def_pattern = re.compile(rf'@Builder\s+\w+\s*\([^)]*{var_name}\s*:\s*string[^)]*\)')
    builder_match = builder_def_pattern.search(content)
    if builder_match:
        builder_name_match = re.search(r'@Builder\s+(\w+)', builder_match.group(0))
        if builder_name_match:
            builder_name = builder_name_match.group(1)
            params_str = builder_match.group(0)
            all_params = re.findall(r'(\w+)\s*:\s*string', params_str)
            param_index = all_params.index(var_name) if var_name in all_params else -1
            if param_index >= 0:
                call_pattern = re.compile(rf'{builder_name}\s*\(([^)]+)\)')
                for call_match in call_pattern.finditer(content):
                    args_str = call_match.group(1)
                    string_args = re.findall(r'[\'"](\w+)[\'"]', args_str)
                    if param_index < len(string_args):
                        values.add(string_args[param_index])
                    values.update(string_args)
    map_pattern = re.compile(rf'{var_name}\s*:\s*[\'"](\w+)[\'"]')
    for match in map_pattern.finditer(content):
        values.add(match.group(1))
    call_arg_pattern = re.compile(r'[\'"]([a-zA-Z_]\w*)[\'"]\s*,\s*[\'"]([a-zA-Z_]\w*)[\'"]')
    for match in call_arg_pattern.finditer(content):
        values.add(match.group(1))
        values.add(match.group(2))
    valid_values = set()
    for v in values:
        if re.match(r'^[a-zA-Z_]\w*$', v) and not re.match(r'^[A-Z]', v):
            valid_values.add(v)
    return valid_values


def extract_refs_from_file(filepath: Path, root_dir: Path = None,
                           rawfile_name_re: 're.Pattern | None' = None) -> dict:
    static_refs = set()
    prefix_refs = set()
    traced_refs = set()
    rawfile_refs = set()
    bare_refs = set()
    dynamic_contexts = []
    display_path = filepath.relative_to(root_dir) if root_dir else filepath
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return {'static_refs': static_refs, 'prefix_refs': prefix_refs,
                'traced_refs': traced_refs, 'rawfile_refs': rawfile_refs,
                'bare_refs': bare_refs, 'dynamic_contexts': dynamic_contexts}
    lines = content.split('\n')

    for match in _RE_STATIC.finditer(content):
        static_refs.add(match.group(1))

    for match in _RE_TEMPLATE.finditer(content):
        before_var, after_var = match.group(1), match.group(2)
        if before_var == '' and after_var == '':
            var_match = _RE_VAR_IN_TEMPLATE.search(match.group(0))
            if var_match:
                var_name = var_match.group(1)
                traced = trace_variable_values(content, var_name)
                if traced:
                    traced_refs.update(traced)
                else:
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = lines[line_num - 1].strip() if line_num <= len(lines) else ''
                    dynamic_contexts.append((f'{display_path}:{line_num} 全变量 ${var_name}', line_content))
        else:
            prefix_refs.add(before_var)

    for match in _RE_COMPILED_TEMPLATE.finditer(content):
        before_var, after_var = match.group(1), match.group(2)
        if before_var == '' and after_var == '':
            var_match = _RE_VAR_IN_TEMPLATE.search(match.group(0))
            if var_match:
                var_name = var_match.group(1)
                traced = trace_variable_values(content, var_name)
                if traced:
                    traced_refs.update(traced)
                else:
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = lines[line_num - 1].strip() if line_num <= len(lines) else ''
                    dynamic_contexts.append((f'{display_path}:{line_num} 全变量 ${var_name}', line_content))
        else:
            prefix_refs.add(before_var)

    for match in _RE_COMPILED_STATIC.finditer(content):
        static_refs.add(match.group(1))

    for match in _RE_TERNARY.finditer(content):
        name = match.group(1)
        if name not in static_refs:
            start, end = max(0, match.start() - 50), min(len(content), match.end() + 50)
            ctx = content[start:end]
            if '?' in ctx or ':' in ctx or 'params' in ctx:
                static_refs.add(name)

    for line in lines:
        comment_idx = line.find('//')
        effective_line = line[:comment_idx] if comment_idx >= 0 else line
        for match in _RE_BARE_STR.finditer(effective_line):
            name = match.group(1)
            before = effective_line[:match.start()]
            if '$r(' in before or '$r (' in before:
                continue
            static_refs.add(name)
        # 裸资源名（含下划线，如 'ic_plus_red'），仅参与"已使用"判断
        for match in _RE_BARE_RES_NAME.finditer(effective_line):
            bare_refs.add(match.group(1))

    # JSON 配置文件引用："[reslib].media.xxx" 或 "[xxx].media.xxx"
    for match in _RE_MODULE_MEDIA.finditer(content):
        static_refs.add(match.group(1))

    for match in _RE_RAWFILE.finditer(content):
        rawfile_refs.add(match.group(1))

    for match in _RE_GET_RAWFILE.finditer(content):
        rawfile_refs.add(match.group(1))

    # rawfile 路径引用：如 JSON/XML 中的 "rawfile/images/icon.png"
    for match in _RE_RAWFILE_PATH.finditer(content):
        rawfile_refs.add(match.group(1))

    # 兜底：用预编译交替模式一次扫描所有行，O(lines) 替代 O(rawfile_names × lines)
    if rawfile_name_re:
        suffix = filepath.suffix.lower()
        is_config_file = suffix in {'.json', '.json5', '.jsonc', '.xml', '.yaml', '.yml', '.toml'}
        for line in lines:
            m = rawfile_name_re.search(line)
            if not m:
                continue
            name = m.group()
            if name in rawfile_refs:
                continue  # 已收集，跳过
            if is_config_file:
                rawfile_refs.add(name)
            else:
                comment_idx = line.find('//')
                if comment_idx == -1 or m.start() < comment_idx:
                    rawfile_refs.add(name)

    return {'static_refs': static_refs, 'prefix_refs': prefix_refs,
            'traced_refs': traced_refs, 'rawfile_refs': rawfile_refs,
            'bare_refs': bare_refs, 'dynamic_contexts': dynamic_contexts}


def find_all_references(root_dir: Path, source_files: list[Path],
                        rawfile_name_re: 're.Pattern | None' = None):
    all_static_refs, all_prefix_refs, all_traced_refs = set(), set(), set()
    all_rawfile_refs, all_bare_refs, all_dynamic_contexts = set(), set(), []
    ref_sources = {}  # name -> list of source file relative paths
    for filepath in source_files:
        rel_src = str(filepath.relative_to(root_dir))
        result = extract_refs_from_file(filepath, root_dir, rawfile_name_re)
        for name in result['static_refs']:
            ref_sources.setdefault(name, []).append(rel_src)
        for name in result['traced_refs']:
            ref_sources.setdefault(name, []).append(rel_src)
        all_static_refs.update(result['static_refs'])
        all_prefix_refs.update(result['prefix_refs'])
        all_traced_refs.update(result['traced_refs'])
        all_rawfile_refs.update(result['rawfile_refs'])
        all_bare_refs.update(result['bare_refs'])
        all_dynamic_contexts.extend(result['dynamic_contexts'])
    return all_static_refs, all_prefix_refs, all_traced_refs, all_rawfile_refs, all_bare_refs, all_dynamic_contexts, ref_sources


def is_prefix_match(name: str, prefixes: set[str]) -> bool:
    for prefix in prefixes:
        if prefix.endswith('_'):
            if name.startswith(prefix):
                return True
        else:
            if name.startswith(prefix) and name != prefix:
                remainder = name[len(prefix):]
                if remainder and (remainder[0].isdigit() or remainder[0] == '_'):
                    return True
    return False


def open_in_file_manager(path: Path) -> bool:
    if not path.exists():
        messagebox.showwarning('文件不存在', str(path))
        return False
    try:
        if sys.platform == 'darwin':
            subprocess.run(['open', '-R', str(path)], check=False)
        elif sys.platform == 'win32':
            subprocess.run(['explorer', f'/select,{path}'], check=False)
        else:
            subprocess.run(['xdg-open', str(path.parent)], check=False)
        return True
    except Exception as e:
        messagebox.showerror('打开失败', str(e))
        return False


def analyze(root_dir: Path) -> dict:
    """执行分析，返回结果字典。单次 os.walk 同时完成资源收集和源码文件收集。"""
    media_resources: dict[str, list[tuple[Path, int]]] = {}   # name -> [(path, size)]
    rawfile_resources: dict[str, tuple[Path, int]] = {}       # rel_path -> (path, size)
    source_files: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        parts = Path(dirpath).parts
        in_media = 'media' in parts
        in_rawfile = 'rawfile' in parts

        for filename in filenames:
            stem, ext = os.path.splitext(filename)
            ext_lower = ext.lower()
            full_path = Path(dirpath) / filename

            # 收集 media 资源
            if in_media and ext_lower in RESOURCE_EXTENSIONS:
                try:
                    size = full_path.stat().st_size
                except OSError:
                    continue
                media_resources.setdefault(stem, []).append((full_path, size))

            # 收集 rawfile 资源
            if in_rawfile and ext_lower in RESOURCE_EXTENSIONS:
                rawfile_idx = parts.index('rawfile')
                if rawfile_idx + 1 < len(parts):
                    relative = str(Path(*parts[rawfile_idx + 1:]) / filename)
                else:
                    relative = filename
                try:
                    size = full_path.stat().st_size
                except OSError:
                    continue
                rawfile_resources[relative] = (full_path, size)

            # 收集源码文件路径
            if ext_lower in SOURCE_EXTENSIONS:
                source_files.append(full_path)

    # 预编译 rawfile 名称交替正则（一次编译，所有文件共用）
    rawfile_name_re = None
    if rawfile_resources:
        escaped_names = [re.escape(n) for n in rawfile_resources]
        rawfile_name_re = re.compile('|'.join(escaped_names))

    static_refs, prefix_refs, traced_refs, rawfile_refs, bare_refs, dynamic_contexts, ref_sources = \
        find_all_references(root_dir, source_files, rawfile_name_re)

    # 显式引用（$r / params / 模板等），用于"引用缺失"判断
    explicit_refs = set()
    explicit_refs.update(static_refs)
    explicit_refs.update(traced_refs)

    # 所有引用（含裸字符串），用于"未使用"判断
    referenced = set(explicit_refs)
    referenced.update(bare_refs)

    potentially_used = set()
    for name in media_resources:
        if name not in referenced and is_prefix_match(name, prefix_refs):
            potentially_used.add(name)

    unused_media = {}
    potentially_used_media = {}
    total_resource_size = 0
    for name, path_sizes in media_resources.items():
        total_resource_size += sum(s for _, s in path_sizes)
        if name in referenced:
            continue
        paths = [p for p, _ in path_sizes]
        if name in potentially_used:
            potentially_used_media[name] = paths
            continue
        total_size = sum(s for _, s in path_sizes)
        unused_media[name] = (paths, total_size)

    unused_rawfile = {}
    for rel_path, (full_path, size) in rawfile_resources.items():
        total_resource_size += size
        if rel_path in rawfile_refs:
            continue
        unused_rawfile[rel_path] = (full_path, size)

    total_unused = sum(size for _, size in unused_media.values()) + sum(
        size for _, size in unused_rawfile.values()
    )

    missing = explicit_refs - set(media_resources.keys())

    all_items = []
    idx = 0
    for rel_path, (full_path, size) in sorted(unused_rawfile.items()):
        idx += 1
        all_items.append({'path': full_path, 'index': idx, 'size': size,
                          'name': rel_path, 'deleted': False, 'category': 'rawfile未使用'})
    idx = 0
    for name, (paths, size) in sorted(unused_media.items(), key=lambda x: x[1][1], reverse=True):
        for p in paths:
            idx += 1
            all_items.append({'path': p, 'index': idx, 'size': size,
                              'name': name, 'deleted': False, 'category': 'media未使用'})
    idx = 0
    for name, paths in sorted(potentially_used_media.items()):
        # 从 media_resources 中取缓存的 size，避免再次 stat
        path_sizes = media_resources.get(name, [])
        size = sum(s for p2, s in path_sizes if p2 in paths)
        for p in paths:
            idx += 1
            all_items.append({'path': p, 'index': idx, 'size': size,
                              'name': name, 'deleted': False, 'category': '前缀匹配'})
    idx = 0
    for name in sorted(missing):
        idx += 1
        sources = ref_sources.get(name, [])
        all_items.append({'path': None, 'index': idx, 'size': 0,
                          'name': name, 'deleted': False, 'category': '引用缺失',
                          'sources': sources})

    return {
        'media_count': len(media_resources),
        'rawfile_count': len(rawfile_resources),
        'static_count': len(static_refs),
        'prefix_count': len(prefix_refs),
        'traced_count': len(traced_refs),
        'rawfile_ref_count': len(rawfile_refs),
        'unused_media_count': len(unused_media),
        'unused_rawfile_count': len(unused_rawfile),
        'pot_count': len(potentially_used_media),
        'missing_count': len(missing),
        'total_resource_size': total_resource_size,
        'total_unused': total_unused,
        'dynamic_contexts': dynamic_contexts,
        'all_items': all_items,
    }


# ═══════════════════════════════════════════════
# GUI · Treeview 列表
# ═══════════════════════════════════════════════

ROW_H = 48
PAD_X = 12
INTRO_HEIGHT = 36
WINDOW_W, WINDOW_H = 1400, 1000


def _build_stats_panel(parent: tk.Widget, result: dict):
    """构建顶部统计卡片面板。"""
    container = tk.Frame(parent, bg=C_BG)
    container.pack(fill='x', padx=PAD_X, pady=(0, 0))

    inner = tk.Frame(container, bg=C_BG)
    inner.pack(fill='both', padx=4, pady=4)

    cards = [
        ('media 资源', result['media_count'], '个', C_ACCENT_BLUE),
        ('rawfile 资源', result['rawfile_count'], '个', C_ACCENT_BLUE),
        ('静态引用', result['static_count'], '个', C_ACCENT_GREEN),
        ('前缀引用', result['prefix_count'], '个', C_ACCENT_GREEN),
        ('变量引用', result['traced_count'], '个', C_ACCENT_GREEN),
        ('rawfile 引用', result['rawfile_ref_count'], '个', C_ACCENT_GREEN),
        ('未使用 media', result['unused_media_count'], '个', C_ACCENT_RED),
        ('未使用 rawfile', result['unused_rawfile_count'], '个', C_ACCENT_RED),
        ('前缀匹配', result['pot_count'], '个', C_ACCENT_ORANGE),
        ('引用缺失', result['missing_count'], '个', C_ACCENT_BLUE),
        ('资源总大小', format_size(result['total_resource_size']), '', C_TEXT),
        ('可释放空间', format_size(result['total_unused']), '', C_ACCENT_RED),
    ]

    for i, (label, value, unit, accent) in enumerate(cards):
        col, row = i % 6, i // 6
        card = tk.Frame(inner, bg=accent,
                        highlightbackground=C_BORDER, highlightthickness=1)
        card.grid(row=row, column=col, padx=3, pady=2, sticky='ew')
        card_body = tk.Frame(card, bg=C_CARD_BG, padx=10, pady=6)
        card_body.pack(fill='both', expand=True, pady=(3, 0))
        tk.Label(card_body, text=label, font=('TkDefaultFont', 9), fg=C_TEXT_SEC,
                 bg=C_CARD_BG, anchor='w').pack(anchor='w')
        val_frame = tk.Frame(card_body, bg=C_CARD_BG)
        val_frame.pack(anchor='w')
        tk.Label(val_frame, text=str(value), font=('TkDefaultFont', 15, 'bold'),
                 fg=accent, bg=C_CARD_BG).pack(side='left')
        if unit:
            tk.Label(val_frame, text=f' {unit}', font=('TkDefaultFont', 9),
                     fg=C_TEXT_SEC, bg=C_CARD_BG).pack(side='left', pady=(5, 0))

    for i in range(6):
        inner.columnconfigure(i, weight=1)


def show_action_window(result: dict, root_dir: Path) -> None:
    root = tk.Tk()
    root.title('鸿蒙未使用源分析工具')
    root.minsize(600, 400)
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = (screen_w - WINDOW_W) // 2
    y = (screen_h - WINDOW_H) // 2
    root.geometry(f'{WINDOW_W}x{WINDOW_H}+{x}+{y}')
    root.configure(bg=C_BG)

    # 设置窗口图标（base64 内嵌）
    try:
        icon_bytes = base64.b64decode(ICON_DATA)
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(icon_bytes)
            tmp.flush()
        icon_img = tk.PhotoImage(file=tmp.name)
        root.wm_iconphoto(False, icon_img)
        root._icon_img_ref = icon_img  # 防止被 GC
        root._icon_tmp_path = tmp.name
    except Exception:
        pass  # 图标设置失败不影响主功能

    items = result['all_items']

    # ── 标题栏 ──
    title_bar = tk.Frame(root, bg=C_BG)
    title_bar.pack(fill='x', padx=PAD_X, pady=(10, 2))
    tk.Label(title_bar, text='扫描项目中未使用的资源（media / rawfile），支持定位与删除',
             font=('TkDefaultFont', 11), fg=C_TEXT, bg=C_BG).pack(side='left')
    tk.Label(title_bar, text='python3 find_unused_resources.py [项目根目录]',
             font=(MONO_FONT, 9), fg=C_TEXT_SEC, bg=C_BG).pack(side='right')

    # ── 统计面板 ──
    _build_stats_panel(root, result)

    # ── Treeview 样式 ──
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('Treeview',
                    background='#ffffff',
                    foreground=C_TEXT,
                    fieldbackground='#ffffff',
                    rowheight=ROW_H,
                    font=('TkDefaultFont', 10),
                    borderwidth=0,
                    relief='flat',
                    indent=10)
    style.configure('Treeview.Heading',
                    background='#e8edf4',
                    foreground=C_TEXT,
                    font=('TkDefaultFont', 10, 'bold'),
                    relief='flat',
                    padding=(8, 6))
    style.map('Treeview.Heading',
              background=[('active', '#d0dae8')])
    style.map('Treeview',
              background=[('selected', '#d6e4f0')],
              foreground=[('selected', C_TEXT)])
    # 滚动条
    style.configure('Sbar.Vertical.TScrollbar',
                    width=14,
                    borderwidth=0,
                    relief='flat',
                    troughcolor=C_BG,
                    background='#c0c0c0',
                    arrowsize=12)
    style.map('Sbar.Vertical.TScrollbar',
              background=[('active', '#a0a0a0'),
                          ('pressed', '#909090')])

    # ── Treeview ──
    tree_frame = tk.Frame(root, bg=C_BG)
    tree_frame.pack(fill='both', expand=True, padx=PAD_X, pady=(4, 0))

    # 用 tree+headings：#0 树列放分类标题和"序号 文件名"，无独立序号列
    columns = ('size', 'path', 'status')
    tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings', selectmode='extended')

    tree.heading('#0', text='  分类 / 文件名')
    tree.heading('size', text='大小')
    tree.heading('path', text='路径')
    tree.heading('status', text='状态')

    tree.column('#0', width=320, minwidth=200, anchor='w', stretch=True)
    tree.column('size', width=90, minwidth=70, anchor='w', stretch=False)
    tree.column('path', width=700, minwidth=200, anchor='w', stretch=True)
    tree.column('status', width=100, minwidth=80, anchor='e', stretch=False)

    # ── 标签 ──
    tree.tag_configure('even', background=C_ROW_EVEN)
    tree.tag_configure('odd', background=C_ROW_ODD)
    tree.tag_configure('deleted', background='#f5f5f5', foreground=C_ROW_DELETED)
    tree.tag_configure('hover', background=C_ROW_HOVER)
    tree.tag_configure('missing', foreground=C_ACCENT_RED)

    for cat_key, (bg_color, accent, label_text) in CAT_COLORS.items():
        tree.tag_configure(f'cat_{cat_key}', background=bg_color, foreground='#333333',
                           font=('TkDefaultFont', 10, 'bold'))

    tree.tag_configure('dyn_header', background='#fff5f0', foreground='#8b4513',
                       font=('TkDefaultFont', 10, 'bold'))
    tree.tag_configure('dyn', background='#fffaf7', foreground=C_TEXT_SEC,
                       font=(MONO_FONT, 9))

    scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview,
                              style='Sbar.Vertical.TScrollbar')
    tree.configure(yscrollcommand=scrollbar.set)

    # ── 填充数据：分类为父节点，数据项为子节点 ──
    iid_to_item = {}
    last_cat = None
    cat_iid = None
    row_seq = 0

    # 预计算各分类数量
    cat_counts = {}
    for item in items:
        c = item.get('category', '')
        cat_counts[c] = cat_counts.get(c, 0) + 1

    for item in items:
        cat = item.get('category', '')
        if cat != last_cat:
            last_cat = cat
            _, _, label_text = CAT_COLORS.get(cat, ('#e8e8e8', '#666', cat))
            count = cat_counts.get(cat, 0)
            cat_iid = tree.insert('', 'end',
                                 text=f' {label_text}（{count}）',
                                 values=('', '', ''),
                                 tags=(f'cat_{cat}',))
            row_seq = 0

        is_missing = item['path'] is None
        rel_path = str(item['path'].relative_to(root_dir)) if not is_missing else ', '.join(item.get('sources', []))
        size_str = format_size(item['size']) if not is_missing else '-'
        display_name = f"{item['name']}{item['path'].suffix}" if not is_missing else item['name']
        status_text = '文件不存在' if is_missing else ('已删除' if item['deleted'] else '')

        if item['deleted']:
            row_tags = ('deleted',)
        elif is_missing:
            row_tags = ('missing', 'odd' if row_seq % 2 else 'even')
        else:
            row_tags = ('odd' if row_seq % 2 else 'even',)

        iid = tree.insert(cat_iid, 'end',
                         text=f'{item["index"]}      {display_name}',
                         values=(size_str, rel_path, status_text),
                         tags=row_tags)
        iid_to_item[iid] = item
        row_seq += 1

    # 动态引用区域 — 父节点为标题，子节点为各条引用
    dyn_iid_to_path = {}
    dynamic_contexts = result['dynamic_contexts']
    if dynamic_contexts:
        dyn_parent = tree.insert('', 'end',
                                text=f' ⚠ 无法追踪的动态引用（{len(dynamic_contexts)} 条，需人工确认）',
                                values=('', '', ''),
                                tags=('dyn_header',))
        for dc in dynamic_contexts:
            desc, line_content = dc
            file_rel = desc.split(':')[0]
            abs_path = root_dir / file_rel
            if len(line_content) > 50:
                wrapped_code = line_content[:50] + '\n' + line_content[50:100]
            else:
                wrapped_code = line_content
            iid = tree.insert(dyn_parent, 'end',
                             text=f' {wrapped_code}',
                             values=('', desc, ''),
                             tags=('dyn',))
            dyn_iid_to_path[iid] = abs_path

    # 展开所有分类节点
    for node in tree.get_children():
        tree.item(node, open=True)

    # ── 操作：右键菜单 + 键盘快捷键 ──
    ctx_menu = tk.Menu(root, tearoff=0, font=('TkDefaultFont', 10))

    def _open_selected():
        sel = tree.selection()
        if not sel or len(sel) != 1:
            return  # 只在单选时打开
        iid = sel[0]
        if iid in iid_to_item:
            item = iid_to_item[iid]
            if item['path'] is not None and not item['deleted']:
                open_in_file_manager(item['path'])
            elif item['path'] is None:
                sources = item.get('sources', [])
                if sources:
                    src_path = root_dir / sources[0]
                    open_in_file_manager(src_path)
        elif iid in dyn_iid_to_path:
            open_in_file_manager(dyn_iid_to_path[iid])

    def _delete_selected():
        sel = tree.selection()
        if not sel:
            return
        # 过滤出可删除的项目（未删除且有路径）
        deletable = [(iid, iid_to_item[iid]) for iid in sel
                     if iid in iid_to_item and not iid_to_item[iid]['deleted'] and iid_to_item[iid]['path'] is not None]
        if not deletable:
            return
        # 确认对话框
        count = len(deletable)
        if count == 1:
            item = deletable[0][1]
            msg = f'确定要删除 {item["path"].name} 吗？\n\n{item["path"]}'
        else:
            msg = f'确定要删除选中的 {count} 个文件吗？\n\n此操作不可撤销。'
        if not messagebox.askyesno('确认删除', msg):
            return
        # 批量删除
        failed = []
        for iid, item in deletable:
            try:
                item['path'].unlink()
                item['deleted'] = True
                vals = list(tree.item(iid, 'values'))
                vals[2] = '已删除'
                tree.item(iid, values=vals, tags=('deleted',))
            except Exception as e:
                failed.append(f'{item["path"].name}: {e}')
        _update_deleted_count()
        if failed:
            messagebox.showerror('部分删除失败', '\n'.join(failed))

    def _copy_name():
        sel = tree.selection()
        if not sel:
            return
        copy_list = []
        for iid in sel:
            if iid in iid_to_item:
                item = iid_to_item[iid]
                copy_list.append(item['path'].name if item['path'] is not None else item['name'])
            elif iid in dyn_iid_to_path:
                copy_list.append(dyn_iid_to_path[iid].name)
        if copy_list:
            root.clipboard_clear()
            root.clipboard_append('\n'.join(copy_list))

    def _on_rclick(event):
        row = tree.identify_row(event.y)
        if not row or (row not in iid_to_item and row not in dyn_iid_to_path):
            return
        # 如果右键点击的行不在当前选择中，重新选择该行
        if row not in tree.selection():
            tree.selection_set(row)
        sel = tree.selection()
        deletable_count = sum(1 for iid in sel
                             if iid in iid_to_item and not iid_to_item[iid]['deleted'] and iid_to_item[iid]['path'] is not None)
        ctx_menu.delete(0, 'end')
        if len(sel) > 1:
            # 多选：只显示删除选项
            if deletable_count > 0:
                ctx_menu.add_command(label=f'删除 ({deletable_count} 项)', command=_delete_selected)
        else:
            # 单选：完整菜单
            ctx_menu.add_command(label='打开定位', command=_open_selected)
            ctx_menu.add_command(label='复制名称', command=_copy_name)
            if deletable_count > 0:
                ctx_menu.add_separator()
                ctx_menu.add_command(label='删除文件', command=_delete_selected)
        ctx_menu.post(event.x_root, event.y_root)

    tree.bind('<Button-2>', _on_rclick)
    tree.bind('<Button-3>', _on_rclick)
    tree.bind('<Control-Button-1>', _on_rclick)

    # 单击父节点行任意位置 → 切换展开/收起
    def _on_click(event):
        row = tree.identify_row(event.y)
        if row and tree.get_children(row):
            tree.item(row, open=not tree.item(row, 'open'))
            return 'break'

    tree.bind('<Button-1>', _on_click)

    # 双击 → 打开
    tree.bind('<Double-1>', lambda _e: _open_selected())

    # 键盘快捷键
    tree.bind('<Delete>', lambda _e: _delete_selected())
    tree.bind('<BackSpace>', lambda _e: _delete_selected())
    tree.bind('<Return>', lambda _e: _open_selected())

    # ── hover 效果 ──
    _last_hover = [None]

    def _on_motion(event):
        row = tree.identify_row(event.y)
        if row == _last_hover[0]:
            return
        if _last_hover[0]:
            old_tags = list(tree.item(_last_hover[0], 'tags'))
            old_tags = [t for t in old_tags if t != 'hover']
            tree.item(_last_hover[0], tags=old_tags)
        if row and (row in iid_to_item or row in dyn_iid_to_path):
            if row in iid_to_item:
                item = iid_to_item[row]
                if not item['deleted'] and item['path'] is not None:
                    new_tags = list(tree.item(row, 'tags'))
                    new_tags.append('hover')
                    tree.item(row, tags=new_tags)
            elif row in dyn_iid_to_path:
                new_tags = list(tree.item(row, 'tags'))
                new_tags.append('hover')
                tree.item(row, tags=new_tags)
        _last_hover[0] = row

    def _on_leave(_e):
        if _last_hover[0]:
            old_tags = list(tree.item(_last_hover[0], 'tags'))
            old_tags = [t for t in old_tags if t != 'hover']
            tree.item(_last_hover[0], tags=old_tags)
            _last_hover[0] = None

    tree.bind('<Motion>', _on_motion)
    tree.bind('<Leave>', _on_leave)

    # 进入时聚焦，确保滚轮事件生效
    tree.bind('<Enter>', lambda _e: tree.focus_set())

    # ── 布局 ──
    tree.pack(side='left', fill='both', expand=True)
    scrollbar.pack(side='right', fill='y')

    # ── 底部栏 ──
    footer = tk.Frame(root, bg=C_BG, height=INTRO_HEIGHT)
    footer.pack(fill='x', padx=PAD_X, pady=(2, PAD_X))
    footer.pack_propagate(False)

    tk.Label(footer, text=str(root_dir), font=(MONO_FONT, 9), fg=C_TEXT_SEC, bg=C_BG).pack(side='left')

    deleted_label = tk.Label(footer, text='', font=('TkDefaultFont', 9, 'bold'),
                             fg=C_ACCENT_RED, bg=C_BG)
    deleted_label.pack(side='left', padx=(8, 0))

    tk.Label(footer, text='双击打开  ·  多选: Cmd/Ctrl+点击  ·  右键菜单  ·  ⌫ Delete 删除',
             font=('TkDefaultFont', 9), fg=C_TEXT_SEC, bg=C_BG).pack(side='right')

    def _update_deleted_count():
        d = sum(1 for it in items if it['deleted'])
        deleted_label.configure(text=f'已删除 {d} 项' if d else '')

    root.mainloop()


# ═══════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════

def _run_with_spinner(label: str, fn, *args):
    """在终端显示旋转动画，同时执行 fn(*args)，返回结果。"""
    spinner = itertools.cycle('⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏')
    stop = threading.Event()
    def _spin():
        while not stop.is_set():
            print(f'\r{next(spinner)} {label}', end='', flush=True)
            time.sleep(0.08)
    t = threading.Thread(target=_spin, daemon=True)
    t.start()
    try:
        result = fn(*args)
    finally:
        stop.set()
        t.join()
        print('\r' + ' ' * (len(label) + 4) + '\r', end='', flush=True)
    return result


if __name__ == '__main__':
    arg_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    if not arg_root.is_dir():
        print(f'错误: {arg_root} 不是有效目录', file=sys.stderr)
        sys.exit(1)

    result = _run_with_spinner(f'正在分析: {arg_root}', analyze, arg_root)
    print('分析完成，打开 GUI 面板')
    show_action_window(result, arg_root)