#!/usr/bin/env python3
"""
Clean frontend code - Remove FLUX/SD3.5 UI elements
Keep ONLY ec2-zimage option
"""

import os
import re
import shutil
from datetime import datetime

TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')

def backup_file(filepath):
    """Create backup before modification"""
    backup_path = f"{filepath}.backup_{TIMESTAMP}"
    shutil.copy2(filepath, backup_path)
    print(f"   📦 Backup: {backup_path}")
    return backup_path

def clean_channels_unified_js():
    """Clean js/channels-unified.js - Remove FLUX options"""
    filepath = "js/channels-unified.js"

    print(f"\n🔧 Cleaning {filepath}...")

    if not os.path.exists(filepath):
        print(f"   ⏭️  File not found, skipping")
        return

    backup_file(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned_lines = []
    skip_until_line = None
    removed_blocks = 0

    for i, line in enumerate(lines):
        # Skip flux variant group logic
        if 'fluxVariantGroup' in line and skip_until_line is None:
            skip_until_line = i + 10  # Skip next ~10 lines
            removed_blocks += 1
            cleaned_lines.append("    // FLUX variant options removed - using ec2-zimage only\n")
            continue

        if skip_until_line and i < skip_until_line:
            continue
        else:
            skip_until_line = None

        # Remove FLUX pricing entries
        if "'replicate-flux" in line or "'vast-ai-flux" in line:
            removed_blocks += 1
            continue

        # Remove FLUX switch cases
        if "case 'replicate-flux" in line or "case 'vast-ai-flux" in line:
            # Skip this case block (find next case or default)
            skip_until_line = i + 1
            while skip_until_line < len(lines):
                if 'case ' in lines[skip_until_line] or 'default:' in lines[skip_until_line]:
                    break
                skip_until_line += 1
            removed_blocks += 1
            continue

        # Remove flux_variant save/load logic
        if 'flux_variant' in line and ('getElementById' in line or 'imageGen.flux_variant' in line):
            removed_blocks += 1
            continue

        cleaned_lines.append(line)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)

    original_lines = len(lines)
    new_lines = len(cleaned_lines)

    print(f"   ✅ Cleaned: {original_lines} → {new_lines} lines (-{original_lines - new_lines} lines)")
    print(f"   🗑️  Removed {removed_blocks} deprecated blocks")

def clean_dashboard_html():
    """Clean dashboard.html - Replace FLUX panel with Z-Image panel"""
    filepath = "dashboard.html"

    print(f"\n🔧 Cleaning {filepath}...")

    if not os.path.exists(filepath):
        print(f"   ⏭️  File not found, skipping")
        return

    backup_file(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace FLUX panel with Z-Image panel
    content = re.sub(
        r'<!-- FLUX EC2 Health Monitoring -->.*?</div>\s*</div>\s*</div>',
        '''<!-- Z-Image EC2 Health Monitoring -->
                        <div class="health-card" id="zimageHealthCard">
                            <div class="health-card-header">
                                <i class="bi bi-gpu-card"></i> Z-Image EC2 Instance Status
                            </div>
                            <div class="health-card-body">
                                <div id="zimageStatus" class="status-badge status-unknown">
                                    <i class="bi bi-question-circle"></i> Checking...
                                </div>

                                <div class="health-details" id="zimageDetails">
                                    <div class="detail-row">
                                        <span class="detail-label">Instance:</span>
                                        <span class="detail-value" id="zimageInstance">-</span>
                                    </div>
                                    <div class="detail-row">
                                        <span class="detail-label">Model:</span>
                                        <span class="detail-value">Z-Image-Turbo</span>
                                    </div>
                                    <div class="detail-row">
                                        <span class="detail-label">Speed:</span>
                                        <span class="detail-value">~5s per image</span>
                                    </div>
                                </div>
                            </div>
                        </div>''',
        content,
        flags=re.DOTALL
    )

    # Update JavaScript references from flux to zimage
    content = content.replace('fluxHealthCard', 'zimageHealthCard')
    content = content.replace('fluxStatus', 'zimageStatus')
    content = content.replace('fluxDetails', 'zimageDetails')
    content = content.replace('fluxInstance', 'zimageInstance')
    content = content.replace('FLUX Model', 'Z-Image Model')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"   ✅ Replaced FLUX panel with Z-Image panel")

def clean_channel_configs_html():
    """Clean channel-configs.html - Remove deprecated provider options"""
    filepath = "channel-configs.html"

    print(f"\n🔧 Cleaning {filepath}...")

    if not os.path.exists(filepath):
        print(f"   ⏭️  File not found, skipping")
        return

    backup_file(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove all provider options except ec2-zimage
    # Find provider select element and replace options
    provider_select_pattern = r'(<select[^>]*id=["\']image_generation_provider["\'][^>]*>)(.*?)(</select>)'

    def replace_provider_options(match):
        opening = match.group(1)
        closing = match.group(3)

        new_options = '''
                        <option value="ec2-zimage">EC2 Z-Image-Turbo (Fast, $0.0014/image)</option>
        '''

        return opening + new_options + closing

    content = re.sub(provider_select_pattern, replace_provider_options, content, flags=re.DOTALL)

    # Remove flux_variant field if exists
    content = re.sub(
        r'<div[^>]*id=["\']fluxVariantGroup["\'][^>]*>.*?</div>',
        '',
        content,
        flags=re.DOTALL
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"   ✅ Kept only ec2-zimage provider option")

def main():
    print("=" * 80)
    print("🎨 FRONTEND CODE CLEANUP - Remove FLUX/SD3.5 UI")
    print("=" * 80)

    clean_channels_unified_js()
    clean_dashboard_html()
    clean_channel_configs_html()

    print("\n" + "=" * 80)
    print("✅ Frontend code cleanup completed!")
    print("=" * 80)
    print("\nℹ️  Backups created with timestamp:", TIMESTAMP)
    print("\n📋 Next steps:")
    print("   1. Review cleaned files in browser")
    print("   2. Test provider selection UI")
    print("   3. Verify no broken JavaScript references")

if __name__ == "__main__":
    main()
