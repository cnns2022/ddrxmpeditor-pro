# DDR XMP Editor Pro V1.0

A Python 3 + tkinter desktop application for editing DDR4 and DDR5 SPD (Serial Presence Detect) binary files with XMP/EXPO profile support.

Author: Zhou Qiang (周强) — cnns@sina.com

---

## Features

### Dual DDR4/DDR5 Support

- **Auto-detection**: Identifies DDR4 (Byte 2 = `0x0C`) vs DDR5 (Byte 2 = `0x12`) on file open
- **DDR4**: 512-byte SPD, XMP 2.0 (2 profiles, 47 bytes each), 24 speed bins (DDR4-1600 to DDR4-3200)
- **DDR5**: 1024-byte SPD, XMP 3.0 (5 profiles, 64 bytes each), EXPO (2 profiles), 64 speed bins (DDR5-3200 to DDR5-9200)

### Speed Bin Database

| DDR Type | Range | Count |
|----------|-------|-------|
| DDR4 | DDR4-1600J ~ DDR4-3200AC | 24 bins |
| DDR5 | DDR5-3200AN ~ DDR5-9200C | 64 bins |

Selecting a speed bin and clicking **Apply** auto-fills all timing parameters, CAS latency, and voltages.

### XMP Profile Management

- **DDR5**: XMP 1-3 (vendor) + XMP User 1-2 (user) profiles
- **DDR4**: XMP 1-2 profiles
- Copy, import, and export individual XMP profiles as 64-byte (DDR5) or 47-byte (DDR4) binary files
- Gray-out (disable) for inactive profiles

### EXPO Support (DDR5 Only)

- EXPO 1 and EXPO 2 profiles with independent enable/disable
- Auto-creates EXPO block with defaults on checkbox selection
- Auto-disables conflicting XMP Profile 3 and User Profile 1
- EXPO block written at SPD offset 0x340-0x3BF

### CRC Checksums

| DDR Type | CRC Algorithm | Coverage | Storage Offset |
|----------|--------------|----------|----------------|
| DDR4 | CRC-16/ARC (0x8005) | Bytes 0-125 | Bytes 126-127 |
| DDR5 | CRC-16/XMODEM (0x1021) | Bytes 0-509 | Bytes 510-511 |

### Misc Settings

- Form Factor, Density, Bank Groups, Addressing
- Manufacturing info: Year, Week, Part Number, Heat Spreader
- Real-time auto-computation of frequency (MHz/MT/s) and timing ticks

---

## SPD Space Allocation

### DDR5 (1024 bytes)

```
0x000 - 0x27F   JEDEC standard area (640 bytes)
0x280 - 0x2BF   XMP 3.0 Header (64 bytes)
0x2C0 - 0x2FF   XMP Profile 1 (64 bytes)
0x300 - 0x33F   XMP Profile 2 (64 bytes)
0x340 - 0x37F   XMP Profile 3 / EXPO Header + Profile 1
0x380 - 0x3BF   XMP User 1 / EXPO Profile 2 + Checksum
0x3C0 - 0x3FF   XMP User 2 (64 bytes)
```

### DDR4 (512 bytes)

```
0x000 - 0x17F   JEDEC standard area (384 bytes)
0x180 - 0x188   XMP 2.0 Header (9 bytes)
0x189 - 0x1B7   XMP Profile 1 (47 bytes)
0x1B8 - 0x1E6   XMP Profile 2 (47 bytes)
```

---

## Running

```bash
cd d:\aiwork\ddr_xmp_editor_pro
py ddr_xmp_editor.py
```

### Build Standalone Executable

```bash
py -m PyInstaller --noconfirm ddr_xmp_editor.spec
```

Output: `dist\DDR_XMP_Editor_Pro.exe`

### Shortcuts

| Key | Action |
|-----|--------|
| Ctrl+O | Open SPD file |
| Ctrl+S | Save SPD file |

---

## Usage

1. Dump the SPD from your memory module using [SPD-Reader-Writer](https://github.com/1a2m3/SPD-Reader-Writer).
2. Open the SPD dump (.bin or .spd file). The editor auto-detects DDR4 or DDR5.
3. Edit JEDEC timings, XMP profiles, or EXPO profiles as needed.
4. Use Speed Bin dropdown with Apply to quickly configure standard JEDEC parameters.
5. Save your modified SPD. CRC checksums are automatically recalculated.
6. Write the modified SPD back using SPD-Reader-Writer (AT YOUR OWN RISK).

---

## Project Structure

```
ddr_xmp_editor_pro/
├── ddr_xmp_editor.py    # Main GUI application (tkinter)
├── ddr5_spd_model.py    # DDR5 SPD, XMP 3.0, EXPO data models
├── ddr4_spd_model.py    # DDR4 SPD, XMP 2.0 data models
├── ddr5_utils.py        # CRC-16, voltage encoding, timing conversion
└── ddr_xmp_editor.spec  # PyInstaller build configuration
```

---

## Acknowledgments

- This is a Python port of the C# [DDR4XMPEditor](https://github.com/integralfx/DDR4XMPEditor) and [DDR5XMPEditor](https://github.com/integralfx/DDR5XMPEditor) projects
- DDR4/DDR5 speed bin data sourced from JEDEC standards (JESD79-4D / JESD79-5D)
- Built with Python 3.13 and tkinter (stdlib only, no external dependencies)

## Known Limitations

- DDR4 XMP voltage: DDR4 XMP 2.0 stores a single voltage value. VDDQ and VPP are not independently programmable.
- DDR4 EXPO: Not applicable — EXPO is DDR5-only.
- DDR4 timing fields: Some DDR5-specific timing fields (tCCD_M, tCCD_M_WR, etc.) are not present in DDR4 and show as zero.
- Tick rounding: Timing conversions between nanoseconds and MTB ticks use standard rounding that may differ slightly from vendor tools.
