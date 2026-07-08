#!/usr/bin/env python3
"""
DDR XMP Editor Pro V1.0 — tkinter GUI 主应用
=============================================
DDR4/DDR5 SPD 二进制文件编辑器，支持 XMP 2.0/3.0 和 EXPO 配置。
作者: 周强  cnns@sina.com
This is a fork of DDR5 XMP Editor

功能:
  - 自动检测 DDR4/DDR5 (Byte 2)
  - DDR4: 512B SPD + XMP 2.0 (2 profiles) + 24 Speed Bins
  - DDR5: 1024B SPD + XMP 3.0 (5 profiles) + EXPO + 64 Speed Bins
  - Speed Bin 一键填充 (SPD / XMP / EXPO)
  - CRC 自动计算 (DDR4=CRC-16/ARC, DDR5=CRC-16/XMODEM)
  - XMP Profile 复制、导入、导出
"""

import os
import sys
import math
import tkinter as tk

# =============================================================================
# 辅助函数
# =============================================================================

def set_children_state(widget, state: str):
    """递归设置容器内所有子控件的启用/禁用状态。

    state='disabled' → 所有控件灰化不可操作
    state='normal'  → 恢复: Spinbox/Entry='normal', Combobox='readonly'
    """
    for child in widget.winfo_children():
        if isinstance(child, ttk.Combobox):
            try:
                child.configure(state='readonly' if state == 'normal' else 'disabled')
            except tk.TclError:
                pass
        elif isinstance(child, (ttk.Button, ttk.Checkbutton, ttk.Spinbox,
                                 ttk.Entry, ttk.Radiobutton)):
            try:
                child.configure(state=state)
            except tk.TclError:
                pass
        # Frame/Labelframe/Canvas: 递归处理
        set_children_state(child, state)
from tkinter import ttk, filedialog, messagebox

# 导入数据模型
from ddr5_spd_model import (
    DDR5_SPD, XMP_3_0, EXPO,
    FormFactor, Density, OperatingTempRange, CommandRate,
    ALL_CL_VALUES,
    FORM_FACTOR_MAP, DENSITY_MAP,
    BANK_GROUPS_MAP, BANKS_PER_BANK_GROUP_MAP,
    COLUMN_ADDRESS_MAP, ROW_ADDRESS_MAP, DEVICE_WIDTH_MAP,
    COMMAND_RATE_MAP,
)


# =============================================================================
# 辅助函数
# =============================================================================

def format_frequency(min_cycle_time: int) -> str:
    """将 Min Cycle Time (ps) 转换为 MHz 和 MT/s 字符串。"""
    if min_cycle_time <= 0:
        return ("N/A", "N/A")
    freq_mhz = 1.0 / (min_cycle_time / 1_000_000)
    mt_s = freq_mhz * 2
    return (f"{freq_mhz:.3f} MHz", f"{mt_s:.3f} MT/s")


def _on_spinbox_validate_int(P, min_val, max_val):
    """验证 Spinbox 输入是否为有效整数。"""
    if P == "" or P == "-":
        return True
    try:
        v = int(P)
        return min_val <= v <= max_val
    except ValueError:
        return False


# =============================================================================
# SPDTabFrame — JEDEC SPD 参数编辑页
# =============================================================================

