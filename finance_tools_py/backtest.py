import numpy as np
import pandas as pd
import datetime
import abc
from tqdm.auto import tqdm

class CallBack():
    """回测时的回调。"""

    def __init__(self):
        pass

    @abc.abstractmethod
    def on_check_buy(self,
                     date: datetime.datetime.timestamp,
                     code: str,
                     price: float,
                     cash: float) -> bool:
        """检查是否需要买入。

        Args:
            date: 检查时间。
            code: 股票代码。
            price: 当前价格。
            cash: 持有现金。

        Returns:
            bool: 是否买入。返回 `False`。
        """
        return False

    @abc.abstractmethod
    def on_check_sell(self,
                      date: datetime.datetime.timestamp,
                      code: str,
                      price: float,
                      cash: float,
                      hold_amount: float,
                      hold_price: float) -> bool:
        """检查是否需要卖出。

        Args:
            date: 检查时间。
            code: 股票代码。
            price: 当前价格。
            cash: 持有现金。
            hold_amount: 当前持仓数量。
            hold_price: 当前持仓成本。

        Returns:
            bool: 是否卖出。返回 `False`。
        """
        return False

    @abc.abstractmethod
    def on_calc_buy_amount(self,
                           date: datetime.datetime.timestamp,
                           code: str,
                           price: float,
                           cash: float) -> float:
        """计算买入数量

        Args:
            date: 当前时间。
            code: 股票代码。
            price: 当前价格。
            cash: 持有现金。

        Return:
            float: 返回买入数量。返回 `0`。
        """
        return 0

    @abc.abstractmethod
    def on_calc_sell_amount(self,
                            date: datetime.datetime.timestamp,
                            code: str,
                            price: float,
                            cash: float,
                            hold_amount: float,
                            hold_price: float) -> float:
        """计算卖出数量

        Args:
            date: 当前时间。
            code: 股票代码。
            price: 当前价格。
            cash: 持有现金。
            hold_amount: 当前持仓数量。
            hold_price: 当前持仓成本。

        Return:
            float: 返回卖出数量。返回 `0`。
        """
        return 0


class AHundredChecker(CallBack):
    """每次买入和卖出数量都是100股的回调

    Attributes:
        buy_dict ({str,[datetime.datetime]}): 购买日期字典。key值为股票代码，value值为日期集合。
        sell_dict ({str,[datetime.datetime]}): 卖出日期字典。key值为股票代码，value值为日期集合。
        tax_coeff (float): 印花税费率。默认为 `0.001` 。
        commission_coeff (float): 手续费费率。默认为 `0.001` 。
        min_commission (float): 最小手续费费率。默认为 `5` 。
        min_amount (float): 每次交易最小交易数量。默认为 `100` （股）。
    """

    def __init__(self, buy_dict, sell_dict, **kwargs):
        """初始化

        Args:
            buy_dict ({str,[datetime.datetime]}): 购买日期字典。key值为股票代码，value值为日期集合。
            sell_dict ({str,[datetime.datetime]}): 卖出日期字典。key值为股票代码，value值为日期集合。
            tax_coeff (float): 印花税费率。默认为 `0.001` 。
            commission_coeff (float): 手续费费率。默认为 `0.001` 。
            min_commission (float): 最小手续费费率。默认为 `5` 。
            min_amount (float): 每次交易最小交易数量。默认为 `100` （股）。

        """
        self.buy_dict = buy_dict
        self.sell_dict = sell_dict
        self.tax_coeff = kwargs.pop('tax_coeff', 0.001)
        self.commission_coeff = kwargs.pop('commission_coeff', 0.001)
        self.min_commission = kwargs.pop('min_commission', 5)
        self.min_amount = kwargs.pop('min_amount', 100)

    def on_check_buy(self,
                     date: datetime.datetime.timestamp,
                     code: str,
                     price: float,
                     cash: float) -> bool:
        """当 `date` 及 `code` 包含在参数 :py:attr:`buy_dict` 中时返回 `True` 。否则返回 `False` 。"""
        if code in self.buy_dict.keys() and date in self.buy_dict[code]:
            return True
        else:
            return False

    def on_check_sell(self,
                      date: datetime.datetime.timestamp,
                      code: str,
                      price: float,
                      cash: float,
                      hold_amount: float,
                      hold_price: float) -> bool:
        """当 `date` 及 `code` 包含在参数 :py:attr:`sell_dict` 中时返回 `True` 。否则返回 `False` 。"""
        if code in self.sell_dict.keys() and date in self.sell_dict[code]:
            return True
        else:
            return False

    def _calc_commission(self,
                         price: float,
                         amount: int) -> float:
        """计算交易手续费"""
        return max(price * amount * self.commission_coeff, self.min_commission)

    def _calc_tax(self,
                  price: float,
                  amount: int) -> float:
        """计算印花税"""
        return price * amount * self.tax_coeff

    def on_calc_buy_amount(self,
                           date: datetime.datetime.timestamp,
                           code: str,
                           price: float,
                           cash: float) -> float:
        """计算买入数量。当交易实际花费金额小于 `cash` （可用现金） 时，返回参数 :py:attr:`min_amount` （每次交易数量）。"""
        amount = self.min_amount
        if price * amount + self._calc_commission(price, amount) + self._calc_tax(price, amount) <= cash:
            return amount
        return 0

    def on_calc_sell_amount(self,
                            date: datetime.datetime.timestamp,
                            code: str,
                            price: float,
                            cash: float,
                            hold_amount: float,
                            hold_price: float) -> float:
        """计算卖出数量。
            当 `hold_amount` （当前可用持仓） 大于等于参数 :py:attr:`min_amount` （每次交易数量）时返回参数 :py:attr:`min_amount`（每次交易数量）。
            否则返回 `0`。"""
        if hold_amount >= self.min_amount:
            return self.min_amount
        return 0


