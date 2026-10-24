from pathlib import Path
import json
import re

root = Path(__file__).parent / 'xunzhao-chuangye-xiangmu'
records = json.loads((root / 'course-ocr.json').read_text(encoding='utf-8-sig'))
roles = re.compile(r'岗位|角色|团队|分工|创始|经理|客服|美工|采购|财务|运营|人员')
sections = {'images': [], 'exams': []}
for record in records:
    folder = record['source'].split('/')[0]
    lines = record.get('lines') or []
    if isinstance(lines, str):
        lines = [lines]
    lines = [re.sub(r'(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])', '', re.sub(r'(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])', '', line)) for line in lines]
    lines = [re.sub(r'(?<!\d)1[3-9]\d{9}(?!\d)', '[手机号已脱敏]', line) for line in lines]
    text = '\n'.join(lines)
    section = f"## {record['source']}\n\n状态：{record['status']}\n\n{text}\n"
    if record.get('error'):
        section += '\n错误：' + record['error'] + '\n'
    sections.setdefault(folder, []).append(section)
    if folder == 'images' and roles.search(text):
        print(record['source'])
        for i, line in enumerate(lines):
            if roles.search(line):
                print(' | '.join(lines[max(0, i-1):i+3]))
for folder, chunks in sections.items():
    if not chunks:
        continue
    filename = '课程照片逐页文字初提.md' if folder == 'images' else '测试题逐页文字初提.md'
    header = '# ' + filename.removesuffix('.md') + '\n\n原图逐文件本机OCR初提，不等于逐字视觉核对。文字可能错漏；空白、倾斜、遮挡页面需复核。原图与提取文本均保留，不将未确认内容作为课程结论。\n\n'
    (root / 'references' / filename).write_text(header + '\n'.join(chunks), encoding='utf-8')
print('TOTAL', len(records), 'ERRORS', sum(r['status'] == 'error' for r in records))
