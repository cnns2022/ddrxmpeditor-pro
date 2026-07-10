#!/usr/bin/env python3
"""
DDR5 XMP Editor — 工具函数模块
===============================
CRC-16/XMODEM 计算、字节转换、DDR5 时序转换、电压编解码、位操作。

与 C# 原版 Utilities.cs 功能完全一致。
"""

# =============================================================================
# CRC-16/XMODEM
# =============================================================================

def crc16_xmodem(data: bytes) -> int:
    """
    计算 CRC-16/XMODEM (多项式 0x1021)。

    与 C# Utilities.Crc16() 完全一致。
    用于 DDR5 SPD、XMP Header、XMP Profile、EXPO block 的校验和。

    Args:
        data: 输入字节序列

    Returns:
        16 位 CRC 值
    """
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


# =============================================================================
# 字节转换
# =============================================================================

def bytes_to_ushort(lsb: int, msb: int) -> int:
    """将两个字节 (LSB, MSB) 组合为 16 位无符号整数（小端序）。"""
    return ((msb << 8) | lsb) & 0xFFFF


def ushort_to_bytes(value: int) -> tuple:
    """将 16 位无符号整数拆分为 (LSB, MSB) 两个字节。"""
    value &= 0xFFFF
    return (value & 0xFF, (value >> 8) & 0xFF)


# =============================================================================
# DDR5 时序转换 (JESD400-5B)
# =============================================================================

def time_to_ticks_ddr5(time_ps: int, min_cycle_time: int) -> int:
    """
    将时间值(ps)转换为 nCK 时钟周期数。

    使用 JESD400-5B 规定的 0.30% 修正因子进行取整。

    Args:
        time_ps: 以皮秒为单位的时间值
        min_cycle_time: 最小周期时间 (ps)

    Returns:
        nCK 时钟周期数
    """
    if min_cycle_time <= 0:
        return 0

    correction_factor = 3  # 0.30% scaled by 1000

    # Apply correction factor, scaled by 1000
    temp = time_ps * (1000 - correction_factor)
    # Initial nCK calculation, scaled by 1000
    temp_nck = temp / min_cycle_time
    # Add 1, scaled by 1000, to effectively round up
    temp_nck += 1000
    # Round down to next integer
    return int(temp_nck / 1000)


def ticks_to_time_ddr5(ticks: int, min_cycle_time: int) -> int:
    """将 nCK ticks 反向转换为 ps 时间值（近似逆运算）。"""
    if min_cycle_time <= 0 or ticks <= 1:
        return 0
    return int((ticks * 1000 - 1000) * min_cycle_time / 997)


# =============================================================================
# 电压编解码 (DDR5)
# =============================================================================

