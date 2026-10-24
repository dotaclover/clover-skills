from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

roots = [
    Path(r'C:/Users/clove/.workbuddy/plugins/marketplaces/my-experts/plugins/chuangye-xiangmu-team/avatars'),
    Path(r'C:/code/cloverhub/clover-skills/chuangye-xiangmu-team/avatars'),
]
items = [
    ('team.png', '创', '#263238', '#E3F2FD'),
    ('chuangye-xiangmu-team-team-lead.png', '经', '#1565C0', '#E3F2FD'),
    ('founder.png', '创', '#6D4C41', '#FFF3E0'),
    ('opportunity-researcher.png', '研', '#6A1B9A', '#F3E5F5'),
    ('operations-designer.png', '运', '#EF6C00', '#FFF3E0'),
    ('customer-service.png', '客', '#00897B', '#E0F2F1'),
    ('procurement-fulfillment.png', '采', '#2E7D32', '#E8F5E9'),
    ('finance-risk-controller.png', '财', '#37474F', '#ECEFF1'),
]
for root in roots:
    root.mkdir(parents=True, exist_ok=True)
    for name, char, fg, bg in items:
        im = Image.new('RGB', (512, 512), bg)
        d = ImageDraw.Draw(im)
        d.ellipse((64, 64, 448, 448), fill=fg)
        try:
            font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 210)
        except OSError:
            font = ImageFont.load_default()
        box = d.textbbox((0, 0), char, font=font)
        d.text(((512 - (box[2]-box[0]))/2, (512 - (box[3]-box[1]))/2 - 20), char, fill='white', font=font)
        im.save(root / name, 'PNG', optimize=True)
