#v18 being used as foundation for adding new classifier fast_generate_metadata

import os
import sys
import torch

# ------------------------------------------------------------------
# 1⃣  Make sure the parent folder of the package is on sys.path
#     (…/v17/gliclass_source   ←  NOT the inner ‘gliclass/’ folder)
# ------------------------------------------------------------------
sys.path.append(os.path.abspath("./gliclass_source"))

from transformers import AutoTokenizer
from gliclass.model    import GLiClassModel
from gliclass.pipeline import ZeroShotClassificationPipeline

# ------------------------------------------------------------------
# 2⃣  Model + label setup
# ------------------------------------------------------------------
MODEL_ID = "knowledgator/gliclass-modern-base-v2.0-init"

LABELS = [
    "projects", "tasks", "meta", "humor", "personal", "weather",
    "reminder", "welding", "callback", "planning", "fix", "testing", "deadline"
]

device = "cuda" if torch.cuda.is_available() else "cpu"

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model     = GLiClassModel.from_pretrained(MODEL_ID).to(device)

pipe = ZeroShotClassificationPipeline(
    model=model,
    tokenizer=tokenizer,
    device=device,          # must be string ("cuda" / "cpu")
)

# ------------------------------------------------------------------
# 3⃣  Run classification
# ------------------------------------------------------------------
text   = "Let's refactor the camera module this weekend."
scores = pipe(text, labels=LABELS)           # returns [[{label, score}, …]]

inner_scores = scores[0]                     # unpack the single-sentence result
topic        = inner_scores[0]["label"]      # top label
tags         = [d["label"] for d in inner_scores if d["score"] >= 0.30]

print({"topic": topic, "tags": tags})
