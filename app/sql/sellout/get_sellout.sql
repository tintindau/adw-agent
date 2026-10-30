SELECT
    o.DATE_KEY,
    o.DMX_PROD_ID,
    o.DMX_PROD_NAME,
    o.STORE_KEY,
    o.GEO_PROVINCE_CUST,
    o.CHANNEL_KEY,
    o.PROD_STATUS,
    o.IS_GIFT,
    o.QUANTITY_SOLD,
    o.PROMO_QUANTITY,
    o.NET_QUANTITY,
    o.REVENUE_SRC_VND AS unit_price,
    o.NET_QUANTITY * o.REVENUE_SRC_VND AS Revenue -- before VAT
FROM SLV_FACT_DMX_SELLOUT o
JOIN dim_store_shop p
    ON REGEXP_REPLACE(o.store_key, '^([^-]+-){2}', '') = p.store_code
WHERE o.date_key >= :start_date
    AND o.date_key < :end_date