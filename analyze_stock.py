# -*- coding: utf-8 -*-
"""
Created on Tue May 01 00:23:45 2018

@author: A
Note: TAKE THIS INTO ACCOUNT THE LEAST, AFTER INDICATORS
Analyze a specific stock: what are the chances stock goes up or down (next day, next week, next month, next 3 months, next 4 months)
* big_change(symb, datestring, %change, delta, interval, diff, nonres)

Ideas:
Multiple stocks watchlist graphs
- after flat/squeeze (low st. dev.) (slow decrease or slow increase)
- after peaks or dips (find max/min peaks and their dates), will it go up or down. (probably best in short term)
- calculate companies' eps, pe, yield. compare with sector average
- when to sell?
"""
import sys
import os
if os.name == 'nt':
    sys.path.append('C:/Users/name/Questrade_API/')
elif os.name == 'posix':
    sys.path.append('/mnt/name/Questrade_API/')
from questrade import *
import datetime, pandas as pd
import pylab

def big_change(symb, datestring='2017-05-12 to today', change=1, delta=7, interval='OneDay', new=True, nonres=False):
    # after % change, what is success rate of buy-in
    # this only works for specific intervals, how to choose # of days/hours
    # picking OHLC values, which one is best? Idk
    
    # grab candles data
    if new:
        data = token.candles(symb, datestring='beginning to today', interval=interval)[0] # grab max data as possible
        global df
        df = pd.DataFrame(data) # convert to dataframe
        df['mid_oc'] = (df['open'] + df['close'])/2
        
        if interval=='OneDay' or interval=='OneWeek' or interval=='OneMonth' or interval=='OneYear': # if interval is > 1 day, ignore time
            df['start2'] = pd.to_datetime(pd.to_datetime(df['start']).dt.date) # convert from isoformat to date
            df['end2'] = pd.to_datetime(pd.to_datetime(df['end']).dt.date)
        else:
            df['start2'] = pd.to_datetime(df['start']) # convert from isoformat to datetime
            df['end2'] = pd.to_datetime(df['end'])
    cols = ['VWAP', 'close', 'high', 'low', 'open', 'volume', 'mid_oc']
        
    # restrict daterange from initial df
    start_date, end_date = token._daterange(datestring) 
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    mask = (df['start2'] > start_date) & (df['start2'] < end_date) 
    df2 = df.loc[mask]
    
    # price change low/open and high/open
    change = change
    percent_change = 1 + float(change)/100
    if change < 0:
        ids = df2[df2['low']/df2['open'] < percent_change] # change from open to low
    elif change > 0:
        ids = df2[df2['high']/df2['open'] > percent_change] 
    ids = ids.reset_index()
    
    # calculate whether after delta after, if value is positive. -change = open before/after, +change = close before/after. Does this matter?
    delta = delta # depends on intervals. select final day: 1, 7, 14, 30, 90, 120
    day_change = ids['start2'] + datetime.timedelta(days=delta)
    current_guess = []
    ids_after2 = pd.DataFrame()
    for ea in range(len(day_change)):
        while (df2['start2'].isin([day_change.iloc[ea]]).any() or day_change.iloc[ea] >= end_date) == False: # check if day is on weekend/holiday/non-existing day
#            print(' weekend: %s' %day_change.iloc[ea])
            day_change_new = day_change.iloc[ea] + datetime.timedelta(days=1)
            day_change.iloc[ea] = day_change_new
        if day_change.iloc[ea] >= end_date: # days don't exist for these, time for your guess
            print(' future day: %s' %day_change.iloc[ea])
            current_guess.append(day_change.iloc[ea])
        ids_after2 = ids_after2.append(df2[df2['start2']==day_change.iloc[ea]])
    ids_after = df2[df2['start2'].isin(day_change)]
    ids_after = ids_after.reset_index()