class SPDTabFrame(ttk.Frame):
    """JEDEC SPD 基本参数编辑标签页。

    包含:
      - 频率设置 (Min Cycle Time → MHz / MT/s)
      - CAS Latency 复选框网格 (CL20-CL98)
      - 时序参数表 (ps 值 + nCK Ticks)
    """

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.spd: DDR5_SPD = None

        self._vars: dict = {}       # 存储所有 tk.Var
        self._cl_vars: dict = {}    # CAS Latency BooleanVar
        self._setting_vars = False  # 防止 trace 递归

        self._build_ui()

    # ---- UI 构建 ----

    def _build_ui(self):
        self._build_frequency_group()
        self._cas_frame = None
        self._timing_frame = None
        self._build_type_specific()

    def _build_frequency_group(self):
        """频率设置区域（含 Speed Bin 下拉框）。"""
        frame = ttk.Labelframe(self, text="频率 (Frequency) / Speed Bin", padding=5)
        frame.pack(fill=tk.X, padx=5, pady=5)

        # ---- Speed Bin 选择行 ----
        ttk.Label(frame, text="Speed Bin:").grid(
            row=0, column=0, sticky=tk.W, padx=2, pady=2)

        self._speed_bin_var = tk.StringVar(value="")
        self._speed_bin_combo = ttk.Combobox(frame, textvariable=self._speed_bin_var,
                                values=[""], state='readonly', width=16)
        self._speed_bin_combo.grid(row=0, column=1, sticky=tk.W, padx=2, pady=2)
        self._speed_bin_combo.bind('<<ComboboxSelected>>', self._on_speed_bin_selected)

        ttk.Button(frame, text="Apply", width=6,
                   command=self._on_apply_speed_bin).grid(
            row=0, column=2, sticky=tk.W, padx=2, pady=2)

        ttk.Label(frame, text="选择 Speed Bin 后点击 Apply 自动填充参数",
                  foreground='gray').grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)

        # ---- Min Cycle Time ----
        ttk.Label(frame, text="Min Cycle Time (ps):").grid(
            row=1, column=0, sticky=tk.W, padx=2, pady=2)

        v_mct = tk.IntVar(value=0)
        self._vars['min_cycle_time'] = v_mct
        v_mct.trace_add('write', self._on_timing_changed)

        vcmd = (self.register(lambda P: _on_spinbox_validate_int(P, 1, 65535)), '%P')
        sb = ttk.Spinbox(frame, textvariable=v_mct, width=10,
                         from_=1, to=65535, validate='key',
                         validatecommand=vcmd)
        sb.grid(row=1, column=1, sticky=tk.W, padx=2, pady=2)

        # 频率显示 (只读)
        self._freq_var = tk.StringVar(value="")
        self._mt_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self._freq_var, width=16).grid(
            row=1, column=2, padx=5, pady=2)
        ttk.Label(frame, textvariable=self._mt_var, width=16).grid(
            row=1, column=3, padx=5, pady=2)

    def _build_type_specific(self):
        """根据 DDR 类型重建 CAS 和时序区域。"""
        # 清除旧内容
        if self._cas_frame:
            self._cas_frame.destroy()
        if self._timing_frame:
            self._timing_frame.destroy()
        self._cl_vars.clear()

        if self.app.spd_type == 'ddr4':
            self._build_cas_ddr4()
            self._build_timings_ddr4()
        else:
            self._build_cas_ddr5()
            self._build_timings_ddr5()

    def _build_cas_ddr5(self):
        """DDR5 CAS Latency (CL20-CL98, 7×6 网格)。"""
        self._cas_frame = ttk.Labelframe(self, text="支持的 CAS Latency", padding=5)
        self._cas_frame.pack(fill=tk.X, padx=5, pady=5)
        for i, cl in enumerate(ALL_CL_VALUES):
            row, col = i // 12, i % 12
            var = tk.BooleanVar(value=False)
            var.trace_add('write', self._on_cl_changed)
            self._cl_vars[cl] = var
            cb = ttk.Checkbutton(self._cas_frame, text=str(cl), variable=var)
            cb.grid(row=row, column=col, sticky=tk.W, padx=2, pady=1)

    def _build_cas_ddr4(self):
        """DDR4 CAS Latency (CL7-CL36, 4×8 网格)。"""
        from ddr4_spd_model import ALL_DDR4_CL_VALUES
        self._cas_frame = ttk.Labelframe(self, text="支持的 CAS Latency (DDR4)", padding=5)
        self._cas_frame.pack(fill=tk.X, padx=5, pady=5)
        for i, cl in enumerate(ALL_DDR4_CL_VALUES):
            row, col = i // 12, i % 12
            var = tk.BooleanVar(value=False)
            var.trace_add('write', self._on_cl_changed)
            self._cl_vars[cl] = var
            cb = ttk.Checkbutton(self._cas_frame, text=str(cl), variable=var)
            cb.grid(row=row, column=col, sticky=tk.W, padx=2, pady=1)

    def _build_timings_ddr5(self):
        """DDR5 时序参数表。"""
        frame = ttk.Labelframe(self, text="时序参数 (Timings) - DDR5", padding=5)
        frame.pack(fill=tk.X, padx=5, pady=5)
        self._timing_frame = frame

        ttk.Label(frame, text="参数名", font=('', 9, 'bold')).grid(row=0, column=0, padx=2, pady=1, sticky=tk.W)
        ttk.Label(frame, text="值 (ps)", font=('', 9, 'bold')).grid(row=0, column=1, padx=2, pady=1)
        ttk.Label(frame, text="Ticks", font=('', 9, 'bold')).grid(row=0, column=2, padx=2, pady=1)
        ttk.Label(frame, text="", font=('', 9, 'bold')).grid(row=0, column=3, padx=10)
        ttk.Label(frame, text="参数名", font=('', 9, 'bold')).grid(row=0, column=4, padx=2, pady=1, sticky=tk.W)
        ttk.Label(frame, text="值 (ps)", font=('', 9, 'bold')).grid(row=0, column=5, padx=2, pady=1)
        ttk.Label(frame, text="Lower Limit", font=('', 9, 'bold')).grid(row=0, column=6, padx=2, pady=1)
        ttk.Label(frame, text="Ticks", font=('', 9, 'bold')).grid(row=0, column=7, padx=2, pady=1)

        vcmd_spin = (self.register(lambda P: _on_spinbox_validate_int(P, 1, 65535)), '%P')
        vcmd_limit = (self.register(lambda P: _on_spinbox_validate_int(P, 0, 255)), '%P')

        left = [('tAA', 'tAA', False), ('tRCD', 'tRCD', False), ('tRP', 'tRP', False),
                ('tRAS', 'tRAS', False), ('tRC', 'tRC', False), ('tWR', 'tWR', False),
                ('tRFC1_slr', 'tRFC1_slr', False), ('tRFC2_slr', 'tRFC2_slr', False),
                ('tRFCsb_slr', 'tRFCsb_slr', False)]
        right = [('tRRD_L', 'tRRD_L', True), ('tCCD_L', 'tCCD_L', True),
                 ('tCCD_L_WR', 'tCCD_L_WR', True), ('tCCD_L_WR2', 'tCCD_L_WR2', True),
                 ('tFAW', 'tFAW', True), ('tCCD_L_WTR', 'tCCD_L_WTR', True),
                 ('tCCD_S_WTR', 'tCCD_S_WTR', True), ('tRTP', 'tRTP', True)]

        for idx, (name, attr, has_limit) in enumerate(left):
            row = idx + 1
            ttk.Label(frame, text=f"{name}:", width=14).grid(row=row, column=0, sticky=tk.W, padx=1, pady=1)
            var = tk.IntVar(value=0); var.trace_add('write', self._on_timing_changed)
            self._vars[attr] = var
            ttk.Spinbox(frame, textvariable=var, width=10, from_=1, to=65535, validate='key', validatecommand=vcmd_spin).grid(row=row, column=1, padx=1, pady=1)
            tick_var = tk.StringVar(value="0"); self._vars[f"{attr}_ticks"] = tick_var
            ttk.Label(frame, textvariable=tick_var, width=6).grid(row=row, column=2, padx=1, pady=1)

        for idx, (name, attr, has_limit) in enumerate(right):
            row = idx + 1
            ttk.Label(frame, text=f"{name}:", width=14).grid(row=row, column=4, sticky=tk.W, padx=1, pady=1)
            var = tk.IntVar(value=0); var.trace_add('write', self._on_timing_changed)
            self._vars[attr] = var
            ttk.Spinbox(frame, textvariable=var, width=10, from_=1, to=65535, validate='key', validatecommand=vcmd_spin).grid(row=row, column=5, padx=1, pady=1)
            if has_limit:
                limit_var = tk.IntVar(value=0); limit_var.trace_add('write', self._on_timing_changed)
                self._vars[f"{attr}_lower_limit"] = limit_var
                ttk.Spinbox(frame, textvariable=limit_var, width=6, from_=0, to=255, validate='key', validatecommand=vcmd_limit).grid(row=row, column=6, padx=1, pady=1)
            tick_var = tk.StringVar(value="0"); self._vars[f"{attr}_ticks"] = tick_var
            ttk.Label(frame, textvariable=tick_var, width=6).grid(row=row, column=7, padx=1, pady=1)

    def _build_timings_ddr4(self):
        """DDR4 时序参数表 (MTB ticks + ns 显示)。"""
        frame = ttk.Labelframe(self, text="时序参数 (Timings) - DDR4 (MTB=0.125ns)", padding=5)
        frame.pack(fill=tk.X, padx=5, pady=5)
        self._timing_frame = frame

        headers = [("参数名", 0), ("Ticks", 1), ("时间 (ns)", 2), ("", 3),
                   ("参数名", 4), ("Ticks", 5), ("时间 (ns)", 6)]
        for text, col in headers:
            ttk.Label(frame, text=text, font=('', 9, 'bold')).grid(row=0, column=col, padx=2, pady=1, sticky=tk.W)

        vcmd = (self.register(lambda P: _on_spinbox_validate_int(P, 0, 65535)), '%P')

        left = [('tAA (CL)', 'cl_ticks'), ('tRCD', 'rcd_ticks'), ('tRP', 'rp_ticks'),
                ('tRAS', 'ras_ticks'), ('tRC', 'rc_ticks'), ('tWR', 'wr_ticks'),
                ('tRFC1', 'rfc1_ticks'), ('tRFC2', 'rfc2_ticks'), ('tRFC4', 'rfc4_ticks')]
        right = [('tRRD_S', 'rrds_ticks'), ('tRRD_L', 'rrdl_ticks'), ('tCCD_L', 'ccdl_ticks'),
                 ('tFAW', 'faw_ticks'), ('tWTR_S', 'wtrs_ticks'), ('tWTR_L', 'wtrl_ticks')]

        for idx, (name, attr) in enumerate(left):
            row = idx + 1
            ttk.Label(frame, text=f"{name}:", width=14).grid(row=row, column=0, sticky=tk.W, padx=1, pady=1)
            var = tk.IntVar(value=0); var.trace_add('write', self._on_timing_changed)
            self._vars[attr] = var
            ttk.Spinbox(frame, textvariable=var, width=8, from_=0, to=65535, validate='key', validatecommand=vcmd).grid(row=row, column=1, padx=1, pady=1)
            ns_var = tk.StringVar(value="0"); self._vars[f"{attr}_ns"] = ns_var
            ttk.Label(frame, textvariable=ns_var, width=8).grid(row=row, column=2, padx=1, pady=1)

        for idx, (name, attr) in enumerate(right):
            row = idx + 1
            ttk.Label(frame, text=f"{name}:", width=14).grid(row=row, column=4, sticky=tk.W, padx=1, pady=1)
            var = tk.IntVar(value=0); var.trace_add('write', self._on_timing_changed)
            self._vars[attr] = var
            ttk.Spinbox(frame, textvariable=var, width=8, from_=0, to=65535, validate='key', validatecommand=vcmd).grid(row=row, column=5, padx=1, pady=1)
            ns_var = tk.StringVar(value="0"); self._vars[f"{attr}_ns"] = ns_var
            ttk.Label(frame, textvariable=ns_var, width=8).grid(row=row, column=6, padx=1, pady=1)

    # ---- Speed Bin 回调 ----

    def _update_speed_bin_list(self):
        """根据 DDR 类型更新 Speed Bin 列表。"""
        if self.app.spd_type == 'ddr4':
            from ddr4_spd_model import DDR4_SPEED_BINS
            bins = DDR4_SPEED_BINS
        else:
            from ddr5_spd_model import DDR5_SPEED_BINS
            bins = DDR5_SPEED_BINS
        names = [""] + sorted(bins.keys())
        self._speed_bin_combo['values'] = names

    def _on_speed_bin_selected(self, event=None):
        """Speed Bin 下拉框选择事件（仅更新预览，不应用）。"""
        pass  # 用户需点击 Apply 按钮确认

    def _on_apply_speed_bin(self):
        """应用 Speed Bin 参数到 SPD (DDR4/DDR5 自动判断)。"""
        bin_name = self._speed_bin_var.get()
        if not bin_name:
            messagebox.showwarning("提示", "请先选择一个 Speed Bin。")
            return

        if self.spd is None:
            return

        if self.app.spd_type == 'ddr4':
            from ddr4_spd_model import apply_ddr4_speed_bin
            applied = apply_ddr4_speed_bin(self.spd, bin_name)
        else:
            from ddr5_spd_model import apply_speed_bin
            applied = apply_speed_bin(self.spd, bin_name)

        if applied:
            self.load_spd(self.spd)

    # ---- 数据加载与同步 ----

    def load_spd(self, spd):
        """从 SPD 模型加载数据到 UI (兼容 DDR4/DDR5)。"""
        self.spd = spd
        self._setting_vars = True
        try:
            # 频率 (DDR4=ticks, DDR5=ps)
            if hasattr(spd, 'min_cycle_time'):
                self._vars['min_cycle_time'].set(spd.min_cycle_time)
            else:
                self._vars['min_cycle_time'].set(spd.min_cycle_ticks)

            # CAS Latency
            from ddr4_spd_model import ALL_DDR4_CL_VALUES
            cl_list = ALL_DDR4_CL_VALUES if self.app.spd_type == 'ddr4' else ALL_CL_VALUES
            for cl in cl_list:
                if cl in self._cl_vars:
                    self._cl_vars[cl].set(spd.is_cl_supported(cl))

            # 时序: DDR4 用 ticks 字段, DDR5 用 ps 字段
            if self.app.spd_type == 'ddr4':
                for attr in ['cl_ticks', 'rcd_ticks', 'rp_ticks', 'ras_ticks', 'rc_ticks',
                             'wr_ticks', 'rfc1_ticks', 'rfc2_ticks', 'rfc4_ticks',
                             'rrds_ticks', 'rrdl_ticks', 'ccdl_ticks',
                             'faw_ticks', 'wtrs_ticks', 'wtrl_ticks']:
                    if attr in self._vars and hasattr(spd, attr):
                        self._vars[attr].set(getattr(spd, attr))
            else:
                for attr in ['tAA', 'tRCD', 'tRP', 'tRAS', 'tRC', 'tWR',
                             'tRFC1_slr', 'tRFC2_slr', 'tRFCsb_slr',
                             'tRRD_L', 'tCCD_L', 'tCCD_L_WR', 'tCCD_L_WR2',
                             'tFAW', 'tCCD_L_WTR', 'tCCD_S_WTR', 'tRTP']:
                    if attr in self._vars:
                        self._vars[attr].set(getattr(spd, attr))
                    limit_attr = f"{attr}_lower_limit"
                    if limit_attr in self._vars:
                        self._vars[limit_attr].set(getattr(spd, limit_attr))
        finally:
            self._setting_vars = False

        self._update_computed()

    def _update_computed(self):
        """更新计算值（频率、ticks/ns）。"""
        if self.spd is None:
            return

        mct = getattr(self.spd, 'min_cycle_time', 0) or getattr(self.spd, 'min_cycle_ticks', 0)
        if self.app.spd_type == 'ddr4':
            from ddr4_spd_model import MTB_NS
            mct_ns = self.spd.min_cycle_ticks * MTB_NS if hasattr(self.spd, 'min_cycle_ticks') else 0
            mct_ps = mct_ns * 1000
            freq_str = f"{1.0 / mct_ns:.3f} MHz" if mct_ns > 0 else "N/A"
            mt_str = f"{2.0 / mct_ns:.3f} MT/s" if mct_ns > 0 else "N/A"
            self._freq_var.set(freq_str)
            self._mt_var.set(mt_str)
            # DDR4: ticks → ns
            for key in ['cl_ticks', 'rcd_ticks', 'rp_ticks', 'ras_ticks', 'rc_ticks',
                        'wr_ticks', 'rfc1_ticks', 'rfc2_ticks', 'rfc4_ticks',
                        'rrds_ticks', 'rrdl_ticks', 'ccdl_ticks',
                        'faw_ticks', 'wtrs_ticks', 'wtrl_ticks']:
                ns_key = f"{key}_ns"
                if ns_key in self._vars and key in self._vars:
                    ticks = self._vars[key].get()
                    self._vars[ns_key].set(f"{ticks * MTB_NS:.2f}")
        else:
            freq_str, mt_str = format_frequency(mct)
            self._freq_var.set(freq_str)
            self._mt_var.set(mt_str)
            tick_map = {
                'tAA_ticks': 'tAA_ticks', 'tRCD_ticks': 'tRCD_ticks',
                'tRP_ticks': 'tRP_ticks', 'tRAS_ticks': 'tRAS_ticks',
                'tRC_ticks': 'tRC_ticks', 'tWR_ticks': 'tWR_ticks',
                'tRFC1_slr_ticks': 'tRFC1_slr_ticks', 'tRFC2_slr_ticks': 'tRFC2_slr_ticks',
                'tRFCsb_slr_ticks': 'tRFCsb_slr_ticks', 'tRRD_L_ticks': 'tRRD_L_ticks',
                'tCCD_L_ticks': 'tCCD_L_ticks', 'tCCD_L_WR_ticks': 'tCCD_L_WR_ticks',
                'tCCD_L_WR2_ticks': 'tCCD_L_WR2_ticks', 'tFAW_ticks': 'tFAW_ticks',
                'tCCD_L_WTR_ticks': 'tCCD_L_WTR_ticks', 'tCCD_S_WTR_ticks': 'tCCD_S_WTR_ticks',
                'tRTP_ticks': 'tRTP_ticks'}
            for var_key, attr in tick_map.items():
                if var_key in self._vars:
                    self._vars[var_key].set(str(getattr(self.spd, attr)))

    def _on_cl_changed(self, *args):
        """CAS Latency 复选框变更回调。"""
        if self._setting_vars or self.spd is None:
            return
        for cl, var in self._cl_vars.items():
            self.spd.set_cl_supported(cl, var.get())

    def _on_timing_changed(self, *args):
        """时序参数变更回调（延迟计算提升性能）。"""
        if self._setting_vars or self.spd is None:
            return

        # Min Cycle Time
        if self.app.spd_type == 'ddr4':
            if 'min_cycle_time' in self._vars and hasattr(self.spd, 'min_cycle_ticks'):
                from ddr4_spd_model import MTB_NS
                self.spd.min_cycle_ticks = int(self._vars['min_cycle_time'].get() / 1000 / MTB_NS + 0.5)
            # DDR4 ticks 直接写入
            for attr in ['cl_ticks', 'rcd_ticks', 'rp_ticks', 'ras_ticks', 'rc_ticks',
                         'wr_ticks', 'rfc1_ticks', 'rfc2_ticks', 'rfc4_ticks',
                         'rrds_ticks', 'rrdl_ticks', 'ccdl_ticks',
                         'faw_ticks', 'wtrs_ticks', 'wtrl_ticks']:
                if attr in self._vars and hasattr(self.spd, attr):
                    setattr(self.spd, attr, self._vars[attr].get())
        else:
            self.spd.min_cycle_time = self._vars['min_cycle_time'].get()
            timing_attrs = [
                'tAA', 'tRCD', 'tRP', 'tRAS', 'tRC', 'tWR',
                'tRFC1_slr', 'tRFC2_slr', 'tRFCsb_slr',
                'tRRD_L', 'tCCD_L', 'tCCD_L_WR', 'tCCD_L_WR2',
                'tFAW', 'tCCD_L_WTR', 'tCCD_S_WTR', 'tRTP',
        ]

        for attr in timing_attrs:
            if attr in self._vars:
                setattr(self.spd, attr, self._vars[attr].get())
            limit_attr = f"{attr}_lower_limit"
            if limit_attr in self._vars:
                setattr(self.spd, limit_attr, self._vars[limit_attr].get())

        # 延迟计算，合并多次变更
        if getattr(self, '_update_job', None):
            self.after_cancel(self._update_job)
        self._update_job = self.after(30, self._update_computed)


