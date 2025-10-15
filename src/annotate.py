# streamlit_app.py
# Enhanced UI to explore and *annotate* the "nvidia/CantTalkAboutThis-Topic-Control-Dataset"
# New capabilities:
# - Build a curated list of "System Rules" by picking lines from the system instruction (or typing your own)
# - Choose which dialog to view (clean conversation vs. with distractors)
# - Select/copy a bot (assistant) response from that dialog
# - Add a hand-written distractor and tag which rules it breaks (by index)
# - Accumulate multiple annotations and export a JSON file with:
#     { system_rules: [...], annotations: [{bot_response, distractor, rule_indices}], plus split/domain/scenario/context }
# - SAVE/LOAD annotations to continue work across sessions

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime

import streamlit as st
from datasets import load_dataset, Dataset

st.set_page_config(page_title="CantTalkAboutThis Annotator", page_icon="🧭", layout="wide")

st.title("🧭 CantTalkAboutThis Annotator")
st.caption("Dataset: nvidia/CantTalkAboutThis-Topic-Control-Dataset · Build rules, tag violations, export JSON")

# ---------- Constants ----------
SAVE_DIR = Path("annotation_saves")
SAVE_DIR.mkdir(exist_ok=True)


# ---------- Helpers ----------
@st.cache_data(show_spinner=True)
def get_dataset():
    return load_dataset("nvidia/CantTalkAboutThis-Topic-Control-Dataset")


def get_unique_domains(dset: Dataset) -> List[str]:
    try:
        return sorted({d for d in dset["domain"] if d is not None})
    except KeyError:
        return []


@st.cache_data(show_spinner=False)
def get_scenarios_for_domain(_dset: Dataset, domain: str) -> List[str]:
    subset = _dset.filter(lambda ex: ex.get("domain") == domain)
    return sorted({s for s in subset["scenario"] if s is not None})


@st.cache_data(show_spinner=False)
def get_matching(_dset: Dataset, domain: str, scenario: str) -> Dataset:
    return _dset.filter(lambda ex: ex.get("domain") == domain and ex.get("scenario") == scenario)


def safe_lines(text: str) -> List[str]:
    if not text:
        return []
    return [ln.strip() for ln in str(text).splitlines() if ln.strip()]


def extract_assistant_messages(dialog_obj: Any) -> List[str]:
    """Try to extract assistant messages from a variety of likely schemas."""
    msgs: List[str] = []
    if dialog_obj is None:
        return msgs

    # Case 1: list of {role, content} dicts
    if isinstance(dialog_obj, list):
        for item in dialog_obj:
            if isinstance(item, dict):
                role = item.get("role") or item.get("speaker") or item.get("author")
                content = item.get("content") or item.get("text") or item.get("message")
                if role and content and str(role).lower() in {"assistant", "bot", "system_response"}:
                    msgs.append(str(content))
            elif isinstance(item, str):
                # Heuristic: if it's a raw string list, include all (user may filter later)
                msgs.append(item)
        return [m for m in msgs if m]

    # Case 2: dict with messages
    if isinstance(dialog_obj, dict):
        candidates = dialog_obj.get("messages") or dialog_obj.get("turns") or dialog_obj.get("dialog")
        if isinstance(candidates, list):
            return extract_assistant_messages(candidates)

    # Fallback: treat as string
    if isinstance(dialog_obj, str):
        return safe_lines(dialog_obj)

    return msgs


def get_save_filename(split: str, domain: str, scenario: str, row_idx: int) -> str:
    """Generate a consistent filename for saving/loading."""
    safe_domain = domain.replace("/", "_").replace(" ", "_")
    safe_scenario = scenario.replace("/", "_").replace(" ", "_")
    return f"{split}_{safe_domain}_{safe_scenario}_row{row_idx}.json"


