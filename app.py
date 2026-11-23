"""微贷慧查 v1.1：小微贷款资料核查与现金流情景分析（虚构案例）。"""
import streamlit as st

from report import build_docx
from rules import (DEMO_CASES, DOC_ITEMS, calculate_cashflow_scenario,
                   evaluate, load_policy, result_to_text)

st.set_page_config(page_title='微贷慧查｜贷前核查演示', page_icon='📋', layout='wide')
st.markdown('''<style>
.block-container {max-width:1120px;padding-top:1.7rem;padding-bottom:3rem}
h1,h2,h3 {color:#193c59}
[data-testid="stMetric"] {background:#f4f8fc;border:1px solid #dfebf3;border-radius:12px;padding:12px 16px}
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"] {background:#176384;border-color:#176384}
[data-testid="stExpander"] {border:1px solid #e5eaf0;border-radius:10px}
.small-info {font-size:.91rem;color:#597184}
</style>''', unsafe_allow_html=True)

st.caption('银行内部创新参赛 · 规则驱动模拟原型 · 作品二')
st.title('微贷慧查｜贷前调查核查助手')
st.write('**只做两件事：核对经营资料，模拟还款来源承压后的变化。**')
st.info('🔒 仅使用完全虚构的企业资料和模拟制度。公开网页不可录入真实客户信息、征信、账户流水或内部保密文件。无真实AI模型、风险评分和授信决策。')

policy = load_policy()
if 'selected_case' not in st.session_state:
    st.session_state.selected_case = list(DEMO_CASES.keys())[0]
if 'result' not in st.session_state:
    st.session_state.result = None
if 'current_case' not in st.session_state:
    st.session_state.current_case = None


def reset_case():
    st.session_state.result = None
    st.session_state.current_case = None


st.subheader('① 选择模拟案例，核对基础信息')
selected = st.selectbox('虚构案例', list(DEMO_CASES), key='selected_case', on_change=reset_case,
                        help='可以选择预设案例，也可修改下面的虚构字段；不会保存到服务器。')
example = DEMO_CASES[selected]
with st.form(f'case_form_{selected}'):
    left, right = st.columns(2)
    with left:
        company = st.text_input('企业代号（仅虚构）', example['company'])
        industry = st.text_input('行业', example['industry'])
        loan_amount = st.number_input('申请金额（万元）', min_value=0.0, value=example['loan_amount'], step=10.0)
        declared = st.number_input('申报年营业收入（万元）', min_value=0.0, value=example['declared_revenue'], step=10.0)
    with right:
        has_statement = st.checkbox('已录入账户流入金额', value=example['statement_inflow'] is not None)
        statement = st.number_input('账户流入金额（万元）', min_value=0.0,
                                    value=float(example['statement_inflow'] or 0), step=10.0,
                                    help='未勾选“已录入”时，此金额不会被用于计算。')
        has_tax = st.checkbox('已录入纳税销售额', value=example['tax_sales'] is not None)
        tax = st.number_input('纳税申报销售额（万元）', min_value=0.0,
                              value=float(example['tax_sales'] or 0), step=10.0)
    periods = st.checkbox('已核实以上经营数据对应同一统计期间、同一经营主体（演示确认）',
                          value=example['periods_aligned'],
                          help='未确认时不计算相对差异比例；即使期间一致，不同指标仍可能有口径差异。')
    st.markdown('**还款来源与月度债务信息（全部为模拟数据）**')
    a,b,c=st.columns(3)
    with a:
        has_cash = st.checkbox('已录入月可用于偿债现金流', value=example['monthly_available_cashflow'] is not None)
        cash = st.number_input('月可用于偿债现金流（万元）', min_value=0.0,
                               value=float(example['monthly_available_cashflow'] or 0), step=0.1)
    with b:
        has_existing = st.checkbox('已录入已有债务月偿付额', value=example['monthly_existing_debt'] is not None)
        existing = st.number_input('已有债务月偿付额（万元）', min_value=0.0,
                                   value=float(example['monthly_existing_debt'] or 0), step=0.1)
    with c:
        has_new = st.checkbox('已录入拟新增贷款预计月偿付额', value=example['monthly_new_debt'] is not None)
        new = st.number_input('拟新增贷款预计月偿付额（万元）', min_value=0.0,
                              value=float(example['monthly_new_debt'] or 0), step=0.1,
                              help='需按拟定期限和还款方式另行核算，本工具不自动确定贷款额度或还款计划。')
    with st.expander('选填：材料清单、贷款用途与业务备注'):
        purpose = st.text_input('贷款用途', value=example['purpose'])
        repayment = st.text_input('第一还款来源说明', value=example['repayment'])
        docs = st.multiselect('已有模拟材料类别（非正式必交清单）', DOC_ITEMS, default=example['docs'])
        remark = st.text_area('模拟备注', value=example['remark'], height=75)
    submitted = st.form_submit_button('🔍 开始标准化核查', type='primary', use_container_width=True)

