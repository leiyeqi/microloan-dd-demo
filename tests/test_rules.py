import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rules import DEMO_CASES, DOC_ITEMS, evaluate, load_policy
from report import build_docx
from docx import Document
from io import BytesIO


def test_policy():
    assert load_policy()['id']=='CORP-LOAN-001'


def test_difference_detected_without_credit_decision():
    r=evaluate(DEMO_CASES['收入差异案例'])
    assert any(x['code']=='STMT-GAP' for x in r['items'])
    assert r['comparisons'][0]['difference']==220.0
    assert not any('批准贷款' in x['detail'] or '拒贷' in x['detail'] for x in r['items'])


def test_missing_doc():
    r=evaluate(DEMO_CASES['材料缺失案例'])
    assert r['missing_docs']
    assert any(x['code']=='REPAY-MISSING' for x in r['items'])
    assert any(x['code']=='TAX-MISSING' for x in r['items'])


def test_complete_case_has_no_missing_docs():
    r=evaluate(DEMO_CASES['资料较完整案例'])
    assert not r['missing_docs']
    assert any(x['code']=='STMT-COMPARED' for x in r['items'])


def test_report_docx():
    case=DEMO_CASES['收入差异案例']
    blob=build_docx(case,evaluate(case),'模拟核实后补充')
    d=Document(BytesIO(blob))
    text='\n'.join(p.text for p in d.paragraphs)
    assert '微贷慧查' in text and '模拟核实后补充' in text
    assert '差异' in text
