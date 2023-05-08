import torch
import os
from torch import nn
from torchtext import data
import json
import re

MODEL_NAME = "cbtsa_model.pt"


def clean_sentence(sent: str) -> str:
    """
    Args:
        sent (str): an uncleaned sentence with text, punctuations, numbers
    """
    sent = sent.lower()  # converting the text to lower case
    sent = re.sub(
        r"(@|#)([A-Za-z0-9]+)", " ", sent
    )  # removing tags and mentions (there's no right way of doing it with regular expression but this will try)
    sent = re.sub(
        r"([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+", " ", sent
    )  # removing emails
    sent = re.sub(r"https?\S+", " ", sent, flags=re.MULTILINE)  # removing url's
    sent = re.sub(r"\d", " ", sent)  # removing none word characters
    sent = re.sub(
        r"[^\w\s\']", " ", sent
    )  # removing punctuations except for "'" in words like I'm
    sent = re.sub(r"\s+", " ", sent).strip()  # remove more than one space
    words = list()
    for word in sent.split(" "):
        if len(word) == 1 and word not in ["a", "i"]:
            continue
        else:
            words.append(word)
    return " ".join(words)


class Label:
    def __init__(self, label: str, labelId: int, confidence: float):
        self.label = label
        self.labelId = labelId
        self.confidence = confidence

    def __repr__(self) -> str:
        return f"[CBTSA Prediction: {self.label}]"

    def __str__(self) -> str:
        return f"[CBTSA Prediction: {self.label}]"

    def to_json(self):
        return {
            "label": self.label,
            "labelId": self.labelId,
            "confidence": self.confidence,
        }


class Prediction:
    def __init__(self, text: str, label: Label):
        self.text = text
        self.label = label

    def __repr__(self) -> str:
        return f"[CBTSA Preciction: {self.label.label}]"

    def __str__(self) -> str:
        return f"[CBTSA Preciction: {self.label.label}]"

    def to_json(self):
        return {
            "text": self.text,
            "label": self.label.to_json(),
        }


def inference_preprocess_text(text, max_len=100, padding="pre"):
    text = clean_sentence(text)
    assert (
        padding == "pre" or padding == "post"
    ), "the padding can be either pre or post"
    text_holder = torch.zeros(
        max_len, dtype=torch.int32
    )  # fixed size tensor of max_len with  = 0
    processed_text = torch.tensor(text_pipeline(text), dtype=torch.int32)
    pos = min(max_len, len(processed_text))
    if padding == "pre":
        text_holder[:pos] = processed_text[:pos]
    else:
        text_holder[-pos:] = processed_text[-pos:]
    text_list = text_holder.unsqueeze(dim=0)
    return text_list


MODEL_PATH = os.path.join(os.getcwd(), f"model/static/{MODEL_NAME}")
VOCAB_PATH = os.path.join(os.getcwd(), f"model/static/vocab.json")
LABELS_PATH = os.path.join(os.getcwd(), f"model/static/labels_dict.json")
device = torch.device("cpu")
tokenizer = data.utils.get_tokenizer("spacy", "en")

with open(VOCAB_PATH, "r") as reader:
    stoi = json.loads(reader.read())

with open(LABELS_PATH, "r") as reader:
    labels_dict = json.loads(reader.read())


def text_pipeline(x: str):
    values = list()
    tokens = tokenizer(x.lower())  # convert to lower case.
    for token in tokens:
        try:
            v = stoi[token]
        except KeyError as e:
            v = stoi["-unk-"]
        values.append(v)
    return values


class CBTSAModel(nn.Module):
    def __init__(
        self,
        vocab_size,
        embedding_size,
        hidden_size,
        output_size,
        num_layers,
        bidirectional,
        dropout,
        pad_idx,
    ):
        super(CBTSAModel, self).__init__()

        self.embedding = nn.Sequential(
            nn.Embedding(vocab_size, embedding_dim=embedding_size, padding_idx=pad_idx),
            nn.Dropout(dropout),
        )
        self.lstm = nn.Sequential(
            nn.LSTM(
                embedding_size,
                hidden_size=hidden_size,
                bidirectional=bidirectional,
                num_layers=num_layers,
                dropout=dropout,
            )
        )
        self.out = nn.Sequential(
            nn.Linear(hidden_size * 2, out_features=128),
            nn.Dropout(dropout),
            nn.Linear(128, out_features=225),
            nn.Dropout(dropout),
            nn.Linear(225, out_features=64),
            nn.Dropout(dropout),
            nn.Linear(64, out_features=output_size),
            nn.Dropout(dropout),
        )

    def forward(self, text, text_lengths):
        embedded = self.embedding(text)
        # set batch_first=true since input shape has batch_size first and text_lengths to the device.
        packed_embedded = nn.utils.rnn.pack_padded_sequence(
            embedded, text_lengths.to("cpu"), enforce_sorted=False, batch_first=True
        )
        packed_output, (h_0, c_0) = self.lstm(packed_embedded)
        output, output_lengths = nn.utils.rnn.pad_packed_sequence(packed_output)
        output = torch.cat((h_0[-2, :, :], h_0[-1, :, :]), dim=1)
        return self.out(output)


print(" ✅ LOADING MODEL!\n")

INPUT_DIM = len(stoi)
EMBEDDING_DIM = 100
HIDDEN_DIM = 256
OUTPUT_DIM = len(labels_dict)
N_LAYERS = 2
BIDIRECTIONAL = True
DROPOUT = 0.45
PAD_IDX = stoi["-pad-"]
cbtsa_model = CBTSAModel(
    INPUT_DIM,
    EMBEDDING_DIM,
    HIDDEN_DIM,
    OUTPUT_DIM,
    N_LAYERS,
    BIDIRECTIONAL,
    DROPOUT,
    PAD_IDX,
).to(device)

cbtsa_model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
print(" ✅ LOADING MODEL DONE!\n")


def predict_sentiment(model, sentence, device):
    model.eval()
    with torch.no_grad():
        tensor = inference_preprocess_text(sentence.lower()).to(device)
        length = torch.tensor([len(t) for t in tensor])
        out = model(tensor, length)
        out = torch.softmax(out.squeeze(0), dim=0)
        prediction = torch.argmax(out)
        prediction = prediction.detach().cpu().item()
        labels_ = {v: k for k, v in labels_dict.items()}
        label = labels_[prediction]
        _label = Label(label, int(prediction), float(round(out[prediction].item(), 2)))
        return Prediction(sentence.lower(), _label)
