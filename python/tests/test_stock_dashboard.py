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


from stock_dashboard import parse_hk_line


def test_parse_hk_line_normal():
    # fields: 英文名, 中文名, 今开, 昨收, 最高, 最低, 当前价, ...
    line = 'var hq_str_hk00700="TENCENT,腾讯控股,378.00,380.00,382.00,376.00,381.00,extra";'
    q = parse_hk_line("hk00700", line)
    assert q is not None
    assert q["name"] == "腾讯控股"
    assert q["price"] == pytest.approx(381.00)
    assert q["change_pct"] == pytest.approx((381.00 - 380.00) / 380.00 * 100)


def test_parse_hk_line_fallback_to_english_name():
    line = 'var hq_str_hk00700="TENCENT,,378.00,380.00,382.00,376.00,381.00,extra";'
    q = parse_hk_line("hk00700", line)
    assert q is not None
    assert q["name"] == "TENCENT"


def test_parse_hk_line_empty_payload():
    line = 'var hq_str_hk99999="";'
    assert parse_hk_line("hk99999", line) is None


from stock_dashboard import parse_us_line


def test_parse_us_line_normal():
    # [0]名称 [1]当前价 [2]涨跌幅 [3]日期, 后面字段省略
    line = 'var hq_str_gb_aapl="Apple Inc,175.50,0.8614,2026-05-08 09:30:00,...";'
    q = parse_us_line("gb_aapl", line)
    assert q is not None
    assert q["name"] == "Apple Inc"
    assert q["price"] == pytest.approx(175.50)
    assert q["change_pct"] == pytest.approx(0.8614)


def test_parse_us_line_negative_change():
    line = 'var hq_str_gb_tsla="Tesla Inc,245.00,-2.30,2026-05-08 09:30:00,...";'
    q = parse_us_line("gb_tsla", line)
    assert q is not None
    assert q["change_pct"] == pytest.approx(-2.30)


def test_parse_us_line_empty_payload():
    line = 'var hq_str_gb_xxxx="";'
    assert parse_us_line("gb_xxxx", line) is None
