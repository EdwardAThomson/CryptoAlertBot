# ------------------------------------------------------------
# 0.  LOAD YOUR DATA
# ------------------------------------------------------------
import pandas as pd
import numpy as np
from collections import defaultdict

# df must contain a Date index and a 'price' column (daily closes)
# df = pd.read_csv("daily.csv", parse_dates=['date']).set_index('date')

# ------------------------------------------------------------
# 1.  TURN PRICE INTO +/-1 “COLOR” SERIES
# ------------------------------------------------------------
df['ret']  = df['price'].pct_change()               # raw % change
df['sign'] = np.where(df['ret'] >= 0, 1, -1)        # +1 up-day, –1 down-day
df = df.dropna(subset=['sign']).copy()              # drop the first NaN row

# ------------------------------------------------------------
# 2.  RUN-LENGTH ENCODING  →  [(sign, length), ...]
# ------------------------------------------------------------
runs = []
length = 1
sign_series = df['sign'].values

for i in range(1, len(sign_series)):
    if sign_series[i] == sign_series[i-1]:
        length += 1
    else:
        runs.append((sign_series[i-1], length))
        length = 1
runs.append((sign_series[-1], length))              # last run

# ------------------------------------------------------------
# 3.  COUNT CONTINUATIONS & TERMINATIONS
#     cont[k] = #times a run of length k continued to k+1
#     end[k]  = #times a run ended exactly at length k
# ------------------------------------------------------------
cont = defaultdict(int)
end  = defaultdict(int)

for _, L in runs:
    for k in range(1, L):       # continued from k to k+1
        cont[k] += 1
    end[L] += 1                 # ended at its final length

# ------------------------------------------------------------
# 4.  COMPUTE HAZARD & SURVIVAL WITH LAPLACE (+1) SMOOTHING
# ------------------------------------------------------------
max_k   = max(max(cont, default=1), max(end, default=1))
hazard  = {}    # P(run ENDS tomorrow | run length = k)
survive = {}    # P(run CONTINUES tomorrow | run length = k)

for k in range(1, max_k + 1):
    c = cont.get(k, 0) + 1      # +1 Laplace smoothing
    e = end.get(k, 0)  + 1
    hazard[k]  = e / (c + e)
    survive[k] = 1 - hazard[k]

# ------------------------------------------------------------
# 5.  AVERAGE RETURN BY “COLOR” (used later for E[ret])
# ------------------------------------------------------------
mu_pos = df.loc[df['sign'] == 1,  'ret'].mean()     # mean up-day
mu_neg = df.loc[df['sign'] == -1, 'ret'].mean()     # mean down-day

# ------------------------------------------------------------
# 6.  FUNCTION TO PREDICT TOMORROW
# ------------------------------------------------------------
def predict_next(df, hazard, survive, mu_pos, mu_neg):
    """
    Parameters
    ----------
    df : DataFrame with latest 'sign'
    hazard, survive : dicts from step 4
    mu_pos, mu_neg  : average up/down % moves

    Returns
    -------
    k           current run length (int)
    current_col current color (+1 or –1)
    p_continue  probability tomorrow matches today
    exp_ret     expected % price change tomorrow
    """
    # determine current streak length k and its color
    k = 1
    current_col = df['sign'].iat[-1]
    for i in range(len(df)-2, -1, -1):
        if df['sign'].iat[i] == current_col:
            k += 1
        else:
            break

    # fetch survival prob for this k (default = 0.5 if unseen)
    p_continue = survive.get(k, 0.5)
    p_flip     = 1 - p_continue

    # expected return (conditional on streak color)
    mu_same = mu_pos if current_col == 1 else mu_neg
    mu_flip = mu_neg if current_col == 1 else mu_pos
    exp_ret = p_continue * mu_same + p_flip * mu_flip

    return k, current_col, p_continue, exp_ret

# ------------------------------------------------------------
# 7.  EXAMPLE USAGE
# ------------------------------------------------------------
k, col, p_cont, e_ret = predict_next(df, hazard, survive, mu_pos, mu_neg)

print(f"Current streak : {k} {'UP' if col==1 else 'DOWN'} days")
print(f"P(streak continues tomorrow) = {p_cont:.2%}")
print(f"Expected return tomorrow     = {e_ret:.3%}")

