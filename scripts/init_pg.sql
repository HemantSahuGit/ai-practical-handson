-- Sample analytical table for local demos (aligns with Chroma seed descriptions).
CREATE TABLE IF NOT EXISTS public.sales_fact (
    id SERIAL PRIMARY KEY,
    sale_date DATE NOT NULL,
    product_name TEXT NOT NULL,
    region TEXT NOT NULL,
    amount NUMERIC(12, 2) NOT NULL
);

INSERT INTO public.sales_fact (sale_date, product_name, region, amount)
VALUES
    ('2025-01-05', 'Widget A', 'North', 120.50),
    ('2025-01-06', 'Widget A', 'South', 88.00),
    ('2025-01-07', 'Gadget B', 'North', 240.00),
    ('2025-01-08', 'Gadget B', 'West', 64.25),
    ('2025-01-09', 'Widget A', 'West', 150.00);