def voltage_byte_to_mv(val: int) -> int:
    """
    将 DDR5 电压字节解码为毫伏 (mV)。

    编码格式:
      - 高 3 位 (bits 7:5): 整数部分 (ones), 每单位 = 100mV
      - 低 5 位 (bits 4:0): 小数部分 (hundredths), 每单位 = 5mV

    例如: 0x6C → ones=3(300mV), hundredths=12(60mV) → 360mV...
    实际: 0x6C = 0110_1100
      ones = 0b011 = 3 → 300mV
      hundredths = 0b01100 = 12 → 60mV
      总计 = 360mV? 不，C# 代码是 ones*100 + hundredths*5 = 300+60=360mV?

    等等，让我重新看 C# 代码：
      ones = val >> 5           (高3位)
      hundredths = val & 0x1F   (低5位)
      return ones * 100 + hundredths * 5

    对于 VDD=1.1V=1100mV 的情况:
      1100 = ones*100 + hundredths*5
      ones = 11, hundredths = 0 → byte = (11 << 5) | 0 = 0x60 | 0 = 96...

    验证: ConvertVoltageToByteDDR5(1100):
      ones = 1100/100 = 11
      hundredths = 1100%100 = 0
      return (11 << 5) + (0/5) = 0x60

    ConvertByteToVoltageDDR5(0x60):
      ones = 0x60 >> 5 = 3
      hundredths = 0x60 & 0x1F = 0
      return 3*100 + 0*5 = 300...

    Hmm, that gives 300mV, not 1100mV. Let me re-check.

    0x60 = 0110_0000
    ones = 011 = 3
    Wait, 0x60 >> 5: 0x60 = 96, 96 >> 5 = 3.

    But the C# code example from the XMP profile LoadSample:
    VDD = 110 → this is actually 1.10V = 1100mV in the units used by the app.

    Wait, looking at the XAML: Minimum="110" Maximum="240" for voltages.
    And in LoadSample: VDD = 110; VDDQ = 110; VPP = 180; VMEMCTRL = 120;

    So these are in units of 10mV? 110 = 1.10V?

    Let me re-check the encoding.
    110 (decimal) → ConvertVoltageToByteDDR5(110):
      ones = 110/100 = 1
      hundredths = 110%100 = 10
      return (1 << 5) + (10/5) = 32 + 2 = 34 = 0x22

    ConvertByteToVoltageDDR5(0x22):
      ones = 0x22 >> 5 = 1
      hundredths = 0x22 & 0x1F = 2
      return 1*100 + 2*5 = 110 ✓

    OK so the voltage unit is centivolts (10mV steps), not millivolts.
    110 means 1.10V. The encoding works correctly.
    """
    ones = val >> 5
    hundredths = val & 0x1F
    return ones * 100 + hundredths * 5


def voltage_mv_to_byte(mv: int) -> int:
    """
    将电压值编码为 DDR5 电压字节。

    编码格式:
      - 高 3 位: 整数部分 (每单位 100)
      - 低 5 位: 小数部分 (每单位 5)

    Args:
        mv: 电压值（单位：百分之一伏特，即 110 = 1.10V）
    """
    ones = mv // 100
    hundredths = mv % 100
    return ((ones << 5) + (hundredths // 5)) & 0xFF


# =============================================================================
# 位操作
# =============================================================================

def set_bit(bits: int, bit_number: int, value: bool) -> int:
    """设置指定位的值（0 或 1）。"""
    if value:
        return bits | (1 << bit_number)
    else:
        return bits & (0xFF ^ (1 << bit_number))


def get_bit(bits: int, bit_number: int) -> bool:
    """读取指定位的值。"""
    return (bits & (1 << bit_number)) != 0


# =============================================================================
# CAS Latency 辅助函数（DDR5_SPD 和 XMP_3_0 共用）
# =============================================================================

# CL 值对应的 bit 位置映射表
# DDR5 CAS Latency 从 20 到 98，步进 2
_CL_OFFSET = 20

def _cl_to_byte_bit(cl: int) -> tuple:
    """
    将 CAS Latency 值映射到 (字节索引, 位掩码位置)。

    DDR5 CL 范围: 20-98 (偶数)
    5 个字节分别覆盖:
      byte 0: CL 20-34 (8 values)
      byte 1: CL 36-50 (8 values)
      byte 2: CL 52-66 (8 values)
      byte 3: CL 68-82 (8 values)
      byte 4: CL 84-98 (8 values)
    """
    if cl < 20 or cl > 98 or cl % 2 != 0:
        raise ValueError(f"Invalid CAS Latency: {cl}")
    bit = (cl - _CL_OFFSET) // 2
    byte_idx = bit // 8
    bit_pos = bit % 8
    return byte_idx, bit_pos


def is_cl_supported(cl_bytes: bytearray, cl: int) -> bool:
    """检查指定的 CAS Latency 是否被支持。"""
    byte_idx, bit_pos = _cl_to_byte_bit(cl)
    mask = 1 << bit_pos
    return (cl_bytes[byte_idx] & mask) == mask


def set_cl_supported(cl_bytes: bytearray, cl: int, supported: bool):
    """设置指定的 CAS Latency 支持状态。"""
    byte_idx, bit_pos = _cl_to_byte_bit(cl)
    mask = 1 << bit_pos
    if supported:
        cl_bytes[byte_idx] |= mask
    else:
        cl_bytes[byte_idx] &= ~mask & 0xFF
