## 📋 项目概述

这是一个 **BI 数据分析** 的完整实战项目。基于阿里天池电商销售数据，我构建了一条从原始数据到智能决策支持的完整数据链路：

- **SQL**：数据清洗与指标计算（销售额、订单数、用户数、客单价）
- **Python**：环比增长计算、正负品类筛选、DeepSeek API 调用与 AI 报告生成
- **PowerBI**：5 页仪表板设计（全年大盘总览、月度经营环比、平台分析、品类分析、用户客单价分析）
- **Vue**：作品集前端展示页（含 PowerBI 截图与 AI 报告）

> 📸 **作品集预览**：[https://morandis.github.io/e-commerce/]

## 🛠️ 环境变量配置
analysis.py需要以下环境变量，请在运行前设置：

- `DB_USER`: 数据库用户名
- `DB_PASSWORD`: 数据库密码
- `DB_HOST`: 数据库主机（默认 127.0.0.1）
- `DB_PORT`: 数据库端口（默认 3306）
- `DB_NAME`: 数据库名（默认 ecommerce_sales）
- `DEEPSEEK_API_KEY`: deepseek api key

另需要安装依赖：
pip install pandas sqlalchemy openai


