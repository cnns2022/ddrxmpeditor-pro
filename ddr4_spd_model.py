#!/usr/bin/env python3
"""
DDR4 XMP Editor — DDR4 SPD + XMP 2.0 数据模型
==============================================
DDR4 SPD (512 bytes) + XMP 2.0 Profile (47 bytes)。

DDR4 与 DDR5 的关键差异:
  - SPD: 512 字节 (DDR5 1024)
  - Byte 2: 0x0C = DDR4
  - 时序编码: MTB (0.125ns) / FTB (0.001ns)
  - CRC: CRC-16/XMODEM (poly 0x1021) per JEDEC 21-C Annex L §8.1.53
  - XMP 2.0: 47 字节 per profile, 2 profiles
  - 无 EXPO
"""

import enum
from ddr5_utils import bytes_to_ushort, ushort_to_bytes, get_bit, set_bit, crc16_xmodem


# =============================================================================
# CRC-16/ARC (DDR4) — 保留供外部使用，本模块 SPD CRC 已改用 crc16_xmodem
# =============================================================================

def crc16_arc(data: bytes) -> int:
    """CRC-16/ARC（多项式 0x8005，reflected）。注意：DDR4 SPD 规范要求 crc16_xmodem(0x1021)，此函数不应用于 SPD CRC。"""
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


# =============================================================================
# DDR4 时序转换 (MTB/FTB)
# =============================================================================

MTB_NS = 0.125   # Medium Timebase
FTB_NS = 0.001   # Fine Timebase


def ticks_to_ns(ticks: int, mtb: float = MTB_NS) -> float:
    """将 DDR4 MTB ticks 转换为纳秒。"""
    return ticks * mtb


def ns_to_ticks(ns: float, mtb: float = MTB_NS) -> int:
    """将纳秒转换为 DDR4 MTB ticks（向上取整）。"""
    return int(ns / mtb + 0.9999)


def ticks_with_ftb(base_ticks: int, ftb_raw: int, mtb: float = MTB_NS, ftb: float = FTB_NS) -> float:
    """计算带 FTB 修正的精确时间 (ns)。

    DDR4 用 signed FTB 修正 MTB 值:
      actual_ns = (base_ticks * MTB) + (ftb_raw * FTB)
    """
    return (base_ticks * mtb) + (ftb_raw * ftb)


def ftb_ns_to_ps(ftb_raw: int) -> int:
    """FTB 原始值 → ps (仅用于显示参考)。"""
    return round(ftb_raw * FTB_NS * 1000)


# =============================================================================
# DDR4 Speed Bins (from JESD79-4D)
# =============================================================================

