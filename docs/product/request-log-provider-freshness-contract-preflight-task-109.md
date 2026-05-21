# Task 109 — Request-log/provider/source/freshness contract preflight (documentation/design only)

## A) Purpose

Deze preflight definieert een toekomstige storage/API contractbasis voor:
- request logging;
- provider/source metadata;
- freshness-audit records.

Dit document is expliciet **pre-implementatie** en **non-runtime**.

Expliciete afbakening:
- dit is **geen runtime task**;
- dit doet **geen data fetching**;
- dit maakt **geen storage tabellen**;
- dit voegt **geen endpoints** toe;
- dit unlockt **geen analyse, suggesties, Decision Packages, action drafts of orders**.

## B) Source-of-truth references

- `docs/product/locked-decisions.md`
- `docs/product/current-state.md`
- `docs/product/non-runtime-foundation-preflight-task-108.md`
- `docs/product/version-1-scope-register.md`
- `docs/product/version-1-backlog.md`
- `docs/product/codex-ci-quality-rules.md`
- `docs/product/read-only-readiness-pr-checklist.md`

## C) Contract domain overview

De drie domeinen horen bij elkaar omdat ze samen de volledige auditketen vormen:

1. **Request logs** beantwoorden: wat is aangevraagd, bij wie, wanneer, waarom, met welke pacing/account/context en wat was de uitkomst.
2. **Provider/source metadata** beantwoorden: welke bron data levert, met welke scope/provenance/trust-context.
3. **Freshness-audit records** beantwoorden: of een snapshot/record vers genoeg is voor toekomstig gebruik, en waarom niet (blocked/stale/expired).

## D) Request-log candidate field catalog

