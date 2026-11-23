"""微贷慧查 v1.2：两项可演示的模拟贷前核查能力。

公开演示仅使用虚构数据，不做真实授信、风险评级或违约预测。
"""
from __future__ import annotations

from copy import deepcopy

import streamlit as st

from report import build_docx
from rules import (
    DEMO_CASES, DOC_ITEMS, calculate_cashflow_scenario,
    evaluate, load_policy, result_to_text,
)

st.set_page_config(page_title="微贷慧查｜贷前调查辅助", page_icon="📋", layout="wide")
st.markdown("""<style>
.block-container {max-width:1080px;padding-top:1.35rem;padding-bottom:3.2rem}
h1,h2,h3 {color:#183a52;letter-spacing:-.025em}
h1 {font-size:2rem!important}
h2 {font-size:1.4rem!important}
h3 {font-size:1.14rem!important}
[data-testid="stMetric"] {background:#f5f8fb;border:1px solid #dfe8ef;border-radius:12px;padding:13px 16px}
[data-testid="stMetricValue"] {font-size:1.7rem}
.stButton button[kind="primary"],.stDownloadButton button[kind="primary"] {background:#16617b;border-color:#16617b;border-radius:8px}
[data-testid="stExpander"] {border:1px solid #e2e8ed;border-radius:9px}
.hero {background:linear-gradient(115deg,#16354c,#1a6572);border-radius:16px;padding:27px 31px;margin-bottom:14px;color:white}
.hero .eyebrow{font-size:.78rem;letter-spacing:.09em;opacity:.75;margin-bottom:8px}
.hero .name{font-size:2.1rem;font-weight:750;line-height:1.3}
.hero .sub{font-size:.98rem;margin-top:9px;opacity:.91}
.step {background:#f5f8fb;border:1px solid #e6edf2;border-radius:10px;padding:12px 16px;font-weight:600;color:#244559}
.micro-note {font-size:.88rem;color:#677d89}
</style>""", unsafe_allow_html=True)

st.markdown("""<div class="hero">
<div class="eyebrow">MICROLOAN REVIEW · DEMONSTRATION</div>
<div class="name">微贷慧查 <span style="font-size:1.25rem;font-weight:450">｜贷前核查辅助</span></div>
<div class="sub">少填表、先看问题：经营资料核对 × 偿债情景模拟</div>
</div>""", unsafe_allow_html=True)
st.caption("模拟参赛原型｜无AI大模型、无信贷审批决策｜公开网页仅可使用完全虚构的数据")

step1, step2, step3 = st.columns(3)
with step1:
    st.markdown('<div class="step">① 选择虚构案例</div>', unsafe_allow_html=True)
with step2:
    st.markdown('<div class="step">② 查看核查关注点</div>', unsafe_allow_html=True)
with step3:
    st.markdown('<div class="step">③ 模拟偿债情景与导出</div>', unsafe_allow_html=True)

st.subheader("① 选择案例，快速查看核查结果")

if "selected_case" not in st.session_state:
    st.session_state.selected_case = list(DEMO_CASES)[0]
if "current_case" not in st.session_state:
    st.session_state.current_case = None
if "result" not in st.session_state:
    st.session_state.result = None
if "result_case_label" not in st.session_state:
    st.session_state.result_case_label = None


def reset_case():
    st.session_state.current_case = None
    st.session_state.result = None
    st.session_state.result_case_label = None


selected = st.selectbox(
    "选择演示案例", list(DEMO_CASES), key="selected_case", on_change=reset_case,
    help="三种典型情形：金额差异、资料缺失、相对完整。所有数据均为虚构。",
)
example = deepcopy(DEMO_CASES[selected])

with st.container(border=True):
    a, b, c = st.columns(3)
    with a:
        st.caption("模拟企业 / 行业")
        st.write(f"**{example['company']}** · {example['industry']}")
    with b:
        st.caption("拟申请金额")
        st.write(f"**{example['loan_amount']:.0f} 万元**")
    with c:
        st.caption("案例重点")
        if selected.startswith("案例A"):
            st.write("**经营收入资料存在差异**")
        elif selected.startswith("案例B"):
            st.write("**关键资料缺失，不强行计算**")
        else:
            st.write("**资料记录较完整，仍需复核**")
    st.caption("点击下方按钮可一键核查；需要体验手动录入时，再展开“修改虚构资料”。")
    quick_run = st.button("🔎 一键分析当前模拟案例", type="primary", use_container_width=True)

