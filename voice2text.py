import string
from IPython.display import Audio
from scipy.io import wavfile
import numpy as np
import soundfile as sf
import librosa
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Tokenizer

class Texter():
    def __init__(self):
        self.tokenizer = Wav2Vec2Tokenizer.from_pretrained("facebook/wav2vec2-base-960h")
        self.model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-base-960h")
    
    def totext(self, filename: string) -> string:
        input_audio, _ = librosa.load(file_name, 
                              sr=16000)
        input_values = self.tokenizer(input_audio, return_tensors="pt").input_values
        logits = self.model(input_values).logits
        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = self.tokenizer.batch_decode(predicted_ids)[0]
        return transcription

if __name__ == '__main__':
    file_name = '07-10-2022-21-43-20/recording.wav'
    
    tokenizer = Wav2Vec2Tokenizer.from_pretrained("facebook/wav2vec2-base-960h")
    model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-base-960h")
    input_audio, _ = librosa.load(file_name, sr=16000)

    input_values = tokenizer(input_audio, return_tensors="pt").input_values
    logits = model(input_values).logits
    predicted_ids = torch.argmax(logits, dim=-1)
    transcription = tokenizer.batch_decode(predicted_ids)[0]
    print('transcription:', transcription)