#    ids_diff = ids_after[cols] - ids[cols] # take difference of before and after
    
    ids_after2 = ids_after2.reset_index()
    ids_diff = ids_after2[cols] - ids[cols]
    if change < 0:
        rate_success = sum(ids_diff['mid_oc']>0)/float(len(ids_diff)) # % rate, negative change, look at opening difference
        ids_success = ids[ids_diff['mid_oc']>0]
        print('success rate: %.4f, possibilities: %d/%d' %(rate_success, len(ids_success), len(ids_diff)))
    elif change > 0:
        rate_success = sum(ids_diff['close']>0)/float(len(ids_diff)) # % rate, positive change, look at closing difference
        ids_success = ids[ids_diff['close']>0]
        print('success rate: %.4f, possibilities: %d/%d' %(rate_success, len(ids_success), len(ids_diff)))
    ids_guess = ids[len(ids)-len(current_guess):]

    # plot restricted candles
    fig = pylab.figure(figsize=(8,4))
    ax1 = fig.add_subplot(111)
    df2.plot('start2', 'mid_oc', ax=ax1, title='success: %.4f, %d/%d' %(rate_success, len(ids_success), len(ids_diff)))
    df2.plot('start2', 'high', ax=ax1, marker='.', color='r', linestyle='None', markersize=3)
    df2.plot('start2', 'low', ax=ax1, marker='.', color='y', linestyle='None', markersize=3)
    ids.plot('start2', 'mid_oc', ax=ax1, marker='o', color='orange', linestyle='None')
    ids_success.plot('start2', 'mid_oc', ax=ax1, marker='.', color='green', linestyle='None')
    try:
        ids_guess.plot('start2', 'mid_oc', ax=ax1, marker='.', color='r', linestyle='None')
    except:
        print( 'None')
    pylab.show()
    
    # non-restricted
    if nonres:
        fig = pylab.figure(figsize=(8,4))
        ax2 = fig.add_subplot(111)
        df.plot('start2', 'mid_oc', ax=ax2)
        ids.plot('start2', 'mid_oc', ax=ax2, marker='o', color='orange', markersize=1, linestyle='None')
        
    return [df, df2, ids, ids_after, ids_diff, ids_guess, day_change, ids_after2]

#####################
##### MAIN CODE #####
#####################
#if os.name == 'nt':
#    direct_data = 'C:/Users/name/Questrade_Data/' # need for pickle load
#elif os.name == 'posix':
#    direct_data = '/mnt/name/Questrade_Data/'    

#token.check_access()
    
# ids_diff open/close/mid_oc, makes a big difference
others = big_change(symb='spx.in', 
                    datestring='2018-01-01 to today', 
                    change=2, 
                    delta=7, 
                    interval='OneWeek',
                    new=True,
                    nonres=False)



# binning intervals
#test2 = pd.DataFrame()
#test = df.iloc[0:2]
#df['high'].iloc[0:2].max()
#df['low'].iloc[0:2].min()
#df['close'].iloc[0:2].last
#df['open'].iloc[0:2].first


#symbol = token.symbs('RHT')
#
#['eps'] # earnings per share 12-month, compare with others in same sector
#['pe'] # price to earnings per share 12-month, compare with others in same sector: 20 average
#['yield'] # Dividend yield (dividend / prevDayClosePrice), compare this with earnings: 2-3 earnings/dividend average
#
#['prevDayClosePrice']
#['lowPrice52']
#['highPrice52']


'''
OneMinute = 'OneMinute'
TwoMinutes = 'TwoMinutes'
ThreeMinutes = 'ThreeMinutes'    
FourMinutes = 'FourMinutes'
FiveMinutes = 'FiveMinutes'
TenMinutes = 'TenMinutes'
FifteenMinutes = 'FifteenMinutes'
TwentyMinutes = 'TwentyMinutes'
HalfHour = 'HalfHour'
OneHour = 'OneHour'
TwoHours = 'TwoHours'
FourHours = 'FourHours'
OneDay = 'OneDay'
OneWeek = 'OneWeek'
OneMonth = 'OneMonth'
OneYear = 'OneYear'
'''