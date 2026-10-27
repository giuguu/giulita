-- Migración aditiva de la aplicación de arriendos.
-- No elimina tablas, columnas ni registros. Se puede ejecutar una sola vez
-- (o repetir: las partes son idempotentes en su mayoría).
--
-- Antes de ejecutarla en producción: hacer respaldo de la base.

BEGIN;

-- =========================================================
-- PROPIETARIOS
-- =========================================================

ALTER TABLE owners ADD COLUMN IF NOT EXISTS bank_name TEXT NOT NULL DEFAULT '';
ALTER TABLE owners ADD COLUMN IF NOT EXISTS bank_account TEXT NOT NULL DEFAULT '';
ALTER TABLE owners ADD COLUMN IF NOT EXISTS bank_holder TEXT NOT NULL DEFAULT '';
ALTER TABLE owners ADD COLUMN IF NOT EXISTS commission_percent NUMERIC(5, 2) NOT NULL DEFAULT 10;
ALTER TABLE owners ADD COLUMN IF NOT EXISTS notes TEXT NOT NULL DEFAULT '';
ALTER TABLE owners ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE owners ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE owners DROP CONSTRAINT IF EXISTS owners_commission_percent_check;
ALTER TABLE owners ADD CONSTRAINT owners_commission_percent_check
    CHECK (commission_percent BETWEEN 0 AND 100);

-- =========================================================
-- DEPARTAMENTOS
-- =========================================================

ALTER TABLE departments ADD COLUMN IF NOT EXISTS address TEXT NOT NULL DEFAULT '';
ALTER TABLE departments ADD COLUMN IF NOT EXISTS access_instructions TEXT NOT NULL DEFAULT '';
ALTER TABLE departments ADD COLUMN IF NOT EXISTS wifi_name TEXT NOT NULL DEFAULT '';
ALTER TABLE departments ADD COLUMN IF NOT EXISTS wifi_password TEXT NOT NULL DEFAULT '';
ALTER TABLE departments ADD COLUMN IF NOT EXISTS amenities JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE departments ADD COLUMN IF NOT EXISTS notes TEXT NOT NULL DEFAULT '';
ALTER TABLE departments ADD COLUMN IF NOT EXISTS default_check_in_time TEXT NOT NULL DEFAULT '15:00';
ALTER TABLE departments ADD COLUMN IF NOT EXISTS default_check_out_time TEXT NOT NULL DEFAULT '11:00';
ALTER TABLE departments ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
ALTER TABLE departments ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE departments DROP CONSTRAINT IF EXISTS departments_capacity_check;
ALTER TABLE departments ADD CONSTRAINT departments_capacity_check CHECK (capacity >= 1);
ALTER TABLE departments DROP CONSTRAINT IF EXISTS departments_winter_price_check;
ALTER TABLE departments ADD CONSTRAINT departments_winter_price_check CHECK (winter_price >= 0);
ALTER TABLE departments DROP CONSTRAINT IF EXISTS departments_summer_price_check;
ALTER TABLE departments ADD CONSTRAINT departments_summer_price_check CHECK (summer_price >= 0);

-- =========================================================
-- RESERVAS
-- =========================================================

ALTER TABLE reservations ADD COLUMN IF NOT EXISTS deposit_due BIGINT NOT NULL DEFAULT 0;
ALTER TABLE reservations ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'Directo';
ALTER TABLE reservations ADD COLUMN IF NOT EXISTS email TEXT NOT NULL DEFAULT '';
ALTER TABLE reservations ADD COLUMN IF NOT EXISTS document TEXT NOT NULL DEFAULT '';
ALTER TABLE reservations ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;
ALTER TABLE reservations ADD COLUMN IF NOT EXISTS cancelled_reason TEXT NOT NULL DEFAULT '';
ALTER TABLE reservations ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE reservations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE reservations
SET deposit_due = ROUND(total * deposit_percent / 100.0)::BIGINT
WHERE deposit_due = 0 AND total > 0 AND deposit_percent > 0;

