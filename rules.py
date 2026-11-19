"""微贷慧查：小微贷款贷前资料核查模拟规则。所有阈值均非银行授信标准。"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json

POLICY_FILE = Path(__file__).resolve().parent / 'data' / 'loan_policy.json'

DOC_ITEMS = [
    '主体资格及营业执照',
    '经办人身份及授权资料',
    '企业基本信息及实际控制人情况',
    '经营情况说明',
    '融资用途及资金需求说明',
    '经营与财务佐证资料',
]

DEMO_CASES = {
    '收入差异案例': {
        'company': '模拟企业A', 'industry': '食品批发', 'loan_amount': 100.0,
        'declared_revenue': 500.0, 'statement_inflow': 280.0,
        'tax_sales': 310.0, 'purpose': '采购原材料',
        'repayment': '模拟经营收入及销售回款',
        'docs': DOC_ITEMS[:5],
        'remark': '模拟流水统计口径与申报年收入可能不同，尚无其他明细佐证。',
    },
    '材料缺失案例': {
        'company': '模拟企业B', 'industry': '机械加工', 'loan_amount': 80.0,
        'declared_revenue': 420.0, 'statement_inflow': 405.0,
        'tax_sales': None, 'purpose': '补充原材料周转',
        'repayment': '',
        'docs': [DOC_ITEMS[0], DOC_ITEMS[2], DOC_ITEMS[3]],
        'remark': '经办人授权材料、资金需求说明及税务资料尚待补充。',
    },
    '资料较完整案例': {
        'company': '模拟企业C', 'industry': '服装加工', 'loan_amount': 60.0,
        'declared_revenue': 300.0, 'statement_inflow': 294.0,
        'tax_sales': 290.0, 'purpose': '支付面料采购款',
        'repayment': '模拟订单销售回款',
        'docs': DOC_ITEMS[:],
        'remark': '仍应按正式制度核对资料真实性及经营情况。',
    },
}

# 20% 是演示差异提示线，为便于展示人工核查流程而设，不是风险评级、准入或审批标准。
DEMO_DIFF_RATIO = 0.20


def load_policy() -> dict:
    p = json.loads(POLICY_FILE.read_text(encoding='utf-8'))
    assert p['id'] == 'CORP-LOAN-001' and p['version'] == '2026版'
    return p


def item(code: str, title: str, level: str, detail: str, clause: str) -> dict:
    return {'code': code, 'title': title, 'level': level, 'detail': detail, 'clause': clause}


def evaluate(case: dict) -> dict:
    """静态规则核查，不输出信用评级、准入、审批或授信建议。"""
    submitted = set(case.get('docs') or [])
    missing = [d for d in DOC_ITEMS if d not in submitted]
    rows = []
    if missing:
        rows.append(item('DOC-MISSING','演示资料清单存在待补项','待补充',
                         '当前未勾选：' + '、'.join(missing) + '。仅表示此模拟清单未齐，不代表正式业务强制材料缺失。','3.2'))
    else:
        rows.append(item('DOC-CHECK','演示清单已勾选齐全','已记录',
                         '全部演示核对类别已勾选；不代表原始凭证真实或正式审批材料完整。','3.2'))
    if not str(case.get('purpose') or '').strip():
        rows.append(item('PURPOSE-MISSING','贷款用途信息未填写','待补充',
                         '补充用途说明及可核验交易背景，不据此作出准入判断。','3.1 / 4.1'))
    else:
        rows.append(item('PURPOSE-REVIEW','贷款用途已记录','待人工核实',
                         f"已填写用途：{case['purpose']}；仍需核查真实性、合理性与经营匹配情况。",'3.1 / 4.1'))
    if not str(case.get('repayment') or '').strip():
        rows.append(item('REPAY-MISSING','第一还款来源说明待补充','待补充',
                         '应记录第一还款来源及其佐证资料，交由客户经理核实。','3.1 / 4.1'))
    else:
        rows.append(item('REPAY-REVIEW','第一还款来源已记录','待人工核实',
                         '已填写还款来源说明，仍需结合经营现金流及相关证据核实。','3.1 / 4.1'))
    declared = float(case.get('declared_revenue') or 0)
    statement = case.get('statement_inflow')
    tax = case.get('tax_sales')
    contrasts = []
    for code, label, val in [('STMT','账户流入金额',statement),('TAX','纳税申报销售额',tax)]:
        if val is None:
            rows.append(item(f'{code}-MISSING',f'{label}未提供','待补充',
                             f'未提供{label}，暂不能进行这一项模拟差异比较；是否必须提供应由正式制度确定。','3.2 / 5.1'))
            continue
        amount = float(val)
        if declared <= 0:
            rows.append(item(f'{code}-SKIP','申报营业收入需核实','待补充',
                             '申报营业收入未填写或为零，无法计算差异比例。','5.1'))
            continue
        diff = round(declared - amount, 2)
        ratio = abs(diff) / declared
        contrasts.append({'name': label, 'declared': declared, 'comparison': amount,
                          'difference': diff, 'ratio': round(ratio * 100, 1)})
        if ratio > DEMO_DIFF_RATIO:
            rows.append(item(f'{code}-GAP',f'营业收入与{label}存在较大差异','待核实差异',
                             f'申报年收入{declared:.2f}万元，{label}{amount:.2f}万元，差额{diff:+.2f}万元，占申报收入{ratio:.1%}。需核对统计期间、计算口径、其他回款渠道和原始佐证；不能单凭差额认定收入不实。','5.1'))
        else:
            rows.append(item(f'{code}-COMPARED',f'已完成{label}比较','已比较',
                             f'差额{diff:+.2f}万元（占申报收入{ratio:.1%}），未触发本演示的20%差异提示线；不等于已核实收入真实。','5.1'))
    followups = [r for r in rows if r['level'] in ('待补充','待核实差异','待人工核实')]
    return {'items':rows, 'missing_docs':missing, 'comparisons':contrasts,
            'followups':followups, 'policy': load_policy(),
            'notice':'规则阈值仅用于模拟演示，不属于任何银行的风险定级、准入或放款标准。'}


def result_to_text(case: dict, result: dict, auditor_note: str = '') -> str:
    lines = [f"# {case['company']}｜小微贷款贷前尽调模拟核查记录",'',
             '声明：本文件为虚构案例的演示记录，不是正式尽调报告或授信意见。', '',
             '## 一、案例信息']
    for label, field in [('企业代号','company'),('行业','industry'),('贷款用途','purpose'),('还款来源说明','repayment'),('模拟备注','remark')]:
        lines.append(f"- {label}：{case.get(field) or '待补充'}")
    lines.extend([f"- 申请金额：{case.get('loan_amount',0)}万元",f"- 申报年收入：{case.get('declared_revenue',0)}万元",''])
    lines += ['## 二、模拟资料核对']
    for d in DOC_ITEMS:
        lines.append(f"- [{'x' if d in (case.get('docs') or []) else ' '}] {d}")
    lines += ['', '## 三、规则核查结果']
    for i in result['items']:
        lines += [f"### {i['title']}｜{i['level']}",i['detail'], f"模拟制度依据：第{i['clause']}条",'']
    lines += ['## 四、人工复核与下一步', auditor_note.strip() or '待人工补充核查结论和后续动作。', '',
              '## 五、使用边界',result['notice'], '实际业务仅以正式有效制度、原始证据和授权审批流程为准。']
    return '\n'.join(lines)
