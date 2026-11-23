"""微贷慧查 v1.1：仅用于虚构案例的标准化核查与偿债情景演示。

不输出个人或企业信用评分、审批、授信额度或违约概率。
"""
from __future__ import annotations

import json
from pathlib import Path

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
    '案例A｜经营数据存在差异': {
        'company': '模拟企业A', 'industry': '食品批发', 'loan_amount': 100.0,
        'declared_revenue': 500.0, 'statement_inflow': 280.0, 'tax_sales': 310.0,
        'periods_aligned': True,
        'purpose': '采购原材料', 'repayment': '模拟经营收入及销售回款',
        'monthly_available_cashflow': 3.0,
        'monthly_existing_debt': 1.6,
        'monthly_new_debt': 0.9,
        'docs': DOC_ITEMS[:5],
        'remark': '模拟案例已假设数据统计期间一致，但各项收入仍可能存在不同会计口径。',
    },
    '案例B｜缺少现金流信息': {
        'company': '模拟企业B', 'industry': '机械加工', 'loan_amount': 80.0,
        'declared_revenue': 420.0, 'statement_inflow': 405.0, 'tax_sales': None,
        'periods_aligned': False,
        'purpose': '补充原材料周转', 'repayment': '',
        'monthly_available_cashflow': None,
        'monthly_existing_debt': None,
        'monthly_new_debt': 0.7,
        'docs': [DOC_ITEMS[0], DOC_ITEMS[2], DOC_ITEMS[3]],
        'remark': '统计口径和月债务偿付额有待确认，情景分析应显示“无法计算”。',
    },
    '案例C｜资料较完整': {
        'company': '模拟企业C', 'industry': '服装加工', 'loan_amount': 60.0,
        'declared_revenue': 300.0, 'statement_inflow': 294.0, 'tax_sales': 290.0,
        'periods_aligned': True,
        'purpose': '支付面料采购款', 'repayment': '模拟订单销售回款',
        'monthly_available_cashflow': 4.5,
        'monthly_existing_debt': 1.2,
        'monthly_new_debt': 0.5,
        'docs': DOC_ITEMS[:],
        'remark': '即使模拟金额差异不大，仍须核实原始凭证、现金流和还款能力。',
    },
}

# 演示触发差异提示线，并非监管规定、授信准入标准或银行风控阈值。
DEMO_DIFF_RATIO = 0.20


def load_policy() -> dict:
    data = json.loads(POLICY_FILE.read_text(encoding='utf-8'))
    if data.get('id') != 'CORP-LOAN-001':
        raise ValueError('模拟制度文件不匹配')
    return data


def item(code: str, title: str, level: str, detail: str, clause: str) -> dict:
    return {'code': code, 'title': title, 'level': level, 'detail': detail, 'clause': clause}


def _money(value, label: str) -> float | None:
    if value is None:
        return None
    v = float(value)
    if not 0 <= v <= 1e10:
        raise ValueError(f'{label}应为非负且有限的模拟金额')
    return v


def calculate_cashflow_scenario(case: dict, decline_pct: float = 20.0) -> dict:
    """根据*用户提供的假设值*计算覆盖倍数；不估计违约概率和未来经济走势。"""
    pct = float(decline_pct)
    if not 0 <= pct <= 100:
        raise ValueError('情景现金流下降比例应为0%—100%')
    cash = _money(case.get('monthly_available_cashflow'), '模拟月可用于偿债现金流')
    existing = _money(case.get('monthly_existing_debt'), '已有债务月偿付额')
    new = _money(case.get('monthly_new_debt'), '拟新增贷款预计月偿付额')
    data = {'calculable': False, 'decline_pct': pct, 'cashflow': cash,
            'existing': existing, 'new': new, 'monthly_total': None,
            'scenario_cashflow': None, 'baseline_cover': None,
            'scenario_cover': None, 'scenario_surplus': None}
    if any(v is None for v in (cash, existing, new)):
        data['message'] = ('缺少月可用于偿债现金流或债务月偿付额，不能计算覆盖倍数；'
                           '应先补充并核实数据来源。')
        return data
    total = existing + new
    data['monthly_total'] = round(total, 2)
    if total <= 0:
        data['message'] = '尚无已录入的每月债务偿付金额，不适用覆盖倍数计算。'
        return data
    stressed = cash * (1 - pct / 100)
    baseline = cash / total
    cover = stressed / total
    data.update({'calculable': True, 'scenario_cashflow': round(stressed, 2),
                 'baseline_cover': round(baseline, 3), 'scenario_cover': round(cover, 3),
                 'scenario_surplus': round(stressed - total, 2)})
    if cover < 1:
        data['message'] = ('在该假设下，已录入的模拟月可用于偿债现金流低于已录入的月债务偿付额；'
                           '应核实收入稳定性、费用、其他还款来源和债务资料。')
    else:
        data['message'] = ('在该假设下，模拟现金流可覆盖已录入的月债务偿付额；'
                           '这并不意味着未来还款有保障，也不是授信结论。')
    return data


