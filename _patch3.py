#!/usr/bin/env python3
"""Final patch: items hoàn toàn không dùng st.columns — checkbox left, delete inline right."""
import ast, sys

c = open('app.py', encoding='utf-8').read()

# ─────────────────────────────────────────────────────────────────────────────
# 1. Replace _FRAGMENT_CSS with clean version
# ─────────────────────────────────────────────────────────────────────────────
start = '_FRAGMENT_CSS = """\n<style>'
end   = '</style>\n"""'
i_s = c.find(start)
i_e = c.find(end, i_s) + len(end)
assert i_s > 0

NEW_CSS = '''_FRAGMENT_CSS = """
<style>
/* CVC card */
.cvc-card {
    border: 1px solid #e5e7eb; border-radius: 10px;
    padding: 9px 12px 7px 12px; background: #fff;
    margin-bottom: 6px; word-break: break-word;
}
.cvc-title { font-size: 0.93rem; font-weight: 600; color: #1a1a1a; margin-bottom: 2px; }
.cvc-meta  { font-size: 0.79rem; color: #6b7280; display: flex; align-items: center;
             gap: 8px; flex-wrap: wrap; margin-top: 2px; }
.cvc-av {
    display: inline-flex; align-items: center; justify-content: center;
    width: 20px; height: 20px; border-radius: 50%; flex-shrink: 0;
    background: #6c63ff; color: #fff; font-size: 0.6rem; font-weight: 700;
}
/* Checklist item */
.cl-item {
    display: flex; align-items: center; gap: 6px;
    border: 1px solid #e5e7eb; border-radius: 10px;
    padding: 7px 10px; background: #fff; margin-bottom: 5px;
    word-break: break-word;
}
.cl-item.done-item { background: #f9fafb; opacity: 0.75; }
.cl-item .cl-txt { flex: 1 1 0; min-width: 0; font-size: 0.93rem; color: #1a1a1a; }
.cl-item.done-item .cl-txt { text-decoration: line-through; color: #9ca3af; }
.cl-item .cl-chk { flex-shrink: 0; width: 16px; height: 16px; accent-color: #7c3aed; }
/* Checklist done via Streamlit checkbox */
div[data-testid="stCheckbox"]:has(:checked) label p {
    text-decoration: line-through !important; color: #9ca3af !important;
}
/* Delete button: small, ghost, below each item */
.del-row { margin: -2px 0 6px 0; }
.del-row button, div[data-testid="stButton"] .del-btn-st {
    background: transparent !important; border: none !important;
    color: #c4c4c4 !important; font-size: 0.75rem !important;
    padding: 0 4px !important; cursor: pointer;
    box-shadow: none !important;
}
</style>
"""'''

