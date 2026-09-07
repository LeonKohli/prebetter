-- Apply once to an existing Better Auth database before starting Better Auth 1.7.
-- NULL preserves the default EdDSA/Ed25519 behavior for existing keys.
ALTER TABLE `jwks` ADD COLUMN `alg` text, ADD COLUMN `crv` text;