def evaluate(case: dict) -> dict:
    """对材料清单与模拟数值进行核对，不代替正式尽调或授信判断。"""
    _money(case.get('loan_amount'), '申请金额')
    declared = _money(case.get('declared_revenue'), '申报年营业收入') or 0.0
    statement = _money(case.get('statement_inflow'), '模拟账户流入')
    tax = _money(case.get('tax_sales'), '模拟纳税销售额')
    docs = set(case.get('docs') or [])
    missing = [d for d in DOC_ITEMS if d not in docs]
    rows = []
    if missing:
        rows.append(item('DOC-MISSING','演示材料类别尚待补充','待补充',
                         '未勾选：' + '、'.join(missing) + '。仅代表模拟清单状态，不等于违反正式材料要求。','3.2'))
    else:
        rows.append(item('DOC-CHECK','演示材料清单已勾选齐全','已记录',
                         '仅表示演示记录完整，未核验原始资料的真实性或适用性。','3.2'))
    if not str(case.get('purpose') or '').strip():
        rows.append(item('PURPOSE-MISSING','贷款用途说明待补充','待补充',
                         '补充经营相关的资金用途及证明材料，按适用制度复核。','3.1 / 4.1'))
    else:
        rows.append(item('PURPOSE-REVIEW','贷款用途已录入','待人工核实',
                         f"模拟用途：{case['purpose']}。仍需核实交易背景及经营关联性。",'3.1 / 4.1'))
    if not str(case.get('repayment') or '').strip():
        rows.append(item('REPAY-MISSING','第一还款来源说明待补充','待补充',
                         '尚未录入第一还款来源，需取得可核查的现金流与佐证材料。','3.1 / 4.1'))
    else:
        rows.append(item('REPAY-REVIEW','第一还款来源已录入','待人工核实',
                         '已录入文字说明，但须结合现金流、负债及原始资料验证。','3.1 / 4.1'))
    comparisons = []
    aligned = bool(case.get('periods_aligned', False))
    if not aligned:
        rows.append(item('PERIOD-NOT-ALIGNED','比较期间或主体口径尚未确认','待核实',
                         '尚未确认申报收入、账户流入与纳税销售额对应同一期间和同一经营主体，'
                         '暂不据此计算差异比例。即使期间一致，各指标会计口径仍可能不同。','5.1'))
    for code, label, val in [('STMT', '账户流入金额', statement), ('TAX', '纳税申报销售额', tax)]:
        if val is None:
            rows.append(item(f'{code}-MISSING', f'{label}未提供', '待补充',
                             f'缺少{label}，无法完成相应对照；是否必须提供以正式制度为准。','3.2 / 5.1'))
            continue
        if not aligned:
            continue
        if declared <= 0:
            rows.append(item(f'{code}-SKIP', '申报收入未填写或为零', '待补充',
                             '没有有效的正数申报收入，不能计算相对差异。','5.1'))
            continue
        diff = round(declared - val, 2)
        ratio = abs(diff)/declared
        comparisons.append({'name':label, 'declared':declared, 'comparison':val,
                            'difference':diff, 'ratio':round(ratio*100, 1)})
        if ratio > DEMO_DIFF_RATIO:
            rows.append(item(f'{code}-GAP', f'申报收入与{label}存在数值差异', '待核实差异',
                             f'申报年收入{declared:.2f}万元，{label}{val:.2f}万元，差额{diff:+.2f}万元，'
                             f'约为申报收入的{ratio:.1%}，超过演示差异提示线20%。'
                             '应分别核实统计期间、会计口径、账户范围及佐证来源，'
                             '不能据此推断收入不实。','5.1'))
        else:
            rows.append(item(f'{code}-COMPARED', f'{label}已完成对照', '已比较',
                             f'差额{diff:+.2f}万元，约为申报收入的{ratio:.1%}；'
                             '未触发演示提示线不代表资料真实或还款能力充足。','5.1'))
    base_cashflow = calculate_cashflow_scenario(case, 0)
    if not base_cashflow['calculable']:
        rows.append(item('CASHFLOW-UNAVAILABLE', '月度偿债信息不足', '待补充',
                         base_cashflow['message'], '3.1 / 4.1'))
    else:
        rows.append(item('CASHFLOW-RECORDED', '月度现金流及债务偿付信息已录入', '待人工核实',
                         '数据用于模拟覆盖倍数；仍需核对金额、期间、费用、其他债务和稳定性。', '3.1 / 4.1'))
    followups = [x for x in rows if x['level'] in ('待补充', '待核实', '待核实差异', '待人工核实')]
    return {'items': rows, 'missing_docs': missing, 'comparisons': comparisons,
            'followups': followups, 'periods_aligned':aligned,
            'policy': load_policy(), 'base_cashflow':base_cashflow,
            'notice': '本工具仅展示虚构数据与透明规则，不输出信用评分、准入、授信额度、违约概率或自动放款结论。'}


