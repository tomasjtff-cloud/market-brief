"""Keeps the portfolio in the visitor's own browser (localStorage), with a JSON backup file to move or restore it.

Nothing personal is asked for and nothing is stored on the server: the app reads the saved book when the
Portfolio page opens, works on it in the session, and writes it back to the same browser after every change.
"""
from __future__ import annotations

import datetime as dt
import json

import streamlit as st

import portfolio as pf

STORAGE_KEY = "market_brief_portfolio_v1"

_JS = """
export default function(component) {
  const { data, setStateValue } = component;
  const KEY = "%s";
  const w = window;
  w.__mbStore = w.__mbStore || { sent: false, rev: -1 };
  let stored = null;
  try { stored = w.localStorage.getItem(KEY); } catch (e) { stored = "__unavailable__"; }
  if (!w.__mbStore.sent) {
    w.__mbStore.sent = true;
    setStateValue("stored", stored === null ? "" : stored);
  }
  if (data && typeof data.rev === "number" && data.rev > w.__mbStore.rev && typeof data.payload === "string") {
    try {
      if (data.payload === "__clear__") { w.localStorage.removeItem(KEY); } else { w.localStorage.setItem(KEY, data.payload); }
      w.__mbStore.rev = data.rev;
    } catch (e) { /* storage full or blocked: the backup file still works */ }
  }
}
""" % STORAGE_KEY


@st.cache_resource
def _component():
    return st.components.v2.component("mb_portfolio_store", js=_JS)


def sync() -> bool:
    """Mount the bridge. Returns True once the saved book (if any) has been loaded into the session.

    If the browser never answers (scripts or storage blocked), the page falls back to a session-only book after a
    couple of reruns, and then never writes to storage, so a late answer can't be overwritten by an empty book.
    """
    ss = st.session_state
    ss.setdefault("pf_rev", 0)
    payload = None
    if ss.get("pf_loaded") and ss.get("pf_dirty"):
        ss.pf_touched = True
        if ss.get("pf_source") == "storage":
            payload = "__clear__" if ss.get("pf_cleared") else json.dumps(ss.pf_book, separators=(",", ":"))
            ss.pf_rev += 1
        ss.pf_dirty = False
        ss.pf_cleared = False
    try:
        res = _component()(key="mb_store", data={"rev": ss.pf_rev if payload is not None else -1, "payload": payload},
                           on_stored_change=lambda: None)
        stored = getattr(res, "stored", None)
    except Exception:
        stored = None
    if stored is not None and (not ss.get("pf_loaded") or (ss.get("pf_source") == "fallback" and not ss.get("pf_touched"))):
        book = pf.empty_book()
        ss.pf_storage_ok = stored != "__unavailable__"
        if stored and stored != "__unavailable__":
            try:
                book, problems = pf.clean_book(json.loads(stored))
                ss.pf_problems = problems
            except (ValueError, TypeError):
                ss.pf_problems = ["saved data could not be read"]
        ss.pf_book = book
        ss.pf_loaded = True
        ss.pf_source = "storage" if ss.pf_storage_ok else "fallback"
    elif not ss.get("pf_loaded"):
        ss.pf_wait = ss.get("pf_wait", 0) + 1
        if ss.pf_wait >= 3 or ss.get("pf_force_fallback"):
            ss.pf_book, ss.pf_loaded, ss.pf_source, ss.pf_storage_ok = pf.empty_book(), True, "fallback", False
    return bool(ss.get("pf_loaded"))


def book() -> dict:
    return st.session_state.get("pf_book") or pf.empty_book()


def save(new_book: dict) -> None:
    new_book["updated"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    st.session_state.pf_book = new_book
    st.session_state.pf_dirty = True


def clear() -> None:
    st.session_state.pf_book = pf.empty_book()
    st.session_state.pf_dirty = True
    st.session_state.pf_cleared = True


def backup_bytes() -> bytes:
    return json.dumps(book(), indent=2).encode()


def restore(raw: bytes) -> list[str]:
    data = json.loads(raw.decode("utf-8"))
    clean, problems = pf.clean_book(data)
    save(clean)
    return problems
