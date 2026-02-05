#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PWA Icon Generator for PhysiologicPRISM
Generates all required icon sizes from logo.png
"""

import os
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from PIL import Image, ImageDraw, ImageFont
    print("[OK] Pillow library found")
except ImportError:
    print("[ERROR] Pillow library not found!")
    print("Please install it: pip install Pillow")
    sys.exit(1)


# Configuration
SOURCE_LOGO = "static/logo.png"
OUTPUT_DIR = "static/icons"

# All required icon sizes
ICON_SIZES = [
    # Standard PWA icons
    (72, 72, "Small Android"),
    (96, 96, "Standard Android"),
    (128, 128, "Chrome Web Store"),
    (144, 144, "Windows Tile / Standard Android"),
    (152, 152, "iPad Home Screen"),
    (180, 180, "iPhone Retina"),
    (192, 192, "Android Splash (REQUIRED)"),
    (384, 384, "Android High-Res"),
    (512, 512, "Android Splash (REQUIRED)"),

    # Windows tiles
    (70, 70, "Windows Small Tile"),
    (150, 150, "Windows Medium Tile"),
    (310, 310, "Windows Large Tile"),
]

# Wide tile needs special handling (not square)
WIDE_TILE = (310, 150, "Windows Wide Tile")


def create_icons_directory():
    """Create the icons directory if it doesn't exist"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"[OK] Created/verified directory: {OUTPUT_DIR}")


def check_source_logo():
    """Check if source logo exists"""
    if not os.path.exists(SOURCE_LOGO):
        print(f"ERROR: Source logo not found at {SOURCE_LOGO}")
        print("Please ensure logo.png exists in the static folder")
        return False

    # Check if it's a valid image
    try:
        img = Image.open(SOURCE_LOGO)
        width, height = img.size
        print(f"[OK] Source logo found: {width}x{height} pixels")

        # Recommend minimum size
        if width < 512 or height < 512:
            print(f"[WARNING] Logo is smaller than recommended (512x512)")
            print(f"  Current size: {width}x{height}")
            print(f"  Icons may look blurry when upscaled")

        return True
    except Exception as e:
        print(f"[ERROR] Cannot open logo file: {e}")
        return False


def generate_icon(source_img, width, height, description, output_path):
    """Generate a single icon size"""
    try:
        # Create a copy to avoid modifying original
        img = source_img.copy()

        # Resize using high-quality Lanczos resampling
        img = img.resize((width, height), Image.Resampling.LANCZOS)

        # Save as PNG
        img.save(output_path, "PNG", optimize=True)

        print(f"  [OK] {width}x{height} - {description}")
        return True
    except Exception as e:
        print(f"  [FAIL] {width}x{height} - FAILED: {e}")
        return False


def generate_wide_tile(source_img, width, height, description, output_path):
    """Generate wide tile (special case - not square)"""
    try:
        # For wide tiles, we need to fit the logo and add padding
        img = source_img.copy()

        # Calculate scaling to fit within wide tile
        img.thumbnail((width, height), Image.Resampling.LANCZOS)

        # Create a new image with wide dimensions and transparent background
        wide_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))

        # Paste the logo in the center
        x = (width - img.width) // 2
        y = (height - img.height) // 2
        wide_img.paste(img, (x, y), img if img.mode == 'RGBA' else None)

        # Save as PNG
        wide_img.save(output_path, "PNG", optimize=True)

        print(f"  [OK] {width}x{height} - {description}")
        return True
    except Exception as e:
        print(f"  [FAIL] {width}x{height} - FAILED: {e}")
        return False


def generate_shortcut_icons(source_img):
    """Generate icons for app shortcuts"""
    print("\n[SHORTCUTS] Generating App Shortcut Icons...")

    shortcuts = [
        ("add-patient-icon.png", "Add Patient Shortcut", "+"),
        ("patients-icon.png", "Patients List Shortcut", "list"),
        ("dashboard-icon.png", "Dashboard Shortcut", "chart"),
    ]

    success_count = 0

    for filename, description, emoji in shortcuts:
        try:
            # Create a simplified version of logo for shortcuts (96x96)
            shortcut_img = source_img.copy()
            shortcut_img = shortcut_img.resize((96, 96), Image.Resampling.LANCZOS)

            output_path = os.path.join(OUTPUT_DIR, filename)
            shortcut_img.save(output_path, "PNG", optimize=True)

            print(f"  [OK] {filename} - {description}")
            success_count += 1
        except Exception as e:
            print(f"  [WARNING] {filename} - Using logo as fallback")
            # Use the main logo as fallback
            try:
                shortcut_img = source_img.copy()
                shortcut_img = shortcut_img.resize((96, 96), Image.Resampling.LANCZOS)
                output_path = os.path.join(OUTPUT_DIR, filename)
                shortcut_img.save(output_path, "PNG", optimize=True)
                success_count += 1
            except:
                pass

    return success_count