-- =========================================================
-- PAGOS
-- =========================================================

ALTER TABLE payments ADD COLUMN IF NOT EXISTS method TEXT NOT NULL DEFAULT 'Transferencia';
ALTER TABLE payments ADD COLUMN IF NOT EXISTS reference TEXT NOT NULL DEFAULT '';
ALTER TABLE payments ADD COLUMN IF NOT EXISTS receipt_note TEXT NOT NULL DEFAULT '';
ALTER TABLE payments ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE payments ADD COLUMN IF NOT EXISTS voided_at TIMESTAMPTZ;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS void_reason TEXT NOT NULL DEFAULT '';

ALTER TABLE payments ALTER COLUMN payment_date DROP DEFAULT;
ALTER TABLE payments ALTER COLUMN payment_date TYPE DATE USING NULLIF(payment_date, '')::DATE;
ALTER TABLE payments ALTER COLUMN payment_date SET DEFAULT CURRENT_DATE;
ALTER TABLE payments ALTER COLUMN payment_date SET NOT NULL;

ALTER TABLE payments DROP CONSTRAINT IF EXISTS payments_amount_check;
ALTER TABLE payments ADD CONSTRAINT payments_amount_check CHECK (amount > 0);

-- Conciliación: el usuario confirmó que lo que figuraba como "abonado"
-- es dinero realmente recibido. Creamos un pago histórico por la diferencia
-- para que la tabla payments sea la única fuente de verdad.
INSERT INTO payments (reservation_id, amount, payment_date, note, method, created_at)
SELECT
    r.id,
    (r.deposited - COALESCE(SUM(p.amount), 0))::INTEGER,
    COALESCE(r.check_in_date, r.check_in::DATE),
    'Pago migrado desde el abono ya registrado en la reserva',
    'Migrado',
    NOW()
FROM reservations r
LEFT JOIN payments p
    ON p.reservation_id = r.id
   AND p.voided_at IS NULL
GROUP BY r.id, r.deposited, r.check_in_date, r.check_in
HAVING r.deposited > COALESCE(SUM(p.amount), 0);

UPDATE reservations r
SET deposited = COALESCE((
    SELECT SUM(p.amount)::BIGINT
    FROM payments p
    WHERE p.reservation_id = r.id AND p.voided_at IS NULL
), 0);

UPDATE reservations
SET status = CASE
    WHEN status = 'Cancelada' THEN 'Cancelada'
    WHEN deposited <= 0 THEN 'Sin abono'
    WHEN deposited >= total THEN 'Pagado completamente'
    ELSE 'Abono recibido'
END;

ALTER TABLE reservations DROP CONSTRAINT IF EXISTS reservations_status_check;
ALTER TABLE reservations ADD CONSTRAINT reservations_status_check
    CHECK (status IN ('Sin abono', 'Abono recibido', 'Pagado completamente', 'Cancelada'));

ALTER TABLE reservations DROP CONSTRAINT IF EXISTS reservations_deposit_due_check;
ALTER TABLE reservations ADD CONSTRAINT reservations_deposit_due_check CHECK (deposit_due >= 0);
ALTER TABLE reservations DROP CONSTRAINT IF EXISTS reservations_total_check;
ALTER TABLE reservations ADD CONSTRAINT reservations_total_check CHECK (total >= 0);

-- =========================================================
-- LIQUIDACIONES
-- =========================================================

ALTER TABLE owner_liquidation_settings DROP CONSTRAINT IF EXISTS owner_liquidation_settings_commission_percent_check;
ALTER TABLE owner_liquidation_settings ADD CONSTRAINT owner_liquidation_settings_commission_percent_check
    CHECK (commission_percent BETWEEN 0 AND 100);

