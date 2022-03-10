"""
VIX Strategy using hourly RSI 
(which is used as momentum indicator rather than a contrarian)
"""

import numpy as np; import pandas as pd
from datetime import datetime, timedelta
import decimal
import talib

class VIXbyRSI(QCAlgorithm):
    
    def __init__(self):
        self._period = 6
        self.perc_pos = 1.0 # just need something ~0.3 for enough fun
        
    def Initialize(self):
        self.SetCash(100000)
        self.SetStartDate(2018,5,1) # Note that backtesting this strategy to dates earlier than March 2018 will not be consistent as after Feb 5, 2018 the SVXY was deleveraged from x2 to x0.5
        # self.SetEndDate(datetime.now().date())
        
        self.first_time = True
        self.RSI_previous = None

        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)
        
        self.SVXY = self.AddEquity("SVXY", Resolution.Hour).Symbol # Short Volatility
        self.VXX = self.AddEquity("VXX", Resolution.Hour).Symbol

        self._RSI = self.RSI(self.SVXY, self._period, MovingAverageType.Simple, Resolution.Hour)
        self.Plot("Indicators", self._RSI)
        
        # Set Benchmark        
        self.SetBenchmark('SPY')
        
        # Set Rebalancing Check Every 2 hours
        self.Schedule.On(self.DateRules.EveryDay(self.SVXY), self.TimeRules.Every(timedelta(minutes=120)), self.rebalance)

    def OnData(self, data):
        pass

    def rebalance(self): # every two hours

        # wait if still open orders
        if len(self.Transactions.GetOpenOrders())>0: return
        
        # wait for i. indicator warm up 
        if (not self._RSI.IsReady):
            if self.first_time:    # update RSI previous
                self.RSI_previous = self._RSI.Current.Value
                self.first_time = False
            return
        
        # update RSI
        RSI_curr = self._RSI.Current.Value
        self.Log(str(self.Time)+" RSI: "+ str(RSI_curr))
    
        # get current qnties
        SVXY_qnty = self.Portfolio[self.SVXY].Quantity
        VXX_qnty = self.Portfolio[self.VXX].Quantity
       
        # SVXY positions
        if self.RSI_previous > 85 and RSI_curr <= 85: # down and below 85 (OVERBOUGHT): SELL
            if SVXY_qnty > 0:
                self.Liquidate(self.SVXY)
            if VXX_qnty == 0:
                self.SetHoldings(self.VXX, self.perc_pos)
        if self.RSI_previous < 70 and RSI_curr >= 70: # up and above 70: BUY
            if SVXY_qnty == 0:
                self.SetHoldings(self.SVXY, self.perc_pos)
                # Set stop loss sell order when the price moves 4% against. Note. .Close means the last SVXY value based on the resolution
                #self.StopMarketOrder(self.SVXY, -self.perc_pos, self.Securities["SVXY"].Close * 0.96)
            if VXX_qnty > 0:
                self.Liquidate(self.VXX)
       
        # VXX positions
        if self.RSI_previous > 30 and RSI_curr <= 30: # down and below 30 (OVERSOLD): BUY
            if SVXY_qnty > 0:
                self.Liquidate(self.SVXY)
                #self.LimitOrder(self.SVXY, self.perc_pos, self.Securities["SVXY"].Close * 1.04)
            if VXX_qnty == 0:
                self.SetHoldings(self.VXX, self.perc_pos)
                #self.StopMarketOrder(self.VXX, self.perc_pos, self.Securities["VXX"].Close * 0.96)

        if self.RSI_previous < 15 and RSI_curr >= 15: # up and above 15: SELL
            if VXX_qnty > 0:
                self.Liquidate(self.VXX)
            if SVXY_qnty == 0:
                self.SetHoldings(self.SVXY, self.perc_pos)
                #self.StopMarketOrder(self.SVXY, -self.perc_pos, self.Securities["SVXY"].Close * 0.96)

        self.RSI_previous = RSI_curr