def save_work(split: str, domain: str, scenario: str, row_idx: int,
              system_instruction: str, system_rules: List[str],
              annotations: List[Dict[str, Any]]) -> str:
    """Save current work to a file."""
    filename = get_save_filename(split, domain, scenario, row_idx)
    filepath = SAVE_DIR / filename

    save_data = {
        "saved_at": datetime.now().isoformat(),
        "split": split,
        "domain": domain,
        "scenario": scenario,
        "row_index": row_idx,
        "system_instruction": system_instruction,
        "system_rules": system_rules,
        "annotations": annotations,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    return str(filepath)


def load_work(split: str, domain: str, scenario: str, row_idx: int) -> Dict[str, Any] | None:
    """Load previously saved work if it exists."""
    filename = get_save_filename(split, domain, scenario, row_idx)
    filepath = SAVE_DIR / filename

    if not filepath.exists():
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading saved work: {e}")
        return None


def list_saved_files() -> List[str]:
    """List all saved annotation files."""
    if not SAVE_DIR.exists():
        return []
    return sorted([f.name for f in SAVE_DIR.glob("*.json")])


def delete_save_file(filename: str) -> bool:
    """Delete a saved file."""
    try:
        (SAVE_DIR / filename).unlink()
        return True
    except Exception as e:
        st.error(f"Error deleting file: {e}")
        return False


# ---------- Load dataset ----------
with st.spinner("Loading dataset..."):
    ds = get_dataset()

# Sidebar: split / domain / scenario
st.sidebar.header("Controls")
st.sidebar.markdown("**Split:** `train` (annotations allowed only on train)")
split = "train"
if "train" not in ds:
    st.error("The dataset doesn't have a 'train' split.")
    st.stop()
dset: Dataset = ds["train"]

domains = get_unique_domains(dset)
if not domains:
    st.error("No domains found in the selected split.")
    st.stop()

selected_domain = st.sidebar.selectbox("Domain", domains)
scenarios = get_scenarios_for_domain(dset, selected_domain)
if not scenarios:
    st.warning("No scenarios for this domain in the selected split.")
    st.stop()

selected_scenario = st.sidebar.selectbox("Scenario", scenarios)

matching = get_matching(dset, selected_domain, selected_scenario)
if len(matching) == 0:
    st.error("No entries matched this domain & scenario.")
    st.stop()

# If multiple rows match, allow index selection
row_idx = 0
if len(matching) > 1:
    st.info(f"Multiple entries found (n={len(matching)}). Showing the first by default.")
    row_idx = st.number_input("Select match index", min_value=0, max_value=len(matching) - 1, value=0, step=1)

row: Dict[str, Any] = matching[int(row_idx)]

# ---------- Save/Load Management ----------
st.sidebar.markdown("---")
st.sidebar.subheader("💾 Save/Load Work")

# Check if there's saved work for this selection
saved_data = load_work(split, selected_domain, selected_scenario, int(row_idx))

if saved_data:
    st.sidebar.success(f"✅ Saved work found (from {saved_data.get('saved_at', 'unknown time')})")

    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("📂 Load Saved"):
            st.session_state.system_rules = saved_data.get("system_rules", [])
            st.session_state.annotations = saved_data.get("annotations", [])
            st.success("Loaded saved work!")
            st.rerun()

    with col2:
        if st.button("🗑️ Delete Save"):
            filename = get_save_filename(split, selected_domain, selected_scenario, int(row_idx))
            if delete_save_file(filename):
                st.success("Save deleted!")
                st.rerun()
else:
    st.sidebar.info("No saved work for this selection")

# Save current work button
if st.sidebar.button("💾 Save Current Work", type="primary"):
    try:
        filepath = save_work(
            split,
            selected_domain,
            selected_scenario,
            int(row_idx),
            row.get("system_instruction", ""),
            st.session_state.get("system_rules", []),
            st.session_state.get("annotations", [])
        )
        st.sidebar.success(f"✅ Saved to: {filepath}")
    except Exception as e:
        st.sidebar.error(f"Error saving: {e}")

# Show all saved files
with st.sidebar.expander("📁 All Saved Files"):
    saved_files = list_saved_files()
    if saved_files:
        for sf in saved_files:
            st.caption(sf)
    else:
        st.caption("No saved files yet")

# ---------- System Instruction & Rule Builder ----------
st.subheader("System Instruction → System Rules")
system_instruction = row.get("system_instruction") or ""

cA, cB = st.columns([2, 3])
with cA:
    st.markdown("**System Instruction (source)**")
    st.code(system_instruction or "<empty>", language="markdown")

with cB:
    # Initialize session state
    if "system_rules" not in st.session_state:
        st.session_state.system_rules: List[str] = []

    st.markdown("**Quick-add lines as rules**")
    lines = safe_lines(system_instruction)
    if not lines:
        st.caption("No lines detected — you can still add custom rules below.")

    # Multi-select lines to add in one shot
    preselect = st.multiselect(
        "Pick instruction lines to add as rules",
        options=lines,
        help="You can also type your own rule below and click Add",
    )
    cols = st.columns(2)
    with cols[0]:
        if st.button("➕ Add selected lines"):
            for ln in preselect:
                if ln not in st.session_state.system_rules:
                    st.session_state.system_rules.append(ln)
            st.rerun()
    with cols[1]:
        if st.button("🗑️ Clear all rules"):
            st.session_state.system_rules = []
            st.rerun()

    # Initialize custom rule in session state for proper clearing
    if "_custom_rule_input" not in st.session_state:
        st.session_state._custom_rule_input = ""

    custom_rule = st.text_input(
        "Or type a new rule",
        value=st.session_state._custom_rule_input,
        key="_custom_rule"
    )
    add_custom = st.button("➕ Add custom rule")
    if add_custom and custom_rule:
        rule = custom_rule.strip()
        if rule and rule not in st.session_state.system_rules:
            st.session_state.system_rules.append(rule)
            st.session_state._custom_rule_input = ""
            st.rerun()

    # Show current rules with stable indices
    st.markdown("### Current Rules (indexed)")
    if st.session_state.system_rules:
        for i, r in enumerate(st.session_state.system_rules):
            cols = st.columns([0.08, 0.82, 0.10])
            cols[0].markdown(f"**{i}**")
            cols[1].write(r)
            if cols[2].button("Remove", key=f"rm_rule_{i}"):
                st.session_state.system_rules.pop(i)
                st.rerun()
    else:
        st.caption("No rules yet — add some from the left or type your own.")

# ---------- Dialog Browser & Annotation ----------
st.subheader("Dialog → Pick a Bot Response & Create a Distractor")

# Choose which dialog to view
dialog_choice = st.radio(
    "Choose dialog source",
    options=["conversation", "conversation_with_distractors"],
    index=0,
    horizontal=True,
)

dialog_obj = row.get(dialog_choice)
assistant_msgs = extract_assistant_messages(dialog_obj)

with st.expander("Preview raw dialog object"):
    st.json(dialog_obj)

if not assistant_msgs:
    st.warning("No assistant messages detected in this dialog.")
else:
    st.markdown("**Assistant messages** (choose one to annotate)")


    # For readability, show truncated labels
    def labelify(msg: str, maxlen: int = 140) -> str:
        s = " ".join(str(msg).split())
        return (s[: maxlen - 1] + "…") if len(s) > maxlen else s


    selected_bot_msg = st.selectbox(
        "Bot response to annotate",
        options=assistant_msgs,
        format_func=labelify,
        help="Select which bot response this distractor is linked to"
    )

    st.text_area("Write a Distractor", key="_distractor", height=120, placeholder="Type your distractor here…")

    # Rule tagging
    rule_labels = [f"{i}: {r}" for i, r in enumerate(st.session_state.get("system_rules", []))]

    # Initialize selected rules in session state for proper clearing
    if "_selected_rule_labels" not in st.session_state:
        st.session_state._selected_rule_labels = []

    chosen_rule_labels = st.multiselect(
        "Which rules does this distractor break? (choose by label)",
        options=rule_labels,
        default=st.session_state._selected_rule_labels,
        key="_rule_multiselect"
    )

    # Convert back to indices
    chosen_indices: List[int] = []
    for lab in chosen_rule_labels:
        try:
            idx = int(lab.split(":", 1)[0])
            chosen_indices.append(idx)
        except Exception:
            pass

    if "annotations" not in st.session_state:
        st.session_state.annotations: List[Dict[str, Any]] = []

    if st.button("➕ Add annotation"):
        distractor = (st.session_state.get("_distractor") or "").strip()
        if not distractor:
            st.error("Distractor is required.")
        else:
            st.session_state.annotations.append(
                {
                    "distractor": distractor,
                    "rule_indices": sorted(set(chosen_indices)),
                }
            )
            # Clear inputs for next entry properly
            st.session_state._distractor = ""
            st.session_state._selected_rule_labels = []
            st.success("Annotation added. Don't forget to save your work!")
            st.rerun()

# Show current annotations with ability to remove
st.markdown("### Annotations")
if st.session_state.get("annotations"):
    for j, ann in enumerate(st.session_state.annotations):
        with st.expander(f"Annotation {j}"):
            st.write("**Distractor:**")
            st.write(ann["distractor"])
            st.write("**Rule indices:**", ann.get("rule_indices", []))
            if st.button("Remove", key=f"rm_ann_{j}"):
                st.session_state.annotations.pop(j)
                st.rerun()
else:
    st.caption("No annotations yet — add one above.")

# ---------- Export JSON ----------
st.markdown("---")

export_payload = {
    "split": split,
    "domain": selected_domain,
    "scenario": selected_scenario,
    "row_index": int(row_idx),
    "system_instruction": system_instruction,
    "system_rules": st.session_state.get("system_rules", []),
    "annotations": st.session_state.get("annotations", []),
    "exported_at": datetime.now().isoformat(),
}

st.download_button(
    label="⬇️ Download annotations JSON",
    data=json.dumps(export_payload, ensure_ascii=False, indent=2),
    file_name=f"canttalk_annotations_{split}_{selected_domain}_{selected_scenario}.json",
    mime="application/json",
)

# Also keep the previous lightweight export for the selected row
with st.expander("Advanced: Export full selection context"):
    full_export = {
        **export_payload,
        "conversation": row.get("conversation"),
        "conversation_with_distractors": row.get("conversation_with_distractors"),
        "distractors": row.get("distractors"),
    }
    st.download_button(
        label="⬇️ Download full JSON",
        data=json.dumps(full_export, ensure_ascii=False, indent=2),
        file_name=f"canttalk_full_{split}_{selected_domain}_{selected_scenario}.json",
        mime="application/json",
    )

# Footer stats
st.markdown("---")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Rows in split", len(dset))
with c2:
    st.metric("Unique domains", len(domains))
with c3:
    st.metric("Scenarios in domain", len(scenarios))
with c4:
    st.metric("Annotations", len(st.session_state.get("annotations", [])))