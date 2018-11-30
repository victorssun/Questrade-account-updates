# -*- coding: utf-8 -*-
"""
Created on Thu Apr 26 00:33:45 2018

@author: A
Run script at night. 6pm. Maintence usually from 9pm-3am
Grab daily portfolio and balances data
Save to pickle file: positions_daily2, balances_daily2

Grab net profit data and currency exchanges every Friday
Save to pickle file: list_returns
"""
import sys
import os
if os.name == 'nt':
    sys.path.append('C:/Users/name/Questrade_API/')
elif os.name == 'posix':
    sys.path.append('/mnt/name/Questrade_API/')
from questrade import *
import pickle, datetime, pandas as pd
import numpy as np
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

def save(data, filename):
    # save positions, balances data to pickle file if global variable autosave is True
    if autosave == True:
        pickle.dump(data, open(filename, 'wb'))
        print('%s. saved' %filename)
    elif raw_input('save %s? (y/n): ' %filename) == 'y':
        pickle.dump(data, open(filename, 'wb'))
        print('%s. saved' %filename)
    else:
        print('not saved')

def account_daily(direct_data, token): 
    # grab positions and balances data and saves to a single pickle file
    
    ex = token.ex_rate() # grab USD/CAD Ex. rate
    today_date = datetime.date.today() # grab the day
    # load pickled positions/balances data
    positions_daily2, balances_daily2 = pickle.load(open('%saccount_daily.pickle' %direct_data, 'rb'))
#    positions_daily2, balances_daily2 = pd.DataFrame(), pd.DataFrame() # if want to make a new dataframe
    save([positions_daily2, balances_daily2], filename='%sdaily pickles/account_daily_%s.pickle' %(direct_data, datetime.date.today()))
    
    # grab positions data every 24 hours
    symbols = []
    currentValues = []
    dates = [today_date] # add initial date for appended cash value
    for i in range(len(token.positions()[0])): # for each current position 
        if token.positions()[0][i]['currentMarketValue'] >= 0: # if (all shares of) current position is not sold
            dates.append(today_date)
            symbol2 = str(token.positions()[0][i]['symbol'])
            symbols.append(symbol2)
            if symbol2.find('.TO') != -1:
                currentValues.append(token.positions()[0][i]['currentMarketValue'])
            else: # if stock in USD
                currentValues.append(token.positions()[0][i]['currentMarketValue'] * ex)
        else:
            print('%s skipped/sold.' %token.positions()[0][i]['symbol'])
    cash = token.balances()[0]['combinedBalances'][0]['cash'] # sod or eod, which one is more accurate?
    symbols.append('cash') 
    currentValues.append(cash) # append cash
    # append positions data to ongoing dataframe: date, symbol, market value
    positions_daily = pd.DataFrame({'date': dates, 'symbol': symbols, 'value': currentValues})
    positions_daily2 = positions_daily2.append(positions_daily)
    
    # grab balance data every 24 hours
    balances_daily = token.balances()[0]['combinedBalances'][0]
    balances_daily = [balances_daily.get(key) for key in ['cash', 'marketValue', 'totalEquity']]
    balances_daily.append(ex)
    balances_daily.append(today_date)
    balances_daily = pd.DataFrame(balances_daily).T
    balances_daily.columns = ['cash', 'marketValue', 'totalEquity', 'exchangeRate', 'date']
    # append balance data to ongoing dataframe: cash, stock holdings value, total, exchange rate, date
    balances_daily2 = balances_daily2.append(balances_daily)
    
    # save positions/balances data
    print balances_daily2.tail(7)
    save([positions_daily2, balances_daily2], filename='%sdaily pickles/account_daily.pickle' %(direct_data))
    save([positions_daily2, balances_daily2], '%saccount_daily.pickle' %direct_data)
    return positions_daily2, balances_daily2


