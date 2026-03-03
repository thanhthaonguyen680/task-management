#!/usr/bin/env python3
"""Patch: bỏ data_editor, dùng container(border=True) per item — đảm bảo mobile."""
import ast, sys

c = open('app.py', encoding='utf-8').read()

# ── 1. CSS ───────────────────────────────────────────────────────────────────
CSS_START = '_FRAGMENT_CSS = """\n<style>'
CSS_END   = '</style>\n"""'
cs = c.find(CSS_START)
ce = c.find(CSS_END, cs) + len(CSS_END)
assert cs > 0

NEW_CSS = '''_FRAGMENT_CSS = """
<style>
/* Card viền bo góc cho mỗi item */
div[data-testid="stVerticalBlockBorderWrapper"] > div > div {
    border-radius: 12px !important;
}
/* Nút xóa: ghost nhỏ màu đỏ nhạt */
div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stButton"] > button {
    background: transparent !important;
    border: none !important;
    color: #cbd5e1 !important;
    font-size: 0.75rem !important;
    padding: 0 4px 2px 0 !important;
    box-shadow: none !important;
    min-height: 0 !important;
    line-height: 1.2 !important;
    margin-top: -6px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stButton"] > button:hover {
    color: #ef4444 !important;
    background: #fff1f1 !important;
    border-radius: 6px !important;
}
/* Checkbox done: gạch ngang */
div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stCheckbox"]:has(input:checked) label {
    text-decoration: line-through;
    color: #9ca3af;
    opacity: 0.8;
}
/* Caption màu xanh lá khi hoàn thành */
.done-caption { color: #16a34a !important; font-size: 0.78rem; margin-top: -4px; }
</style>
"""'''

c = c[:cs] + NEW_CSS + c[ce:]
print("[1] CSS OK")

# ── 2. _fragment_checklist ───────────────────────────────────────────────────
CL_START = '@st.fragment\ndef _fragment_checklist(key_prefix: str):'
CL_END   = '\n\n\n@st.fragment\ndef _fragment_cong_viec_con('
i1 = c.find(CL_START)
i2 = c.find(CL_END, i1)
assert i1 > 0 and i2 > 0

NEW_CL = '''@st.fragment
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
        done_val = bool(item.get("done", False))
        with st.container(border=True):
            new_done = st.checkbox(
                item["text"],
                value=done_val,
                key=f"{key_prefix}_ck_{i}",
            )
            if done_val:
                st.markdown("<span class='done-caption'>✅ Hoàn thành</span>",
                            unsafe_allow_html=True)
            if st.button("🗑️ Xóa mục này", key=f"{key_prefix}_cl_del_{i}"):
                _xoa = i
            if new_done != done_val:
                st.session_state[cl_key][i]["done"] = new_done
                st.rerun()

    if _xoa is not None:
        st.session_state[cl_key].pop(_xoa)
        st.rerun()

    col_i, col_b = st.columns([5, 2])
    with col_i:
        moi = st.text_input(
            "", placeholder="Nhập tên checklist...",
            key=f"{key_prefix}_cl_inp_{st.session_state[cl_inp_v]}",
            label_visibility="collapsed",
        )
    with col_b:
        if st.button("＋ Thêm", key=f"{key_prefix}_cl_add",
                     use_container_width=True):
            val = st.session_state.get(
                f"{key_prefix}_cl_inp_{st.session_state[cl_inp_v]}", "").strip()
            if val:
                st.session_state[cl_key].append({"text": val, "done": False})
                st.session_state[cl_inp_v] += 1
                st.rerun()
'''

c = c[:i1] + NEW_CL + c[i2:]
print("[2] _fragment_checklist OK")

# ── 3. _fragment_cong_viec_con ───────────────────────────────────────────────
CVC_START = '@st.fragment\ndef _fragment_cong_viec_con(key_prefix: str, ds_nhan_vien: list):'
ADMIN_MK  = '\n\n\n# ============================================================\n# GIAO DIỆN ADMIN'
i3 = c.find(CVC_START)
i4 = c.find(ADMIN_MK, i3)
assert i3 > 0 and i4 > 0