with st.expander("✏️ 修改虚构资料（选用，不影响一键演示）", expanded=False):
    st.caption("本区域专供修改演示数据。填写后点击底部“用修改后的资料核查”，不需要返回上方按钮。")
    with st.form(f"case_form_{selected}"):
        st.markdown("**基本资料与经营对照**")
        c1, c2 = st.columns(2)
        with c1:
            company = st.text_input("企业代号（仅虚构）", value=example["company"])
            industry = st.text_input("行业", value=example["industry"])
            loan_amount = st.number_input("申请金额（万元）", min_value=0.0, value=example["loan_amount"], step=5.0)
            declared = st.number_input("申报年营业收入（万元）", min_value=0.0, value=example["declared_revenue"], step=10.0)
        with c2:
            has_statement = st.checkbox("已录入账户流入金额", value=example["statement_inflow"] is not None)
            statement = st.number_input("账户流入金额（万元）", min_value=0.0, value=float(example["statement_inflow"] or 0), step=10.0,
                                        help="如未勾选‘已录入’，该值不会参与核查。")
            has_tax = st.checkbox("已录入纳税申报销售额", value=example["tax_sales"] is not None)
            tax = st.number_input("纳税申报销售额（万元）", min_value=0.0, value=float(example["tax_sales"] or 0), step=10.0)
        periods = st.checkbox("已模拟确认：上述经营数据属同一统计期间及经营主体", value=example["periods_aligned"],
                              help="确认同期间不代表收入与账户流入的会计口径相同。")

        st.markdown("**月现金流与月债务偿付额（仅模拟输入）**")
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            has_cash = st.checkbox("已提供可用于偿债现金流", value=example["monthly_available_cashflow"] is not None)
            cash = st.number_input("月可用于偿债现金流（万元）", min_value=0.0,
                                   value=float(example["monthly_available_cashflow"] or 0), step=0.1)
        with cc2:
            has_existing = st.checkbox("已提供现有债务月偿付额", value=example["monthly_existing_debt"] is not None)
            existing = st.number_input("现有债务月偿付额（万元）", min_value=0.0,
                                       value=float(example["monthly_existing_debt"] or 0), step=0.1)
        with cc3:
            has_new = st.checkbox("已提供拟新增贷款月偿付额", value=example["monthly_new_debt"] is not None)
            new = st.number_input("拟新增贷款月偿付额（万元）", min_value=0.0,
                                  value=float(example["monthly_new_debt"] or 0), step=0.1)
        st.markdown("**材料及用途（非正式必交清单）**")
        purpose = st.text_input("贷款用途说明", value=example["purpose"])
        repayment = st.text_input("第一还款来源说明", value=example["repayment"])
        docs = st.multiselect("已有模拟材料类别", DOC_ITEMS, default=example["docs"])
        remark = st.text_area("补充备注", value=example["remark"], height=75)
        custom_run = st.form_submit_button("✅ 用修改后的资料核查", type="primary", use_container_width=True)

if quick_run:
    st.session_state.current_case = example
    st.session_state.result = evaluate(example)
    st.session_state.result_case_label = selected
elif custom_run:
    case = {
        "company": company or "未命名模拟企业", "industry": industry,
        "loan_amount": loan_amount, "declared_revenue": declared,
        "statement_inflow": statement if has_statement else None,
        "tax_sales": tax if has_tax else None, "periods_aligned": periods,
        "monthly_available_cashflow": cash if has_cash else None,
        "monthly_existing_debt": existing if has_existing else None,
        "monthly_new_debt": new if has_new else None,
        "purpose": purpose, "repayment": repayment, "docs": docs, "remark": remark,
    }
    st.session_state.current_case = case
    st.session_state.result = evaluate(case)
    st.session_state.result_case_label = f"{selected}（手动修改）"

