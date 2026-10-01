-- Local disposable database only; Step 1 column grants at spec 9c393949.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE s1786_step5 TO s1786_step5_runtime;
GRANT USAGE ON SCHEMA public TO s1786_step5_runtime;
GRANT INSERT (id, occurred_at, event_type, outcome, event_count, request_id,
  trace_id, user_id, org_id, client_id, grant_id, profile, tool, scopes_used,
  error_code, policy_decision, pending_action_id, latency_ms, args_hmac,
  result_hmac, ip, user_agent_hmac, binding_terms)
  ON connector_audit_events TO s1786_step5_runtime;
GRANT SELECT (scope, key, disabled) ON connector_switches TO s1786_step5_runtime;
GRANT INSERT (id, user_id, org_id, client_id, first_burst_at, last_burst_at,
  burst_count, throttle_until) ON connector_review_queue TO s1786_step5_runtime;
GRANT UPDATE (last_burst_at, burst_count, throttle_until)
  ON connector_review_queue TO s1786_step5_runtime;
GRANT SELECT (burst_count, reviewed_at) ON connector_review_queue TO s1786_step5_runtime;
GRANT SELECT (id, user_id, organization_id, client_id, scopes, profile,
  revoked_at, created_at) ON connector_oauth_grants TO s1786_step5_runtime;
GRANT SELECT (client_id, client_name) ON connector_oauth_clients TO s1786_step5_runtime;
GRANT SELECT (organization_id, user_id, status, role)
  ON organization_memberships TO s1786_step5_runtime;
GRANT SELECT (id, name) ON organizations TO s1786_step5_runtime;
GRANT SELECT (id, display_name, email) ON users TO s1786_step5_runtime;
GRANT SELECT (user_id) ON seller_profiles TO s1786_step5_runtime;
GRANT SELECT (id, title, slug, description, short_description, category, price,
  privacy_score, compliance_status, data_format, source_row_count, tags,
  published_at, synthetic_queries, status, is_listed, license_code,
  license_version, license_params, license_sha256, covenant_sha256,
  seller_acceptance_id, seller_acceptance_source, license, schema_info,
  update_cadence_days) ON listings TO s1786_step5_runtime;
GRANT SELECT (id, type, created_at, read_at, user_id, archived_at)
  ON notifications TO s1786_step5_runtime;
GRANT SELECT (id, title, description, categories, urgency, status,
  published_at, buyer_id, created_at) ON data_requests TO s1786_step5_runtime;