NEW_CVC = '''@st.fragment
def _fragment_cong_viec_con(key_prefix: str, ds_nhan_vien: list):
    cv_key   = f"{key_prefix}_cong_viec_con"
    cv_inp_v = f"{key_prefix}_cv_inp_v"
    if cv_key   not in st.session_state: st.session_state[cv_key]   = []
    if cv_inp_v not in st.session_state: st.session_state[cv_inp_v] = 0

    st.markdown(_FRAGMENT_CSS, unsafe_allow_html=True)
    st.markdown("**📋 Công Việc Con**")

    _xoa = None
    for i, cv in enumerate(st.session_state[cv_key]):
        done_val = bool(cv.get("done", False))
        with st.container(border=True):
            st.markdown(f"**{i+1}. {cv['ten']}**")
            meta = []
            if cv.get("nguoi"): meta.append(f"👤 {cv['nguoi']}")
            if cv.get("deadline"): meta.append(f"📅 {cv['deadline']}")
            if meta:
                st.caption("  │  ".join(meta))
            if done_val:
                st.markdown("<span class='done-caption'>✅ Hoàn thành</span>",
                            unsafe_allow_html=True)
            if st.button("🗑️ Xóa mục này", key=f"{key_prefix}_cv_del_{i}"):
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
        cv_nv = st.session_state.get(
            f"{key_prefix}_cv_nv_{st.session_state[cv_inp_v]}", "-- Chọn nhân viên --")
        cv_dl = st.session_state.get(f"{key_prefix}_cv_dl", "")
        if ten_val:
            st.session_state[cv_key].append({
                "ten":      ten_val,
                "nguoi":    cv_nv if cv_nv != "-- Chọn nhân viên --" else "",
                "deadline": str(cv_dl),
                "done":     False,
            })
            st.session_state[cv_inp_v] += 1
            st.rerun()
'''

c = c[:i3] + NEW_CVC + c[i4:]
print("[3] _fragment_cong_viec_con OK")

# ── 4. _fragment_chi_tiet_task: thay checklist + CVC bằng container approach ──
# Checklist loop
OLD_CHI_CL = '''    import pandas as _pd
    # Chuẩn hoá checklist
    _cl_list = [
        ({"text": it, "done": False} if isinstance(it, str) else it)
        for it in checklist
    ]
    _cl_df = _pd.DataFrame([
        {"✓": bool(it.get("done", False)), "Nội dung": it.get("text", ""),
         "Trạng thái": "✅ Hoàn thành" if (it.get("done") if isinstance(it, dict) else False) else ""}
        for it in _cl_list
    ])
    _cl_edited = st.data_editor(
        _cl_df,
        column_config={
            "✓":          st.column_config.CheckboxColumn("✓",          width="small"),
            "Nội dung":   st.column_config.TextColumn("Nội dung",       width="large",  disabled=True),
            "Trạng thái": st.column_config.TextColumn("Trạng thái",     width="medium", disabled=True),
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=f"cl_editor_{task_id}",
    )
    _new_cl = [
        {"text": str(r["Nội dung"]).strip(), "done": bool(r["✓"])}
        for _, r in _cl_edited.iterrows()
        if str(r["Nội dung"]).strip()
    ]
    if _new_cl != _cl_list:
        st.session_state[_cl_key] = _new_cl
        cap_nhat_checklist(task_id, _new_cl)

    # Form thêm checklist
    _cl_add_cnt = st.session_state.get(f"cl_add_cnt_{task_id}", 0)
    _cc1, _cc2 = st.columns([5, 2])
    with _cc1:
        cl_moi = st.text_input(
            "", placeholder="Nhập mục checklist...",
            key=f"cl_inp_{task_id}_{_cl_add_cnt}", label_visibility="collapsed",
        )
    with _cc2:
        if st.button("＋ Thêm", key=f"cl_add_{task_id}", use_container_width=True):
            if cl_moi.strip():
                _cur = st.session_state.get(_cl_key, []) + [{"text": cl_moi.strip(), "done": False}]
                st.session_state[_cl_key] = _cur
                st.session_state[f"cl_add_cnt_{task_id}"] = _cl_add_cnt + 1
                cap_nhat_checklist(task_id, _cur)'''

