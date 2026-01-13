# Lumen Font Requirements

## Required Fonts

Lumen uses two custom fonts for optimal display:

### 1. Geist (UI Text)
- **Purpose:** All UI labels, buttons, and interface text
- **Download:** https://vercel.com/font (Geist Sans)
- **Format:** `.ttf` or `.otf`
- **Files needed:** `Geist-Regular.ttf`, `Geist-Bold.ttf`

### 2. Azeret Mono (Data Display)
- **Purpose:** Numbers, metrics, and data values
- **Download:** https://fonts.google.com/specimen/Azeret+Mono
- **Format:** `.ttf` or `.otf`
- **Files needed:** `AzeretMono-Regular.ttf`

## Installation

1. Download the font files from the links above
2. Place font files in: `assets/fonts/`
3. Restart Lumen

## Directory Structure

```
Lumen/
├── assets/
│   └── fonts/
│       ├── Geist-Regular.ttf
│       ├── Geist-Bold.ttf
│       └── AzeretMono-Regular.ttf
```

## Fallback Behavior

If custom fonts are not installed:
- The application will use system default fonts
- A log message will indicate: "Custom fonts directory not found... using system fonts"
- All functionality remains intact; only visual appearance differs

## Supported Formats

- `.ttf` (TrueType Font)
- `.otf` (OpenType Font)
