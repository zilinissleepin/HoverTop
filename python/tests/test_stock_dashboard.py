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


from unittest.mock import MagicMock

from stock_dashboard import fetch_quotes


class _FakeResp:
    def __init__(self, content: bytes, status: int = 200) -> None:
        self.content = content
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_fetch_quotes_cn_parses_gbk(monkeypatch):
    body = (
        'var hq_str_sh600519="贵州茅台,1630.00,1630.00,1650.00,1660.00,1620.00,a,b";\n'
        'var hq_str_sz000001="平安银行,12.00,12.50,12.45,12.60,12.30,a,b";\n'
    ).encode("gbk")

    fake_get = MagicMock(return_value=_FakeResp(body))
    monkeypatch.setattr("stock_dashboard.requests.get", fake_get)

    result = fetch_quotes(["sh600519", "sz000001"], market="cn")
    assert set(result.keys()) == {"sh600519", "sz000001"}
    assert result["sh600519"]["name"] == "贵州茅台"
    assert result["sz000001"]["price"] == pytest.approx(12.45)

    # 确认带了 Referer 头
    _, kwargs = fake_get.call_args
    assert kwargs["headers"]["Referer"] == "https://finance.sina.com.cn"


def test_fetch_quotes_empty_list_no_request(monkeypatch):
    fake_get = MagicMock()
    monkeypatch.setattr("stock_dashboard.requests.get", fake_get)
    result = fetch_quotes([], market="cn")
    assert result == {}
    fake_get.assert_not_called()


def test_fetch_quotes_request_error_returns_empty(monkeypatch, capsys):
    fake_get = MagicMock(side_effect=RuntimeError("network down"))
    monkeypatch.setattr("stock_dashboard.requests.get", fake_get)
    result = fetch_quotes(["sh600519"], market="cn")
    assert result == {}
    # 错误打到 stderr
    err = capsys.readouterr().err
    assert "network down" in err


from stock_dashboard import format_price, format_change_pct


def test_format_price_large():
    assert format_price(1650.0) == "1,650.00"


def test_format_price_small():
    assert format_price(0.1234) == "0.1234"


def test_format_price_zero():
    assert format_price(0.0) == "0"


def test_format_change_pct_positive():
    assert format_change_pct(1.23) == "+1.23%"


def test_format_change_pct_negative():
    assert format_change_pct(-0.80) == "-0.80%"


def test_format_change_pct_zero():
    assert format_change_pct(0.0) == "+0.00%"