DDR4_SPEED_BINS = {
    "DDR4-1600J": {
        "mt_s": 1600, "tCKmin_ns": 1.250, "tCKmax_ns": 1.600,
        "CL": 10, "supported_cl": [9, 10, 11, 12],
        "tAA_ns": 12.50, "tRCD_ns": 12.50, "tRP_ns": 12.50,
        "tRAS_ns": 35.00, "tRC_ns": 47.50, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 5.00, "tRRD_L_ns": 6.00,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 25.00,
    },
    "DDR4-1600K": {
        "mt_s": 1600, "tCKmin_ns": 1.250, "tCKmax_ns": 1.600,
        "CL": 11, "supported_cl": [9, 11, 12],
        "tAA_ns": 13.75, "tRCD_ns": 13.75, "tRP_ns": 13.75,
        "tRAS_ns": 35.00, "tRC_ns": 48.75, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 5.00, "tRRD_L_ns": 6.00,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 25.00,
    },
    "DDR4-1600L": {
        "mt_s": 1600, "tCKmin_ns": 1.250, "tCKmax_ns": 1.600,
        "CL": 12, "supported_cl": [10, 12],
        "tAA_ns": 15.00, "tRCD_ns": 15.00, "tRP_ns": 15.00,
        "tRAS_ns": 35.00, "tRC_ns": 50.00, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 5.00, "tRRD_L_ns": 6.00,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 25.00,
    },
    "DDR4-1866L": {
        "mt_s": 1866, "tCKmin_ns": 1.071, "tCKmax_ns": 1.600,
        "CL": 12, "supported_cl": [9, 10, 12, 13, 14],
        "tAA_ns": 12.85, "tRCD_ns": 12.85, "tRP_ns": 12.85,
        "tRAS_ns": 34.00, "tRC_ns": 46.85, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 4.20, "tRRD_L_ns": 5.30,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 23.00,
    },
    "DDR4-1866M": {
        "mt_s": 1866, "tCKmin_ns": 1.071, "tCKmax_ns": 1.600,
        "CL": 13, "supported_cl": [9, 11, 12, 13, 14],
        "tAA_ns": 13.92, "tRCD_ns": 13.92, "tRP_ns": 13.92,
        "tRAS_ns": 34.00, "tRC_ns": 47.92, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 4.20, "tRRD_L_ns": 5.30,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 23.00,
    },
    "DDR4-1866N": {
        "mt_s": 1866, "tCKmin_ns": 1.071, "tCKmax_ns": 1.600,
        "CL": 14, "supported_cl": [10, 12, 14],
        "tAA_ns": 15.00, "tRCD_ns": 15.00, "tRP_ns": 15.00,
        "tRAS_ns": 34.00, "tRC_ns": 49.00, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 4.20, "tRRD_L_ns": 5.30,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 23.00,
    },
    "DDR4-2133N": {
        "mt_s": 2133, "tCKmin_ns": 0.938, "tCKmax_ns": 1.600,
        "CL": 14, "supported_cl": [9, 10, 12, 14, 15, 16],
        "tAA_ns": 13.13, "tRCD_ns": 13.13, "tRP_ns": 13.13,
        "tRAS_ns": 33.00, "tRC_ns": 46.13, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 3.70, "tRRD_L_ns": 5.30,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 21.00,
    },
    "DDR4-2133P": {
        "mt_s": 2133, "tCKmin_ns": 0.938, "tCKmax_ns": 1.600,
        "CL": 15, "supported_cl": [9, 11, 12, 13, 14, 15, 16],
        "tAA_ns": 14.06, "tRCD_ns": 14.06, "tRP_ns": 14.06,
        "tRAS_ns": 33.00, "tRC_ns": 47.06, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 3.70, "tRRD_L_ns": 5.30,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 21.00,
    },
    "DDR4-2133R": {
        "mt_s": 2133, "tCKmin_ns": 0.938, "tCKmax_ns": 1.600,
        "CL": 16, "supported_cl": [10, 12, 14, 16],
        "tAA_ns": 15.00, "tRCD_ns": 15.00, "tRP_ns": 15.00,
        "tRAS_ns": 33.00, "tRC_ns": 48.00, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 3.70, "tRRD_L_ns": 5.30,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 21.00,
    },
    "DDR4-2400P": {
        "mt_s": 2400, "tCKmin_ns": 0.833, "tCKmax_ns": 1.600,
        "CL": 15, "supported_cl": list(range(9, 18+1)),
        "tAA_ns": 12.50, "tRCD_ns": 12.50, "tRP_ns": 12.50,
        "tRAS_ns": 32.00, "tRC_ns": 44.50, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 3.30, "tRRD_L_ns": 4.90,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 21.00,
    },
    "DDR4-2400R": {
        "mt_s": 2400, "tCKmin_ns": 0.833, "tCKmax_ns": 1.600,
        "CL": 16, "supported_cl": list(range(9, 18+1)),
        "tAA_ns": 13.33, "tRCD_ns": 13.33, "tRP_ns": 13.33,
        "tRAS_ns": 32.00, "tRC_ns": 45.32, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 3.30, "tRRD_L_ns": 4.90,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 21.00,
    },
    "DDR4-2400T": {
        "mt_s": 2400, "tCKmin_ns": 0.833, "tCKmax_ns": 1.600,
        "CL": 17, "supported_cl": [10, 11, 12, 14, 16, 18],
        "tAA_ns": 14.16, "tRCD_ns": 14.16, "tRP_ns": 14.16,
        "tRAS_ns": 32.00, "tRC_ns": 46.16, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 3.30, "tRRD_L_ns": 4.90,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 21.00,
    },
    "DDR4-2400U": {
        "mt_s": 2400, "tCKmin_ns": 0.833, "tCKmax_ns": 1.600,
        "CL": 18, "supported_cl": [10, 12, 14, 16, 18],
        "tAA_ns": 15.00, "tRCD_ns": 15.00, "tRP_ns": 15.00,
        "tRAS_ns": 32.00, "tRC_ns": 47.00, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 3.30, "tRRD_L_ns": 4.90,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 21.00,
    },
    "DDR4-2666T": {
        "mt_s": 2666, "tCKmin_ns": 0.750, "tCKmax_ns": 1.600,
        "CL": 17, "supported_cl": list(range(9, 20+1)),
        "tAA_ns": 12.75, "tRCD_ns": 12.75, "tRP_ns": 12.75,
        "tRAS_ns": 32.00, "tRC_ns": 44.75, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 3.00, "tRRD_L_ns": 4.90,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 21.00,
    },
    "DDR4-2666U": {
        "mt_s": 2666, "tCKmin_ns": 0.750, "tCKmax_ns": 1.600,
        "CL": 18, "supported_cl": list(range(9, 20+1)),
        "tAA_ns": 13.50, "tRCD_ns": 13.50, "tRP_ns": 13.50,
        "tRAS_ns": 32.00, "tRC_ns": 45.50, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 3.00, "tRRD_L_ns": 4.90,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 21.00,
    },
    "DDR4-2666V": {
        "mt_s": 2666, "tCKmin_ns": 0.750, "tCKmax_ns": 1.600,
        "CL": 19, "supported_cl": list(range(10, 20+1)),
        "tAA_ns": 14.25, "tRCD_ns": 14.25, "tRP_ns": 14.25,
        "tRAS_ns": 32.00, "tRC_ns": 46.25, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 3.00, "tRRD_L_ns": 4.90,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 21.00,
    },
    "DDR4-2666W": {
        "mt_s": 2666, "tCKmin_ns": 0.750, "tCKmax_ns": 1.600,
        "CL": 20, "supported_cl": list(range(10, 20+1)),
        "tAA_ns": 15.00, "tRCD_ns": 15.00, "tRP_ns": 15.00,
        "tRAS_ns": 32.00, "tRC_ns": 47.00, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 3.00, "tRRD_L_ns": 4.90,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 21.00,
    },
    "DDR4-2933V": {
        "mt_s": 2933, "tCKmin_ns": 0.682, "tCKmax_ns": 1.600,
        "CL": 19, "supported_cl": list(range(10, 21+1)),
        "tAA_ns": 12.96, "tRCD_ns": 12.96, "tRP_ns": 12.96,
        "tRAS_ns": 32.00, "tRC_ns": 44.96, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 3.00, "tRRD_L_ns": 4.90,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 21.00,
    },
    "DDR4-2933W": {
        "mt_s": 2933, "tCKmin_ns": 0.682, "tCKmax_ns": 1.600,
        "CL": 20, "supported_cl": list(range(10, 21+1)),
        "tAA_ns": 13.64, "tRCD_ns": 13.64, "tRP_ns": 13.64,
        "tRAS_ns": 32.00, "tRC_ns": 45.64, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 3.00, "tRRD_L_ns": 4.90,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 21.00,
    },
    "DDR4-2933Y": {
        "mt_s": 2933, "tCKmin_ns": 0.682, "tCKmax_ns": 1.600,
        "CL": 21, "supported_cl": list(range(10, 24+1)),
        "tAA_ns": 14.32, "tRCD_ns": 14.32, "tRP_ns": 14.32,
        "tRAS_ns": 32.00, "tRC_ns": 46.32, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 3.00, "tRRD_L_ns": 4.90,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 21.00,
    },
    "DDR4-2933AA": {
        "mt_s": 2933, "tCKmin_ns": 0.682, "tCKmax_ns": 1.600,
        "CL": 22, "supported_cl": list(range(10, 24+1)),
        "tAA_ns": 15.00, "tRCD_ns": 15.00, "tRP_ns": 15.00,
        "tRAS_ns": 32.00, "tRC_ns": 47.00, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 3.00, "tRRD_L_ns": 4.90,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 21.00,
    },
    "DDR4-3200W": {
        "mt_s": 3200, "tCKmin_ns": 0.625, "tCKmax_ns": 1.600,
        "CL": 20, "supported_cl": list(range(10, 24+1)),
        "tAA_ns": 12.50, "tRCD_ns": 12.50, "tRP_ns": 12.50,
        "tRAS_ns": 32.00, "tRC_ns": 44.50, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 3.00, "tRRD_L_ns": 4.90,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 21.00,
    },
    "DDR4-3200AA": {
        "mt_s": 3200, "tCKmin_ns": 0.625, "tCKmax_ns": 1.600,
        "CL": 22, "supported_cl": list(range(10, 24+1)),
        "tAA_ns": 13.75, "tRCD_ns": 13.75, "tRP_ns": 13.75,
        "tRAS_ns": 32.00, "tRC_ns": 45.75, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 3.00, "tRRD_L_ns": 4.90,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 21.00,
    },
    "DDR4-3200AC": {
        "mt_s": 3200, "tCKmin_ns": 0.625, "tCKmax_ns": 1.600,
        "CL": 24, "supported_cl": list(range(10, 24+1)),
        "tAA_ns": 15.00, "tRCD_ns": 15.00, "tRP_ns": 15.00,
        "tRAS_ns": 32.00, "tRC_ns": 47.00, "tWR_ns": 15.00,
        "tWTR_S_ns": 2.50, "tWTR_L_ns": 7.50,
        "tRRD_S_ns": 3.00, "tRRD_L_ns": 4.90,
        "tRFC1_ns": 350.0, "tRFC2_ns": 260.0, "tRFC4_ns": 160.0,
        "tFAW_ns": 21.00,
    },
}

# DDR4 CAS Latency range (CL7-CL36)
ALL_DDR4_CL_VALUES = list(range(7, 37))


# =============================================================================
# DDR4 XMP 2.0 Profile (47 bytes)
# =============================================================================