| Field name | Required now? | Future storage type hint | Meaning | Allowed values / format | Safety notes | Runtime status |
|---|---|---|---|---|---|---|
| request_log_id | Proposed required | UUID | Unieke request-log identiteit | UUID v4 | Geen businessinhoud | Not implemented |
| correlation_id | Proposed required | UUID/string | Correlatie over flow heen | UUID of stabiele key | Verplicht voor audit trace | Not implemented |
| parent_correlation_id | Optional | UUID/string | Parent flow correlatie | UUID/string/null | Ondersteunt chain-trace | Not implemented |
| idempotency_key | Optional | String | Idempotency referentie | Hash/key | Geen secrets opnemen | Not implemented |
| request_family | Proposed required | Enum/string | Groep requests | `market_data`,`ibkr_status`,`readiness_eval`,... | Future enum, nu voorstel | Not implemented |
| request_purpose | Proposed required | String | Waarom request bestaat | Korte NL/EN code + beschrijving | Auditverplichting | Not implemented |
| created_at | Proposed required | Timestamp | Log-aanmaakmoment | ISO-8601 UTC | Verplicht voor audit | Not implemented |
| completed_at | Optional | Timestamp | Afsluitmoment | ISO-8601 UTC/null | Null toegestaan bij fail/block | Not implemented |
| provider_code | Proposed required | String | Canonieke providercode | `ibkr`,`polygon`,`manual_upload`,... | Niet impliceren dat provider actief is | Not implemented |
| provider_display_name | Optional | String | Leesbare naam | Tekst | UI-hulp, geen logic | Not implemented |
| provider_account_mode | Proposed required | Enum/string | Accountmoduscontext | `paper`,`live`,`unknown` | `unknown` conservatief blokkeren | Not implemented |
| provider_environment | Proposed required | Enum/string | Omgevingscontext | `production`,`sandbox`,`unknown` | `unknown` blokkeren | Not implemented |
| source_type | Proposed required | Enum/string | Bronsoort | `broker`,`market_data`,`user_upload`,... | Moet met provider metadata matchen | Not implemented |
| source_scope | Optional | String | Scope van bron | Vrije scopecode | Audit-only | Not implemented |
| source_priority | Optional | Integer | Prioriteitsvolgorde | 0..n | Geen auto-override zonder policy | Not implemented |
| data_domain | Proposed required | Enum/string | Datadomein | `price_snapshot`,`portfolio`,`fx`,`calendar`,... | Nodig voor freshness policy | Not implemented |
| asset_id | Optional | UUID | Asset identiteit | UUID/null | Alleen referentie | Not implemented |
| asset_listing_id | Optional | UUID | Listing identiteit | UUID/null | Listing-validatie gate blijft leidend | Not implemented |
| ibkr_conid | Optional | Integer/string | IBKR contract id | Positief getal/string | Geen conid => mogelijke blokkade | Not implemented |
| symbol | Optional | String | Ticker/symbool | Tekst/null | Nooit alleen symbol vertrouwen | Not implemented |
| currency | Optional | String | Valuta | ISO-4217/null | Auditcontext | Not implemented |
| exchange | Optional | String | Exchange | MIC/string/null | Auditcontext | Not implemented |
| primary_exchange | Optional | String | Primary exchange | MIC/string/null | Auditcontext | Not implemented |
| account_id_hash | Optional | String | Gehashte accountreferentie | Hash/null | Geen raw account ID | Not implemented |
| portfolio_scope | Optional | String | Portfolio-/watchlistscope | `portfolio`,`watchlist`,`global`,... | Scope expliciet loggen | Not implemented |
| request_kind | Proposed required | Enum/string | Type request | `snapshot`,`detail`,`list`,`probe`,... | Voorstelwaarde | Not implemented |
| request_target | Proposed required | String | Doelresource | Route/resource code | Geen secrets in target | Not implemented |
| request_parameters_hash | Optional | String | Hash parameters | Hash/null | Sensitive data niet raw opslaan | Not implemented |
| request_parameters_redacted | Optional | JSON/text | Geredigeerde params | Redacted JSON/text | Nooit credentials/token opslaan | Not implemented |
| requested_time_range_start | Optional | Timestamp | Gevraagde starttijd | ISO-8601 UTC/null | Validatie tegen eindtijd | Not implemented |
| requested_time_range_end | Optional | Timestamp | Gevraagde eindtijd | ISO-8601 UTC/null | `end >= start` | Not implemented |
| requested_granularity | Optional | String | Gevraagde granulariteit | `1m`,`5m`,`1d`,... | Alleen metadata; geen fetch | Not implemented |
| requested_snapshot_type | Optional | String | Type snapshot | `latest`,`close`,`ohlc`,... | Voorstel, geen runtimegedrag | Not implemented |
| pacing_bucket | Optional | String | Pacing bucket | Provider-specifieke key | Audit voor rate-limit | Not implemented |
| pacing_weight | Optional | Integer | Pacing cost | 0..n | Negatieve waarden verboden | Not implemented |
| pacing_reset_at | Optional | Timestamp | Resetmoment pacing | ISO-8601 UTC/null | Verduidelijkt blokkades | Not implemented |
| provider_request_budget_remaining | Optional | Integer | Resterend budget | 0..n/null | Niet als runtimebeslissing nu | Not implemented |
| local_throttle_status | Optional | Enum/string | Lokale throttle status | `ok`,`throttled`,`blocked` | `blocked` vereist reason code | Not implemented |
| retry_count | Optional | Integer | Aantal retries | 0..n | Idempotency + audit | Not implemented |
| next_retry_not_before | Optional | Timestamp | Earliest retry | ISO-8601 UTC/null | Policy-gedreven | Not implemented |
| request_status | Proposed required | Enum/string | Uitkomststatus | Zie sectie E | Proposal only | Not implemented |
| provider_status_code | Optional | String/int | Externe statuscode | HTTP/code/null | Geen impliciete mapping naar succes | Not implemented |
| provider_error_code | Optional | String | Provider error code | Tekst/null | Redacted context | Not implemented |
| provider_error_message_redacted | Optional | Text | Geredigeerde foutboodschap | Tekst/null | Nooit secrets of raw PII | Not implemented |
| outcome_reason_code | Optional | String | Redencode uitkomst | Zie sectie E | Proposal only | Not implemented |
| received_record_count | Optional | Integer | Aantal ontvangen records | 0..n | 0 kan geldig zijn | Not implemented |
| stored_record_count | Optional | Integer | Aantal opgeslagen records | 0..n | Mag lager zijn dan received | Not implemented |
| rejected_record_count | Optional | Integer | Aantal geweigerde records | 0..n | Reden loggen verplicht | Not implemented |
| null_or_empty_response | Optional | Boolean | Lege response indicator | true/false/null | Nooit stilzwijgend corrigeren | Not implemented |
| initiated_by | Proposed required | String | Trigger actor | `system_job`,`user`,`api`,... | Auditverplichting | Not implemented |
| initiated_by_job_id | Optional | UUID/string | Job referentie | UUID/string/null | Jobfalen zichtbaar houden | Not implemented |
| triggered_by_event_id | Optional | UUID/string | Event referentie | UUID/string/null | Event chain trace | Not implemented |
| linked_readiness_evaluation_id | Optional | UUID/string | Link readiness evaluatie | UUID/string/null | Read-only readiness koppeling | Not implemented |
| linked_freshness_audit_id | Optional | UUID/string | Link freshness audit | UUID/string/null | Cross-contract trace | Not implemented |
| audit_notes_nl | Optional | Text | Menselijke auditnotitie | Eenvoudig NL | Geen adviesinhoud zonder trail | Not implemented |
| safe_for_analysis | Proposed required | Boolean | Veilig voor analyse | Default `false` | Conservatief default false | Not implemented |
| safe_for_suggestions | Proposed required | Boolean | Veilig voor suggesties | Default `false` | Conservatief default false | Not implemented |
| safe_for_action_drafts | Proposed required | Boolean | Veilig voor actiedrafts | Default `false` | Conservatief default false | Not implemented |

