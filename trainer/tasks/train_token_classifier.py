"""
Token Classification Training Task (ARQ Job) + MLflow Integration
อ้างอิงจาก: https://huggingface.co/learn/llm-course/en/chapter7/2

Flow การทำงาน:
1. โหลด Dataset จาก MinIO (parquet files)
2. Load Tokenizer + Model (distilbert-base-uncased)
3. Tokenize + Align Labels กับ Subwords
4. เทรนด้วย HuggingFace Trainer API
5. บันทึก Training Metrics → MLflow Tracking
6. บันทึก Model → MLflow Model Registry
7. บันทึก Training Log → MinIO (backup)
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import evaluate
import datasets as hf_datasets
import mlflow
import mlflow.transformers
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    DataCollatorForTokenClassification,
    Trainer,
    TrainerCallback,
    TrainingArguments,
)

from tasks.minio_utils import (
    download_dataset_from_minio,
    upload_model_to_minio,
    upload_log_to_minio,
)

logger = logging.getLogger(__name__)

# ── Label Names สำหรับ CoNLL-2003 NER Dataset ──
# O = Outside (ไม่ใช่ Entity)
# B-PER = Beginning of Person name
# I-PER = Inside Person name
# B-ORG = Beginning of Organization
# I-ORG = Inside Organization
# B-LOC = Beginning of Location
# I-LOC = Inside Location
# B-MISC = Beginning of Miscellaneous
# I-MISC = Inside Miscellaneous
CONLL2003_LABEL_NAMES = [
    "O", "B-PER", "I-PER", "B-ORG", "I-ORG",
    "B-LOC", "I-LOC", "B-MISC", "I-MISC",
]


class TrainingLogCallback(TrainerCallback):
    """Custom Callback สำหรับเก็บ Log ทุก Epoch"""

    def __init__(self):
        self.epoch_logs: list[dict] = []

    def on_epoch_end(self, args, state, control, **kwargs):
        """บันทึก Metrics หลังสิ้นสุดแต่ละ Epoch"""
        log_entry = {
            "epoch": state.epoch,
            "step": state.global_step,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        # ดึง metrics ล่าสุด
        if state.log_history:
            latest = state.log_history[-1]
            log_entry.update({
                k: v for k, v in latest.items()
                if k not in ("epoch", "step")
            })
        self.epoch_logs.append(log_entry)
        logger.info(f"📊 Epoch {state.epoch:.0f} completed: {log_entry}")


class MLflowLoggingCallback(TrainerCallback):
    """Callback สำหรับ Log Metrics ไป MLflow ทุก Epoch"""

    def on_log(self, args, state, control, logs=None, **kwargs):
        """ส่ง metrics ไป MLflow ทุกครั้งที่ Trainer log"""
        if logs and mlflow.active_run():
            step = state.global_step
            for key, value in logs.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(key, value, step=step)


def tokenize_and_align_labels(examples: dict, tokenizer, label_all_tokens: bool = False) -> dict:
    """
    Tokenize inputs และ Align Labels กับ Subword Tokens

    ปัญหา: BERT Tokenizer แบ่งคำออกเป็น Subwords เช่น
    "Washington" → ["Wash", "##ington"]
    แต่ Label ต้นฉบับมีแค่ 1 Label ต่อ 1 คำ

    วิธีแก้: Label แรกของแต่ละคำ = Label จริง
             Subword ที่เหลือ = -100 (ไม่นำมาคำนวณ Loss)

    Ref: https://huggingface.co/learn/llm-course/en/chapter7/2
    """
    tokenized_inputs = tokenizer(
        examples["tokens"],
        truncation=True,
        is_split_into_words=True,  # Input เป็น List of Words แล้ว
    )

    all_labels = []
    for i, labels in enumerate(examples["ner_tags"]):
        word_ids = tokenized_inputs.word_ids(batch_index=i)
        aligned_labels = []
        previous_word_idx = None

        for word_idx in word_ids:
            if word_idx is None:
                # Special tokens ([CLS], [SEP], padding) → -100
                aligned_labels.append(-100)
            elif word_idx != previous_word_idx:
                # Token แรกของคำใหม่ → ใช้ Label จริง
                aligned_labels.append(labels[word_idx])
            else:
                # Subword ที่เหลือ
                if label_all_tokens:
                    aligned_labels.append(labels[word_idx])
                else:
                    aligned_labels.append(-100)  # ไม่นำมา Train

            previous_word_idx = word_idx

        all_labels.append(aligned_labels)

    tokenized_inputs["labels"] = all_labels
    return tokenized_inputs


def build_compute_metrics(label_names: list[str]):
    """
    สร้างฟังก์ชันคำนวณ Metrics สำหรับ NER
    ใช้ seqeval library (F1, Precision, Recall per Entity type)
    """
    seqeval = evaluate.load("seqeval")

    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        # แปลง Logits → Label IDs ที่มี Probability สูงสุด
        predictions = np.argmax(predictions, axis=2)

        true_labels = []
        true_predictions = []

        for pred_seq, label_seq in zip(predictions, labels):
            true_label_row = []
            true_pred_row = []
            for p, l in zip(pred_seq, label_seq):
                if l != -100:  # ข้าม padding และ special tokens
                    true_label_row.append(label_names[l])
                    true_pred_row.append(label_names[p])
            true_labels.append(true_label_row)
            true_predictions.append(true_pred_row)

        results = seqeval.compute(predictions=true_predictions, references=true_labels)
        return {
            "precision": results["overall_precision"],
            "recall": results["overall_recall"],
            "f1": results["overall_f1"],
            "accuracy": results["overall_accuracy"],
        }

    return compute_metrics


async def train_token_classifier(
    ctx: dict,
    job_id: str,
    dataset_name: str,
    model_name: str,
    num_epochs: int,
    learning_rate: float,
) -> dict:
    """
    ARQ Job Function: เทรน Token Classification Model + บันทึกผลลง MLflow

    Args:
        ctx: ARQ context (ส่งจาก Worker)
        job_id: UUID ของ Job สำหรับ tracking
        dataset_name: ชื่อ Dataset ใน MinIO เช่น "conll2003"
        model_name: ชื่อ Pre-trained Model เช่น "distilbert-base-uncased"
        num_epochs: จำนวน Epoch
        learning_rate: Learning Rate

    Returns:
        dict: สรุปผลการเทรน
    """
    started_at = datetime.now(timezone.utc).isoformat()
    logger.info(f"🎯 [Job {job_id}] Starting Token Classification Training")
    logger.info(f"   Dataset: {dataset_name}")
    logger.info(f"   Model:   {model_name}")
    logger.info(f"   Epochs:  {num_epochs}, LR: {learning_rate}")

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"   Device:  {device.upper()}")

    # ── Setup MLflow Tracking ──
    mlflow_tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment("token-classification")
    logger.info(f"   MLflow:  {mlflow_tracking_uri}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        dataset_dir = tmp_path / "dataset"
        model_output_dir = tmp_path / "model_output"
        log_output_path = tmp_path / "training_log.json"
        model_output_dir.mkdir()

        # ────────────────────────────────────────
        # Step 1: โหลด Dataset จาก MinIO
        # ────────────────────────────────────────
        logger.info(f"📥 [Step 1] Loading dataset '{dataset_name}' from MinIO...")
        dataset_local_dir = download_dataset_from_minio(
            dataset_name=dataset_name,
            local_dir=str(dataset_dir),
        )

        # โหลด parquet files เป็น DatasetDict
        raw_dataset = hf_datasets.DatasetDict({
            split: hf_datasets.Dataset.from_parquet(str(dataset_local_dir / f"{split}.parquet"))
            for split in ["train", "validation", "test"]
            if (dataset_local_dir / f"{split}.parquet").exists()
        })
        logger.info(f"✅ Dataset loaded: {raw_dataset}")

        # ดึง Label Names จาก Dataset feature (ถ้าเป็น ClassLabel) หรือใช้ค่า default
        try:
            from datasets import ClassLabel
            ner_feature = raw_dataset["train"].features.get("ner_tags")
            inner = getattr(ner_feature, "feature", None)
            if isinstance(inner, ClassLabel):
                label_names = inner.names
            else:
                label_names = CONLL2003_LABEL_NAMES
        except Exception:
            label_names = CONLL2003_LABEL_NAMES
        logger.info(f"   Labels ({len(label_names)}): {label_names}")

        # ════════════════════════════════════════
        # MLflow Run — เปิด Run แล้วทำทุกอย่างภายใน
        # ════════════════════════════════════════
        with mlflow.start_run(run_name=f"job-{job_id[:8]}") as run:
            mlflow_run_id = run.info.run_id
            logger.info(f"📊 MLflow Run started: {mlflow_run_id}")

            # ── Log Parameters (Hyperparameters) ──
            mlflow.log_params({
                "job_id": job_id,
                "dataset_name": dataset_name,
                "model_name": model_name,
                "num_epochs": num_epochs,
                "learning_rate": learning_rate,
                "device": device,
                "label_count": len(label_names),
            })

            # ────────────────────────────────────────
            # Step 2: Load Tokenizer + Model
            # ────────────────────────────────────────
            logger.info(f"🤖 [Step 2] Loading model '{model_name}'...")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForTokenClassification.from_pretrained(
                model_name,
                num_labels=len(label_names),
                id2label={i: label for i, label in enumerate(label_names)},
                label2id={label: i for i, label in enumerate(label_names)},
            )
            logger.info(f"✅ Model loaded: {model_name} ({model.num_parameters():,} params)")
            mlflow.log_param("total_params", model.num_parameters())

            # ────────────────────────────────────────
            # Step 3: Tokenize + Align Labels
            # ────────────────────────────────────────
            logger.info("🔤 [Step 3] Tokenizing dataset and aligning labels...")
            tokenized_dataset = raw_dataset.map(
                lambda examples: tokenize_and_align_labels(examples, tokenizer),
                batched=True,
                remove_columns=raw_dataset["train"].column_names,
            )
            logger.info(f"✅ Tokenization complete: {tokenized_dataset}")

            # ────────────────────────────────────────
            # Step 4: Setup Training
            # ────────────────────────────────────────
            logger.info("⚙️  [Step 4] Setting up TrainingArguments...")
            data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)
            log_callback = TrainingLogCallback()
            mlflow_callback = MLflowLoggingCallback()

            training_args = TrainingArguments(
                output_dir=str(model_output_dir),
                num_train_epochs=num_epochs,
                learning_rate=learning_rate,
                per_device_train_batch_size=16,
                per_device_eval_batch_size=16,
                weight_decay=0.01,
                evaluation_strategy="epoch",
                save_strategy="epoch",
                load_best_model_at_end=True,
                metric_for_best_model="f1",
                push_to_hub=False,
                logging_strategy="epoch",
                report_to="none",   # ปิด WandB / TensorBoard (ใช้ MLflow แทน)
                no_cuda=(device == "cpu"),
            )

            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=tokenized_dataset["train"],
                eval_dataset=tokenized_dataset.get("validation"),
                tokenizer=tokenizer,
                data_collator=data_collator,
                compute_metrics=build_compute_metrics(label_names),
                callbacks=[log_callback, mlflow_callback],
            )

            # ────────────────────────────────────────
            # Step 5: เทรน Model
            # ────────────────────────────────────────
            logger.info(f"🚀 [Step 5] Starting training ({num_epochs} epochs)...")
            train_result = trainer.train()
            logger.info(f"✅ Training complete! Metrics: {train_result.metrics}")

            # ── Log Final Training Metrics ไป MLflow ──
            mlflow.log_metrics({
                "final_train_loss": train_result.metrics.get("train_loss", 0),
                "train_runtime": train_result.metrics.get("train_runtime", 0),
                "train_samples_per_second": train_result.metrics.get("train_samples_per_second", 0),
            })

            # ── Evaluate and Log Eval Metrics ──
            if tokenized_dataset.get("validation"):
                eval_results = trainer.evaluate()
                logger.info(f"📈 Eval results: {eval_results}")
                mlflow.log_metrics({
                    "eval_loss": eval_results.get("eval_loss", 0),
                    "eval_f1": eval_results.get("eval_f1", 0),
                    "eval_precision": eval_results.get("eval_precision", 0),
                    "eval_recall": eval_results.get("eval_recall", 0),
                    "eval_accuracy": eval_results.get("eval_accuracy", 0),
                })

            # ────────────────────────────────────────
            # Step 6: บันทึก Model → MLflow Model Registry
            # ────────────────────────────────────────
            logger.info("📦 [Step 6] Saving model to MLflow Model Registry...")

            # บันทึก Model ลง Local ก่อน แล้ว Log เข้า MLflow
            trainer.save_model(str(model_output_dir / "final"))
            tokenizer.save_pretrained(str(model_output_dir / "final"))

            # Log model artifacts ไป MLflow
            mlflow.log_artifacts(str(model_output_dir / "final"), artifact_path="model")

            # ── Register Model ใน MLflow Model Registry ──
            model_uri = f"runs:/{mlflow_run_id}/model"
            registered_model = mlflow.register_model(
                model_uri=model_uri,
                name="token-classifier",
            )
            logger.info(
                f"✅ Model registered: token-classifier "
                f"v{registered_model.version}"
            )

            # ────────────────────────────────────────
            # Step 7: บันทึก Training Log → MinIO (backup)
            # ────────────────────────────────────────
            logger.info("📝 [Step 7] Saving training log...")
            training_summary = {
                "job_id": job_id,
                "mlflow_run_id": mlflow_run_id,
                "mlflow_model_version": registered_model.version,
                "dataset_name": dataset_name,
                "model_name": model_name,
                "num_epochs": num_epochs,
                "learning_rate": learning_rate,
                "device": device,
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "train_metrics": train_result.metrics,
                "epoch_logs": log_callback.epoch_logs,
                "label_names": label_names,
                "full_log_history": trainer.state.log_history,
            }

            with open(log_output_path, "w", encoding="utf-8") as f:
                json.dump(training_summary, f, ensure_ascii=False, indent=2)

            # Log training_log.json เป็น MLflow Artifact ด้วย
            mlflow.log_artifact(str(log_output_path))

            # Upload ไป MinIO (backup)
            log_object = upload_log_to_minio(job_id, str(log_output_path))

            # Upload model ไป MinIO (backup)
            model_objects = upload_model_to_minio(job_id, str(model_output_dir / "final"))

            result = {
                "job_id": job_id,
                "status": "completed",
                "mlflow_run_id": mlflow_run_id,
                "mlflow_model_version": registered_model.version,
                "model_objects": model_objects,
                "log_object": log_object,
                "train_metrics": train_result.metrics,
            }
            logger.info(f"🎉 [Job {job_id}] Training pipeline finished successfully!")
            return result