def account_profits(direct_data, token):
    # load list_returns
    list_returns = pickle.load(open('%saccount_profits.pickle' %direct_data, 'rb'))
    save(list_returns, filename='%sdaily pickles/account_profits_%s.pickle' %(direct_data, datetime.date.today()))
    ex_rate1 = token.ex_rate() # get current exchange rate
    
    # create filtered exec list
    execlist = token.executions()[0] # newest to oldest
    execlist2 = []
    key_list = ['symbol', 'side', 'totalCost', 'quantity', 'price', 'commission', 'secFee', 'executionFee', 'canadianExecutionFee']
    for e in execlist: # for each execution, append the desired keys to dataframe
        execlist2.append([e.get(key) for key in key_list])
    df = pd.DataFrame(execlist2)
    df.columns = key_list
    
    # determine dividends and exchange rate accumulation
    df_dividends, netProfit_cad = ex_profits_dividends(21)
    
    # append dividends to df to sum stock profits
    df = pd.concat([df, df_dividends])
    
    # convert HMLSF to HMMJ.TO, need to update if journalling over different shares
    df_HMLSF = df[df['symbol']=='HMLSF']
    test2 = df[['totalCost', 'price', 'commission', 'secFee', 'executionFee', 'canadianExecutionFee']][df['symbol']=='HMLSF'] * ex_rate1
    df_HMLSF[['totalCost', 'price', 'commission', 'secFee', 'executionFee', 'canadianExecutionFee']] = test2 # convert USD values to CAD and append new exec
    df_HMLSF['symbol'] = 'HMMJ.TO'
    df = df.append(df_HMLSF)
    df = df[df['symbol']!='HMLSF'] # remove USD's HMLSF
    
    # convert HMMJ.U.TO to HMMJ.TO
    df_HMLSF2 = df[df['symbol']=='HMMJ.U.TO']
    test2 = df[['totalCost', 'price', 'commission', 'secFee', 'executionFee', 'canadianExecutionFee']][df['symbol']=='HMMJ.U.TO'] * ex_rate1
    df_HMLSF2[['totalCost', 'price', 'commission', 'secFee', 'executionFee', 'canadianExecutionFee']] = test2 # convert USD values to CAD and append new exec
    df_HMLSF2['symbol'] = 'HMMJ.TO'
    df = df.append(df_HMLSF2)
    df = df[df['symbol']!='HMMJ.U.TO'] # remove USD's HMLSF
    
    # create list of summarized stocks and their profits
    returns = pd.DataFrame()
    for e in df['symbol'].unique(): # for all executions of the same stock
        sum_total = []
        df2 = df[df['symbol']==e]
        if e.find('.TO') != -1: # if stock is CAD
            ex_rate2 = 1
        elif e.find('.TO') == -1: # if stock is USD, set exchange rate
            ex_rate2 = ex_rate1
        sum_fees = ex_rate2 * df2[['commission', 'secFee', 'executionFee', 'canadianExecutionFee']].sum().sum() # sum all fees by type, then by total
        sum_buy = ex_rate2 * df2[['totalCost']][df2['side']=='Buy'].sum() # sum all the bought shares (totalCost, quantity)
        sum_buy = sum_buy.append(df2[['quantity']][df2['side']=='Buy'].sum())
        sum_sell = ex_rate2 * df2[['totalCost']][df2['side']=='Sell'].sum() # sum all the sold shares
        sum_sell = sum_sell.append(df2[['quantity']][df2['side']=='Sell'].sum())
        sum_total = sum_sell - sum_buy # difference of sold and bought value, quantity = net profit, net sold
        if sum_total['quantity'] < 0: # negative quantity means current positions/didn't sell all shares bought
            df3 = df2[['price', 'quantity']][df2['side']=='Buy']
            counter_quantity = sum_total['quantity'] # acquire how many current shares
            counter = 0
            holdings = 0
            print 'symb: %s, quant: %s, currentTotal: %s' %(e, counter_quantity, holdings)
            while counter_quantity < 0: # while shares still exist, find the value of the shares by determining its most recent bought prices
                counter_quantity2 = df3['quantity'].iloc[counter] + counter_quantity # subtract each exec from current shares
                if counter_quantity2 >= 0: # if counter quantity positive, overshot, therefore, quantity of shares*price
                    holdings = holdings + counter_quantity * df3['price'].iloc[counter] * -1
                elif counter_quantity < 0: # undershot, therefore, quantity of exec*price
                    holdings = holdings + df3['quantity'].iloc[counter] * df3['price'].iloc[counter] 
                counter_quantity = counter_quantity2
                counter = counter + 1
            print 'symb: %s, quant: %s, currentTotal: %s' %(e, counter_quantity, holdings)
            sum_total = sum_total.append(pd.Series({'currentHoldings': ex_rate2 * holdings})) # holdings at bought price
