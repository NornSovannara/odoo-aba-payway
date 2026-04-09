-- disable aba payway payment bank account credentials
UPDATE res_partner_bank
   SET production_payway_merchant_id = NULL,
       production_payway_key = NULL,
       production_rsa_public_key = NULL,
       sandbox_payway_merchant_id = NULL,
       sandbox_payway_key = NULL,
       sandbox_rsa_public_key = NULL;
