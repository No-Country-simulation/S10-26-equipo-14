BEGIN;

-- Running upgrade cb0deba93496 -> 4db267e3b121

CREATE TABLE categories (
    id BIGSERIAL NOT NULL,
    name VARCHAR(120) NOT NULL,
    slug VARCHAR(140) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_categories_name UNIQUE (name),
    CONSTRAINT uq_categories_slug UNIQUE (slug)
);

CREATE TABLE products (
    id BIGSERIAL NOT NULL,
    name VARCHAR(250) NOT NULL,
    brand VARCHAR(120),
    model VARCHAR(120),
    description TEXT,
    category_id BIGINT,
    PRIMARY KEY (id),
    FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE SET NULL
);

CREATE INDEX ix_products_name ON products (name);

CREATE INDEX ix_products_category_id ON products (category_id);

CREATE TABLE store_products (
    id BIGSERIAL NOT NULL,
    store_id BIGINT NOT NULL,
    product_id BIGINT,
    external_id VARCHAR(180),
    product_url TEXT NOT NULL,
    product_name VARCHAR(300) NOT NULL,
    currency VARCHAR(3) DEFAULT 'ARS' NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT,
    FOREIGN KEY(store_id) REFERENCES stores (id) ON DELETE RESTRICT,
    CONSTRAINT uq_store_products_store_external UNIQUE (store_id, external_id)
);

CREATE INDEX ix_store_products_store_id ON store_products (store_id);

CREATE INDEX ix_store_products_product_id ON store_products (product_id);

CREATE TABLE price_observations (
    id BIGSERIAL NOT NULL,
    store_product_id BIGINT NOT NULL,
    amount NUMERIC(14, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'ARS' NOT NULL,
    observed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(store_product_id) REFERENCES store_products (id) ON DELETE RESTRICT,
    CONSTRAINT uq_price_observations_product_time UNIQUE (store_product_id, observed_at),
    CONSTRAINT ck_price_observations_amount_positive CHECK (amount > 0)
);

CREATE INDEX ix_price_observations_product_observed ON price_observations (store_product_id, observed_at);

CREATE TABLE exchange_rates (
    id BIGSERIAL NOT NULL,
    source VARCHAR(100) NOT NULL,
    rate_type VARCHAR(30) NOT NULL,
    base_currency VARCHAR(3) DEFAULT 'USD' NOT NULL,
    quote_currency VARCHAR(3) DEFAULT 'ARS' NOT NULL,
    rate NUMERIC(18, 6) NOT NULL,
    observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_exchange_rates_observation UNIQUE (source, rate_type, base_currency, quote_currency, observed_at),
    CONSTRAINT ck_exchange_rates_rate_positive CHECK (rate > 0)
);

CREATE INDEX ix_exchange_rates_type_date ON exchange_rates (rate_type, observed_at);

CREATE TABLE extraction_runs (
    id BIGSERIAL NOT NULL,
    source VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE,
    records_seen BIGINT DEFAULT '0' NOT NULL,
    error_summary TEXT,
    PRIMARY KEY (id)
);

CREATE INDEX ix_extraction_runs_source ON extraction_runs (source);

UPDATE alembic_version SET version_num='4db267e3b121' WHERE alembic_version.version_num = 'cb0deba93496';

COMMIT;
