"""生成 Word 核查记录草稿，不是银行正式调查报告。"""
from __future__ import annotations
from io import BytesIO
from datetime import date
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from rules import DOC_ITEMS, calculate_cashflow_scenario


def _font(style, size=10.5, bold=False, color=(42,57,75)):
    style.font.name = 'Microsoft YaHei'
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = RGBColor(*color)
    style._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')


def build_docx(case: dict, result: dict, note: str = '') -> bytes:
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2.2)
    sec.top_margin = sec.bottom_margin = Cm(1.65)
    _font(doc.styles['Normal'], 10)
    doc.styles['Normal'].paragraph_format.space_after = Pt(4)
    doc.styles['Heading 1'].paragraph_format.space_before = Pt(10)
    doc.styles['Heading 1'].paragraph_format.space_after = Pt(5)
    doc.styles['Heading 2'].paragraph_format.space_before = Pt(5)
    doc.styles['Heading 2'].paragraph_format.space_after = Pt(2)
    _font(doc.styles['Title'], 18, True, (26,65,104))
    _font(doc.styles['Heading 1'], 12, True, (26,65,104))
    _font(doc.styles['Heading 2'], 10.5, True, (26,65,104))
    doc.add_heading('微贷慧查｜贷前核查与偿债情景记录', 0)
    doc.add_paragraph(f'生成日期：{date.today().isoformat()}    案例：{case.get("company", "模拟客户")}', style='Subtitle')
    doc.add_paragraph('演示原型 • 虚构案例 • 不代表正式调查、风险评级、准入或授信结论')
    doc.add_heading('一、模拟客户基本情况', 1)
    table = doc.add_table(rows=0, cols=2)
    table.style = 'Light Shading Accent 1'
    table.autofit = False
    for a,b in [
        ('模拟企业代号',case.get('company','')),('经营行业',case.get('industry','')),
        ('申请贷款金额',f"{case.get('loan_amount',0):.2f} 万元"),
        ('申报年营业收入',f"{case.get('declared_revenue',0):.2f} 万元"),
        ('模拟账户流入金额',('未提供' if case.get('statement_inflow') is None else f"{case['statement_inflow']:.2f} 万元")),
        ('模拟纳税申报销售额',('未提供' if case.get('tax_sales') is None else f"{case['tax_sales']:.2f} 万元")),
        ('贷款用途',case.get('purpose','') or '待补充'),
        ('第一还款来源',case.get('repayment','') or '待补充'),
        ('统计期间及主体口径', '已模拟确认' if result.get('periods_aligned') else '待核实'),
    ]:
        r = table.add_row().cells
        r[0].text, r[1].text = a, str(b)
    doc.add_heading('二、材料核对情况', 1)
    for label in DOC_ITEMS:
        mark = '已勾选' if label in case.get('docs',[]) else '待补充'
        doc.add_paragraph(f'□ {label}  ——  {mark}', style='Normal')
    doc.add_paragraph('“已勾选”仅表示演示中有该类资料记录，不代表原件真实、完整或符合正式业务要求。')
    doc.add_heading('三、模拟规则核查结果', 1)
    for idx, row in enumerate(result['items'],1):
        doc.add_heading(f"{idx}. {row['title']}（{row['level']}）",2)
        doc.add_paragraph(row['detail'] + '  （模拟制度依据：第' + row['clause'] + '条）')
    doc.add_heading('四、偿债压力情景（假设分析）', 1)
    stress = result.get('scenario') or calculate_cashflow_scenario(case, 20)
    doc.add_paragraph(f"假设月可用于偿债现金流下降：{stress['decline_pct']:.0f}%")
    if stress['calculable']:
        t2 = doc.add_table(rows=0, cols=2)
        t2.style = 'Light Shading Accent 1'
        for label, value in [
            ('模拟可用于偿债的月均现金流', f"{stress['cashflow']:.2f} 万元"),
            ('已有债务月偿付额', f"{stress['existing']:.2f} 万元"),
            ('拟新增贷款预计月偿付额', f"{stress['new']:.2f} 万元"),
            ('已录入月债务偿付额合计', f"{stress['monthly_total']:.2f} 万元"),
            ('基准覆盖倍数', f"{stress['baseline_cover']:.2f} 倍"),
            ('情景覆盖倍数', f"{stress['scenario_cover']:.2f} 倍"),
            ('情景现金流减偿付额', f"{stress['scenario_surplus']:+.2f} 万元")]:
            cells = t2.add_row().cells
            cells[0].text = label
            cells[1].text = value
    else:
        doc.add_paragraph('数据不足，未计算偿债覆盖倍数。')
    doc.add_paragraph(stress['message'])
    doc.add_paragraph('该情景仅改变用户输入的假设现金流，不是实际经济预测，也不用于确定准入、额度或审批结果。')
    doc.add_heading('五、人工复核意见与后续动作', 1)
    doc.add_paragraph(note.strip() or '待经办人员补充核查结论、证明材料来源及后续动作。')
    doc.add_paragraph('核查人员：________________      复核日期：________________')
    doc.add_heading('六、使用边界', 1)
    doc.add_paragraph(result['notice'])
    doc.add_paragraph('本文件是用于银行AI创新应用比赛的规则核查模拟样例。所有制度均为虚构演示文本；真实业务请使用正式有效制度、证据及经授权的业务流程。')
    doc.core_properties.title = '微贷慧查贷前尽调模拟核查记录'
    doc.core_properties.subject = '虚构数据演示'
    doc.core_properties.author = '微贷慧查参赛原型'
    buff = BytesIO()
    doc.save(buff)
    return buff.getvalue()
