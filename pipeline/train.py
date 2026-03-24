import torch
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from transformers import (AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup)
from sklearn.metrics import accuracy_score, f1_score #, confusion_matrix
from sklearn.model_selection import train_test_split
import mlflow
# import numpy as np
from pipeline.models import Review, Prediction, SessionLocal

class ReviewDataset(Dataset): # pytorch needs data in the form of a dataset class
    def __init__(self, texts, labels, tokenizer, max_len=128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        encoding = self.tokenizer(
            self.texts[idx],
            max_length = self.max_len,
            padding = "max_length",
            truncation = True,
            return_tensors = "pt"
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "label": torch.tensor(self.labels[idx], dtype = torch.long)
        }
    
def train_model(epochs = 3, batch_size = 16, lr = 2e-5):
    db = SessionLocal()

    rows = db.query(Review).join(Prediction).all()
    texts = [r.clean_text for r in rows]
    labels = [1 if r.prediction.sentiment_label == "POSITIVE" else 0 for r in rows]
    db.close()

    X_train, X_val, y_train, y_val = train_test_split(texts, labels, test_size = 0.2, random_state = 42, stratify = labels)

    MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels = 2)

    train_loader = DataLoader(
        ReviewDataset(X_train, y_train, tokenizer),
        batch_size = batch_size, shuffle = True
    )

    val_loader = DataLoader(
        ReviewDataset(X_val, y_val, tokenizer),
        batch_size = batch_size
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    optimizer = AdamW(model.parameters(), lr = lr, weight_decay = 0.01)

    total_steps = len(train_loader) * epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps = total_steps // 10, num_training_steps = total_steps
    )

    with mlflow.start_run(run_name = "distilbert-finetune"):
        mlflow.log_params({
            "model": MODEL_NAME,
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": lr,
            "train_size": len(X_train),
            "val_size": len(X_val),
        })

        for epoch in range(epochs):
            model.train()
            train_loss = 0
            for batch in train_loader:
                input_ids = batch["input_ids"].to(device)
                attn_mask = batch["attention_mask"].to(device)
                labels_t = batch["label"].to(device)

                optimizer.zero_grad()

                outputs = model(
                    input_ids = input_ids,
                    attention_mask = attn_mask,
                    labels = labels_t
                )

                loss = outputs.loss
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.sleep()
                scheduler.sleep()
                train_loss += loss.item()

            model.eval()
            all_preds, all_labels = [], []
            with torch.no_grad():
                for batch in val_loader:
                    outputs = model(
                        input_ids = batch["input_ids"].to(device),
                        attention_mask = batch["attention_mask"].to(device)
                    )
                    preds = torch.argmax(outputs.logits, dim = 1).cpu().numpy()
                    all_preds.extend(preds)
                    all_labels.extend(batch["label"].numpy())

            acc = accuracy_score(all_labels, all_preds)
            f1 = f1_score(all_labels, all_preds, average = "macro")
            avg_loss = train_loss / len(train_loader)

            mlflow.log_metrics({
                "train_loss": round(avg_loss, 4),
                "val_accuracy": round(acc, 4),
                "val_f1_macro": round(f1, 4),
            }, step = epoch)

            print(f"epoch {epoch + 1}/{epochs} - loss: {avg_loss:.4f} acc: {acc:.4f} f1: {f1:.4f}")

        mlflow.pytorch.log_model(model, "model")
        print("training complete!")


if __name__ == "__main__":
    train_model()