class DDR4_XMP:
    """DDR4 XMP 2.0 Profile (47 字节)"""

    SIZE = 0x2F

    def __init__(self, profile_no: int = 0):
        self._data = bytearray(self.SIZE)
        self.profile_no = profile_no

    # 字节偏移量
    _O_VOLTAGE = 0
    _O_UNKNOWN1 = 1           # 2 bytes
    _O_SDRAM_CYCLE = 3
    _O_CL_SUPPORTED = 4       # 3 bytes (CL7-CL14, CL15-CL22, CL23-CL30)
    _O_UNKNOWN2 = 7
    _O_CL_TICKS = 8
    _O_RCD_TICKS = 9
    _O_RP_TICKS = 10
    _O_RASRC_UPPER = 11
    _O_RAS_TICKS = 12
    _O_RC_TICKS = 13
    _O_RFC1_TICKS = 14        # 2 bytes (ushort)
    _O_RFC2_TICKS = 16        # 2 bytes
    _O_RFC4_TICKS = 18        # 2 bytes
    _O_FAW_UPPER = 20
    _O_FAW_TICKS = 21
    _O_RRDS_TICKS = 22
    _O_RRDL_TICKS = 23
    _O_UNKNOWN3 = 24          # 8 bytes
    _O_RRDL_FC = 32
    _O_RRDS_FC = 33
    _O_RC_FC = 34
    _O_RP_FC = 35
    _O_RCD_FC = 36
    _O_CL_FC = 37
    _O_SDRAM_CYCLE_FC = 38
    _O_UNKNOWN4 = 39          # 8 bytes

    # ---- 电压 ----
    @property
    def voltage(self) -> int:
        """电压 (百分之一伏特, 如 135 = 1.35V)。"""
        hundredths = self._data[self._O_VOLTAGE] & 0x7F
        ones = (self._data[self._O_VOLTAGE] & 0x80) >> 7
        return ones * 100 + hundredths

    @voltage.setter
    def voltage(self, value: int):
        if value > 227:
            value = 227
        ones = 1 if value >= 100 else 0
        hundredths = (value - 100) if value >= 100 else value
        self._data[self._O_VOLTAGE] = ((0x80 if ones else 0x00) | (hundredths & 0x7F)) & 0xFF

    # ---- 频率 ----
    @property
    def min_cycle_ticks(self) -> int:
        return self._data[self._O_SDRAM_CYCLE]

    @min_cycle_ticks.setter
    def min_cycle_ticks(self, value: int):
        self._data[self._O_SDRAM_CYCLE] = value & 0xFF

    @property
    def min_cycle_fc(self) -> int:
        """FTB 修正值 (signed)。"""
        return self._data[self._O_SDRAM_CYCLE_FC] if self._data[self._O_SDRAM_CYCLE_FC] < 128 else self._data[self._O_SDRAM_CYCLE_FC] - 256

    @min_cycle_fc.setter
    def min_cycle_fc(self, value: int):
        self._data[self._O_SDRAM_CYCLE_FC] = value & 0xFF

    @property
    def min_cycle_ns(self) -> float:
        return ticks_with_ftb(self.min_cycle_ticks, self._data[self._O_SDRAM_CYCLE_FC])

    # ---- CAS Latency ----
    def is_cl_supported(self, cl: int) -> bool:
        if cl < 7 or cl > 30:
            return False
        bit = cl - 7
        byte_idx = bit // 8
        bit_pos = bit % 8
        return bool(self._data[self._O_CL_SUPPORTED + byte_idx] & (1 << bit_pos))

    def set_cl_supported(self, cl: int, supported: bool):
        if cl < 7 or cl > 30:
            return
        bit = cl - 7
        byte_idx = bit // 8
        bit_pos = bit % 8
        if supported:
            self._data[self._O_CL_SUPPORTED + byte_idx] |= (1 << bit_pos)
        else:
            self._data[self._O_CL_SUPPORTED + byte_idx] &= ~(1 << bit_pos) & 0xFF

    # ---- CL Ticks + FC ----
    @property
    def cl_ticks(self) -> int:
        return self._data[self._O_CL_TICKS]
    @cl_ticks.setter
    def cl_ticks(self, v: int): self._data[self._O_CL_TICKS] = v & 0xFF

    @property
    def cl_fc(self) -> int:
        return self._data[self._O_CL_FC] if self._data[self._O_CL_FC] < 128 else self._data[self._O_CL_FC] - 256
    @cl_fc.setter
    def cl_fc(self, v: int): self._data[self._O_CL_FC] = v & 0xFF

    @property
    def cl_ns(self) -> float:
        return ticks_with_ftb(self.cl_ticks, self._data[self._O_CL_FC])

    # ---- tRCD ----
    @property
    def rcd_ticks(self) -> int: return self._data[self._O_RCD_TICKS]
    @rcd_ticks.setter
    def rcd_ticks(self, v: int): self._data[self._O_RCD_TICKS] = v & 0xFF

    @property
    def rcd_fc(self) -> int: return self._data[self._O_RCD_FC] if self._data[self._O_RCD_FC] < 128 else self._data[self._O_RCD_FC] - 256
    @rcd_fc.setter
    def rcd_fc(self, v: int): self._data[self._O_RCD_FC] = v & 0xFF

    # ---- tRP ----
    @property
    def rp_ticks(self) -> int: return self._data[self._O_RP_TICKS]
    @rp_ticks.setter
    def rp_ticks(self, v: int): self._data[self._O_RP_TICKS] = v & 0xFF

    @property
    def rp_fc(self) -> int: return self._data[self._O_RP_FC] if self._data[self._O_RP_FC] < 128 else self._data[self._O_RP_FC] - 256
    @rp_fc.setter
    def rp_fc(self, v: int): self._data[self._O_RP_FC] = v & 0xFF

    # ---- tRAS (12 bits) ----
    @property
    def ras_ticks(self) -> int:
        upper = self._data[self._O_RASRC_UPPER] & 0xF
        return (upper << 8) | self._data[self._O_RAS_TICKS]
    @ras_ticks.setter
    def ras_ticks(self, value: int):
        self._data[self._O_RASRC_UPPER] = (self._data[self._O_RASRC_UPPER] & 0xF0) | ((value >> 8) & 0xF)
        self._data[self._O_RAS_TICKS] = value & 0xFF

    # ---- tRC (12 bits) ----
    @property
    def rc_ticks(self) -> int:
        upper = (self._data[self._O_RASRC_UPPER] & 0xF0) >> 4
        return (upper << 8) | self._data[self._O_RC_TICKS]
    @rc_ticks.setter
    def rc_ticks(self, value: int):
        self._data[self._O_RASRC_UPPER] = (self._data[self._O_RASRC_UPPER] & 0x0F) | (((value >> 8) & 0xF) << 4)
        self._data[self._O_RC_TICKS] = value & 0xFF

    @property
    def rc_fc(self) -> int: return self._data[self._O_RC_FC] if self._data[self._O_RC_FC] < 128 else self._data[self._O_RC_FC] - 256
    @rc_fc.setter
    def rc_fc(self, v: int): self._data[self._O_RC_FC] = v & 0xFF

    # ---- tRFC1/2/4 ----
    @property
    def rfc1_ticks(self) -> int:
        return bytes_to_ushort(self._data[self._O_RFC1_TICKS], self._data[self._O_RFC1_TICKS + 1])
    @rfc1_ticks.setter
    def rfc1_ticks(self, v: int):
        lo, hi = ushort_to_bytes(v)
        self._data[self._O_RFC1_TICKS] = lo; self._data[self._O_RFC1_TICKS + 1] = hi

    @property
    def rfc2_ticks(self) -> int:
        return bytes_to_ushort(self._data[self._O_RFC2_TICKS], self._data[self._O_RFC2_TICKS + 1])
    @rfc2_ticks.setter
    def rfc2_ticks(self, v: int):
        lo, hi = ushort_to_bytes(v)
        self._data[self._O_RFC2_TICKS] = lo; self._data[self._O_RFC2_TICKS + 1] = hi

    @property
    def rfc4_ticks(self) -> int:
        return bytes_to_ushort(self._data[self._O_RFC4_TICKS], self._data[self._O_RFC4_TICKS + 1])
    @rfc4_ticks.setter
    def rfc4_ticks(self, v: int):
        lo, hi = ushort_to_bytes(v)
        self._data[self._O_RFC4_TICKS] = lo; self._data[self._O_RFC4_TICKS + 1] = hi

    # ---- tFAW (12 bits) ----
    @property
    def faw_ticks(self) -> int:
        upper = self._data[self._O_FAW_UPPER] & 0xF
        return (upper << 8) | self._data[self._O_FAW_TICKS]
    @faw_ticks.setter
    def faw_ticks(self, value: int):
        self._data[self._O_FAW_UPPER] = (self._data[self._O_FAW_UPPER] & 0xF0) | ((value >> 8) & 0xF)
        self._data[self._O_FAW_TICKS] = value & 0xFF

    # ---- tRRDS/tRRDL ----
    @property
    def rrds_ticks(self) -> int: return self._data[self._O_RRDS_TICKS]
    @rrds_ticks.setter
    def rrds_ticks(self, v: int): self._data[self._O_RRDS_TICKS] = v & 0xFF

    @property
    def rrdl_ticks(self) -> int: return self._data[self._O_RRDL_TICKS]
    @rrdl_ticks.setter
    def rrdl_ticks(self, v: int): self._data[self._O_RRDL_TICKS] = v & 0xFF

    @property
    def rrds_fc(self) -> int: return self._data[self._O_RRDS_FC] if self._data[self._O_RRDS_FC] < 128 else self._data[self._O_RRDS_FC] - 256
    @property
    def rrdl_fc(self) -> int: return self._data[self._O_RRDL_FC] if self._data[self._O_RRDL_FC] < 128 else self._data[self._O_RRDL_FC] - 256

    @rrds_fc.setter
    def rrds_fc(self, v: int): self._data[self._O_RRDS_FC] = v & 0xFF
    @rrdl_fc.setter
    def rrdl_fc(self, v: int): self._data[self._O_RRDL_FC] = v & 0xFF

    # ---- 序列化 ----
    def get_bytes(self) -> bytes:
        return bytes(self._data)

    def load_sample(self):
        """加载 DDR4-3200 默认 XMP 值。"""
        self.min_cycle_ticks = 5        # 0.625ns / 0.125 = 5
        self.min_cycle_fc = 0
        self.voltage = 120              # 1.20V (DDR4 默认)

        for cl in [10, 11, 12, 14, 16, 18, 20, 22, 24]:
            self.set_cl_supported(cl, True)

        self.cl_ticks = 20; self.cl_fc = 0       # CL20 @ 2.5ns
        self.rcd_ticks = 20; self.rcd_fc = 0
        self.rp_ticks = 20; self.rp_fc = 0
        self.ras_ticks = 256                     # 32ns
        self.rc_ticks = 360; self.rc_fc = 0      # 45ns
        self.rfc1_ticks = 2800                   # 350ns
        self.rfc2_ticks = 2080                   # 260ns
        self.rfc4_ticks = 1280                   # 160ns
        self.faw_ticks = 168                     # 21ns
        self.rrds_ticks = 24; self.rrds_fc = 0   # 3ns
        self.rrdl_ticks = 39; self.rrdl_fc = 0   # 4.9ns

    # ---- DDR5 XMP 兼容属性 ----
    @property
    def min_cycle_time(self) -> int:
        return round(self.min_cycle_ns * 1000)  # ns → ps
    @min_cycle_time.setter
    def min_cycle_time(self, v: int):
        self.min_cycle_ticks = int(v / 1000 / MTB_NS + 0.5)
        self.min_cycle_fc = 0

    @property
    def tAA(self) -> int: return round(ticks_with_ftb(self.cl_ticks, self.cl_fc) * 1000)
    @tAA.setter
    def tAA(self, v: int): self.cl_ticks = int(v / 1000 / MTB_NS + 0.5)
    @property
    def tAA_ticks(self) -> int: return self.cl_ticks
    @property
    def tRCD(self) -> int: return round(ticks_with_ftb(self.rcd_ticks, self.rcd_fc) * 1000)
    @tRCD.setter
    def tRCD(self, v: int): self.rcd_ticks = int(v / 1000 / MTB_NS + 0.5)
    @property
    def tRCD_ticks(self) -> int: return self.rcd_ticks
    @property
    def tRP(self) -> int: return round(ticks_with_ftb(self.rp_ticks, self.rp_fc) * 1000)
    @tRP.setter
    def tRP(self, v: int): self.rp_ticks = int(v / 1000 / MTB_NS + 0.5)
    @property
    def tRP_ticks(self) -> int: return self.rp_ticks
    @property
    def tRAS(self) -> int: return round(self.ras_ticks * MTB_NS * 1000)
    @tRAS.setter
    def tRAS(self, v: int): self.ras_ticks = int(v / 1000 / MTB_NS + 0.5)
    @property
    def tRAS_ticks(self) -> int: return self.ras_ticks
    @property
    def tRC(self) -> int: return round(ticks_with_ftb(self.rc_ticks, self.rc_fc) * 1000)
    @tRC.setter
    def tRC(self, v: int): self.rc_ticks = int(v / 1000 / MTB_NS + 0.5)
    @property
    def tRC_ticks(self) -> int: return self.rc_ticks
    @property
    def tWR(self) -> int: return 15000  # DDR4 tWR = 15ns
    @tWR.setter
    def tWR(self, v: int): pass
    @property
    def tWR_ticks(self) -> int: return 120  # 15ns / 0.125
    @property
    def tRFC1(self) -> int: return self.rfc1_ticks
    @tRFC1.setter
    def tRFC1(self, v: int): self.rfc1_ticks = v & 0xFFFF
    @property
    def tRFC1_ticks(self) -> int: return self.rfc1_ticks
    @property
    def tRFC2(self) -> int: return self.rfc2_ticks
    @tRFC2.setter
    def tRFC2(self, v: int): self.rfc2_ticks = v & 0xFFFF
    @property
    def tRFC2_ticks(self) -> int: return self.rfc2_ticks
    @property
    def tRFC(self) -> int: return self.rfc4_ticks
    @tRFC.setter
    def tRFC(self, v: int): self.rfc4_ticks = v & 0xFFFF
    @property
    def tRFC_ticks(self) -> int: return self.rfc4_ticks
    # DDR4 XMP 电压默认值 (1.20V / 1.20V / 2.50V)
    vdd = 120
    vddq = 120
    vpp = 250
    vmemctrl = 120
    command_rate = 2  # 2N
    intel_dynamic_memory_boost = False
    realtime_memory_frequency_oc = False
    tRRD_L = tRRD_L_ticks = 0
    tRRD_L_lower_limit = 4
    tCCD_L = tCCD_L_ticks = 0
    tCCD_L_lower_limit = 4
    tCCD_L_WR = tCCD_L_WR_ticks = tCCD_L_WR_lower_limit = 0
    tCCD_L_WR2 = tCCD_L_WR2_ticks = tCCD_L_WR2_lower_limit = 0
    tFAW = tFAW_ticks = tFAW_lower_limit = 0
    tCCD_L_WTR = tCCD_L_WTR_ticks = tCCD_L_WTR_lower_limit = 0
    tCCD_S_WTR = tCCD_S_WTR_ticks = tCCD_S_WTR_lower_limit = 0
    tRTP = tRTP_ticks = tRTP_lower_limit = 0
    def is_user_profile(self): return self.profile_no >= 4
    def check_crc_validity(self): return True
    def update_crc(self): pass
    def calculate_crc(self): return 0
    @property
    def crc(self): return 0
    @crc.setter
    def crc(self, v): pass
    def _set_cl(self, cl: int, supported: bool):
        self.set_cl_supported(cl, supported)
    def _get_cl(self, cl: int) -> bool:
        return self.is_cl_supported(cl)

    def is_empty(self) -> bool:
        return all(b == 0x00 for b in self._data)

    def wipe(self):
        for i in range(self.SIZE):
            self._data[i] = 0

    @classmethod
    def parse(cls, profile_no: int, data: bytes) -> 'DDR4_XMP':
        if len(data) != cls.SIZE:
            return None
        xmp = cls(profile_no)
        xmp._data = bytearray(data)
        return xmp


