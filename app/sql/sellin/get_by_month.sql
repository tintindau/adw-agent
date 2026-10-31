SELECT
	si.gh_date_key AS date_,
	si.gh_month_key AS month_,
	s.store_name,
	s.stock_code AS store_code,
	s.region_name_tmp AS region,
	s.province,
	p.prod_id_kgr AS prod_code,
	p.prod_name_kgr AS prod_name,
	p.model_name,
	p.category_bod AS prod_class_dmx,
	p.sub_category AS prod_category,
	p.is_shibu_25pct AS is_shibu,
	p.is_mockup_dummy AS is_dummy,
	si.gh_flow,
	NVL(si.gh_so_qty, 0) AS gh_so_qty,
	NVL(si.gh_so_promo_qty, 0) AS gh_so_promo_qty,
	NVL(si.gh_so_out_qty, 0) AS gh_so_out_qty,
	NVL(si.gh_so_out_qty_new, 0) AS gh_so_out_qty_new,
	NVL(si.gh_si_amount, 0) AS gh_si_amount,
	NVL(si.gh_si_qty, 0) AS gh_si_qty,
	NVL(si.gh_si_promo_qty, 0) AS gh_si_promo_qty,
	NVL(si.gh_si_qty_new, 0) AS gh_si_qty_new
FROM GLD_HIST_DMX_SISO_DAY si
JOIN SLV_DIM_DMX_STORE s
	ON si.gh_store_key = s.store_key
JOIN dim_product p
	ON si.gh_dmx_prod_id = p.prod_id_kgr
WHERE si.gh_month_key = :month_
  AND (:date_ IS NULL OR si.gh_date_key = :date_)
	AND (:from_date IS NULL OR si.gh_date_key >= :from_date)
	AND (:to_date IS NULL OR si.gh_date_key <= :to_date)
  AND (
	  :store_name IS NULL
	  OR INSTR(UPPER(s.store_name), UPPER(TRIM(:store_name))) > 0
	  OR UTL_MATCH.JARO_WINKLER_SIMILARITY(UPPER(s.store_name), UPPER(TRIM(:store_name))) >= 85
  )
  AND (:store_code IS NULL OR INSTR(UPPER(s.stock_code), UPPER(TRIM(:store_code))) > 0)
  AND (
	  :region IS NULL
	  OR INSTR(UPPER(s.region_name_tmp), UPPER(TRIM(:region))) > 0
	  OR UTL_MATCH.JARO_WINKLER_SIMILARITY(UPPER(s.region_name_tmp), UPPER(TRIM(:region))) >= 85
  )
  AND (
	  :province IS NULL
	  OR INSTR(UPPER(s.province), UPPER(TRIM(:province))) > 0
	  OR UTL_MATCH.JARO_WINKLER_SIMILARITY(UPPER(s.province), UPPER(TRIM(:province))) >= 85
  )
  AND (:prod_code IS NULL OR INSTR(UPPER(p.prod_id_kgr), UPPER(TRIM(:prod_code))) > 0)
  AND (
	  :prod_name IS NULL
	  OR INSTR(UPPER(p.prod_name_kgr), UPPER(TRIM(:prod_name))) > 0
	  OR UTL_MATCH.JARO_WINKLER_SIMILARITY(UPPER(p.prod_name_kgr), UPPER(TRIM(:prod_name))) >= 85
  )
  AND (
	  :model_name IS NULL
	  OR INSTR(UPPER(p.model_name), UPPER(TRIM(:model_name))) > 0
	  OR UTL_MATCH.JARO_WINKLER_SIMILARITY(UPPER(p.model_name), UPPER(TRIM(:model_name))) >= 85
  )
  AND (
	  :prod_class_dmx IS NULL
	  OR INSTR(UPPER(p.category_bod), UPPER(TRIM(:prod_class_dmx))) > 0
	  OR UTL_MATCH.JARO_WINKLER_SIMILARITY(UPPER(p.category_bod), UPPER(TRIM(:prod_class_dmx))) >= 85
  )
  AND (
	  :prod_category IS NULL
	  OR INSTR(UPPER(p.sub_category), UPPER(TRIM(:prod_category))) > 0
	  OR UTL_MATCH.JARO_WINKLER_SIMILARITY(UPPER(p.sub_category), UPPER(TRIM(:prod_category))) >= 85
  )
  AND (:is_shibu IS NULL OR p.is_shibu_25pct = :is_shibu)
  AND (:is_dummy IS NULL OR p.is_mockup_dummy = :is_dummy)
