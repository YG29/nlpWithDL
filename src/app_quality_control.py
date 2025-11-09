# streamlit_app.py
# CSV annotator that loads the CSV from your local Git repo folder (current working directory).
# Sidebar: pick CSV from repo (optionally search subfolders) or upload
# Main: Title -> Scenario -> System Prompt -> Bot + Distractor (pretty cards) -> Broken span
# Save: writes span into a new column next to the distractor column and exports only a JSON file for that row
# Optional: save full annotated CSV for download
# usage: streamlit run src/app_quality_control.py

import json
import re
from glob import glob
from pathlib import Path
from typing import Optional, Tuple, List, Any

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

def list_repo_csvs(base_dir: Path, recursive: bool = True, limit: int = 500) -> List[Path]:
    pattern = "**/*.csv" if recursive else "*.csv"
    paths = [Path(p) for p in glob(str(base_dir / pattern), recursive=recursive)]
    paths = sorted(paths)[:limit]
    return paths

# ---------- Pretty renderer for Bot + Distractor without sideways scroll ----------
CARD_CSS = """
<style>
.card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 10px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
  background: #ffffff;
}
.card h4 {
  margin: 0 0 8px 0;
  font-size: 0.95rem;
  color: #111827;
}
.card p {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-wrap: anywhere;
  line-height: 1.5;
}
.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
@media(max-width: 1000px){
  .grid2 { grid-template-columns: 1fr; }
}
</style>
"""

def _html_escape(s: str) -> str:
    return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def _extract_pairs_from_cell(cell_text: str) -> List[Tuple[str, str]]:
    """
    Return list of (bot_turn, distractor) pairs.
    Handles:
      - JSON list of dicts with 'bot turn' and 'distractor'
      - JSON dict with those keys
      - Fallback: try simple heuristics, else put entire text as a single 'distractor'
    """
    s = (cell_text or "").strip()
    pairs: List[Tuple[str, str]] = []

    # Try JSON first
    if s.startswith("{") or s.startswith("["):
        try:
            obj: Any = json.loads(s)
            if isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict):
                        bt = item.get("bot turn") or item.get("bot_turn") or item.get("bot") or ""
                        ds = item.get("distractor") or item.get("distractors") or ""
                        if bt or ds:
                            pairs.append((str(bt), str(ds)))
            elif isinstance(obj, dict):
                bt = obj.get("bot turn") or obj.get("bot_turn") or obj.get("bot") or ""
                ds = obj.get("distractor") or obj.get("distractors") or ""
                if bt or ds:
                    pairs.append((str(bt), str(ds)))
        except Exception:
            pass

    if pairs:
        return pairs

    # Heuristic parse "bot turn: ... distractor: ..."
    low = s.lower()
    if "bot turn" in low and "distractor" in low:
        try:
            bot_part = re.split(r"(?i)distractor\s*:", s, maxsplit=1)[0]
            bot_val = re.split(r"(?i)bot\s*turn\s*:", bot_part, maxsplit=1)[1]
            dist_val = re.split(r"(?i)distractor\s*:", s, maxsplit=1)[1]
            pairs.append((bot_val.strip(), dist_val.strip()))
            return pairs
        except Exception:
            pass

    # Fallback
    return [("", s)]

