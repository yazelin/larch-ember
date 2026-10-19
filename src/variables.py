"""全專案變數（design/重寫.md 第四稿、劇本第二稿）。"""

VARS = {
    'heard': ('string', '', '天黑時她心裡聽見誰：a 他／b 歌／c 父親'),
    'dusk': ('number', 0, '落日進度 0–4：每完成一件事加一，窗外越暗、燈越多、內心話掉字'),
    'knob': ('boolean', False, '拿到收音機旋鈕'),
    'radio_on': ('boolean', False, '收音機裝上旋鈕、聽過電台'),
    'letter': ('boolean', False, '讀過信，名字抄在歌譜上'),
    'zhou': ('boolean', False, '走廊聽過周老師'),
    'seat': ('boolean', False, '看過三排十四號的玫瑰'),
    'tao': ('boolean', False, '巷子遇過阿桃姨'),
    'seen': ('string', '', '化妝間看過的東西（逗號分隔）'),
}

RPG_VARS = [
    ('hp', 'rpgHp', 'number', 100),
    ('bag', 'inventory', 'string', '[]'),
    ('equipment', 'rpgEquipment', 'string', '{}'),
    ('state', 'rpgState', 'string', ''),
    ('used', 'inventoryLastUsed', 'string', ''),
    ('count', 'inventoryCount', 'number', 0)
]


def project_variables():
    return ([{'id': k, 'name': k, 'label': lab, 'type': t, 'defaultValue': d} for k, (t, d, lab) in VARS.items()]
            + [{'id': i, 'name': n, 'label': n, 'type': t, 'defaultValue': d} for i, n, t, d in RPG_VARS])
