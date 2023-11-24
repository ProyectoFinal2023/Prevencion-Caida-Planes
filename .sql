select cuotas_impagas 
from etl.dim_cliente dc 
inner join etl.fact_plan fp 
on dc.cliente_id  = fp.cliente_id 
where dc.cuit_cuil=23325218822