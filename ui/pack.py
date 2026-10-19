"""把 ui/parts/ 七個部位包成一個「信紙與餘燼」Skills 檔（每段第一行是部位標記），給 Larch 編輯器「匯入 HTML／貼上」用。
gallery 部位 agent 工具寫不進去，靠這個檔一次貼齊。python3 ui/ember.py && python3 ui/pack.py → ui/信紙與餘燼.html"""
import pathlib
HERE = pathlib.Path(__file__).parent
ORDER = ('title', 'dialogue', 'choices', 'menu', 'inventory', 'gallery', 'rpg')
parts = []
for k in ORDER:
    f = next((HERE / 'parts').glob(f'{k}.*'))
    mark = f'<!-- larch-skill-part: {k} -->' if f.suffix == '.html' else f'/* larch-skill-part: {k} */'
    parts.append(mark + '\n' + f.read_text(encoding='utf-8').strip() + '\n')
out = HERE / '信紙與餘燼.html'
out.write_text('\n'.join(parts), encoding='utf-8')
assert all(f'larch-skill-part: {k}' in out.read_text() for k in ORDER)
assert all(len((HERE / 'parts' / f.name).read_text()) < 200000 for f in (HERE / 'parts').iterdir())   # 單一部位上限 20 萬字
print(out, out.stat().st_size)
