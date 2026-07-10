"""Language strings for DDR XMP Editor Pro."""

_current = 'zh'

STRINGS = {
    # Title
    'title': {'zh': 'DDR XMP Editor Pro V1.0 — 周强  cnns@sina.com',
              'en': 'DDR XMP Editor Pro V1.0'},

    # Menu
    'menu_file': {'zh': '文件 (File)', 'en': 'File'},
    'menu_open': {'zh': '打开 (Open)...', 'en': 'Open...'},
    'menu_save': {'zh': '保存 (Save)...', 'en': 'Save...'},
    'menu_exit': {'zh': '退出 (Exit)', 'en': 'Exit'},
    'menu_help': {'zh': '帮助 (Help)', 'en': 'Help'},
    'menu_usage': {'zh': '使用说明 (Help)', 'en': 'Usage Guide'},
    'menu_lang': {'zh': '语言 (Language)', 'en': 'Language'},
    'menu_lang_zh': {'zh': '中文', 'en': 'Chinese'},
    'menu_lang_en': {'zh': 'English', 'en': 'English'},

    # Dialogs
    'open_title': {'zh': '打开 SPD 文件', 'en': 'Open SPD File'},
    'save_title': {'zh': '保存 SPD 文件', 'en': 'Save SPD File'},
    'file_filter': {'zh': 'SPD 文件', 'en': 'SPD files'},
    'error': {'zh': '错误', 'en': 'Error'},
    'warning': {'zh': '警告', 'en': 'Warning'},
    'info': {'zh': '提示', 'en': 'Info'},
    'success': {'zh': '成功', 'en': 'Success'},

    # Profile checkboxes
    'xmp1': {'zh': 'XMP 1', 'en': 'XMP 1'},
    'xmp2': {'zh': 'XMP 2', 'en': 'XMP 2'},
    'xmp3': {'zh': 'XMP 3', 'en': 'XMP 3'},
    'xmp_u1': {'zh': 'XMP User 1', 'en': 'XMP User 1'},
    'xmp_u2': {'zh': 'XMP User 2', 'en': 'XMP User 2'},
    'expo1': {'zh': 'EXPO 1', 'en': 'EXPO 1'},
    'expo2': {'zh': 'EXPO 2', 'en': 'EXPO 2'},
    'spd_file_label': {'zh': 'SPD 文件:', 'en': 'SPD File:'},
    'no_file': {'zh': '未打开文件', 'en': 'No file opened'},

    # Tabs
    'tab_spd': {'zh': 'SPD', 'en': 'SPD'},
    'tab_xmp1': {'zh': 'XMP 1', 'en': 'XMP 1'},
    'tab_xmp2': {'zh': 'XMP 2', 'en': 'XMP 2'},
    'tab_xmp3': {'zh': 'XMP 3', 'en': 'XMP 3'},
    'tab_xmp_u1': {'zh': 'XMP User 1', 'en': 'XMP User 1'},
    'tab_xmp_u2': {'zh': 'XMP User 2', 'en': 'XMP User 2'},
    'tab_expo1': {'zh': 'EXPO 1', 'en': 'EXPO 1'},
    'tab_expo2': {'zh': 'EXPO 2', 'en': 'EXPO 2'},
    'tab_misc': {'zh': '杂项 (Misc)', 'en': 'Misc'},

    # Frequency
    'freq_group': {'zh': '频率 (Frequency) / Speed Bin', 'en': 'Frequency / Speed Bin'},
    'freq_group_xmp': {'zh': '频率 (Frequency) / Speed Bin', 'en': 'Frequency / Speed Bin'},
    'speed_bin': {'zh': 'Speed Bin:', 'en': 'Speed Bin:'},
    'apply': {'zh': 'Apply', 'en': 'Apply'},
    'speed_bin_hint': {'zh': '选择 Speed Bin 后点击 Apply 自动填充参数', 'en': 'Select Speed Bin and click Apply'},
    'min_cycle': {'zh': 'Min Cycle Time (ps):', 'en': 'Min Cycle Time (ps):'},

    # CAS
    'cas_group': {'zh': '支持的 CAS Latency', 'en': 'Supported CAS Latency'},
    'cas_group_ddr4': {'zh': '支持的 CAS Latency (DDR4)', 'en': 'Supported CAS Latency (DDR4)'},

    # Timings
    'timing_ddr5': {'zh': '时序参数 (Timings) - DDR5', 'en': 'Timings - DDR5'},
    'timing_ddr4': {'zh': '时序参数 (Timings) - DDR4 (MTB=0.125ns)', 'en': 'Timings - DDR4 (MTB=0.125ns)'},
    'timing': {'zh': '时序参数 (Timings)', 'en': 'Timings'},
    'param_name': {'zh': '参数名', 'en': 'Parameter'},
    'value_ps': {'zh': '值 (ps)', 'en': 'Value (ps)'},
    'ticks': {'zh': 'Ticks', 'en': 'Ticks'},
    'lower_limit': {'zh': 'Lower Limit', 'en': 'Lower Limit'},
    'time_ns': {'zh': '时间 (ns)', 'en': 'Time (ns)'},

    # XMP Profile
    'profile_info': {'zh': 'Profile 信息', 'en': 'Profile Info'},
    'profile_name': {'zh': 'Profile 名称:', 'en': 'Profile Name:'},
    'cmd_rate': {'zh': '命令速率:', 'en': 'Command Rate:'},
    'voltage_ddr5': {'zh': '电压 (Voltages) - DDR5', 'en': 'Voltages - DDR5'},
    'voltage_ddr4': {'zh': '电压 (Voltage) - DDR4', 'en': 'Voltage - DDR4'},
    'vdd': {'zh': 'VDD:', 'en': 'VDD:'},
    'vddq': {'zh': 'VDDQ:', 'en': 'VDDQ:'},
    'vpp': {'zh': 'VPP:', 'en': 'VPP:'},
    'vmemctrl': {'zh': 'VMEMCTRL:', 'en': 'VMEMCTRL:'},

    # Misc tab
    'physical': {'zh': '物理特性 (Physical)', 'en': 'Physical'},
    'form_factor': {'zh': 'Form Factor:', 'en': 'Form Factor:'},
    'density_group': {'zh': '密度 / Downbin', 'en': 'Density / Downbin'},
    'density': {'zh': 'Density:', 'en': 'Density:'},
    'bank_groups': {'zh': 'Bank Groups:', 'en': 'Bank Groups:'},
    'banks_per_bg': {'zh': 'Banks per Bank Group:', 'en': 'Banks per Bank Group:'},
    'col_addr': {'zh': 'Column Addresses:', 'en': 'Column Addresses:'},
    'row_addr': {'zh': 'Row Addresses:', 'en': 'Row Addresses:'},
    'module_org': {'zh': '模组组织 (Module Organization)', 'en': 'Module Organization'},
    'dev_width': {'zh': 'Device Width:', 'en': 'Device Width:'},
    'module_info': {'zh': '模组信息 (Module Info)', 'en': 'Module Info'},
    'mfg_year': {'zh': '制造年份:', 'en': 'Mfg Year:'},
    'mfg_week': {'zh': '制造周数:', 'en': 'Mfg Week:'},
    'part_num': {'zh': '料号 (Part Number):', 'en': 'Part Number:'},
    'heat_spreader': {'zh': '安装散热片 (Heat Spreader)', 'en': 'Heat Spreader'},
    'copy_xmp': {'zh': '复制 XMP Profile', 'en': 'Copy XMP Profile'},
    'src': {'zh': '源 (Source):', 'en': 'Source:'},
    'tgt': {'zh': '目标 (Target):', 'en': 'Target:'},
    'copy_btn': {'zh': '复制 (Copy)', 'en': 'Copy'},
    'import_export': {'zh': '导入/导出 XMP Profile', 'en': 'Import/Export XMP Profile'},
    'profile': {'zh': 'Profile:', 'en': 'Profile:'},
    'import_btn': {'zh': '导入 (Import)', 'en': 'Import'},
    'export_btn': {'zh': '导出 (Export)', 'en': 'Export'},

    # Messages
    'need_open_file': {'zh': '请先打开一个 SPD 文件。', 'en': 'Please open an SPD file first.'},
    'need_select_bin': {'zh': '请先选择一个 Speed Bin。', 'en': 'Please select a Speed Bin first.'},
    'save_ok': {'zh': 'DDR5 SPD 已成功保存到:\n', 'en': 'SPD saved to:\n'},
    'copy_ok': {'zh': 'XMP Profile 数据已成功复制。', 'en': 'XMP Profile copied.'},
    'import_ok': {'zh': 'XMP 3.0 Profile 已成功导入。', 'en': 'XMP 3.0 Profile imported.'},
    'export_ok': {'zh': 'XMP 3.0 Profile [{n}] 已成功保存到:\n{p}', 'en': 'XMP 3.0 Profile [{n}] saved to:\n{p}'},
    'copy_fail': {'zh': '复制 XMP Profile 数据时出错。', 'en': 'Error copying XMP Profile.'},
    'export_fail': {'zh': '保存文件时出错:\n', 'en': 'Error saving file:\n'},
    'import_fail': {'zh': '读取文件时出错:\n', 'en': 'Error reading file:\n'},
    'open_fail': {'zh': '打开文件时出错:\n', 'en': 'Error opening file:\n'},
    'expo_fail': {'zh': '创建 EXPO 失败:\n', 'en': 'Failed to create EXPO:\n'},
    'expo_rm_fail': {'zh': '删除 EXPO 失败:\n', 'en': 'Failed to remove EXPO:\n'},
    'spd_size_err': {'zh': 'SPD 文件至少需要 {n} 字节，实际为 {m} 字节。', 'en': 'SPD file requires at least {n} bytes, got {m} bytes.'},
    'unknown_type': {'zh': '未知内存类型 (Byte 2 = 0x{t:02X})\n支持: DDR4 (0x0C) / DDR5 (0x12)', 'en': 'Unknown memory type (Byte 2 = 0x{t:02X})\nSupported: DDR4 (0x0C) / DDR5 (0x12)'},
    'parse_fail': {'zh': '解析 DDR5 SPD 文件失败。', 'en': 'Failed to parse SPD file.'},
    'expo_warn': {'zh': '检测到 EXPO 数据。\n\n当前对 EXPO 的支持仍处于实验阶段！', 'en': 'EXPO data detected. EXPO support is experimental!'},
    'expo_created': {'zh': 'EXPO 数据块已创建。\n请在 EXPO 1 和 EXPO 2 标签页中编辑参数。\n保存时 CRC 会自动更新。', 'en': 'EXPO block created. Edit in EXPO 1/2 tabs. CRC auto-updated on save.'},
    'expo_removed': {'zh': 'EXPO 数据块已删除。', 'en': 'EXPO block removed.'},
    'expo_exists': {'zh': '当前 SPD 已包含 EXPO 数据。', 'en': 'SPD already contains EXPO data.'},

    # Help content
    'help_title': {'zh': 'DDR XMP Editor Pro V1.0 — 使用说明', 'en': 'DDR XMP Editor Pro V1.0 — Usage Guide'},
    'help_text': {
        'zh': (
            "DDR XMP Editor Pro V1.0\n"
            "DDR4/DDR5 SPD 二进制文件编辑器 — 支持 XMP 2.0/3.0 和 EXPO 配置\n"
            "作者: 周强  cnns@sina.com\n"
            "This is a fork of DDR5 XMP Editor\n\n"
            "——— 基本操作 ———\n\n"
            "1. 文件 → 打开: 打开 DDR4/DDR5 SPD 二进制文件(.spd/.bin)\n"
            "   文件必须 ≥512(DDR4)/1024(DDR5)字节，超长自动截取\n\n"
            "2. 文件 → 保存: 保存修改后的 SPD 文件\n"
            "   CRC 校验和自动计算并更新\n\n"
            "——— SPD 标签页 ———\n\n"
            "• Speed Bin 下拉框: 选择 JEDEC 标准 Speed Bin\n"
            "  点击 Apply 自动填充频率、CAS Latency、全部时序参数\n"
            "• 频率: Min Cycle Time(ps) → 自动显示 MHz / MT/s\n"
            "• CAS Latency: 勾选支持的 CL 值\n"
            "• 时序参数: 左列为主时序，右列为第二时序\n\n"
            "——— XMP 标签页 ———\n\n"
            "• 勾选顶部复选框启用 Profile，取消勾选禁用\n"
            "• 禁用时标签页灰化不可编辑\n"
            "• Speed Bin: 选择后点 Apply 自动填充 Profile 参数\n"
            "• 电压单位: 110 = 1.10V, 135 = 1.35V\n\n"
            "——— EXPO 标签页 (仅 DDR5) ———\n\n"
            "• 勾选顶部 EXPO 复选框自动创建 EXPO 数据块\n"
            "• EXPO 不支持 CAS Latency / 命令速率\n\n"
            "——— 快捷键 ———\n"
            "Ctrl+O: 打开文件    Ctrl+S: 保存文件\n"
        ),
        'en': (
            "DDR XMP Editor Pro V1.0\n"
            "DDR4/DDR5 SPD binary editor — XMP 2.0/3.0 and EXPO support\n"
            "Author: Zhou Qiang  cnns@sina.com\n"
            "This is a fork of DDR5 XMP Editor\n\n"
            "——— Basic Operations ———\n\n"
            "1. File → Open: Open DDR4/DDR5 SPD binary (.spd/.bin)\n"
            "   File must be >= 512(DDR4)/1024(DDR5) bytes\n\n"
            "2. File → Save: Save modified SPD file\n"
            "   CRC checksum auto-calculated\n\n"
            "——— SPD Tab ———\n\n"
            "• Speed Bin dropdown: Select JEDEC standard speed bin\n"
            "  Click Apply to auto-fill frequency, CAS, all timings\n"
            "• Frequency: Min Cycle Time(ps) → auto-display MHz/MT/s\n"
            "• CAS Latency: Check supported CL values\n"
            "• Timings: Left=primary timings, Right=secondary timings\n\n"
            "——— XMP Tabs ———\n\n"
            "• Check top checkbox to enable profile\n"
            "• Disabled tabs are grayed out\n"
            "• Speed Bin: Select and Apply to auto-fill\n"
            "• Voltage unit: 110 = 1.10V, 135 = 1.35V\n\n"
            "——— EXPO Tabs (DDR5 only) ———\n\n"
            "• Check EXPO checkbox to auto-create EXPO block\n"
            "• EXPO does not support CAS Latency / Command Rate\n\n"
            "——— Shortcuts ———\n"
            "Ctrl+O: Open    Ctrl+S: Save\n"
        ),
    },
    'help_close': {'zh': '关闭', 'en': 'Close'},
}


def t(key: str, **kwargs) -> str:
    """Get translated string for current language."""
    s = STRINGS.get(key, {}).get(_current, key)
    if kwargs:
        s = s.format(**kwargs)
    return s


def set_lang(lang: str):
    """Switch language ('zh' or 'en')."""
    global _current
    _current = lang


def current_lang() -> str:
    return _current
