select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    

with all_values as (

    select
        order_status as value_field,
        count(*) as n_records

    from "raw"."dev"."stg_jaffle_shop__orders"
    group by order_status

)

select *
from all_values
where value_field not in (
    'completed','shipped','returned','return_pending','placed'
)



      
    ) dbt_internal_test