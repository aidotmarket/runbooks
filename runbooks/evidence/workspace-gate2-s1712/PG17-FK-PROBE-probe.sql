\set ON_ERROR_STOP on
\pset pager off
BEGIN;
SELECT version(),current_setting('server_version_num');
CREATE TEMP TABLE probe_orders(id uuid PRIMARY KEY,seller_id uuid,buyer_id uuid,listing_id uuid,stripe_payment_intent_id varchar(255),status text NOT NULL DEFAULT 'created',CONSTRAINT uq_s1712_order_discovery UNIQUE(id,seller_id,buyer_id,listing_id,stripe_payment_intent_id));
CREATE TEMP TABLE probe_authority(order_id uuid NOT NULL,seller_id uuid NOT NULL,buyer_id uuid NOT NULL,listing_id uuid NOT NULL,payment_intent_id varchar(255) NOT NULL,CONSTRAINT fk_s1712_registered_order_discovery FOREIGN KEY(order_id,seller_id,buyer_id,listing_id,payment_intent_id) REFERENCES probe_orders(id,seller_id,buyer_id,listing_id,stripe_payment_intent_id) MATCH SIMPLE ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE);
CREATE TEMP TABLE probe_results(test text PRIMARY KEY,sqlstate text,expected text);
INSERT INTO probe_orders VALUES ('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000004','pi_probe_registered','created');
INSERT INTO probe_authority SELECT id,seller_id,buyer_id,listing_id,stripe_payment_intent_id FROM probe_orders;
INSERT INTO probe_results VALUES ('valid_complete_registration','00000','00000');
DO $probe$
DECLARE col text; state text; expected text; value text; expr text; child_col text;
BEGIN
FOREACH col IN ARRAY ARRAY['id','seller_id','buyer_id','listing_id','stripe_payment_intent_id'] LOOP
 expected:=CASE WHEN col='id' THEN '23502' ELSE '23503' END;
 BEGIN EXECUTE format('UPDATE probe_orders SET %I=NULL WHERE id=%L::uuid',col,'00000000-0000-0000-0000-000000000001');state:='00000';EXCEPTION WHEN OTHERS THEN GET STACKED DIAGNOSTICS state=RETURNED_SQLSTATE;END;
 IF state<>expected THEN RAISE EXCEPTION 'Unexpected parent NULL behavior % %',col,state;END IF;
 INSERT INTO probe_results VALUES ('parent_null_'||col,state,expected);
 value:=CASE WHEN col='stripe_payment_intent_id' THEN 'pi_probe_changed' ELSE '00000000-0000-0000-0000-000000000099' END;
 BEGIN EXECUTE format('UPDATE probe_orders SET %I=%L WHERE id=%L::uuid',col,value,'00000000-0000-0000-0000-000000000001');state:='00000';EXCEPTION WHEN OTHERS THEN GET STACKED DIAGNOSTICS state=RETURNED_SQLSTATE;END;
 IF state<>'23503' THEN RAISE EXCEPTION 'Unexpected parent change behavior % %',col,state;END IF;
 INSERT INTO probe_results VALUES ('parent_change_'||col,state,'23503');
 child_col:=CASE WHEN col='id' THEN 'order_id' WHEN col='stripe_payment_intent_id' THEN 'payment_intent_id' ELSE col END;
 SELECT string_agg(CASE WHEN x=col THEN 'NULL' ELSE quote_ident(x) END,',' ORDER BY ord) INTO expr FROM unnest(ARRAY['id','seller_id','buyer_id','listing_id','stripe_payment_intent_id']) WITH ORDINALITY AS t(x,ord);
 BEGIN EXECUTE 'INSERT INTO probe_authority SELECT '||expr||' FROM probe_orders';state:='00000';EXCEPTION WHEN OTHERS THEN GET STACKED DIAGNOSTICS state=RETURNED_SQLSTATE;END;
 IF state<>'23502' THEN RAISE EXCEPTION 'Unexpected child NULL behavior % %',child_col,state;END IF;
 INSERT INTO probe_results VALUES ('child_null_'||child_col,state,'23502');
