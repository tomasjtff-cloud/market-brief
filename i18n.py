"""English / Spanish interface. English strings are the keys; Spanish lives in i18n_es.py.

T("text") translates a UI string, T("text {x}", x=1) also fills placeholders.
D(date, "%b %d") formats a date with month and day names in the current language.
"""
from __future__ import annotations

import datetime as dt

import streamlit as st

from i18n_es import ES

LANGS = {"EN": "English", "ES": "Español"}


def lang() -> str:
    return st.session_state.get("lang_sel") or "EN"


def es() -> bool:
    return lang() == "ES"


def T(text: str, **kw) -> str:
    out = ES.get(text, text) if es() else text
    return out.format(**kw) if kw else out


_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def D(when: dt.date | dt.datetime | None, fmt: str) -> str:
    """strftime with Spanish month and day names when the interface is in Spanish."""
    if when is None:
        return ""
    if not es():
        return when.strftime(fmt)
    fmt = (fmt.replace("%B", _MESES[when.month - 1]).replace("%b", _MESES[when.month - 1][:3])
           .replace("%A", _DIAS[when.weekday()]).replace("%a", _DIAS[when.weekday()][:3]))
    if "%p" in fmt and isinstance(when, dt.datetime):  # 24-hour clock reads more naturally in Spanish
        fmt = fmt.replace("%-I:%M %p", "%H:%M").replace("%-I %p", "%H h")
    return when.strftime(fmt)


def choice(widget, label: str, options: list[str], key: str, default=None, multi: bool = False, **kw):
    """A segmented control / pills / radio whose labels follow the language while the app keeps the English value.

    The English value lives in st.session_state[key] (so code and links can set it); the widget itself uses a
    per-language key and is synced both ways.
    """
    labels = [T(o) for o in options]
    back = dict(zip(labels, options))
    wkey = f"{key}__w_{lang()}"
    if key not in st.session_state:
        st.session_state[key] = default
    canon = st.session_state[key]
    want = [T(v) for v in (canon or []) if v in options] if multi else (T(canon) if canon in options else None)
    if st.session_state.get(wkey) != want:
        st.session_state[wkey] = want

    def _sync():
        v = st.session_state.get(wkey)
        if multi:
            st.session_state[key] = [back[x] for x in (v or []) if x in back]
        elif v is not None:
            st.session_state[key] = back.get(v, st.session_state[key])

    if multi:
        widget(label, labels, key=wkey, on_change=_sync, selection_mode="multi", **kw)
    else:
        widget(label, labels, key=wkey, on_change=_sync, **kw)
    return st.session_state[key]