## E) Request-log status and reason-code proposal

Voorgestelde toekomstige `request_status` waarden (proposal, niet geïmplementeerd):
- `planned`
- `blocked_before_request`
- `skipped_by_policy`
- `throttled`
- `requested`
- `provider_timeout`
- `provider_error`
- `invalid_response`
- `empty_response`
- `stored_metadata_only`
- `stored_snapshot_metadata`
- `rejected_by_validation`
- `completed_status_only`

Voorgestelde reason-code groepen (proposal, geen enum-implementatie in Task 109):
- `identity_missing`
- `listing_unvalidated`
- `provider_not_configured`
- `account_mode_unknown`
- `paper_only_guard`
- `pacing_limit`
- `freshness_policy_block`
- `unsupported_asset_type`
- `unsupported_market`
- `invalid_time_range`
- `provider_unavailable`
- `provider_permission_denied`
- `provider_response_invalid`
- `no_data_returned`
- `storage_unavailable`
- `validation_failed`
- `runtime_not_enabled`

## F) Provider/source metadata candidate field catalog

| Field name | Required now? | Future storage type hint | Meaning | Safety notes |
|---|---|---|---|---|
| provider_source_id | Proposed required | UUID | Unieke provider/source identiteit | Auditanker |
| provider_code | Proposed required | String | Canonieke providercode | Consistent met request logs |
| provider_display_name | Optional | String | Leesbare providernaam | Alleen presentatie |
| provider_kind | Proposed required | Enum/string | Soort provider | Zie lijst hieronder |
| data_domain | Proposed required | Enum/string | Datadomein | Verbindt naar freshness policies |
| source_type | Proposed required | Enum/string | Brontype | Consistent met readiness contracten |
| source_authority_level | Optional | Enum/string | Autoriteitsniveau | Policy-gestuurd, geen runtime unlock |
| source_credibility_scope | Optional | String | Credibility scope | Evidence-only |
| source_license_scope | Optional | String | Licentiescope | Juridische audit |
| source_terms_scope | Optional | String | Terms-of-use scope | Juridische audit |
| provider_environment | Proposed required | Enum/string | Environment context | `unknown` conservatief |
| provider_account_mode | Proposed required | Enum/string | Accountmodus context | paper-only guard relevant |
| official_source | Optional | Boolean | Officiële bronvlag | Niet voldoende voor suggestieunlock |
| broker_source | Optional | Boolean | Brokerbronvlag | Metadata-only |
| user_uploaded_source | Optional | Boolean | User upload bronvlag | Evidence, geen instructie |
| third_party_market_data_source | Optional | Boolean | Derde partij marktdata | Vertrouwenscontext expliciet |
| derived_source | Optional | Boolean | Afgeleide bron | Herleidbaarheid verplicht |
| source_url_hash | Optional | String | Gehashte bron-URL | Geen raw secrets/query tokens |
| source_version | Optional | String | Bronversie | Reproduceerbaarheid |
| source_effective_from | Optional | Timestamp | Ingang broncontext | ISO-8601 UTC |
| source_effective_to | Optional | Timestamp | Einde broncontext | ISO-8601 UTC/null |
| created_at | Proposed required | Timestamp | Aanmaakmoment | Auditverplichting |
| updated_at | Proposed required | Timestamp | Laatste wijziging | Auditverplichting |
| disabled_at | Optional | Timestamp | Deactivatiemoment | ISO-8601 UTC/null |
| disabled_reason | Optional | String | Reden deactivatie | Veiligheidsbewijs |
| audit_notes_nl | Optional | Text | Eenvoudige NL auditnota | Geen runtimeclaim |

