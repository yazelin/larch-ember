"""台語換聲自驗（在 .11 的 ~/seed-vc 跑，用它的 .venv 與 CAMPPlus 說話人模型）：
每支檔量音高中位數（要在參考 ±4 個半音內），並算說話人向量跟四個參考聲音的相似度，最像的那個要等於它該換成的聲音。
python voice_check.py <參考目錄 ref-*.wav> <檔案…>   檔名前綴「<參考名>__」標出預期，例：child__b04f.mp3
"""
import sys, glob, os, torch, torchaudio, librosa, numpy as np
sys.path.insert(0, os.path.expanduser('~/seed-vc'))
from modules.campplus.DTDNN import CAMPPlus

m = CAMPPlus(feat_dim=80, embedding_size=192)
m.load_state_dict(torch.load(os.path.expanduser('~/seed-vc/campplus_cn_common.bin'), map_location='cpu')); m.eval()


def emb(p):
    y, _ = librosa.load(p, sr=16000)
    f = torchaudio.compliance.kaldi.fbank(torch.tensor(y).unsqueeze(0), num_mel_bins=80, dither=0, sample_frequency=16000)
    with torch.no_grad():
        e = m((f - f.mean(0, keepdim=True)).unsqueeze(0))[0]
    return e / e.norm(), y


def pitch(y):
    f, _, _ = librosa.pyin(y, fmin=60, fmax=600, sr=16000)
    return int(np.nanmedian(f)) if np.any(~np.isnan(f)) else 0


refs = {os.path.basename(p)[4:-4]: emb(p) for p in sorted(glob.glob(os.path.join(sys.argv[1], 'ref-*.wav')))}
print('參考', {k: pitch(y) for k, (e, y) in refs.items()})
bad = 0
for p in sys.argv[2:]:
    want = os.path.basename(p).split('__')[0]
    e, y = emb(p)
    sims = {k: round(float(e @ r), 2) for k, (r, _) in refs.items()}
    near = max(sims, key=sims.get)
    pr = pitch(refs[want][1]) if want in refs else 0
    ok = near == want and pr and abs(np.log2(max(pitch(y), 1) / pr)) < 1 / 3   # 音高離參考 4 個半音內（換聲壞掉時一律掉到 140 Hz 上下）
    bad += not ok
    print('OK ' if ok else 'BAD', os.path.basename(p), pitch(y), 'Hz', sims)
print('不合', bad)