#            sum_total = sum_total.append(pd.Series({'currentHoldings_now': ex_rate2 * token.symbs(e)[0][0]['prevDayClosePrice'] * -sum_total['quantity']})) # holdings at last day's close
            sum_total = sum_total.append(pd.Series({'currentHoldings_now': ex_rate2 * token.candles(e)[0][-1]['close'] * -sum_total['quantity']})) # holdings at current price
        else: # quantity is zero, therefore no current holdings
            sum_total = sum_total.append(pd.Series({'currentHoldings': 0}))
            sum_total = sum_total.append(pd.Series({'currentHoldings_now': np.nan}))
        # append netProfit, netProfit_now (if holdings exist, valued at current prices), total fees, symbol
        sum_total['totalCost'] = sum_total['totalCost'] - sum_fees 
        sum_total = sum_total.append(pd.Series({'netProfit': sum_total['totalCost'] + sum_total['currentHoldings']}))
        sum_total = sum_total.append(pd.Series({'netProfit_now': sum_total['totalCost'] + sum_total['currentHoldings_now']}))
        sum_total = sum_total.append(pd.Series({'fees': sum_fees}))
        sum_total = sum_total.append(pd.Series({'symbol': e}))
        returns = returns.append(sum_total, ignore_index=True)
    # append returns with date key to list_returns
    list_returns.update({str(datetime.date.today()): returns}) # + datetime.timedelta(days=1)
    # run currency exchange returns and appends to returns
    sum_total = pd.DataFrame(['cash', netProfit_cad, netProfit_cad], index=['symbol', 'netProfit', 'netProfit_now']).T 
    returns = returns.append(sum_total, ignore_index=True)
    list_returns.update({str(datetime.date.today()): returns})
    
    # save list_returns and exchange rate values
    save(list_returns, filename='%sdaily pickles/account_profits.pickle' %(direct_data))
    save(list_returns, filename='%saccount_profits.pickle' %direct_data)
    return returns, list_returns

def ex_profits_dividends(delta=21):
#    delta = 19
    list_dividends = []
    df_usdex = pd.DataFrame()
    end = datetime.date.today()
    diff = end - datetime.date(2018, 01, 01)
    for i in range(int(round(diff.days/float(delta)+0.5))):
        start = end-datetime.timedelta(days=delta)
        try:
            actives = token.activities(datetime.datetime.strftime(start, '%Y-%m-%d') + ' to ' + datetime.datetime.strftime(end, '%Y-%m-%d'))[0]
            end = start    
            # dividend accumulator    
            for i in range(len(actives)):
                if actives[i]['type'] == 'Dividends':
                    list_dividends.append(actives[i])
            # within daterange, find currency exchanges.
            list_value_usd = []
            list_ex_cad = []
            for i in range(len(actives)):
                if actives[i]['action'] == 'BRW':
                    # for when journalling over shares. split description string
                    s = actives[i]['description']
                    s2 = s.split()
                    if s2[-2] == 'CNV@' and s2[-3] == 'U$':
                        # from CAD to USD
                        ex_tocad = float(s2[-1])
                        value_usd = float(s2[-4].replace(',', ''))
                        list_ex_cad.append(ex_tocad)
                        list_value_usd.append(value_usd)
                        print(' counter: %d, CAD to USD' %i)
                    elif s2[-2] == 'CNV@' and s2[-3] == 'C$':
                        # from USD to CAD
                        ex_tocad = float(s2[-1])
                        value_usd = float(s2[-4].replace(',', '')) * -1 / ex_tocad
                        list_ex_cad.append(ex_tocad)
                        list_value_usd.append(value_usd)
                        print(' counter: %d, USD to CAD' %(i+2)) # activities reversed compared to other for some reason
                    else:
                        print(' check string if below counter != %d:' %(i+1))
                if actives[i]['action'] == 'FXT':
                    # for when directly converting from CAD to USD. assumes first find is negative usd, next is cad
                    if actives[i]['netAmount'] < 0:
                        if actives[i]['currency'] == 'CAD':
                            value_usd = actives[i+1]['netAmount']
                            ex_tocad = -actives[i]['netAmount']/value_usd
                            list_ex_cad.append(ex_tocad)
                            list_value_usd.append(value_usd)
                '''
                        elif actives[i]['currency'] == 'USD':
                            value_usd = actives[i]['netAmount']
                            ex_tocad = actives[i+1]['netAmount']/-value_usd # have to confirm
                            list_ex_cad.append(ex_tocad)
                            list_value_usd.append(value_usd)
                        else:
                            print(' not CAD, check currency')
                '''
            df2 = pd.DataFrame([list_ex_cad, list_value_usd]).T
            # calculate current returns
            df_usdex = df_usdex.append(df2).reset_index()