if submitted:
    case = {'company':company or '未命名模拟企业', 'industry':industry,
            'loan_amount':loan_amount, 'declared_revenue':declared,
            'statement_inflow': statement if has_statement else None,
            'tax_sales': tax if has_tax else None, 'periods_aligned':periods,
            'monthly_available_cashflow':cash if has_cash else None,
            'monthly_existing_debt':existing if has_existing else None,
            'monthly_new_debt':new if has_new else None,
            'purpose':purpose, 'repayment':repayment, 'docs':docs, 'remark':remark}
    st.session_state.current_case = case
    st.session_state.result = evaluate(case)

if st.session_state.result is not None:
    case = st.session_state.current_case
    result = st.session_state.result
    st.divider()
    st.subheader('② 查看经营资料核对结果')
    x,y,z=st.columns(3)
    x.metric('待补材料类别', len(result['missing_docs']))
    y.metric('可进行的数据对照', len(result['comparisons']))
    z.metric('待补充或待核实事项', len(result['followups']))
    st.caption('以上为清单条目数量，不是信用评分、风险等级或审批结果。')
    if result['comparisons']:
        st.markdown('**同期间经营数据数值对照（万元）**')
        st.dataframe([{'佐证项目':d['name'], '申报年收入':d['declared'],
                       '相关佐证金额':d['comparison'], '数值差额':d['difference'],
                       '绝对差异占申报收入':f"{d['ratio']}%"} for d in result['comparisons']],
                     use_container_width=True, hide_index=True)
        st.caption('数值差异不等于虚报收入；需核查会计口径、账户范围、期间及原始凭证。20%仅为演示提示线。')
    else:
        st.info('当前无法完成金额对照：请确认统计期间、主体及必需数值。')
    for row in result['items']:
        if row['level'] in ('待补充','待核实','待核实差异','待人工核实'):
            with st.expander(f"{row['title']} · {row['level']}", expanded=row['level'] in ('待补充','待核实差异')):
                st.write(row['detail'])
                st.caption(f"关联模拟制度：第{row['clause']}条（仅为参照）")
    with st.expander('查看全部核对记录（含已比较项目）'):
        for row in result['items']:
            st.write(f"**{row['title']}｜{row['level']}**：{row['detail']}")

    st.divider()
    st.subheader('③ 模拟偿债压力情景，导出核查记录')
    decline = st.slider('假设未来月可用于偿债现金流下降（不是经济预测）',
                        min_value=0, max_value=60, value=20, step=5,
                        key=f'stress_{selected}', format='%d%%')
    scenario = calculate_cashflow_scenario(case, decline)
    if scenario['calculable']:
        p,q,r = st.columns(3)
        p.metric('已录入月债务偿付额', f"{scenario['monthly_total']:.2f}万元")
        q.metric('基准覆盖倍数', f"{scenario['baseline_cover']:.2f}倍")
        r.metric('情景覆盖倍数', f"{scenario['scenario_cover']:.2f}倍")
        st.write(f"情景月可用现金流：**{scenario['scenario_cashflow']:.2f}万元**；"
                 f"现金流与已录入月偿付额差额：**{scenario['scenario_surplus']:+.2f}万元**。")
    else:
        st.warning('情景分析暂不能计算：' + scenario['message'])
    st.info(scenario['message'])
    st.caption('仅对人工输入的月现金流作百分比变化假设；未预测宏观经济，也不能用覆盖倍数直接判断是否授信。')
    note = st.text_area('模拟经办人员复核记录（不提交真实客户信息）',
                        value='请补充原始佐证，核对收入期间与现金流数据，并由有权人员复核。',
                        height=90)
    final_result = {**result, 'scenario': scenario}
    c1,c2=st.columns(2)
    with c1:
        st.download_button('⬇️ 下载Word核查记录', build_docx(case, final_result, note),
                           file_name='微贷慧查_模拟核查记录.docx',
                           mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                           type='primary', use_container_width=True)
    with c2:
        st.download_button('⬇️ 下载Markdown记录', result_to_text(case, final_result, note),
                           file_name='微贷慧查_模拟核查记录.md', mime='text/markdown',
                           use_container_width=True)
else:
    st.info('先选择一个虚构案例，并点击“开始标准化核查”，即可查看差异提示和偿债情景。')

with st.expander('模拟制度依据与技术边界'):
    st.caption(f"{policy['title']} · {policy['version']} · 项目自拟模拟内容，非正式制度")
    for section in policy['sections']:
        st.markdown(f"**{section['id']} {section['title']}**")
        st.write(section['content'])
    st.write('本版本使用透明Python规则和算术情景分析，不涉及机器学习模型、不调用大语言模型。')
st.caption('微贷慧查 v1.1 | 仅供模拟参赛演示 | 无真实信用风险预测与审批能力')
