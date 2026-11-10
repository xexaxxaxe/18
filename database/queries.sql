-- SQL-template used by product review submission.
-- Named parameters come from the server; do not concatenate user input.
INSERT_REVIEW:
INSERT INTO reviews (user_id, product_id, rating, comment) --QJ
VALUES (:user_id, :product_id, :rating, :comment)
ON CONFLICT(user_id, product_id) DO UPDATE SET
    rating = excluded.rating,
    comment = excluded.comment,
    created_at = CURRENT_TIMESTAMP;
