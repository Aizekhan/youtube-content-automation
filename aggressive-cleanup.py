import re

# Clean js/channels-unified.js - remove ALL switch cases except ec2-zimage
print("Cleaning js/channels-unified.js aggressively...")

with open('js/channels-unified.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove entire switch statement and replace with simple ec2-zimage only logic
# Find the switch(provider) block
switch_pattern = r'switch\s*\(\s*provider\s*\)\s*{.*?(?=\n\s{4}(?:function|var|const|let|//|$))'

def replace_switch(match):
    return '''// Provider info - ec2-zimage only
    const infoBox = document.getElementById('providerSetupInfo');
    let setupInfo = '';
    let infoText = document.querySelector('#imageGenerationSettings .settings-info-text');

    if (provider === 'ec2-zimage') {
        infoText.textContent = 'Z-Image-Turbo - Fast and efficient';
        setupInfo = `
            <div style="padding: 16px; background: #dcfce7; border: 1px solid #16a34a; border-radius: 8px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <i class="bi bi-lightning-charge" style="color: #16a34a; font-size: 20px;"></i>
                    <strong style="color: #166534;">EC2 Z-Image-Turbo</strong>
                </div>
                <p style="color: #166534; font-size: 13px; margin-bottom: 8px;">
                    Fast image generation (~5s per image) | g5.xlarge GPU
                </p>
                <p style="color: #15803d; font-size: 12px; margin: 0;">
                    Managed automatically by Step Functions
                </p>
            </div>
        `;
    } else {
        infoText.textContent = 'Unknown provider - using ec2-zimage';
        setupInfo = '<p style="color: #dc2626;">Unknown provider. Please select ec2-zimage.</p>';
    }'''

content = re.sub(switch_pattern, replace_switch, content, flags=re.DOTALL)

# Remove pricing for deprecated providers
content = re.sub(
    r"'(?:aws-bedrock-sdxl|replicate-flux-schnell|replicate-flux-dev|vast-ai-flux-schnell)':\s*[^,]+,?\s*\n",
    "",
    content
)

# Remove any remaining Vast.ai control panel references
content = re.sub(
    r"document\.getElementById\('vastaiControlPanel'\)\.style\.display = '[^']+';?\s*\n",
    "",
    content
)

# Write cleaned content
with open('js/channels-unified.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ js/channels-unified.js aggressively cleaned")

# Clean channel-configs.html
print("\nCleaning channel-configs.html...")

with open('channel-configs.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all provider options with ONLY ec2-zimage
content = re.sub(
    r'<option value="replicate_sdxl">[^<]+</option>',
    '',
    content
)

with open('channel-configs.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ channel-configs.html cleaned")

# Clean dashboard.html - remove ALL SD35 references
print("\nCleaning dashboard.html...")

with open('dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove all SD35 element IDs
content = re.sub(r'id="sd35-[^"]+"', 'id="zimage-removed"', content)

# Remove SD35_HEALTH_API_URL
content = re.sub(r"const SD35_HEALTH_API_URL = '[^']+';", "// SD35 removed", content)

# Remove checkSD35Health function
content = re.sub(
    r'async function checkSD35Health\(\)\s*{.*?}',
    '// checkSD35Health removed - using Z-Image only',
    content,
    flags=re.DOTALL
)

with open('dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ dashboard.html cleaned")
print("\n✅ Aggressive cleanup completed!")
