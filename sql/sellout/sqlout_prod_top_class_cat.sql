select 
    o.dmx_prod_id as prod_code,
    o.DMX_PROD_NAME as prod_name,
    o.date_key as date_,
    d.cal_month_number as month_,
    d.cal_year_code as year_,
    p.PROD_ID_KGR as prod_id_kgr,
    p.PROD_NAME_KGR as prod_name_kgr,
    p.CATEGORY_BOD as category_bod,
    p.IS_SHIBU_25PCT as is_shibu,
    NVL(o.REVENUE_SRC_VND, 0) as amount_
from SLV_FACT_DMX_SELLOUT o, 
     oax_user.DW_NS_DAY_D d,
     dim_product p
where o.date_key = d.CAL_DAY_ID
  and o.dmx_prod_id = p.PROD_ID_KGR