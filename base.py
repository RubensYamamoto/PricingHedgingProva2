import pandas as pd
import numpy as np
import scipy.stats as st
import datetime
from dateutil.relativedelta import relativedelta

#define constants
call=1
put=-1
positionLong=1
positionShort=-1

#build dataframes from Excel
path = 'C:/Users/RUBENS_PC/Google Drive/Mestrado/semestre04/Pricing and Hedging/Pricing - Prova 02/BBergValues_split.xlsx';
xlsx = pd.ExcelFile(path)
usdbrl_df = xlsx.parse('USDBRL')
ptax_df = xlsx.parse('PTAX')
ibovespa_df = xlsx.parse('Ibovespa')
di1Jan21_df = xlsx.parse('DI1Jan21')
cdi_df = xlsx.parse('CDI')
cds_df = xlsx.parse('CDS')
volATM1M_df = xlsx.parse('VolATM1M')
volATM3M_df = xlsx.parse('VolATM3M')
volATM12M_df = xlsx.parse('VolATM12M')
swapPreCDI1M_df = xlsx.parse('SwapPreCDI1M')
swapPreCDI3M_df = xlsx.parse('SwapPreCDI3M')
swapPreCDI12M_df = xlsx.parse('SwapPreCDI12M')
fwd1M_df = xlsx.parse('FWD1M')
fwd3M_df = xlsx.parse('FWD3M')
fwd12M_df = xlsx.parse('FWD12M')
referenceDates_df = pd.DataFrame(usdbrl_df['Date'], columns=['Date'])

# Calculate business days between two dates
def busDaysQty(endDate, startDate):
    daysQty = np.busday_count( startDate.date(), endDate.date() )
    return daysQty

# Black 76 formula for forwards
def black76(phi, fwd, K, vol, t, df):
    efv=t*(vol**2)
    # calculate d1 and d2
    d1=(np.log(fwd/K)+(efv/2))/(np.sqrt(efv))
    d2=(np.log(fwd/K)-(efv/2))/(np.sqrt(efv))
    # calculate N(d1) and N(d2)
    Nd1=st.norm.cdf(phi*d1)
    Nd2=st.norm.cdf(phi*d2)
    # calculate premium
    pr=phi*(fwd*Nd1 - K*Nd2)*df
    # calculate delta
    de=phi*Nd1*df
        
    return [pr, de]

# Perform linear interpolation between two dates with respective values
def linearInterpolation(date0, value0, date1, value1, targetDate):
    targetValue = value0 + (value1 - value0) * busDaysQty(targetDate, date0) / busDaysQty(date1, date0)
    return targetValue

# Perform interpolation between two dates with respective effective variances
def volInterpolation(date0, value0, date1, value1, t):
    effectiveVarianceLongPeriod=busDaysQty(date1, date0)*(value1**2)
    effectiveVarianceShortPeriod=busDaysQty(t, date0)*(value0**2)
    targetValue = np.sqrt((effectiveVarianceLongPeriod-effectiveVarianceShortPeriod)/(busDaysQty(date1, t)))
    return targetValue

# Calculate CDI at maturity
# i is the index to get info from dataframes
def calcCDIAtMaturity(currentDate, maturityDate, tenor, i):
    if (tenor == 1):
        date0=currentDate
        value0=cdi_df['PX_LAST'][i]
        date1=currentDate + relativedelta(months=1)
        value1=swapPreCDI1M_df['PX_LAST'][i]
    elif (tenor == 3):
        date0=currentDate + relativedelta(months=1)
        value0=swapPreCDI1M_df['PX_LAST'][i]
        date1=currentDate + relativedelta(months=3)
        value1=swapPreCDI3M_df['PX_LAST'][i]
    elif (tenor == 12):
        date0=currentDate + relativedelta(months=3)
        value0=swapPreCDI3M_df['PX_LAST'][i]
        date1=currentDate + relativedelta(months=12)
        value1=swapPreCDI12M_df['PX_LAST'][i]
    
    cdiAtMaturity=linearInterpolation(date0, value0, date1, value1, maturityDate)
    return cdiAtMaturity

# Calculate Forward at maturity
# i is the index to get info from dataframes
def calcFwdAtMaturity(currentDate, maturityDate, tenor, i):
    if (tenor == 1):
        date0=currentDate
        value0=usdbrl_df['PX_LAST'][i]
        date1=currentDate + relativedelta(months=1)
        value1=fwd1M_df['PX_LAST'][i]
    elif (tenor == 3):
        date0=currentDate + relativedelta(months=1)
        value0=fwd1M_df['PX_LAST'][i]
        date1=currentDate + relativedelta(months=3)
        value1=fwd3M_df['PX_LAST'][i]
    elif (tenor == 12):
        date0=currentDate + relativedelta(months=3)
        value0=fwd3M_df['PX_LAST'][i]
        date1=currentDate + relativedelta(months=12)
        value1=fwd12M_df['PX_LAST'][i]  
    
    fwdAtMaturity=linearInterpolation(date0, value0, date1, value1, maturityDate)
    return fwdAtMaturity

