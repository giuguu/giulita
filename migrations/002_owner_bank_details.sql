-- Migración aditiva: datos bancarios de propietarios.
--
-- Agrega el tipo de cuenta como campo independiente y normaliza los registros
-- antiguos que tenían el tipo de cuenta dentro del nombre del banco
-- (por ejemplo, "Santander cta/cte").
--
-- No elimina columnas ni registros. Los valores que no se reconocen con
-- certeza se dejan intactos. Antes de ejecutarla en producción, haz un respaldo
-- de la tabla owners.
--
-- Es idempotente: se puede ejecutar más de una vez sin duplicar cambios.

BEGIN;

-- =========================================================
-- 1. NUEVO CAMPO: TIPO DE CUENTA
-- =========================================================

ALTER TABLE owners
    ADD COLUMN IF NOT EXISTS bank_account_type TEXT NOT NULL DEFAULT '';

COMMENT ON COLUMN owners.bank_account_type IS
    'Tipo de cuenta bancaria: Cuenta Corriente, Cuenta Vista, Cuenta de Ahorro, Cuenta RUT, Cuenta Chequera Electrónica u Otra';

-- =========================================================
-- 2. MIGRACIÓN SEGURA DEL TEXTO ANTIGUO
-- =========================================================
-- Solo se infiere el tipo cuando el nombre del banco lo dice de forma
-- explícita. Si no hay certeza, el campo queda vacío para que se complete al
-- editar el propietario.

UPDATE owners
SET bank_account_type = 'Cuenta Corriente'
WHERE bank_account_type = ''
  AND bank_name <> ''
  AND (
      translate(lower(bank_name), 'áéíóúü', 'aeiouu')
          ~ '(cta|cuenta)[[:space:]/.-]*(cte|corriente)'
      OR translate(lower(bank_name), 'áéíóúü', 'aeiouu')
          ~ '(^|[^a-z])corriente([^a-z]|$)'
  );

UPDATE owners
SET bank_account_type = 'Cuenta Vista'
WHERE bank_account_type = ''
  AND bank_name <> ''
  AND translate(lower(bank_name), 'áéíóúü', 'aeiouu')
      ~ '(^|[^a-z])(cta|cuenta)[[:space:]/.-]*vista([^a-z]|$)';

UPDATE owners
SET bank_account_type = 'Cuenta de Ahorro'
WHERE bank_account_type = ''
  AND bank_name <> ''
  AND translate(lower(bank_name), 'áéíóúü', 'aeiouu')
      ~ '(^|[^a-z])(cta|cuenta)[[:space:]/.-]*ahorro([^a-z]|$)';

UPDATE owners
SET bank_account_type = 'Cuenta RUT'
WHERE bank_account_type = ''
  AND bank_name <> ''
  AND translate(lower(bank_name), 'áéíóúü', 'aeiouu')
      ~ '(^|[^a-z])rut([^a-z]|$)';

UPDATE owners
SET bank_account_type = 'Cuenta Chequera Electrónica'
WHERE bank_account_type = ''
  AND bank_name <> ''
  AND translate(lower(bank_name), 'áéíóúü', 'aeiouu')
      ~ 'chequera';

-- =========================================================
-- 3. NORMALIZACIÓN DEL NOMBRE DEL BANCO
-- =========================================================
-- El tipo de cuenta ya quedó guardado en su propia columna. Ahora se limpia
-- el nombre del banco para que la vista y el selector muestren una sola
-- entidad. Los valores desconocidos se conservan tal como estaban.

WITH normalized AS (
    SELECT
        id,
        bank_name AS original,
        translate(lower(COALESCE(bank_name, '')), 'áéíóúü', 'aeiouu') AS norm
    FROM owners
), canonical AS (
    SELECT
        id,
        original,
        CASE
            WHEN norm LIKE '%santander%' THEN 'Banco Santander'
            WHEN norm LIKE '%bancoestado%'
              OR norm ~ '(^|[^a-z])estado([^a-z]|$)' THEN 'BancoEstado'
            WHEN norm LIKE '%bci%'
              OR norm LIKE '%credito e inversiones%' THEN 'Banco BCI'
            WHEN norm LIKE '%falabella%' THEN 'Banco Falabella'
            WHEN norm LIKE '%scotiabank%' THEN 'Banco Scotiabank'
            WHEN norm LIKE '%itau%' THEN 'Banco Itaú'
            WHEN norm LIKE '%ripley%' THEN 'Banco Ripley'
            WHEN norm LIKE '%security%' THEN 'Banco Security'
            WHEN norm LIKE '%bice%' THEN 'Banco BICE'
            WHEN norm LIKE '%consorcio%' THEN 'Banco Consorcio'
            WHEN norm LIKE '%internacional%' THEN 'Banco Internacional'
            WHEN norm LIKE '%btg%' THEN 'Banco BTG Pactual Chile'
            WHEN norm LIKE '%coopeuch%' THEN 'Coopeuch'
            WHEN norm LIKE '%tenpo%' THEN 'Tenpo'
            WHEN norm LIKE '%mercado pago%'
              OR norm LIKE '%mercadopago%' THEN 'Mercado Pago'
            WHEN norm LIKE '%efectivo%' THEN 'Efectivo'
            WHEN norm ~ '(^|[^a-z])chile([^a-z]|$)' THEN 'Banco de Chile'
            ELSE original
        END AS new_name
    FROM normalized
)
UPDATE owners o
SET bank_name = c.new_name
FROM canonical c
WHERE o.id = c.id
  AND c.original <> ''
  AND c.new_name <> c.original;

-- =========================================================
-- 4. INTEGRIDAD DEL NUEVO CAMPO
-- =========================================================

ALTER TABLE owners
    DROP CONSTRAINT IF EXISTS owners_bank_account_type_check;

ALTER TABLE owners
    ADD CONSTRAINT owners_bank_account_type_check
    CHECK (
        bank_account_type IN (
            '',
            'Cuenta Corriente',
            'Cuenta Vista',
            'Cuenta de Ahorro',
            'Cuenta RUT',
            'Cuenta Chequera Electrónica',
            'Otra'
        )
    );

COMMIT;
