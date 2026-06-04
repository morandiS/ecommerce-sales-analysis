import pandas as pd

# 用户订单记录
df_trans = pd.read_csv('trans.csv')
# 定义参考日期
max_date = pd.to_datetime(df_trans['order_date']).max()
ref_date = max_date + pd.Timedelta(days=1)

rfm = df_trans.groupby('user_id').agg({
    'order_date': lambda x: (ref_date - pd.to_datetime(x).max()).days,
    'user_id': 'count',
    'order_amount': 'sum'
}).rename(columns={'order_date': 'R', 'user_id': 'F', 'order_amount': 'M'})

# 用百分位数打分（1-4分）
rfm['R_score'] = pd.qcut(rfm['R'], 4, labels=[4,3,2,1])   # R越小分越高
rfm['F_score'] = pd.qcut(rfm['F'].rank(method='first'), 4, labels=[1,2,3,4])
rfm['M_score'] = pd.qcut(rfm['M'], 4, labels=[1,2,3,4])

# 总分或分类逻辑
rfm['RFM_Class'] = rfm['R_score'].astype(str) + rfm['F_score'].astype(str) + rfm['M_score'].astype(str)
# 定义用户分层
def classify_user(row):
    if row['R_score'] >= 3 and row['F_score'] >= 3 and row['M_score'] >= 3:
        return '高价值用户'
    elif row['R_score'] >= 3 and row['F_score'] >= 2:
        return '忠诚用户'
    elif row['R_score'] <= 2 and row['F_score'] >= 3:
        return '近期高频但消费低'
    elif row['R_score'] <= 2 and row['F_score'] <= 2:
        return '沉睡/流失用户'
    else:
        return '一般用户'

rfm['User_Segment'] = rfm.apply(classify_user, axis=1)

# 保存结果
rfm.reset_index().to_csv('user_rfm.csv', index=False)
print("RFM 分层完成，结果已保存")