if st.session_state.result is not None:
    case = st.session_state.current_case
    result = st.session_state.result
    st.divider()
    st.subheader("② 核查摘要：先看重点，再查明细")
    st.caption(f"当前分析：{st.session_state.result_case_label}｜只识别资料和数值核查线索，不判断贷款准入")
    gap_rows = [row for row in result["items"] if row["level"] == "待核实差异"]
    missing_count = len(result["missing_docs"])
    comps = len(result["comparisons"])
    x, y, z = st.columns(3)
    x.metric("未勾选材料类别", missing_count)
    y.metric("金额对照完成", comps)
    z.metric("数值差异提示", len(gap_rows))
    st.caption("以上均为演示条目数量；不构成风险等级、信用评分、授信建议。")

    # 业务重点放在最前面，不让评委先滚过十几个长折叠框。
    if gap_rows:
        for row in gap_rows[:2]:
            st.warning(f"**{row['title']}**：{row['detail']}")
    if missing_count:
        st.info("**模拟材料待补：**" + "、".join(result["missing_docs"]) + "。这不等于正式制度强制要求。")
    if not result["periods_aligned"]:
        st.info("**暂不进行金额差异比较：**统计期间或经营主体尚未确认。请先核实口径。")
    if not result["base_cashflow"]["calculable"]:
        st.info("**偿债情景暂不可计算：**月现金流或债务偿付信息不足，不能把缺失数据视为0。")
    if not gap_rows and not missing_count and result["periods_aligned"]:
        st.success("当前未触发演示材料缺失或数值差异提示；仍需核实原始凭证、经营真实性及还款来源。")

    if result["comparisons"]:
        with st.expander("查看经营数据对照表", expanded=True):
            st.dataframe([
                {"佐证类型": row["name"], "申报收入（万元）": row["declared"],
                 "佐证金额（万元）": row["comparison"], "数值差额（万元）": row["difference"],
                 "绝对差异比例": f"{row['ratio']}%"}
                for row in result["comparisons"]
            ], use_container_width=True, hide_index=True)
            st.caption("只是不同口径数值的对照；差额不等于收入虚报。20%为自定义演示提示线，而非监管标准。")

    with st.expander("查看全部核查项目和模拟制度出处", expanded=False):
        for row in result["items"]:
            st.markdown(f"**{row['title']}** · {row['level']}")
            st.write(row["detail"])
            st.caption(f"演示制度参考：第 {row['clause']} 条（仅为模拟引用）")
            st.divider()

    st.subheader("③ 现金流压力情景与核查记录")
    decline = st.slider(
        "假设月可用于偿债现金流下降幅度（非经济预测）",
        min_value=0, max_value=60, value=20, step=5,
        key=f"stress_{selected}", format="%d%%",
    )
    scenario = calculate_cashflow_scenario(case, decline)
    if scenario["calculable"]:
        base, stressed, due = st.columns(3)
        base.metric("基准偿债覆盖倍数", f"{scenario['baseline_cover']:.2f} 倍")
        stressed.metric("情景偿债覆盖倍数", f"{scenario['scenario_cover']:.2f} 倍",
                        delta=f"{scenario['scenario_cover']-scenario['baseline_cover']:+.2f} 倍")
        due.metric("情景月现金流－月债务", f"{scenario['scenario_surplus']:+.2f} 万元")
        st.write(
            f"假设月可用于偿债现金流从 **{scenario['cashflow']:.2f}万元** "
            f"变化为 **{scenario['scenario_cashflow']:.2f}万元**；"
            f"已录入月债务偿付额合计 **{scenario['monthly_total']:.2f}万元**。"
        )
        if scenario["scenario_cover"] < 1:
            st.warning(scenario["message"])
        else:
            st.info(scenario["message"])
    else:
        st.warning("当前无法计算偿债覆盖倍数：" + scenario["message"])
    st.caption("这是对输入值施加百分比变化的简单情景演算，不预测经济走势、实际违约概率或授信结果。")

    with st.expander("人工复核意见（用于导出报告）", expanded=True):
        auditor_note = st.text_area(
            "经办人员模拟核查记录",
            value="后续应补充核对原始经营凭证、数据统计口径、债务偿付额和第一还款来源。",
            height=90, key=f"review_note_{selected}",
        )
    final_result = {**result, "scenario": scenario}
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "⬇ 下载Word核查记录", build_docx(case, final_result, auditor_note),
            file_name="微贷慧查_模拟核查记录.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary", use_container_width=True,
        )
    with dl2:
        st.download_button(
            "下载Markdown备份", result_to_text(case, final_result, auditor_note),
            file_name="微贷慧查_模拟核查记录.md", mime="text/markdown",
            use_container_width=True,
        )
else:
    st.info("先选择一个虚构案例，点击“一键分析当前模拟案例”；也可以展开修改资料进行自定义演示。")

with st.expander("模拟制度与使用边界", expanded=False):
    policy = load_policy()
    st.write(f"**{policy['title']}** · {policy['version']}（自拟模拟内容，非银行正式制度）")
    for part in policy["sections"]:
        st.markdown(f"**{part['id']} {part['title']}**")
        st.write(part["content"])
    st.caption("无大模型推理；不读取真实客户资料；输出只供模拟参赛和教学演示。")

st.caption("微贷慧查 v1.2｜经营资料核对 + 偿债情景｜规则驱动模拟原型")
