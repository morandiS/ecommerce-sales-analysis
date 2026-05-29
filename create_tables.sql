CREATE DATABASE IF NOT EXISTS ecommerce_sales;
USE ecommerce_sales;
# 用户表
CREATE TABLE dim_user (
	user_id VARCHAR(50) PRIMARY KEY COMMENT '用户ID',
	user_name VARCHAR(50) COMMENT '用户姓名',
	gender TINYINT DEFAULT 0 COMMENT '性别 0=未知 1=男 2=女',
	age TINYINT UNSIGNED DEFAULT 0 COMMENT '年龄',
	city VARCHAR(50) COMMENT '用户城市'
);
# 交易表
CREATE TABLE fact_transaction (
  user_id VARCHAR(50),
  product_id VARCHAR(20),
  quantity INT,
  order_date DATETIME,
  platform VARCHAR(20),
  UNIQUE KEY (user_id, product_id, order_date, platform)
);
# 商品表
CREATE TABLE dim_product (
  product_id VARCHAR(20),
  product_name VARCHAR(100),
  category VARCHAR(50),
  price DECIMAL(10, 2)
);
# 导入excel中csv格式的数据
-- 创建临时性别字段（因为excel数据中的性别是字符串类型）
ALTER table dim_user add COLUMN gender_str varchar(10);

# 创建临时表dim_user_temp（这里创建用户临时表是发现用户表中ID很多重复的，为了去掉主键约束把数据先导入）
CREATE TABLE dim_user_temp LIKE dim_user;
--desc dim_user_temp;
ALTER TABLE dim_user_temp DROP PRIMARY KEY; -- 去掉主键约束
--SELECT * FROM dim_user;
-- ----------------用户表---------------------
ALTER TABLE dim_user_temp ADD COLUMN platform VARCHAR(20);
-- 这里增加order_date为了拿到同一用户ID的最新order_date，为了后续只保留唯一ID
ALTER TABLE dim_user_temp ADD COLUMN order_date DATETIME;
SELECT * FROM dim_user_temp WHERE platform = '天猫';
-- 更新平台字段的值，各平台数据分别导入，对应修改即可
UPDATE dim_user_temp
SET platform = '天猫'
WHERE platform IS NULL;
-- ------------------开始处理商品表-----------------
ALTER TABLE dim_product ADD COLUMN platform VARCHAR(20);
UPDATE dim_product
SET platform = '淘宝'
WHERE platform IS NULL;
-- -----------------交易表------------------------
UPDATE fact_transaction
SET platform = '淘宝'
WHERE platform IS NULL;
------------------开始处理数据----------------------
# 处理数据
-- 处理user中重复ID
-- 找出重复的user_id，这里是为了看删除冗余数据之后，数据条数还是否能够对应
select user_id, platform, COUNT(user_id)
FROM dim_user_temp
GROUP BY user_id, platform
HAVING COUNT(user_id) > 1;
-- 保留最新order_date的用户id
SELECT user_id, MAX(order_date) AS max_order_date
FROM dim_user_temp
GROUP BY user_id, platform;
-- 查询某平台可保留的有效数据
SELECT user_id, MAX(order_date) AS max_order_date
FROM dim_user_temp
WHERE platform = '苏宁易购'
GROUP BY user_id;
-- 删除 旧的冗余数据，只保留最新user_id
DELETE t1
FROM dim_user_temp t1
LEFT JOIN (
    SELECT user_id, MAX(order_date) AS max_dt
    FROM dim_user_temp
    GROUP BY user_id, platform
) t2 ON t1.user_id = t2.user_id AND t1.order_date = t2.max_dt
WHERE t2.user_id IS NULL;
-- 将gender赋值
UPDATE dim_user_temp
SET gender =
    CASE gender_str
      WHEN '男' THEN 1
      WHEN '女' THEN 2
      ELSE 0
    END;
-- 删除dim_user中的gender_str字段，没有意义，使用gender就够了
ALTER TABLE dim_user DROP COLUMN gender_str;
-- 给dim_user添加平台字段，需要user_id和platform共同作为主键
ALTER TABLE dim_user ADD COLUMN platform VARCHAR(20);
-- dim_user使用user_id和platform作为混合主键
ALTER TABLE dim_user DROP PRIMARY KEY;
ALTER TABLE dim_user
ADD PRIMARY KEY (user_id, platform);
-- 从dim_user_temp给dim_user导入数据
INSERT INTO dim_user (user_id, user_name, gender, age, city, platform)
SELECT user_id, user_name, gender, age, city, platform FROM dim_user_temp;
-- -------------------------商品表---------------------------
SELECT product_id, COUNT(product_id) FROM dim_product
GROUP BY product_id, platform HAVING COUNT(product_id) > 1;
-- 商品id去重，只保留一个
DELETE t1
FROM dim_product t1
LEFT JOIN (
    SELECT product_id, MAX(product_name) AS max_pn
    FROM dim_product
    GROUP BY product_id, platform
) t2 ON t1.product_id = t2.product_id AND t1.product_name = t2.max_pn
WHERE t2.product_id IS NULL;
-- 将product_id和platform设为共同主键
ALTER TABLE dim_product
ADD PRIMARY KEY (product_id, platform);