ALTER TABLE owner_liquidations DROP CONSTRAINT IF EXISTS owner_liquidations_commission_percent_check;
ALTER TABLE owner_liquidations ADD CONSTRAINT owner_liquidations_commission_percent_check
    CHECK (commission_percent BETWEEN 0 AND 100);

ALTER TABLE owner_liquidations ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'Emitida';
ALTER TABLE owner_liquidations ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ;
ALTER TABLE owner_liquidations ADD COLUMN IF NOT EXISTS payment_reference TEXT NOT NULL DEFAULT '';
ALTER TABLE owner_liquidations ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

ALTER TABLE owner_liquidations DROP CONSTRAINT IF EXISTS owner_liquidations_status_check;
ALTER TABLE owner_liquidations ADD CONSTRAINT owner_liquidations_status_check
    CHECK (status IN ('Borrador', 'Emitida', 'Pagada', 'Anulada'));

-- =========================================================
-- LIQUIDACIONES MENSUALES POR PROPIETARIO
-- =========================================================

CREATE TABLE IF NOT EXISTS owner_statements (
    id BIGSERIAL PRIMARY KEY,
    owner_id BIGINT NOT NULL REFERENCES owners(id) ON DELETE RESTRICT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'Borrador'
        CHECK (status IN ('Borrador', 'Emitida', 'Pagada', 'Anulada')),
    gross_total BIGINT NOT NULL DEFAULT 0,
    commission_total BIGINT NOT NULL DEFAULT 0,
    expenses_total BIGINT NOT NULL DEFAULT 0,
    net_total BIGINT NOT NULL DEFAULT 0,
    paid_at TIMESTAMPTZ,
    payment_reference TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT owner_statements_period_check CHECK (period_end >= period_start)
);