# Calculate Vol Impl ATM at maturity
# i is the index to get info from dataframes
def calcVolAtMaturity(currentDate, tenor, i):
    # interpolating vol
    if (tenor == 1):
        volAtMaturity=volATM1M_df['PX_LAST'][i]
    elif (tenor == 3):
        date0=currentDate + relativedelta(months=1)
        value0=volATM1M_df['PX_LAST'][i]
        date1=currentDate + relativedelta(months=3)
        value1=volATM3M_df['PX_LAST'][i]
        volAtMaturity=volInterpolation(currentDate, value0, date1, value1, date0)
    elif (tenor == 12):
        date0=currentDate + relativedelta(months=3)
        value0=volATM3M_df['PX_LAST'][i]
        date1=currentDate + relativedelta(months=12)
        value1=volATM12M_df['PX_LAST'][i]
        volAtMaturity=volInterpolation(currentDate, value0, date1, value1, date0)
        
    return volAtMaturity

# Generates partial dataframe with dates and respectives time to maturity, discount factor, 
def fillPartialDf(phi, position, tenor, startDate):
    #stablish dataframe limits
    startIndex = referenceDates_df.loc[referenceDates_df['Date'] == startDate].index[0]
    maturityDate = startDate + relativedelta(months=tenor)

    #check if maturity date is greater than the last Bloomberg date available
    lastRow=len(referenceDates_df['Date'])
    if (maturityDate > referenceDates_df['Date'][lastRow-1]):
        maturityDate = referenceDates_df['Date'][lastRow-1]
    
    endIndex = referenceDates_df.loc[referenceDates_df['Date'] == maturityDate].index[0]
    
    #define strike ATMF
    if (tenor == 1):
        K=fwd1M_df['PX_LAST'][startIndex]
    elif (tenor == 3):
        K=fwd3M_df['PX_LAST'][startIndex]
    elif (tenor == 12):
        K=fwd12M_df['PX_LAST'][startIndex]
    
    #create initial arrays
    size=len(referenceDates_df['Date'].loc[startIndex:endIndex])
    referenceDate_array = np.empty(size, dtype=datetime.date);
    ttm_array = np.empty(size);
    discountFactor_array = np.empty(size);
    fwdAtMaturity_array = np.empty(size);
    volAtMaturity_array = np.empty(size);
    premium_array = np.empty(size);
    delta_array = np.empty(size);
    cdiOver_array = np.empty(size);
    
    #loop dataframes row by row from start date to maturity
    idx=0
    for i in range(startIndex,endIndex+1):
        currentDate=referenceDates_df['Date'][i]
        #calculate time to maturity
        ttm=busDaysQty(maturityDate,currentDate)/252
        # interpolating CDI
        cdiAtMaturity=calcCDIAtMaturity(currentDate, maturityDate, tenor, i)
        discountFactor = 1/((1 + (cdiAtMaturity/100))**ttm)
        # interpolating Forward
        fwdAtMaturity=calcFwdAtMaturity(currentDate, maturityDate, tenor, i)
        # interpolating vol
        volAtMaturity=calcVolAtMaturity(currentDate, tenor, i)/100
    
        # calculate premium
        if (currentDate == maturityDate):
            S = usdbrl_df['PX_LAST'][i]
            premium=position*max(phi*(S-K), 0)
            delta=0
        else:
            black76Result = black76(phi, fwdAtMaturity, K, volAtMaturity, ttm, discountFactor)
            premium=position*black76Result[0]
            delta=position*black76Result[1]
    
        referenceDate_array[idx]=currentDate
        ttm_array[idx]=ttm
        discountFactor_array[idx]=discountFactor
        fwdAtMaturity_array[idx]=fwdAtMaturity
        volAtMaturity_array[idx]=volAtMaturity
        premium_array[idx]=premium
        delta_array[idx]=delta
        # calculate CDI overnight
        cdiOver_array[idx]=(1 + (cdi_df['PX_LAST'][i])/100)**(1/252)    
        idx = idx + 1
    
    resultMatrix=np.array([[referenceDate_array[j].date(), ttm_array[j], discountFactor_array[j], fwdAtMaturity_array[j], volAtMaturity_array[j], premium_array[j], delta_array[j], cdiOver_array[j]] for j in range(size)])

    dfResult = pd.DataFrame(resultMatrix,columns=['date','ttm','df','fwd','vol','premium','delta','cdiOver'])
    return dfResult

# Calculate portfolio by date
def calcPortfolio(phi, position, tenor, startDate, includeHedge):
    df=fillPartialDf(phi, position, tenor, startDate)
    nstp=len(df.index)-1
    # cashflows for the option
    df['cfwprem']=0
    df.loc[0,'cfwprem']=-df['premium'][0]
    for j in range(1,nstp+1):
        df.loc[j:,'cfwprem']=df['cfwprem'][j-1]*df['cdiOver'][j-1]
    
    # calculate changes in forward price
    df['fwdchg']=df['fwd'].diff()
    df.loc[0,'fwdchg']=0
    
    # hedging cashflows
    df['cfwhdg']=0
    for j in range(1,nstp+1):
        df.loc[j:,'cfwhdg']=df['fwdchg'][j]*df['delta'][j-1]
    
    # total cashflow
    if (includeHedge == 1):
        df['cfwtotal']=df['cfwprem']+df['cfwhdg']
    else:
        df['cfwtotal']=df['cfwprem']
    
    # portfolio
    df['portf']=df['premium']+df['cfwtotal']
    return pd.Series(df['portf'].values, index=df['date'].values)