#            netProfit_cad = sum((token.ex_rate() - df_usdex[0]) * df_usdex[1]) * token.ex_rate()
        except:
            print('%s to %s' %(start, end))
        try:
            df_usdex = df_usdex.drop(['level_0', 'index'], 1)
        except:
            pass
    print('%s number of conversions' %len(df_usdex))
    print('%s dividends identified' %len(list_dividends))
    netProfit_cad = sum((token.ex_rate() - df_usdex[0]) * df_usdex[1]) * token.ex_rate()
    df_dividends = pd.DataFrame()
    for each in list_dividends:
        df_dividends = pd.concat([df_dividends, pd.DataFrame([each['symbol'], 'Sell', each['netAmount']])], axis=1)
    df_dividends = df_dividends.T
    df_dividends.columns = ['symbol', 'side', 'totalCost']
    return df_dividends, netProfit_cad

def send_email(subject, message):
    # send email
    sender = 'sender_email'
    receiver = 'receiver_email' 

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = subject    
    
    msg.attach(MIMEText(message, 'plain'))
    text = msg.as_string()
    
    smtpObj = smtplib.SMTP(host='smtp.gmail.com', port=587)
    smtpObj.starttls()
    if os.name == 'nt':
        meme = pickle.load(open('C:/Users/name/Questrade_API/for_email.pickle', 'rb'))
    elif os.name == 'posix':
        meme = pickle.load(open('/mnt/name/Questrade_API/for_email.pickle', 'rb'))
    smtpObj.login('sender_email', meme)
    smtpObj.sendmail(sender, receiver, text)
    smtpObj.quit()
    print('email sent')
    
#####################
##### MAIN CODE #####
#####################
if os.name == 'nt':
    direct_data = 'C:/Users/name/Questrade_Data/' # need for pickle load
elif os.name == 'posix':
    direct_data = '/mnt/name/Questrade_Data/'
#direct_data = '' # need for pickle load?
token.check_access()
autosave = False # true to autosave data

try:    
    positions_daily2, balances_daily2 = account_daily(direct_data, token) # run positions and balances script
    if datetime.datetime.today().weekday() == 4: # grab profits data every Friday
        returns, list_returns = account_profits(direct_data, token)
    elif autosave == False: # if autosave is off and not a Friday, 
        if raw_input('run account_profits? (y/n): ') == 'y':
            returns, list_returns = account_profits(direct_data, token)
    else: # if autosave is on
        print('Not Friday: %d' %datetime.date.today().weekday())
    
    # send success email
    subject = str(datetime.date.today()) + "'s account_daily success"
    message = str(balances_daily2.tail(7))
    send_email(subject, message)
    
except Exception as e: 
    print('%s error: %s' %(datetime.date.today(), str(e)))
    # send fail email
    subject = 'account_daily error'
    message = """ account_daily.py error: """ + str(e)
    send_email(subject, message)
    # won't find empy cell errors?
    