def main():
    """Main function to generate all icons"""
    print("=" * 60)
    print("PWA ICON GENERATOR - PhysiologicPRISM")
    print("=" * 60)
    print()

    # Step 1: Create icons directory
    print("[SETUP] Step 1: Setting up directories...")
    create_icons_directory()
    print()

    # Step 2: Check source logo
    print("[CHECK] Step 2: Checking source logo...")
    if not check_source_logo():
        return False
    print()

    # Step 3: Load source image
    print("[LOAD] Step 3: Loading source image...")
    try:
        source_img = Image.open(SOURCE_LOGO)

        # Convert to RGBA if not already (for transparency support)
        if source_img.mode != 'RGBA':
            source_img = source_img.convert('RGBA')

        print(f"[OK] Loaded: {source_img.size[0]}x{source_img.size[1]} pixels")
        print(f"[OK] Mode: {source_img.mode}")
    except Exception as e:
        print(f"[FAIL] Failed to load image: {e}")
        return False
    print()

    # Step 4: Generate standard icons
    print("[GENERATE] Step 4: Generating standard icons...")
    success_count = 0
    failed_count = 0

    for width, height, description in ICON_SIZES:
        output_path = os.path.join(OUTPUT_DIR, f"icon-{width}x{height}.png")
        if generate_icon(source_img, width, height, description, output_path):
            success_count += 1
        else:
            failed_count += 1
    print()

    # Step 5: Generate wide tile
    print("[GENERATE] Step 5: Generating Windows wide tile...")
    width, height, description = WIDE_TILE
    output_path = os.path.join(OUTPUT_DIR, f"icon-{width}x{height}.png")
    if generate_wide_tile(source_img, width, height, description, output_path):
        success_count += 1
    else:
        failed_count += 1
    print()

    # Step 6: Generate shortcut icons
    shortcut_count = generate_shortcut_icons(source_img)
    print()

    # Summary
    total_icons = success_count + len(ICON_SIZES) + 1  # +1 for wide tile
    print("=" * 60)
    print("[COMPLETE] GENERATION COMPLETE")
    print("=" * 60)
    print(f"[OK] Standard icons: {success_count}")
    print(f"[OK] Shortcut icons: {shortcut_count}")
    print(f"[FAIL] Failed: {failed_count}")
    print(f"[DIR] Output directory: {OUTPUT_DIR}")
    print()

    # Verification
    print("[VERIFY] VERIFICATION:")
    required_icons = [
        ("icon-192x192.png", "REQUIRED for Android"),
        ("icon-512x512.png", "REQUIRED for Android"),
    ]

    all_required_exist = True
    for icon_name, description in required_icons:
        icon_path = os.path.join(OUTPUT_DIR, icon_name)
        if os.path.exists(icon_path):
            file_size = os.path.getsize(icon_path) / 1024  # Convert to KB
            print(f"  [OK] {icon_name} - {description} ({file_size:.1f} KB)")
        else:
            print(f"  [FAIL] {icon_name} - MISSING!")
            all_required_exist = False
    print()

    # Final status
    if all_required_exist and failed_count == 0:
        print("[SUCCESS] All PWA icons generated successfully!")
        print()
        print("[NEXT] NEXT STEPS:")
        print("  1. Test icons in browser: http://localhost:5000/static/icons/icon-192x192.png")
        print("  2. Run your app and test PWA installation")
        print("  3. Check Lighthouse audit (should be 95-100% now)")
        print("  4. Deploy to production!")
    elif all_required_exist:
        print("[PARTIAL] Required icons generated, but some failed")
        print("   Your PWA will work, but may be missing some optional sizes")
    else:
        print("[FAILED] Required icons are missing!")
        print("   Your PWA will not install on Android without 192x192 and 512x512")

    print()
    return all_required_exist


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[CANCEL] Generation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