# =============================================================================
# XMPTabFrame — XMP 3.0 Profile 编辑页
# =============================================================================

class XMPTabFrame(ttk.Frame):
    """XMP 3.0 Profile 编辑标签页。每个 XMP Profile 一个实例。

    包含:
      - Profile 名称
      - 频率 + 命令速率
      - 电压 (VDD, VDDQ, VPP, VMEMCTRL)
      - CAS Latency 复选框
      - 时序参数
    """

    def __init__(self, parent, app, profile_no: int, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.profile_no = profile_no
        self.spd: DDR5_SPD = None
        self.xmp: XMP_3_0 = None

        self._vars: dict = {}
        self._cl_vars: dict = {}
        self._setting_vars = False

        self._build_ui()

    def _build_ui(self):
        self._build_profile_group()
        self._build_frequency_group()
        self._voltage_frame = None
        self._cas_frame = None
        self._timing_frame = None
        self._build_type_specific()

    def _build_type_specific(self):
        """根据 DDR 类型重建电压、CAS 和时序区域。"""
        if self._voltage_frame:
            self._voltage_frame.destroy()
        if self._cas_frame:
            self._cas_frame.destroy()
        if self._timing_frame:
            self._timing_frame.destroy()
        # 清除旧 vars
        for k in list(self._vars.keys()):
            if k not in ('min_cycle_time',):
                del self._vars[k]
        self._cl_vars.clear()
        if self.app.spd_type == 'ddr4':
            self._build_voltage_ddr4()
            self._build_cas_ddr4()
            self._build_timings_ddr4()
        else:
            self._build_voltage_ddr5()
            self._build_cas_ddr5()
            self._build_timings_ddr5()

    def _build_profile_group(self):
        """Profile 名称区域。"""
        frame = ttk.Labelframe(self, text="Profile 信息", padding=5)
        frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(frame, text="Profile 名称:").grid(
            row=0, column=0, sticky=tk.W, padx=2, pady=2)
        self._name_var = tk.StringVar(value="")
        self._name_var.trace_add('write', self._on_name_changed)
        self._name_entry = ttk.Entry(frame, textvariable=self._name_var,
                                     width=20)
        self._name_entry.grid(row=0, column=1, sticky=tk.W, padx=2, pady=2)

    def _build_frequency_group(self):
        """频率 + 命令速率设置。"""
        frame = ttk.Labelframe(self, text="频率 (Frequency) / Speed Bin", padding=5)
        frame.pack(fill=tk.X, padx=5, pady=5)

        # ---- Speed Bin 选择行 ----
        ttk.Label(frame, text="Speed Bin:").grid(
            row=0, column=0, sticky=tk.W, padx=2, pady=2)

        self._speed_bin_var = tk.StringVar(value="")
        self._speed_bin_combo = ttk.Combobox(frame, textvariable=self._speed_bin_var,
                                values=[""], state='readonly', width=16)
        self._speed_bin_combo.grid(row=0, column=1, sticky=tk.W, padx=2, pady=2)

        ttk.Button(frame, text="Apply", width=6,
                   command=self._on_apply_speed_bin).grid(
            row=0, column=2, sticky=tk.W, padx=2, pady=2)

        # ---- Min Cycle Time ----
        ttk.Label(frame, text="Min Cycle Time (ps):").grid(
            row=1, column=0, sticky=tk.W, padx=2, pady=2)

        v_mct = tk.IntVar(value=0)
        v_mct.trace_add('write', self._on_data_changed)
        self._vars['min_cycle_time'] = v_mct

        vcmd = (self.register(lambda P: _on_spinbox_validate_int(P, 1, 65535)), '%P')
        sb = ttk.Spinbox(frame, textvariable=v_mct, width=10,
                         from_=1, to=65535, validate='key',
                         validatecommand=vcmd)
        sb.grid(row=1, column=1, sticky=tk.W, padx=2, pady=2)

        # 频率显示
        self._freq_var = tk.StringVar(value="")
        self._mt_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self._freq_var, width=16).grid(
            row=1, column=2, padx=5, pady=2)
        ttk.Label(frame, textvariable=self._mt_var, width=16).grid(
            row=1, column=3, padx=5, pady=2)

        # 命令速率
        ttk.Label(frame, text="命令速率:").grid(
            row=2, column=0, sticky=tk.W, padx=2, pady=2)
        self._cmd_rate_var = tk.StringVar(value="Undefined")
        self._cmd_rate_var.trace_add('write', self._on_cmd_rate_changed)
        cr_combo = ttk.Combobox(frame, textvariable=self._cmd_rate_var,
                                values=["Undefined", "1N", "2N", "3N"],
                                state='readonly', width=10)
        cr_combo.grid(row=2, column=1, sticky=tk.W, padx=2, pady=2)

        # Intel Dynamic Memory Boost
        self._dmb_var = tk.BooleanVar(value=False)
        self._dmb_var.trace_add('write', self._on_data_changed)
        ttk.Checkbutton(frame, text="Intel Dynamic Memory Boost",
                        variable=self._dmb_var).grid(
            row=3, column=0, columnspan=3, sticky=tk.W, padx=2, pady=1)

        # Real-time Memory Frequency OC
        self._rtoc_var = tk.BooleanVar(value=False)
        self._rtoc_var.trace_add('write', self._on_data_changed)
        ttk.Checkbutton(frame, text="Realtime Memory Frequency OC",
                        variable=self._rtoc_var).grid(
            row=4, column=0, columnspan=3, sticky=tk.W, padx=2, pady=1)

    def _build_voltage_ddr5(self):
        """DDR5 电压 (VDD, VDDQ, VPP, VMEMCTRL)。"""
        self._voltage_frame = ttk.Labelframe(self, text="电压 (Voltages) - DDR5", padding=5)
        self._voltage_frame.pack(fill=tk.X, padx=5, pady=5)
        voltages = [("VDD:", 'vdd'), ("VDDQ:", 'vddq'), ("VPP:", 'vpp'), ("VMEMCTRL:", 'vmemctrl')]
        vcmd = (self.register(lambda P: _on_spinbox_validate_int(P, 110, 300)), '%P')
        for i, (label, key) in enumerate(voltages):
            col = i * 2
            ttk.Label(self._voltage_frame, text=label).grid(row=0, column=col, sticky=tk.W, padx=2, pady=2)
            var = tk.IntVar(value=110)
            var.trace_add('write', self._on_data_changed)
            self._vars[key] = var
            ttk.Spinbox(self._voltage_frame, textvariable=var, width=7, from_=110, to=300, validate='key', validatecommand=vcmd).grid(row=0, column=col + 1, sticky=tk.W, padx=2, pady=2)

    def _build_voltage_ddr4(self):
        """DDR4 电压 (仅 VDD, 默认 1.20V)。"""
        self._voltage_frame = ttk.Labelframe(self, text="电压 (Voltage) - DDR4", padding=5)
        self._voltage_frame.pack(fill=tk.X, padx=5, pady=5)
        vcmd = (self.register(lambda P: _on_spinbox_validate_int(P, 110, 300)), '%P')
        ttk.Label(self._voltage_frame, text="VDD:").grid(row=0, column=0, sticky=tk.W, padx=2, pady=2)
        var = tk.IntVar(value=120)
        var.trace_add('write', self._on_data_changed)
        self._vars['vdd'] = var
        ttk.Spinbox(self._voltage_frame, textvariable=var, width=7, from_=110, to=300, validate='key', validatecommand=vcmd).grid(row=0, column=1, sticky=tk.W, padx=2, pady=2)

    def _build_cas_ddr5(self):
        """DDR5 CAS (CL20-CL98)。"""
        self._cas_frame = ttk.Labelframe(self, text="支持的 CAS Latency", padding=5)
        self._cas_frame.pack(fill=tk.X, padx=5, pady=5)
        for i, cl in enumerate(ALL_CL_VALUES):
            row, col = i // 12, i % 12
            var = tk.BooleanVar(value=False)
            var.trace_add('write', self._on_data_changed)
            self._cl_vars[cl] = var
            ttk.Checkbutton(self._cas_frame, text=str(cl), variable=var).grid(row=row, column=col, sticky=tk.W, padx=2, pady=1)

    def _build_cas_ddr4(self):
        """DDR4 CAS (CL7-CL36)。"""
        from ddr4_spd_model import ALL_DDR4_CL_VALUES
        self._cas_frame = ttk.Labelframe(self, text="支持的 CAS Latency (DDR4)", padding=5)
        self._cas_frame.pack(fill=tk.X, padx=5, pady=5)
        for i, cl in enumerate(ALL_DDR4_CL_VALUES):
            row, col = i // 12, i % 12
            var = tk.BooleanVar(value=False)
            var.trace_add('write', self._on_data_changed)
            self._cl_vars[cl] = var
            ttk.Checkbutton(self._cas_frame, text=str(cl), variable=var).grid(row=row, column=col, sticky=tk.W, padx=2, pady=1)

    def _build_timings_ddr5(self):
        """DDR5 XMP 时序参数。"""
        self._timing_frame = ttk.Labelframe(self, text="时序参数 (Timings) - DDR5", padding=5)
        self._timing_frame.pack(fill=tk.X, padx=5, pady=5)
        frame = self._timing_frame

        # 标题
        ttk.Label(frame, text="参数名", font=('', 9, 'bold')).grid(
            row=0, column=0, padx=2, pady=1, sticky=tk.W)
        ttk.Label(frame, text="值 (ps)", font=('', 9, 'bold')).grid(
            row=0, column=1, padx=2, pady=1)
        ttk.Label(frame, text="Ticks", font=('', 9, 'bold')).grid(
            row=0, column=2, padx=2, pady=1)
        ttk.Label(frame, text="", font=('', 9, 'bold')).grid(
            row=0, column=3, padx=10)
        ttk.Label(frame, text="参数名", font=('', 9, 'bold')).grid(
            row=0, column=4, padx=2, pady=1, sticky=tk.W)
        ttk.Label(frame, text="值 (ps)", font=('', 9, 'bold')).grid(
            row=0, column=5, padx=2, pady=1)
        ttk.Label(frame, text="Lower Limit", font=('', 9, 'bold')).grid(
            row=0, column=6, padx=2, pady=1)
        ttk.Label(frame, text="Ticks", font=('', 9, 'bold')).grid(
            row=0, column=7, padx=2, pady=1)

        vcmd_spin = (self.register(
            lambda P: _on_spinbox_validate_int(P, 1, 65535)), '%P')
        vcmd_limit = (self.register(
            lambda P: _on_spinbox_validate_int(P, 0, 255)), '%P')

        left_timings = [
            ("tAA", "tAA"),
            ("tRCD", "tRCD"),
            ("tRP", "tRP"),
            ("tRAS", "tRAS"),
            ("tRC", "tRC"),
            ("tWR", "tWR"),
            ("tRFC1", "tRFC1"),
            ("tRFC2", "tRFC2"),
            ("tRFCsb", "tRFC"),
        ]

        right_timings = [
            ("tRRD_L", "tRRD_L"),
            ("tCCD_L", "tCCD_L"),
            ("tCCD_L_WR", "tCCD_L_WR"),
            ("tCCD_L_WR2", "tCCD_L_WR2"),
            ("tFAW", "tFAW"),
            ("tCCD_L_WTR", "tCCD_L_WTR"),
            ("tCCD_S_WTR", "tCCD_S_WTR"),
            ("tRTP", "tRTP"),
        ]

        for idx, (name, attr) in enumerate(left_timings):
            row = idx + 1
            ttk.Label(frame, text=f"{name}:", width=14).grid(
                row=row, column=0, sticky=tk.W, padx=1, pady=1)

            var = tk.IntVar(value=0)
            var.trace_add('write', self._on_data_changed)
            self._vars[attr] = var
            sb = ttk.Spinbox(frame, textvariable=var, width=10,
                             from_=1, to=65535, validate='key',
                             validatecommand=vcmd_spin)
            sb.grid(row=row, column=1, padx=1, pady=1)

            tick_var = tk.StringVar(value="0")
            self._vars[f"{attr}_ticks"] = tick_var
            ttk.Label(frame, textvariable=tick_var, width=6).grid(
                row=row, column=2, padx=1, pady=1)

        for idx, (name, attr) in enumerate(right_timings):
            row = idx + 1
            ttk.Label(frame, text=f"{name}:", width=14).grid(
                row=row, column=4, sticky=tk.W, padx=1, pady=1)

            var = tk.IntVar(value=0)
            var.trace_add('write', self._on_data_changed)
            self._vars[attr] = var
            sb = ttk.Spinbox(frame, textvariable=var, width=10,
                             from_=1, to=65535, validate='key',
                             validatecommand=vcmd_spin)
            sb.grid(row=row, column=5, padx=1, pady=1)

            limit_var = tk.IntVar(value=0)
            limit_var.trace_add('write', self._on_data_changed)
            self._vars[f"{attr}_lower_limit"] = limit_var
            sb_l = ttk.Spinbox(frame, textvariable=limit_var, width=6,
                               from_=0, to=255, validate='key',
                               validatecommand=vcmd_limit)
            sb_l.grid(row=row, column=6, padx=1, pady=1)

            tick_var = tk.StringVar(value="0")
            self._vars[f"{attr}_ticks"] = tick_var
            ttk.Label(frame, textvariable=tick_var, width=6).grid(
                row=row, column=7, padx=1, pady=1)

    def _build_timings_ddr4(self):
        """DDR4 XMP 时序参数 (ticks + ns)。"""
        self._timing_frame = ttk.Labelframe(self, text="时序参数 (Timings) - DDR4 (MTB=0.125ns)", padding=5)
        self._timing_frame.pack(fill=tk.X, padx=5, pady=5)
        frame = self._timing_frame

        headers = [("参数名", 0), ("Ticks", 1), ("时间 (ns)", 2), ("", 3),
                   ("参数名", 4), ("Ticks", 5), ("时间 (ns)", 6)]
        for text, col in headers:
            ttk.Label(frame, text=text, font=('', 9, 'bold')).grid(row=0, column=col, padx=2, pady=1, sticky=tk.W)

        vcmd = (self.register(lambda P: _on_spinbox_validate_int(P, 0, 65535)), '%P')

        left = [('tAA (CL)', 'cl_ticks'), ('tRCD', 'rcd_ticks'), ('tRP', 'rp_ticks'),
                ('tRAS', 'ras_ticks'), ('tRC', 'rc_ticks'), ('tWR', 'wr_ticks'),
                ('tRFC1', 'rfc1_ticks'), ('tRFC2', 'rfc2_ticks'), ('tRFC4', 'rfc4_ticks')]
        right = [('tRRD_S', 'rrds_ticks'), ('tRRD_L', 'rrdl_ticks'),
                 ('tFAW', 'faw_ticks')]

        from ddr4_spd_model import MTB_NS
        for idx, (name, attr) in enumerate(left):
            row = idx + 1
            ttk.Label(frame, text=f"{name}:", width=14).grid(row=row, column=0, sticky=tk.W, padx=1, pady=1)
            var = tk.IntVar(value=0); var.trace_add('write', self._on_data_changed)
            self._vars[attr] = var
            ttk.Spinbox(frame, textvariable=var, width=8, from_=0, to=65535, validate='key', validatecommand=vcmd).grid(row=row, column=1, padx=1, pady=1)
            ns_var = tk.StringVar(value="0"); self._vars[f"{attr}_ns"] = ns_var
            ttk.Label(frame, textvariable=ns_var, width=8).grid(row=row, column=2, padx=1, pady=1)

        for idx, (name, attr) in enumerate(right):
            row = idx + 1
            ttk.Label(frame, text=f"{name}:", width=14).grid(row=row, column=4, sticky=tk.W, padx=1, pady=1)
            var = tk.IntVar(value=0); var.trace_add('write', self._on_data_changed)
            self._vars[attr] = var
            ttk.Spinbox(frame, textvariable=var, width=8, from_=0, to=65535, validate='key', validatecommand=vcmd).grid(row=row, column=5, padx=1, pady=1)
            ns_var = tk.StringVar(value="0"); self._vars[f"{attr}_ns"] = ns_var
            ttk.Label(frame, textvariable=ns_var, width=8).grid(row=row, column=6, padx=1, pady=1)

    # ---- 数据加载 ----

    def load_spd(self, spd: DDR5_SPD):
        """从 SPD 加载 XMP Profile 数据。"""
        self.spd = spd
        if hasattr(self, '_update_speed_bin_list'):
            self._update_speed_bin_list()
        profile_map = {
            1: spd.xmp1, 2: spd.xmp2, 3: spd.xmp3,
            4: spd.xmp_user1, 5: spd.xmp_user2,
        }
        self.xmp = profile_map.get(self.profile_no)
        if self.xmp is None:
            return

        self._setting_vars = True
        try:
            # Profile 名称
            name_map = {
                1: lambda: spd.xmp_profile1_name,
                2: lambda: spd.xmp_profile2_name,
                3: lambda: spd.xmp_profile3_name,
                4: lambda: "User Profile 1",
                5: lambda: "User Profile 2",
            }
            self._name_var.set(name_map.get(self.profile_no,
                                             lambda: "")())

            # 频率
            self._vars['min_cycle_time'].set(self.xmp.min_cycle_time)

            # 命令速率
            cr_map = {0: "Undefined", 1: "1N", 2: "2N", 3: "3N"}
            self._cmd_rate_var.set(cr_map.get(
                int(self.xmp.command_rate), "Undefined"))

            # 特性
            self._dmb_var.set(self.xmp.intel_dynamic_memory_boost)
            self._rtoc_var.set(self.xmp.realtime_memory_frequency_oc)

            # 电压
            if self.app.spd_type == 'ddr4':
                if 'vdd' in self._vars:
                    self._vars['vdd'].set(getattr(self.xmp, 'vdd', 120))
            else:
                for key in ['vdd', 'vddq', 'vpp', 'vmemctrl']:
                    if key in self._vars:
                        self._vars[key].set(getattr(self.xmp, key))

            # CAS Latency
            if self.app.spd_type == 'ddr4':
                from ddr4_spd_model import ALL_DDR4_CL_VALUES
                cl_list = ALL_DDR4_CL_VALUES
            else:
                cl_list = ALL_CL_VALUES
            for cl in cl_list:
                if cl in self._cl_vars:
                    if self.app.spd_type == 'ddr4':
                        self._cl_vars[cl].set(self.xmp.is_cl_supported(cl))
                    else:
                        self._cl_vars[cl].set(is_cl_supported_xmp(self.xmp, cl))

            # 时序
            if self.app.spd_type == 'ddr4':
                for attr in ['cl_ticks', 'rcd_ticks', 'rp_ticks', 'ras_ticks', 'rc_ticks',
                             'wr_ticks', 'rfc1_ticks', 'rfc2_ticks', 'rfc4_ticks',
                             'rrds_ticks', 'rrdl_ticks', 'faw_ticks']:
                    if attr in self._vars and hasattr(self.xmp, attr):
                        self._vars[attr].set(getattr(self.xmp, attr))
            else:
                for attr in ['tAA', 'tRCD', 'tRP', 'tRAS', 'tRC', 'tWR',
                             'tRFC1', 'tRFC2', 'tRFC',
                             'tRRD_L', 'tCCD_L', 'tCCD_L_WR', 'tCCD_L_WR2',
                             'tFAW', 'tCCD_L_WTR', 'tCCD_S_WTR', 'tRTP']:
                    if attr in self._vars:
                        self._vars[attr].set(getattr(self.xmp, attr))
                    limit_attr = f"{attr}_lower_limit"
                    if limit_attr in self._vars:
                        self._vars[limit_attr].set(getattr(self.xmp, limit_attr, 0))

            # 名称编辑可用性
            if self.xmp.is_user_profile():
                self._name_entry.configure(state='disabled')
            else:
                self._name_entry.configure(state='normal')
        finally:
            self._setting_vars = False

        self._update_computed()

    def _update_computed(self):
        """更新计算值。"""
        if self.xmp is None:
            return

        mct = self.xmp.min_cycle_time
        freq_str, mt_str = format_frequency(mct)
        self._freq_var.set(freq_str)
        self._mt_var.set(mt_str)

        tick_attrs = [
            'tAA_ticks', 'tRCD_ticks', 'tRP_ticks', 'tRAS_ticks',
            'tRC_ticks', 'tWR_ticks', 'tRFC1_ticks', 'tRFC2_ticks',
            'tRFC_ticks', 'tRRD_L_ticks', 'tCCD_L_ticks',
            'tCCD_L_WR_ticks', 'tCCD_L_WR2_ticks', 'tFAW_ticks',
            'tCCD_L_WTR_ticks', 'tCCD_S_WTR_ticks', 'tRTP_ticks',
        ]

        for attr in tick_attrs:
            if attr in self._vars:
                self._vars[attr].set(str(getattr(self.xmp, attr)))

    # ---- 事件回调 ----

    def _on_data_changed(self, *args):
        """通用数据变更回调。"""
        if self._setting_vars or self.xmp is None:
            return

        # Min Cycle Time
        self.xmp.min_cycle_time = self._vars['min_cycle_time'].get()

        # 特性
        self.xmp.intel_dynamic_memory_boost = self._dmb_var.get()
        self.xmp.realtime_memory_frequency_oc = self._rtoc_var.get()

        # 电压
        if self.app.spd_type == 'ddr4':
            if 'vdd' in self._vars:
                self.xmp.vdd = self._vars['vdd'].get()
        else:
            for key in ['vdd', 'vddq', 'vpp', 'vmemctrl']:
                if key in self._vars:
                    setattr(self.xmp, key, self._vars[key].get())

        # CAS Latency（直接通过 XMP 内部方法写入原始 bytearray）
        for cl, var in self._cl_vars.items():
            try:
                set_cl_supported_xmp(self.xmp, cl, var.get())
            except ValueError:
                pass

        # 时序
        if self.app.spd_type == 'ddr4':
            for attr in ['cl_ticks', 'rcd_ticks', 'rp_ticks', 'ras_ticks', 'rc_ticks',
                         'wr_ticks', 'rfc1_ticks', 'rfc2_ticks', 'rfc4_ticks',
                         'rrds_ticks', 'rrdl_ticks', 'faw_ticks']:
                if attr in self._vars and hasattr(self.xmp, attr):
                    setattr(self.xmp, attr, self._vars[attr].get())
        else:
            for attr in ['tAA', 'tRCD', 'tRP', 'tRAS', 'tRC', 'tWR',
                         'tRFC1', 'tRFC2', 'tRFC',
                         'tRRD_L', 'tCCD_L', 'tCCD_L_WR', 'tCCD_L_WR2',
                         'tFAW', 'tCCD_L_WTR', 'tCCD_S_WTR', 'tRTP']:
                if attr in self._vars:
                    setattr(self.xmp, attr, self._vars[attr].get())
                limit_attr = f"{attr}_lower_limit"
                if limit_attr in self._vars:
                    setattr(self.xmp, limit_attr, self._vars[limit_attr].get())

        if getattr(self, '_update_job', None):
            self.after_cancel(self._update_job)
        self._update_job = self.after(30, self._update_computed)

    def _on_name_changed(self, *args):
        """Profile 名称变更。"""
        if self._setting_vars or self.spd is None or self.xmp is None:
            return
        if self.xmp.is_user_profile():
            return
        name = self._name_var.get()
        name_map = {
            1: lambda v: setattr(self.spd, 'xmp_profile1_name', v),
            2: lambda v: setattr(self.spd, 'xmp_profile2_name', v),
            3: lambda v: setattr(self.spd, 'xmp_profile3_name', v),
        }
        fn = name_map.get(self.profile_no)
        if fn:
            fn(name)

    def _update_speed_bin_list(self):
        if self.app.spd_type == 'ddr4':
            from ddr4_spd_model import DDR4_SPEED_BINS
            bins = DDR4_SPEED_BINS
        else:
            from ddr5_spd_model import DDR5_SPEED_BINS
            bins = DDR5_SPEED_BINS
        names = [""] + sorted(bins.keys())
        self._speed_bin_combo['values'] = names

    def _on_apply_speed_bin(self):
        """应用 Speed Bin 到当前 XMP Profile。"""
        bin_name = self._speed_bin_var.get()
        if not bin_name:
            messagebox.showwarning("提示", "请先选择一个 Speed Bin。")
            return
        if self.xmp is None or self.spd is None:
            return
        if self.app.spd_type == 'ddr4':
            from ddr4_spd_model import apply_ddr4_speed_bin_to_xmp
            applied = apply_ddr4_speed_bin_to_xmp(self.xmp, bin_name)
        else:
            from ddr5_spd_model import apply_speed_bin_to_xmp
            applied = apply_speed_bin_to_xmp(self.xmp, bin_name)
        if applied:
            self.spd.update_crc()
            self.load_spd(self.spd)

    def _on_cmd_rate_changed(self, *args):
        """命令速率变更。"""
        if self._setting_vars or self.xmp is None:
            return
        cr_map = {"Undefined": 0, "1N": 1, "2N": 2, "3N": 3}
        val = cr_map.get(self._cmd_rate_var.get(), 0)
        self.xmp.command_rate = CommandRate(val)


