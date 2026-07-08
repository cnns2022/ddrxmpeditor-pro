#!/usr/bin/env python3
"""
DDR5 XMP Editor — SPD 数据模型模块
==================================
定义 DDR5_SPD、XMP_3_0、EXPO 类，负责 DDR5 SPD（1024 字节）的解析、编辑与序列化。

字节布局遵循 JEDEC 标准:
  - JESD 400-5C (DDR5 SPD Specification)
  - JEDEC 21-C Annex L

与 C# 原版 DDR5_SPD.cs / XMP_3_0.cs / EXPO.cs 功能完全一致。
"""

import enum
from ddr5_utils import (
    crc16_xmodem,
    bytes_to_ushort, ushort_to_bytes,
    time_to_ticks_ddr5,
    voltage_byte_to_mv, voltage_mv_to_byte,
    set_bit, get_bit,
    is_cl_supported, set_cl_supported,
)


# =============================================================================
# 枚举定义
# =============================================================================

class FormFactor(enum.IntEnum):
    """DDR5 模组类型 (SPD Byte 3 bits[3:0])"""
    RESERVED = 0
    RDIMM = 1
    UDIMM = 2
    SODIMM = 3
    LRDIMM = 4
    CUDIMM = 5
    CSODIMM = 6
    MRDIMM = 7
    CAMM2 = 8
    RESERVED_9 = 9
    DDIMM = 10
    SOLDER_DOWN = 11
    RESERVED_12 = 12
    RESERVED_13 = 13
    RESERVED_14 = 14
    RESERVED_15 = 15


FORM_FACTOR_MAP = [
    FormFactor.RESERVED,
    FormFactor.RDIMM,
    FormFactor.UDIMM,
    FormFactor.SODIMM,
    FormFactor.LRDIMM,
    FormFactor.CUDIMM,
    FormFactor.CSODIMM,
    FormFactor.MRDIMM,
    FormFactor.CAMM2,
    FormFactor.RESERVED_9,
    FormFactor.DDIMM,
    FormFactor.SOLDER_DOWN,
    FormFactor.RESERVED_12,
    FormFactor.RESERVED_13,
    FormFactor.RESERVED_14,
    FormFactor.RESERVED_15,
]


class Density(enum.IntEnum):
    """DDR5 DRAM 密度 (SPD Byte 4 bits[3:0])"""
    _0Gb = 0
    _4Gb = 1
    _8Gb = 2
    _12Gb = 3
    _16Gb = 4
    _24Gb = 5
    _32Gb = 6
    _48Gb = 7
    _64Gb = 8


DENSITY_MAP = [
    Density._0Gb, Density._4Gb, Density._8Gb,
    Density._12Gb, Density._16Gb, Density._24Gb,
    Density._32Gb, Density._48Gb, Density._64Gb,
]


class OperatingTempRange(enum.IntEnum):
    """DDR5 工作温度范围 (SPD Byte 233 bits[7:4])"""
    A1T = 0  # -40 to +125 °C
    A2T = 1  # -40 to +105 °C
    A3T = 2  # -40 to +85 °C
    IT = 3   # -40 to +95 °C
    ST = 4   # -25 to +85 °C
    ET = 5   # -25 to +105 °C
    RT = 6   # 0 to +45 °C
    NT = 7   # 0 to +85 °C
    XT = 8   # 0 to +95 °C


class CommandRate(enum.IntEnum):
    """XMP 3.0 命令速率"""
    UNDEFINED = 0
    N1 = 1
    N2 = 2
    N3 = 3


COMMAND_RATE_MAP = [
    CommandRate.UNDEFINED, CommandRate.N1, CommandRate.N2, CommandRate.N3
]

# =============================================================================
# 查找表
# =============================================================================

BANK_GROUPS_MAP = [1, 2, 4, 8]
BANKS_PER_BANK_GROUP_MAP = [1, 2, 4]
COLUMN_ADDRESS_MAP = [10, 11]
ROW_ADDRESS_MAP = [16, 17, 18]
DEVICE_WIDTH_MAP = [4, 8, 16, 32]

# 所有 DDR5 支持的 CAS Latency 值 (CL20-CL98, 偶数)
ALL_CL_VALUES = list(range(20, 99, 2))


# =============================================================================
# XMP_3_0 — XMP 3.0 Profile (64 字节)
# =============================================================================

# =============================================================================
# DDR5 Speed Bin 数据库 (JESD79-5D)
# =============================================================================

