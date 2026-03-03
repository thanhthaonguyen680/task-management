#!/usr/bin/env python3
"""Patch: dùng st.data_editor cho checklist — inline checkbox + delete, mobile safe."""
import ast, sys, re

c = open('app.py', encoding='utf-8').read()

# ─────────────────────────────────────────────────────────────────────────────
# 1. Thay _fragment_checklist — dùng st.data_editor
# ─────────────────────────────────────────────────────────────────────────────
FRAG_CL_START = '@st.fragment\ndef _fragment_checklist(key_prefix: str):'
FRAG_CL_END   = '\n\n\n@st.fragment\ndef _fragment_cong_viec_con('
i_s = c.find(FRAG_CL_START)
i_e = c.find(FRAG_CL_END, i_s)
assert i_s > 0 and i_e > 0, "Cannot find _fragment_checklist"

NEW_CL = '''@st.fragment
def _fragment_checklist(key_prefix: str):
    import pandas as pd
    cl_key   = f"{key_prefix}_checklist"
    cl_inp_v = f"{key_prefix}_cl_inp_v"
    if cl_key   not in st.session_state: st.session_state[cl_key]   = []
    if cl_inp_v not in st.session_state: st.session_state[cl_inp_v] = 0

    st.markdown(_FRAGMENT_CSS, unsafe_allow_html=True)
    st.markdown("**☑️ Checklist**")

    items = st.session_state[cl_key]

    if items:
        df = pd.DataFrame([
            {"✓": it.get("done", False), "Nội dung": it.get("text", "")}
            for it in items
        ])
        edited = st.data_editor(
            df,
            column_config={
                "✓":       st.column_config.CheckboxColumn("✓",      width="small"),
                "Nội dung": st.column_config.TextColumn("Nội dung",  width="large", disabled=True),
            },
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key=f"{key_prefix}_cl_editor",
        )
        # Sync lại session state
        new_items = []
        for _, row in edited.iterrows():
            text = str(row["Nội dung"]).strip()
            if text:
                new_items.append({"text": text, "done": bool(row["✓"])})
        if new_items != items:
            st.session_state[cl_key] = new_items
            st.rerun()

    # Form thêm mục mới
    col_inp, col_btn = st.columns([5, 2])
    with col_inp:
        moi = st.text_input(
            "", placeholder="Nhập tên checklist...",
            key=f"{key_prefix}_cl_inp_{st.session_state[cl_inp_v]}",
            label_visibility="collapsed",
        )
    with col_btn:
        if st.button("＋ Thêm", key=f"{key_prefix}_cl_add", use_container_width=True):
            val = st.session_state.get(
                f"{key_prefix}_cl_inp_{st.session_state[cl_inp_v]}", "").strip()
            if val:
                st.session_state[cl_key].append({"text": val, "done": False})
                st.session_state[cl_inp_v] += 1
                st.rerun()
'''

c = c[:i_s] + NEW_CL + c[i_e:]
print(f"[1] _fragment_checklist replaced (data_editor)")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Thay _fragment_cong_viec_con — CVC card + nút xóa inline dùng data_editor  
# ─────────────────────────────────────────────────────────────────────────────
FRAG_CVC_START = '@st.fragment\ndef _fragment_cong_viec_con(key_prefix: str, ds_nhan_vien: list):'
ADMIN_MARKER   = '\n\n\n# ============================================================\n# GIAO DIỆN ADMIN'
i_s2 = c.find(FRAG_CVC_START)
i_e2 = c.find(ADMIN_MARKER, i_s2)
assert i_s2 > 0 and i_e2 > 0, "Cannot find _fragment_cong_viec_con"

