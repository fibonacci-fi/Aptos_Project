-- Schema for aptos_transactions
CREATE TABLE aptos_transactions (    id integer NOT NULL,
    version bigint NOT NULL,
    timestamp timestamp with time zone,
    pool_address text NOT NULL,
    coin1 text NOT NULL,
    coin2 text NOT NULL,
    provider text NOT NULL,
    volume double precision,
    delta_x double precision,
    price_x double precision,
    fees double precision,
    tvl double precision,
    slippage double precision,
    decimal_x numeric(10,2),
    delta_y numeric,
    price_y numeric,
    created_at timestamp with time zone,
    pool_name character varying
);

-- Schema for aptos_pools
CREATE TABLE aptos_pools (    id bigint NOT NULL,
    timestamp timestamp with time zone NOT NULL,
    provider text NOT NULL,
    pool_address text NOT NULL,
    token_a text NOT NULL,
    token_b text NOT NULL,
    tvl double precision,
    volume_day double precision,
    volume_week double precision,
    volume_month double precision,
    fees_day double precision,
    fees_week double precision,
    fees_month double precision,
    state jsonb,
    curve text,
    amp double precision,
    median_slippage_1d numeric,
    median_slippage_7d numeric,
    median_slippage_30d numeric,
    pool_name character varying(255)
);

-- Triggers
CREATE TRIGGER update_timestamp_trigger BEFORE INSERT ON aptos_pools FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER update_timestamp_trigger BEFORE UPDATE ON aptos_pools FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER transactions_after_insert AFTER INSERT ON aptos_transactions FOR EACH ROW EXECUTE FUNCTION update_pool_metrics();

-- Functions
CREATE OR REPLACE FUNCTION public.update_pool_metrics()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    volume_1d NUMERIC;
    volume_7d NUMERIC;
    volume_30d NUMERIC;
    fees_1d NUMERIC;
    fees_7d NUMERIC;
    fees_30d NUMERIC;
    median_slippage_1d NUMERIC;
    median_slippage_7d NUMERIC;
    median_slippage_30d NUMERIC;
BEGIN
    -- Calculate volume and fees for 1, 7, and 30 days
    SELECT
        SUM(CASE WHEN timestamp >= (NEW.timestamp - INTERVAL '1 day') THEN volume ELSE 0 END) AS volume_1d,
        SUM(CASE WHEN timestamp >= (NEW.timestamp - INTERVAL '1 day') THEN fees ELSE 0 END) AS fees_1d,
        SUM(CASE WHEN timestamp >= (NEW.timestamp - INTERVAL '7 days') THEN volume ELSE 0 END) AS volume_7d,
        SUM(CASE WHEN timestamp >= (NEW.timestamp - INTERVAL '7 days') THEN fees ELSE 0 END) AS fees_7d,
        SUM(CASE WHEN timestamp >= (NEW.timestamp - INTERVAL '30 days') THEN volume ELSE 0 END) AS volume_30d,
        SUM(CASE WHEN timestamp >= (NEW.timestamp - INTERVAL '30 days') THEN fees ELSE 0 END) AS fees_30d,
        -- Calculate median slippage for 1, 7, and 30 days
        percentile_cont(0.5) WITHIN GROUP (ORDER BY slippage) AS median_slippage_1d,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY slippage) AS median_slippage_7d,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY slippage) AS median_slippage_30d
    INTO
        volume_1d, fees_1d, volume_7d, fees_7d, volume_30d, fees_30d, median_slippage_1d, median_slippage_7d, median_slippage_30d
    FROM aptos_transactions
    WHERE pool_address = NEW.pool_address;

    -- Insert the aggregated values into the aptos_pools table
    INSERT INTO aptos_pools (
        timestamp, provider, pool_address, token_a, token_b, tvl,
        volume_day, volume_week, volume_month, fees_day, fees_week, fees_month,
        median_slippage_1d, median_slippage_7d, median_slippage_30d,
        state, curve, amp, pool_name
    )
    VALUES (
        CURRENT_TIMESTAMP,              -- Use current timestamp
        NEW.provider,                   -- Provider from the new transaction
        NEW.pool_address,               -- Pool address
        NEW.coin1,                      -- Map coin1 to token_a
        NEW.coin2,                      -- Map coin2 to token_b
        NEW.tvl,                        -- Use the latest TVL from the new transaction
        COALESCE(volume_1d, 0),         -- Volume for the last 1 day
        COALESCE(volume_7d, 0),         -- Volume for the last 7 days
        COALESCE(volume_30d, 0),        -- Volume for the last 30 days
        COALESCE(fees_1d, 0),           -- Fees for the last 1 day
        COALESCE(fees_7d, 0),           -- Fees for the last 7 days
        COALESCE(fees_30d, 0),          -- Fees for the last 30 days
        COALESCE(median_slippage_1d, 0),  -- Median slippage for the last 1 day
        COALESCE(median_slippage_7d, 0),  -- Median slippage for the last 7 days
        COALESCE(median_slippage_30d, 0), -- Median slippage for the last 30 days
        NULL,                           -- Default state (you can modify this as needed)
        NULL,                           -- Curve (if applicable, modify as needed)
        NULL,                           -- Amp (if applicable, modify as needed)
        NEW.pool_name                   -- Insert pool_name from the new transaction
    );

    RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.update_timestamp()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.timestamp = now();  -- Use the correct column name
    RETURN NEW;
END;
$function$
;