# ---- XMP CAS 辅助 ----

def is_cl_supported_xmp(xmp: XMP_3_0, cl: int) -> bool:
    """检查 XMP Profile 的 CL 支持（避免重复导入 ddr5_utils）。"""
    from ddr5_utils import is_cl_supported
    cl_bytes = xmp._data[xmp._O_CL_SUPPORTED:
                         xmp._O_CL_SUPPORTED + 5]
    return is_cl_supported(cl_bytes, cl)


def set_cl_supported_xmp(xmp: XMP_3_0, cl: int, supported: bool):
    """设置 XMP Profile 的 CL 支持（直接在原始数据上操作）。"""
    xmp._set_cl(cl, supported)


# =============================================================================
# EXPOTabFrame — EXPO Profile 编辑页
# =============================================================================

class EXPOTabFrame(ttk.Frame):
    """EXPO Profile 编辑标签页。"""

    def __init__(self, parent, app, profile_no: int, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.profile_no = profile_no
        self.spd: DDR5_SPD = None
        self.expo: EXPO = None

        self._vars: dict = {}
        self._setting_vars = False

        self._build_ui()

    def _build_ui(self):
        self._build_frequency_group()
        self._build_voltage_group()
        self._build_timings_group()

    def _build_frequency_group(self):
        """频率设置。"""
        frame = ttk.Labelframe(self, text="频率 (Frequency) / Speed Bin", padding=5)
        frame.pack(fill=tk.X, padx=5, pady=5)

        # ---- Speed Bin 选择行 ----
        ttk.Label(frame, text="Speed Bin:").grid(
            row=0, column=0, sticky=tk.W, padx=2, pady=2)

        self._speed_bin_var = tk.StringVar(value="")
        self._speed_bin_combo = ttk.Combobox(frame, textvariable=self._speed_bin_var,
                                values=[""], state='readonly', width=16)
        self._speed_bin_combo.grid(row=0, column=1, sticky=tk.W, padx=2, pady=2)

        ttk.Button(frame, text="Apply", width=6,
                   command=self._on_apply_speed_bin).grid(
            row=0, column=2, sticky=tk.W, padx=2, pady=2)

        # ---- Min Cycle Time ----
        ttk.Label(frame, text="Min Cycle Time (ps):").grid(
            row=1, column=0, sticky=tk.W, padx=2, pady=2)

        v_mct = tk.IntVar(value=0)
        v_mct.trace_add('write', self._on_data_changed)
        self._vars['min_cycle_time'] = v_mct

        vcmd = (self.register(lambda P: _on_spinbox_validate_int(P, 1, 65535)), '%P')
        sb = ttk.Spinbox(frame, textvariable=v_mct, width=10,
                         from_=1, to=65535, validate='key',
                         validatecommand=vcmd)
        sb.grid(row=1, column=1, sticky=tk.W, padx=2, pady=2)

        self._freq_var = tk.StringVar(value="")
        self._mt_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self._freq_var, width=16).grid(
            row=1, column=2, padx=5, pady=2)
        ttk.Label(frame, textvariable=self._mt_var, width=16).grid(
            row=1, column=3, padx=5, pady=2)

    def _build_voltage_group(self):
        """电压设置。"""
        frame = ttk.Labelframe(self, text="电压 (Voltages)", padding=5)
        frame.pack(fill=tk.X, padx=5, pady=5)

        voltages = [("VDD:", 'vdd'), ("VDDQ:", 'vddq'), ("VPP:", 'vpp')]

        vcmd = (self.register(lambda P: _on_spinbox_validate_int(P, 110, 240)), '%P')

        for i, (label, key) in enumerate(voltages):
            col = i * 2
            ttk.Label(frame, text=label).grid(
                row=0, column=col, sticky=tk.W, padx=2, pady=2)
            var = tk.IntVar(value=110)
            var.trace_add('write', self._on_data_changed)
            self._vars[key] = var
            sb = ttk.Spinbox(frame, textvariable=var, width=7,
                             from_=110, to=240, validate='key',
                             validatecommand=vcmd)
            sb.grid(row=0, column=col + 1, sticky=tk.W, padx=2, pady=2)

    def _build_timings_group(self):
        """时序参数。"""
        frame = ttk.Labelframe(self, text="时序参数 (Timings)", padding=5)
        frame.pack(fill=tk.X, padx=5, pady=5)

        # 标题
        ttk.Label(frame, text="参数名", font=('', 9, 'bold')).grid(
            row=0, column=0, padx=2, pady=1, sticky=tk.W)
        ttk.Label(frame, text="值 (ps)", font=('', 9, 'bold')).grid(
            row=0, column=1, padx=2, pady=1)
        ttk.Label(frame, text="Ticks", font=('', 9, 'bold')).grid(
            row=0, column=2, padx=2, pady=1)
        ttk.Label(frame, text="", font=('', 9, 'bold')).grid(
            row=0, column=3, padx=10)
        ttk.Label(frame, text="参数名", font=('', 9, 'bold')).grid(
            row=0, column=4, padx=2, pady=1, sticky=tk.W)
        ttk.Label(frame, text="值 (ps)", font=('', 9, 'bold')).grid(
            row=0, column=5, padx=2, pady=1)
        ttk.Label(frame, text="Ticks", font=('', 9, 'bold')).grid(
            row=0, column=6, padx=2, pady=1)

        vcmd_spin = (self.register(
            lambda P: _on_spinbox_validate_int(P, 1, 65535)), '%P')

        left_timings = [
            ("tAA", "tAA"), ("tRCD", "tRCD"), ("tRP", "tRP"),
            ("tRAS", "tRAS"), ("tRC", "tRC"), ("tWR", "tWR"),
            ("tRFC1", "tRFC1"), ("tRFC2", "tRFC2"), ("tRFCsb", "tRFC"),
        ]

        right_timings = [
            ("tRRD_L", "tRRD_L"), ("tCCD_L", "tCCD_L"),
            ("tCCD_L_WR", "tCCD_L_WR"), ("tCCD_L_WR2", "tCCD_L_WR2"),
            ("tFAW", "tFAW"), ("tCCD_L_WTR", "tCCD_L_WTR"),
            ("tCCD_S_WTR", "tCCD_S_WTR"), ("tRTP", "tRTP"),
        ]

        for idx, (name, attr) in enumerate(left_timings):
            row = idx + 1
            ttk.Label(frame, text=f"{name}:", width=14).grid(
                row=row, column=0, sticky=tk.W, padx=1, pady=1)

            var = tk.IntVar(value=0)
            var.trace_add('write', self._on_data_changed)
            self._vars[attr] = var
            sb = ttk.Spinbox(frame, textvariable=var, width=10,
                             from_=1, to=65535, validate='key',
                             validatecommand=vcmd_spin)
            sb.grid(row=row, column=1, padx=1, pady=1)

            tick_var = tk.StringVar(value="0")
            self._vars[f"{attr}_ticks"] = tick_var
            ttk.Label(frame, textvariable=tick_var, width=6).grid(
                row=row, column=2, padx=1, pady=1)

        for idx, (name, attr) in enumerate(right_timings):
            row = idx + 1
            ttk.Label(frame, text=f"{name}:", width=14).grid(
                row=row, column=4, sticky=tk.W, padx=1, pady=1)

            var = tk.IntVar(value=0)
            var.trace_add('write', self._on_data_changed)
            self._vars[attr] = var
            sb = ttk.Spinbox(frame, textvariable=var, width=10,
                             from_=1, to=65535, validate='key',
                             validatecommand=vcmd_spin)
            sb.grid(row=row, column=5, padx=1, pady=1)

            tick_var = tk.StringVar(value="0")
            self._vars[f"{attr}_ticks"] = tick_var
            ttk.Label(frame, textvariable=tick_var, width=6).grid(
                row=row, column=6, padx=1, pady=1)

    # ---- 数据加载 ----

    def load_spd(self, spd: DDR5_SPD):
        """从 SPD 加载 EXPO Profile 数据。"""
        self.spd = spd
        if hasattr(self, '_update_speed_bin_list'):
            self._update_speed_bin_list()
        profile_map = {1: spd.expo1, 2: spd.expo2}
        self.expo = profile_map.get(self.profile_no)
        if self.expo is None:
            return

        self._setting_vars = True
        try:
            self._vars['min_cycle_time'].set(self.expo.min_cycle_time)

            for key in ['vdd', 'vddq', 'vpp']:
                if key in self._vars:
                    self._vars[key].set(getattr(self.expo, key))

            timing_attrs = [
                'tAA', 'tRCD', 'tRP', 'tRAS', 'tRC', 'tWR',
                'tRFC1', 'tRFC2', 'tRFC',
                'tRRD_L', 'tCCD_L', 'tCCD_L_WR', 'tCCD_L_WR2',
                'tFAW', 'tCCD_L_WTR', 'tCCD_S_WTR', 'tRTP',
            ]
            for attr in timing_attrs:
                if attr in self._vars:
                    self._vars[attr].set(getattr(self.expo, attr))
        finally:
            self._setting_vars = False

        self._update_computed()

    def _update_speed_bin_list(self):
        from ddr5_spd_model import DDR5_SPEED_BINS
        names = [""] + sorted(DDR5_SPEED_BINS.keys())
        self._speed_bin_combo['values'] = names

    def _on_apply_speed_bin(self):
        """应用 Speed Bin 到当前 EXPO Profile。"""
        bin_name = self._speed_bin_var.get()
        if not bin_name:
            messagebox.showwarning("提示", "请先选择一个 Speed Bin。")
            return
        if self.expo is None or self.spd is None:
            return
        from ddr5_spd_model import apply_speed_bin_to_expo
        if apply_speed_bin_to_expo(self.expo, bin_name):
            self.spd.update_crc()
            self.load_spd(self.spd)
            # Speed Bin 已应用

    def _update_computed(self):
        """更新计算值。"""
        if self.expo is None:
            return

        mct = self.expo.min_cycle_time
        freq_str, mt_str = format_frequency(mct)
        self._freq_var.set(freq_str)
        self._mt_var.set(mt_str)

        tick_attrs = [
            'tAA_ticks', 'tRCD_ticks', 'tRP_ticks', 'tRAS_ticks',
            'tRC_ticks', 'tWR_ticks', 'tRFC1_ticks', 'tRFC2_ticks',
            'tRFC_ticks', 'tRRD_L_ticks', 'tCCD_L_ticks',
            'tCCD_L_WR_ticks', 'tCCD_L_WR2_ticks', 'tFAW_ticks',
            'tCCD_L_WTR_ticks', 'tCCD_S_WTR_ticks', 'tRTP_ticks',
        ]
        for attr in tick_attrs:
            if attr in self._vars:
                self._vars[attr].set(str(getattr(self.expo, attr)))

    def _on_data_changed(self, *args):
        """数据变更回调。"""
        if self._setting_vars or self.expo is None:
            return

        self.expo.min_cycle_time = self._vars['min_cycle_time'].get()

        for key in ['vdd', 'vddq', 'vpp']:
            if key in self._vars:
                setattr(self.expo, key, self._vars[key].get())

        timing_attrs = [
            'tAA', 'tRCD', 'tRP', 'tRAS', 'tRC', 'tWR',
            'tRFC1', 'tRFC2', 'tRFC',
            'tRRD_L', 'tCCD_L', 'tCCD_L_WR', 'tCCD_L_WR2',
            'tFAW', 'tCCD_L_WTR', 'tCCD_S_WTR', 'tRTP',
        ]
        for attr in timing_attrs:
            if attr in self._vars:
                setattr(self.expo, attr, self._vars[attr].get())

        if getattr(self, '_update_job', None):
            self.after_cancel(self._update_job)
        self._update_job = self.after(30, self._update_computed)


