SELECT 
    -- 1. Chiều Thời gian
    si.gh_date_key AS date_,
    si.gh_month_key AS month_,
    -- 2. Chiều Địa lý
    s.REGION_NAME_TMP AS region,
    s.PROVINCE AS province,
    -- 3. Chiều Nhóm hàng
    p.category_bod AS prod_class_dmx,
    p.sub_category AS prod_category,
    -- 4. Chiều Loại hàng & Luồng hàng
    CASE 
        WHEN p.IS_SHIBU_25PCT = 1 THEN 'Shibu'
        WHEN p.IS_MOCKUP_DUMMY = 1 THEN 'Trung_bay'
        ELSE 'Con_lai'
    END AS prod_type,
    si.GH_FLOW AS gh_flow,
    -- Các chỉ số (Metrics) Sell-in / Sell-out
    si.GH_SO_QTY AS so_qty,
    si.GH_SO_PROMO_QTY AS so_promo_qty,
    si.GH_SO_OUT_QTY AS so_out_qty,
    si.GH_SO_OUT_QTY_NEW AS so_out_qty_new,
    si.GH_SI_AMOUNT AS si_amount,
    si.GH_SI_QTY AS si_qty,
    si.GH_SI_PROMO_QTY AS si_promo_qty,
    si.GH_SI_QTY_NEW AS si_qty_new
FROM GLD_HIST_DMX_SISO_DAY si
JOIN SLV_DIM_DMX_STORE s ON si.gh_store_key = s.Store_key
JOIN dim_product p ON si.GH_DMX_PROD_ID = p.prod_id_kgr
WHERE 1=1