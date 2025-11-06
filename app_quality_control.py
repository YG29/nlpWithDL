# streamlit_app.py
# CSV annotator that loads the CSV from your local Git repo folder (current working directory).
# - Sidebar: pick CSV from repo (optionally search subfolders) or upload
# - Main: Title -> Scenario -> System Prompt -> Bot turn + Distractor (read-only) -> Broken span
# - Save: writes span into a new column next to the distractor column and exports only a JSON file for that row
# - Optional: save full annotated CSV for download

import json
import re
import os
from glob import glob
from pathlib import Path
from typing import Optional, Tuple, List

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Distractor Span Annotator", page_icon="🧭", layout="wide")

# ---------------- Config ----------------
DEFAULT_FILE_NAME = "Group 10 - Distractors - 20 random sample.csv"  # expected repo CSV name
DEFAULT_EXPORT_DIR = "distractor_span"
ANNOT_COL_NAME = "broken_span"
SAVE_SUFFIX = "_annotated"

# ---------------- Helpers ----------------
def ensure_col_insert_after(df: pd.DataFrame, new_col: str, after_col: Optional[str]) -> None:
    if new_col in df.columns:
        return
    insert_at = len(df.columns)
    if after_col in df.columns:
        insert_at = list(df.columns).index(after_col) + 1
    df.insert(insert_at, new_col, "")

def save_whole_csv(original_path: Path, df: pd.DataFrame) -> Path:
    out = original_path.with_name(f"{original_path.stem}{SAVE_SUFFIX}{original_path.suffix or '.csv'}")
    df.to_csv(out, index=False)
    return out

def discover_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    cols = [c.lower() for c in df.columns]

    scenario_col = None
    for cand in ["scenario", "scenarios", "title", "name"]:
        if cand in cols:
            scenario_col = df.columns[cols.index(cand)]
            break

    system_col = None
    for cand in ["system_instruction", "system prompt", "system_prompt", "system rules", "system_rules"]:
        if cand in cols:
            system_col = df.columns[cols.index(cand)]
            break

    distractor_col = None
    for cand in ["distractors", "distractor", "last column", "last_column", "annotation", "annotations"]:
        if cand in cols:
            distractor_col = df.columns[cols.index(cand)]
            break
    if distractor_col is None and len(df.columns) > 0:
        distractor_col = df.columns[-1]

    return scenario_col, system_col, distractor_col

def safe_slug(s: str, maxlen: int = 60) -> str:
    base = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(s).strip())
    base = re.sub(r"_+", "_", base).strip("_")
    return base[:maxlen] if base else "row"

def save_row_to_repo_folder(
    df: pd.DataFrame,
    row_idx: int,
    export_dir: Path,
    scenario_col: str,
    system_col: str,
    distractor_col: str,
    annot_col: str
) -> Path:
    """Save only a JSON file for this row into export_dir."""
    export_dir.mkdir(parents=True, exist_ok=True)
    row = df.iloc[row_idx]
    scenario = row.get(scenario_col, "")
    slug = safe_slug(scenario) or f"row_{row_idx}"

    payload = {
        "row_index": int(row_idx),
        "scenario": scenario,
        "system_prompt": row.get(system_col, ""),
        "distractor_cell_raw": row.get(distractor_col, ""),
        "broken_span": row.get(annot_col, ""),
        "all_row_values": row.to_dict(),
    }

    json_path = export_dir / f"{row_idx:05d}_{slug}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return json_path