NEW_CHI_CL = '''    st.markdown(_FRAGMENT_CSS, unsafe_allow_html=True)
    _cl_xoa2 = None
    _cl_changed = False
    for _ci, _cit in enumerate(checklist):
        if isinstance(_cit, str):
            _cit = {"text": _cit, "done": False}
            checklist[_ci] = _cit
        _done_v = bool(_cit.get("done", False))
        with st.container(border=True):
            _nd = st.checkbox(
                _cit.get("text", f"Mục {_ci+1}"),
                value=_done_v,
                key=f"cl_{task_id}_{_ci}",
            )
            if _done_v:
                st.markdown("<span class='done-caption'>✅ Hoàn thành</span>",
                            unsafe_allow_html=True)
            if st.button("🗑️ Xóa mục này", key=f"cl_del_{task_id}_{_ci}"):
                _cl_xoa2 = _ci
            if _nd != _done_v:
                checklist[_ci]["done"] = _nd
                _cl_changed = True
    if _cl_xoa2 is not None:
        checklist.pop(_cl_xoa2)
        st.session_state[_cl_key] = checklist
        cap_nhat_checklist(task_id, checklist)
    elif _cl_changed:
        st.session_state[_cl_key] = checklist
        cap_nhat_checklist(task_id, checklist)

    # Form thêm checklist
    _cl_add_cnt = st.session_state.get(f"cl_add_cnt_{task_id}", 0)
    _cc1, _cc2 = st.columns([5, 2])
    with _cc1:
        cl_moi = st.text_input(
            "", placeholder="Nhập mục checklist...",
            key=f"cl_inp_{task_id}_{_cl_add_cnt}", label_visibility="collapsed",
        )
    with _cc2:
        if st.button("＋ Thêm", key=f"cl_add_{task_id}", use_container_width=True):
            if cl_moi.strip():
                _cur = st.session_state.get(_cl_key, []) + [{"text": cl_moi.strip(), "done": False}]
                st.session_state[_cl_key] = _cur
                st.session_state[f"cl_add_cnt_{task_id}"] = _cl_add_cnt + 1
                cap_nhat_checklist(task_id, _cur)'''

if OLD_CHI_CL in c:
    c = c.replace(OLD_CHI_CL, NEW_CHI_CL, 1)
    print("[4] checklist in chi_tiet OK")
else:
    print("[4] WARN checklist chi_tiet not found")

# CVC loop trong chi_tiet
OLD_CHI_CV_DF = '''    _df_cv2 = _pd.DataFrame([
        {
            "✓":          bool(cv.get("done", False)),
            "Tên việc":   cv.get("ten", f"Việc {j+1}"),
            "Nhân viên":  cv.get("nhan_vien", ""),
            "Deadline":   cv.get("deadline", ""),
            "Trạng thái": "✅ Hoàn thành" if cv.get("done") else "🔄 Đang làm",
        }
        for j, cv in enumerate(ds_cv_con) if isinstance(cv, dict)
    ])
    _ed_cv2 = st.data_editor(
        _df_cv2,
        column_config={
            "✓":          st.column_config.CheckboxColumn("✓",          width="small"),
            "Tên việc":   st.column_config.TextColumn("Tên việc",       width="medium", disabled=True),
            "Nhân viên":  st.column_config.TextColumn("Nhân viên",      width="small",  disabled=True),
            "Deadline":   st.column_config.TextColumn("Deadline",       width="small",  disabled=True),
            "Trạng thái": st.column_config.TextColumn("Trạng thái",     width="medium", disabled=True),
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=f"cv_editor_{task_id}",
    )
    _new_cv2 = [
        {
            "ten":       str(r["Tên việc"]).strip(),
            "nhan_vien": str(r["Nhân viên"]),
            "deadline":  str(r["Deadline"]),
            "done":      bool(r["✓"]),
        }
        for _, r in _ed_cv2.iterrows()
        if str(r["Tên việc"]).strip()
    ]
    _cv_changed2 = _new_cv2 != ds_cv_con
    _cv_xoa = None   # không còn dùng nhưng giữ biến cho block phía dưới'''

