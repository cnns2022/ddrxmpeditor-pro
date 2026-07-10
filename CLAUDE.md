# CLAUDE.md — DDR XMP Editor Pro

> 开发规则已统一至用户级全局 CLAUDE.md，本文件仅保留项目架构速查。

## 代码结构

```
ddr_xmp_editor_pro/
├── lang.py              # 语言字符串（新增功能放这里）
├── ddr5_utils.py        # CRC、转换函数（只追加新函数，不改现有）
├── ddr5_spd_model.py    # DDR5 数据模型
├── ddr4_spd_model.py    # DDR4 数据模型
└── ddr_xmp_editor.py    # GUI 主程序
```

### GUI 类层次
- `DDR5XMPEditorApp` — 主窗口，菜单，标签页管理
- `SPDTabFrame` — SPD 时序编辑（DDR4/DDR5 双模式）
- `XMPTabFrame` — XMP Profile 编辑（DDR4/DDR5 双模式）
- `EXPOTabFrame` — EXPO 编辑（仅 DDR5）
- `MiscTabFrame` — 杂项设置
