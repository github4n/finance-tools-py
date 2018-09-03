# Copyright (C) 2018 GuQiangJs.
# Licensed under Apache License 2.0 <see LICENSE file>

import unittest

from finance_datareader_py.sohu.daily import SohuDailyReader

from finance_tools_py.calculate import *


class CalculateTestCase(unittest.TestCase):
    def test_daily_return(self):
        df = SohuDailyReader('000300', prefix='zs_').read()['Close']
        self.assertFalse(df.empty)
        df1 = daily_returns(df)
        self.assertFalse(df1.empty)
        print(df.sort_index().tail())
        print(df1.tail())
        # 2018-08-15    3291.98
        # 2018-08-16    3276.73
        # 2018-08-17    3229.62
        # 2018-08-20    3267.25
        # 2018-08-21    3326.65
        self.assertEqual(np.around((df1['2018-08-16']), decimals=6),
                         np.around((3276.73 / 3291.98 - 1), decimals=6))
        self.assertEqual(np.around((df1['2018-08-20']), decimals=6),
                         np.around((3267.25 / 3229.62 - 1), decimals=6))
        self.assertEqual(np.around((df1['2018-08-21']), decimals=6),
                         np.around((3326.65 / 3267.25 - 1), decimals=6))

    def test_cum_returns(self):
        data = [1, 2, 3, 4, 5]
        corr = (5 / 1) - 1
        df = pd.DataFrame(data)
        cum = cum_returns(df)
        self.assertEqual(cum, corr)
        column_name = 'A'
        df = pd.DataFrame({column_name: data})
        cum1 = cum_returns(df, column_name)
        cum2 = cum_returns(df)
        self.assertEqual(cum1, cum2)
        self.assertEqual(cum1, corr)

    def test_daily_returns_avg(self):
        data = [1, 2, 3, 4, 5]
        df = pd.DataFrame(data)
        self.assertEqual(daily_returns_avg(df)[0], daily_returns(df).mean()[0])

    def test_daily_returns_std(self):
        data = [1, 2, 3, 4, 5]
        df = pd.DataFrame(data)
        self.assertEqual(daily_returns_std(df)[0], daily_returns(df).std()[0])

    def test_risk_free_interest_rate(self):
        # 年化收益 5%，持有 30 天，本金 10000。月均收益应该为 41.1
        risk = risk_free_interest_rate(0.05, 365)
        # print(risk)
        # print(risk * 30 * 10000)
        # print(np.around((risk * 30 * 10000), decimals=2))
        # print(np.around(41.1, decimals=2))
        self.assertEqual(np.around((risk * 30 * 10000), decimals=2),
                         np.around(41.1, decimals=2))

    def test_sharpe_ratio(self):
        """测试夏普比率计算"""
        # 假设你希望你的股票投资组合，返回12％，明年全年。
        # 如果无风险国债收益票据的，比如说5％，你的投资组合带有0.06标准偏差，
        # 然后从上面的公式，我们可以计算出的夏普比率为你的投资组合是：
        # （0.12 - 0.05） / 0.06 = 1.17
        # 这意味着对于每个回报点，您承担1.17“单位”的风险。
        sr = sharpe_ratio(0.12, 0.05, 0.06)
        self.assertIsInstance(sr, float)
        self.assertEqual(np.around(sr, decimals=2), 1.17)

        lst = []
        for i in range(100):
            lst.append(sharpe_ratio(pd.DataFrame(np.random.normal(0.12, 0.06,
                                                                  10)), 0.05))

        sr = sharpe_ratio(pd.DataFrame([0.0100, -0.0100, 0.0300, 0.0400,
                                        -0.0200, -0.0100]), 0)
        self.assertIsInstance(sr, float)
        self.assertEqual(np.around(sr, decimals=6), 0.275241)

    def test_mo(self):
        """测试 MO运动量震荡指标 (Momentum Oscillator)"""
        max = 10
        min = 1
        n = 3
        # 模拟计算开始
        lst = np.arange(min, max)
        lst_1 = []
        for i in range(n, max - min):
            lst_1.append((lst[i] / lst[i - n]) * 100)
        # 模拟计算结束
        _mo = mo(pd.DataFrame(np.arange(min, max)), n)
        _mo = _mo.dropna()
        self.assertFalse(_mo.empty)
        self.assertEqual(_mo.index.size, max - min - n)
        # mo方法结果应该和模拟计算结果一致
        self.assertTrue(np.array_equal(_mo[0].values, np.array(lst_1)))
        # print(__mo)
        self.assertEqual(mo(pd.DataFrame(np.arange(min, max)),
                            n, dropna=True).index.size, max - min - n)

    def test_beta(self):
        symbol_code = '300104'
        market_code = '000300'
        df = pd.DataFrame()
        df[market_code] = SohuDailyReader(market_code, prefix='zs_').read()[
            'Close']
        df = df.join(SohuDailyReader(symbol_code).read()['Close'])
        df = df.rename(columns={'Close': symbol_code})
        df = df.sort_index()
        df = df.fillna(method='ffill')
        df_dr = daily_returns(df)
        b, a = beta_alpha(df_dr, m_name=market_code, s_name=symbol_code)
        print(b, a)
        b_np, a_np = np.polyfit(df_dr[market_code], df_dr[symbol_code], 1)
        print(b_np, a_np)
        self.assertEqual(np.around(b, decimals=8), np.around(b_np, decimals=8))
        self.assertEqual(np.around(a, decimals=8), np.around(a_np, decimals=8))

    def test_sma(self):
        """测试简单移动平均计算"""
        symbol_code = '300104'
        market_code = '000300'
        df = pd.DataFrame()
        df[market_code] = SohuDailyReader(market_code, prefix='zs_').read()[
            'Close']
        df = df.join(SohuDailyReader(symbol_code).read()['Close'])
        df = df.rename(columns={'Close': symbol_code})
        df_sma = sma(df, 5)
        self.assertFalse(df_sma.empty)
        print(df.sort_index().tail())
        print(df_sma.tail())

    def test_ema(self):
        """测试简单移动平均计算"""
        symbol_code = '300104'
        market_code = '000300'
        df = pd.DataFrame()
        df[market_code] = SohuDailyReader(market_code, prefix='zs_').read()[
            'Close']
        df = df.join(SohuDailyReader(symbol_code).read()['Close'])
        df = df.rename(columns={'Close': symbol_code})
        df_sma = ema(df)
        self.assertFalse(df_sma.empty)
        print(df.sort_index().tail())
        print(df_sma.tail())

    def test_momentum(self):
        """测试 动量指标 (momentum)"""
        max = 10
        min = 1
        n = 3
        # 模拟计算开始
        lst = np.arange(min, max)
        lst_1 = []
        for i in range(n, max - min):
            lst_1.append(lst[i] - lst[i - n])
        # 模拟计算结束
        _mo = momentum(pd.DataFrame(np.arange(min, max)), n, True)
        self.assertFalse(_mo.empty)
        self.assertEqual(_mo.index.size, max - min - n)
        # 结果应该和模拟计算结果一致
        self.assertTrue(np.array_equal(_mo[0].values, np.array(lst_1)))
        # print(__mo)
        self.assertEqual(mo(pd.DataFrame(np.arange(min, max)),
                            n, dropna=True).index.size, max - min - n)


if __name__ == '__main__':
    unittest.main()