# =============================================================================
# DDR4 SPD (512 bytes)
# =============================================================================

class DDR4_SPD:
    """DDR4 SPD 数据模型 (512 字节)"""

    TOTAL_SIZE = 512
    PART_NUMBER_SIZE = 20

    # XMP 常量
    XMP_OFFSET = 0x180        # DDR4 XMP 2.0 起始位置 (Header)
    XMP_HEADER_SIZE = 9       # magic(2) + enabled(1) + version(1) + reserved(5)
    XMP_PROFILE_OFFSET = 0x189 # Profile 1 起始 (0x180 + 9)
    XMP_PROFILE_SIZE = 0x2F   # 47 bytes
    TOTAL_XMP_PROFILES = 2

    def __init__(self):
        self._data = bytearray(self.TOTAL_SIZE)
        self.xmp_found = False
        self.xmp_profiles: list[DDR4_XMP] = [
            DDR4_XMP(i + 1) for i in range(self.TOTAL_XMP_PROFILES)
        ]

    # ---- 字节偏移量 ----
    _O_MEMORY_TYPE = 2
    _O_MODULE_TYPE = 3
    _O_DENSITY_BANKS = 4
    _O_ROWCOL_ADDR = 5
    _O_TIMEBASE = 17          # [0:1] FTB, [2:3] MTB
    _O_MIN_CYCLE = 18
    _O_MAX_CYCLE = 19
    _O_CL_SUPPORTED = 20      # 4 bytes, CL7-CL36
    _O_CL_TICKS = 24
    _O_RCD_TICKS = 25
    _O_RP_TICKS = 26
    _O_RASRC_UPPER = 27
    _O_RAS_TICKS = 28
    _O_RC_TICKS = 29
    _O_RFC1_LSB = 30
    _O_RFC1_MSB = 31
    _O_RFC2_LSB = 32
    _O_RFC2_MSB = 33
    _O_RFC4_LSB = 34
    _O_RFC4_MSB = 35
    _O_FAW_UPPER = 36
    _O_FAW_TICKS = 37
    _O_RRDS_TICKS = 38
    _O_RRDL_TICKS = 39
    _O_CCDL_TICKS = 40
    _O_WR_UPPER = 41
    _O_WR_TICKS = 42
    _O_WTR_UPPER = 43
    _O_WTRS_TICKS = 44
    _O_WTRL_TICKS = 45
    # Fine corrections (signed) — JEDEC 21-C Annex L §8.1.44~8.1.52, 从 byte 117 起
    _O_CCDL_FC = 117          # Byte 117: Fine Offset for tCCD_L
    _O_RRDL_FC = 118          # Byte 118: Fine Offset for tRRD_L
    _O_RRDS_FC = 119          # Byte 119: Fine Offset for tRRD_S
    _O_RC_FC = 120            # Byte 120: Fine Offset for tRC
    _O_RP_FC = 121            # Byte 121: Fine Offset for tRP
    _O_RCD_FC = 122           # Byte 122: Fine Offset for tRCD
    _O_CL_FC = 123            # Byte 123: Fine Offset for tAA
    _O_MAX_CYCLE_FC = 124     # Byte 124: Fine Offset for tCKmax
    _O_MIN_CYCLE_FC = 125     # Byte 125: Fine Offset for tCKmin
    _O_CRC_LSB = 126
    _O_CRC_MSB = 127
    # Module specific
    _O_MFG_ID = 320           # 2 bytes
    _O_MFG_LOC = 322
    _O_MFG_YEAR = 323
    _O_MFG_WEEK = 324
    _O_SERIAL = 325           # 4 bytes
    _O_PARTNUMBER = 329       # 20 bytes
    _O_REVISION = 349
    _O_DRAM_MFG_ID = 350      # 2 bytes
    _O_DRAM_STEPPING = 352

    # ---- 时序基值 (MTB) ----
    @property
    def mtb_ns(self) -> float:
        tb = self._data[self._O_TIMEBASE]
        mtb_code = (tb >> 2) & 0x3
        return {0: 0.125, 1: 0.125, 2: 0.25, 3: 0.5}.get(mtb_code, 0.125)

    @property
    def ftb_ns(self) -> float:
        tb = self._data[self._O_TIMEBASE]
        ftb_code = tb & 0x3
        return {0: 0.001, 1: 0.002, 2: 0.005, 3: 0.01}.get(ftb_code, 0.001)

    def _ticks_to_ns(self, ticks: int) -> float:
        return ticks * self.mtb_ns

    def _ticks_to_ps(self, ticks: int) -> int:
        return round(ticks * self.mtb_ns * 1000)

    def _ns_to_ticks(self, ns: float) -> int:
        return int(ns / self.mtb_ns + 0.9999)

    def _ps_to_ticks_fc(self, ps: int):
        """ps 时间拆成 (MTB ticks 向上取整, FTB 微调 fc)，保证 ticks*MTB + fc*FTB 往返一致。"""
        ticks = int(ps / (self.mtb_ns * 1000) + 0.9999)
        return ticks, ps - self._ticks_to_ps(ticks)

    def _signed(self, val: int) -> int:
        return val if val < 128 else val - 256

    # ---- 频率 ----
    @property
    def min_cycle_ticks(self) -> int: return self._data[self._O_MIN_CYCLE]
    @min_cycle_ticks.setter
    def min_cycle_ticks(self, v: int): self._data[self._O_MIN_CYCLE] = v & 0xFF

    @property
    def min_cycle_fc(self) -> int: return self._signed(self._data[self._O_MIN_CYCLE_FC])
    @min_cycle_fc.setter
    def min_cycle_fc(self, v: int): self._data[self._O_MIN_CYCLE_FC] = v & 0xFF

    @property
    def min_cycle_ns(self) -> float:
        return ticks_with_ftb(self.min_cycle_ticks, self._data[self._O_MIN_CYCLE_FC], self.mtb_ns, self.ftb_ns)

    # ---- CAS Latency (CL7-CL36) ----
    def is_cl_supported(self, cl: int) -> bool:
        if cl < 7 or cl > 36:
            return False
        bit = cl - 7
        byte_idx = bit // 8
        bit_pos = bit % 8
        return bool(self._data[self._O_CL_SUPPORTED + byte_idx] & (1 << bit_pos))

    def set_cl_supported(self, cl: int, supported: bool):
        if cl < 7 or cl > 36:
            return
        bit = cl - 7
        byte_idx = bit // 8
        bit_pos = bit % 8
        if supported:
            self._data[self._O_CL_SUPPORTED + byte_idx] |= (1 << bit_pos)
        else:
            self._data[self._O_CL_SUPPORTED + byte_idx] &= ~(1 << bit_pos) & 0xFF

    # ---- 时序 (ticks) ----
    @property
    def cl_ticks(self) -> int: return self._data[self._O_CL_TICKS]
    @cl_ticks.setter
    def cl_ticks(self, v: int): self._data[self._O_CL_TICKS] = v & 0xFF

    @property
    def rcd_ticks(self) -> int: return self._data[self._O_RCD_TICKS]
    @rcd_ticks.setter
    def rcd_ticks(self, v: int): self._data[self._O_RCD_TICKS] = v & 0xFF

    @property
    def rp_ticks(self) -> int: return self._data[self._O_RP_TICKS]
    @rp_ticks.setter
    def rp_ticks(self, v: int): self._data[self._O_RP_TICKS] = v & 0xFF

    @property
    def ras_ticks(self) -> int:
        return ((self._data[self._O_RASRC_UPPER] & 0xF) << 8) | self._data[self._O_RAS_TICKS]
    @ras_ticks.setter
    def ras_ticks(self, v: int):
        self._data[self._O_RASRC_UPPER] = (self._data[self._O_RASRC_UPPER] & 0xF0) | ((v >> 8) & 0xF)
        self._data[self._O_RAS_TICKS] = v & 0xFF

    @property
    def rc_ticks(self) -> int:
        return ((self._data[self._O_RASRC_UPPER] & 0xF0) << 4) | self._data[self._O_RC_TICKS]
    @rc_ticks.setter
    def rc_ticks(self, v: int):
        self._data[self._O_RASRC_UPPER] = (self._data[self._O_RASRC_UPPER] & 0x0F) | (((v >> 8) & 0xF) << 4)
        self._data[self._O_RC_TICKS] = v & 0xFF

    @property
    def rfc1_ticks(self) -> int: return bytes_to_ushort(self._data[self._O_RFC1_LSB], self._data[self._O_RFC1_MSB])
    @rfc1_ticks.setter
    def rfc1_ticks(self, v: int): lo, hi = ushort_to_bytes(v); self._data[self._O_RFC1_LSB]=lo; self._data[self._O_RFC1_MSB]=hi

    @property
    def rfc2_ticks(self) -> int: return bytes_to_ushort(self._data[self._O_RFC2_LSB], self._data[self._O_RFC2_MSB])
    @rfc2_ticks.setter
    def rfc2_ticks(self, v: int): lo, hi = ushort_to_bytes(v); self._data[self._O_RFC2_LSB]=lo; self._data[self._O_RFC2_MSB]=hi

    @property
    def rfc4_ticks(self) -> int: return bytes_to_ushort(self._data[self._O_RFC4_LSB], self._data[self._O_RFC4_MSB])
    @rfc4_ticks.setter
    def rfc4_ticks(self, v: int): lo, hi = ushort_to_bytes(v); self._data[self._O_RFC4_LSB]=lo; self._data[self._O_RFC4_MSB]=hi

    @property
    def faw_ticks(self) -> int: return ((self._data[self._O_FAW_UPPER] & 0xF) << 8) | self._data[self._O_FAW_TICKS]
    @faw_ticks.setter
    def faw_ticks(self, v: int):
        self._data[self._O_FAW_UPPER] = (self._data[self._O_FAW_UPPER] & 0xF0) | ((v >> 8) & 0xF)
        self._data[self._O_FAW_TICKS] = v & 0xFF

    @property
    def wr_ticks(self) -> int: return ((self._data[self._O_WR_UPPER] & 0xF) << 8) | self._data[self._O_WR_TICKS]
    @wr_ticks.setter
    def wr_ticks(self, v: int):
        self._data[self._O_WR_UPPER] = (self._data[self._O_WR_UPPER] & 0xF0) | ((v >> 8) & 0xF)
        self._data[self._O_WR_TICKS] = v & 0xFF

    @property
    def rrds_ticks(self) -> int: return self._data[self._O_RRDS_TICKS]
    @rrds_ticks.setter
    def rrds_ticks(self, v: int): self._data[self._O_RRDS_TICKS] = v & 0xFF

    @property
    def rrdl_ticks(self) -> int: return self._data[self._O_RRDL_TICKS]
    @rrdl_ticks.setter
    def rrdl_ticks(self, v: int): self._data[self._O_RRDL_TICKS] = v & 0xFF

    @property
    def ccdl_ticks(self) -> int: return self._data[self._O_CCDL_TICKS]
    @ccdl_ticks.setter
    def ccdl_ticks(self, v: int): self._data[self._O_CCDL_TICKS] = v & 0xFF

    @property
    def wtr_ticks(self) -> int: return ((self._data[self._O_WTR_UPPER] & 0xF) << 8) | self._data[self._O_WTRL_TICKS]
    @property
    def wtrs_ticks(self) -> int: return self._data[self._O_WTRS_TICKS]
    @wtrs_ticks.setter
    def wtrs_ticks(self, v: int): self._data[self._O_WTRS_TICKS] = v & 0xFF
    @property
    def wtrl_ticks(self) -> int: return self._data[self._O_WTRL_TICKS]
    @wtrl_ticks.setter
    def wtrl_ticks(self, v: int): self._data[self._O_WTRL_TICKS] = v & 0xFF

    # ---- Fine Corrections ----
    @property
    def cl_fc(self) -> int: return self._signed(self._data[self._O_CL_FC])
    @cl_fc.setter
    def cl_fc(self, v: int): self._data[self._O_CL_FC] = v & 0xFF
    @property
    def rcd_fc(self) -> int: return self._signed(self._data[self._O_RCD_FC])
    @rcd_fc.setter
    def rcd_fc(self, v: int): self._data[self._O_RCD_FC] = v & 0xFF
    @property
    def rp_fc(self) -> int: return self._signed(self._data[self._O_RP_FC])
    @rp_fc.setter
    def rp_fc(self, v: int): self._data[self._O_RP_FC] = v & 0xFF
    @property
    def rc_fc(self) -> int: return self._signed(self._data[self._O_RC_FC])
    @rc_fc.setter
    def rc_fc(self, v: int): self._data[self._O_RC_FC] = v & 0xFF
    @property
    def rrds_fc(self) -> int: return self._signed(self._data[self._O_RRDS_FC])
    @rrds_fc.setter
    def rrds_fc(self, v: int): self._data[self._O_RRDS_FC] = v & 0xFF
    @property
    def rrdl_fc(self) -> int: return self._signed(self._data[self._O_RRDL_FC])
    @rrdl_fc.setter
    def rrdl_fc(self, v: int): self._data[self._O_RRDL_FC] = v & 0xFF
    @property
    def ccdl_fc(self) -> int: return self._signed(self._data[self._O_CCDL_FC])
    @ccdl_fc.setter
    def ccdl_fc(self, v: int): self._data[self._O_CCDL_FC] = v & 0xFF

    # ---- 制造信息 ----
    @property
    def mfg_year(self) -> int:
        return int(f"{self._data[self._O_MFG_YEAR]:02X}")
    @mfg_year.setter
    def mfg_year(self, v: int): self._data[self._O_MFG_YEAR] = int(f"{min(v,99):02d}", 16)

    @property
    def mfg_week(self) -> int:
        return int(f"{self._data[self._O_MFG_WEEK]:02X}")
    @mfg_week.setter
    def mfg_week(self, v: int): self._data[self._O_MFG_WEEK] = int(f"{min(v,52):02d}", 16)

    @property
    def part_number(self) -> str:
        raw = self._data[self._O_PARTNUMBER:self._O_PARTNUMBER + self.PART_NUMBER_SIZE]
        return raw.rstrip(b'\x00').decode('ascii', errors='replace')
    @part_number.setter
    def part_number(self, value: str):
        encoded = value[:self.PART_NUMBER_SIZE].encode('ascii', errors='replace')
        for i in range(self.PART_NUMBER_SIZE):
            self._data[self._O_PARTNUMBER + i] = encoded[i] if i < len(encoded) else 0

    # ---- CRC Block1 (CRC-16/XMODEM over bytes 0-125, stored at 126-127) ----
    @property
    def crc(self) -> int:
        return bytes_to_ushort(self._data[self._O_CRC_LSB], self._data[self._O_CRC_MSB])
    @crc.setter
    def crc(self, v: int):
        lo, hi = ushort_to_bytes(v)
        self._data[self._O_CRC_LSB] = lo; self._data[self._O_CRC_MSB] = hi

    # ---- CRC Block2 (CRC-16/XMODEM over bytes 128-253, stored at 254-255) ----
    _O_CRC2_LSB = 254
    _O_CRC2_MSB = 255

    @property
    def crc2(self) -> int:
        return bytes_to_ushort(self._data[self._O_CRC2_LSB], self._data[self._O_CRC2_MSB])
    @crc2.setter
    def crc2(self, v: int):
        lo, hi = ushort_to_bytes(v)
        self._data[self._O_CRC2_LSB] = lo; self._data[self._O_CRC2_MSB] = hi

    def update_crc(self):
        raw = bytes(self._data[:0x7E])  # bytes 0-125
        self.crc = crc16_xmodem(raw)    # JEDEC 21-C §8.1.53: poly 0x1021
        raw2 = bytes(self._data[0x80:0xFE])  # bytes 128-253
        self.crc2 = crc16_xmodem(raw2)

    # ---- XMP ----
    @property
    def xmp1(self) -> DDR4_XMP: return self.xmp_profiles[0]
    @xmp1.setter
    def xmp1(self, v: DDR4_XMP): self.xmp_profiles[0] = v

    @property
    def xmp2(self) -> DDR4_XMP: return self.xmp_profiles[1]
    @xmp2.setter
    def xmp2(self, v: DDR4_XMP): self.xmp_profiles[1] = v

    @property
    def xmp1_enabled(self) -> bool: return self.xmp_found and not self.xmp1.is_empty()
    @xmp1_enabled.setter
    def xmp1_enabled(self, value: bool):
        if value and self.xmp1.is_empty():
            self.xmp1.load_sample()
            self.xmp_found = True

    @property
    def xmp2_enabled(self) -> bool: return self.xmp_found and not self.xmp2.is_empty()
    @xmp2_enabled.setter
    def xmp2_enabled(self, value: bool):
        if value and self.xmp2.is_empty():
            self.xmp2.load_sample()
            self.xmp_found = True

    # ---- 序列化 ----
    def get_bytes(self) -> bytes:
        result = bytearray(self._data)
        # 写入 XMP Header + Profiles
        if self.xmp_found:
            # XMP Header (9 bytes: magic + enabled + version + reserved)
            result[self.XMP_OFFSET] = 0x0C       # magic1
            result[self.XMP_OFFSET + 1] = 0x4A   # magic2
            # profile enabled: bit0=prof1, bit1=prof2
            enabled = 0
            if self.xmp1_enabled:
                enabled |= 0x1
            if self.xmp2_enabled:
                enabled |= 0x2
            result[self.XMP_OFFSET + 2] = enabled
            result[self.XMP_OFFSET + 3] = 0x20   # version 2.0
            # reserved bytes 4-8 (already 0)

            # Profiles
            for i, prof in enumerate(self.xmp_profiles):
                offset = self.XMP_PROFILE_OFFSET + i * self.XMP_PROFILE_SIZE
                pb = prof.get_bytes()
                result[offset:offset + self.XMP_PROFILE_SIZE] = pb
        return bytes(result)

    @classmethod
    def parse(cls, data: bytes) -> 'DDR4_SPD':
        if len(data) < cls.TOTAL_SIZE:
            raise ValueError(f"DDR4 SPD 至少需要 {cls.TOTAL_SIZE} 字节")
        data = data[:cls.TOTAL_SIZE]
        spd = cls()
        spd._data = bytearray(data)

        if spd._data[cls._O_MEMORY_TYPE] != 0x0C:
            raise ValueError(f"不是 DDR4 SPD (Byte 2 = 0x{spd._data[cls._O_MEMORY_TYPE]:02X})")

        spd._parse_xmp(data)
        return spd

    def _parse_xmp(self, data: bytes):
        """解析 DDR4 XMP 2.0 区域 (Header + 2 Profiles)。"""
        if len(data) <= self.XMP_OFFSET + self.XMP_HEADER_SIZE:
            return
        hdr = data[self.XMP_OFFSET:self.XMP_OFFSET + self.XMP_HEADER_SIZE]
        # 检查 magic: 0x0C 0x4A
        if hdr[0] != 0x0C or hdr[1] != 0x4A:
            return
        self.xmp_found = True
        # Profile 1 @ 0x189, Profile 2 @ 0x1B8
        p1_data = data[self.XMP_PROFILE_OFFSET:self.XMP_PROFILE_OFFSET + self.XMP_PROFILE_SIZE]
        p2_data = data[self.XMP_PROFILE_OFFSET + self.XMP_PROFILE_SIZE:
                       self.XMP_PROFILE_OFFSET + self.XMP_PROFILE_SIZE * 2]
        self.xmp1 = DDR4_XMP.parse(1, p1_data) if len(p1_data) == self.XMP_PROFILE_SIZE else DDR4_XMP(1)
        self.xmp2 = DDR4_XMP.parse(2, p2_data) if len(p2_data) == self.XMP_PROFILE_SIZE else DDR4_XMP(2)

    # ---- DDR5 兼容属性 (供 GUI 透明使用) ----
    @property
    def min_cycle_time(self) -> int: return self._ticks_to_ps(self.min_cycle_ticks) + self.min_cycle_fc
    @min_cycle_time.setter
    def min_cycle_time(self, v: int): self.min_cycle_ticks, self.min_cycle_fc = self._ps_to_ticks_fc(v)
    max_cycle_time = 0
    @property
    def tAA(self) -> int: return self._ticks_to_ps(self.cl_ticks) + self.cl_fc
    @tAA.setter
    def tAA(self, v: int): self.cl_ticks, self.cl_fc = self._ps_to_ticks_fc(v)
    @property
    def tAA_ticks(self) -> int: return self.cl_ticks
    @property
    def tRCD(self) -> int: return self._ticks_to_ps(self.rcd_ticks) + self.rcd_fc
    @tRCD.setter
    def tRCD(self, v: int): self.rcd_ticks, self.rcd_fc = self._ps_to_ticks_fc(v)
    @property
    def tRCD_ticks(self) -> int: return self.rcd_ticks
    @property
    def tRP(self) -> int: return self._ticks_to_ps(self.rp_ticks) + self.rp_fc
    @tRP.setter
    def tRP(self, v: int): self.rp_ticks, self.rp_fc = self._ps_to_ticks_fc(v)
    @property
    def tRP_ticks(self) -> int: return self.rp_ticks
    @property
    def tRAS(self) -> int: return self._ticks_to_ps(self.ras_ticks)
    @tRAS.setter
    def tRAS(self, v: int): self.ras_ticks = int(v / 1000 / self.mtb_ns + 0.5)
    @property
    def tRAS_ticks(self) -> int: return self.ras_ticks
    @property
    def tRC(self) -> int: return self._ticks_to_ps(self.rc_ticks) + self.rc_fc
    @tRC.setter
    def tRC(self, v: int): self.rc_ticks, self.rc_fc = self._ps_to_ticks_fc(v)
    @property
    def tRC_ticks(self) -> int: return self.rc_ticks
    @property
    def tWR(self) -> int: return self._ticks_to_ps(self.wr_ticks)
    @tWR.setter
    def tWR(self, v: int): self.wr_ticks = int(v / 1000 / self.mtb_ns + 0.5)
    @property
    def tWR_ticks(self) -> int: return self.wr_ticks
    @property
    def tRFC1_slr(self) -> int: return self.rfc1_ticks
    @tRFC1_slr.setter
    def tRFC1_slr(self, v: int): self.rfc1_ticks = v & 0xFFFF
    @property
    def tRFC1_slr_ticks(self) -> int: return self.rfc1_ticks
    @property
    def tRFC2_slr(self) -> int: return self.rfc2_ticks
    @tRFC2_slr.setter
    def tRFC2_slr(self, v: int): self.rfc2_ticks = v & 0xFFFF
    @property
    def tRFC2_slr_ticks(self) -> int: return self.rfc2_ticks
    @property
    def tRFCsb_slr(self) -> int: return self.rfc4_ticks
    @tRFCsb_slr.setter
    def tRFCsb_slr(self, v: int): self.rfc4_ticks = v & 0xFFFF
    @property
    def tRFCsb_slr_ticks(self) -> int: return self.rfc4_ticks
    @property
    def tRRD_L(self) -> int: return self._ticks_to_ps(self.rrdl_ticks) + self.rrdl_fc
    @tRRD_L.setter
    def tRRD_L(self, v: int): self.rrdl_ticks, self.rrdl_fc = self._ps_to_ticks_fc(v)
    @property
    def tRRD_L_ticks(self) -> int: return self.rrdl_ticks
    tRRD_L_lower_limit = 4
    @property
    def tCCD_L(self) -> int: return self._ticks_to_ps(self.ccdl_ticks) + self.ccdl_fc
    @tCCD_L.setter
    def tCCD_L(self, v: int): self.ccdl_ticks, self.ccdl_fc = self._ps_to_ticks_fc(v)
    @property
    def tCCD_L_ticks(self) -> int: return self.ccdl_ticks
    tCCD_L_lower_limit = 4
    # DDR4 无以下字段, 返回 0
    tCCD_L_WR = tCCD_L_WR_ticks = tCCD_L_WR_lower_limit = 0
    tCCD_L_WR2 = tCCD_L_WR2_ticks = tCCD_L_WR2_lower_limit = 0
    tFAW = tFAW_ticks = tFAW_lower_limit = 0
    tCCD_L_WTR = tCCD_L_WTR_ticks = tCCD_L_WTR_lower_limit = 0
    tCCD_S_WTR = tCCD_S_WTR_ticks = tCCD_S_WTR_lower_limit = 0
    tRTP = tRTP_ticks = tRTP_lower_limit = 0
    tRFC1_dlr = tRFC1_dlr_ticks = tRFC2_dlr = tRFC2_dlr_ticks = 0
    tRFCsb_dlr = tRFCsb_dlr_ticks = 0
    tCCD_M = tCCD_M_ticks = tCCD_M_lower_limit = 0
    tCCD_M_WR = tCCD_M_WR_ticks = tCCD_M_WR_lower_limit = 0
    tCCD_M_WTR = tCCD_M_WTR_ticks = tCCD_M_WTR_lower_limit = 0
    # ---- DDR4 特有解码 (Byte 4, 5, 12) ----
    _DDR4_DENSITY_NAMES = {0:'256Mb',1:'512Mb',2:'1Gb',3:'2Gb',4:'4Gb',5:'8Gb',6:'16Gb',7:'32Gb',8:'12Gb',9:'24Gb'}
    _DDR4_COL_MAP = {0:9, 1:10, 2:11, 3:12}
    _DDR4_ROW_MAP = {0:12, 1:13, 2:14, 3:15, 4:16, 5:17, 6:18}
    _DDR4_WIDTH_MAP = {0:4, 1:8, 2:16, 3:32}

    @property
    def density_str(self) -> str: return self._DDR4_DENSITY_NAMES.get(self._data[4] & 0xF, 'Unknown')
    @property
    def bank_groups(self) -> int: return 2 if (self._data[4] >> 6) == 0 else 4
    @bank_groups.setter
    def bank_groups(self, v: int): pass
    @property
    def banks_per_bank_group(self) -> int: return [4, 8][(self._data[4] >> 4) & 1] if (self._data[4] >> 4) & 1 else 4
    @banks_per_bank_group.setter
    def banks_per_bank_group(self, v: int): pass
    @property
    def column_addresses(self) -> int: return self._DDR4_COL_MAP.get(self._data[5] & 0x7, 10)
    @column_addresses.setter
    def column_addresses(self, v: int): pass
    @property
    def row_addresses(self) -> int: return self._DDR4_ROW_MAP.get((self._data[5] >> 3) & 0x7, 16)
    @row_addresses.setter
    def row_addresses(self, v: int): pass
    @property
    def device_width(self) -> int: return self._DDR4_WIDTH_MAP.get(self._data[12] & 0x7, 8)
    @device_width.setter
    def device_width(self, v: int): pass

    # Density alias for GUI
    @property
    def density(self): return self.density_str
    @density.setter
    def density(self, v): pass

    # Form factor (Byte 3 bits 3:0, same as DDR5)
    _DDR4_FF_MAP = {1:'RDIMM', 2:'UDIMM', 3:'SODIMM', 4:'LRDIMM', 8:'CUDIMM', 9:'CSODIMM'}
    @property
    def form_factor(self) -> str: return self._DDR4_FF_MAP.get(self._data[3] & 0xF, 'Reserved')
    @form_factor.setter
    def form_factor(self, v: str): pass

    heat_spreader = False
    @property
    def manufacturing_year(self) -> int: return self.mfg_year
    @manufacturing_year.setter
    def manufacturing_year(self, v: int): self.mfg_year = v
    @property
    def manufacturing_week(self) -> int: return self.mfg_week
    @manufacturing_week.setter
    def manufacturing_week(self, v: int): self.mfg_week = v
    operating_temperature_range = 0

    # DDR5-only XMP stub (DDR4 只有 2 个 Profile)
    xmp3 = xmp_user1 = xmp_user2 = None
    xmp3_enabled = xmp_user1_enabled = xmp_user2_enabled = False
    expo_found = False
    expo1_enabled = expo2_enabled = False
    xmp_header_crc = 0
    def copy_xmp_profile(self, *a): return False
    def init_expo(self): pass
    # DDR4 XMP 没有 profile 名称，但 GUI 需要这些属性
    _xmp_name1 = _xmp_name2 = _xmp_name3 = ""
    @property
    def xmp_profile1_name(self) -> str: return self._xmp_name1
    @xmp_profile1_name.setter
    def xmp_profile1_name(self, v: str): self._xmp_name1 = v
    @property
    def xmp_profile2_name(self) -> str: return self._xmp_name2
    @xmp_profile2_name.setter
    def xmp_profile2_name(self, v: str): self._xmp_name2 = v
    @property
    def xmp_profile3_name(self) -> str: return self._xmp_name3
    @xmp_profile3_name.setter
    def xmp_profile3_name(self, v: str): self._xmp_name3 = v


