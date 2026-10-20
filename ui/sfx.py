"""介面音效（自己合成，不用內建、也不是水滴）：紙與鉛筆。
press＝鉛筆尖點在紙上的一聲輕響；advance＝翻一頁信紙的沙聲；hover＝幾乎聽不到的紙面摩擦；
open／close＝信紙攤開／折起；use＝一個很輕的鋼琴音。python3 ui/sfx.py → ui/sfx/*.mp3（要 ffmpeg）"""
import numpy as np, subprocess, pathlib, wave
SR = 44100
OUT = pathlib.Path(__file__).resolve().parent / 'sfx'
rng = np.random.default_rng(7)


def env(n, a=.003, tau=.05):
    t = np.arange(n) / SR
    return np.clip(t / a, 0, 1) * np.exp(-t / tau)


def lowpass(x, k):   # 一階低通，k 越大越悶
    y = np.zeros_like(x); acc = 0.
    for i, v in enumerate(x):
        acc += (v - acc) / k; y[i] = acc
    return y


def tick(vol=.35):   # 鉛筆點紙：一小段濾過的噪音＋很短的木頭共振
    n = int(SR * .09); t = np.arange(n) / SR
    noise = lowpass(rng.standard_normal(n), 3) * env(n, .001, .012)
    wood = np.sin(2 * np.pi * 310 * t) * env(n, .001, .02) * .5
    return (noise * .9 + wood) * vol


def rustle(dur, vol, lo=2, hi=9, sweep=True):   # 紙的沙聲：帶通噪音、起音慢、中間有顆粒
    n = int(SR * dur); x = rng.standard_normal(n)
    x = lowpass(x, lo) - lowpass(x, hi * 6)
    grain = np.clip(rng.standard_normal(n // 40 + 1).repeat(40)[:n] * .6 + .7, 0, 1)
    t = np.arange(n) / SR
    shape = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** (1.4 if sweep else 1)
    return x * grain * shape * vol


def piano(f, dur=.6, vol=.3):
    t = np.arange(int(SR * dur)) / SR
    s = sum(a * np.sin(2 * np.pi * f * k * t) * np.exp(-t * d) for k, a, d in ((1, 1, 5), (2, .35, 8), (3, .15, 11)))
    return s * np.clip(t / .004, 0, 1) * vol


def softnote(f=293.66, dur=.45):
    """翻頁：不用噪音（沙沙聲像預設音效，作者 2026-10-20 說要柔和）。毛氈包著的一個低音：起音慢、泛音少、很快淡掉。"""
    t = np.arange(int(SR * dur)) / SR
    s = sum(a * np.sin(2 * np.pi * f * k * t) * np.exp(-t * d) for k, a, d in ((1, 1, 7), (2, .15, 12)))
    return lowpass(s * np.clip(t / .014, 0, 1), 3)


def seq(*parts):
    n = max(int(SR * d) + len(w) for d, w in parts); out = np.zeros(n)
    for d, w in parts:
        out[int(SR * d):int(SR * d) + len(w)] += w
    return out


SOUNDS = {
    'hover': rustle(.07, .5, 2, 5, False) * .12,
    'press': tick(),
    'advance': (rustle(.26, 1.6), softnote())[1],   # 舊的沙聲照樣呼叫一次，只為了讓後面 open／close 的亂數序列不變
    'open': rustle(.3, 1.2),
    'close': rustle(.22, 1.0),
    'use': piano(523.25),
}

if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    for name, s in SOUNDS.items():
        s = np.concatenate([s, np.zeros(int(SR * .03))])
        s = s / max(1e-9, np.abs(s).max()) * {'hover': .1, 'press': .5, 'advance': .22, 'open': .4, 'close': .35, 'use': .45}[name]
        wav = OUT / f'{name}.wav'
        with wave.open(str(wav), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((s * 32767).astype('<i2').tobytes())
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(wav), '-b:a', '96k', str(OUT / f'{name}.mp3')], check=True)
        wav.unlink()
        print(name, round(len(s) / SR, 2), 's')