NEW_CVC = '''@st.fragment
def _fragment_cong_viec_con(key_prefix: str, ds_nhan_vien: list):
    import pandas as pd
    cv_key   = f"{key_prefix}_cong_viec_con"
    cv_inp_v = f"{key_prefix}_cv_inp_v"
    if cv_key   not in st.session_state: st.session_state[cv_key]   = []
    if cv_inp_v not in st.session_state: st.session_state[cv_inp_v] = 0

    st.markdown(_FRAGMENT_CSS, unsafe_allow_html=True)
    st.markdown("**📋 Công Việc Con**")

    items = st.session_state[cv_key]

    if items:
        df = pd.DataFrame([
            {
                "✓": bool(cv.get("done", False)),
                "Tên việc": cv.get("ten", ""),
                "Nhân viên": cv.get("nguoi", ""),
                "Deadline": cv.get("deadline", ""),
            }
            for cv in items
        ])
        edited = st.data_editor(
            df,
            column_config={
                "✓":         st.column_config.CheckboxColumn("✓",          width="small"),
                "Tên việc":  st.column_config.TextColumn("Tên việc",       width="medium", disabled=True),
                "Nhân viên": st.column_config.TextColumn("Nhân viên",      width="small",  disabled=True),
                "Deadline":  st.column_config.TextColumn("Deadline",       width="small",  disabled=True),
            },
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key=f"{key_prefix}_cv_editor",
        )
        new_items = []
        for _, row in edited.iterrows():
            ten = str(row["Tên việc"]).strip()
            if ten:
                new_items.append({
                    "ten":      ten,
                    "nguoi":    str(row["Nhân viên"]),
                    "deadline": str(row["Deadline"]),
                    "done":     bool(row["✓"]),
                })
        if new_items != items:
            st.session_state[cv_key] = new_items
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

c = c[:i_s2] + NEW_CVC + c[i_e2:]
print("[2] _fragment_cong_viec_con replaced (data_editor)")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Thay checklist loop trong _fragment_chi_tiet_task — dùng data_editor
# ─────────────────────────────────────────────────────────────────────────────
OLD_CHI_TIET_CL = '''    da_thay_doi = False
    _cl_xoa = None
    for i, item in enumerate(checklist):
        if isinstance(item, str):
            item = {"text": item, "done": False}
            checklist[i] = item
        hien_tai = bool(item.get("done", False))
        # Full-width checkbox — không dùng columns tránh wrap trên mobile
        moi = st.checkbox(
            label=item.get("text", f"Mục {i+1}"),
            value=hien_tai,
            key=f"cl_{task_id}_{i}",
        )
        if st.button("🗑️ Xóa", key=f"cl_del_{task_id}_{i}",
                     use_container_width=False):
            _cl_xoa = i
        if moi != hien_tai:
            checklist[i]["done"] = moi
            da_thay_doi = True
    if _cl_xoa is not None:
        checklist.pop(_cl_xoa)
        st.session_state[_cl_key] = checklist
        cap_nhat_checklist(task_id, checklist)
    elif da_thay_doi:
        st.session_state[_cl_key] = checklist
        cap_nhat_checklist(task_id, checklist)

    # Form thêm checklist
    _cl_add_cnt = st.session_state.get(f"cl_add_cnt_{task_id}", 0)
    cl_moi = st.text_input(
        "Thêm mục", placeholder="Nhập mục checklist rồi bấm ➕...",
        key=f"cl_inp_{task_id}_{_cl_add_cnt}", label_visibility="collapsed",
    )
    if st.button("➕ Thêm checklist", key=f"cl_add_{task_id}", use_container_width=True):
        if cl_moi.strip():
            checklist.append({"text": cl_moi.strip(), "done": False})
            st.session_state[_cl_key] = checklist
            st.session_state[f"cl_add_cnt_{task_id}"] = _cl_add_cnt + 1
            cap_nhat_checklist(task_id, checklist)'''

NEW_CHI_TIET_CL = '''    import pandas as pd as _pd
    _cl_df = _pd.DataFrame([
        {"✓": bool(it.get("done", False)) if isinstance(it, dict) else False,
         "Nội dung": it.get("text", it) if isinstance(it, dict) else str(it)}
        for it in checklist
    ])
    _cl_edited = st.data_editor(
        _cl_df,
        column_config={
            "✓":       st.column_config.CheckboxColumn("✓",       width="small"),
            "Nội dung": st.column_config.TextColumn("Nội dung",  width="large", disabled=True),
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=f"cl_editor_{task_id}",
    )
    _new_cl = []
    for _, _row in _cl_edited.iterrows():
        _txt = str(_row["Nội dung"]).strip()
        if _txt:
            _new_cl.append({"text": _txt, "done": bool(_row["✓"])})
    if _new_cl != checklist:
        st.session_state[_cl_key] = _new_cl
        cap_nhat_checklist(task_id, _new_cl)

    # Form thêm checklist
    _cl_add_cnt = st.session_state.get(f"cl_add_cnt_{task_id}", 0)
    _col_ci, _col_cb = st.columns([5, 2])
    with _col_ci:
        cl_moi = st.text_input(
            "", placeholder="Nhập mục checklist...",
            key=f"cl_inp_{task_id}_{_cl_add_cnt}", label_visibility="collapsed",
        )
    with _col_cb:
        if st.button("＋ Thêm", key=f"cl_add_{task_id}", use_container_width=True):
            if cl_moi.strip():
                _new_cl2 = st.session_state.get(_cl_key, []) + [{"text": cl_moi.strip(), "done": False}]
                st.session_state[_cl_key] = _new_cl2
                st.session_state[f"cl_add_cnt_{task_id}"] = _cl_add_cnt + 1
                cap_nhat_checklist(task_id, _new_cl2)'''

# Fix import alias typo
NEW_CHI_TIET_CL = NEW_CHI_TIET_CL.replace('import pandas as pd as _pd', 'import pandas as _pd')

if OLD_CHI_TIET_CL in c:
    c = c.replace(OLD_CHI_TIET_CL, NEW_CHI_TIET_CL, 1)
    print("[3] checklist in _fragment_chi_tiet_task replaced")
else:
    print("[3] WARN: checklist block in _fragment_chi_tiet_task NOT found — skipping")

# ─────────────────────────────────────────────────────────────────────────────
# 4. Thay CVC loop trong _fragment_chi_tiet_task — dùng data_editor
# ─────────────────────────────────────────────────────────────────────────────
OLD_CHI_TIET_CV = '''    cv_changed = False
    _cv_xoa = None
    for j, cv in enumerate(ds_cv_con):
        if not isinstance(cv, dict):
            continue
        ten_cv  = cv.get("ten",       cv.get("Tên",       f"Việc {j+1}"))
        nv_cv   = cv.get("nhan_vien", cv.get("Nhân Viên", ""))
        dl_cv   = cv.get("deadline",  cv.get("Deadline",  ""))
        done_cv = bool(cv.get("done", False))

        # Full-width — không dùng columns tránh wrap trên mobile
        da_xong = st.checkbox(
            label=f"{j+1}. {ten_cv}",
            value=done_cv,
            key=f"cv_{task_id}_{j}",
        )
        # Meta info line
        meta_txt = []
        if nv_cv: meta_txt.append(f"👤 {nv_cv}")
        if dl_cv: meta_txt.append(f"📅 {dl_cv}")
        if done_cv: meta_txt.append("✅ Đã xong")
        if meta_txt:
            st.caption("  │  ".join(meta_txt))
        if da_xong != done_cv:
            ds_cv_con[j]["done"] = da_xong
            cv_changed = True
        if st.button("🗑️ Xóa", key=f"cv_del_{task_id}_{j}",
                     use_container_width=False):
            _cv_xoa = j'''

NEW_CHI_TIET_CV = '''    import pandas as _pd2
    _cv_df = _pd2.DataFrame([
        {
            "✓": bool(cv.get("done", False)) if isinstance(cv, dict) else False,
            "Tên việc":  cv.get("ten", cv.get("Tên", "")) if isinstance(cv, dict) else "",
            "Nhân viên": cv.get("nhan_vien", cv.get("Nhân Viên", "")) if isinstance(cv, dict) else "",
            "Deadline":  cv.get("deadline", cv.get("Deadline", "")) if isinstance(cv, dict) else "",
        }
        for cv in ds_cv_con if isinstance(cv, dict)
    ])
    _cv_edited = st.data_editor(
        _cv_df,
        column_config={
            "✓":         st.column_config.CheckboxColumn("✓",         width="small"),
            "Tên việc":  st.column_config.TextColumn("Tên việc",      width="medium", disabled=True),
            "Nhân viên": st.column_config.TextColumn("Nhân viên",     width="small",  disabled=True),
            "Deadline":  st.column_config.TextColumn("Deadline",      width="small",  disabled=True),
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=f"cv_editor_{task_id}",
    )
    _new_cv = []
    cv_changed = False
    _cv_xoa = None  # not used but keep for next block
    for _, _row in _cv_edited.iterrows():
        _ten = str(_row["Tên việc"]).strip()
        if _ten:
            _new_cv.append({
                "ten": _ten,
                "nhan_vien": str(_row["Nhân viên"]),
                "deadline":  str(_row["Deadline"]),
                "done": bool(_row["✓"]),
            })
    if _new_cv != ds_cv_con:
        cv_changed = True'''

if OLD_CHI_TIET_CV in c:
    c = c.replace(OLD_CHI_TIET_CV, NEW_CHI_TIET_CV, 1)
    print("[4] CVC loop in _fragment_chi_tiet_task replaced")
else:
    print("[4] WARN: CVC loop NOT found — skipping")

# ─────────────────────────────────────────────────────────────────────────────
# 5. Fix block sau CVC loop (cv_changed / _cv_xoa handling) trong chi_tiet
# ─────────────────────────────────────────────────────────────────────────────
OLD_CV_AFTER = '''    # Form thêm công việc con
    _ds_nv_cv = lay_danh_sach_nhan_vien()
    _cv_add_cnt = st.session_state.get(f"cv_add_cnt_{task_id}", 0)
    st.markdown("---")'''

# Tìm và chèn handling cho _new_cv và _cv_xoa trước Form thêm
if OLD_CV_AFTER in c:
    INSERT_BEFORE = '''    # Lưu thay đổi CVC
    if cv_changed:
        # Tìm _cv_xoa
        pass
    if _new_cv != ds_cv_con:
        st.session_state[_cv_key] = _new_cv
        cap_nhat_cong_viec_con(task_id, _new_cv)
        st.rerun()

    # Form thêm công việc con
    _ds_nv_cv = lay_danh_sach_nhan_vien()
    _cv_add_cnt = st.session_state.get(f"cv_add_cnt_{task_id}", 0)
    st.markdown("---")'''
    c = c.replace(OLD_CV_AFTER, INSERT_BEFORE, 1)
    print("[5] cv_changed save block inserted")
else:
    print("[5] WARN: cv save block not found")

# ─────────────────────────────────────────────────────────────────────────────
# Save
# ─────────────────────────────────────────────────────────────────────────────
open('app.py', 'w', encoding='utf-8').write(c)
try:
    ast.parse(c)
    print("Syntax: OK")
except SyntaxError as e:
    print(f"Syntax ERROR line {e.lineno}: {e.msg}")
    sys.exit(1)