NEW_CHI_CV_DF = '''    _cv_xoa2 = None
    _cv_ch2  = False
    for _cvi, cv in enumerate(ds_cv_con):
        if not isinstance(cv, dict): continue
        _tcv  = cv.get("ten",       cv.get("Tên",       f"Việc {_cvi+1}"))
        _nvcv = cv.get("nhan_vien", cv.get("Nhân Viên", ""))
        _dlcv = cv.get("deadline",  cv.get("Deadline",  ""))
        _dcv  = bool(cv.get("done", False))
        with st.container(border=True):
            _nxong = st.checkbox(
                f"{_cvi+1}. {_tcv}", value=_dcv, key=f"cv_{task_id}_{_cvi}"
            )
            _meta2 = []
            if _nvcv: _meta2.append(f"👤 {_nvcv}")
            if _dlcv: _meta2.append(f"📅 {_dlcv}")
            if _meta2: st.caption("  │  ".join(_meta2))
            if _dcv:
                st.markdown("<span class='done-caption'>✅ Hoàn thành</span>",
                            unsafe_allow_html=True)
            if st.button("🗑️ Xóa mục này", key=f"cv_del_{task_id}_{_cvi}"):
                _cv_xoa2 = _cvi
            if _nxong != _dcv:
                ds_cv_con[_cvi]["done"] = _nxong
                _cv_ch2 = True
    _cv_changed2 = _cv_ch2
    _cv_xoa = _cv_xoa2'''

if OLD_CHI_CV_DF in c:
    c = c.replace(OLD_CHI_CV_DF, NEW_CHI_CV_DF, 1)
    print("[5] CVC in chi_tiet OK")
else:
    print("[5] WARN CVC chi_tiet not found")

# Fix block save CVC (if _cv_changed2)
OLD_SAVE = '''    if _cv_changed2:
        st.session_state[_cv_key] = _new_cv2
        _sh = lay_sheet()
        _o  = _sh.find(str(task_id), in_column=1)
        if _o:
            _sh.update_cell(_o.row, 14, json.dumps(_new_cv2, ensure_ascii=False))
            lay_danh_sach_cong_viec.clear()'''

NEW_SAVE = '''    if _cv_xoa2 is not None:
        ds_cv_con.pop(_cv_xoa2)
        st.session_state[_cv_key] = ds_cv_con
        _sh = lay_sheet()
        _o  = _sh.find(str(task_id), in_column=1)
        if _o:
            _sh.update_cell(_o.row, 14, json.dumps(ds_cv_con, ensure_ascii=False))
            lay_danh_sach_cong_viec.clear()
    elif _cv_changed2:
        st.session_state[_cv_key] = ds_cv_con
        _sh = lay_sheet()
        _o  = _sh.find(str(task_id), in_column=1)
        if _o:
            _sh.update_cell(_o.row, 14, json.dumps(ds_cv_con, ensure_ascii=False))
            lay_danh_sach_cong_viec.clear()'''

if OLD_SAVE in c:
    c = c.replace(OLD_SAVE, NEW_SAVE, 1)
    print("[6] save CVC OK")
else:
    print("[6] WARN save CVC not found")

open('app.py', 'w', encoding='utf-8').write(c)
try:
    ast.parse(c)
    print("Syntax: OK ✓")
except SyntaxError as e:
    print(f"Syntax ERROR line {e.lineno}: {e.msg}")
    sys.exit(1)
