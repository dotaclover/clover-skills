from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
root = Path(__file__).parent / 'xunzhao-chuangye-xiangmu'
out = root / '_ocr_prepared'
for folder in ['images', 'exams']:
    target = out / folder
    target.mkdir(parents=True, exist_ok=True)
    paths = sorted((root / folder).glob('*.jpg'))
    for p in paths:
        if p.name.startswith('contact-'):
            continue
        im = ImageOps.exif_transpose(Image.open(p)).convert('RGB')
        im.thumbnail((2200, 2200))
        # Dark photographed projector text requires local contrast enhancement.
        gray = ImageOps.grayscale(im)
        gray = ImageOps.autocontrast(gray, cutoff=1)
        gray = gray.filter(ImageFilter.UnsharpMask(radius=2, percent=160, threshold=2))
        gray.save(target / p.name, quality=95)
    print(folder, 'prepared')