END LOOP;
BEGIN DELETE FROM probe_orders WHERE id='00000000-0000-0000-0000-000000000001';state:='00000';EXCEPTION WHEN OTHERS THEN GET STACKED DIAGNOSTICS state=RETURNED_SQLSTATE;END;
IF state<>'23503' THEN RAISE EXCEPTION 'Unexpected parent deletion %',state;END IF;
INSERT INTO probe_results VALUES ('parent_delete',state,'23503');
END $probe$;
UPDATE probe_orders SET status='paid' WHERE id='00000000-0000-0000-0000-000000000001';
INSERT INTO probe_results SELECT 'registered_status_update','00000','00000' WHERE (SELECT status FROM probe_orders WHERE id='00000000-0000-0000-0000-000000000001')='paid';
INSERT INTO probe_orders VALUES ('00000000-0000-0000-0000-000000000010','00000000-0000-0000-0000-000000000020','00000000-0000-0000-0000-000000000030','00000000-0000-0000-0000-000000000040',NULL,'created');
INSERT INTO probe_results VALUES ('unregistered_nullable_parent','00000','00000');
DO $probe$
DECLARE state text;
BEGIN
BEGIN INSERT INTO probe_authority SELECT id,seller_id,buyer_id,listing_id,'pi_no_parent_match' FROM probe_orders WHERE id='00000000-0000-0000-0000-000000000010';state:='00000';EXCEPTION WHEN OTHERS THEN GET STACKED DIAGNOSTICS state=RETURNED_SQLSTATE;END;
IF state<>'23503' THEN RAISE EXCEPTION 'Null parent falsely matched nonnull child %',state;END IF;
INSERT INTO probe_results VALUES ('null_parent_nonnull_child_refused',state,'23503');
BEGIN INSERT INTO probe_authority SELECT id,seller_id,buyer_id,listing_id,stripe_payment_intent_id FROM probe_orders WHERE id='00000000-0000-0000-0000-000000000010';state:='00000';EXCEPTION WHEN OTHERS THEN GET STACKED DIAGNOSTICS state=RETURNED_SQLSTATE;END;
IF state<>'23502' THEN RAISE EXCEPTION 'Null parent plus null child escaped %',state;END IF;
INSERT INTO probe_results VALUES ('null_parent_null_child_refused',state,'23502');
END $probe$;
UPDATE probe_orders SET seller_id=NULL,stripe_payment_intent_id='pi_unregistered' WHERE id='00000000-0000-0000-0000-000000000010';
UPDATE probe_orders SET stripe_payment_intent_id=NULL,status='created' WHERE id='00000000-0000-0000-0000-000000000010';
INSERT INTO probe_results VALUES ('unregistered_identity_and_null_updates','00000','00000');
SELECT conname,pg_get_constraintdef(oid,true),convalidated,condeferrable,condeferred FROM pg_constraint WHERE conrelid IN ('probe_orders'::regclass,'probe_authority'::regclass) ORDER BY conname;
SELECT c.relname,i.indisunique,i.indisvalid,i.indisready,i.indimmediate FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid WHERE i.indrelid='probe_orders'::regclass ORDER BY c.relname;
SELECT c.relname,t.tgname,t.tgenabled,t.tgisinternal,p.proname FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_proc p ON p.oid=t.tgfoid WHERE t.tgconstraint=(SELECT oid FROM pg_constraint WHERE conname='fk_s1712_registered_order_discovery' AND conrelid='probe_authority'::regclass) ORDER BY c.relname,p.proname;
SELECT json_agg(row_to_json(r) ORDER BY test) AS results FROM probe_results r;
SELECT count(*) AS cases,bool_and(sqlstate=expected) AS all_expected FROM probe_results;
SELECT count(*) AS retained_authorities FROM probe_authority;
ROLLBACK;