# =============================================================================
# MiscTabFrame — 杂项设置页
# =============================================================================

class MiscTabFrame(ttk.Frame):
    """杂项设置标签页。

    包含:
      - 物理特性 (Form Factor)
      - 密度/Downbin (Density, Bank Groups, Addressing)
      - 模组组织 (Device Width)
      - 模组信息 (制造年份/周数/料号/散热片)
      - XMP Profile 复制
      - XMP Profile 导入/导出
    """

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.spd: DDR5_SPD = None

        self._vars: dict = {}
        self._setting_vars = False

        self._build_ui()

    def _build_ui(self):
        """构建杂项设置 UI。"""
        # 使用 Canvas + Scrollbar 支持滚动
        canvas = tk.Canvas(self, width=480, height=600)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self._scroll_frame = scroll_frame

        self._build_physical_group(scroll_frame)
        self._build_density_group(scroll_frame)
        self._build_module_org_group(scroll_frame)
        self._build_module_info_group(scroll_frame)
        self._build_copy_xmp_group(scroll_frame)
        self._build_import_export_group(scroll_frame)

    def _build_physical_group(self, parent):
        """物理特性。"""
        frame = ttk.Labelframe(parent, text="物理特性 (Physical)", padding=5)
        frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(frame, text="Form Factor:").grid(
            row=0, column=0, sticky=tk.W, padx=2, pady=2)

        ff_names = [f.name for f in FORM_FACTOR_MAP]
        self._ff_var = tk.StringVar(value="UDIMM")
        self._ff_var.trace_add('write', self._on_form_factor_changed)
        combo = ttk.Combobox(frame, textvariable=self._ff_var,
                             values=ff_names, state='readonly', width=14)
        combo.grid(row=0, column=1, sticky=tk.W, padx=2, pady=2)

    def _build_density_group(self, parent):
        """密度/Downbin 设置。"""
        frame = ttk.Labelframe(parent, text="密度 / Downbin", padding=5)
        frame.pack(fill=tk.X, padx=5, pady=5)

        # Density
        ttk.Label(frame, text="Density:").grid(
            row=0, column=0, sticky=tk.W, padx=2, pady=2)

        density_names = [d.name for d in DENSITY_MAP]
        self._density_var = tk.StringVar(value="_0Gb")
        self._density_var.trace_add('write', self._on_density_changed)
        combo = ttk.Combobox(frame, textvariable=self._density_var,
                             values=density_names, state='readonly', width=10)
        combo.grid(row=0, column=1, sticky=tk.W, padx=2, pady=2)

        # Bank Groups
        ttk.Label(frame, text="Bank Groups:").grid(
            row=1, column=0, sticky=tk.W, padx=2, pady=2)
        self._bank_groups_var = tk.IntVar(value=4)
        self._bank_groups_var.trace_add('write', self._on_data_changed)
        combo = ttk.Combobox(frame, textvariable=self._bank_groups_var,
                             values=BANK_GROUPS_MAP, state='readonly', width=10)
        combo.grid(row=1, column=1, sticky=tk.W, padx=2, pady=2)

        # Banks per Bank Group
        ttk.Label(frame, text="Banks per Bank Group:").grid(
            row=2, column=0, sticky=tk.W, padx=2, pady=2)
        self._bpb_var = tk.IntVar(value=4)
        self._bpb_var.trace_add('write', self._on_data_changed)
        combo = ttk.Combobox(frame, textvariable=self._bpb_var,
                             values=BANKS_PER_BANK_GROUP_MAP,
                             state='readonly', width=10)
        combo.grid(row=2, column=1, sticky=tk.W, padx=2, pady=2)

        # Column Addresses
        ttk.Label(frame, text="Column Addresses:").grid(
            row=3, column=0, sticky=tk.W, padx=2, pady=2)
        self._col_addr_var = tk.IntVar(value=10)
        self._col_addr_var.trace_add('write', self._on_data_changed)
        combo = ttk.Combobox(frame, textvariable=self._col_addr_var,
                             values=COLUMN_ADDRESS_MAP,
                             state='readonly', width=10)
        combo.grid(row=3, column=1, sticky=tk.W, padx=2, pady=2)

        # Row Addresses
        ttk.Label(frame, text="Row Addresses:").grid(
            row=4, column=0, sticky=tk.W, padx=2, pady=2)
        self._row_addr_var = tk.IntVar(value=16)
        self._row_addr_var.trace_add('write', self._on_data_changed)
        combo = ttk.Combobox(frame, textvariable=self._row_addr_var,
                             values=ROW_ADDRESS_MAP,
                             state='readonly', width=10)
        combo.grid(row=4, column=1, sticky=tk.W, padx=2, pady=2)

    def _build_module_org_group(self, parent):
        """模组组织。"""
        frame = ttk.Labelframe(parent, text="模组组织 (Module Organization)",
                               padding=5)
        frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(frame, text="Device Width:").grid(
            row=0, column=0, sticky=tk.W, padx=2, pady=2)
        self._dev_width_var = tk.IntVar(value=8)
        self._dev_width_var.trace_add('write', self._on_data_changed)
        combo = ttk.Combobox(frame, textvariable=self._dev_width_var,
                             values=DEVICE_WIDTH_MAP,
                             state='readonly', width=10)
        combo.grid(row=0, column=1, sticky=tk.W, padx=2, pady=2)

    def _build_module_info_group(self, parent):
        """模组信息。"""
        frame = ttk.Labelframe(parent, text="模组信息 (Module Info)", padding=5)
        frame.pack(fill=tk.X, padx=5, pady=5)

        vcmd_year = (self.register(
            lambda P: _on_spinbox_validate_int(P, 0, 99)), '%P')
        vcmd_week = (self.register(
            lambda P: _on_spinbox_validate_int(P, 0, 52)), '%P')

        ttk.Label(frame, text="制造年份:").grid(
            row=0, column=0, sticky=tk.W, padx=2, pady=2)
        self._year_var = tk.IntVar(value=0)
        self._year_var.trace_add('write', self._on_data_changed)
        ttk.Spinbox(frame, textvariable=self._year_var, width=8,
                    from_=0, to=99, validate='key',
                    validatecommand=vcmd_year).grid(
            row=0, column=1, sticky=tk.W, padx=2, pady=2)

        ttk.Label(frame, text="制造周数:").grid(
            row=1, column=0, sticky=tk.W, padx=2, pady=2)
        self._week_var = tk.IntVar(value=0)
        self._week_var.trace_add('write', self._on_data_changed)
        ttk.Spinbox(frame, textvariable=self._week_var, width=8,
                    from_=0, to=52, validate='key',
                    validatecommand=vcmd_week).grid(
            row=1, column=1, sticky=tk.W, padx=2, pady=2)

        ttk.Label(frame, text="料号 (Part Number):").grid(
            row=2, column=0, sticky=tk.W, padx=2, pady=2)
        self._pn_var = tk.StringVar(value="")
        self._pn_var.trace_add('write', self._on_data_changed)
        ttk.Entry(frame, textvariable=self._pn_var, width=24).grid(
            row=2, column=1, sticky=tk.W, padx=2, pady=2)

        self._hs_var = tk.BooleanVar(value=False)
        self._hs_var.trace_add('write', self._on_data_changed)
        ttk.Checkbutton(frame, text="安装散热片 (Heat Spreader)",
                        variable=self._hs_var).grid(
            row=3, column=0, columnspan=2, sticky=tk.W, padx=2, pady=2)

    def _build_copy_xmp_group(self, parent):
        """XMP Profile 复制。"""
        frame = ttk.Labelframe(parent, text="复制 XMP Profile", padding=5)
        frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(frame, text="源 (Source):").grid(
            row=0, column=0, sticky=tk.W, padx=2, pady=2)
        self._src_var = tk.IntVar(value=1)
        combo = ttk.Combobox(frame, textvariable=self._src_var,
                             values=[1, 2, 3, 4, 5],
                             state='readonly', width=5)
        combo.grid(row=0, column=1, sticky=tk.W, padx=2, pady=2)

        ttk.Label(frame, text="目标 (Target):").grid(
            row=0, column=2, sticky=tk.W, padx=2, pady=2)
        self._tgt_var = tk.IntVar(value=2)
        combo = ttk.Combobox(frame, textvariable=self._tgt_var,
                             values=[1, 2, 3, 4, 5],
                             state='readonly', width=5)
        combo.grid(row=0, column=3, sticky=tk.W, padx=2, pady=2)

        ttk.Button(frame, text="复制 (Copy)",
                   command=self._on_copy_xmp).grid(
            row=0, column=4, padx=10, pady=2)

    def _build_import_export_group(self, parent):
        """XMP Profile 导入/导出。"""
        frame = ttk.Labelframe(parent, text="导入/导出 XMP Profile", padding=5)
        frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(frame, text="Profile:").grid(
            row=0, column=0, sticky=tk.W, padx=2, pady=2)
        self._ie_var = tk.IntVar(value=1)
        combo = ttk.Combobox(frame, textvariable=self._ie_var,
                             values=[1, 2, 3, 4, 5],
                             state='readonly', width=5)
        combo.grid(row=0, column=1, sticky=tk.W, padx=2, pady=2)

        ttk.Button(frame, text="导入 (Import)",
                   command=self._on_import_xmp).grid(
            row=0, column=2, padx=5, pady=2)
        ttk.Button(frame, text="导出 (Export)",
                   command=self._on_export_xmp).grid(
            row=0, column=3, padx=5, pady=2)

    # ---- 数据加载 ----

    def load_spd(self, spd: DDR5_SPD):
        """从 SPD 加载杂项数据。"""
        self.spd = spd
        self._setting_vars = True
        try:
            if spd.form_factor is not None:
                ff = spd.form_factor
                self._ff_var.set(ff.name if hasattr(ff, 'name') else str(ff))
            if spd.density is not None:
                den = spd.density
                self._density_var.set(den.name if hasattr(den, 'name') else str(den))
            self._bank_groups_var.set(spd.bank_groups)
            self._bpb_var.set(spd.banks_per_bank_group)
            self._col_addr_var.set(spd.column_addresses)
            self._row_addr_var.set(spd.row_addresses)
            self._dev_width_var.set(spd.device_width)
            self._year_var.set(spd.manufacturing_year)
            self._week_var.set(spd.manufacturing_week)
            self._pn_var.set(spd.part_number)
            self._hs_var.set(spd.heat_spreader)
        finally:
            self._setting_vars = False

    # ---- 事件回调 ----

    def _on_form_factor_changed(self, *args):
        if self._setting_vars or self.spd is None:
            return
        if self.app.spd_type == 'ddr4':
            return  # DDR4 form factor 不支持 GUI 修改
        name = self._ff_var.get()
        for ff in FORM_FACTOR_MAP:
            if ff.name == name:
                self.spd.form_factor = ff
                break

    def _on_density_changed(self, *args):
        if self._setting_vars or self.spd is None:
            return
        if self.app.spd_type == 'ddr4':
            return
        name = self._density_var.get()
        for d in DENSITY_MAP:
            if d.name == name:
                self.spd.density = d
                break

    def _on_data_changed(self, *args):
        if self._setting_vars or self.spd is None:
            return
        self.spd.bank_groups = self._bank_groups_var.get()
        self.spd.banks_per_bank_group = self._bpb_var.get()
        self.spd.column_addresses = self._col_addr_var.get()
        self.spd.row_addresses = self._row_addr_var.get()
        self.spd.device_width = self._dev_width_var.get()
        self.spd.manufacturing_year = self._year_var.get()
        self.spd.manufacturing_week = self._week_var.get()
        self.spd.part_number = self._pn_var.get()
        self.spd.heat_spreader = self._hs_var.get()

    def _on_copy_xmp(self):
        """复制 XMP Profile。"""
        if self.spd is None:
            return
        src = self._src_var.get()
        tgt = self._tgt_var.get()
        if self.spd.copy_xmp_profile(src, tgt):
            self.app.refresh_all_tabs()
            messagebox.showinfo("复制成功", "XMP Profile 数据已成功复制。")
        else:
            messagebox.showerror("复制失败", "复制 XMP Profile 数据时出错。")

    def _on_export_xmp(self):
        """导出 XMP Profile。"""
        if self.spd is None:
            return
        profile_no = self._ie_var.get()
        self.spd.update_crc()

        profile_map = {
            1: (self.spd.xmp1, lambda: self.spd.xmp_profile1_name),
            2: (self.spd.xmp2, lambda: self.spd.xmp_profile2_name),
            3: (self.spd.xmp3, lambda: self.spd.xmp_profile3_name),
            4: (self.spd.xmp_user1, lambda: "User_1"),
            5: (self.spd.xmp_user2, lambda: "User_2"),
        }

        xmp, name_fn = profile_map.get(profile_no, (None, None))
        if xmp is None:
            return

        if not xmp.check_crc_validity() or xmp.is_empty():
            messagebox.showerror("导出失败", "XMP Profile 无效或为空，无法导出。")
            return

        filepath = filedialog.asksaveasfilename(
            title="导出 XMP 3.0 Profile",
            defaultextension=".bin",
            filetypes=[("XMP 3.0 files", "*.bin"), ("All files", "*.*")]
        )
        if filepath:
            try:
                with open(filepath, 'wb') as f:
                    f.write(xmp.get_bytes())
                messagebox.showinfo("导出成功",
                    f"XMP 3.0 Profile [{name_fn()}] 已成功保存到:\n{filepath}")
            except Exception as e:
                messagebox.showerror("导出失败", f"保存文件时出错:\n{e}")

    def _on_import_xmp(self):
        """导入 XMP Profile。"""
        if self.spd is None:
            return
        profile_no = self._ie_var.get()

        filepath = filedialog.askopenfilename(
            title="导入 XMP 3.0 Profile",
            filetypes=[("XMP 3.0 files", "*.bin"), ("All files", "*.*")]
        )
        if not filepath:
            return

        try:
            file_size = os.path.getsize(filepath)
            if file_size != XMP_3_0.SIZE:
                messagebox.showerror("导入失败",
                    f"文件大小必须为 {XMP_3_0.SIZE} 字节，实际为 {file_size} 字节。")
                return

            with open(filepath, 'rb') as f:
                data = f.read()

            xmp = XMP_3_0.parse(profile_no, data)
            if xmp is None:
                messagebox.showerror("导入失败", "无法解析 XMP 3.0 Profile。")
                return

            if not xmp.check_crc_validity():
                messagebox.showerror("导入失败",
                    "XMP 3.0 Profile 校验和无效。")
                return

            # 应用到 SPD
            if profile_no == 1:
                self.spd.xmp1 = xmp
                self.spd.xmp_profile1_name = "Imported"
                self.spd.xmp1_enabled = True
            elif profile_no == 2:
                self.spd.xmp2 = xmp
                self.spd.xmp_profile2_name = "Imported"
                self.spd.xmp2_enabled = True
            elif profile_no == 3:
                self.spd.xmp3 = xmp
                self.spd.xmp_profile3_name = "Imported"
                self.spd.xmp3_enabled = True
            elif profile_no == 4:
                self.spd.xmp_user1 = xmp
            elif profile_no == 5:
                self.spd.xmp_user2 = xmp

            self.app.refresh_all_tabs()
            messagebox.showinfo("导入成功", "XMP 3.0 Profile 已成功导入。")

        except Exception as e:
            messagebox.showerror("导入失败", f"读取文件时出错:\n{e}")