Voorgestelde `provider_kind` opties (anticiperend, proposal only):
- `broker`
- `market_data`
- `user_upload`
- `website_snapshot`
- `filing`
- `internal_derived`
- `manual_reference`
- `system_status`

## G) Freshness-audit record candidate field catalog

| Field name | Required now? | Future storage type hint | Meaning | Allowed values / format | Safety notes |
|---|---|---|---|---|---|
| freshness_audit_id | Proposed required | UUID | Unieke freshness audit id | UUID v4 | Auditanker |
| evaluated_at | Proposed required | Timestamp | Evaluatiemoment | ISO-8601 UTC | Tijdstempel verplicht |
| data_domain | Proposed required | Enum/string | Datadomein | `price_snapshot`,`fx`,`portfolio`,... | Policy-koppeling |
| provider_code | Optional | String | Providercontext | Canonieke code/null | Link met provider metadata |
| source_type | Optional | String | Brontypecontext | Enum/string/null | Link met source metadata |
| asset_id | Optional | UUID | Asset identity | UUID/null | Referentie-only |
| asset_listing_id | Optional | UUID | Listing identity | UUID/null | Listing gate blijft leidend |
| ibkr_conid | Optional | String/int | IBKR conid | Positief/null | Ontbreken kan blokkeren |
| snapshot_id | Optional | UUID/string | Snapshot referentie | UUID/string/null | Linkbaar naar snapshotrecord |
| snapshot_as_of | Optional | Timestamp | Snapshot as-of tijd | ISO-8601 UTC/null | Geen aanname over versheid |
| observed_at | Optional | Timestamp | Waarnemingstijd | ISO-8601 UTC/null | Moet valide zijn |
| received_at | Optional | Timestamp | Ontvangsttijd | ISO-8601 UTC/null | Voor leeftijdsberekening |
| stored_at | Optional | Timestamp | Opslagtijd | ISO-8601 UTC/null | Voor audittrail |
| age_seconds | Optional | Integer | Leeftijd op evaluatiemoment | 0..n/null | Negatief ongeldig |
| freshness_policy_code | Proposed required | String | Toegepaste policy | Policy code | Geen runtimepolicy in Task 109 |
| freshness_status | Proposed required | Enum/string | Resultaat status | Zie sectie H | Proposal only |
| freshness_reason_code | Optional | String | Redencode | Zie sectie H | Proposal only |
| freshness_window_seconds | Optional | Integer | Toegestane versheidswindow | 0..n | Domeinspecifiek |
| market_session_context | Optional | String | Market session context | `open`,`closed`,`pre`,`post`,... | Alleen context, geen runtime |
| market_calendar_status | Optional | String | Kalenderstatus | String/enum | Geen scheduler unlock |
| stale_after | Optional | Timestamp | Wanneer stale wordt | ISO-8601 UTC/null | Afgeleid van policy |
| expires_at | Optional | Timestamp | Wanneer expired wordt | ISO-8601 UTC/null | Afgeleid van policy |
| safe_for_analysis | Proposed required | Boolean | Veilig voor analyse | Default `false` | Conservatief false |
| safe_for_suggestions | Proposed required | Boolean | Veilig voor suggesties | Default `false` | Conservatief false |
| safe_for_action_drafts | Proposed required | Boolean | Veilig voor actiedrafts | Default `false` | Conservatief false |
| linked_request_log_id | Optional | UUID/string | Link naar request log | UUID/string/null | Traceability |
| linked_readiness_evaluation_id | Optional | UUID/string | Link naar readiness evaluatie | UUID/string/null | Cross-contract audit |
| blocker_summary_nl | Optional | Text | Eenvoudige NL blocker samenvatting | Korte NL tekst | Geen runtimeadvies |
| audit_help_nl | Optional | Text | Eenvoudige NL audithulp | Korte NL tekst | Duidelijk en conservatief |

## H) Freshness status and reason-code proposal

Voorgestelde toekomstige `freshness_status` waarden (proposal only):
- `not_evaluated`
- `blocked`
- `missing_snapshot`
- `metadata_only`
- `fresh_enough`
- `stale`
- `expired`
- `invalid_timestamp`
- `provider_unavailable`
- `storage_unavailable`
- `runtime_not_enabled`

