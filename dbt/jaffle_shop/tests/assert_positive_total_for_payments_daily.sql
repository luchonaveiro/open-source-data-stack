WITH payments AS (
    SELECT
        *
    FROM
        {{ ref ('stg_stripe__payments') }}
    WHERE
        payment_created_at = '{{ var ("date") }}'
),
test_data AS (
    SELECT
        order_id,
        sum(payment_amount) AS total_amount
FROM
    payments
GROUP BY
    1
)
SELECT
    *
FROM
    test_data
WHERE
    total_amount < 0