# =============================================================================
# Speed Bin Apply
# =============================================================================

def apply_ddr4_speed_bin(spd: DDR4_SPD, bin_name: str) -> bool:
    """应用 DDR4 Speed Bin 到 SPD。"""
    if bin_name not in DDR4_SPEED_BINS:
        return False
    b = DDR4_SPEED_BINS[bin_name]

    spd.min_cycle_ticks = spd._ns_to_ticks(b["tCKmin_ns"])
    spd.min_cycle_fc = 0

    for cl in ALL_DDR4_CL_VALUES:
        spd.set_cl_supported(cl, False)
    for cl in b["supported_cl"]:
        if 7 <= cl <= 36:
            spd.set_cl_supported(cl, True)

    spd.cl_ticks = spd._ns_to_ticks(b["tAA_ns"])
    spd.rcd_ticks = spd._ns_to_ticks(b["tRCD_ns"])
    spd.rp_ticks = spd._ns_to_ticks(b["tRP_ns"])
    spd.ras_ticks = spd._ns_to_ticks(b["tRAS_ns"])
    spd.rc_ticks = spd._ns_to_ticks(b["tRC_ns"])
    spd.rfc1_ticks = spd._ns_to_ticks(b["tRFC1_ns"])
    spd.rfc2_ticks = spd._ns_to_ticks(b["tRFC2_ns"])
    spd.rfc4_ticks = spd._ns_to_ticks(b["tRFC4_ns"])
    spd.faw_ticks = spd._ns_to_ticks(b["tFAW_ns"])
    spd.wr_ticks = spd._ns_to_ticks(b["tWR_ns"])
    spd.rrds_ticks = spd._ns_to_ticks(b["tRRD_S_ns"])
    spd.rrds_fc = round((b["tRRD_S_ns"] - spd.rrds_ticks * MTB_NS) * 1000)
    spd.rrdl_ticks = spd._ns_to_ticks(b["tRRD_L_ns"])
    spd.rrdl_fc = round((b["tRRD_L_ns"] - spd.rrdl_ticks * MTB_NS) * 1000)

    return True


