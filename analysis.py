import pandas as pd
from sqlalchemy import create_engine
import os
from openai import OpenAI
from dateutil.relativedelta import relativedelta
from datetime import datetime
import sys
# 1. 连接数据库
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '123456')   # 上传 GitHub 时改成假密码
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_NAME = os.getenv('DB_NAME', 'ecommerce_sales')
connection_string = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8"
def get_db_engine():
    try:
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            return engine
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return None

engine = get_db_engine()
if engine is None:
    print("无法继续，程序退出。")
    sys.exit(1)

# 处理月份
def get_month_range(year_month):
    """
    给定 'YYYY-MM'，返回该月的第一天 和 下个月的第一天（用于 < 比较）
    """
    dt = datetime.strptime(year_month, '%Y-%m')
    month_start = dt.strftime('%Y-%m-%d')
    next_month_start = (dt + relativedelta(months=1)).strftime('%Y-%m-%d')
    return month_start, next_month_start
# 2. 从数据库中拿数据
def get_report_data(start_month, end_month):
    """
    start_month: '2024-10'
    end_month: '2024-11'
    engine: SQLAlchemy engine
    返回:
        df_total: 包含两行（start_month和end_month）的整体指标
        df_category: 包含两个月所有品类销售额（含month列）
    """
    # 计算两个月的起止（使用下个月第一天作为结束边界）
    start_start, start_end_exclusive = get_month_range(start_month)
    end_start, end_end_exclusive = get_month_range(end_month)

    # 整个查询范围：从 start_month 第一天 到 end_month 最后一天（用 end_end_exclusive）
    query_start = start_start
    query_end = end_end_exclusive  # 例如 '2024-12-01'，不包含12月数据
    sql_total = f"""
    SELECT SUM(amount) AS total_sales,
      COUNT(DISTINCT product_id, platform) AS order_count,
      ROUND(SUM(amount) / COUNT(DISTINCT product_id, platform), 2) AS avg_order,
      COUNT(DISTINCT user_id, platform) AS user_count,
      DATE_FORMAT(order_date, '%%Y-%%m') AS `month`
    FROM (
      SELECT ft.product_id, ft.user_id, ft.order_date, ft.platform, ft.quantity * p.price AS amount
      FROM fact_transaction ft
      LEFT JOIN dim_product p ON ft.product_id = p.product_id AND ft.platform = p.platform
      WHERE order_date >= '{query_start}' AND ft.order_date < '{query_end}'
    ) ft_temp
    GROUP BY `month`
    ORDER BY `month` DESC;
    """
    sql_category = f"""
    SELECT 
        DATE_FORMAT(ft.order_date, '%%Y-%%m') AS month,
        SUM(ft.quantity * p.price) AS sales,
        p.category
    FROM fact_transaction ft
    LEFT JOIN dim_product p ON ft.product_id = p.product_id AND ft.platform = p.platform
    WHERE ft.order_date >= '{query_start}' AND ft.order_date < '{query_end}'
      AND p.category IS NOT NULL
    GROUP BY month, p.category;
    """
    total = pd.read_sql(sql_total, engine)
    category = pd.read_sql(sql_category, engine)
    return total, category

# 3. 直接读取 得到 DataFrame
df_total, df_category = get_report_data('2024-10', '2024-11')
# print(df_category)

# 拆分成上月和本月
current = df_total[df_total['month'] == '2024-11'].iloc[0]
previous = df_total[df_total['month'] == '2024-10'].iloc[0]
# 环比
sales_ratio = (current['total_sales'] - previous['total_sales']) / previous['total_sales']
order_ratio = (current['order_count'] - previous['order_count']) / previous['order_count']
user_ratio = (current['user_count'] - previous['user_count']) / previous['user_count']
avg_order_ratio = (current['avg_order'] - previous['avg_order']) / previous['avg_order']

