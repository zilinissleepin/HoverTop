"""stock_dashboard 解析与排序的单元测试。"""
from __future__ import annotations

import pytest

from stock_dashboard import Quote, parse_cn_line


def test_parse_cn_line_normal():
    line = 'var hq_str_sh600519="贵州茅台,1630.00,1630.00,1650.00,1660.00,1620.00,extra,fields";'
    q = parse_cn_line("sh600519", line)
    assert q is not None
    assert q["name"] == "贵州茅台"
    assert q["price"] == pytest.approx(1650.00)
    # 涨跌幅 = (1650 - 1630) / 1630 * 100 ≈ 1.2270
    assert q["change_pct"] == pytest.approx((1650.00 - 1630.00) / 1630.00 * 100)


def test_parse_cn_line_empty_payload():
    # 无效代码时新浪返回 var hq_str_xxx="";
    line = 'var hq_str_sh999999="";'
    assert parse_cn_line("sh999999", line) is None


def test_parse_cn_line_zero_prev_close():
    # 昨收为 0 时避免除零
    line = 'var hq_str_sh000000="测试,0.00,0.00,0.00,0.00,0.00,a,b";'
    q = parse_cn_line("sh000000", line)
    assert q is None
