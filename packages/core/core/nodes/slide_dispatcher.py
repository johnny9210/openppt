"""
Phase 2-A: Slide Dispatcher
Fan-out: dispatches parallel slide generation using LangGraph Send API.
Returns Command(goto=list[Send]) for proper fan-out.
create mode: all slides in parallel
edit mode: only target_slide_id
retry mode: only slides with failed semantic slots (avoids regenerating correct slides)
"""

from __future__ import annotations

from langgraph.types import Send, Command
from core.state import PPTState


def _find_failed_slide_ids(
    slides: list[dict],
    missing_slots: list[str],
) -> set[str]:
    """Map missing slot keys back to slide_ids using the slide_spec.

    Each slide in the spec has a ``slots`` dict whose keys are slot names.
    We return the set of slide_ids that own at least one of the missing slots.
    """
    missing_set = set(missing_slots)
    failed_ids: set[str] = set()
    for slide in slides:
        slide_slots = set(slide.get("slots", {}).keys())
        if slide_slots & missing_set:
            failed_ids.add(slide["slide_id"])
    return failed_ids


def _build_per_slide_fix_prompt(
    slide_id: str,
    fix_prompt: str,
) -> str:
    """Extract fix_prompt lines relevant to a specific slide_id.

    The full ``fix_prompt`` from semantic_validator contains lines like:
        - [slide_003] 'chart_renderer' 슬롯 누락.
          지시사항: ...
          Reference Component의 ...

    We keep the header/footer of the prompt and only the slot entries
    that reference the given slide_id, so the generator focuses on its
    own missing slots.
    """
    if not fix_prompt:
        return ""

    lines = fix_prompt.split("\n")
    header_lines: list[str] = []
    slot_entries: list[str] = []
    footer_lines: list[str] = []

    # Parse the fix_prompt structure:
    # - Everything before "[누락된 슬롯 목록]" is header
    # - Slot entries start with "- [slide_xxx]"
    #   and continuation lines are indented with "  "
    # - Everything after "[원칙]" is footer
    section = "header"
    current_entry: list[str] = []

    for line in lines:
        if "[누락된 슬롯 목록]" in line:
            header_lines.append(line)
            section = "slots"
            continue
        if "[원칙]" in line:
            # Flush any pending entry
            if current_entry:
                entry_text = "\n".join(current_entry)
                if f"[{slide_id}]" in entry_text:
                    slot_entries.append(entry_text)
                current_entry = []
            section = "footer"
            footer_lines.append(line)
            continue

        if section == "header":
            header_lines.append(line)
        elif section == "footer":
            footer_lines.append(line)
        elif section == "slots":
            if line.startswith("- ["):
                # New slot entry — flush previous
                if current_entry:
                    entry_text = "\n".join(current_entry)
                    if f"[{slide_id}]" in entry_text:
                        slot_entries.append(entry_text)
                current_entry = [line]
            elif line.startswith("  ") and current_entry:
                # Continuation of current entry
                current_entry.append(line)
            elif not line.strip():
                # Blank line — may separate entries
                if current_entry:
                    current_entry.append(line)
            else:
                header_lines.append(line)

    # Flush last entry
    if current_entry:
        entry_text = "\n".join(current_entry)
        if f"[{slide_id}]" in entry_text:
            slot_entries.append(entry_text)

    if not slot_entries:
        # Fallback: return the full prompt if parsing didn't isolate entries
        return fix_prompt

    return "\n".join(header_lines + slot_entries + footer_lines)


def slide_dispatcher(state: PPTState) -> Command:
    """Dispatch slide generation tasks in parallel via Command + Send.

    On semantic validation retries, only dispatches slides that have
    failing slots — previously correct slides keep their generated code.
    """
    slides = state["slide_spec"]["ppt_state"]["presentation"]["slides"]
    reference_components = state["reference_components"]

    validation = state.get("validation_result", {})
    fix_prompt = validation.get("fix_prompt", "") or ""
    missing_slots = validation.get("missing_slots", [])
    is_semantic_retry = (
        validation.get("layer") == "semantic"
        and validation.get("status") == "fail"
        and missing_slots
    )

    if state["mode"] == "edit" and state["target_slide_id"]:
        # Edit mode: only regenerate target slide
        slides = [s for s in slides if s["slide_id"] == state["target_slide_id"]]

    # On semantic retry, narrow dispatch to only slides with failed slots
    if is_semantic_retry:
        failed_ids = _find_failed_slide_ids(slides, missing_slots)
        # Safety: if mapping found no slides (shouldn't happen), fall back to all
        if failed_ids:
            slides = [s for s in slides if s["slide_id"] in failed_ids]

    sends = []
    for slide in slides:
        slide_type = slide["type"]
        # Give each slide only its own relevant fix instructions
        slide_fix = (
            _build_per_slide_fix_prompt(slide["slide_id"], fix_prompt)
            if is_semantic_retry
            else fix_prompt
        )
        sends.append(
            Send(
                "slide_generator",
                {
                    "slide_spec": state["slide_spec"],
                    "slide": slide,
                    "reference_component": reference_components.get(slide_type, ""),
                    "generated_code": "",
                    "fix_prompt": slide_fix,
                },
            )
        )

    # Command(goto=list[Send]) fans out to slide_generator instances
    return Command(goto=sends)