def apply_ddr4_speed_bin_to_xmp(xmp: DDR4_XMP, bin_name: str) -> bool:
    """应用 DDR4 Speed Bin 到 XMP Profile。"""
    if bin_name not in DDR4_SPEED_BINS:
        return False
    b = DDR4_SPEED_BINS[bin_name]

    mtb = MTB_NS
    xmp.min_cycle_ticks = int(b["tCKmin_ns"] / mtb + 0.9999)
    xmp.min_cycle_fc = 0
    xmp.voltage = 120  # DDR4 默认 1.20V

    for cl in ALL_DDR4_CL_VALUES:
        xmp.set_cl_supported(cl, False)
    for cl in b["supported_cl"]:
        if 7 <= cl <= 30:
            xmp.set_cl_supported(cl, True)

    xmp.cl_ticks = int(b["tAA_ns"] / mtb + 0.9999); xmp.cl_fc = 0
    xmp.rcd_ticks = int(b["tRCD_ns"] / mtb + 0.9999); xmp.rcd_fc = 0
    xmp.rp_ticks = int(b["tRP_ns"] / mtb + 0.9999); xmp.rp_fc = 0
    xmp.ras_ticks = int(b["tRAS_ns"] / mtb + 0.9999)
    xmp.rc_ticks = int(b["tRC_ns"] / mtb + 0.9999); xmp.rc_fc = 0
    xmp.rfc1_ticks = int(b["tRFC1_ns"] / mtb + 0.9999)
    xmp.rfc2_ticks = int(b["tRFC2_ns"] / mtb + 0.9999)
    xmp.rfc4_ticks = int(b["tRFC4_ns"] / mtb + 0.9999)
    xmp.faw_ticks = int(b["tFAW_ns"] / mtb + 0.9999)
    xmp.rrds_ticks = int(b["tRRD_S_ns"] / mtb + 0.9999); xmp.rrds_fc = 0
    xmp.rrdl_ticks = int(b["tRRD_L_ns"] / mtb + 0.9999); xmp.rrdl_fc = 0

    return True
