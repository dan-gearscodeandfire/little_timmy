#!/usr/bin/env python3
"""Debug script to see raw GLiClass scores."""

import sys
sys.path.append("./gliclass_source")

from transformers import AutoTokenizer
from gliclass.model import GLiClassModel
from gliclass.pipeline import ZeroShotClassificationPipeline
import torch

MODEL_ID = "knowledgator/gliclass-modern-base-v2.0-init"
device = "cuda" if torch.cuda.is_available() else "cpu"

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = GLiClassModel.from_pretrained(MODEL_ID).to(device)
pipe = ZeroShotClassificationPipeline(model=model, tokenizer=tokenizer, device=device)

LABELS = [
    "stating facts",
    "asking questions",
    "personal data",
    "project activity",
    "future planning",
    "testing memory",
    "referencing past",
    "making jokes",
    "chatting casually",
    "technical issues",
    "urgent matters"
]

test_inputs = [
    "My cat's name is Winston",
    "What is my cat's name?",
    "I'm going to weld the chassis this weekend",
]

print("="*70)
print("GLiClass Raw Scores Debug")
print("="*70)

for text in test_inputs:
    print(f"\nInput: {text}")
    print("-"*70)
    scores = pipe(text, labels=LABELS)
    inner_scores = scores[0]
    
    # Show all scores
    for item in inner_scores:
        print(f"  {item['label']:30s} {item['score']:.4f}")
    
    # Show what would be selected
    print(f"\n  Top topic: {inner_scores[0]['label']}")
    tags_60 = [d["label"] for d in inner_scores if d["score"] >= 0.60]
    tags_70 = [d["label"] for d in inner_scores if d["score"] >= 0.70]
    print(f"  Tags @ 0.60: {tags_60}")
    print(f"  Tags @ 0.70: {tags_70}")