def render_bot_and_distractor(cell_text: str, key: str) -> None:
    st.markdown("**Bot turn + Distractor**")
    st.markdown(CARD_CSS, unsafe_allow_html=True)

    pairs = _extract_pairs_from_cell(cell_text)
    if len(pairs) >= 2:
        st.markdown('<div class="grid2">', unsafe_allow_html=True)
        for i, (bt, ds) in enumerate(pairs[:2]):
            st.markdown(
                f"""
                <div class="card">
                  <h4>Set {i+1}</h4>
                  <p><strong>Bot turn</strong><br>{_html_escape(bt)}</p>
                  <br/>
                  <p><strong>Distractor</strong><br>{_html_escape(ds)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        bt, ds = pairs[0]
        st.markdown(
            f"""
            <div class="card">
              <h4>Set 1</h4>
              <p><strong>Bot turn</strong><br>{_html_escape(bt)}</p>
              <br/>
              <p><strong>Distractor</strong><br>{_html_escape(ds)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ---------------- Load CSV (from repo) ----------------
st.sidebar.header("Data source (from your repo)")

repo_base = Path(st.sidebar.text_input("Repo folder (relative)", value=".")).resolve()
search_subfolders = st.sidebar.checkbox("Search subfolders", value=True)

default_path = repo_base / DEFAULT_FILE_NAME
csv_candidates = [default_path] if default_path.exists() else list_repo_csvs(repo_base, recursive=search_subfolders)

mode = st.sidebar.radio("Pick CSV", ["From repo", "Upload"], horizontal=True)

csv_path: Optional[Path] = None
df: Optional[pd.DataFrame] = None

if mode == "From repo":
    if not csv_candidates:
        st.sidebar.warning("No CSVs found in the selected folder. You can upload one instead.")
    else:
        show_labels = [str(p.relative_to(repo_base)) for p in csv_candidates]
        idx = st.sidebar.selectbox(
            "CSV file",
            options=list(range(len(csv_candidates))),
            format_func=lambda i: show_labels[i],
            index=0,
            key="csv_file_select",
        )
        csv_path = csv_candidates[idx]
        # Robust CSV read
        try:
            df = pd.read_csv(csv_path)
        except UnicodeDecodeError:
            df = pd.read_csv(csv_path, encoding="latin-1")
else:
    up = st.sidebar.file_uploader("Upload a CSV", type=["csv"])
    if up is not None:
        csv_path = repo_base / up.name  # naming only
        try:
            df = pd.read_csv(up)
        except UnicodeDecodeError:
            up.seek(0)
            df = pd.read_csv(up, encoding="latin-1")

if df is None:
    st.info("Pick or upload a CSV in the sidebar to begin.")
    st.stop()

# ---------------- Column mapping ----------------
scenario_guess, system_guess, distractor_guess = discover_columns(df)
scenario_col = st.sidebar.selectbox(
    "Scenario column", list(df.columns),
    index=list(df.columns).index(scenario_guess) if scenario_guess in df.columns else 0,
    key="scenario_col_select",
)
system_col = st.sidebar.selectbox(
    "System Prompt column", list(df.columns),
    index=list(df.columns).index(system_guess) if system_guess in df.columns else 0,
    key="system_col_select",
)
distractor_col = st.sidebar.selectbox(
    "Distractors column", list(df.columns),
    index=list(df.columns).index(distractor_guess) if distractor_guess in df.columns else len(df.columns) - 1,
    key="distractor_col_select",
)

# Ensure annotation column exists and sits right after the distractor column
ensure_col_insert_after(df, ANNOT_COL_NAME, distractor_col)

# Export directory inside repo
export_dir_str = st.sidebar.text_input("Per-row export folder", value=DEFAULT_EXPORT_DIR, key="export_dir_input")
export_dir = (repo_base / export_dir_str).resolve()

st.sidebar.markdown("---")

# ---------------- Row picker ----------------
def unique_scenario_label(idx: int) -> str:
    """Make labels unique so the selectbox never collapses different rows into the same visible name."""
    val = df.iloc[idx].get(scenario_col, f"Row {idx}")
    s = str(val).replace("\n", " ")
    trunc = (s[:80] + "…") if len(s) > 80 else s
    # Prefix with a zero-padded index to guarantee uniqueness
    return f"#{idx:04d} | {trunc}"

row_index = st.sidebar.selectbox(
    "Pick a row / scenario",
    options=list(range(len(df))),
    format_func=unique_scenario_label,  # ensures no duplicate visible labels
    index=0,
    key="row_picker",
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
    key=f"sys_show_{row_index}",  # key depends on row_index so it refreshes on change
)

# Pretty, non-scroll, auto-wrapping cards for Bot + Distractor
render_bot_and_distractor(str(row.get(distractor_col, "") or ""), key=f"combo_{row_index}")

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
    if st.button("💾 Save to this row and export JSON", type="primary", key=f"save_btn_{row_index}"):
        df.at[df.index[row_index], ANNOT_COL_NAME] = span_text
        json_path = save_row_to_repo_folder(
            df, row_index, export_dir, scenario_col, system_col, distractor_col, ANNOT_COL_NAME
        )
        try:
            rel_json = json_path.relative_to(repo_base)
        except ValueError:
            rel_json = json_path
        st.success(f"Saved JSON for row {row_index}: {rel_json}")

with colB:
    if csv_path is not None and st.button("⬇️ Save full annotated CSV", key=f"save_csv_{row_index}"):
        out_path = save_whole_csv(Path(csv_path), df)
        try:
            rel_csv = out_path.relative_to(repo_base)
        except ValueError:
            rel_csv = out_path
        st.success(f"Saved full CSV: {rel_csv}")
        st.download_button(
            "Download annotated CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=Path(out_path).name,
            mime="text/csv",
            key=f"download_csv_{row_index}",
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
