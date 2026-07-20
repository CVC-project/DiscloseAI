from scripts.fetch_krx_listed_tickers import parse_krx_tickers


def test_parse_krx_tickers_uses_stock_code_column_only():
    html = """
    <table>
      <tr><th>Company</th><th>Market</th><th>Ticker</th></tr>
      <tr><td>Samsung</td><td>KOSPI</td><td>005930</td></tr>
      <tr><td>Example</td><td>KOSDAQ</td><td>123456</td></tr>
      <tr><td>Preferred</td><td>KOSPI</td><td>005935</td></tr>
      <tr><td>Invalid</td><td>KOSPI</td><td>0039P0</td></tr>
    </table>
    """
    assert parse_krx_tickers(html) == ["005930", "005935", "123456"]
