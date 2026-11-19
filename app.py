"""作品二：微贷慧查——小微贷款贷前尽调模拟核查原型。"""
import streamlit as st
from rules import DOC_ITEMS, DEMO_CASES, evaluate, load_policy, result_to_text
from report import build_docx

st.set_page_config(page_title='微贷慧查 | 小微贷款贷前尽调',page_icon='🧾',layout='wide')
st.markdown('''<style>
.block-container {max-width:1120px;padding-top:2rem}
[data-testid="stMetric"] {background:#f3f7fb;border:1px solid #dce7f3;border-radius:12px;padding:14px}
.stButton button[kind="primary"] {background:#1c4975;border-color:#1c4975}
</style>''',unsafe_allow_html=True)
st.caption('普惠金融业务应用 · 独立参赛作品 02')
st.title('🧾 微贷慧查 · 小微贷款贷前尽调辅助工具')
st.write('聚焦 **材料完整性核对、经营数据差异提示、核查记录生成**，不搭建完整的授信审批系统。')
st.warning('本系统仅用于虚构客户案例和模拟规则展示，不调用大模型、不评定客户信用或授信结果。不得录入真实客户资料。')

policy=load_policy()
if 'case_name' not in st.session_state:
    st.session_state.case_name='收入差异案例'
if 'result' not in st.session_state:
    st.session_state.result=None
if 'current_case' not in st.session_state:
    st.session_state.current_case=None

st.subheader('第一步｜选择案例并录入模拟资料')
def _reset_case_result():
    st.session_state.result = None
    st.session_state.current_case = None
name=st.selectbox('一键载入模拟案例',list(DEMO_CASES.keys()),key='case_name',on_change=_reset_case_result,help='切换案例后，下方表单自动刷新成对应的虚构数据。')
example=DEMO_CASES[name]
with st.form(f'loan_form_{name}'):
    c1,c2=st.columns(2)
    with c1:
        company=st.text_input('企业代号（仅虚构名称）',value=example['company'])
        industry=st.text_input('经营行业',value=example['industry'])
        loan_amount=st.number_input('申请金额（万元）',min_value=0.0,max_value=100000.0,value=example['loan_amount'],step=10.0)
        declared=st.number_input('申报年营业收入（万元）',min_value=0.0,max_value=10000000.0,value=example['declared_revenue'],step=10.0)
    with c2:
        statement_has=st.checkbox('有模拟银行流水/账户流入数据',value=example['statement_inflow'] is not None)
        statement=st.number_input('模拟账户流入总额（万元）',min_value=0.0,max_value=10000000.0,value=float(example['statement_inflow'] or 0),disabled=not statement_has,step=10.0)
        tax_has=st.checkbox('有模拟纳税销售额数据',value=example['tax_sales'] is not None)
        tax=st.number_input('模拟纳税申报销售额（万元）',min_value=0.0,max_value=10000000.0,value=float(example['tax_sales'] or 0),disabled=not tax_has,step=10.0)
    purpose=st.text_input('融资用途说明',value=example['purpose'])
    repayment=st.text_input('第一还款来源说明',value=example['repayment'])
    docs=st.multiselect('已提供资料类别（演示核对清单，并非正式必交材料清单）',DOC_ITEMS,default=example['docs'])
    remark=st.text_area('案例备注（请勿填写真实客户信息）',value=example['remark'],height=80)
    submitted=st.form_submit_button('🔍 运行模拟资料核查',type='primary',use_container_width=True)

if submitted:
    case={'company':company or '未命名虚构企业', 'industry':industry,'loan_amount':loan_amount,
          'declared_revenue':declared, 'statement_inflow':statement if statement_has else None,
          'tax_sales':tax if tax_has else None, 'purpose':purpose, 'repayment':repayment,
          'docs':docs, 'remark':remark}
    st.session_state.current_case=case
    st.session_state.result=evaluate(case)

if st.session_state.result:
    case=st.session_state.current_case
    result=st.session_state.result
    st.divider()
    st.subheader('第二步｜查看核查结果')
    a,b,c=st.columns(3)
    a.metric('演示清单待补类别',len(result['missing_docs']))
    b.metric('数据比较项',len(result['comparisons']))
    c.metric('需复核或补充事项',len(result['followups']))
    st.caption('仅为记录条目数，不是风险评分、授信标准或客户评级。')
    if result['comparisons']:
        st.markdown('**经营数据交叉比较（金额单位：万元）**')
        st.dataframe([{'比较项目':x['name'], '申报营业收入':x['declared'], '对应佐证金额':x['comparison'],
                       '差额(申报−佐证)':x['difference'], '差异占申报收入':f"{x['ratio']}%"} for x in result['comparisons']],
                     use_container_width=True,hide_index=True)
        st.caption('注意：账户流入与纳税销售额的统计口径可能与营业收入不同，差异只提示进一步人工核查。')
    for item in result['items']:
        with st.container(border=True):
            st.markdown(f"**{item['title']}** · `{item['level']}`")
            st.write(item['detail'])
            st.caption(f"关联模拟制度：{policy['title']}，第{item['clause']}条")
    st.subheader('第三步｜人工备注和报告导出')
    note=st.text_area('经办人员复核意见（仅用于模拟展示）',value='建议按正式制度进一步核对交易口径、经营资料和用途凭证。',height=100)
    left,right=st.columns(2)
    with left:
        st.download_button('⬇️ 下载Word核查记录草稿',data=build_docx(case,result,note),
                           file_name='微贷慧查_模拟尽调核查记录.docx',
                           mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                           type='primary',use_container_width=True)
    with right:
        st.download_button('⬇️ 下载Markdown记录',data=result_to_text(case,result,note),
                           file_name='微贷慧查_模拟尽调核查记录.md',mime='text/markdown',use_container_width=True)
else:
    st.info('先选择一个虚构案例，点击“运行模拟资料核查”，再查看差异提示和导出报告。')

with st.expander('查看本作品引用的模拟制度条款'):
    st.caption(f"{policy['title']} · {policy['version']} · 仅供比赛演示")
    for section in policy['sections']:
        st.markdown(f"**{section['id']} {section['title']}**")
        st.write(section['content'])
with st.expander('未来落地时可以扩展什么？'):
    st.markdown('''- 仅在获得银行授权及满足数据安全要求后，接入真实制度知识库和受控大模型。
- 加入影像资料识别、资料真伪核验、经授权的业务系统接口。
- 增加审核权限、操作审计、版本治理；当前公开演示版不具有这些能力。''')
