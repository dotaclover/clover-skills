from pathlib import Path
from PIL import Image, ImageOps, ImageDraw

root = Path(r'C:/code/cloverhub/clover-skills/xunzhao-chuangye-xiangmu')
for folder, out_name, cols in [('images', 'images-contact.jpg', 6), ('exams', 'exams-contact.jpg', 5)]:
    paths = sorted((root / folder).glob('*.jpg'))
    thumbs = []
    for p in paths:
        try:
            im = Image.open(p).convert('RGB')
            im.thumbnail((240, 180))
            canvas = Image.new('RGB', (260, 220), 'white')
            x = (260 - im.width) // 2
            y = 5 + (180 - im.height) // 2
            canvas.paste(im, (x, y))
            d = ImageDraw.Draw(canvas)
            d.text((5, 190), p.name[:32], fill='black')
            thumbs.append(canvas)
        except Exception as e:
            print('skip', p, e)
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * 260, rows * 220), '#dddddd')
    for i, im in enumerate(thumbs):
        sheet.paste(im, ((i % cols) * 260, (i // cols) * 220))
    sheet.save(root / out_name, quality=88)
    print(out_name, len(paths), sheet.size)