# =============================================================================
# DDR5XMPEditorApp — 主应用
# =============================================================================

class DDR5XMPEditorApp:
    """DDR XMP Editor Pro V1.0 — 周强  cnns@sina.com"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DDR XMP Editor Pro V1.0 — 周强  cnns@sina.com")
        self.root.geometry("820x750")
        self.root.minsize(780, 700)

        self.current_spd = None
        self.current_filepath: str = None
        self.spd_type = 'ddr5'  # 'ddr4' or 'ddr5'

        self._build_menu()
        self._build_main_area()

    # ---- 菜单栏 ----

    def _build_menu(self):
        """构建菜单栏。"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="打开 (Open)...", command=self._on_open,
                              accelerator="Ctrl+O")
        file_menu.add_command(label="保存 (Save)...", command=self._on_save,
                              accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="退出 (Exit)", command=self.root.quit)
        menubar.add_cascade(label="文件 (File)", menu=file_menu)

        # Help 菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="使用说明 (Help)", command=self._on_help)
        menubar.add_cascade(label="帮助 (Help)", menu=help_menu)

        # 快捷键
        self.root.bind('<Control-o>', lambda e: self._on_open())
        self.root.bind('<Control-s>', lambda e: self._on_save())

    # ---- 主区域 ----

    def _build_main_area(self):
        """构建主区域（Profile 启用 + 标签页）。"""
        main_frame = ttk.Frame(self.root, padding=5)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---- Profile 启用行 ----
        profile_frame = ttk.Frame(main_frame)
        profile_frame.pack(fill=tk.X, pady=(0, 5))

        self._xmp_enable_vars: dict[int, tk.BooleanVar] = {}
        self._xmp_checkbuttons: dict[int, ttk.Checkbutton] = {}
        xmp_labels = {
            1: "XMP 1", 2: "XMP 2", 3: "XMP 3",
            4: "XMP User 1", 5: "XMP User 2",
        }
        for i in range(1, 6):
            var = tk.BooleanVar(value=False)
            var.trace_add('write', lambda *a, n=i: self._on_profile_toggle(n))
            self._xmp_enable_vars[i] = var
            cb = ttk.Checkbutton(profile_frame, text=xmp_labels[i], variable=var)
            cb.pack(side=tk.LEFT, padx=3)
            self._xmp_checkbuttons[i] = cb

        # 分隔符
        self._expo_separator = ttk.Separator(profile_frame, orient=tk.VERTICAL)
        self._expo_separator.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)

        # EXPO 复选框
        self._expo_enable_vars: dict[int, tk.BooleanVar] = {}
        self._expo_checkbuttons: dict[int, ttk.Checkbutton] = {}
        for i in range(1, 3):
            var = tk.BooleanVar(value=False)
            var.trace_add('write', lambda *a, n=i: self._on_expo_toggle(n))
            self._expo_enable_vars[i] = var
            cb = ttk.Checkbutton(profile_frame, text=f"EXPO {i}", variable=var)
            cb.pack(side=tk.LEFT, padx=3)
            self._expo_checkbuttons[i] = cb

        # 文件名显示
        self._file_label_var = tk.StringVar(value="未打开文件")
        ttk.Label(profile_frame, text="  SPD 文件:").pack(side=tk.LEFT, padx=(15, 2))
        ttk.Label(profile_frame, textvariable=self._file_label_var).pack(
            side=tk.LEFT, padx=2)

        # ---- 标签页 ----
        self._notebook = ttk.Notebook(main_frame)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        # SPD 标签页
        self._spd_tab = SPDTabFrame(self._notebook, self)
        self._notebook.add(self._spd_tab, text="SPD")

        # XMP 标签页 (×5)
        self._xmp_tabs: list[XMPTabFrame] = []
        xmp_tab_names = ["XMP 1", "XMP 2", "XMP 3", "XMP User 1", "XMP User 2"]
        for i, name in enumerate(xmp_tab_names):
            tab = XMPTabFrame(self._notebook, self, profile_no=i + 1)
            self._xmp_tabs.append(tab)
            self._notebook.add(tab, text=name)

        # EXPO 标签页 (×2)
        self._expo_tabs: list[EXPOTabFrame] = []
        for i in range(2):
            tab = EXPOTabFrame(self._notebook, self, profile_no=i + 1)
            self._expo_tabs.append(tab)
            self._notebook.add(tab, text=f"EXPO {i + 1}")

        # Misc 标签页
        self._misc_tab = MiscTabFrame(self._notebook, self)
        self._notebook.add(self._misc_tab, text="杂项 (Misc)")

        # 启动时灰化所有 XMP/EXPO 标签页
        self.refresh_all_tabs()

    # ---- 文件操作 ----

    def _on_open(self):
        """打开 SPD 文件 (自动检测 DDR4/DDR5)。"""
        filepath = filedialog.askopenfilename(
            title="打开 SPD 文件",
            filetypes=[("SPD files", "*.spd *.bin"), ("All files", "*.*")]
        )
        if not filepath:
            return

        try:
            file_size = os.path.getsize(filepath)
            with open(filepath, 'rb') as f:
                data = f.read()

            # 检测 DDR 类型 (Byte 2)
            mem_type = data[2] if len(data) > 2 else 0

            if mem_type == 0x0C:  # DDR4
                if file_size < 512:
                    messagebox.showerror("错误", f"DDR4 SPD 至少需要 512 字节")
                    return
                data = data[:512]
                from ddr4_spd_model import DDR4_SPD
                spd = DDR4_SPD.parse(data)
                self.spd_type = 'ddr4'
            elif mem_type == 0x12:  # DDR5
                if file_size < 1024:
                    messagebox.showerror("错误", f"DDR5 SPD 至少需要 1024 字节")
                    return
                if len(data) > 1024:
                    data = data[:1024]
                spd = DDR5_SPD.parse(data)
                self.spd_type = 'ddr5'
            else:
                messagebox.showerror("错误",
                    f"未知内存类型 (Byte 2 = 0x{mem_type:02X})\n"
                    "支持: DDR4 (0x0C) / DDR5 (0x12)")
                return

            self.current_spd = spd
            self.current_filepath = filepath
            self._file_label_var.set(f"{os.path.basename(filepath)} [{self.spd_type.upper()}]")

            # 警告 EXPO (DDR5 only)
            if self.spd_type == 'ddr5' and spd.expo_found:
                messagebox.showwarning("EXPO 警告",
                    "检测到 EXPO 数据。\n\n当前对 EXPO 的支持仍处于实验阶段！")

            # 重建标签页
            self._rebuild_tabs()
            self.refresh_all_tabs()

        except ValueError as e:
            messagebox.showerror("解析错误", str(e))
        except Exception as e:
            messagebox.showerror("错误", f"打开文件时出错:\n{e}")

    def _on_save(self):
        """保存 SPD 文件。"""
        if self.current_spd is None:
            messagebox.showwarning("警告", "请先打开一个 SPD 文件。")
            return

        filepath = filedialog.asksaveasfilename(
            title="保存 DDR5 SPD 文件",
            defaultextension=".spd",
            filetypes=[("SPD files", "*.spd"), ("Binary files", "*.bin"),
                       ("All files", "*.*")]
        )
        if not filepath:
            return

        try:
            self.current_spd.update_crc()
            data = self.current_spd.get_bytes()
            with open(filepath, 'wb') as f:
                f.write(data)
            self.current_filepath = filepath
            self._file_label_var.set(os.path.basename(filepath))
            messagebox.showinfo("保存成功",
                f"DDR5 SPD 已成功保存到:\n{filepath}")
        except Exception as e:
            messagebox.showerror("保存失败", f"保存文件时出错:\n{e}")

    # ---- 帮助 ----

    def _on_help(self):
        """显示使用说明（自定义尺寸窗口）。"""
        help_text = (
            "DDR5 XMP Editor Pro V1.0\n"
            "DDR5 SPD 二进制文件编辑器 — 支持 XMP 3.0 / EXPO 配置\n"
            "作者: 周强  cnns@sina.com\n"
            "This is a fork of DDR5 XMP Editor\n\n"
            "——— 基本操作 ———\n\n"
            "1. 文件 → 打开: 打开 DDR5 SPD 二进制文件(.spd/.bin)\n"
            "   文件必须 ≥1024 字节，超长自动截取前 1KB\n\n"
            "2. 文件 → 保存: 保存修改后的 SPD 文件\n"
            "   CRC-16/XMODEM 校验和自动计算并更新\n\n"
            "——— SPD 标签页 ———\n\n"
            "• Speed Bin 下拉框: 选择 JEDEC 标准 Speed Bin\n"
            "  点击 Apply 自动填充频率、CAS Latency、全部时序参数\n"
            "• 频率: Min Cycle Time(ps) → 自动显示 MHz / MT/s\n"
            "• CAS Latency: 勾选支持的 CL 值 (CL20-CL98)\n"
            "• 时序参数: 左列为主时序，右列为第二时序+Lower Limit\n"
            "  Ticks 值根据 Min Cycle Time 自动计算\n\n"
            "——— XMP 标签页 (XMP 1-3, XMP User 1-2) ———\n\n"
            "• 勾选顶部复选框启用 Profile，取消勾选禁用\n"
            "• 禁用时标签页灰化不可编辑\n"
            "• Speed Bin: 选择后点 Apply 自动填充 Profile 参数\n"
            "• 电压单位: 110 = 1.10V, 135 = 1.35V\n"
            "• 命令速率: 1N / 2N / 3N\n\n"
            "——— EXPO 标签页 (EXPO 1-2) ———\n\n"
            "• 勾选顶部 EXPO 复选框自动创建 EXPO 数据块\n"
            "  取消双勾自动删除\n"
            "• EXPO 占用 SPD 0x340-0x3BF\n"
            "  与 XMP Profile 3 / User 1 冲突，会自动禁用\n"
            "• EXPO 不支持 CAS Latency / 命令速率\n\n"
            "——— 杂项 (Misc) 标签页 ———\n\n"
            "• Form Factor / Density / Bank Groups 等物理参数\n"
            "• 制造信息: 年份/周数/料号/散热片\n"
            "• XMP Profile 复制: 将源 Profile 复制到目标\n"
            "• XMP Profile 导入/导出: 单独的 64 字节 .bin 文件\n\n"
            "——— 快捷键 ———\n"
            "Ctrl+O: 打开文件    Ctrl+S: 保存文件\n\n"
            "——— SPD 空间分配 ———\n\n"
            "JEDEC 标准区域: 0x000-0x27F (640 bytes)\n"
            "XMP 3.0 区域:   0x280-0x3FF (384 bytes)\n"
            "  XMP Header:   0x280-0x2BF (64B)\n"
            "  XMP Profile 1: 0x2C0-0x2FF (64B)    XMP Profile 2: 0x300-0x33F (64B)\n"
            "  XMP Profile 3: 0x340-0x37F (64B) ← EXPO 冲突\n"
            "  XMP User 1:   0x380-0x3BF (64B) ← EXPO 冲突\n"
            "  XMP User 2:   0x3C0-0x3FF (64B)\n"
            "EXPO 区域:      0x340-0x3BF (128 bytes)\n"
            "  EXPO Header:  0x340-0x349 (10B)\n"
            "  EXPO Profile 1: 0x34A-0x371 (40B)  EXPO Profile 2: 0x372-0x399 (40B)\n"
            "  Filler + CRC: 0x39A-0x3BF (38B)\n"
        )

        win = tk.Toplevel(self.root)
        win.title("DDR5 XMP Editor Pro V1.0 — 使用说明")
        win.geometry("750x460")
        win.resizable(True, True)
        win.transient(self.root)
        win.grab_set()

        frame = ttk.Frame(win, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        text = tk.Text(frame, wrap=tk.WORD, font=('Microsoft YaHei', 10),
                       padx=6, pady=6)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)

        text.insert('1.0', help_text)
        text.configure(state='disabled')

        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(win, padding=5)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="关闭", command=win.destroy, width=10).pack(pady=4)

        win.wait_window()

    def _rebuild_tabs(self):
        """根据 SPD 类型重建标签页。"""
        # 清除旧标签页
        for tab in self._notebook.tabs():
            self._notebook.forget(tab)

        if self.spd_type == 'ddr4':
            # DDR4: 隐藏 XMP3/4/5 + EXPO 复选框
            for i in [3, 4, 5]:
                self._xmp_checkbuttons[i].pack_forget()
            for i in [1, 2]:
                self._xmp_checkbuttons[i].pack(side=tk.LEFT, padx=3)
                self._xmp_checkbuttons[i].lift()
            self._expo_separator.pack_forget()
            for i in [1, 2]:
                self._expo_checkbuttons[i].pack_forget()

            self._spd_tab = SPDTabFrame(self._notebook, self)
            self._notebook.add(self._spd_tab, text="SPD")

            self._xmp_tabs = []
            for i in range(2):
                tab = XMPTabFrame(self._notebook, self, profile_no=i + 1)
                self._xmp_tabs.append(tab)
                self._notebook.add(tab, text=f"XMP {i + 1}")

            self._expo_tabs = []

            self._misc_tab = MiscTabFrame(self._notebook, self)
            self._notebook.add(self._misc_tab, text="杂项 (Misc)")

            # 隐藏 EXPO 复选框
            for i in [1, 2]:
                self._expo_enable_vars[i].set(False)
        else:
            # DDR5: 显示所有复选框
            for i in range(1, 6):
                self._xmp_checkbuttons[i].pack(side=tk.LEFT, padx=3)
            self._expo_separator.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)
            for i in [1, 2]:
                self._expo_checkbuttons[i].pack(side=tk.LEFT, padx=3)

            self._spd_tab = SPDTabFrame(self._notebook, self)
            self._notebook.add(self._spd_tab, text="SPD")

            self._xmp_tabs = []
            xmp_names = ["XMP 1", "XMP 2", "XMP 3", "XMP User 1", "XMP User 2"]
            for i, name in enumerate(xmp_names):
                tab = XMPTabFrame(self._notebook, self, profile_no=i + 1)
                self._xmp_tabs.append(tab)
                self._notebook.add(tab, text=name)

            self._expo_tabs = []
            for i in range(2):
                tab = EXPOTabFrame(self._notebook, self, profile_no=i + 1)
                self._expo_tabs.append(tab)
                self._notebook.add(tab, text=f"EXPO {i + 1}")

            self._misc_tab = MiscTabFrame(self._notebook, self)
            self._notebook.add(self._misc_tab, text="杂项 (Misc)")

    # ---- Profile 切换 ----

    def _on_profile_toggle(self, profile_no: int):
        """XMP Profile 启用/禁用切换。"""
        if self.current_spd is None:
            return

        # 防止 refresh_all_tabs 同步复选框时触发递归
        if getattr(self, '_refreshing', False):
            return

        enabled = self._xmp_enable_vars[profile_no].get()

        if profile_no == 1:
            self.current_spd.xmp1_enabled = enabled
        elif profile_no == 2:
            self.current_spd.xmp2_enabled = enabled
        elif profile_no == 3:
            self.current_spd.xmp3_enabled = enabled
        elif profile_no == 4:
            self.current_spd.xmp_user1_enabled = enabled
        elif profile_no == 5:
            self.current_spd.xmp_user2_enabled = enabled

        self.refresh_all_tabs()

    def _on_expo_toggle(self, profile_no: int):
        """EXPO Profile 复选框切换：独立控制每个 Profile 的启用/禁用。"""
        if self.current_spd is None:
            return

        if getattr(self, '_refreshing', False):
            return

        enabled = self._expo_enable_vars[profile_no].get()
        spd = self.current_spd

        if enabled:
            # 勾选 → EXPO 不存在则创建，然后启用对应 profile
            if not spd.expo_found:
                spd.init_expo()
            if profile_no == 1:
                spd.expo1_enabled = True
            else:
                spd.expo2_enabled = True
        else:
            # 取消勾选 → 禁用对应 profile
            if not spd.expo_found:
                return
            if profile_no == 1:
                spd.expo1_enabled = False
            else:
                spd.expo2_enabled = False
            # 如果两个都禁用了，删除整个 EXPO 块
            if not spd.expo1_enabled and not spd.expo2_enabled:
                spd._expo_raw_data = bytearray(spd.EXPO_SIZE)
                spd.expo_found = False
                spd.expo1 = EXPO(1)
                spd.expo2 = EXPO(2)
                spd.xmp3 = XMP_3_0(3)
                spd.xmp_user1 = XMP_3_0(4)

        self.refresh_all_tabs()

    # ---- 刷新 ----

    def refresh_all_tabs(self):
        """刷新所有标签页的数据。"""
        if self.current_spd is None:
            for tab in self._xmp_tabs:
                set_children_state(tab, 'disabled')
            for tab in self._expo_tabs:
                set_children_state(tab, 'disabled')
            return

        spd = self.current_spd

        self._refreshing = True
        try:
            if self.spd_type == 'ddr5':
                self._xmp_enable_vars[1].set(spd.xmp1_enabled)
                self._xmp_enable_vars[2].set(spd.xmp2_enabled)
                self._xmp_enable_vars[3].set(spd.xmp3_enabled)
                self._xmp_enable_vars[4].set(spd.xmp_user1_enabled)
                self._xmp_enable_vars[5].set(spd.xmp_user2_enabled)
                self._expo_enable_vars[1].set(spd.expo1_enabled)
                self._expo_enable_vars[2].set(spd.expo2_enabled)
            else:  # DDR4
                self._xmp_enable_vars[1].set(spd.xmp1_enabled)
                self._xmp_enable_vars[2].set(spd.xmp2_enabled)
                self._expo_enable_vars[1].set(False)
                self._expo_enable_vars[2].set(False)
        finally:
            self._refreshing = False

        self._spd_tab.load_spd(spd)
        if hasattr(self._spd_tab, '_update_speed_bin_list'):
            self._spd_tab._update_speed_bin_list()

        if self.spd_type == 'ddr5':
            xmp_enabled = [
                spd.xmp1_enabled, spd.xmp2_enabled, spd.xmp3_enabled,
                spd.xmp_user1_enabled, spd.xmp_user2_enabled,
            ]
            for i, tab in enumerate(self._xmp_tabs):
                tab.load_spd(spd)
                set_children_state(tab, 'normal' if xmp_enabled[i] else 'disabled')
            expo_enabled = [spd.expo1_enabled, spd.expo2_enabled]
            for i, tab in enumerate(self._expo_tabs):
                tab.load_spd(spd)
                set_children_state(tab, 'normal' if expo_enabled[i] else 'disabled')
        else:  # DDR4
            ddr4_enabled = [spd.xmp1_enabled, spd.xmp2_enabled]
            for i, tab in enumerate(self._xmp_tabs):
                tab.load_spd(spd)
                set_children_state(tab, 'normal' if ddr4_enabled[i] else 'disabled')

        self._misc_tab.load_spd(spd)

    def run(self):
        """启动主事件循环。"""
        self.root.mainloop()


# =============================================================================
# 入口
# =============================================================================

def main():
    """主入口函数。"""
    app = DDR5XMPEditorApp()
    app.run()


if __name__ == '__main__':
    main()