class AllInChecker(AHundredChecker):
    """全部资金进入及全部持仓卖出的回调"""

    def on_calc_buy_amount(self,
                           date: datetime.datetime.timestamp,
                           code: str,
                           price: float,
                           cash: float) -> float:
        """计算买入数量。
        根据 `cash` （可用现金）及 `price` （当前价格）计算实际可以买入的数量（参数 :py:attr:`min_amount` 的倍数）
            （计算时包含考虑了交易时可能产生的印花税和手续费）
        """
        amount = self.min_amount
        while price * amount + self._calc_commission(price, amount) + self._calc_tax(price, amount) <= cash:
            amount = amount + self.min_amount
        amount = amount - self.min_amount
        return amount

    def on_calc_sell_amount(self,
                            date: datetime.datetime.timestamp,
                            code: str,
                            price: float,
                            cash: float,
                            hold_amount: float,
                            hold_price: float) -> float:
        """计算买入数量
        直接返回 `hold_amount` 。表示全部可以卖出。"""
        return hold_amount


class BackTest():
    """简单的回测系统。根据传入的购买日期和卖出日期，计算收益。

    Example:
        >>> from datetime import date
        >>> import pandas as pd
        >>> from finance_tools_py.backtest import BackTest
        >>> from finance_tools_py.backtest import AHundredChecker
        >>> 
        >>> data = pd.DataFrame({
        >>>     'code': ['000001' for x in range(4)],
        >>>     'date': [date(1998, 1, 1), date(1999, 1, 1), date(2000, 1, 1), date(2001, 1, 1)],
        >>>     'close': [4.5, 7.9, 6.7, 10],
        >>> })
        >>> bt = BackTest(data, init_cash=1000, callbacks=[AHundredChecker(
        >>>     buy_dict={'000001': [date(1998, 1, 1), date(2000, 1, 1)]},
        >>>     sell_dict={'000001': [date(1999, 1, 1)]})])
        >>> bt.calc_trade_history()
        >>> print(bt.report())
        数据时间:1998-01-01~2001-01-01（可交易天数4）
        初始资金:1000.00
        交易次数:3 (买入/卖出各算1次)
        可用资金:653.09
        当前持仓:code
        000001    (6.7, 100.0)
        当前总资产:1323.09
        资金变化率:65.31%
        资产变化率:132.31%
        总手续费:15.00
        总印花税:1.91
        交易历史：
             datetime    code  price  amount     cash  commission   tax   total  toward
        0  1998-01-01  000001    4.5     100   544.55           5  0.45  455.45       1
        1  1999-01-01  000001    7.9    -100  1328.76           5  0.79  795.79      -1
        2  2000-01-01  000001    6.7     100   653.09           5  0.67  675.67       1

    """

    def __init__(self,
                 data,
                 init_cash=10000,
                 tax_coeff=0.001,
                 commission_coeff=0.001,
                 min_commission=5,
                 col_name='close',
                 callbacks=[CallBack()]):
        """初始化

        Args:
            data (:py:class:`pandas.DataFrame`): 完整的日线数据。数据中需要包含 `date` 列，用来标记日期。
                数据中至少需要包含 `date` 列、 `code` 列和 `close` 列，其中 `close` 列可以由参数 `colname` 参数指定。
            init_cash (float): 初始资金。
            tax_coeff (float): 印花税费率。默认0.001。
            commission_coeff (float): 手续费率。默认0.001。
            min_commission (float): 最小印花税费。默认5。
            col_name (str): 计算用的列名。默认为 `close` 。
                这个列名必须包含在参数 `data` 中。是用来进行回测计算的列，用来标记回测时使用的价格数据。
            callbacks ([:py:class:`finance_tools_py.backtest.CallBack`]): 回调函数集合。
        """
        self._min_buy_amount = 100  # 单次可买最小数量
        self.data = data
        self.init_cash = init_cash
        self.cash = [init_cash]  # 资金明细
        self.tax_coeff = tax_coeff
        self.commission_coeff = commission_coeff
        self.min_commission = min_commission
        self.history = []  # 交易历史
        self._init_hold = pd.Series([], name='amount')
        self._init_hold.index.name = 'code'
        self._calced = False
        self._colname = col_name
        self._calbacks = callbacks
        self._hold_price_cur = pd.DataFrame()
        self._history_headers = [
            'datetime',  # 时间
            'code',  # 代码
            'price',  # 成交价
            'amount',  # 成交量
            'cash',  # 剩余现金
            'commission',  # 手续费
            'tax',  # 印花税
            'total',  # 总金额
            'toward',  # 方向
        ]
        # self.hold_amount=[]#当前持仓数量
        # self.hold_price=[]#当前持仓金额

    @property
    def history_df(self):
        """获取成交历史的 :py:class:`pandas.DataFrame` 格式。"""
        if len(self.history) > 0:
            lens = len(self.history[0])
        else:
            lens = len(self._history_headers)

        return pd.DataFrame(
            data=self.history,
            columns=self._history_headers[:lens]
        ).sort_index()

    @property
    def available_hold_df(self):
        """获取可用持仓

        Returns:
            :py:class:`pandas.Series`
        """
        return self.history_df.groupby('code').amount.sum().replace(
            0,
            np.nan
        ).dropna().sort_index()

    # @property
    # def trade(self):
    #     """每次交易的pivot表
    #     Returns:
    #         pd.DataFrame
    #         此处的pivot_table一定要用np.sum
    #     """
    #
    #     return self.history_df.pivot_table(
    #         index=['datetime'],
    #         columns='code',
    #         values='amount',
    #         aggfunc=np.sum
    #     ).fillna(0).sort_index()

    def __hold_price_cur(self):
        """计算目前持仓的成本。

        因为这个属性可能会频繁调用apply，造成性能极低。所以改为内部属性。

        Returns:
            :py:class:`pandas.Series`
        """

        def weights(x):
            n = len(x)
            res = 1
            while res > 0 or res < 0:
                res = sum(x[:n]['amount'])
                n = n - 1

            x = x[n + 1:]

            if sum(x['amount']) != 0:
                return np.average(x['price'], weights=x['amount'], returned=True)
            else:
                return np.nan

        return self.history_df.set_index('datetime', drop=False).sort_index().groupby('code').apply(weights).dropna()

    @property
    def hold_price_cur(self):
        """目前持仓的成本。是 :py:class: `pandas.Series` 类型或 :py:class: `pandas.DataFrame` 类型。
            其中 `code` 是索引，通过索引访问会返回一个数组（price,amount）"""
        return self._hold_price_cur

    def _update_hold_price_cur(self):
        self._hold_price_cur = self.__hold_price_cur()

    def hold_time(self, dt=None):
        """持仓时间。根据参数 `dt` 查询截止时间之前的交易，并与当前时间计算差异。

        Args:
            dt (datetime): 交易截止时间。如果为 `None` 则表示计算所有交易。默认为 `None` 。

        Returns:
            :py:class:`pandas.DataFrame`
        """

        def weights(x):
            if sum(x['amount']) != 0:
                return pd.Timestamp(datetime.datetime.today()) - pd.to_datetime(x.datetime.max())
            else:
                return np.nan

        if datetime is None:
            return self.history_df.set_index(
                'datetime',
                drop=False
            ).sort_index().groupby('code').apply(weights).dropna()
        else:
            return self.history_df.set_index(
                'datetime',
                drop=False
            ).sort_index().loc[:dt].groupby('code').apply(weights).dropna()

    @property
    def total_assets_cur(self) -> float:
        """获取当前总资产

        当前可用资金+当前持仓。
        """
        return self.available_cash + sum([x[0] * x[1] for x in self.hold_price_cur])

    # def hold_table(self, datetime=None):
    #     """到某一个时刻的持仓 如果给的是日期,则返回当日开盘前的持仓"""
    #     if datetime is None:
    #         hold_available = self.history_df.set_index(
    #             'datetime'
    #         ).sort_index().groupby('code').amount.sum().sort_index()
    #     else:
    #         hold_available = self.history_df.set_index(
    #             'datetime'
    #         ).sort_index().loc[:datetime].groupby('code').amount.sum().sort_index()
    #
    #     return pd.concat([self._init_hold,
    #                       hold_available]).groupby('code').sum().sort_index(
    #     )

    @property
    def available_cash(self) -> float:
        """获取当前可用资金"""
        return self.cash[-1]

    def _calc_commission(self, price, amount) -> float:
        """计算交易手续费"""
        return max(price * amount * self.commission_coeff, self.min_commission)

    def _calc_tax(self, price, amount) -> float:
        """计算印花税"""
        return price * amount * self.tax_coeff

    def _check_callback_buy(self, date, code, price) -> bool:
        for cb in self._calbacks:
            if cb.on_check_buy(date, code, price, self.available_cash):
                return True
        return False

    def _check_callback_sell(self, date, code, price) -> bool:
        for cb in self._calbacks:
            hold_amount, hold_price = 0, 0
            if not self.hold_price_cur.empty and code in self.hold_price_cur.index:
                hold_price, hold_amount = self.hold_price_cur[code]
            if cb.on_check_sell(date, code, price, self.available_cash, hold_amount, hold_price):
                return True
        return False

    def _calc_buy_amount(self, date, code, price) -> float:
        for cb in self._calbacks:
            amount = cb.on_calc_buy_amount(date, code, price, self.available_cash)
            if amount:
                return amount
        return 0

    def _calc_sell_amount(self, date, code, price) -> float:
        for cb in self._calbacks:
            if not self.hold_price_cur.empty and code in self.hold_price_cur.index:
                hold_price, hold_amount = self.hold_price_cur[code]
                amount = cb.on_calc_sell_amount(date, code, price, self.available_cash, hold_amount, hold_price)
                if amount:
                    return amount
        return 0

    def calc_trade_history(self, verbose=0):
        """计算交易记录

        Args:
            verbose (int): 是否显示计算过程。0（不显示），1（显示部分），2（显示全部）。默认为0。
        """

        def update_history(history, date, code, price, amount, available_cash, commission, tax, toward):
            history.append([
                date,  # 时间
                code,  # 代码
                price,  # 成交价
                amount * toward,  # 成交量
                available_cash,  # 剩余现金
                commission,  # 手续费
                tax,  # 印花税
                price * amount + commission + tax,  # 总金额
                toward,  # 方向
            ])

        for index, row in tqdm(self.data.iterrows()):
            date = row['date']
            code = row['code']
            price = row['close']  # 价格
            if self._check_callback_buy(date, code, price):
                amount = self._calc_buy_amount(date, code, price)  # 买入数量
                commission = self._calc_commission(price, amount)
                tax = self._calc_tax(price, amount)
                value = price * amount + commission + tax
                if value <= self.available_cash and amount > 0:
                    self.cash.append(self.available_cash - value)
                    update_history(self.history,
                                   date,
                                   code,
                                   price,
                                   amount,
                                   self.cash[-1],
                                   commission,
                                   tax,
                                   1, )
                    self._update_hold_price_cur()
                    if verbose > 0:
                        print('{:%Y-%m-%d} {} 买入 {:.2f}/{:.2f}，剩余资金 {:.2f}'.format(date, code, price, amount,
                                                                                   self.available_cash))
                else:
                    if verbose > 1:
                        print('{:%Y-%m-%d} {} {:.2f} 可用资金不足，跳过购买。'.format(date, code, price))
            if self._check_callback_sell(date, code, price):
                amount = self._calc_sell_amount(date, code, price)
                if amount > 0:
                    commission = self._calc_commission(price, amount)
                    tax = self._calc_tax(price, amount)
                    value = price * amount - commission - tax
                    self.cash.append(self.available_cash + value)
                    update_history(self.history,
                                   date,
                                   code,
                                   price,
                                   amount,
                                   self.cash[-1],
                                   commission,
                                   tax,
                                   -1, )
                    self._update_hold_price_cur()
                    if verbose > 0:
                        print('{:%Y-%m-%d} {} 卖出 {:.2f}/{:.2f}，剩余资金 {:.2f}'.format(date, code, price, amount,
                                                                                   self.available_cash))
                else:
                    if verbose > 1:
                        print('{:%Y-%m-%d} {} 没有持仓，跳过卖出。'.format(date, code))
        if verbose > 0:
            print('计算完成！')
        self._calced = True

    def _calc_total_tax(self) -> float:
        return np.asarray(self.history).T[6].sum() if len(self.history) > 0 else 0

    def _calc_total_commission(self) -> float:
        return np.asarray(self.history).T[5].sum() if len(self.history) > 0 else 0

    def report(self):
        """获取计算结果

        Returns:
            str: 返回计算结果。
        """
        result = ''
        if not self._calced:
            result = '没有经过计算。请先调用 `calc_trade_history` 方法进行计算。'
            return result
        result = '数据时间:{}~{}（可交易天数{}）'.format(self.data.iloc[0]['date'], self.data.iloc[-1]['date'],
                                              len(self.data['date'].unique()))
        result = result + '\n初始资金:{:.2f}'.format(self.init_cash)
        result = result + '\n交易次数:{} (买入/卖出各算1次)'.format(len(self.history))
        result = result + '\n可用资金:{:.2f}'.format(self.available_cash)
        result = result + '\n当前持仓:'
        if not self.hold_price_cur.empty:
            result = result + self.hold_price_cur.to_string()
        else:
            result = result + '无'
        result = result + '\n当前总资产:{:.2f}'.format(self.total_assets_cur)
        result = result + '\n资金变化率:{:.2%}'.format(self.available_cash / self.init_cash)
        result = result + '\n资产变化率:{:.2%}'.format(self.total_assets_cur / self.init_cash)
        result = result + '\n总手续费:{:.2f}'.format(self._calc_total_commission())
        result = result + '\n总印花税:{:.2f}'.format(self._calc_total_tax())
        result = result + '\n交易历史：\n'
        result = result + self.history_df.sort_values('datetime').to_string()
        return result
