"""試 CosyVoice3 的閩南話指令能不能唸台語：阿桃姨兩句，閩南話指令版＋不加指令的對照版。
用 ~/CosyVoice 的 venv 跑：~/CosyVoice/.venv/bin/python cosy_minnan.py"""
import sys, os
sys.path[:0] = [os.path.expanduser('~/CosyVoice'), os.path.expanduser('~/CosyVoice/third_party/Matcha-TTS')]
import onnxruntime
_IS = onnxruntime.InferenceSession
onnxruntime.InferenceSession = lambda *a, **k: _IS(*a, **{**k, 'providers': ['CPUExecutionProvider']})   # 8G 顯存放不下 onnx 的 CUDA EP
from cosyvoice.cli.cosyvoice import AutoModel
import torchaudio
HERE = os.path.dirname(os.path.abspath(__file__))
m = AutoModel(model_dir=os.path.expanduser('~/CosyVoice/pretrained_models/Fun-CosyVoice3-0.5B'), fp16=True)
PROMPT = os.path.expanduser('~/CosyVoice/asset/zero_shot_prompt.wav')
LINES = {'a1': '淑靜仔，你轉來矣喔。', 'a2': '恁阿爸彼當陣，逐工都講你唱歌上好聽。'}
for k, t in LINES.items():
    for tag, fn in (('minnan', lambda: m.inference_instruct2(t, 'You are a helpful assistant. 请用闽南话表达。<|endofprompt|>', PROMPT, stream=False)),
                    ('plain', lambda: m.inference_cross_lingual('You are a helpful assistant.<|endofprompt|>' + t, PROMPT, stream=False))):
        out = next(fn())['tts_speech']
        torchaudio.save(os.path.join(HERE, f'{k}-{tag}.wav'), out, m.sample_rate)
        print('ok', k, tag)