CREATE TABLE IF NOT EXISTS owner_statement_items (
    id BIGSERIAL PRIMARY KEY,
    statement_id BIGINT NOT NULL REFERENCES owner_statements(id) ON DELETE CASCADE,
    reservation_id BIGINT NOT NULL REFERENCES reservations(id) ON DELETE RESTRICT,
    owner_liquidation_id BIGINT REFERENCES owner_liquidations(id) ON DELETE SET NULL,
    condo_name TEXT NOT NULL DEFAULT '',
    department_name TEXT NOT NULL DEFAULT '',
    guest_name TEXT NOT NULL DEFAULT '',
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    nights INTEGER NOT NULL DEFAULT 0,
    price_night BIGINT NOT NULL DEFAULT 0,
    gross_total BIGINT NOT NULL DEFAULT 0,
    commission_percent NUMERIC(5, 2) NOT NULL DEFAULT 0,
    commission_amount BIGINT NOT NULL DEFAULT 0,
    expenses_total BIGINT NOT NULL DEFAULT 0,
    net_total BIGINT NOT NULL DEFAULT 0,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================================================
-- TEMPORADAS Y PRECIOS
-- =========================================================

CREATE TABLE IF NOT EXISTS seasons (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    price_per_night BIGINT NOT NULL CHECK (price_per_night >= 0),
    min_nights INTEGER NOT NULL DEFAULT 1 CHECK (min_nights >= 1),
    department_id BIGINT REFERENCES departments(id) ON DELETE CASCADE,
    condo TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT seasons_dates_check CHECK (end_date > start_date)
);

-- =========================================================
-- BLOQUEOS POR MANTENCIÓN
-- =========================================================

CREATE TABLE IF NOT EXISTS department_blocks (
    id BIGSERIAL PRIMARY KEY,
    department_id BIGINT NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    reason TEXT NOT NULL DEFAULT 'Mantención',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT department_blocks_dates_check CHECK (end_date > start_date)
);

-- =========================================================
-- AUDITORÍA
-- =========================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    entity TEXT NOT NULL,
    entity_id BIGINT,
    action TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    actor TEXT NOT NULL DEFAULT 'admin',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================================================
-- MINIATURAS DE IMÁGENES
-- =========================================================

ALTER TABLE condo_images ADD COLUMN IF NOT EXISTS thumb_data BYTEA;
ALTER TABLE condo_images ADD COLUMN IF NOT EXISTS thumb_mime TEXT NOT NULL DEFAULT 'image/jpeg';

-- =========================================================
-- ÍNDICES
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_departments_condo_name
    ON departments (condo, name);
CREATE INDEX IF NOT EXISTS idx_reservations_dates
    ON reservations (department_id, check_in_date, check_out_date);
CREATE INDEX IF NOT EXISTS idx_reservations_status
    ON reservations (status);
CREATE INDEX IF NOT EXISTS idx_payments_reservation_date
    ON payments (reservation_id, payment_date);
CREATE INDEX IF NOT EXISTS idx_owner_statements_period
    ON owner_statements (owner_id, period_start);
CREATE INDEX IF NOT EXISTS idx_seasons_dates
    ON seasons (start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_seasons_department
    ON seasons (department_id);
CREATE INDEX IF NOT EXISTS idx_blocks_department_dates
    ON department_blocks USING GIST (
        department_id,
        daterange(start_date, end_date, '[)')
    );
CREATE INDEX IF NOT EXISTS idx_audit_created
    ON audit_log (created_at DESC);

-- =========================================================
-- TRIGGERS DE updated_at
-- =========================================================

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_owners_updated_at ON owners;
CREATE TRIGGER trg_owners_updated_at BEFORE UPDATE ON owners
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_departments_updated_at ON departments;
CREATE TRIGGER trg_departments_updated_at BEFORE UPDATE ON departments
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_reservations_updated_at ON reservations;
CREATE TRIGGER trg_reservations_updated_at BEFORE UPDATE ON reservations
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_seasons_updated_at ON seasons;
CREATE TRIGGER trg_seasons_updated_at BEFORE UPDATE ON seasons
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_owner_statements_updated_at ON owner_statements;
CREATE TRIGGER trg_owner_statements_updated_at BEFORE UPDATE ON owner_statements
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =========================================================
-- RESERVAS VS. BLOQUEOS
-- =========================================================

CREATE OR REPLACE FUNCTION public.check_reservation_block()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM public.department_blocks b
        WHERE b.department_id = NEW.department_id
          AND daterange(b.start_date, b.end_date, '[)')
              && daterange(
                     COALESCE(NEW.check_in_date, NEW.check_in::DATE),
                     COALESCE(NEW.check_out_date, NEW.check_out::DATE),
                     '[)'
                 )
    ) THEN
        RAISE EXCEPTION 'El departamento tiene un bloqueo por mantención en esas fechas';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_reservation_block_check ON reservations;
CREATE TRIGGER trg_reservation_block_check
BEFORE INSERT OR UPDATE ON reservations
FOR EACH ROW EXECUTE FUNCTION public.check_reservation_block();

CREATE OR REPLACE FUNCTION public.check_block_conflicts()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM public.reservations r
        WHERE r.department_id = NEW.department_id
          AND r.status <> 'Cancelada'
          AND daterange(r.check_in_date, r.check_out_date, '[)')
              && daterange(NEW.start_date, NEW.end_date, '[)')
    ) THEN
        RAISE EXCEPTION 'No se puede bloquear: existen reservas en esas fechas';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_block_reservation_check ON department_blocks;
CREATE TRIGGER trg_block_reservation_check
BEFORE INSERT OR UPDATE ON department_blocks
FOR EACH ROW EXECUTE FUNCTION public.check_block_conflicts();

-- =========================================================
-- RLS Y PERMISOS
-- =========================================================

ALTER TABLE owner_statements ENABLE ROW LEVEL SECURITY;
ALTER TABLE owner_statement_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE seasons ENABLE ROW LEVEL SECURITY;
ALTER TABLE department_blocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- La app se conecta con el rol postgres, que no pasa por RLS.
-- La Data API no debe poder leer estas tablas con la clave anónima.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon;

COMMIT;