# 注意: 时序值单位是 ns，应用到 SPD 时需转换为 ps (×1000)
# tRFC1/2/4 直接以 ns 存储
DDR5_SPEED_BINS = {
    # ---- DDR5-3200 ----
    "DDR5-3200AN": {
        "mt_s": 3200,
        "tCKmin_ns": 0.625, "tCKmax_ns": 1.01,
        "CL": 24, "supported_cl": [22, 24, 26, 28],
        "tAA_ns": 15.0, "tRCD_ns": 15.0, "tRP_ns": 15.0,
        "tRAS_ns": 32.0, "tRC_ns": 47.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-3200B": {
        "mt_s": 3200,
        "tCKmin_ns": 0.625, "tCKmax_ns": 1.01,
        "CL": 26, "supported_cl": [22, 26, 28],
        "tAA_ns": 16.25, "tRCD_ns": 16.25, "tRP_ns": 16.25,
        "tRAS_ns": 32.0, "tRC_ns": 48.25, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-3200BN": {
        "mt_s": 3200,
        "tCKmin_ns": 0.625, "tCKmax_ns": 1.01,
        "CL": 26, "supported_cl": [22, 26, 28],
        "tAA_ns": 16.25, "tRCD_ns": 16.25, "tRP_ns": 16.25,
        "tRAS_ns": 32.0, "tRC_ns": 48.25, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-3200C": {
        "mt_s": 3200,
        "tCKmin_ns": 0.625, "tCKmax_ns": 1.01,
        "CL": 28, "supported_cl": [22, 28],
        "tAA_ns": 17.5, "tRCD_ns": 17.5, "tRP_ns": 17.5,
        "tRAS_ns": 32.0, "tRC_ns": 49.5, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    # ---- DDR5-3600 ----
    "DDR5-3600AN": {
        "mt_s": 3600,
        "tCKmin_ns": 0.556, "tCKmax_ns": 1.01,
        "CL": 26, "supported_cl": [22, 24, 26, 28, 30, 32],
        "tAA_ns": 14.444, "tRCD_ns": 14.444, "tRP_ns": 14.444,
        "tRAS_ns": 32.0, "tRC_ns": 46.444, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-3600B": {
        "mt_s": 3600,
        "tCKmin_ns": 0.556, "tCKmax_ns": 1.01,
        "CL": 30, "supported_cl": [22, 26, 28, 30, 32],
        "tAA_ns": 16.25, "tRCD_ns": 16.25, "tRP_ns": 16.25,
        "tRAS_ns": 32.0, "tRC_ns": 48.25, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-3600BN": {
        "mt_s": 3600,
        "tCKmin_ns": 0.556, "tCKmax_ns": 1.01,
        "CL": 30, "supported_cl": [22, 28, 30, 32],
        "tAA_ns": 16.666, "tRCD_ns": 16.666, "tRP_ns": 16.666,
        "tRAS_ns": 32.0, "tRC_ns": 48.666, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-3600C": {
        "mt_s": 3600,
        "tCKmin_ns": 0.556, "tCKmax_ns": 1.01,
        "CL": 32, "supported_cl": [22, 28, 32],
        "tAA_ns": 17.5, "tRCD_ns": 17.5, "tRP_ns": 17.5,
        "tRAS_ns": 32.0, "tRC_ns": 49.5, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    # ---- DDR5-4000 ----
    "DDR5-4000AN": {
        "mt_s": 4000,
        "tCKmin_ns": 0.5, "tCKmax_ns": 1.01,
        "CL": 28, "supported_cl": [22, 24, 26, 28, 30, 32, 36],
        "tAA_ns": 14.0, "tRCD_ns": 14.0, "tRP_ns": 14.0,
        "tRAS_ns": 32.0, "tRC_ns": 46.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-4000B": {
        "mt_s": 4000,
        "tCKmin_ns": 0.5, "tCKmax_ns": 1.01,
        "CL": 32, "supported_cl": [22, 26, 28, 30, 32, 36],
        "tAA_ns": 16.0, "tRCD_ns": 16.0, "tRP_ns": 16.0,
        "tRAS_ns": 32.0, "tRC_ns": 48.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-4000BN": {
        "mt_s": 4000,
        "tCKmin_ns": 0.5, "tCKmax_ns": 1.01,
        "CL": 32, "supported_cl": [22, 26, 28, 30, 32, 36],
        "tAA_ns": 16.0, "tRCD_ns": 16.0, "tRP_ns": 16.0,
        "tRAS_ns": 32.0, "tRC_ns": 48.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-4000C": {
        "mt_s": 4000,
        "tCKmin_ns": 0.5, "tCKmax_ns": 1.01,
        "CL": 36, "supported_cl": [22, 28, 32, 36],
        "tAA_ns": 17.5, "tRCD_ns": 17.5, "tRP_ns": 17.5,
        "tRAS_ns": 32.0, "tRC_ns": 49.5, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    # ---- DDR5-4400 ----
    "DDR5-4400AN": {
        "mt_s": 4400,
        "tCKmin_ns": 0.455, "tCKmax_ns": 1.01,
        "CL": 32, "supported_cl": [22, 24, 26, 28, 30, 32, 36, 40],
        "tAA_ns": 14.545, "tRCD_ns": 14.545, "tRP_ns": 14.545,
        "tRAS_ns": 32.0, "tRC_ns": 46.545, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-4400B": {
        "mt_s": 4400,
        "tCKmin_ns": 0.455, "tCKmax_ns": 1.01,
        "CL": 36, "supported_cl": [22, 26, 28, 30, 32, 36, 40],
        "tAA_ns": 16.0, "tRCD_ns": 16.0, "tRP_ns": 16.0,
        "tRAS_ns": 32.0, "tRC_ns": 48.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-4400BN": {
        "mt_s": 4400,
        "tCKmin_ns": 0.455, "tCKmax_ns": 1.01,
        "CL": 36, "supported_cl": [22, 28, 30, 32, 36, 40],
        "tAA_ns": 16.363, "tRCD_ns": 16.363, "tRP_ns": 16.363,
        "tRAS_ns": 32.0, "tRC_ns": 48.363, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-4400C": {
        "mt_s": 4400,
        "tCKmin_ns": 0.455, "tCKmax_ns": 1.01,
        "CL": 40, "supported_cl": [22, 28, 32, 36, 40],
        "tAA_ns": 17.5, "tRCD_ns": 17.5, "tRP_ns": 17.5,
        "tRAS_ns": 32.0, "tRC_ns": 49.5, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    # ---- DDR5-4800 ----
    "DDR5-4800AN": {
        "mt_s": 4800,
        "tCKmin_ns": 0.416, "tCKmax_ns": 1.01,
        "CL": 34, "supported_cl": [22, 24, 26, 28, 30, 32, 34, 36, 40, 42],
        "tAA_ns": 14.166, "tRCD_ns": 14.166, "tRP_ns": 14.166,
        "tRAS_ns": 32.0, "tRC_ns": 46.166, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-4800B": {
        "mt_s": 4800,
        "tCKmin_ns": 0.416, "tCKmax_ns": 1.01,
        "CL": 40, "supported_cl": [22, 26, 28, 30, 32, 36, 40, 42],
        "tAA_ns": 16.0, "tRCD_ns": 16.0, "tRP_ns": 16.0,
        "tRAS_ns": 32.0, "tRC_ns": 48.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-4800BN": {
        "mt_s": 4800,
        "tCKmin_ns": 0.416, "tCKmax_ns": 1.01,
        "CL": 40, "supported_cl": [22, 28, 30, 32, 36, 40, 42],
        "tAA_ns": 16.666, "tRCD_ns": 16.666, "tRP_ns": 16.666,
        "tRAS_ns": 32.0, "tRC_ns": 48.666, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-4800C": {
        "mt_s": 4800,
        "tCKmin_ns": 0.416, "tCKmax_ns": 1.01,
        "CL": 42, "supported_cl": [22, 28, 32, 36, 40, 42],
        "tAA_ns": 17.5, "tRCD_ns": 17.5, "tRP_ns": 17.5,
        "tRAS_ns": 32.0, "tRC_ns": 49.5, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    # ---- DDR5-5200 ----
    "DDR5-5200AN": {
        "mt_s": 5200,
        "tCKmin_ns": 0.385, "tCKmax_ns": 1.01,
        "CL": 38, "supported_cl": [22, 24, 26, 28, 30, 32, 36, 38, 40, 42, 46],
        "tAA_ns": 14.615, "tRCD_ns": 14.615, "tRP_ns": 14.615,
        "tRAS_ns": 32.0, "tRC_ns": 46.615, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-5200B": {
        "mt_s": 5200,
        "tCKmin_ns": 0.385, "tCKmax_ns": 1.01,
        "CL": 42, "supported_cl": [22, 26, 28, 30, 32, 36, 40, 42, 46],
        "tAA_ns": 16.0, "tRCD_ns": 16.0, "tRP_ns": 16.0,
        "tRAS_ns": 32.0, "tRC_ns": 48.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-5200C": {
        "mt_s": 5200,
        "tCKmin_ns": 0.385, "tCKmax_ns": 1.01,
        "CL": 46, "supported_cl": [22, 28, 32, 36, 40, 42, 46],
        "tAA_ns": 17.5, "tRCD_ns": 17.5, "tRP_ns": 17.5,
        "tRAS_ns": 32.0, "tRC_ns": 49.5, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    # ---- DDR5-5600 ----
    "DDR5-5600AN": {
        "mt_s": 5600,
        "tCKmin_ns": 0.357, "tCKmax_ns": 1.01,
        "CL": 40, "supported_cl": [22, 24, 26, 28, 30, 32, 36, 40, 42, 46, 50],
        "tAA_ns": 14.285, "tRCD_ns": 14.285, "tRP_ns": 14.285,
        "tRAS_ns": 32.0, "tRC_ns": 46.285, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-5600B": {
        "mt_s": 5600,
        "tCKmin_ns": 0.357, "tCKmax_ns": 1.01,
        "CL": 46, "supported_cl": [22, 26, 28, 30, 32, 36, 40, 42, 46, 50],
        "tAA_ns": 16.0, "tRCD_ns": 16.0, "tRP_ns": 16.0,
        "tRAS_ns": 32.0, "tRC_ns": 48.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-5600BN": {
        "mt_s": 5600,
        "tCKmin_ns": 0.357, "tCKmax_ns": 1.01,
        "CL": 46, "supported_cl": [22, 28, 30, 32, 36, 40, 42, 46, 50],
        "tAA_ns": 16.428, "tRCD_ns": 16.428, "tRP_ns": 16.428,
        "tRAS_ns": 32.0, "tRC_ns": 48.428, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-5600C": {
        "mt_s": 5600,
        "tCKmin_ns": 0.357, "tCKmax_ns": 1.01,
        "CL": 50, "supported_cl": [22, 28, 32, 36, 40, 42, 46, 50],
        "tAA_ns": 17.5, "tRCD_ns": 17.5, "tRP_ns": 17.5,
        "tRAS_ns": 32.0, "tRC_ns": 49.5, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    # ---- DDR5-6400 ----
    "DDR5-6400AN": {
        "mt_s": 6400,
        "tCKmin_ns": 0.312, "tCKmax_ns": 1.01,
        "CL": 46, "supported_cl": [22, 24, 26, 28, 30, 32, 36, 38, 40, 42, 46, 50, 52, 54],
        "tAA_ns": 14.375, "tRCD_ns": 14.375, "tRP_ns": 14.375,
        "tRAS_ns": 32.0, "tRC_ns": 46.375, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-6400B": {
        "mt_s": 6400,
        "tCKmin_ns": 0.312, "tCKmax_ns": 1.01,
        "CL": 52, "supported_cl": [22, 26, 28, 30, 32, 36, 40, 42, 46, 50, 52, 54],
        "tAA_ns": 16.0, "tRCD_ns": 16.0, "tRP_ns": 16.0,
        "tRAS_ns": 32.0, "tRC_ns": 48.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-6400BN": {
        "mt_s": 6400,
        "tCKmin_ns": 0.312, "tCKmax_ns": 1.01,
        "CL": 52, "supported_cl": [22, 28, 30, 32, 36, 40, 42, 46, 50, 52, 54],
        "tAA_ns": 16.25, "tRCD_ns": 16.25, "tRP_ns": 16.25,
        "tRAS_ns": 32.0, "tRC_ns": 48.25, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-6400C": {
        "mt_s": 6400,
        "tCKmin_ns": 0.312, "tCKmax_ns": 1.01,
        "CL": 56, "supported_cl": [22, 28, 32, 36, 40, 42, 46, 50, 52, 54],
        "tAA_ns": 17.5, "tRCD_ns": 17.5, "tRP_ns": 17.5,
        "tRAS_ns": 32.0, "tRC_ns": 49.5, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    # ---- DDR5-5200 (补充) ----
    "DDR5-5200BN": {
        "mt_s": 5200,
        "tCKmin_ns": 0.385, "tCKmax_ns": 1.01,
        "CL": 42, "supported_cl": [22, 28, 30, 32, 36, 40, 42, 46],
        "tAA_ns": 16.153, "tRCD_ns": 16.153, "tRP_ns": 16.153,
        "tRAS_ns": 32.0, "tRC_ns": 48.153, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-5200C": {
        "mt_s": 5200,
        "tCKmin_ns": 0.385, "tCKmax_ns": 1.01,
        "CL": 46, "supported_cl": [22, 28, 32, 36, 40, 42, 46],
        "tAA_ns": 17.5, "tRCD_ns": 17.5, "tRP_ns": 17.5,
        "tRAS_ns": 32.0, "tRC_ns": 49.5, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    # ---- DDR5-6000 ----
    "DDR5-6000AN": {
        "mt_s": 6000,
        "tCKmin_ns": 0.333, "tCKmax_ns": 1.01,
        "CL": 42, "supported_cl": [22, 24, 26, 28, 30, 32, 36, 38, 40, 42, 46, 50, 52],
        "tAA_ns": 14.0, "tRCD_ns": 14.0, "tRP_ns": 14.0,
        "tRAS_ns": 32.0, "tRC_ns": 46.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-6000B": {
        "mt_s": 6000,
        "tCKmin_ns": 0.333, "tCKmax_ns": 1.01,
        "CL": 48, "supported_cl": [22, 26, 28, 30, 32, 36, 40, 42, 46, 50, 52],
        "tAA_ns": 16.0, "tRCD_ns": 16.0, "tRP_ns": 16.0,
        "tRAS_ns": 32.0, "tRC_ns": 48.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-6000BN": {
        "mt_s": 6000,
        "tCKmin_ns": 0.333, "tCKmax_ns": 1.01,
        "CL": 48, "supported_cl": [22, 28, 30, 32, 36, 40, 42, 46, 50, 52],
        "tAA_ns": 16.0, "tRCD_ns": 16.0, "tRP_ns": 16.0,
        "tRAS_ns": 32.0, "tRC_ns": 48.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-6000C": {
        "mt_s": 6000,
        "tCKmin_ns": 0.333, "tCKmax_ns": 1.01,
        "CL": 54, "supported_cl": [22, 28, 32, 36, 40, 42, 46, 50, 52],
        "tAA_ns": 17.5, "tRCD_ns": 17.5, "tRP_ns": 17.5,
        "tRAS_ns": 32.0, "tRC_ns": 49.5, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    # ---- DDR5-6800 ----
    "DDR5-6800AN": {
        "mt_s": 6800,
        "tCKmin_ns": 0.294, "tCKmax_ns": 1.01,
        "CL": 48, "supported_cl": [22, 24, 26, 28, 30, 32, 36, 40, 42, 46, 50, 52, 54, 56, 60],
        "tAA_ns": 14.117, "tRCD_ns": 14.117, "tRP_ns": 14.117,
        "tRAS_ns": 32.0, "tRC_ns": 46.117, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-6800B": {
        "mt_s": 6800,
        "tCKmin_ns": 0.294, "tCKmax_ns": 1.01,
        "CL": 56, "supported_cl": [22, 28, 30, 32, 36, 40, 42, 46, 50, 52, 54, 56],
        "tAA_ns": 16.0, "tRCD_ns": 16.0, "tRP_ns": 16.0,
        "tRAS_ns": 32.0, "tRC_ns": 48.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-6800BN": {
        "mt_s": 6800,
        "tCKmin_ns": 0.294, "tCKmax_ns": 1.01,
        "CL": 56, "supported_cl": [22, 28, 30, 32, 36, 40, 42, 46, 50, 52, 54, 56],
        "tAA_ns": 16.47, "tRCD_ns": 16.47, "tRP_ns": 16.47,
        "tRAS_ns": 32.0, "tRC_ns": 48.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-6800C": {
        "mt_s": 6800,
        "tCKmin_ns": 0.294, "tCKmax_ns": 1.01,
        "CL": 60, "supported_cl": [22, 28, 32, 36, 40, 42, 46, 50, 52, 54, 56],
        "tAA_ns": 17.5, "tRCD_ns": 17.5, "tRP_ns": 17.5,
        "tRAS_ns": 32.0, "tRC_ns": 49.5, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    # ---- DDR5-7200 ----
    "DDR5-7200AN": {
        "mt_s": 7200,
        "tCKmin_ns": 0.278, "tCKmax_ns": 1.01,
        "CL": 52, "supported_cl": [22, 24, 26, 28, 30, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64],
        "tAA_ns": 14.444, "tRCD_ns": 14.444, "tRP_ns": 14.444,
        "tRAS_ns": 32.0, "tRC_ns": 46.444, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-7200B": {
        "mt_s": 7200,
        "tCKmin_ns": 0.278, "tCKmax_ns": 1.01,
        "CL": 58, "supported_cl": [22, 28, 30, 32, 36, 40, 42, 46, 50, 52, 56, 60],
        "tAA_ns": 16.0, "tRCD_ns": 16.0, "tRP_ns": 16.0,
        "tRAS_ns": 32.0, "tRC_ns": 48.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-7200BN": {
        "mt_s": 7200,
        "tCKmin_ns": 0.278, "tCKmax_ns": 1.01,
        "CL": 58, "supported_cl": [22, 28, 30, 32, 36, 40, 42, 46, 50, 52, 56, 60],
        "tAA_ns": 16.111, "tRCD_ns": 16.111, "tRP_ns": 16.111,
        "tRAS_ns": 32.0, "tRC_ns": 48.111, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-7200C": {
        "mt_s": 7200,
        "tCKmin_ns": 0.278, "tCKmax_ns": 1.01,
        "CL": 64, "supported_cl": [22, 28, 32, 36, 40, 42, 46, 50, 52, 56, 60],
        "tAA_ns": 17.5, "tRCD_ns": 17.5, "tRP_ns": 17.5,
        "tRAS_ns": 32.0, "tRC_ns": 49.5, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    # ---- DDR5-7600 ----
    "DDR5-7600AN": {
        "mt_s": 7600,
        "tCKmin_ns": 0.263, "tCKmax_ns": 1.01,
        "CL": 54, "supported_cl": [22, 24, 26, 28, 30, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64, 68],
        "tAA_ns": 14.21, "tRCD_ns": 14.21, "tRP_ns": 14.21,
        "tRAS_ns": 32.0, "tRC_ns": 46.21, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-7600B": {
        "mt_s": 7600,
        "tCKmin_ns": 0.263, "tCKmax_ns": 1.01,
        "CL": 62, "supported_cl": [22, 28, 30, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64],
        "tAA_ns": 16.0, "tRCD_ns": 16.0, "tRP_ns": 16.0,
        "tRAS_ns": 32.0, "tRC_ns": 48.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-7600BN": {
        "mt_s": 7600,
        "tCKmin_ns": 0.263, "tCKmax_ns": 1.01,
        "CL": 62, "supported_cl": [22, 28, 30, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64],
        "tAA_ns": 16.315, "tRCD_ns": 16.315, "tRP_ns": 16.315,
        "tRAS_ns": 32.0, "tRC_ns": 48.315, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-7600C": {
        "mt_s": 7600,
        "tCKmin_ns": 0.263, "tCKmax_ns": 1.01,
        "CL": 68, "supported_cl": [22, 28, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64],
        "tAA_ns": 17.5, "tRCD_ns": 17.5, "tRP_ns": 17.5,
        "tRAS_ns": 32.0, "tRC_ns": 49.5, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    # ---- DDR5-8000 ----
    "DDR5-8000AN": {
        "mt_s": 8000,
        "tCKmin_ns": 0.25, "tCKmax_ns": 1.01,
        "CL": 56, "supported_cl": [22, 24, 26, 28, 30, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64, 68, 72],
        "tAA_ns": 14.0, "tRCD_ns": 14.0, "tRP_ns": 14.0,
        "tRAS_ns": 32.0, "tRC_ns": 46.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-8000B": {
        "mt_s": 8000,
        "tCKmin_ns": 0.25, "tCKmax_ns": 1.01,
        "CL": 64, "supported_cl": [22, 28, 30, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64, 68],
        "tAA_ns": 16.0, "tRCD_ns": 16.0, "tRP_ns": 16.0,
        "tRAS_ns": 32.0, "tRC_ns": 48.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-8000BN": {
        "mt_s": 8000,
        "tCKmin_ns": 0.25, "tCKmax_ns": 1.01,
        "CL": 64, "supported_cl": [22, 28, 30, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64, 68],
        "tAA_ns": 16.0, "tRCD_ns": 16.0, "tRP_ns": 16.0,
        "tRAS_ns": 32.0, "tRC_ns": 48.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-8000C": {
        "mt_s": 8000,
        "tCKmin_ns": 0.25, "tCKmax_ns": 1.01,
        "CL": 70, "supported_cl": [22, 28, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64, 68],
        "tAA_ns": 17.5, "tRCD_ns": 17.5, "tRP_ns": 17.5,
        "tRAS_ns": 32.0, "tRC_ns": 49.5, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    # ---- DDR5-8400 ----
    "DDR5-8400AN": {
        "mt_s": 8400,
        "tCKmin_ns": 0.238, "tCKmax_ns": 1.01,
        "CL": 60, "supported_cl": [22, 24, 26, 28, 30, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64, 68, 72, 76],
        "tAA_ns": 14.285, "tRCD_ns": 14.285, "tRP_ns": 14.285,
        "tRAS_ns": 32.0, "tRC_ns": 46.285, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-8400B": {
        "mt_s": 8400,
        "tCKmin_ns": 0.238, "tCKmax_ns": 1.01,
        "CL": 68, "supported_cl": [22, 28, 30, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64, 68, 72],
        "tAA_ns": 16.0, "tRCD_ns": 16.0, "tRP_ns": 16.0,
        "tRAS_ns": 32.0, "tRC_ns": 48.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-8400BN": {
        "mt_s": 8400,
        "tCKmin_ns": 0.238, "tCKmax_ns": 1.01,
        "CL": 68, "supported_cl": [22, 28, 30, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64, 68, 72],
        "tAA_ns": 16.19, "tRCD_ns": 16.19, "tRP_ns": 16.19,
        "tRAS_ns": 32.0, "tRC_ns": 48.19, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-8400C": {
        "mt_s": 8400,
        "tCKmin_ns": 0.238, "tCKmax_ns": 1.01,
        "CL": 74, "supported_cl": [22, 28, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64, 68, 72],
        "tAA_ns": 17.5, "tRCD_ns": 17.5, "tRP_ns": 17.5,
        "tRAS_ns": 32.0, "tRC_ns": 49.5, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    # ---- DDR5-8800 ----
    "DDR5-8800AN": {
        "mt_s": 8800,
        "tCKmin_ns": 0.227, "tCKmax_ns": 1.01,
        "CL": 62, "supported_cl": [22, 24, 26, 28, 30, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64, 68, 72, 76, 80],
        "tAA_ns": 14.09, "tRCD_ns": 14.09, "tRP_ns": 14.09,
        "tRAS_ns": 32.0, "tRC_ns": 46.09, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-8800B": {
        "mt_s": 8800,
        "tCKmin_ns": 0.227, "tCKmax_ns": 1.01,
        "CL": 72, "supported_cl": [22, 28, 30, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64, 68, 72, 76],
        "tAA_ns": 16.0, "tRCD_ns": 16.0, "tRP_ns": 16.0,
        "tRAS_ns": 32.0, "tRC_ns": 48.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-8800BN": {
        "mt_s": 8800,
        "tCKmin_ns": 0.227, "tCKmax_ns": 1.01,
        "CL": 72, "supported_cl": [22, 28, 30, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64, 68, 72, 76],
        "tAA_ns": 16.363, "tRCD_ns": 16.363, "tRP_ns": 16.363,
        "tRAS_ns": 32.0, "tRC_ns": 48.363, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-8800C": {
        "mt_s": 8800,
        "tCKmin_ns": 0.227, "tCKmax_ns": 1.01,
        "CL": 78, "supported_cl": [22, 28, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64, 68, 72, 76],
        "tAA_ns": 17.5, "tRCD_ns": 17.5, "tRP_ns": 17.5,
        "tRAS_ns": 32.0, "tRC_ns": 49.5, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    # ---- DDR5-9200 ----
    "DDR5-9200AN": {
        "mt_s": 9200,
        "tCKmin_ns": 0.217, "tCKmax_ns": 1.01,
        "CL": 66, "supported_cl": [22, 24, 26, 28, 30, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64, 68, 72, 76, 80, 84],
        "tAA_ns": 14.347, "tRCD_ns": 14.347, "tRP_ns": 14.347,
        "tRAS_ns": 32.0, "tRC_ns": 46.347, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-9200B": {
        "mt_s": 9200,
        "tCKmin_ns": 0.217, "tCKmax_ns": 1.01,
        "CL": 74, "supported_cl": [22, 28, 30, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64, 68, 72, 76, 80],
        "tAA_ns": 16.0, "tRCD_ns": 16.0, "tRP_ns": 16.0,
        "tRAS_ns": 32.0, "tRC_ns": 48.0, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-9200BN": {
        "mt_s": 9200,
        "tCKmin_ns": 0.217, "tCKmax_ns": 1.01,
        "CL": 74, "supported_cl": [22, 28, 30, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64, 68, 72, 76, 80],
        "tAA_ns": 16.086, "tRCD_ns": 16.086, "tRP_ns": 16.086,
        "tRAS_ns": 32.0, "tRC_ns": 48.086, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
    "DDR5-9200C": {
        "mt_s": 9200,
        "tCKmin_ns": 0.217, "tCKmax_ns": 1.01,
        "CL": 82, "supported_cl": [22, 28, 32, 36, 40, 42, 46, 50, 52, 56, 60, 64, 68, 72, 76, 80],
        "tAA_ns": 17.5, "tRCD_ns": 17.5, "tRP_ns": 17.5,
        "tRAS_ns": 32.0, "tRC_ns": 49.5, "tWR_ns": 30.0,
        "tWTR_S_ns": 2.5, "tWTR_L_ns": 7.5,
        "tRRD_S_ns": 3.7, "tRRD_L_ns": 4.9,
        "tRFC1_ns": 295.0, "tRFC2_ns": 160.0, "tRFC4_ns": 130.0,
        "tFAW_ns": 21.0,
    },
}


def apply_speed_bin(spd: 'DDR5_SPD', bin_name: str) -> bool:
    """将 Speed Bin 参数应用到 DDR5_SPD 的 JEDEC 基本配置区域。

    参数映射:
      tCKmin_ns → min_cycle_time (ns→ps)
      tCKmax_ns → max_cycle_time (ns→ps)
      supported_cl → CAS Latency 位掩码
      tAA_ns, tRCD_ns, tRP_ns → ps
      tRAS_ns, tRC_ns → ps
      tWR_ns → ps
      tRFC1/2/4_ns → tRFC1_slr/tRFC2_slr/tRFCsb_slr (ns)
      tRRD_L_ns → tRRD_L ps
      tWTR_L_ns → tCCD_L_WTR ps
      tWTR_S_ns → tCCD_S_WTR ps
      tFAW_ns → tFAW ps
    """
    if bin_name not in DDR5_SPEED_BINS:
        return False

    b = DDR5_SPEED_BINS[bin_name]

    def _ns2ps(ns: float) -> int:
        return round(ns * 1000)

    # 频率
    spd.min_cycle_time = _ns2ps(b["tCKmin_ns"])
    spd.max_cycle_time = _ns2ps(b["tCKmax_ns"])

    # CAS Latency: 先全部清零，再设置支持的
    for cl in ALL_CL_VALUES:
        spd.set_cl_supported(cl, False)
    for cl in b["supported_cl"]:
        spd.set_cl_supported(cl, True)

    # 主时序 (ns → ps)
    spd.tAA = _ns2ps(b["tAA_ns"])
    spd.tRCD = _ns2ps(b["tRCD_ns"])
    spd.tRP = _ns2ps(b["tRP_ns"])
    spd.tRAS = _ns2ps(b["tRAS_ns"])
    spd.tRC = _ns2ps(b["tRC_ns"])
    spd.tWR = _ns2ps(b["tWR_ns"])

    # Refresh (ns, 直接存储为 ns)
    spd.tRFC1_slr = round(b["tRFC1_ns"])
    spd.tRFC2_slr = round(b["tRFC2_ns"])
    spd.tRFCsb_slr = round(b["tRFC4_ns"])

    # 第二时序 (ns → ps)
    spd.tRRD_L = _ns2ps(b["tRRD_L_ns"])
    spd.tCCD_L = _ns2ps(max(b["tRRD_L_ns"], 4.0))  # tCCD_L = max(tRRD_L, 4ns)
    spd.tCCD_L_WR = _ns2ps(max(b["tWTR_L_ns"] + b["tWR_ns"], 20.0))
    spd.tCCD_L_WR2 = _ns2ps(max(b["tWTR_L_ns"] + b["tWR_ns"] / 2, 10.0))
    spd.tFAW = _ns2ps(b["tFAW_ns"])
    spd.tCCD_L_WTR = _ns2ps(b["tWTR_L_ns"])
    spd.tCCD_S_WTR = _ns2ps(b["tWTR_S_ns"])
    spd.tRTP = _ns2ps(max(b["tWTR_L_ns"], 7.5))

    # tCCD_M / tCCD_M_WR / tCCD_M_WTR = 0 (reserved/optional for now)

    # Lower limits (与 C# 原版 LoadSample 一致)
    mct = spd.min_cycle_time
    from ddr5_utils import time_to_ticks_ddr5
    spd.tRRD_L_lower_limit = max(4, time_to_ticks_ddr5(_ns2ps(b["tRRD_L_ns"]), mct))
    spd.tCCD_L_lower_limit = max(4, time_to_ticks_ddr5(_ns2ps(max(b["tRRD_L_ns"], 4.0)), mct))
    spd.tCCD_L_WR_lower_limit = max(16, time_to_ticks_ddr5(_ns2ps(b["tWR_ns"]), mct))
    spd.tCCD_L_WR2_lower_limit = max(8, time_to_ticks_ddr5(_ns2ps(b["tWR_ns"] / 2), mct))
    spd.tFAW_lower_limit = max(20, time_to_ticks_ddr5(_ns2ps(b["tFAW_ns"]), mct))
    spd.tCCD_L_WTR_lower_limit = max(4, time_to_ticks_ddr5(_ns2ps(b["tWTR_L_ns"]), mct))
    spd.tCCD_S_WTR_lower_limit = max(2, time_to_ticks_ddr5(_ns2ps(b["tWTR_S_ns"]), mct))
    spd.tRTP_lower_limit = max(6, time_to_ticks_ddr5(_ns2ps(max(b["tWTR_L_ns"], 7.5)), mct))

    return True


def apply_speed_bin_to_xmp(xmp: 'XMP_3_0', bin_name: str) -> bool:
    """将 Speed Bin 参数应用到 XMP 3.0 Profile。

    填充: 频率, CAS, 电压(默认), 时序, Lower Limits。
    """
    if bin_name not in DDR5_SPEED_BINS:
        return False

    b = DDR5_SPEED_BINS[bin_name]

    def _ns2ps(ns):
        return round(ns * 1000)

    # 频率
    xmp.min_cycle_time = _ns2ps(b["tCKmin_ns"])

    # CAS Latency
    for cl in ALL_CL_VALUES:
        xmp._set_cl(cl, False)
    for cl in b["supported_cl"]:
        xmp._set_cl(cl, True)

    # 电压 (默认值，用户可后续调整)
    xmp.vdd = 110
    xmp.vddq = 110
    xmp.vpp = 180
    xmp.vmemctrl = 110

    # 命令速率 (默认 2N)
    xmp.command_rate = CommandRate.N2

    # 主时序
    xmp.tAA = _ns2ps(b["tAA_ns"])
    xmp.tRCD = _ns2ps(b["tRCD_ns"])
    xmp.tRP = _ns2ps(b["tRP_ns"])
    xmp.tRAS = _ns2ps(b["tRAS_ns"])
    xmp.tRC = _ns2ps(b["tRC_ns"])
    xmp.tWR = _ns2ps(b["tWR_ns"])

    # Refresh (ns)
    xmp.tRFC1 = round(b["tRFC1_ns"])
    xmp.tRFC2 = round(b["tRFC2_ns"])
    xmp.tRFC = round(b["tRFC4_ns"])

    # 第二时序
    tWTR_L_ps = _ns2ps(b["tWTR_L_ns"])
    tWTR_S_ps = _ns2ps(b["tWTR_S_ns"])
    tWR_ps = _ns2ps(b["tWR_ns"])
    tRRD_L_ps = _ns2ps(b["tRRD_L_ns"])
    tFAW_ps = _ns2ps(b["tFAW_ns"])

    xmp.tRRD_L = tRRD_L_ps
    xmp.tCCD_L = _ns2ps(max(b["tRRD_L_ns"], 4.0))
    xmp.tCCD_L_WR = _ns2ps(max(b["tWTR_L_ns"] + b["tWR_ns"], 20.0))
    xmp.tCCD_L_WR2 = _ns2ps(max(b["tWTR_L_ns"] + b["tWR_ns"] / 2, 10.0))
    xmp.tFAW = tFAW_ps
    xmp.tCCD_L_WTR = tWTR_L_ps
    xmp.tCCD_S_WTR = tWTR_S_ps
    xmp.tRTP = max(tWTR_L_ps, _ns2ps(7.5))

    # Lower Limits
    mct = xmp.min_cycle_time
    from ddr5_utils import time_to_ticks_ddr5
    xmp.tRRD_L_lower_limit = max(4, time_to_ticks_ddr5(tRRD_L_ps, mct))
    xmp.tCCD_L_lower_limit = max(4, time_to_ticks_ddr5(_ns2ps(max(b["tRRD_L_ns"], 4.0)), mct))
    xmp.tCCD_L_WR_lower_limit = max(16, time_to_ticks_ddr5(tWR_ps, mct))
    xmp.tCCD_L_WR2_lower_limit = max(8, time_to_ticks_ddr5(_ns2ps(b["tWR_ns"] / 2), mct))
    xmp.tFAW_lower_limit = max(20, time_to_ticks_ddr5(tFAW_ps, mct))
    xmp.tCCD_L_WTR_lower_limit = max(4, time_to_ticks_ddr5(tWTR_L_ps, mct))
    xmp.tCCD_S_WTR_lower_limit = max(2, time_to_ticks_ddr5(tWTR_S_ps, mct))
    xmp.tRTP_lower_limit = max(6, time_to_ticks_ddr5(max(tWTR_L_ps, _ns2ps(7.5)), mct))

    xmp.update_crc()
    return True


def apply_speed_bin_to_expo(expo: 'EXPO', bin_name: str) -> bool:
    """将 Speed Bin 参数应用到 EXPO Profile。

    填充: 频率, 电压(默认), 时序 (EXPO 无 CAS Latency 字段)。
    """
    if bin_name not in DDR5_SPEED_BINS:
        return False

    b = DDR5_SPEED_BINS[bin_name]

    def _ns2ps(ns):
        return round(ns * 1000)

    # 频率
    expo.min_cycle_time = _ns2ps(b["tCKmin_ns"])

    # 电压 (默认值)
    expo.vdd = 110
    expo.vddq = 110
    expo.vpp = 180

    # 主时序
    expo.tAA = _ns2ps(b["tAA_ns"])
    expo.tRCD = _ns2ps(b["tRCD_ns"])
    expo.tRP = _ns2ps(b["tRP_ns"])
    expo.tRAS = _ns2ps(b["tRAS_ns"])
    expo.tRC = _ns2ps(b["tRC_ns"])
    expo.tWR = _ns2ps(b["tWR_ns"])

    # Refresh (ns)
    expo.tRFC1 = round(b["tRFC1_ns"])
    expo.tRFC2 = round(b["tRFC2_ns"])
    expo.tRFC = round(b["tRFC4_ns"])

    # 第二时序
    tWTR_L_ps = _ns2ps(b["tWTR_L_ns"])
    tWTR_S_ps = _ns2ps(b["tWTR_S_ns"])

    expo.tRRD_L = _ns2ps(b["tRRD_L_ns"])
    expo.tCCD_L = _ns2ps(max(b["tRRD_L_ns"], 4.0))
    expo.tCCD_L_WR = _ns2ps(max(b["tWTR_L_ns"] + b["tWR_ns"], 20.0))
    expo.tCCD_L_WR2 = _ns2ps(max(b["tWTR_L_ns"] + b["tWR_ns"] / 2, 10.0))
    expo.tFAW = _ns2ps(b["tFAW_ns"])
    expo.tCCD_L_WTR = tWTR_L_ps
    expo.tCCD_S_WTR = tWTR_S_ps
    expo.tRTP = max(tWTR_L_ps, _ns2ps(7.5))

    return True


class XMP_3_0:
    """XMP 3.0 Profile 数据模型 (64 字节)"""

    SIZE = 0x40  # 64 bytes

    def __init__(self, profile_no: int = 0):
        self._data = bytearray(self.SIZE)
        self.profile_no = profile_no

    def is_user_profile(self) -> bool:
        """是否为 User Profile (编号 4 或 5)"""
        return self.profile_no in (4, 5)

    # ---- 字节偏移量常量 ----
    # XMP Profile 3.0 内部布局
    _O_VPP = 0
    _O_VDD = 1
    _O_VDDQ = 2
    _O_UNK03 = 3
    _O_VMEMCTRL = 4
    _O_MIN_CYCLE_TIME = 5      # 2 bytes
    _O_CL_SUPPORTED = 7         # 5 bytes
    _O_UNK0A = 12
    _O_TAA = 13                 # 2 bytes
    _O_TRCD = 15                # 2 bytes
    _O_TRP = 17                 # 2 bytes
    _O_TRAS = 19                # 2 bytes
    _O_TRC = 21                 # 2 bytes
    _O_TWR = 23                 # 2 bytes
    _O_TRFC1 = 25               # 2 bytes
    _O_TRFC2 = 27               # 2 bytes
    _O_TRFC = 29                # 2 bytes
    _O_TRRD_L = 31              # 2 bytes
    _O_TRRD_L_LIMIT = 33
    _O_TCCD_L_WR = 34           # 2 bytes
    _O_TCCD_L_WR_LIMIT = 36
    _O_TCCD_L_WR2 = 37          # 2 bytes
    _O_TCCD_L_WR2_LIMIT = 39
    _O_TCCD_L_WTR = 40          # 2 bytes
    _O_TCCD_L_WTR_LIMIT = 42
    _O_TCCD_S_WTR = 43          # 2 bytes
    _O_TCCD_S_WTR_LIMIT = 45
    _O_TCCD_L = 46              # 2 bytes
    _O_TCCD_L_LIMIT = 48
    _O_TRTP = 49                # 2 bytes
    _O_TRTP_LIMIT = 51
    _O_TFAW = 52                # 2 bytes
    _O_TFAW_LIMIT = 54
    _O_UNK07 = 55
    _O_UNK08 = 56
    _O_UNK09 = 57
    _O_UNK0A2 = 58
    _O_MEMORY_BOOST = 59
    _O_COMMAND_RATE = 60
    _O_UNK0D = 61
    _O_CHECKSUM = 62            # 2 bytes

    # ---- 电压属性 ----

    @property
    def vdd(self) -> int:
        return voltage_byte_to_mv(self._data[self._O_VDD])

    @vdd.setter
    def vdd(self, value: int):
        self._data[self._O_VDD] = voltage_mv_to_byte(value)

    @property
    def vddq(self) -> int:
        return voltage_byte_to_mv(self._data[self._O_VDDQ])

    @vddq.setter
    def vddq(self, value: int):
        self._data[self._O_VDDQ] = voltage_mv_to_byte(value)

    @property
    def vpp(self) -> int:
        return voltage_byte_to_mv(self._data[self._O_VPP])

    @vpp.setter
    def vpp(self, value: int):
        self._data[self._O_VPP] = voltage_mv_to_byte(value)

    @property
    def vmemctrl(self) -> int:
        return voltage_byte_to_mv(self._data[self._O_VMEMCTRL])

    @vmemctrl.setter
    def vmemctrl(self, value: int):
        self._data[self._O_VMEMCTRL] = voltage_mv_to_byte(value)

    # ---- 频率 ----

    @property
    def min_cycle_time(self) -> int:
        return bytes_to_ushort(self._data[self._O_MIN_CYCLE_TIME],
                               self._data[self._O_MIN_CYCLE_TIME + 1])

    @min_cycle_time.setter
    def min_cycle_time(self, value: int):
        lo, hi = ushort_to_bytes(value)
        self._data[self._O_MIN_CYCLE_TIME] = lo
        self._data[self._O_MIN_CYCLE_TIME + 1] = hi

    # ---- 命令速率 ----

    @property
    def command_rate(self) -> CommandRate:
        idx = self._data[self._O_COMMAND_RATE] & 0xF
        if idx >= len(COMMAND_RATE_MAP):
            return CommandRate.UNDEFINED
        return COMMAND_RATE_MAP[idx]

    @command_rate.setter
    def command_rate(self, value: CommandRate):
        self._data[self._O_COMMAND_RATE] = (
            (self._data[self._O_COMMAND_RATE] & 0xF0) | (int(value) & 0xF)
        )

    # ---- 内存增强特性 ----

    @property
    def intel_dynamic_memory_boost(self) -> bool:
        return get_bit(self._data[self._O_MEMORY_BOOST], 0)

    @intel_dynamic_memory_boost.setter
    def intel_dynamic_memory_boost(self, value: bool):
        self._data[self._O_MEMORY_BOOST] = set_bit(
            self._data[self._O_MEMORY_BOOST], 0, value)

    @property
    def realtime_memory_frequency_oc(self) -> bool:
        return get_bit(self._data[self._O_MEMORY_BOOST], 1)

    @realtime_memory_frequency_oc.setter
    def realtime_memory_frequency_oc(self, value: bool):
        self._data[self._O_MEMORY_BOOST] = set_bit(
            self._data[self._O_MEMORY_BOOST], 1, value)

    # ---- CAS Latency ----
    # 动态生成 CL20-CL98 属性
    def _get_cl(self, cl: int) -> bool:
        # 读取操作使用切片拷贝是安全的
        cl_view = self._data[self._O_CL_SUPPORTED:
                             self._O_CL_SUPPORTED + 5]
        return is_cl_supported(cl_view, cl)

    def _set_cl(self, cl: int, value: bool):
        # 写入操作必须在原始 bytearray 上进行
        from ddr5_utils import _cl_to_byte_bit
        byte_idx, bit_pos = _cl_to_byte_bit(cl)
        mask = 1 << bit_pos
        offset = self._O_CL_SUPPORTED + byte_idx
        if value:
            self._data[offset] |= mask
        else:
            self._data[offset] &= ~mask & 0xFF

    # ---- 时序参数 (ps + nCK ticks) ----
    # 使用内部辅助方法统一处理

    def _get_timing(self, offset: int) -> int:
        return bytes_to_ushort(self._data[offset], self._data[offset + 1])

    def _set_timing(self, offset: int, value: int):
        lo, hi = ushort_to_bytes(value)
        self._data[offset] = lo
        self._data[offset + 1] = hi

    def _get_ticks(self, offset: int, multiplier: int = 1) -> int:
        """计算 nCK ticks 值。multiplier 用于 tRFC (乘以 1000)。"""
        raw = self._get_timing(offset) * multiplier
        return time_to_ticks_ddr5(raw, self.min_cycle_time)

    def _get_limit(self, offset: int) -> int:
        return self._data[offset]

    def _set_limit(self, offset: int, value: int):
        self._data[offset] = value & 0xFF

    # tAA
    @property
    def tAA(self) -> int:
        return self._get_timing(self._O_TAA)
    @tAA.setter
    def tAA(self, v: int): self._set_timing(self._O_TAA, v)

    @property
    def tAA_ticks(self) -> int:
        return self._get_ticks(self._O_TAA)

    # tRCD
    @property
    def tRCD(self) -> int:
        return self._get_timing(self._O_TRCD)
    @tRCD.setter
    def tRCD(self, v: int): self._set_timing(self._O_TRCD, v)

    @property
    def tRCD_ticks(self) -> int:
        return self._get_ticks(self._O_TRCD)

    # tRP
    @property
    def tRP(self) -> int:
        return self._get_timing(self._O_TRP)
    @tRP.setter
    def tRP(self, v: int): self._set_timing(self._O_TRP, v)

    @property
    def tRP_ticks(self) -> int:
        return self._get_ticks(self._O_TRP)

    # tRAS
    @property
    def tRAS(self) -> int:
        return self._get_timing(self._O_TRAS)
    @tRAS.setter
    def tRAS(self, v: int): self._set_timing(self._O_TRAS, v)

    @property
    def tRAS_ticks(self) -> int:
        return self._get_ticks(self._O_TRAS)

    # tRC
    @property
    def tRC(self) -> int:
        return self._get_timing(self._O_TRC)
    @tRC.setter
    def tRC(self, v: int): self._set_timing(self._O_TRC, v)

    @property
    def tRC_ticks(self) -> int:
        return self._get_ticks(self._O_TRC)

    # tWR
    @property
    def tWR(self) -> int:
        return self._get_timing(self._O_TWR)
    @tWR.setter
    def tWR(self, v: int): self._set_timing(self._O_TWR, v)

    @property
    def tWR_ticks(self) -> int:
        return self._get_ticks(self._O_TWR)

    # tRFC1 (单位: ns, 需 ×1000 转换为 ps 再计算 ticks)
    @property
    def tRFC1(self) -> int:
        return self._get_timing(self._O_TRFC1)
    @tRFC1.setter
    def tRFC1(self, v: int): self._set_timing(self._O_TRFC1, v)

    @property
    def tRFC1_ticks(self) -> int:
        return self._get_ticks(self._O_TRFC1, multiplier=1000)

    # tRFC2
    @property
    def tRFC2(self) -> int:
        return self._get_timing(self._O_TRFC2)
    @tRFC2.setter
    def tRFC2(self, v: int): self._set_timing(self._O_TRFC2, v)

    @property
    def tRFC2_ticks(self) -> int:
        return self._get_ticks(self._O_TRFC2, multiplier=1000)

    # tRFC (sb)
    @property
    def tRFC(self) -> int:
        return self._get_timing(self._O_TRFC)
    @tRFC.setter
    def tRFC(self, v: int): self._set_timing(self._O_TRFC, v)

    @property
    def tRFC_ticks(self) -> int:
        return self._get_ticks(self._O_TRFC, multiplier=1000)

    # tRRD_L
    @property
    def tRRD_L(self) -> int:
        return self._get_timing(self._O_TRRD_L)
    @tRRD_L.setter
    def tRRD_L(self, v: int): self._set_timing(self._O_TRRD_L, v)

    @property
    def tRRD_L_ticks(self) -> int:
        return self._get_ticks(self._O_TRRD_L)

    @property
    def tRRD_L_lower_limit(self) -> int:
        return self._get_limit(self._O_TRRD_L_LIMIT)
    @tRRD_L_lower_limit.setter
    def tRRD_L_lower_limit(self, v: int): self._set_limit(self._O_TRRD_L_LIMIT, v)

    # tCCD_L
    @property
    def tCCD_L(self) -> int:
        return self._get_timing(self._O_TCCD_L)
    @tCCD_L.setter
    def tCCD_L(self, v: int): self._set_timing(self._O_TCCD_L, v)

    @property
    def tCCD_L_ticks(self) -> int:
        return self._get_ticks(self._O_TCCD_L)

    @property
    def tCCD_L_lower_limit(self) -> int:
        return self._get_limit(self._O_TCCD_L_LIMIT)
    @tCCD_L_lower_limit.setter
    def tCCD_L_lower_limit(self, v: int): self._set_limit(self._O_TCCD_L_LIMIT, v)

    # tCCD_L_WR
    @property
    def tCCD_L_WR(self) -> int:
        return self._get_timing(self._O_TCCD_L_WR)
    @tCCD_L_WR.setter
    def tCCD_L_WR(self, v: int): self._set_timing(self._O_TCCD_L_WR, v)

    @property
    def tCCD_L_WR_ticks(self) -> int:
        return self._get_ticks(self._O_TCCD_L_WR)

    @property
    def tCCD_L_WR_lower_limit(self) -> int:
        return self._get_limit(self._O_TCCD_L_WR_LIMIT)
    @tCCD_L_WR_lower_limit.setter
    def tCCD_L_WR_lower_limit(self, v: int): self._set_limit(self._O_TCCD_L_WR_LIMIT, v)

    # tCCD_L_WR2
    @property
    def tCCD_L_WR2(self) -> int:
        return self._get_timing(self._O_TCCD_L_WR2)
    @tCCD_L_WR2.setter
    def tCCD_L_WR2(self, v: int): self._set_timing(self._O_TCCD_L_WR2, v)

    @property
    def tCCD_L_WR2_ticks(self) -> int:
        return self._get_ticks(self._O_TCCD_L_WR2)

    @property
    def tCCD_L_WR2_lower_limit(self) -> int:
        return self._get_limit(self._O_TCCD_L_WR2_LIMIT)
    @tCCD_L_WR2_lower_limit.setter
    def tCCD_L_WR2_lower_limit(self, v: int): self._set_limit(self._O_TCCD_L_WR2_LIMIT, v)

    # tFAW
    @property
    def tFAW(self) -> int:
        return self._get_timing(self._O_TFAW)
    @tFAW.setter
    def tFAW(self, v: int): self._set_timing(self._O_TFAW, v)

    @property
    def tFAW_ticks(self) -> int:
        return self._get_ticks(self._O_TFAW)

    @property
    def tFAW_lower_limit(self) -> int:
        return self._get_limit(self._O_TFAW_LIMIT)
    @tFAW_lower_limit.setter
    def tFAW_lower_limit(self, v: int): self._set_limit(self._O_TFAW_LIMIT, v)

    # tCCD_L_WTR
    @property
    def tCCD_L_WTR(self) -> int:
        return self._get_timing(self._O_TCCD_L_WTR)
    @tCCD_L_WTR.setter
    def tCCD_L_WTR(self, v: int): self._set_timing(self._O_TCCD_L_WTR, v)

    @property
    def tCCD_L_WTR_ticks(self) -> int:
        return self._get_ticks(self._O_TCCD_L_WTR)

    @property
    def tCCD_L_WTR_lower_limit(self) -> int:
        return self._get_limit(self._O_TCCD_L_WTR_LIMIT)
    @tCCD_L_WTR_lower_limit.setter
    def tCCD_L_WTR_lower_limit(self, v: int): self._set_limit(self._O_TCCD_L_WTR_LIMIT, v)

    # tCCD_S_WTR
    @property
    def tCCD_S_WTR(self) -> int:
        return self._get_timing(self._O_TCCD_S_WTR)
    @tCCD_S_WTR.setter
    def tCCD_S_WTR(self, v: int): self._set_timing(self._O_TCCD_S_WTR, v)

    @property
    def tCCD_S_WTR_ticks(self) -> int:
        return self._get_ticks(self._O_TCCD_S_WTR)

    @property
    def tCCD_S_WTR_lower_limit(self) -> int:
        return self._get_limit(self._O_TCCD_S_WTR_LIMIT)
    @tCCD_S_WTR_lower_limit.setter
    def tCCD_S_WTR_lower_limit(self, v: int): self._set_limit(self._O_TCCD_S_WTR_LIMIT, v)

    # tRTP
    @property
    def tRTP(self) -> int:
        return self._get_timing(self._O_TRTP)
    @tRTP.setter
    def tRTP(self, v: int): self._set_timing(self._O_TRTP, v)

    @property
    def tRTP_ticks(self) -> int:
        return self._get_ticks(self._O_TRTP)

    @property
    def tRTP_lower_limit(self) -> int:
        return self._get_limit(self._O_TRTP_LIMIT)
    @tRTP_lower_limit.setter
    def tRTP_lower_limit(self, v: int): self._set_limit(self._O_TRTP_LIMIT, v)

    # ---- CRC ----

    @property
    def crc(self) -> int:
        return bytes_to_ushort(self._data[self._O_CHECKSUM],
                               self._data[self._O_CHECKSUM + 1])

    @crc.setter
    def crc(self, value: int):
        lo, hi = ushort_to_bytes(value)
        self._data[self._O_CHECKSUM] = lo
        self._data[self._O_CHECKSUM + 1] = hi

    def calculate_crc(self) -> int:
        """计算 XMP Profile 的 CRC-16（覆盖字节 0 ~ 0x3D）。"""
        raw = bytes(self._data[:0x3E])  # 前 0x3E 字节
        return crc16_xmodem(raw)

    def update_crc(self):
        """更新 XMP Profile 的 CRC-16 校验和。"""
        self.crc = self.calculate_crc()

    def check_crc_validity(self) -> bool:
        """验证 CRC-16 校验和是否正确。"""
        return self.crc == self.calculate_crc()

    # ---- 序列化 ----

    def get_bytes(self) -> bytes:
        """将 XMP Profile 序列化为 64 字节。"""
        return bytes(self._data)

    def is_empty(self) -> bool:
        """检查 Profile 是否全为零（空 profile）。"""
        return all(b == 0x00 for b in self._data)

    def wipe(self):
        """将 Profile 全部清零。"""
        for i in range(self.SIZE):
            self._data[i] = 0x00

    def load_sample(self):
        """加载示例默认值（与 C# LoadSample 一致）。"""
        self.min_cycle_time = 312
        self.command_rate = CommandRate.N2
        self.vdd = 110
        self.vddq = 110
        self.vpp = 180
        self.vmemctrl = 120

        # CAS Latencies
        for cl in [22, 26, 28, 30, 32, 36, 40, 42, 46, 48, 50, 52, 54, 56]:
            self._set_cl(cl, True)

        # 时序参数
        self.tAA = 16250
        self.tRCD = 16250
        self.tRP = 16250
        self.tRAS = 32000
        self.tRC = 48250
        self.tWR = 30000
        self.tRFC1 = 295
        self.tRFC2 = 160
        self.tRFC = 130
        self.tRRD_L = 5000
        self.tRRD_L_lower_limit = 8
        self.tCCD_L = 5000
        self.tCCD_L_lower_limit = 8
        self.tCCD_L_WR = 20000
        self.tCCD_L_WR_lower_limit = 32
        self.tCCD_L_WR2 = 10000
        self.tCCD_L_WR2_lower_limit = 16
        self.tFAW = 10000
        self.tFAW_lower_limit = 32
        self.tCCD_L_WTR = 10000
        self.tCCD_L_WTR_lower_limit = 16
        self.tCCD_S_WTR = 2500
        self.tCCD_S_WTR_lower_limit = 4
        self.tRTP = 7500
        self.tRTP_lower_limit = 12
        self.update_crc()

    @classmethod
    def parse(cls, profile_no: int, data: bytes) -> 'XMP_3_0':
        """从 64 字节数据解析 XMP 3.0 Profile。"""
        if len(data) != cls.SIZE:
            return None
        xmp = cls(profile_no)
        xmp._data = bytearray(data)
        return xmp


# =============================================================================
# EXPO — EXPO Profile (40 字节 per profile)
# =============================================================================

class EXPO:
    """EXPO Profile 数据模型 (40 字节 per profile)"""

    EXPO_PROFILE_SIZE = 0x28  # 40 bytes

    def __init__(self, profile_no: int = 0):
        self._data = bytearray(self.EXPO_PROFILE_SIZE)
        self.profile_no = profile_no

    # 字节偏移量
    _O_VDD = 0
    _O_VDDQ = 1
    _O_VPP = 2
    _O_UNK1 = 3
    _O_MIN_CYCLE_TIME = 4      # 2 bytes
    _O_TAA = 6                  # 2 bytes
    _O_TRCD = 8                 # 2 bytes
    _O_TRP = 10                 # 2 bytes
    _O_TRAS = 12                # 2 bytes
    _O_TRC = 14                 # 2 bytes
    _O_TWR = 16                 # 2 bytes
    _O_TRFC1 = 18               # 2 bytes
    _O_TRFC2 = 20               # 2 bytes
    _O_TRFC = 22                # 2 bytes
    _O_TRRD_L = 24              # 2 bytes
    _O_TCCD_L = 26              # 2 bytes
    _O_TCCD_L_WR = 28           # 2 bytes
    _O_TCCD_L_WR2 = 30          # 2 bytes
    _O_TFAW = 32                # 2 bytes
    _O_TCCD_L_WTR = 34          # 2 bytes
    _O_TCCD_S_WTR = 36          # 2 bytes
    _O_TRTP = 38                # 2 bytes

    # ---- 辅助方法 ----
    def _get_timing(self, offset: int) -> int:
        return bytes_to_ushort(self._data[offset], self._data[offset + 1])

    def _set_timing(self, offset: int, value: int):
        lo, hi = ushort_to_bytes(value)
        self._data[offset] = lo
        self._data[offset + 1] = hi

    def _get_ticks(self, offset: int, multiplier: int = 1) -> int:
        raw = self._get_timing(offset) * multiplier
        return time_to_ticks_ddr5(raw, self.min_cycle_time)

    # ---- 电压 ----
    @property
    def vdd(self) -> int:
        return voltage_byte_to_mv(self._data[self._O_VDD])
    @vdd.setter
    def vdd(self, v: int): self._data[self._O_VDD] = voltage_mv_to_byte(v)

    @property
    def vddq(self) -> int:
        return voltage_byte_to_mv(self._data[self._O_VDDQ])
    @vddq.setter
    def vddq(self, v: int): self._data[self._O_VDDQ] = voltage_mv_to_byte(v)

    @property
    def vpp(self) -> int:
        return voltage_byte_to_mv(self._data[self._O_VPP])
    @vpp.setter
    def vpp(self, v: int): self._data[self._O_VPP] = voltage_mv_to_byte(v)

    # ---- 频率 ----
    @property
    def min_cycle_time(self) -> int:
        return bytes_to_ushort(self._data[self._O_MIN_CYCLE_TIME],
                               self._data[self._O_MIN_CYCLE_TIME + 1])
    @min_cycle_time.setter
    def min_cycle_time(self, value: int):
        lo, hi = ushort_to_bytes(value)
        self._data[self._O_MIN_CYCLE_TIME] = lo
        self._data[self._O_MIN_CYCLE_TIME + 1] = hi

    # ---- 时序参数 ----
    # tAA
    @property
    def tAA(self) -> int: return self._get_timing(self._O_TAA)
    @tAA.setter
    def tAA(self, v: int): self._set_timing(self._O_TAA, v)
    @property
    def tAA_ticks(self) -> int: return self._get_ticks(self._O_TAA)

    # tRCD
    @property
    def tRCD(self) -> int: return self._get_timing(self._O_TRCD)
    @tRCD.setter
    def tRCD(self, v: int): self._set_timing(self._O_TRCD, v)
    @property
    def tRCD_ticks(self) -> int: return self._get_ticks(self._O_TRCD)

    # tRP
    @property
    def tRP(self) -> int: return self._get_timing(self._O_TRP)
    @tRP.setter
    def tRP(self, v: int): self._set_timing(self._O_TRP, v)
    @property
    def tRP_ticks(self) -> int: return self._get_ticks(self._O_TRP)

    # tRAS
    @property
    def tRAS(self) -> int: return self._get_timing(self._O_TRAS)
    @tRAS.setter
    def tRAS(self, v: int): self._set_timing(self._O_TRAS, v)
    @property
    def tRAS_ticks(self) -> int: return self._get_ticks(self._O_TRAS)

    # tRC
    @property
    def tRC(self) -> int: return self._get_timing(self._O_TRC)
    @tRC.setter
    def tRC(self, v: int): self._set_timing(self._O_TRC, v)
    @property
    def tRC_ticks(self) -> int: return self._get_ticks(self._O_TRC)

    # tWR
    @property
    def tWR(self) -> int: return self._get_timing(self._O_TWR)
    @tWR.setter
    def tWR(self, v: int): self._set_timing(self._O_TWR, v)
    @property
    def tWR_ticks(self) -> int: return self._get_ticks(self._O_TWR)

    # tRFC1
    @property
    def tRFC1(self) -> int: return self._get_timing(self._O_TRFC1)
    @tRFC1.setter
    def tRFC1(self, v: int): self._set_timing(self._O_TRFC1, v)
    @property
    def tRFC1_ticks(self) -> int: return self._get_ticks(self._O_TRFC1, multiplier=1000)

    # tRFC2
    @property
    def tRFC2(self) -> int: return self._get_timing(self._O_TRFC2)
    @tRFC2.setter
    def tRFC2(self, v: int): self._set_timing(self._O_TRFC2, v)
    @property
    def tRFC2_ticks(self) -> int: return self._get_ticks(self._O_TRFC2, multiplier=1000)

    # tRFC
    @property
    def tRFC(self) -> int: return self._get_timing(self._O_TRFC)
    @tRFC.setter
    def tRFC(self, v: int): self._set_timing(self._O_TRFC, v)
    @property
    def tRFC_ticks(self) -> int: return self._get_ticks(self._O_TRFC, multiplier=1000)

    # tRRD_L
    @property
    def tRRD_L(self) -> int: return self._get_timing(self._O_TRRD_L)
    @tRRD_L.setter
    def tRRD_L(self, v: int): self._set_timing(self._O_TRRD_L, v)
    @property
    def tRRD_L_ticks(self) -> int: return self._get_ticks(self._O_TRRD_L)

    # tCCD_L
    @property
    def tCCD_L(self) -> int: return self._get_timing(self._O_TCCD_L)
    @tCCD_L.setter
    def tCCD_L(self, v: int): self._set_timing(self._O_TCCD_L, v)
    @property
    def tCCD_L_ticks(self) -> int: return self._get_ticks(self._O_TCCD_L)

    # tCCD_L_WR
    @property
    def tCCD_L_WR(self) -> int: return self._get_timing(self._O_TCCD_L_WR)
    @tCCD_L_WR.setter
    def tCCD_L_WR(self, v: int): self._set_timing(self._O_TCCD_L_WR, v)
    @property
    def tCCD_L_WR_ticks(self) -> int: return self._get_ticks(self._O_TCCD_L_WR)

    # tCCD_L_WR2
    @property
    def tCCD_L_WR2(self) -> int: return self._get_timing(self._O_TCCD_L_WR2)
    @tCCD_L_WR2.setter
    def tCCD_L_WR2(self, v: int): self._set_timing(self._O_TCCD_L_WR2, v)
    @property
    def tCCD_L_WR2_ticks(self) -> int: return self._get_ticks(self._O_TCCD_L_WR2)

    # tFAW
    @property
    def tFAW(self) -> int: return self._get_timing(self._O_TFAW)
    @tFAW.setter
    def tFAW(self, v: int): self._set_timing(self._O_TFAW, v)
    @property
    def tFAW_ticks(self) -> int: return self._get_ticks(self._O_TFAW)

    # tCCD_L_WTR
    @property
    def tCCD_L_WTR(self) -> int: return self._get_timing(self._O_TCCD_L_WTR)
    @tCCD_L_WTR.setter
    def tCCD_L_WTR(self, v: int): self._set_timing(self._O_TCCD_L_WTR, v)
    @property
    def tCCD_L_WTR_ticks(self) -> int: return self._get_ticks(self._O_TCCD_L_WTR)

    # tCCD_S_WTR
    @property
    def tCCD_S_WTR(self) -> int: return self._get_timing(self._O_TCCD_S_WTR)
    @tCCD_S_WTR.setter
    def tCCD_S_WTR(self, v: int): self._set_timing(self._O_TCCD_S_WTR, v)
    @property
    def tCCD_S_WTR_ticks(self) -> int: return self._get_ticks(self._O_TCCD_S_WTR)

    # tRTP
    @property
    def tRTP(self) -> int: return self._get_timing(self._O_TRTP)
    @tRTP.setter
    def tRTP(self, v: int): self._set_timing(self._O_TRTP, v)
    @property
    def tRTP_ticks(self) -> int: return self._get_ticks(self._O_TRTP)

    # ---- 序列化 ----
    def get_bytes(self) -> bytes:
        return bytes(self._data)

    @classmethod
    def parse(cls, profile_no: int, data: bytes) -> 'EXPO':
        if len(data) != cls.EXPO_PROFILE_SIZE:
            return None
        expo = cls(profile_no)
        expo._data = bytearray(data)
        return expo


# =============================================================================
# DDR5_SPD — 主 SPD 数据模型 (1024 字节)
# =============================================================================

class DDR5_SPD:
    """DDR5 SPD 数据模型 (1024 字节)

    管理完整的 DDR5 SPD 二进制数据，包括:
      - JEDEC 基本配置 (字节 0-127)
      - 通用模组参数 (字节 192-447)
      - 制造信息 (字节 512-639)
      - XMP 3.0 Header + Profiles (字节 640-1023)
      - EXPO Block (可能在 XMP Profile 3 位置)
    """

    TOTAL_SIZE = 1024
    PART_NUMBER_SIZE = 30
    HEAT_SPREADER_BIT = 2

    # XMP 常量
    XMP_HEADER_MAGIC = b'\x0C\x4A'
    XMP_VERSION = 0x30
    XMP_OFFSET = 0x280
    XMP_PROFILE_OFFSETS = [0x2C0, 0x300, 0x340, 0x380, 0x3C0]
    XMP_PROFILE_SIZE = 0x40
    XMP_HEADER_SIZE = 0x40
    MAX_XMP_PROFILE_NAME = 16
    TOTAL_XMP_PROFILES = 5

    # EXPO 常量
    EXPO_OFFSET = 0x340
    EXPO_SIZE = 0x80
    EXPO_HEADER_MAGIC = b'EXPO'
    EXPO_PROFILE_SIZE = 0x28
    EXPO_HEADER_SIZE = 0x0A
    TOTAL_EXPO_PROFILES = 2

    def __init__(self):
        self._data = bytearray(self.TOTAL_SIZE)
        self.xmp_found = False
        self.expo_found = False
        self.xmp_profiles: list[XMP_3_0] = [
            XMP_3_0(i + 1) for i in range(self.TOTAL_XMP_PROFILES)
        ]
        self.expo_profiles: list[EXPO] = [
            EXPO(i + 1) for i in range(self.TOTAL_EXPO_PROFILES)
        ]
        # XMP Header 内部数据（字节 0x280 ~ 0x2BF）
        self._xmp_header_data = bytearray(self.XMP_HEADER_SIZE)
        # EXPO 原始块数据（字节 0x340 ~ 0x3BF）
        self._expo_raw_data = bytearray(self.EXPO_SIZE)

    # ================================================================
    # SPD 字节偏移量常量
    # ================================================================
    # Block 0-1: 基本配置 (0x00 - 0x7F)
    _O_BYTES_USED = 0
    _O_REVISION = 1
    _O_MEMORY_TYPE = 2
    _O_MODULE_TYPE = 3
    _O_FIRST_DENSITY_PACKAGE = 4
    _O_FIRST_ADDRESSING = 5
    _O_FIRST_IO_WIDTH = 6
    _O_FIRST_BANK_GROUPS = 7
    _O_SDRAM_BL32 = 12
    _O_SDRAM_DUTY_CYCLE = 13
    _O_SDRAM_FAULT_HANDLING = 14
    _O_VOLTAGE_VDD = 16
    _O_VOLTAGE_VDDQ = 17
    _O_VOLTAGE_VPP = 18
    _O_SDRAM_TIMING = 19
    _O_MIN_CYCLE_TIME = 20       # 2 bytes
    _O_MAX_CYCLE_TIME = 22       # 2 bytes
    _O_CL_SUPPORTED = 24         # 5 bytes
    _O_TAA = 30                  # 2 bytes
    _O_TRCD = 32                 # 2 bytes
    _O_TRP = 34                  # 2 bytes
    _O_TRAS = 36                 # 2 bytes
    _O_TRC = 38                  # 2 bytes
    _O_TWR = 40                  # 2 bytes
    _O_TRFC1_SLR = 42            # 2 bytes
    _O_TRFC2_SLR = 44            # 2 bytes
    _O_TRFCSB_SLR = 46           # 2 bytes
    _O_TRFC1_DLR = 48            # 2 bytes
    _O_TRFC2_DLR = 50            # 2 bytes
    _O_TRFCSB_DLR = 52           # 2 bytes
    _O_TRRD_L = 70               # 2 bytes
    _O_TRRD_L_LIMIT = 72
    _O_TCCD_L = 73               # 2 bytes
    _O_TCCD_L_LIMIT = 75
    _O_TCCD_L_WR = 76            # 2 bytes
    _O_TCCD_L_WR_LIMIT = 78
    _O_TCCD_L_WR2 = 79           # 2 bytes
    _O_TCCD_L_WR2_LIMIT = 81
    _O_TFAW = 82                 # 2 bytes
    _O_TFAW_LIMIT = 84
    _O_TCCD_L_WTR = 85           # 2 bytes
    _O_TCCD_L_WTR_LIMIT = 87
    _O_TCCD_S_WTR = 88           # 2 bytes
    _O_TCCD_S_WTR_LIMIT = 90
    _O_TRTP = 91                 # 2 bytes
    _O_TRTP_LIMIT = 93
    _O_TCCD_M = 94               # 2 bytes
    _O_TCCD_M_LIMIT = 96
    _O_TCCD_M_WR = 97            # 2 bytes
    _O_TCCD_M_WR_LIMIT = 99
    _O_TCCD_M_WTR = 100          # 2 bytes
    _O_TCCD_M_WTR_LIMIT = 102

    # Block 3: 通用模组参数 (0xC0 - 0xDF)
    _O_REVISION_COMMON = 192
    _O_HASHING_SEQUENCE = 193
    _O_DIMM_ATTRIBUTES = 233
    _O_MODULE_ORGANIZATION = 234
    _O_MEMORY_CHANNEL_BUS_WIDTH = 235

    # Block 7: 校验和 (0x1FE - 0x1FF)
    _O_CHECKSUM = 510             # 2 bytes

    # Block 8: 制造信息 (0x200 - 0x27F)
    _O_MODULE_MANUFACTURER = 512  # 2 bytes
    _O_MANUFACTURE_LOCATION = 514
    _O_MANUFACTURE_DATE = 515     # 2 bytes (year, week)
    _O_SERIAL_NUMBER = 517        # 4 bytes
    _O_MODULE_PARTNUMBER = 521    # 30 bytes
    _O_MODULE_REVISION = 551
    _O_DRAM_MANUFACTURER = 552    # 2 bytes
    _O_DRAM_STEPPING = 554

    # ================================================================
    # 内部辅助方法
    # ================================================================

    def _get_word(self, offset: int) -> int:
        return bytes_to_ushort(self._data[offset], self._data[offset + 1])

    def _set_word(self, offset: int, value: int):
        lo, hi = ushort_to_bytes(value)
        self._data[offset] = lo
        self._data[offset + 1] = hi

    def _get_ticks(self, offset: int, multiplier: int = 1) -> int:
        raw = self._get_word(offset) * multiplier
        return time_to_ticks_ddr5(raw, self.min_cycle_time)

    # ================================================================
    # 频率属性
    # ================================================================

    @property
    def min_cycle_time(self) -> int:
        return self._get_word(self._O_MIN_CYCLE_TIME)

    @min_cycle_time.setter
    def min_cycle_time(self, value: int):
        self._set_word(self._O_MIN_CYCLE_TIME, value)

    @property
    def max_cycle_time(self) -> int:
        return self._get_word(self._O_MAX_CYCLE_TIME)

    @max_cycle_time.setter
    def max_cycle_time(self, value: int):
        self._set_word(self._O_MAX_CYCLE_TIME, value)

    # ================================================================
    # CAS Latency 属性 (CL20-CL98)
    # ================================================================

    def _get_cl_view(self) -> bytearray:
        """获取 CL 支持位掩码的 5 字节视图（仅用于读取）。"""
        return self._data[self._O_CL_SUPPORTED:
                          self._O_CL_SUPPORTED + 5]

    def is_cl_supported(self, cl: int) -> bool:
        return is_cl_supported(self._get_cl_view(), cl)

    def set_cl_supported(self, cl: int, supported: bool):
        # 直接在原始 bytearray 上操作（避免切片拷贝问题）
        from ddr5_utils import _cl_to_byte_bit
        byte_idx, bit_pos = _cl_to_byte_bit(cl)
        mask = 1 << bit_pos
        offset = self._O_CL_SUPPORTED + byte_idx
        if supported:
            self._data[offset] |= mask
        else:
            self._data[offset] &= ~mask & 0xFF

    # ================================================================
    # 时序参数 (ps 值 + nCK ticks)
    # ================================================================

    # tAA
    @property
    def tAA(self) -> int: return self._get_word(self._O_TAA)
    @tAA.setter
    def tAA(self, v: int): self._set_word(self._O_TAA, v)
    @property
    def tAA_ticks(self) -> int: return self._get_ticks(self._O_TAA)

    # tRCD
    @property
    def tRCD(self) -> int: return self._get_word(self._O_TRCD)
    @tRCD.setter
    def tRCD(self, v: int): self._set_word(self._O_TRCD, v)
    @property
    def tRCD_ticks(self) -> int: return self._get_ticks(self._O_TRCD)

    # tRP
    @property
    def tRP(self) -> int: return self._get_word(self._O_TRP)
    @tRP.setter
    def tRP(self, v: int): self._set_word(self._O_TRP, v)
    @property
    def tRP_ticks(self) -> int: return self._get_ticks(self._O_TRP)

    # tRAS
    @property
    def tRAS(self) -> int: return self._get_word(self._O_TRAS)
    @tRAS.setter
    def tRAS(self, v: int): self._set_word(self._O_TRAS, v)
    @property
    def tRAS_ticks(self) -> int: return self._get_ticks(self._O_TRAS)

    # tRC
    @property
    def tRC(self) -> int: return self._get_word(self._O_TRC)
    @tRC.setter
    def tRC(self, v: int): self._set_word(self._O_TRC, v)
    @property
    def tRC_ticks(self) -> int: return self._get_ticks(self._O_TRC)

    # tWR
    @property
    def tWR(self) -> int: return self._get_word(self._O_TWR)
    @tWR.setter
    def tWR(self, v: int): self._set_word(self._O_TWR, v)
    @property
    def tWR_ticks(self) -> int: return self._get_ticks(self._O_TWR)

    # tRFC1_slr
    @property
    def tRFC1_slr(self) -> int: return self._get_word(self._O_TRFC1_SLR)
    @tRFC1_slr.setter
    def tRFC1_slr(self, v: int): self._set_word(self._O_TRFC1_SLR, v)
    @property
    def tRFC1_slr_ticks(self) -> int: return self._get_ticks(self._O_TRFC1_SLR, multiplier=1000)

    # tRFC2_slr
    @property
    def tRFC2_slr(self) -> int: return self._get_word(self._O_TRFC2_SLR)
    @tRFC2_slr.setter
    def tRFC2_slr(self, v: int): self._set_word(self._O_TRFC2_SLR, v)
    @property
    def tRFC2_slr_ticks(self) -> int: return self._get_ticks(self._O_TRFC2_SLR, multiplier=1000)

    # tRFCsb_slr
    @property
    def tRFCsb_slr(self) -> int: return self._get_word(self._O_TRFCSB_SLR)
    @tRFCsb_slr.setter
    def tRFCsb_slr(self, v: int): self._set_word(self._O_TRFCSB_SLR, v)
    @property
    def tRFCsb_slr_ticks(self) -> int: return self._get_ticks(self._O_TRFCSB_SLR, multiplier=1000)

    # tRFC1_dlr
    @property
    def tRFC1_dlr(self) -> int: return self._get_word(self._O_TRFC1_DLR)
    @tRFC1_dlr.setter
    def tRFC1_dlr(self, v: int): self._set_word(self._O_TRFC1_DLR, v)
    @property
    def tRFC1_dlr_ticks(self) -> int: return self._get_ticks(self._O_TRFC1_DLR, multiplier=1000)

    # tRFC2_dlr
    @property
    def tRFC2_dlr(self) -> int: return self._get_word(self._O_TRFC2_DLR)
    @tRFC2_dlr.setter
    def tRFC2_dlr(self, v: int): self._set_word(self._O_TRFC2_DLR, v)
    @property
    def tRFC2_dlr_ticks(self) -> int: return self._get_ticks(self._O_TRFC2_DLR, multiplier=1000)

    # tRFCsb_dlr
    @property
    def tRFCsb_dlr(self) -> int: return self._get_word(self._O_TRFCSB_DLR)
    @tRFCsb_dlr.setter
    def tRFCsb_dlr(self, v: int): self._set_word(self._O_TRFCSB_DLR, v)
    @property
    def tRFCsb_dlr_ticks(self) -> int: return self._get_ticks(self._O_TRFCSB_DLR, multiplier=1000)

    # tRRD_L
    @property
    def tRRD_L(self) -> int: return self._get_word(self._O_TRRD_L)
    @tRRD_L.setter
    def tRRD_L(self, v: int): self._set_word(self._O_TRRD_L, v)
    @property
    def tRRD_L_ticks(self) -> int: return self._get_ticks(self._O_TRRD_L)
    @property
    def tRRD_L_lower_limit(self) -> int: return self._data[self._O_TRRD_L_LIMIT]
    @tRRD_L_lower_limit.setter
    def tRRD_L_lower_limit(self, v: int): self._data[self._O_TRRD_L_LIMIT] = v & 0xFF

    # tCCD_L
    @property
    def tCCD_L(self) -> int: return self._get_word(self._O_TCCD_L)
    @tCCD_L.setter
    def tCCD_L(self, v: int): self._set_word(self._O_TCCD_L, v)
    @property
    def tCCD_L_ticks(self) -> int: return self._get_ticks(self._O_TCCD_L)
    @property
    def tCCD_L_lower_limit(self) -> int: return self._data[self._O_TCCD_L_LIMIT]
    @tCCD_L_lower_limit.setter
    def tCCD_L_lower_limit(self, v: int): self._data[self._O_TCCD_L_LIMIT] = v & 0xFF

    # tCCD_L_WR
    @property
    def tCCD_L_WR(self) -> int: return self._get_word(self._O_TCCD_L_WR)
    @tCCD_L_WR.setter
    def tCCD_L_WR(self, v: int): self._set_word(self._O_TCCD_L_WR, v)
    @property
    def tCCD_L_WR_ticks(self) -> int: return self._get_ticks(self._O_TCCD_L_WR)
    @property
    def tCCD_L_WR_lower_limit(self) -> int: return self._data[self._O_TCCD_L_WR_LIMIT]
    @tCCD_L_WR_lower_limit.setter
    def tCCD_L_WR_lower_limit(self, v: int): self._data[self._O_TCCD_L_WR_LIMIT] = v & 0xFF

    # tCCD_L_WR2
    @property
    def tCCD_L_WR2(self) -> int: return self._get_word(self._O_TCCD_L_WR2)
    @tCCD_L_WR2.setter
    def tCCD_L_WR2(self, v: int): self._set_word(self._O_TCCD_L_WR2, v)
    @property
    def tCCD_L_WR2_ticks(self) -> int: return self._get_ticks(self._O_TCCD_L_WR2)
    @property
    def tCCD_L_WR2_lower_limit(self) -> int: return self._data[self._O_TCCD_L_WR2_LIMIT]
    @tCCD_L_WR2_lower_limit.setter
    def tCCD_L_WR2_lower_limit(self, v: int): self._data[self._O_TCCD_L_WR2_LIMIT] = v & 0xFF

    # tFAW
    @property
    def tFAW(self) -> int: return self._get_word(self._O_TFAW)
    @tFAW.setter
    def tFAW(self, v: int): self._set_word(self._O_TFAW, v)
    @property
    def tFAW_ticks(self) -> int: return self._get_ticks(self._O_TFAW)
    @property
    def tFAW_lower_limit(self) -> int: return self._data[self._O_TFAW_LIMIT]
    @tFAW_lower_limit.setter
    def tFAW_lower_limit(self, v: int): self._data[self._O_TFAW_LIMIT] = v & 0xFF

    # tCCD_L_WTR
    @property
    def tCCD_L_WTR(self) -> int: return self._get_word(self._O_TCCD_L_WTR)
    @tCCD_L_WTR.setter
    def tCCD_L_WTR(self, v: int): self._set_word(self._O_TCCD_L_WTR, v)
    @property
    def tCCD_L_WTR_ticks(self) -> int: return self._get_ticks(self._O_TCCD_L_WTR)
    @property
    def tCCD_L_WTR_lower_limit(self) -> int: return self._data[self._O_TCCD_L_WTR_LIMIT]
    @tCCD_L_WTR_lower_limit.setter
    def tCCD_L_WTR_lower_limit(self, v: int): self._data[self._O_TCCD_L_WTR_LIMIT] = v & 0xFF

    # tCCD_S_WTR
    @property
    def tCCD_S_WTR(self) -> int: return self._get_word(self._O_TCCD_S_WTR)
    @tCCD_S_WTR.setter
    def tCCD_S_WTR(self, v: int): self._set_word(self._O_TCCD_S_WTR, v)
    @property
    def tCCD_S_WTR_ticks(self) -> int: return self._get_ticks(self._O_TCCD_S_WTR)
    @property
    def tCCD_S_WTR_lower_limit(self) -> int: return self._data[self._O_TCCD_S_WTR_LIMIT]
    @tCCD_S_WTR_lower_limit.setter
    def tCCD_S_WTR_lower_limit(self, v: int): self._data[self._O_TCCD_S_WTR_LIMIT] = v & 0xFF

    # tRTP
    @property
    def tRTP(self) -> int: return self._get_word(self._O_TRTP)
    @tRTP.setter
    def tRTP(self, v: int): self._set_word(self._O_TRTP, v)
    @property
    def tRTP_ticks(self) -> int: return self._get_ticks(self._O_TRTP)
    @property
    def tRTP_lower_limit(self) -> int: return self._data[self._O_TRTP_LIMIT]
    @tRTP_lower_limit.setter
    def tRTP_lower_limit(self, v: int): self._data[self._O_TRTP_LIMIT] = v & 0xFF

    # tCCD_M
    @property
    def tCCD_M(self) -> int: return self._get_word(self._O_TCCD_M)
    @tCCD_M.setter
    def tCCD_M(self, v: int): self._set_word(self._O_TCCD_M, v)
    @property
    def tCCD_M_ticks(self) -> int: return self._get_ticks(self._O_TCCD_M)
    @property
    def tCCD_M_lower_limit(self) -> int: return self._data[self._O_TCCD_M_LIMIT]
    @tCCD_M_lower_limit.setter
    def tCCD_M_lower_limit(self, v: int): self._data[self._O_TCCD_M_LIMIT] = v & 0xFF

    # tCCD_M_WR
    @property
    def tCCD_M_WR(self) -> int: return self._get_word(self._O_TCCD_M_WR)
    @tCCD_M_WR.setter
    def tCCD_M_WR(self, v: int): self._set_word(self._O_TCCD_M_WR, v)
    @property
    def tCCD_M_WR_ticks(self) -> int: return self._get_ticks(self._O_TCCD_M_WR)
    @property
    def tCCD_M_WR_lower_limit(self) -> int: return self._data[self._O_TCCD_M_WR_LIMIT]
    @tCCD_M_WR_lower_limit.setter
    def tCCD_M_WR_lower_limit(self, v: int): self._data[self._O_TCCD_M_WR_LIMIT] = v & 0xFF

    # tCCD_M_WTR
    @property
    def tCCD_M_WTR(self) -> int: return self._get_word(self._O_TCCD_M_WTR)
    @tCCD_M_WTR.setter
    def tCCD_M_WTR(self, v: int): self._set_word(self._O_TCCD_M_WTR, v)
    @property
    def tCCD_M_WTR_ticks(self) -> int: return self._get_ticks(self._O_TCCD_M_WTR)
    @property
    def tCCD_M_WTR_lower_limit(self) -> int: return self._data[self._O_TCCD_M_WTR_LIMIT]
    @tCCD_M_WTR_lower_limit.setter
    def tCCD_M_WTR_lower_limit(self, v: int): self._data[self._O_TCCD_M_WTR_LIMIT] = v & 0xFF

    # ================================================================
    # 组织/配置属性
    # ================================================================

    @property
    def banks_per_bank_group(self) -> int:
        return BANKS_PER_BANK_GROUP_MAP[self._data[self._O_FIRST_BANK_GROUPS] & 0x7]

    @banks_per_bank_group.setter
    def banks_per_bank_group(self, value: int):
        try:
            idx = BANKS_PER_BANK_GROUP_MAP.index(value)
        except ValueError:
            return
        self._data[self._O_FIRST_BANK_GROUPS] = (
            (self._data[self._O_FIRST_BANK_GROUPS] & 0xF8) | (idx & 0x7)
        )

    @property
    def bank_groups(self) -> int:
        return BANK_GROUPS_MAP[(self._data[self._O_FIRST_BANK_GROUPS] >> 5) & 0x3]

    @bank_groups.setter
    def bank_groups(self, value: int):
        try:
            idx = BANK_GROUPS_MAP.index(value)
        except ValueError:
            return
        self._data[self._O_FIRST_BANK_GROUPS] = (
            (self._data[self._O_FIRST_BANK_GROUPS] & 0x1F) | (idx << 5)
        )

    @property
    def column_addresses(self) -> int:
        return COLUMN_ADDRESS_MAP[(self._data[self._O_FIRST_ADDRESSING] >> 5) & 0x1]

    @column_addresses.setter
    def column_addresses(self, value: int):
        try:
            idx = COLUMN_ADDRESS_MAP.index(value)
        except ValueError:
            return
        self._data[self._O_FIRST_ADDRESSING] = (
            (self._data[self._O_FIRST_ADDRESSING] & 0x1F) | (idx << 5)
        )

    @property
    def row_addresses(self) -> int:
        return ROW_ADDRESS_MAP[self._data[self._O_FIRST_ADDRESSING] & 0x1F]

    @row_addresses.setter
    def row_addresses(self, value: int):
        try:
            idx = ROW_ADDRESS_MAP.index(value)
        except ValueError:
            return
        self._data[self._O_FIRST_ADDRESSING] = (
            (self._data[self._O_FIRST_ADDRESSING] & 0xE0) | idx
        )

    @property
    def device_width(self) -> int:
        return DEVICE_WIDTH_MAP[(self._data[self._O_FIRST_IO_WIDTH] >> 5) & 0x3]

    @device_width.setter
    def device_width(self, value: int):
        try:
            idx = DEVICE_WIDTH_MAP.index(value)
        except ValueError:
            return
        self._data[self._O_FIRST_IO_WIDTH] = (
            (self._data[self._O_FIRST_IO_WIDTH] & 0x1F) | (idx << 5)
        )

    @property
    def density(self) -> Density:
        idx = self._data[self._O_FIRST_DENSITY_PACKAGE] & 0xF
        if idx >= len(DENSITY_MAP):
            return None
        return DENSITY_MAP[idx]

    @density.setter
    def density(self, value: Density):
        if value is not None:
            idx = DENSITY_MAP.index(value) if value in DENSITY_MAP else 0
            self._data[self._O_FIRST_DENSITY_PACKAGE] = (
                (self._data[self._O_FIRST_DENSITY_PACKAGE] & 0xF0) | (idx & 0xF)
            )

    @property
    def form_factor(self) -> FormFactor:
        idx = self._data[self._O_MODULE_TYPE] & 0xF
        if idx >= len(FORM_FACTOR_MAP):
            return None
        return FORM_FACTOR_MAP[idx]

    @form_factor.setter
    def form_factor(self, value: FormFactor):
        if value is not None:
            idx = FORM_FACTOR_MAP.index(value) if value in FORM_FACTOR_MAP else 0
            self._data[self._O_MODULE_TYPE] = (
                (self._data[self._O_MODULE_TYPE] & 0xF0) | (idx & 0xF)
            )

    # ================================================================
    # 制造信息
    # ================================================================

    @property
    def manufacturing_year(self) -> int:
        """制造年份 (BCD 编码, 如 0x22 = 2022)"""
        return int(f"{self._data[self._O_MANUFACTURE_DATE]:02X}")

    @manufacturing_year.setter
    def manufacturing_year(self, value: int):
        if value > 99:
            value = 99
        self._data[self._O_MANUFACTURE_DATE] = int(f"{value:02d}", 16)

    @property
    def manufacturing_week(self) -> int:
        """制造周数 (BCD 编码, 如 0x10 = Week 10)"""
        return int(f"{self._data[self._O_MANUFACTURE_DATE + 1]:02X}")

    @manufacturing_week.setter
    def manufacturing_week(self, value: int):
        if value > 52:
            value = 52
        self._data[self._O_MANUFACTURE_DATE + 1] = int(f"{value:02d}", 16)

    @property
    def part_number(self) -> str:
        """模组料号 (最多 30 字符 ASCII)"""
        raw = self._data[self._O_MODULE_PARTNUMBER:
                         self._O_MODULE_PARTNUMBER + self.PART_NUMBER_SIZE]
        # 去除尾部的 null 字节
        return raw.rstrip(b'\x00').decode('ascii', errors='replace')

    @part_number.setter
    def part_number(self, value: str):
        max_size = self.PART_NUMBER_SIZE
        encoded = value[:max_size].encode('ascii', errors='replace')
        start = self._O_MODULE_PARTNUMBER
        for i in range(max_size):
            if i < len(encoded):
                self._data[start + i] = encoded[i]
            else:
                self._data[start + i] = 0

    @property
    def heat_spreader(self) -> bool:
        return get_bit(self._data[self._O_DIMM_ATTRIBUTES],
                       self.HEAT_SPREADER_BIT)

    @heat_spreader.setter
    def heat_spreader(self, value: bool):
        self._data[self._O_DIMM_ATTRIBUTES] = set_bit(
            self._data[self._O_DIMM_ATTRIBUTES],
            self.HEAT_SPREADER_BIT, value)

    @property
    def operating_temperature_range(self) -> OperatingTempRange:
        return OperatingTempRange(self._data[self._O_DIMM_ATTRIBUTES] >> 4)

    # ================================================================
    # CRC
    # ================================================================

    @property
    def crc(self) -> int:
        return bytes_to_ushort(self._data[self._O_CHECKSUM],
                               self._data[self._O_CHECKSUM + 1])

    @crc.setter
    def crc(self, value: int):
        lo, hi = ushort_to_bytes(value)
        self._data[self._O_CHECKSUM] = lo
        self._data[self._O_CHECKSUM + 1] = hi

    # ================================================================
    # XMP Header 属性 (内部 _xmp_header_data)
    # ================================================================
    # XMP Header 布局:
    #   0: magic1 (0x0C)
    #   1: magic2 (0x4A)
    #   2: version (0x30)
    #   3: profileEnabled
    #   4-13: unknown[10]
    #   14-29: profileName1[16]
    #   30-45: profileName2[16]
    #   46-61: profileName3[16]
    #   62-63: checksum[2]

    _O_XH_PROFILE_ENABLED = 3
    _O_XH_PROFILE_NAME1 = 14
    _O_XH_PROFILE_NAME2 = 30
    _O_XH_PROFILE_NAME3 = 46
    _O_XH_CHECKSUM = 62

    def _read_xmp_name(self, offset: int) -> str:
        raw = self._xmp_header_data[offset:offset + self.MAX_XMP_PROFILE_NAME]
        return raw.rstrip(b'\x00').decode('ascii', errors='replace')

    def _write_xmp_name(self, offset: int, value: str):
        max_size = self.MAX_XMP_PROFILE_NAME
        encoded = value[:max_size].encode('ascii', errors='replace')
        for i in range(max_size):
            if i < len(encoded):
                self._xmp_header_data[offset + i] = encoded[i]
            else:
                self._xmp_header_data[offset + i] = 0

    @property
    def xmp1_enabled(self) -> bool:
        return bool(self._xmp_header_data[self._O_XH_PROFILE_ENABLED] & 0x1)

    @xmp1_enabled.setter
    def xmp1_enabled(self, value: bool):
        if value:
            self._xmp_header_data[self._O_XH_PROFILE_ENABLED] |= 0x1
        else:
            self._xmp_header_data[self._O_XH_PROFILE_ENABLED] &= 0xFE

    @property
    def xmp2_enabled(self) -> bool:
        return bool(self._xmp_header_data[self._O_XH_PROFILE_ENABLED] & 0x2)

    @xmp2_enabled.setter
    def xmp2_enabled(self, value: bool):
        if value:
            self._xmp_header_data[self._O_XH_PROFILE_ENABLED] |= 0x2
        else:
            self._xmp_header_data[self._O_XH_PROFILE_ENABLED] &= 0xFD

    @property
    def xmp3_enabled(self) -> bool:
        return bool(self._xmp_header_data[self._O_XH_PROFILE_ENABLED] & 0x4)

    @xmp3_enabled.setter
    def xmp3_enabled(self, value: bool):
        if not self.expo_found:
            if value:
                self._xmp_header_data[self._O_XH_PROFILE_ENABLED] |= 0x4
            else:
                self._xmp_header_data[self._O_XH_PROFILE_ENABLED] &= 0xFB

    @property
    def xmp_user1_exists(self) -> bool:
        if self.xmp_profiles[3] is None or self.expo_found:
            return False
        return (self.xmp_profiles[3].check_crc_validity() and
                not self.xmp_profiles[3].is_empty())

    @property
    def xmp_user1_enabled(self) -> bool:
        if self.xmp_profiles[3] is None or self.expo_found:
            return False
        return self.xmp_user1_exists

    @xmp_user1_enabled.setter
    def xmp_user1_enabled(self, value: bool):
        if not self.expo_found:
            if value:
                if not self.xmp_user1_exists:
                    self.xmp_profiles[3].load_sample()
            else:
                self.xmp_profiles[3].wipe()

    @property
    def xmp_user2_exists(self) -> bool:
        if self.xmp_profiles[4] is None:
            return False
        return (self.xmp_profiles[4].check_crc_validity() and
                not self.xmp_profiles[4].is_empty())

    @property
    def xmp_user2_enabled(self) -> bool:
        if self.xmp_profiles[4] is None:
            return False
        return self.xmp_user2_exists

    @xmp_user2_enabled.setter
    def xmp_user2_enabled(self, value: bool):
        if value:
            if not self.xmp_user2_exists:
                self.xmp_profiles[4].load_sample()
        else:
            self.xmp_profiles[4].wipe()

    @property
    def xmp_profile1_name(self) -> str:
        return self._read_xmp_name(self._O_XH_PROFILE_NAME1)

    @xmp_profile1_name.setter
    def xmp_profile1_name(self, value: str):
        self._write_xmp_name(self._O_XH_PROFILE_NAME1, value)

    @property
    def xmp_profile2_name(self) -> str:
        return self._read_xmp_name(self._O_XH_PROFILE_NAME2)

    @xmp_profile2_name.setter
    def xmp_profile2_name(self, value: str):
        self._write_xmp_name(self._O_XH_PROFILE_NAME2, value)

    @property
    def xmp_profile3_name(self) -> str:
        return self._read_xmp_name(self._O_XH_PROFILE_NAME3)

    @xmp_profile3_name.setter
    def xmp_profile3_name(self, value: str):
        self._write_xmp_name(self._O_XH_PROFILE_NAME3, value)

    @property
    def xmp_header_crc(self) -> int:
        return bytes_to_ushort(
            self._xmp_header_data[self._O_XH_CHECKSUM],
            self._xmp_header_data[self._O_XH_CHECKSUM + 1])

    @xmp_header_crc.setter
    def xmp_header_crc(self, value: int):
        lo, hi = ushort_to_bytes(value)
        self._xmp_header_data[self._O_XH_CHECKSUM] = lo
        self._xmp_header_data[self._O_XH_CHECKSUM + 1] = hi

    # ================================================================
    # EXPO 属性
    # ================================================================

    @property
    def expo1_enabled(self) -> bool:
        """EXPO Profile 1 是否启用 (enabledProfiles bit0)。"""
        return self.expo_found and bool(self._expo_raw_data[5] & 0x1)

    @expo1_enabled.setter
    def expo1_enabled(self, value: bool):
        if value:
            self._expo_raw_data[5] |= 0x1
        else:
            self._expo_raw_data[5] &= 0xFE

    @property
    def expo2_enabled(self) -> bool:
        """EXPO Profile 2 是否启用 (enabledProfiles bit1)。"""
        return self.expo_found and bool(self._expo_raw_data[5] & 0x2)

    @expo2_enabled.setter
    def expo2_enabled(self, value: bool):
        if value:
            self._expo_raw_data[5] |= 0x2
        else:
            self._expo_raw_data[5] &= 0xFD

    @property
    def expo_crc(self) -> int:
        """EXPO 块 CRC（字节 0x7E-0x7F of EXPO block）"""
        return bytes_to_ushort(
            self._expo_raw_data[0x7E],
            self._expo_raw_data[0x7F])

    @expo_crc.setter
    def expo_crc(self, value: int):
        lo, hi = ushort_to_bytes(value)
        self._expo_raw_data[0x7E] = lo
        self._expo_raw_data[0x7F] = hi

    # ================================================================
    # XMP Profile 快捷访问
    # ================================================================

    @property
    def xmp1(self) -> XMP_3_0: return self.xmp_profiles[0]
    @xmp1.setter
    def xmp1(self, v: XMP_3_0): self.xmp_profiles[0] = v

    @property
    def xmp2(self) -> XMP_3_0: return self.xmp_profiles[1]
    @xmp2.setter
    def xmp2(self, v: XMP_3_0): self.xmp_profiles[1] = v

    @property
    def xmp3(self) -> XMP_3_0: return self.xmp_profiles[2]
    @xmp3.setter
    def xmp3(self, v: XMP_3_0): self.xmp_profiles[2] = v

    @property
    def xmp_user1(self) -> XMP_3_0: return self.xmp_profiles[3]
    @xmp_user1.setter
    def xmp_user1(self, v: XMP_3_0): self.xmp_profiles[3] = v

    @property
    def xmp_user2(self) -> XMP_3_0: return self.xmp_profiles[4]
    @xmp_user2.setter
    def xmp_user2(self, v: XMP_3_0): self.xmp_profiles[4] = v

    @property
    def expo1(self) -> EXPO: return self.expo_profiles[0]
    @expo1.setter
    def expo1(self, v: EXPO): self.expo_profiles[0] = v

    @property
    def expo2(self) -> EXPO: return self.expo_profiles[1]
    @expo2.setter
    def expo2(self, v: EXPO): self.expo_profiles[1] = v

    # ================================================================
    # XMP Profile 管理
    # ================================================================

    def copy_xmp_profile(self, source: int, target: int) -> bool:
        """复制 XMP Profile 数据。"""
        if source == target:
            return False

        profile_map = {
            1: (self.xmp1, lambda: self.xmp_profile1_name),
            2: (self.xmp2, lambda: self.xmp_profile2_name),
            3: (self.xmp3, lambda: self.xmp_profile3_name),
            4: (self.xmp_user1, lambda: "User 1"),
            5: (self.xmp_user2, lambda: "User 2"),
        }

        if source not in profile_map or target not in profile_map:
            return False

        src_profile, src_name_fn = profile_map[source]
        src_bytes = src_profile.get_bytes()
        profile_name = src_name_fn()

        # 创建新的 profile 副本
        new_profile = XMP_3_0.parse(target, src_bytes)

        if target == 1:
            self.xmp1 = new_profile
            self.xmp1_enabled = True
            self.xmp_profile1_name = profile_name
        elif target == 2:
            self.xmp2 = new_profile
            self.xmp2_enabled = True
            self.xmp_profile2_name = profile_name
        elif target == 3:
            self.xmp3 = new_profile
            self.xmp3_enabled = True
            self.xmp_profile3_name = profile_name
        elif target == 4:
            self.xmp_user1 = new_profile
            self.xmp_user1.update_crc()
        elif target == 5:
            self.xmp_user2 = new_profile
            self.xmp_user2.update_crc()

        self.update_crc()
        return True

    # ================================================================
    # EXPO 初始化
    # ================================================================

    def init_expo(self):
        """初始化 EXPO 数据块（从无到有创建 EXPO）。

        将 EXPO header + 2 个默认 profile 写入 _expo_raw_data，
        设置 expo_found = True，并自动禁用冲突的 XMP Profile 3 和 User Profile 1。
        """
        # 1. 初始化 EXPO raw data（128 bytes）
        self._expo_raw_data = bytearray(self.EXPO_SIZE)

        # Magic "EXPO"
        self._expo_raw_data[0] = 0x45  # 'E'
        self._expo_raw_data[1] = 0x58  # 'X'
        self._expo_raw_data[2] = 0x50  # 'P'
        self._expo_raw_data[3] = 0x4F  # 'O'

        # Revision
        self._expo_raw_data[4] = 0x10

        # Enabled Profiles: bit0=prof1, bit1=prof2 → 0x03 = both enabled
        # Upper nibble mirrors lower (per spec)
        self._expo_raw_data[5] = 0x33  # both enabled

        # Enhanced Timings flag: 0 = simple timings only
        self._expo_raw_data[6] = 0x00

        # Reserved bytes 7-9 (already 0)

        # 2. 创建默认 EXPO Profile 1（DDR5-6000, 1.25V）
        expo1_defaults = {
            'vdd': 125, 'vddq': 125, 'vpp': 180,
            'min_cycle_time': 333,    # DDR5-6000
            'tAA': 16000, 'tRCD': 16000, 'tRP': 16000,
            'tRAS': 32000, 'tRC': 48000, 'tWR': 30000,
            'tRFC1': 295, 'tRFC2': 160, 'tRFC': 130,
            'tRRD_L': 5000, 'tCCD_L': 5000,
            'tCCD_L_WR': 20000, 'tCCD_L_WR2': 10000,
            'tFAW': 10000, 'tCCD_L_WTR': 10000,
            'tCCD_S_WTR': 2500, 'tRTP': 7500,
        }
        self.expo1 = EXPO(1)
        for attr, val in expo1_defaults.items():
            setattr(self.expo1, attr, val)

        # 3. 创建默认 EXPO Profile 2（DDR5-5600, 1.20V）
        expo2_defaults = {
            'vdd': 120, 'vddq': 120, 'vpp': 180,
            'min_cycle_time': 357,    # DDR5-5600
            'tAA': 16428, 'tRCD': 16428, 'tRP': 16428,
            'tRAS': 32000, 'tRC': 48428, 'tWR': 30000,
            'tRFC1': 295, 'tRFC2': 160, 'tRFC': 130,
            'tRRD_L': 5000, 'tCCD_L': 5000,
            'tCCD_L_WR': 20000, 'tCCD_L_WR2': 10000,
            'tFAW': 10000, 'tCCD_L_WTR': 10000,
            'tCCD_S_WTR': 2500, 'tRTP': 7500,
        }
        self.expo2 = EXPO(2)
        for attr, val in expo2_defaults.items():
            setattr(self.expo2, attr, val)

        # 4. 将 EXPO profiles 写入 _expo_raw_data
        p1_bytes = self.expo1.get_bytes()
        p2_bytes = self.expo2.get_bytes()
        self._expo_raw_data[self.EXPO_HEADER_SIZE:
                            self.EXPO_HEADER_SIZE + self.EXPO_PROFILE_SIZE] = p1_bytes
        self._expo_raw_data[self.EXPO_HEADER_SIZE + self.EXPO_PROFILE_SIZE:
                            self.EXPO_HEADER_SIZE + 2 * self.EXPO_PROFILE_SIZE] = p2_bytes

        # 5. 标记 EXPO 存在
        self.expo_found = True

        # 6. 禁用与 EXPO 冲突的 XMP Profile 3 和 User Profile 1
        self.xmp3 = XMP_3_0(3)
        self.xmp_user1 = XMP_3_0(4)
        # 从 XMP header 中清除对应的 enable bits
        self._xmp_header_data[3] &= 0xFB  # 清除 bit 2 (XMP3)
        # XMP3 的 SPD 区域（0x340-0x37F）已被 EXPO block 覆盖

        # 7. 更新 EXPO CRC
        self._update_expo_crc()

        # 8. 如果 XMP header 存在，更新 XMP header CRC
        if self.xmp_found:
            self._update_xmp_header_crc()

        # 9. 更新 JEDEC CRC
        raw_spd = bytes(self._data[:0x1FE])
        self.crc = crc16_xmodem(raw_spd)

    # ================================================================
    # CRC 更新
    # ================================================================

    def _update_xmp_header_crc(self):
        """更新 XMP Header 的 CRC（覆盖字节 0 ~ 0x3D）。"""
        raw = bytes(self._xmp_header_data[:0x3E])
        self.xmp_header_crc = crc16_xmodem(raw)

    def _update_expo_crc(self):
        """更新 EXPO 块的 CRC（覆盖字节 0 ~ 0x7D）。"""
        raw = bytes(self._expo_raw_data[:0x7E])
        self.expo_crc = crc16_xmodem(raw)

    def update_crc(self):
        """更新所有 CRC 校验和。"""
        # 1. JEDEC block CRC (bytes 0-509)
        raw_spd = bytes(self._data[:0x1FE])
        self.crc = crc16_xmodem(raw_spd)

        if self.xmp_found:
            self._update_xmp_header_crc()

            # 更新启用的 XMP Profile CRC
            if self.xmp1_enabled:
                self.xmp1.update_crc()
            if self.xmp2_enabled:
                self.xmp2.update_crc()
            if self.xmp3_enabled and not self.expo_found:
                self.xmp3.update_crc()
            if self.xmp_user1_enabled and not self.expo_found:
                self.xmp_user1.update_crc()
            if self.xmp_user2_enabled:
                self.xmp_user2.update_crc()

        if self.expo_found:
            self._update_expo_crc()

    # ================================================================
    # 序列化 / 反序列化
    # ================================================================

    def get_bytes(self) -> bytes:
        """将整个 SPD 序列化为 1024 字节。

        包括 JEDEC 区域 + XMP Header + XMP/EXPO Profiles。
        """
        result = bytearray(self._data)

        # 写入 XMP Header
        result[self.XMP_OFFSET:self.XMP_OFFSET + self.XMP_HEADER_SIZE] = \
            self._xmp_header_data

        # 写入 XMP Profiles
        for i in range(min(5, len(self.xmp_profiles))):
            profile_bytes = self.xmp_profiles[i].get_bytes()
            offset = self.XMP_PROFILE_OFFSETS[i]
            result[offset:offset + self.XMP_PROFILE_SIZE] = profile_bytes

        # EXPO 处理
        if self.expo_found:
            # 将 EXPO profiles 数据合并到 EXPO 原始块
            self._expo_raw_data[self.EXPO_HEADER_SIZE:
                                self.EXPO_HEADER_SIZE + self.EXPO_PROFILE_SIZE] = \
                self.expo1.get_bytes()
            self._expo_raw_data[self.EXPO_HEADER_SIZE + self.EXPO_PROFILE_SIZE:
                                self.EXPO_HEADER_SIZE + 2 * self.EXPO_PROFILE_SIZE] = \
                self.expo2.get_bytes()
            result[self.EXPO_OFFSET:self.EXPO_OFFSET + self.EXPO_SIZE] = \
                self._expo_raw_data

        return bytes(result)

    def _parse_xmp(self, data: bytes):
        """从 SPD 数据中解析 XMP 3.0 区域。"""
        xmp_area = data[self.XMP_OFFSET:]

        # 读取 XMP Header
        self._xmp_header_data = bytearray(xmp_area[:self.XMP_HEADER_SIZE])

        # 解析 XMP Profiles
        profiles_data = xmp_area[self.XMP_HEADER_SIZE:]
        self.xmp1 = XMP_3_0.parse(1, profiles_data[:self.XMP_PROFILE_SIZE])
        self.xmp2 = XMP_3_0.parse(2, profiles_data[
            self.XMP_PROFILE_SIZE:2 * self.XMP_PROFILE_SIZE])

        if self.expo_found:
            self.xmp3 = XMP_3_0()
            self.xmp_user1 = XMP_3_0()
        else:
            self.xmp3 = XMP_3_0.parse(3, profiles_data[
                2 * self.XMP_PROFILE_SIZE:3 * self.XMP_PROFILE_SIZE])
            self.xmp_user1 = XMP_3_0.parse(4, profiles_data[
                3 * self.XMP_PROFILE_SIZE:4 * self.XMP_PROFILE_SIZE])

        self.xmp_user2 = XMP_3_0.parse(5, profiles_data[
            4 * self.XMP_PROFILE_SIZE:5 * self.XMP_PROFILE_SIZE])

    def _parse_expo(self, data: bytes):
        """从 SPD 数据中解析 EXPO 区域。"""
        expo_area = data[self.EXPO_OFFSET:
                         self.EXPO_OFFSET + self.EXPO_SIZE]
        self._expo_raw_data = bytearray(expo_area)

        profile1_data = expo_area[self.EXPO_HEADER_SIZE:
                                  self.EXPO_HEADER_SIZE + self.EXPO_PROFILE_SIZE]
        profile2_data = expo_area[self.EXPO_HEADER_SIZE + self.EXPO_PROFILE_SIZE:
                                  self.EXPO_HEADER_SIZE + 2 * self.EXPO_PROFILE_SIZE]

        self.expo1 = EXPO.parse(1, profile1_data)
        self.expo2 = EXPO.parse(2, profile2_data)

    @classmethod
    def parse(cls, data: bytes) -> 'DDR5_SPD':
        """从 1024 字节数据解析 DDR5 SPD。

        Args:
            data: 1024 字节的 SPD 二进制数据

        Returns:
            DDR5_SPD 实例，解析失败返回 None
        """
        if len(data) != cls.TOTAL_SIZE:
            raise ValueError(f"SPD 必须是 {cls.TOTAL_SIZE} 字节，实际为 {len(data)} 字节")

        spd = cls()
        spd._data = bytearray(data)

        # 验证内存类型 (Byte 2: 0x12 = DDR5)
        if spd._data[cls._O_MEMORY_TYPE] != 0x12:
            raise ValueError("SPD 不是 DDR5 类型 (Byte 2 != 0x12)，不支持")

        # 验证模组类型 (仅支持 UDIMM 0x02 和 SODIMM 0x03)
        module_type = spd._data[cls._O_MODULE_TYPE]
        if module_type not in (0x02, 0x03):
            raise ValueError(
                f"SPD 模组类型不是 UDIMM/SODIMM (Byte 3 = 0x{module_type:02X})，不支持")

        # 检测 XMP 3.0
        xmp_magic = data[cls.XMP_OFFSET:cls.XMP_OFFSET + 2]
        xmp_version = data[cls.XMP_OFFSET + 2]
        spd.xmp_found = (xmp_magic == cls.XMP_HEADER_MAGIC and
                         xmp_version == cls.XMP_VERSION)

        # 检测 EXPO
        expo_magic = data[cls.EXPO_OFFSET:cls.EXPO_OFFSET + 4]
        spd.expo_found = (expo_magic == cls.EXPO_HEADER_MAGIC)

        # 解析 EXPO
        spd._parse_expo(data)

        # 解析 XMP
        spd._parse_xmp(data)

        return spd