c = c[:i_s] + NEW_CSS + c[i_e:]
print(f"[1] CSS replaced at {i_s}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Replace _fragment_checklist body
# ─────────────────────────────────────────────────────────────────────────────
FRAG_CL_START = '@st.fragment\ndef _fragment_checklist(key_prefix: str):'
FRAG_CL_END   = '\n\n\n@st.fragment\ndef _fragment_cong_viec_con('
i_s2 = c.find(FRAG_CL_START)
i_e2 = c.find(FRAG_CL_END, i_s2)
assert i_s2 > 0 and i_e2 > 0

NEW_FRAG_CL = '''@st.fragment
def _fragment_checklist(key_prefix: str):
    cl_key   = f"{key_prefix}_checklist"
    cl_inp_v = f"{key_prefix}_cl_inp_v"
    if cl_key   not in st.session_state: st.session_state[cl_key]   = []
    if cl_inp_v not in st.session_state: st.session_state[cl_inp_v] = 0

    st.markdown(_FRAGMENT_CSS, unsafe_allow_html=True)
    st.markdown("**☑️ Checklist**")

    items = st.session_state[cl_key]
    _xoa  = None
    for i, item in enumerate(items):
        done_val = item.get("done", False)
        # Checkbox full-width — no columns, no overlap
        new_done = st.checkbox(
            f"{i+1}. {item['text']}",
            value=done_val,
            key=f"{key_prefix}_ck_{i}",
        )
        if new_done != done_val:
            st.session_state[cl_key][i]["done"] = new_done
            st.rerun()
        # Delete button on its own line, small
        if st.button(f"🗑️ Xóa mục {i+1}", key=f"{key_prefix}_cl_del_{i}",
                     use_container_width=False):
            _xoa = i

    if _xoa is not None:
        st.session_state[cl_key].pop(_xoa)
        st.rerun()

    st.text_input(
        "", placeholder="Nhập tên checklist...",
        key=f"{key_prefix}_cl_inp_{st.session_state[cl_inp_v]}",
        label_visibility="collapsed",
    )
    if st.button("＋ Thêm checklist", key=f"{key_prefix}_cl_add",
                 use_container_width=True):
        val = st.session_state.get(
            f"{key_prefix}_cl_inp_{st.session_state[cl_inp_v]}", "").strip()
        if val:
            st.session_state[cl_key].append({"text": val, "done": False})
            st.session_state[cl_inp_v] += 1
            st.rerun()
'''

c = c[:i_s2] + NEW_FRAG_CL + c[i_e2:]
print("[2] _fragment_checklist replaced")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Replace _fragment_cong_viec_con body
# ─────────────────────────────────────────────────────────────────────────────
FRAG_CVC_START = '@st.fragment\ndef _fragment_cong_viec_con(key_prefix: str, ds_nhan_vien: list):'
FRAG_CVC_END   = '\n\n\n# ============================================================\n# GIAO DIỆN ADMIN'
i_s3 = c.find(FRAG_CVC_START)
i_e3 = c.find(FRAG_CVC_END, i_s3)
assert i_s3 > 0 and i_e3 > 0

NEW_FRAG_CVC = '''@st.fragment
def _fragment_cong_viec_con(key_prefix: str, ds_nhan_vien: list):
    cv_key   = f"{key_prefix}_cong_viec_con"
    cv_inp_v = f"{key_prefix}_cv_inp_v"
    if cv_key   not in st.session_state: st.session_state[cv_key]   = []
    if cv_inp_v not in st.session_state: st.session_state[cv_inp_v] = 0

    st.markdown(_FRAGMENT_CSS, unsafe_allow_html=True)
    st.markdown("**📋 Công Việc Con**")

    _xoa = None
    for i, cv in enumerate(st.session_state[cv_key]):
        nguoi = cv.get("nguoi") or ""
        dl    = cv.get("deadline", "")
        if nguoi:
            initials = nguoi.strip().split()[-1][0].upper()
            av = f"<span class='cvc-av'>{initials}</span>"
        else:
            av = ""
        meta_parts = []
        if av or nguoi:
            meta_parts.append(f"{av}&nbsp;{nguoi}" if av else nguoi)
        if dl:
            meta_parts.append(f"📅&nbsp;{dl}")
        meta_html = (
            f"<div class='cvc-meta'>{'&nbsp;&nbsp;│&nbsp;&nbsp;'.join(meta_parts)}</div>"
            if meta_parts else ""
        )
        st.markdown(
            f"<div class='cvc-card'>"
            f"<div class='cvc-title'>{i+1}. {cv['ten']}</div>"
            f"{meta_html}"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button(f"🗑️ Xóa mục {i+1}", key=f"{key_prefix}_cv_del_{i}",
                     use_container_width=False):
            _xoa = i

    if _xoa is not None:
        st.session_state[cv_key].pop(_xoa)
        st.rerun()

    st.divider()
    st.text_input(
        "", placeholder="Tên công việc con...",
        key=f"{key_prefix}_cv_ten_{st.session_state[cv_inp_v]}",
        label_visibility="collapsed",
    )
    st.selectbox(
        "👤 Nhân viên",
        options=["-- Chọn nhân viên --"] + ds_nhan_vien,
        key=f"{key_prefix}_cv_nv_{st.session_state[cv_inp_v]}",
    )
    st.date_input("📅 Deadline", key=f"{key_prefix}_cv_dl")

    if st.button("＋ Thêm công việc con", key=f"{key_prefix}_cv_add",
                 use_container_width=True):
        ten_val = st.session_state.get(
            f"{key_prefix}_cv_ten_{st.session_state[cv_inp_v]}", "").strip()
        cv_nv  = st.session_state.get(
            f"{key_prefix}_cv_nv_{st.session_state[cv_inp_v]}", "-- Chọn nhân viên --")
        cv_dl  = st.session_state.get(f"{key_prefix}_cv_dl", "")
        if ten_val:
            st.session_state[cv_key].append({
                "ten": ten_val,
                "nguoi": cv_nv if cv_nv != "-- Chọn nhân viên --" else "",
                "deadline": str(cv_dl),
                "done": False,
            })
            st.session_state[cv_inp_v] += 1
            st.rerun()
'''

c = c[:i_s3] + NEW_FRAG_CVC + c[i_e3:]
print("[3] _fragment_cong_viec_con replaced")

# ─────────────────────────────────────────────────────────────────────────────
# Save & syntax check
# ─────────────────────────────────────────────────────────────────────────────
open('app.py', 'w', encoding='utf-8').write(c)
try:
    ast.parse(c)
    print("Syntax: OK")
except SyntaxError as e:
    print(f"Syntax ERROR: {e}")
    sys.exit(1)