def result_to_text(case: dict, result: dict, auditor_note: str = '') -> str:
    lines = [f"# {case.get('company', '模拟企业')}｜微贷慧查核查记录",'',
             '声明：完全虚构的演示案例；非正式贷前调查、授信或风险评级意见。', '',
             '## 一、模拟案例信息']
    for label, field in [('企业代号','company'),('经营行业','industry'),('贷款用途','purpose'),
                         ('还款来源说明','repayment'),('模拟备注','remark')]:
        lines.append(f"- {label}：{case.get(field) or '待补充'}")
    lines += [f"- 申请金额：{case.get('loan_amount', 0)}万元",
              f"- 申报年收入：{case.get('declared_revenue', 0)}万元",
              f"- 已核实同期间与同主体：{'是（仅模拟确认）' if result['periods_aligned'] else '否/待确认'}",'']
    lines += ['## 二、资料核对']
    for d in DOC_ITEMS:
        lines.append(f"- [{'x' if d in (case.get('docs') or []) else ' '}] {d}")
    lines += ['', '## 三、模拟资料差异及待核查事项']
    for row in result['items']:
        lines += [f"### {row['title']}｜{row['level']}",row['detail'], f"模拟制度条款：第{row['clause']}条",'']
    s = result.get('scenario') or calculate_cashflow_scenario(case, 20)
    lines += ['## 四、现金流压力情景（假设，不是预测）',
              f"- 假设月可用于偿债现金流下降：{s['decline_pct']:.0f}%"]
    if s['calculable']:
        lines += [f"- 已录入月可用于偿债现金流：{s['cashflow']:.2f}万元",
                  f"- 已录入月债务偿付额合计：{s['monthly_total']:.2f}万元",
                  f"- 基准覆盖倍数：{s['baseline_cover']:.2f}倍",
                  f"- 情景覆盖倍数：{s['scenario_cover']:.2f}倍",
                  f"- 情景下现金流与月偿付额差额：{s['scenario_surplus']:+.2f}万元"]
    else:
        lines += ['- 计算结果：资料不足，未计算覆盖倍数']
    lines += [s['message'],
              '注意：这是对已录入假设的算术情景测试，不代表真实经济预测，也未核验现金流、债务和其他家庭/经营支出。','',
              '## 五、人工复核', auditor_note.strip() or '待补充原始证据、核验口径和经办意见。','',
              '## 六、使用边界',result['notice'],
              '适用要求以正式制度、业务审批权限和真实经核实的材料为准。']
    return '\n'.join(lines)