# 品类
prev_cat = df_category[df_category['month'] == '2024-10'][['category', 'sales']].rename(columns={'sales': 'sales_prev'})
current_cat = df_category[df_category['month'] == '2024-11'][['category', 'sales']].rename(columns={'sales': 'sales_current'})
# 合并
df_category = pd.merge(current_cat, prev_cat, on='category', how='outer').fillna(0)
df_category['growth'] = df_category['sales_current'] - df_category['sales_prev']
df_category['growth_rate'] = (df_category['growth'] / df_category['sales_prev'].replace(0, 1)) * 100
# 找出“上升最快”和“下降最快”的品类（正增长各取3个）
df_positive = df_category[df_category['growth_rate'] > 0]
rising = df_positive.nlargest(3, 'growth_rate')[['category', 'sales_current', 'sales_prev', 'growth_rate']]
df_negative = df_category[df_category['growth_rate'] < 0]
falling = df_negative.nsmallest(3, 'growth_rate')[['category', 'sales_current', 'sales_prev', 'growth_rate']]
# 找出“持续TOP3”：上月和本月都在整体排名前3的品类（这里需要先排名）
df_category['rank_current'] = df_category['sales_current'].rank(ascending=False, method='min')
df_category['rank_prev'] = df_category['sales_prev'].rank(ascending=False, method='min')
consistent_top = df_category[(df_category['rank_current'] <= 3) & (df_category['rank_prev'] <= 3)]['category'].tolist()
consistent_top_str = '、'.join(consistent_top) if consistent_top else '无'
# print("上升最快:", rising.to_dict('records'))
# print("下降最快:", falling.to_dict('records'))
# print("持续TOP:", consistent_top_str)

# 预先处理一下品类增长数量，输出更准确的报告
if len(rising) > 0:
    rising_desc = "、".join([f"{row['category']}（+{row['growth_rate']:.1f}%）" for _, row in rising.iterrows()])
    if len(rising) < 3:
        rising_desc += f"（仅{len(rising)}个品类正增长）"
else:
    rising_desc = "无正增长品类"

if len(falling) > 0:
    falling_desc = "、".join([f"{row['category']}（{row['growth_rate']:.1f}%）" for _, row in falling.iterrows()])
else:
    falling_desc = "无负增长品类"
# print(rising_desc, falling_desc)
# 构建描述字符串
prompt_text = f"""
你是一位资深的电商数据分析师。请根据以下数据，写一份300字左右的经营分析报告，使用流畅的段落文字，不要使用列表或Markdown格式。

要求：
1. 指出整体趋势是向好还是向坏，并说明依据。
2. 重点分析增长最快和下降最快的品类，推测可能的原因（结合电商常识，如季节、促销、竞品活动等）。
3. 针对持续下滑的品类，给出2条具体、可落地的改善建议。
4. 指出下个月需要重点关注的品类，并说明理由。

数据周期：2024年11月（本月） vs 2024年10月（上月）
整体指标：
销售额：{current['total_sales']}元，环比{round(sales_ratio*100,2)}%
订单数：{current['order_count']}单，环比{round(order_ratio*100,2)}%
活跃用户数：{current['user_count']}人，环比{round(user_ratio*100,2)}%
客单价：{current['avg_order']}元，环比{round(avg_order_ratio*100,2)}%
品类变化亮点：
- 增长最快的品类：{rising_desc}
- 下降最快的品类：{falling_desc}
- 持续TOP的品类：{consistent_top_str}

注意：如果“增长最快的品类”显示无正增长，请分析整体下滑的原因；如果“下降最快的品类”显示无负增长，请分析增长的主要驱动力。
"""
# print(prompt_text)
# --- 读取 API Key 并做基础检查 ---
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    print("错误: 未找到 DEEPSEEK_API_KEY 环境变量。")
    sys.exit(1)
# --- 初始化客户端 ---
try:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )
except Exception as e:
    print(f"客户端初始化失败: {e}")
    sys.exit(1)
# noinspection PyTypeChecker
response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "你是资深电商数据分析师"},
        {"role": "user", "content": prompt_text}
    ],
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}},
)

report = response.choices[0].message.content
# print(report)

# 保存报告到txt文件，供后续粘贴到PPT或PowerBI
with open('AI_report.txt', 'w', encoding='utf-8') as f:
    f.write(report)
