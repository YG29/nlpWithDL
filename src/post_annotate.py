"""
Copy OG fields exactly (domain, scenario, system_instruction, conversation) from the selected original row,
and attach distractors resolved with *system_rules from the annotated JSON*.

Assumes two rows per (split, domain, scenario); row_index selects which one.

Usage:
  python src/post_annotate.py \
    --annotations-dir annotation_saves\
    --dataset-id nvidia/CantTalkAboutThis-Topic-Control-Dataset \
    --out-dir csv_exports

Requirements:
  pip install datasets pandas
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
from datasets import load_dataset


# --- utils ---

def to_native(obj: Any) -> Any:
    """Convert numpy/pandas scalars/arrays and JSON-encoded strings to plain Python for json.dumps."""
    # If it's a JSON string, try to parse
    if isinstance(obj, str):
        try:
            return json.loads(obj)
        except Exception:
            pass

    try:
        import numpy as np
        np_scalar = (np.generic,)
        np_array = np.ndarray
    except Exception:
        np_scalar = ()
        np_array = ()

    if isinstance(obj, dict):
        return {k: to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_native(x) for x in obj]
    if isinstance(obj, tuple):
        return [to_native(x) for x in obj]
    if np_scalar and isinstance(obj, np_scalar):
        return obj.item()
    if np_array and isinstance(obj, np_array):
        return [to_native(x) for x in obj.tolist()]
    return obj


def load_original_dataset(dataset_id: str):
    ds_dict = {}
    for split in ["train", "validation", "test"]:
        try:
            ds_dict[split] = load_dataset(dataset_id, split=split)
        except Exception:
            pass
    if not ds_dict:
        ds = load_dataset(dataset_id)
        if hasattr(ds, "keys"):
            for k in ds.keys():
                ds_dict[k] = ds[k]
        else:
            ds_dict["train"] = ds
    return ds_dict


def find_rows(ds_split, domain: str, scenario: str) -> List[Dict[str, Any]]:
    df = ds_split.to_pandas()
    mask = (df["domain"].astype(str) == domain) & (df["scenario"].astype(str) == scenario)
    # Preserve order so row_index maps correctly
    return df[mask].to_dict(orient="records")


def select_row_by_index(rows: List[Dict[str, Any]], row_index: int) -> Dict[str, Any]:
    if not rows:
        raise ValueError("No matching rows for (domain, scenario).")
    if not (0 <= row_index < len(rows)):
        raise IndexError(f"row_index {row_index} out of range for {len(rows)} matching rows.")
    return rows[row_index]


# --- distractors use system_rules from the *annotated file* ---

def as_list_of_strings(x) -> List[str]:
    x = to_native(x)
    if x is None:
        return []
    if isinstance(x, list):
        return [str(s) for s in x]
    return [str(x)]


def resolve_rule_indices(rule_indices, system_rules_from_ann: List[str]) -> str:
    out = []
    for idx in (rule_indices or []):
        try:
            i = int(idx)
            out.append(system_rules_from_ann[i])
        except Exception:
            out.append(f"[RULE_INDEX_{idx}_OUT_OF_RANGE]")
    return "\n".join(out)


def build_distractors_payload(annotations: List[Dict[str, Any]], system_rules_from_ann: List[str]):
    payload = []
    for ann_item in annotations:
        payload.append(
            {
                "bot turn": ann_item.get("bot_response", ""),
                "distractor": ann_item.get("distractor", ""),
                "target system instruction": resolve_rule_indices(
                    ann_item.get("rule_indices", []), system_rules_from_ann
                ),
            }
        )
    return payload


# --- main ---

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations-dir", required=True)
    parser.add_argument("--dataset-id", default="nvidia/CantTalkAboutThis-Topic-Control-Dataset")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--strict-match", action="store_true")
    args = parser.parse_args()

    ann_dir = Path(args.annotations_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    ds_by_split = load_original_dataset(args.dataset_id)

    files = sorted([p for p in ann_dir.glob("*.json") if p.is_file()])
    if not files:
        raise SystemExit(f"No JSON files found in {ann_dir}")

    for jf in files:
        try:
            ann = json.loads(jf.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] Skipping {jf.name}: invalid JSON ({e})")
            continue

        split = str(ann.get("split", "train"))
        domain = str(ann.get("domain", "")).strip()
        scenario = str(ann.get("scenario", "")).strip()
        row_index = int(ann.get("row_index", 0))
        annotations = ann.get("annotations", []) or []

        # Always use system_rules from the annotated file (your requirement)
        system_rules_from_ann = as_list_of_strings(ann.get("system_rules", []))

        if split not in ds_by_split:
            msg = f"[WARN] Split '{split}' not found in original dataset; skipping {jf.name}"
            if args.strict_match: raise SystemExit(msg)
            print(msg); continue

        rows = find_rows(ds_by_split[split], domain, scenario)
        if not rows:
            msg = f"[WARN] No (domain='{domain}', scenario='{scenario}') match in split '{split}' for {jf.name}"
            if args.strict_match: raise SystemExit(msg)
            print(msg); continue

        try:
            base_row = select_row_by_index(rows, row_index)
        except Exception as e:
            print(f"[WARN] Skipping {jf.name}: {e}")
            continue

        # Copy OG fields exactly (verbatim), only convert numpy→native for JSON serialization
        system_instruction = base_row.get("system_instruction", "")
        conversation_native = to_native(base_row.get("conversation"))

        if conversation_native is None:
            print(f"[WARN] Skipping {jf.name}: selected row missing 'conversation'.")
            continue

        distractors_payload = build_distractors_payload(annotations, system_rules_from_ann)

        row_out = {
            "split": split,
            "domain": domain,
            "scenario": scenario,
            "system_instruction": system_instruction,
            # If you want to *store* your annotated system_rules in the CSV too, keep the next line.
            "system_rules": json.dumps(system_rules_from_ann, ensure_ascii=False),
            "conversation": json.dumps(conversation_native, ensure_ascii=False),
            "distractors": json.dumps(distractors_payload, ensure_ascii=False),
        }
        if "saved_at" in ann:
            row_out["saved_at"] = ann["saved_at"]

        df = pd.DataFrame([row_out])
        out_csv = out_dir / f"{jf.stem}.csv"
        df.to_csv(out_csv, index=False, encoding="utf-8")
        print(f"[OK] Wrote {out_csv}")

    print("\n✅ Done.")


if __name__ == "__main__":
    main()