def readonly_textbox(label: str, value: str, height: int, key: str):
    """Render a read-only textarea that looks enabled (not greyed)."""
    st.markdown(f"**{label}**")
    html = f"""
    <div style="border:1px solid #e5e7eb;border-radius:6px;padding:8px;">
      <textarea readonly
        style="
          width:100%;
          height:{height}px;
          border:none;
          outline:none;
          resize:vertical;
          background-color:#ffffff;
          color:inherit;
          font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
          line-height:1.4;
        ">{(value or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')}</textarea>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def list_repo_csvs(base_dir: Path, recursive: bool = True, limit: int = 500) -> List[Path]:
    """List CSV files under base_dir. If recursive, search subfolders."""
    pattern = "**/*.csv" if recursive else "*.csv"
    paths = [Path(p) for p in glob(str(base_dir / pattern), recursive=recursive)]
    # Keep it stable and not huge
    paths = sorted(paths)[:limit]
    return paths

# ---------------- Load CSV (from repo) ----------------
st.sidebar.header("Data source (from your repo)")

repo_base = Path(st.sidebar.text_input("Repo folder (relative)", value=".")).resolve()
search_subfolders = st.sidebar.checkbox("Search subfolders", value=True)

# Prefer the expected filename if present, else list candidates
default_path = repo_base / DEFAULT_FILE_NAME
csv_candidates = []
if default_path.exists():
    csv_candidates = [default_path]
else:
    csv_candidates = list_repo_csvs(repo_base, recursive=search_subfolders)

mode = st.sidebar.radio("Pick CSV", ["From repo", "Upload"], horizontal=True)

csv_path: Optional[Path] = None
df: Optional[pd.DataFrame] = None

if mode == "From repo":
    if not csv_candidates:
        st.sidebar.warning("No CSVs found in the selected folder. You can upload one instead.")
    else:
        show_labels = [str(p.relative_to(repo_base)) for p in csv_candidates]
        idx = st.sidebar.selectbox("CSV file", options=list(range(len(csv_candidates))), format_func=lambda i: show_labels[i], index=0)
        csv_path = csv_candidates[idx]
        df = pd.read_csv(csv_path)
else:
    up = st.sidebar.file_uploader("Upload a CSV", type=["csv"])
    if up is not None:
        csv_path = repo_base / up.name  # not saved to disk; just for naming
        df = pd.read_csv(up)

if df is None:
    st.info("Pick or upload a CSV in the sidebar to begin.")
    st.stop()

# ---------------- Column mapping ----------------
scenario_guess, system_guess, distractor_guess = discover_columns(df)
scenario_col = st.sidebar.selectbox(
    "Scenario column", list(df.columns),
    index=list(df.columns).index(scenario_guess) if scenario_guess in df.columns else 0
)
system_col = st.sidebar.selectbox(
    "System Prompt column", list(df.columns),
    index=list(df.columns).index(system_guess) if system_guess in df.columns else 0
)
distractor_col = st.sidebar.selectbox(
    "Distractors column", list(df.columns),
    index=list(df.columns).index(distractor_guess) if distractor_guess in df.columns else len(df.columns) - 1
)

# Ensure annotation column exists and sits right after the distractor column
ensure_col_insert_after(df, ANNOT_COL_NAME, distractor_col)

# Export directory inside repo
export_dir_str = st.sidebar.text_input("Per-row export folder", value=DEFAULT_EXPORT_DIR)
export_dir = (repo_base / export_dir_str).resolve()

st.sidebar.markdown("---")

# Scrollable row picker
def scenario_label(idx: int) -> str:
    val = df.iloc[idx].get(scenario_col, f"Row {idx}")
    s = str(val)
    return (s[:80] + "…") if len(s) > 80 else s

row_index = st.sidebar.selectbox(
    "Pick a row / scenario",
    options=list(range(len(df))),
    format_func=scenario_label,
    index=0,
)

# ---------------- Main layout ----------------
st.title("🧭 Distractor Span Annotator")

row = df.iloc[row_index]
scenario_name = str(row.get(scenario_col, "")) or f"Row {row_index}"
st.subheader(scenario_name)

st.markdown("**System Prompt**")
st.text_area(
    label="",
    value=str(row.get(system_col, "") or ""),
    height=180,
    key=f"sys_show_{row_index}",
)

# Read-only combined cell (normal appearance)
readonly_textbox(
    label="Bot turn + Distractor (raw cell from CSV)",
    value=str(row.get(distractor_col, "") or ""),
    height=200,
    key=f"combo_{row_index}",
)

st.markdown("**Broken span (what part of the system prompt is violated?)**")
current_span_val = "" if pd.isna(row.get(ANNOT_COL_NAME, "")) else str(row.get(ANNOT_COL_NAME, ""))
span_text = st.text_area(
    label="",
    value=current_span_val,
    height=120,
    placeholder='e.g., "Do not provide legal advice" or paste the exact span from the system prompt',
    key=f"span_{row_index}",
)

colA, colB = st.columns([1, 1])
with colA:
    if st.button("💾 Save to this row and export JSON", type="primary"):
        df.at[df.index[row_index], ANNOT_COL_NAME] = span_text
        json_path = save_row_to_repo_folder(
            df, row_index, export_dir, scenario_col, system_col, distractor_col, ANNOT_COL_NAME
        )
        rel_json = json_path.relative_to(repo_base) if json_path.is_relative_to(repo_base) else json_path
        st.success(f"Saved JSON for row {row_index}: {rel_json}")

with colB:
    if csv_path is not None and st.button("⬇️ Save full annotated CSV"):
        out_path = save_whole_csv(Path(csv_path), df)
        rel_csv = out_path.relative_to(repo_base) if out_path.is_relative_to(repo_base) else out_path
        st.success(f"Saved full CSV: {rel_csv}")
        st.download_button(
            "Download annotated CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=Path(out_path).name,
            mime="text/csv",
        )

st.markdown("---")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Rows", len(df))
with c2:
    st.metric("Annotated", int(df[ANNOT_COL_NAME].astype(str).str.len().gt(0).sum()))
with c3:
    st.metric("Repo base", str(repo_base))
with c4:
    st.metric("Export folder", str(export_dir.relative_to(repo_base)) if export_dir.exists() else str(export_dir))