Voorgestelde `freshness_reason_code` waarden (proposal only):
- `no_snapshot`
- `no_validated_listing`
- `no_provider_config`
- `no_runtime_fetch`
- `no_latest_price_fetching`
- `timestamp_missing`
- `timestamp_in_future`
- `observed_time_too_old`
- `received_time_too_old`
- `market_closed_policy`
- `unsupported_asset_type`
- `unsupported_exchange`
- `provider_error`
- `validation_failed`
- `manual_review_required`
- `safe_metadata_only`

Belangrijke safetyduiding:
- `fresh_enough` op zichzelf unlockt **geen suggesties**.
- Freshness is slechts **één gate** naast andere gates.
- Suggesties/action drafts mogen **nooit** op freshness alleen steunen.

## I) Relationship to existing readiness contracts

| Existing concept | Current status | Future relationship | Safety constraint |
|---|---|---|---|
| market-data readiness list/detail | Read-only contract actief | `linked_readiness_evaluation_id` + reason-code alignment | Geen runtime unlock |
| latest-snapshot metadata endpoint | Metadata/status-only actief | `snapshot_id`,`snapshot_as_of`,`freshness_status` mapping | Geen live/current prijsclaim |
| watchlist `asset_listing_readiness` | Read-only gate actief | `asset_listing_id`/`ibkr_conid` in request/freshness contracts | Ongevalideerd blijft blocked |
| AssetListing validation gate | Actief als blocker | Reason-codes `listing_unvalidated`/`no_validated_listing` | Geen analyse/suggestie unlock |
| source/evidence blocked-for-suggestions status | Actief als boundary | provider/source metadata ondersteunt provenance/trust audit | Evidence blijft geen instructie |
| Decision Package future requirement | Runtime pending | Future packages refereren request/freshness links | Task 109 maakt geen packages |
| AI output future requirement | Runtime pending | AI-output moet freshness/request auditlinks kunnen refereren | AI mag gates niet overrulen |
| IBKR paper action future requirement | Runtime pending | Paper-action audit kan request/freshness chain consumeren | Paper-only + user approval blijft hard |

## J) Traceability and audit linking proposal

Voorgesteld koppelmodel (toekomstig):
- request log linkt naar provider metadata (`provider_code` / `provider_source_id`);
- request log linkt naar freshness audit (`linked_freshness_audit_id`);
- freshness audit linkt naar readiness evaluatie (`linked_readiness_evaluation_id`);
- toekomstige snapshots linken terug naar request log (`linked_request_log_id`);
- toekomstig Decision Package kan refereren naar freshness audit + request log (Task 109 creëert géén Decision Packages);
- toekomstige audit viewer kan de volledige keten visualiseren.

## K) Security and privacy notes

- Geen secrets opslaan.
- Geen raw API keys opslaan.
- Geen raw account identifiers opslaan.
- Account IDs enkel gehashed/redacted (`account_id_hash`) indien nodig.
- Provider foutboodschappen redigeren (`provider_error_message_redacted`).
- Request parameters alleen gehashed/redacted opslaan indien gevoelig.
- User-upload source metadata blijft evidence, nooit instructie.

## L) Implementation sequencing proposal

Voorgestelde vervolgvolgorde (alleen voorstel):
1. **Task 110 kandidaat**: conservative storage/API contract skeleton voor request logs/provider metadata/freshness audit records (bij product owner approval).
2. **Task 111 kandidaat**: read-only status/API exposure voor deze contractrecords, nog steeds zonder runtime fetching.
3. Later: provider adapters, pacing enforcement en freshness evaluation runtime pas na expliciete gates.

## M) Explicit non-runtime proof checklist

- [ ] No app code changed
- [ ] No package code changed
- [ ] No migrations added
- [ ] No API endpoints added
- [ ] No web UI changed
- [ ] No scheduler added
- [ ] No fetch runtime added
- [ ] No latest-price fetching added
- [ ] No AI runtime added
- [ ] No suggestions added
- [ ] No Decision Packages runtime added
- [ ] No action drafts added
- [ ] No orders added
- [ ] No fake data added

## N) Task 107 tracking-drift prevention confirmation

Voor Task 109 completion in dezelfde PR bevestigd en geüpdatet:
- current-state title updated;
- `Huidige toestand:` line updated;
- Task 109 completion line added;
- `task-history.md` updated;
- `version-1-scope-register.md` updated;
- `version-1-backlog.md` updated;
- `next-task.md` updated.
